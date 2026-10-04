from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from gbm_twin.data import cfb_acquisition as acquisition


@pytest.fixture
def remote(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    browsed = []
    requested = []
    transfers = []

    class Client:
        token = "sensitive-bearer"

        def authenticate(self):
            pass

        def browse(self, path):
            browsed.append(path)
            pid, tp = path.split("/")[-2:]
            return [
                {
                    "path": path + f"/{int(pid)}_{tp}_{suffix}.nii.gz",
                    "basename": f"{int(pid)}_{tp}_{suffix}.nii.gz",
                    "type": "symbolic_link",
                }
                for suffix in ("gtv", "brain_mask", "t1gd", "rtdose", "flair")
            ]

        def transfer_spec(self, paths):
            requested.extend(paths)
            return {
                "direction": "receive",
                "paths": [{"source": "/package" + p["path"]} for p in paths],
                "token": "sensitive-transfer",
                "cookie": "sensitive-cookie",
                "remote_host": "tcia-node",
                "remote_user": "faspex",
                "ssh_port": 33001,
                "fasp_port": 33001,
            }

    monkeypatch.setattr(acquisition, "CFBPublicClient", Client)
    monkeypatch.setattr(acquisition, "resolve_ascp", lambda _: tmp_path / "ascp.exe")
    monkeypatch.setattr(acquisition, "_transport_key", lambda _, root: root / "key.pem")
    monkeypatch.setattr(
        acquisition.shutil, "disk_usage", lambda _: SimpleNamespace(free=10 * 1024**3)
    )

    def transfer(command, **kwargs):
        transfers.append(command)
        pairs_path = next(arg.split("=", 1)[1] for arg in command if "--file-pair-list=" in arg)
        pairs = Path(pairs_path).read_text().splitlines()
        assert "sensitive-transfer" not in " ".join(command)
        assert kwargs["env"]["ASPERA_SCP_TOKEN"] == "sensitive-transfer"
        for relative in pairs[1::2]:
            (Path(command[-1]) / relative).write_bytes(b"opaque-not-nifti")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(acquisition.subprocess, "run", transfer)
    kwargs = dict(
        source_root=tmp_path / "data",
        patient_ids=(15, 47),
        require_rtdose=False,
        plan_sha256="sealed-plan",
    )
    return kwargs, browsed, requested, transfers


def test_only_sealed_required_files_are_downloaded_and_receipted(remote):
    kwargs, browsed, requested, transfers = remote
    receipt = acquisition.acquire_cfb_files(**kwargs)
    assert receipt["complete"] is True
    assert len(receipt["files"]) == 18
    assert len(transfers) == 1
    assert {p.split("/")[2] for p in browsed} == {"015", "047"}
    assert not any("flair" in p["path"] or "rtdose" in p["path"] for p in requested)
    assert all(p["type"] == "symbolic_link" for p in requested)
    stored = (kwargs["source_root"] / "stage10_acquisition.json").read_text()
    assert "sensitive" not in stored
    assert receipt["image_content_decoded"] is False
    second = acquisition.acquire_cfb_files(**kwargs)
    assert second == receipt
    assert len(transfers) == 1


def test_remote_dry_run_does_not_create_source_or_transfer(remote):
    kwargs, _, _, transfers = remote
    result = acquisition.acquire_cfb_files(**kwargs, dry_run=True)
    assert len(result["missing_paths"]) == 18
    assert not kwargs["source_root"].exists()
    assert transfers == []


def test_spatial_model_adds_only_selected_t0_rtdose(remote):
    kwargs, _, requested, _ = remote
    kwargs["require_rtdose"] = True
    result = acquisition.acquire_cfb_files(**kwargs)
    assert len(result["files"]) == 20
    assert [p["path"] for p in requested if "rtdose" in p["path"]] == [
        "/CFB-GBM/015/t0/15_t0_rtdose.nii.gz",
        "/CFB-GBM/047/t0/47_t0_rtdose.nii.gz",
    ]


def test_modified_existing_file_is_rejected_without_network(remote):
    kwargs, browsed, _, _ = remote
    acquisition.acquire_cfb_files(**kwargs)
    (kwargs["source_root"] / "15/t2/15_t2_gtv.nii.gz").write_bytes(b"modified")
    count = len(browsed)
    with pytest.raises(ValueError, match="checksum mismatch"):
        acquisition.acquire_cfb_files(**kwargs)
    assert len(browsed) == count


def test_unverified_existing_source_is_never_overwritten(remote):
    kwargs, browsed, _, _ = remote
    target = kwargs["source_root"] / "15/t0/15_t0_t1gd.nii.gz"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing")
    with pytest.raises(ValueError, match="will not be overwritten"):
        acquisition.acquire_cfb_files(**kwargs)
    assert target.read_bytes() == b"existing"
    assert browsed == []


def test_missing_remote_input_prevents_all_downloads(remote, monkeypatch):
    kwargs, _, _, transfers = remote
    monkeypatch.setattr(acquisition.CFBPublicClient, "browse", lambda _, path: [])
    with pytest.raises(FileNotFoundError, match="missing/ambiguous"):
        acquisition.acquire_cfb_files(**kwargs)
    assert not kwargs["source_root"].exists()
    assert transfers == []


def test_scope_tampering_in_resealed_receipt_is_rejected(remote):
    kwargs, _, _, _ = remote
    acquisition.acquire_cfb_files(**kwargs)
    path = kwargs["source_root"] / "stage10_acquisition.json"
    payload = json.loads(path.read_text())
    payload["files"]["99/t2/99_t2_gtv.nii.gz"] = {}
    path.write_text(json.dumps(payload))
    (path.parent / "stage10_acquisition.sha256").write_text(acquisition.sha256_file(path))
    with pytest.raises(ValueError, match="sealed file scope"):
        acquisition.acquire_cfb_files(**kwargs)


def test_incomplete_transfer_keeps_completed_receipts_and_redacts_tokens(remote, monkeypatch):
    kwargs, _, _, transfers = remote
    original = acquisition.subprocess.run

    def partial(command, **args):
        original(command, **args)
        (kwargs["source_root"] / "47/t2/47_t2_gtv.nii.gz").unlink()
        return subprocess.CompletedProcess(command, 1, "", "sensitive-transfer sensitive-cookie")

    monkeypatch.setattr(acquisition.subprocess, "run", partial)
    with pytest.raises(RuntimeError) as error:
        acquisition.acquire_cfb_files(**kwargs)
    assert "sensitive" not in str(error.value)
    monkeypatch.setattr(acquisition.subprocess, "run", original)
    result = acquisition.acquire_cfb_files(**kwargs)
    assert result["complete"] is True
    last_pairs = [arg for arg in transfers[-1] if "--file-pair-list=" in arg]
    assert len(last_pairs) == 1


def test_bearer_token_is_never_sent_to_sdk_host():
    client = acquisition.CFBPublicClient()
    client.token = "private-bearer"
    seen = []

    class Opener:
        def open(self, request, **kwargs):
            seen.append(request)
            return io.BytesIO(b"data")

    client.opener = Opener()
    client._request(acquisition.SDK_KEY_URL)
    client._request(acquisition.FASPEX_URL + "/test")
    assert not seen[0].has_header("Authorization")
    assert seen[1].get_header("Authorization") == "Bearer private-bearer"
