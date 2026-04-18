"""Backwards-compatibility shim.

``DaikinOnectaDevice`` moved to ``custom_components.daikin_onecta.model.device``
as step 7.3 of the domain-model refactor (see
``docs/adr/0003-domain-model-package-layout.md``). This module only
re-exports the public names so that existing imports keep working during
phase 7. It will be removed once all internal consumers have migrated to
``model.device``.
"""

from __future__ import annotations

from typing import Final

from .model.device import DaikinOnectaDevice

__all__: Final = ("DaikinOnectaDevice",)
