from __future__ import annotations

from pydantic import BaseModel


class FeatureCapability(BaseModel):
    available: bool
    reason: str | None = None


class CapabilitiesResponse(BaseModel):
    patients: FeatureCapability
    viewer: FeatureCapability
    anatomy: FeatureCapability

    digital_twin: FeatureCapability
    runs: FeatureCapability
    tools: FeatureCapability
    research: FeatureCapability