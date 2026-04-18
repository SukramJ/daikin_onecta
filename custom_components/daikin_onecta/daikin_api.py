"""Backwards-compatibility shim.

The transport layer moved to ``custom_components.daikin_onecta.client.api``
as step 7.2 of the domain-model refactor (see
``docs/adr/0003-domain-model-package-layout.md``). This module only
re-exports the public names so that existing imports keep working during
phase 7. It will be removed once all internal consumers and downstream
packages have migrated to ``client.api``.
"""

from __future__ import annotations

from typing import Final

from .client.api import DaikinApi
from .client.api import JsonResponse
from .client.api import RateLimits
from .client.api import RequestResult

__all__: Final = ("DaikinApi", "JsonResponse", "RateLimits", "RequestResult")
