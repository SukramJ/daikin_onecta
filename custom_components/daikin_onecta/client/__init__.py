"""Transport layer: HTTP, OAuth, retry, circuit breaker.

Extracted from ``daikin_api.py`` as step 7.2 of the domain-model refactor
(see ``docs/adr/0003-domain-model-package-layout.md``). The old
``custom_components.daikin_onecta.daikin_api`` module keeps working as a
thin re-export shim for the duration of phase 7.
"""

from __future__ import annotations

from typing import Final

from .api import DaikinApi
from .api import JsonResponse
from .api import RateLimits
from .api import RequestResult

__all__: Final = ("DaikinApi", "JsonResponse", "RateLimits", "RequestResult")
