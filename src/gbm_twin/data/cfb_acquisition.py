"""Selective opaque downloads from the official TCIA CFB-GBM package."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from gbm_twin.workflows.provenance import sha256_file

COLLECTION_URL = "https://www.cancerimagingarchive.net/collection/cfb-gbm/"
FASPEX_URL = "https://faspex.cancerimagingarchive.net"
PACKAGE_ID = "1345"  # Version 4; never silently switch versions/patient numbering.
SDK_KEY_URL = "https://raw.githubusercontent.com/IBM/aspera-cli/main/lib/aspera/data/2"
SDK_KEY_SHA256 = "0ffb27243d7e77fd2c565a25f910b9dad305750cda96c959be8605b292a8c3d0"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CFBPublicClient:
    """Use the same public-link OAuth flow as the official Faspex web client."""

    def __init__(self) -> None:
        self.opener = build_opener(_NoRedirect())
        self.token = ""

    def _request(self, url: str, payload: dict | None = None) -> bytes:
        headers = {"User-Agent": "gbm-digital-twin/CFB-reserve", "Accept": "application/json"}
        if self.token and urlparse(url).netloc == urlparse(FASPEX_URL).netloc:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None if payload is None else json.dumps(payload).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        try:
            with self.opener.open(Request(url, data=data, headers=headers), timeout=60) as response:
                return response.read()
        except HTTPError as exc:
            # Do not include tokens, passcodes or authorization-code query strings in errors.
            raise RuntimeError(f"TCIA HTTP {exc.code}: {urlparse(url).path}") from None

    def authenticate(self) -> None:
        page = self._request(COLLECTION_URL).decode()
        match = re.search(
            r'href="(https://faspex\.cancerimagingarchive\.net/\?context=[^"]+)"', page
        )
        if match is None:
            raise ValueError("Official CFB-GBM public link was not found")
        context = parse_qs(urlparse(html.unescape(match[1])).query)["context"][0]
        info = json.loads(base64.b64decode(context))
        if str(info.get("package_id")) != PACKAGE_ID:
            raise ValueError(
                "TCIA published a different package; review dataset version before reveal"
            )
        config = self._request(FASPEX_URL + "/aspera/faspex/config.js").decode()
        client = re.search(r"client_id:\s*'([^']+)'", config)
        redirect = re.search(r"redirect_uri:\s*'([^']+)'", config)
        if client is None or redirect is None or not redirect[1].startswith("/aspera/faspex/"):
            raise ValueError("Unexpected public Faspex client configuration")
        redirect_uri = FASPEX_URL + redirect[1]
        query = urlencode(
            {
                "response_type": "code",
                "client_id": client[1],
                "redirect_uri": redirect_uri,
                "state": context,
            }
        )
        try:
            self.opener.open(
                FASPEX_URL + "/aspera/faspex/auth/authorize_public_link?" + query, timeout=60
            )
        except HTTPError as exc:
            if exc.code != 302:
                raise RuntimeError(
                    f"TCIA public-link authorization failed: HTTP {exc.code}"
                ) from None
            location = urlparse(exc.headers["Location"])
        else:
            raise ValueError("TCIA authorization did not return an authorization-code redirect")
        if location.netloc != urlparse(FASPEX_URL).netloc or location.path != redirect[1]:
            raise ValueError("Unexpected TCIA authorization redirect")
        auth = parse_qs(location.query)
        if auth.get("state") != [context] or not auth.get("code"):
            raise ValueError("TCIA OAuth state/code mismatch")
        result = json.loads(
            self._request(
                FASPEX_URL + "/aspera/faspex/auth/token",
                {
                    "code": auth["code"][0],
                    "state": context,
                    "grant_type": "authorization_code",
                    "client_id": client[1],
                    "redirect_uri": redirect_uri,
                },
            )
        )
        self.token = result["access_token"]

    def browse(self, path: str) -> list[dict]:
        url = FASPEX_URL + f"/aspera/faspex/api/v5/packages/{PACKAGE_ID}/files/received"
        result = json.loads(self._request(url, {"path": path}))
        items = result["items"]
        if len(items) != result["total_count"]:
            raise ValueError(f"Incomplete TCIA directory listing: {path}")
        return items

    def transfer_spec(self, paths: list[dict]) -> dict:
        url = (
            FASPEX_URL + f"/aspera/faspex/api/v5/packages/{PACKAGE_ID}/transfer_spec/download"
            "?type=received&transfer_type=connect"
        )
        return json.loads(self._request(url, {"paths": paths}))


def required_cfb_paths(patient_ids: tuple[int, ...], *, require_rtdose: bool) -> tuple[str, ...]:
    if not patient_ids or any(type(pid) is not int or pid <= 0 for pid in patient_ids):
        raise ValueError("CFB acquisition requires positive sealed patient IDs")
    paths = [
        f"{pid}/{tp}/{pid}_{tp}_{suffix}.nii.gz"
        for pid in patient_ids
        for tp in ("t0", "t1", "t2")
        for suffix in ("t1gd", "gtv", "brain_mask")
    ]
    if require_rtdose:
        paths.extend(f"{pid}/t0/{pid}_t0_rtdose.nii.gz" for pid in patient_ids)
    return tuple(paths)


def resolve_ascp(explicit: Path | None = None) -> Path:
    candidates = [
        explicit,
        os.getenv("GBM_TWIN_ASCP"),
        shutil.which("ascp"),
        Path("C:/Apps/IBM Aspera/transferd/bin/ascp.exe"),
    ]
    for candidate in candidates:
        if candidate is not None and Path(candidate).is_file():
            return Path(candidate).resolve()
    raise FileNotFoundError("Aspera ascp not found; pass --ascp-path or set GBM_TWIN_ASCP")


def _transport_key(client: CFBPublicClient, directory: Path) -> Path:
    # IBM distributes this well-known SSH transport key with its token-based CLI.
    # It grants no dataset rights; the scoped TCIA transfer token remains mandatory.
    der = client._request(SDK_KEY_URL)
    if hashlib.sha256(der).hexdigest() != SDK_KEY_SHA256:
        raise ValueError("IBM public SDK transport key checksum mismatch")
    key = directory / "ibm_token_transport.pem"
    key.write_text(
        "-----BEGIN RSA PRIVATE KEY-----\n"
        + "\n".join(textwrap.wrap(base64.b64encode(der).decode("ascii"), 64))
        + "\n-----END RSA PRIVATE KEY-----\n",
        encoding="ascii",
    )
    key.chmod(0o600)
    return key


def acquire_cfb_files(
    *,
    source_root: Path,
    patient_ids: tuple[int, ...],
    require_rtdose: bool,
    plan_sha256: str,
    ascp_path: Path | None = None,
    dry_run: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Caller must verify the sealed plan/provenance before this network operation."""
    required = required_cfb_paths(patient_ids, require_rtdose=require_rtdose)
    root = source_root.resolve()
    receipt_path = root / "stage10_acquisition.json"
    seal_path = root / "stage10_acquisition.sha256"
    receipt = {
        "package_id": PACKAGE_ID,
        "collection_url": COLLECTION_URL,
        "dataset_version": 4,
        "validation_plan_sha256": plan_sha256,
        "patient_ids": list(patient_ids),
        "files": {},
        "image_content_decoded": False,
    }
    if receipt_path.exists():
        if not seal_path.is_file() or seal_path.read_text().split()[0] != sha256_file(receipt_path):
            raise ValueError("CFB acquisition receipt checksum mismatch")
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        for field in ("package_id", "validation_plan_sha256", "patient_ids"):
            if existing[field] != receipt[field]:
                raise ValueError("CFB acquisition receipt belongs to another plan or dataset")
        receipt = existing
    files = receipt["files"]
    if not set(files).issubset(required) or receipt.get("image_content_decoded") is not False:
        raise ValueError("CFB acquisition receipt violates sealed file scope")
    missing = []
    for relative in required:
        target = root / relative
        if not target.resolve().is_relative_to(root):
            raise ValueError(f"CFB source destination escapes root: {relative}")
        if target.exists():
            if relative not in files or not target.is_file():
                raise ValueError(
                    f"Unverified existing CFB input will not be overwritten: {relative}"
                )
            if sha256_file(target) != files[relative]["sha256"]:
                raise ValueError(f"CFB input checksum mismatch: {relative}")
        else:
            missing.append(relative)
    if not missing:
        return receipt
    ascp = resolve_ascp(ascp_path)
    client = CFBPublicClient()
    client.authenticate()
    remote = {}
    # Browse only selected patient timepoints. Never recurse into other cohorts.
    for pid in patient_ids:
        for tp in ("t0", "t1", "t2"):
            directory = f"/CFB-GBM/{pid:03d}/{tp}"
            listing = client.browse(directory)
            for relative in (p for p in missing if p.startswith(f"{pid}/{tp}/")):
                matches = [entry for entry in listing if entry["basename"] == Path(relative).name]
                if len(matches) != 1 or matches[0]["type"] not in {"file", "symbolic_link"}:
                    raise FileNotFoundError(f"Official TCIA input missing/ambiguous: {relative}")
                entry = matches[0]
                if entry["path"] != directory + "/" + Path(relative).name:
                    raise ValueError(f"Unexpected remote TCIA path: {relative}")
                remote[relative] = entry
        if progress:
            progress(f"[cfb-acquire] verified remote paths for sealed patient {pid}")
    if dry_run:
        return {**receipt, "missing_paths": missing, "dry_run": True}
    root.mkdir(parents=True, exist_ok=True)
    # Leave several GiB for preparation/calibration. Remote symlink sizes are unavailable.
    if shutil.disk_usage(root).free < 4 * 1024**3:
        raise OSError("At least 4 GiB free space required for selective CFB acquisition")
    with tempfile.TemporaryDirectory(prefix=".stage10-transfer-", dir=root) as temporary:
        work = Path(temporary)
        key = _transport_key(client, work)
        spec = client.transfer_spec([remote[p] for p in missing])
        sources = spec.get("paths", [])
        if spec.get("direction") != "receive" or len(sources) != len(missing):
            raise ValueError("TCIA transfer specification does not match selected files")
        pairs = []
        for relative, source in zip(missing, sources, strict=True):
            remote_path = source["source"]
            if not remote_path.endswith(remote[relative]["path"]):
                raise ValueError("TCIA transfer specification changed a requested source path")
            pairs.extend((remote_path, relative))
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
        pair_file = work / "file_pairs.txt"
        pair_file.write_text("\n".join(pairs) + "\n", encoding="utf-8")
        environment = os.environ.copy()
        environment["ASPERA_SCP_TOKEN"] = spec["token"]
        environment["ASPERA_SCP_COOKIE"] = spec.get("cookie", "")
        command = [
            str(ascp),
            "-q",
            "-d",
            "-k",
            "2",
            "-l",
            "100m",
            "-i",
            str(key),
            "-P",
            str(spec["ssh_port"]),
            "-O",
            str(spec["fasp_port"]),
            "--mode=recv",
            "--user=" + spec["remote_user"],
            "--host=" + spec["remote_host"],
            "--overwrite=never",
            "--partial-file-suffix=.partial",
            "--file-pair-list=" + str(pair_file),
            str(root),
        ]
        if progress:
            progress(f"[cfb-acquire] downloading {len(missing)} opaque files; no MRI decoding")
        try:
            completed = subprocess.run(
                command, env=environment, capture_output=True, text=True, timeout=7200, check=False
            )
        except subprocess.TimeoutExpired:
            completed = subprocess.CompletedProcess(command, 124, "", "Transfer timed out")
        # Ascp publishes final names only after completion; retain receipts for an interrupted batch.
        for relative in missing:
            target = root / relative
            if target.is_file() and target.stat().st_size > 0:
                files[relative] = {
                    "remote_path": remote[relative]["path"],
                    "size": target.stat().st_size,
                    "sha256": sha256_file(target),
                }
        receipt["complete"] = len(files) == len(required)
        staged = work / "receipt.json"
        staged.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        staged.replace(receipt_path)
        seal_path.write_text(sha256_file(receipt_path) + "  stage10_acquisition.json\n")
        if completed.returncode or not receipt["complete"]:
            diagnostic = completed.stderr[-800:]
            for secret in (spec["token"], spec.get("cookie", ""), client.token):
                if secret:
                    diagnostic = diagnostic.replace(secret, "[redacted]")
            raise RuntimeError(
                f"CFB transfer incomplete (ascp exit {completed.returncode}); "
                "verified completed files retained; rerun to resume. " + diagnostic
            )
    return receipt
