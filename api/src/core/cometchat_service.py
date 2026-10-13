"""Server-side CometChat integration for secure user provisioning and auth token generation."""

import logging
from typing import Any, Dict, Optional
import httpx
from src.core.config import settings

logger = logging.getLogger(__name__)


class CometChatService:
    """Manages server-to-server CometChat REST API interactions using secure backend credentials."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        region: Optional[str] = None,
        rest_api_key: Optional[str] = None,
    ) -> None:
        self.app_id = (app_id or settings.cometchat_app_id).strip()
        self.region = (region or settings.cometchat_region or "us").strip()
        self.rest_api_key = (rest_api_key or settings.cometchat_rest_api_key).strip()

    @property
    def is_configured(self) -> bool:
        """Returns True if minimum required server-side credentials are present."""
        return bool(self.app_id and self.rest_api_key)

    @property
    def base_url(self) -> str:
        """Constructs the regional CometChat v3 REST API base URL."""
        return f"https://{self.app_id}.api-{self.region}.cometchat.io/v3"

    def get_public_config(self) -> Dict[str, Any]:
        """Returns client-safe configuration parameters (NO secrets)."""
        return {
            "app_id": self.app_id,
            "region": self.region,
            "is_configured": self.is_configured,
            "default_users": [
                {"uid": "analyst_1", "name": "Senior Demand Analyst", "role": "Analyst"},
                {"uid": "analyst_2", "name": "Inventory Operations Lead", "role": "Operations"},
            ],
        }

    def generate_auth_token(self, uid: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Securely provisions user and returns an ephemeral auth token for client-side login.

        Args:
            uid: Unique user identifier in CometChat.
            name: Optional display name for the user.

        Returns:
            Dictionary with auth_token and user metadata.
        """
        clean_uid = uid.strip()
        if not clean_uid:
            raise ValueError("User UID cannot be empty.")

        display_name = (name or clean_uid).strip()

        # Graceful development/test fallback when CometChat keys are not yet configured in environment
        if not self.is_configured:
            logger.info("CometChat not configured on server; returning simulated development auth token.")
            return {
                "status": "mock_mode",
                "uid": clean_uid,
                "name": display_name,
                "auth_token": f"mock_token_{clean_uid}",
                "message": (
                    "CometChat server keys (COMETCHAT_APP_ID, COMETCHAT_REST_API_KEY) "
                    "are not configured. Running in mock/development mode."
                ),
            }

        headers = {
            "apikey": self.rest_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Step 1: Attempt to create an auth token for existing user
        token_endpoint = f"{self.base_url}/users/{clean_uid}/auth_tokens"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(token_endpoint, headers=headers, json={"force": True})

                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    token = data.get("authToken") or data.get("token")
                    return {
                        "status": "success",
                        "uid": clean_uid,
                        "name": display_name,
                        "auth_token": token,
                    }

                # Step 2: If user does not exist (404 / ERR_UID_NOT_FOUND), provision user with withAuthToken
                if resp.status_code in (404, 400):
                    create_user_endpoint = f"{self.base_url}/users"
                    create_resp = client.post(
                        create_user_endpoint,
                        headers=headers,
                        json={
                            "uid": clean_uid,
                            "name": display_name,
                            "withAuthToken": True,
                        },
                    )

                    if create_resp.status_code in (200, 201):
                        create_data = create_resp.json().get("data", {})
                        token = create_data.get("authToken") or create_data.get("token")
                        return {
                            "status": "success",
                            "uid": clean_uid,
                            "name": display_name,
                            "auth_token": token,
                        }

                    err_msg = create_resp.text
                    logger.error("Failed to provision CometChat user: %s", err_msg)
                    raise RuntimeError(f"CometChat user provisioning failed ({create_resp.status_code}): {err_msg}")

                err_msg = resp.text
                logger.error("Failed to generate CometChat auth token: %s", err_msg)
                raise RuntimeError(f"CometChat token generation failed ({resp.status_code}): {err_msg}")

        except httpx.RequestError as exc:
            logger.error("Network error communicating with CometChat REST API: %s", exc)
            raise RuntimeError(f"CometChat API connection error: {exc}") from exc
