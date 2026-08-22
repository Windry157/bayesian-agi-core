import pytest
from src.utils.auth import create_token, verify_token


class TestAuth:
    def test_create_token(self):
        token = create_token("user-1", role="admin")
        assert token is not None
        assert isinstance(token, str)

    def test_verify_token_valid(self):
        token = create_token("user-1")
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["role"] == "user"

    def test_verify_token_invalid(self):
        payload = verify_token("invalid.token.here")
        assert payload is None

    def test_token_contains_claims(self):
        token = create_token("admin-user", role="admin")
        payload = verify_token(token)
        assert payload["role"] == "admin"
        assert "iat" in payload
        assert "exp" in payload
