"""Typed ``DataPoint`` wrapper around a single cloud value field.

The Daikin Onecta cloud encodes writable values as dicts of the form
``{"value": X, "settable": bool, "minValue": N, "maxValue": N,
"stepValue": N, "requiresReboot": bool}``. Not every field carries every
key — e.g. string valued ``onOffMode`` has no min/max.

``DataPoint`` is a frozen view over one such field. It knows:

- its value and the bounds (``value``, ``min_value``, ``max_value``,
  ``step_value``),
- whether the cloud accepts writes (``settable``),
- which management point it belongs to (``embedded_id``) and the raw
  field name inside that management point (``name``).

The wrapper is deliberately pure: writing goes through
``DaikinOnectaDevice.patch(...)`` with the DataPoint's ``embedded_id`` +
``name``. That keeps the transport concerns at the transport layer.
"""

from __future__ import annotations

from collections.abc import Iterator
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Final

__all__: Final = (
    "DataPoint",
    "iter_data_points",
)

# Keys on a management-point dict that carry metadata rather than a value
# field — iterating data points skips these.
_META_KEYS: Final[frozenset[str]] = frozenset(
    {
        "embeddedId",
        "managementPointType",
        "managementPointCategory",
        "managementPointSubType",
    }
)


@dataclass(frozen=True)
class DataPoint:
    """Read-only view over a single ``{value, …}`` field."""

    name: str
    """Field name inside the management point (e.g. ``"targetTemperature"``)."""

    embedded_id: str | None
    """Management-point ``embeddedId`` this DataPoint belongs to."""

    value: Any
    """Current value (type depends on the field: number / string / bool / dict)."""

    settable: bool = False
    """Whether the cloud accepts writes to this field."""

    min_value: float | None = None
    """``minValue`` from the cloud, if present."""

    max_value: float | None = None
    """``maxValue`` from the cloud, if present."""

    step_value: float | None = None
    """``stepValue`` from the cloud, if present."""

    requires_reboot: bool = False
    """Whether a write requires a device reboot."""

    raw: Mapping[str, Any] | None = None
    """Original field dict — useful for fields the wrapper does not yet type."""

    @classmethod
    def from_field(
        cls,
        name: str,
        field: Mapping[str, Any],
        *,
        embedded_id: str | None = None,
    ) -> DataPoint:
        """Build a DataPoint from one ``{"value": …}`` dict.

        If ``field`` is not a mapping, or has no ``value`` key, the call
        returns a DataPoint whose ``value`` is ``None`` and whose bounds
        are ``None`` — the raw passthrough still works.
        """
        if not isinstance(field, Mapping):
            return cls(name=name, embedded_id=embedded_id, value=None)

        def _as_float(key: str) -> float | None:
            raw = field.get(key)
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                return float(raw)
            return None

        return cls(
            name=name,
            embedded_id=embedded_id,
            value=field.get("value"),
            settable=bool(field.get("settable", False)),
            min_value=_as_float("minValue"),
            max_value=_as_float("maxValue"),
            step_value=_as_float("stepValue"),
            requires_reboot=bool(field.get("requiresReboot", False)),
            raw=field,
        )


def iter_data_points(
    mp_raw: Mapping[str, Any],
    *,
    embedded_id: str | None = None,
) -> Iterator[DataPoint]:
    """Yield DataPoints for every top-level value-field on a management point.

    Only fields that look like value wrappers (``Mapping`` containing a
    ``value`` key) are included. Metadata keys (``embeddedId``,
    ``managementPointType``, …) and non-wrapper fields (e.g.
    ``consumptionData``) are skipped.
    """
    mp_embedded_id = embedded_id
    if mp_embedded_id is None:
        raw_id = mp_raw.get("embeddedId")
        mp_embedded_id = raw_id if isinstance(raw_id, str) else None

    for name, field in mp_raw.items():
        if name in _META_KEYS:
            continue
        if isinstance(field, Mapping) and "value" in field:
            yield DataPoint.from_field(name, field, embedded_id=mp_embedded_id)
