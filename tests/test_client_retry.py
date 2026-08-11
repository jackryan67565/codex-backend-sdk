import requests

import codex_backend_sdk._transport as transport_module
from codex_backend_sdk import OpenAI
from codex_backend_sdk._storage import _CredentialStore


class DummySession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class RetryClient(OpenAI):
    def __init__(self, outcomes, **kwargs):
        super().__init__(max_retries=kwargs.pop("max_retries", 2), retry_base_delay=0, **kwargs)
        self._CodexClient__credentials = _CredentialStore(
            access_token="test-token",
            account_id="test-account",
        )
        self._session = DummySession(outcomes)


def _response(status_code, *, body=b"{}", headers=None):
    response = requests.Response()
    response.was_closed = False
    response.status_code = status_code
    response._content = body
    response.headers.update(headers or {})
    response.url = "https://example.test"
    response.close = lambda: setattr(response, "was_closed", True)
    return response


def test_retry_retries_5xx_then_returns_success(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)
    retried_response = _response(503)
    client = RetryClient([
        retried_response,
        _response(200, body=b'{"ok": true}'),
    ])

    response = client._request_models(client_version="test")

    assert response.json() == {"ok": True}
    assert len(client._session.calls) == 2
    assert client._session.calls[0][2]["allow_redirects"] is False
    assert retried_response.was_closed is True
    assert sleeps == [0]


def test_retry_honors_retry_after_header(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)
    client = RetryClient([
        _response(429, headers={"Retry-After": "1.5"}),
        _response(200),
    ])

    client._request_models(client_version="test")

    assert len(client._session.calls) == 2
    assert sleeps == [1.5]


def test_retry_caps_retry_after_header(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)
    client = RetryClient([
        _response(429, headers={"Retry-After": "1000000"}),
        _response(200),
    ])

    client._request_models(client_version="test")

    assert len(client._session.calls) == 2
    assert sleeps == [60]


def test_retry_caps_exponential_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)

    transport_module.sleep_before_retry(
        None,
        5,
        retry_base_delay=60,
    )

    assert sleeps == [60]


def test_retry_does_not_retry_client_errors(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)
    client = RetryClient([
        _response(400, body=b'{"error": "bad request"}'),
    ])

    try:
        client._request_models(client_version="test")
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("Expected HTTPError")

    assert len(client._session.calls) == 1
    assert sleeps == []


def test_retry_retries_transport_timeout(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)
    client = RetryClient([
        requests.Timeout("temporary timeout"),
        _response(200, body=b'{"ok": true}'),
    ])

    response = client._request_models(client_version="test")

    assert response.json() == {"ok": True}
    assert len(client._session.calls) == 2
    assert sleeps == [0]


def test_retry_never_replays_non_idempotent_response_post(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)
    client = RetryClient([
        _response(503),
        _response(200),
    ])

    try:
        client._request_response(body={"input": []})
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("Expected HTTPError")

    assert len(client._session.calls) == 1
    assert sleeps == []


def test_retry_never_replays_response_post_after_timeout(monkeypatch):
    sleeps = []
    monkeypatch.setattr(transport_module.time, "sleep", sleeps.append)
    client = RetryClient([
        requests.Timeout("ambiguous delivery"),
        _response(200),
    ])

    try:
        client._request_response(body={"input": []})
    except requests.Timeout:
        pass
    else:
        raise AssertionError("Expected Timeout")

    assert len(client._session.calls) == 1
    assert sleeps == []
