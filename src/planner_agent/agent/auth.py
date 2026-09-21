"""Authentication utilities for Agent Engine A2A connections.

Provides Google Cloud auth for httpx requests to Agent Engine agents.
"""

import httpx
from google.auth import default
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request as AuthRequest


class GoogleAuthRefresh(httpx.Auth):
    """Google Cloud Auth with lazy credential refresh.

    Credentials are initialized lazily on first request to avoid
    serialization issues with ADK agents.
    """

    def __init__(self, scopes: list[str] | None = None) -> None:
        self.scopes = scopes or ["https://www.googleapis.com/auth/cloud-platform"]
        self.credentials: Credentials | None = None
        self.auth_request: AuthRequest | None = None

    def auth_flow(self, request: httpx.Request):
        if self.credentials is None:
            self.credentials, _ = default(scopes=self.scopes)
            self.auth_request = AuthRequest()

        if not self.credentials.valid:
            self.credentials.refresh(self.auth_request)

        request.headers["Authorization"] = f"Bearer {self.credentials.token}"
        yield request
