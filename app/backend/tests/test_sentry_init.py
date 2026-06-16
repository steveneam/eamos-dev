from app.core.sentry import _scrub_event, _strip_query, init_sentry


def test_strip_query_removes_variant_and_fragment():
    assert (
        _strip_query("https://eamos-dev-sg.onrender.com/report?q=RPE65:c.130C>T")
        == "https://eamos-dev-sg.onrender.com/report"
    )
    assert _strip_query("https://x/path#frag") == "https://x/path"
    assert _strip_query("https://x/path") == "https://x/path"


def test_scrub_event_strips_request_query_and_transaction():
    event = {
        "request": {"url": "https://x/report?q=RPE65:c.130C>T", "query_string": "q=RPE65"},
        "transaction": "GET /report?q=secret",
    }
    out = _scrub_event(event, {})
    assert out is not None
    assert out["request"]["url"] == "https://x/report"
    assert "query_string" not in out["request"]
    assert out["transaction"] == "GET /report"


def test_init_sentry_is_noop_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert init_sentry() is False
