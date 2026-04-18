"""Contract schema for Daikin Onecta cloud responses.

The Daikin cloud answers ``GET /v1/gateway-devices`` with a list of device
dicts. Every field in a device is nested inside ``managementPoints`` which
are themselves dictionaries keyed by ``managementPointType``. Values are
typically wrapped inside an inner dict with a ``value`` key plus metadata
(``settable``, ``maxLength``, ``minValue``, ``stepValue``, …).

This module declares the minimum shape the integration relies on and
provides a small validator used by the contract tests. It deliberately
stays a soft contract: unknown keys are allowed, optional keys are only
checked when present. The goal is to detect **breaking** response shape
changes, not every cosmetic addition.

Phase 5.5 (full schema validation) will build on this — same shape, more
surface.
"""

from __future__ import annotations

from typing import Any
from typing import Final
from typing import TypedDict

from .exceptions import DaikinValidationError

__all__: Final = (
    "DeviceResponse",
    "ManagementPoint",
    "ValidationIssue",
    "ValueWrapper",
    "validate_cloud_response",
    "validate_device",
)


class ValueWrapper(TypedDict, total=False):
    """Wrapper dict Daikin uses for every data point."""

    value: Any
    settable: bool
    maxLength: int
    minValue: float
    maxValue: float
    stepValue: float


class ManagementPoint(TypedDict, total=False):
    """One management point inside a device (by `managementPointType`)."""

    embeddedId: str
    managementPointType: str
    managementPointCategory: str
    firmwareVersion: ValueWrapper
    modelInfo: ValueWrapper
    serialNumber: ValueWrapper
    softwareVersion: ValueWrapper
    macAddress: ValueWrapper
    name: ValueWrapper


class DeviceResponse(TypedDict, total=False):
    """One device entry from ``GET /v1/gateway-devices``."""

    id: str
    deviceModel: str
    type: str
    timestamp: str
    isCloudConnectionUp: ValueWrapper
    managementPoints: list[ManagementPoint]


class ValidationIssue(TypedDict):
    """One issue found by the contract validator."""

    path: str
    reason: str


_REQUIRED_DEVICE_KEYS: Final = ("id", "deviceModel", "managementPoints")
_REQUIRED_MP_KEYS: Final = ("embeddedId", "managementPointType")


def validate_cloud_response(payload: Any) -> list[ValidationIssue]:
    """Validate a full ``GET /v1/gateway-devices`` response.

    Returns a list of issues; an empty list means the payload satisfies the
    contract. Does not raise — callers decide how strict they want to be.
    """
    issues: list[ValidationIssue] = []
    if not isinstance(payload, list):
        issues.append({"path": "$", "reason": f"top-level must be a list, got {type(payload).__name__}"})
        return issues

    for index, device in enumerate(payload):
        issues.extend(validate_device(device, path=f"$[{index}]"))
    return issues


def validate_device(device: Any, *, path: str = "$") -> list[ValidationIssue]:
    """Validate a single device dict. See ``validate_cloud_response``."""
    issues: list[ValidationIssue] = []

    if not isinstance(device, dict):
        issues.append({"path": path, "reason": f"device must be a dict, got {type(device).__name__}"})
        return issues

    for key in _REQUIRED_DEVICE_KEYS:
        if key not in device:
            issues.append({"path": f"{path}.{key}", "reason": "required key missing"})

    if "id" in device and not isinstance(device["id"], str):
        issues.append({"path": f"{path}.id", "reason": "must be str"})

    if "deviceModel" in device and not isinstance(device["deviceModel"], str):
        issues.append({"path": f"{path}.deviceModel", "reason": "must be str"})

    icu = device.get("isCloudConnectionUp")
    if icu is not None:
        if not isinstance(icu, dict):
            issues.append({"path": f"{path}.isCloudConnectionUp", "reason": "must be a value-wrapper dict"})
        elif "value" not in icu:
            issues.append({"path": f"{path}.isCloudConnectionUp.value", "reason": "value-wrapper missing 'value' key"})

    mps = device.get("managementPoints")
    if mps is not None:
        if not isinstance(mps, list):
            issues.append({"path": f"{path}.managementPoints", "reason": "must be a list"})
        else:
            for i, mp in enumerate(mps):
                issues.extend(_validate_management_point(mp, path=f"{path}.managementPoints[{i}]"))

    return issues


def _validate_management_point(mp: Any, *, path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(mp, dict):
        issues.append({"path": path, "reason": f"management point must be a dict, got {type(mp).__name__}"})
        return issues
    for key in _REQUIRED_MP_KEYS:
        if key not in mp:
            issues.append({"path": f"{path}.{key}", "reason": "required key missing"})
        elif not isinstance(mp[key], str):
            issues.append({"path": f"{path}.{key}", "reason": "must be str"})
    return issues


def require_valid_cloud_response(payload: Any) -> None:
    """Raise ``DaikinValidationError`` if the payload does not satisfy the contract.

    Convenience wrapper for callers that want a hard-fail instead of inspecting
    the issue list. Intended for use once phase 5.5 wires this into the
    coordinator path.
    """
    issues = validate_cloud_response(payload)
    if issues:
        first = issues[0]
        raise DaikinValidationError(f"{first['path']}: {first['reason']} (and {len(issues) - 1} more)")
