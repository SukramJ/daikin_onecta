"""Application Credentials platform for Daikin Onecta."""

from __future__ import annotations

from typing import Final

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import OAUTH2_AUTHORIZE
from .const import OAUTH2_TOKEN

__all__: Final = ("async_get_authorization_server",)


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE,
        token_url=OAUTH2_TOKEN,
    )
