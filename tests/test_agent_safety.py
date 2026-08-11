import base64
import importlib
import inspect
import json

import pytest

import codex_backend_sdk
from codex_backend_sdk import CodexClient
from codex_backend_sdk._storage import _CredentialStore, _load_credentials
from codex_backend_sdk._transport import request_with_retries
from codex_backend_sdk.resources.models import _model_from_backend


def _credential() -> _CredentialStore:
    return _CredentialStore(access_token="access-secret", account_id="acct_123")


def test_public_client_exposes_only_agent_safe_resources():
    client = CodexClient()

    assert not hasattr(client, "__dict__")
    assert hasattr(client, "responses")
    assert hasattr(client, "models")
    for unsafe in ("audio", "codex", "embeddings", "files", "images", "realtime"):
        assert not hasattr(client, unsafe)
    for unsafe in (
        "_auth_headers",
        "_credentials",
        "_get_chatgpt",
        "_get_raw",
        "_get_wham",
        "_post",
        "_post_chatgpt",
        "_post_openai",
        "_request_with_retries",
    ):
        assert not hasattr(client, unsafe)


def test_public_package_does_not_export_credential_primitives():
    for unsafe in (
        "TokenStore",
        "load_tokens",
        "save_tokens",
        "run_oauth_flow",
        "refresh_access_token",
    ):
        assert unsafe not in codex_backend_sdk.__all__
        assert not hasattr(codex_backend_sdk, unsafe)


@pytest.mark.parametrize(
    "module",
    [
        "codex_backend_sdk.oauth",
        "codex_backend_sdk.pkce",
        "codex_backend_sdk.storage",
        "codex_backend_sdk.resources.codex",
        "codex_backend_sdk.resources.files",
        "codex_backend_sdk.resources.images",
        "codex_backend_sdk.resources.openai_oauth",
        "codex_backend_sdk.resources.realtime",
    ],
)
def test_retired_sensitive_modules_are_not_shipped(module):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_credential_repr_never_contains_access_token():
    rendered = repr(_credential())
    assert "access-secret" not in rendered
    assert "acct_123" not in rendered


def test_client_session_ignores_environment_proxies():
    assert CodexClient()._session.trust_env is False


def test_internal_transport_does_not_accept_arbitrary_request_options():
    parameters = inspect.signature(request_with_retries).parameters.values()

    assert all(parameter.kind is not inspect.Parameter.VAR_KEYWORD for parameter in parameters)


def test_client_context_manager_closes_owned_session(monkeypatch):
    client = CodexClient()
    closed = []
    monkeypatch.setattr(client._session, "close", lambda: closed.append(True))

    with client as entered:
        assert entered is client

    assert closed == [True]


def test_model_conversion_does_not_retain_unmapped_backend_payload():
    model = _model_from_backend({
        "slug": "gpt-test",
        "display_name": "Test",
        "base_instructions": "do-not-retain",
        "available_in_plans": ["private-plan"],
        "prefer_websockets": True,
        "unmapped_private_field": "do-not-retain",
    })

    assert model.id == "gpt-test"
    assert not hasattr(model, "raw")
    assert not hasattr(model, "base_instructions")
    assert not hasattr(model, "available_in_plans")
    assert not hasattr(model, "prefer_websockets")
    assert not hasattr(model, "unmapped_private_field")


@pytest.mark.parametrize("timeout", [None, 0, -1, 601, True])
def test_client_rejects_unbounded_or_invalid_timeouts(timeout):
    expected = TypeError if timeout is None or timeout is True else ValueError
    with pytest.raises(expected):
        CodexClient(timeout=timeout)


@pytest.mark.parametrize("max_retries", [-1, 6, True, 1.5])
def test_client_bounds_model_read_retries(max_retries):
    expected = TypeError if max_retries is True or max_retries == 1.5 else ValueError
    with pytest.raises(expected):
        CodexClient(max_retries=max_retries)


@pytest.mark.parametrize("timeout", [None, 0, 601])
def test_response_calls_reject_invalid_per_call_timeouts_before_network(timeout):
    client = CodexClient()
    client._CodexClient__credentials = _credential()
    expected = TypeError if timeout is None else ValueError

    with pytest.raises(expected):
        client.responses.create(input="test", timeout=timeout)


def test_authenticate_uses_current_minimal_credentials(monkeypatch):
    monkeypatch.setattr("codex_backend_sdk._client._load_credentials", _credential)
    monkeypatch.setattr(
        "codex_backend_sdk._client._access_token_needs_refresh",
        lambda credentials: False,
    )

    client = CodexClient().authenticate()

    assert client.authenticated is True
    assert not hasattr(client, "account_info")


def test_authenticate_never_starts_interactive_login(monkeypatch):
    monkeypatch.setattr("codex_backend_sdk._client._load_credentials", lambda: None)

    with pytest.raises(RuntimeError, match="trusted Codex CLI"):
        CodexClient().authenticate()


def test_authenticate_refuses_token_that_needs_refresh(monkeypatch):
    monkeypatch.setattr("codex_backend_sdk._client._load_credentials", _credential)
    monkeypatch.setattr(
        "codex_backend_sdk._client._access_token_needs_refresh",
        lambda credentials: True,
    )

    with pytest.raises(RuntimeError, match="expired or near expiry"):
        CodexClient().authenticate()


def test_auth_loader_discards_refresh_token_api_key_and_identity_fields(tmp_path, monkeypatch):
    auth_dir = tmp_path / "codex-home"
    auth_dir.mkdir()
    payload = base64.urlsafe_b64encode(json.dumps({"exp": 4102444800}).encode()).decode().rstrip("=")
    access_token = f"header.{payload}.signature"
    (auth_dir / "auth.json").write_text(
        json.dumps({
            "OPENAI_API_KEY": "api-secret",
            "tokens": {
                "access_token": access_token,
                "refresh_token": "refresh-secret",
                "id_token": "id-secret",
                "account_id": "acct_123",
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(auth_dir))

    credentials = _load_credentials()

    assert credentials is not None
    assert credentials.account_id == "acct_123"
    assert credentials._access_token == access_token
    assert not hasattr(credentials, "__dict__")
    assert not hasattr(credentials, "access_token")
    assert "refresh-secret" not in repr(credentials)
    assert "api-secret" not in repr(credentials)


def test_auth_loader_refuses_linked_credential_file(tmp_path, monkeypatch):
    auth_dir = tmp_path / "codex-home"
    auth_dir.mkdir()
    target = tmp_path / "elsewhere.json"
    target.write_text("{}", encoding="utf-8")
    (auth_dir / "auth.json").symlink_to(target)
    monkeypatch.setenv("CODEX_HOME", str(auth_dir))

    with pytest.raises(RuntimeError, match="linked Codex credential"):
        _load_credentials()
