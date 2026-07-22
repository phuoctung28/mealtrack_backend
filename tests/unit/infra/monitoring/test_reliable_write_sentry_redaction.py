"""Sentinel tests for provider payload redaction."""

from unittest.mock import MagicMock

from src.infra.monitoring.sentry import SentryObservabilityConnector


def test_sentry_hooks_scrub_request_exception_sql_and_breadcrumb_sentinels(monkeypatch):
    sdk = MagicMock()
    monkeypatch.setattr("src.infra.monitoring.sentry.sentry_sdk", sdk)
    monkeypatch.setattr("src.infra.monitoring.sentry.settings.SENTRY_DSN", "dsn")

    connector = SentryObservabilityConnector()
    connector.initialize()
    hooks = sdk.init.call_args.kwargs
    event = {
        "request": {
            "url": "https://host/v1/operations/op-sentinel?key=query-sentinel",
            "data": "body-sentinel",
        },
        "exception": {"values": [{"value": "SQL bind sql-sentinel uid-sentinel"}]},
        "breadcrumbs": {
            "values": [
                {"message": "breadcrumb-sentinel", "data": {"sql": "sql-sentinel"}}
            ]
        },
        "contexts": {
            "trace": {"op": "http.server", "description": "/v1/operations/op-sentinel"}
        },
    }

    scrubbed = hooks["before_send"](event, {})
    rendered = repr(scrubbed)
    for forbidden in (
        "op-sentinel",
        "query-sentinel",
        "body-sentinel",
        "sql-sentinel",
        "uid-sentinel",
        "breadcrumb-sentinel",
    ):
        assert forbidden not in rendered


def test_sentry_transaction_hook_drops_sql_span_and_templates_http_span(monkeypatch):
    sdk = MagicMock()
    monkeypatch.setattr("src.infra.monitoring.sentry.sentry_sdk", sdk)
    monkeypatch.setattr("src.infra.monitoring.sentry.settings.SENTRY_DSN", "dsn")
    connector = SentryObservabilityConnector()
    connector.initialize()
    hook = sdk.init.call_args.kwargs["before_send_transaction"]

    event = {
        "transaction": "/v1/operations/op-sentinel",
        "spans": [
            {"op": "http.server", "description": "/v1/operations/op-sentinel"},
            {
                "op": "db.sql.query",
                "description": "SELECT * FROM users WHERE id = :uid",
                "data": {"db.params": "sql-sentinel"},
            },
        ],
    }
    scrubbed = hook(event, {})
    assert scrubbed is not None
    assert scrubbed["transaction"] == "unmatched"
    assert len(scrubbed["spans"]) == 1
    assert scrubbed["spans"][0]["description"] == "unmatched"
