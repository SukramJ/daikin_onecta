"""Domain model layer: typed devices, management points, data points.

Introduced as step 7.3 of the domain-model refactor (see
``docs/adr/0003-domain-model-package-layout.md``). The old
``custom_components.daikin_onecta.device`` module keeps working as a
re-export shim for the duration of phase 7.
"""

from __future__ import annotations

from typing import Final

from .data_point import DataPoint
from .data_point import iter_data_points
from .device import DaikinOnectaDevice
from .management_point import ManagementPoint
from .management_point import management_point_from_json

__all__: Final = (
    "DaikinOnectaDevice",
    "DataPoint",
    "ManagementPoint",
    "iter_data_points",
    "management_point_from_json",
)
