import json

import pytest
from websockets.asyncio.server import serve

import devtools_inspector.cdp as cdp
from devtools_inspector.cdp import BrowserConnectionError, BrowserSession, DiagnosticCollector, _validate_local_http_endpoint
from devtools_inspector.redaction import redact_text, redact_url


def test_console_issue_keeps_source_location_and_deduplicates():
    collector = DiagnosticCollector("tab-1")
    event = {
        "type": "error",
        "args": [{"type": "string", "value": "TypeError: broken"}],
        "stackTrace": {"callFrames": [{"url": "http://localhost:3000/src/app.js", "lineNumber": 8, "columnNumber": 2, "functionName": "render"}]},
    }
    collector.handle_event("Runtime.consoleAPICalled", event)
    collector.handle_event("Runtime.consoleAPICalled", event)
    issues = collector.issues
    assert len(issues) == 1
    assert issues[0].category == "console"
    assert issues[0].confidence == "confirmed"
    assert issues[0].source_location.line == 9
    assert issues[0].source_location.function == "render"


def test_network_failure_is_normalized_and_redacted():
    collector = DiagnosticCollector("tab-1")
    collector.handle_event(
        "Network.requestWillBeSent",
        {
            "requestId": "req-1",
            "request": {"url": "https://example.test/data?access_token=hidden", "method": "GET"},
            "type": "Fetch",
            "timestamp": 10.0,
            "initiator": {"type": "script"},
        },
    )
    collector.handle_event("Network.loadingFailed", {"requestId": "req-1", "errorText": "net::ERR_FAILED"})
    issue = collector.issues[0]
    assert issue.category == "network"
    assert issue.confidence == "confirmed"
    assert issue.url == "https://example.test/data?access_token=%5BREDACTED%5D"
    assert "hidden" not in issue.explanation
    assert issue.evidence["initiator"] == "script"


def test_http_error_captures_status_and_deduplicates():
    collector = DiagnosticCollector("tab-2")
    request = {"requestId": "r", "request": {"url": "http://localhost/api/missing", "method": "POST"}, "timestamp": 5}
    collector.handle_event("Network.requestWillBeSent", request)
    event = {"requestId": "r", "type": "Fetch", "response": {"url": "http://localhost/api/missing", "status": 503}}
    collector.handle_event("Network.responseReceived", event)
    collector.handle_event("Network.responseReceived", event)
    assert len(collector.issues) == 1
    assert collector.issues[0].evidence["status"] == 503
    assert collector.issues[0].severity == "error"


def test_secret_redaction_handles_text_and_urls():
    assert "hidden" not in redact_text("Bearer hidden api_key=hidden")
    assert "top-secret" not in redact_url("https://example.test/?token=top-secret")
    assert "fragment-secret" not in redact_url("https://example.test/#access_token=fragment-secret")


def test_long_task_is_normalized_with_timing_correlated_action_evidence():
    collector = DiagnosticCollector("tab-3")
    collector.handle_event(
        "Runtime.consoleAPICalled",
        {"type": "debug", "args": [{"value": "__DEVTOOLS_INSPECTOR_PERFORMANCE__:" + json.dumps({
            "kind": "action", "name": "click", "processingStart": 100, "processingEnd": 460,
        })}]},
    )
    collector.handle_event(
        "Runtime.consoleAPICalled",
        {"type": "debug", "args": [{"value": "__DEVTOOLS_INSPECTOR_PERFORMANCE__:" + json.dumps({
            "kind": "longtask", "url": "http://localhost:8000/", "startTime": 105, "duration": 350,
            "name": "self", "attribution": [{"containerSrc": "http://localhost:8000/"}],
        })}]},
    )
    issue = collector.issues[0]
    assert issue.category == "performance"
    assert issue.evidence["duration_ms"] == 350
    assert issue.evidence["action_association"] == "timing_correlated"
    assert issue.evidence["actions"][0]["name"] == "click"


def test_performance_ignores_short_malformed_and_unsupported_entries():
    collector = DiagnosticCollector("tab-4")
    marker = "__DEVTOOLS_INSPECTOR_PERFORMANCE__:"
    collector.handle_event("Runtime.consoleAPICalled", {"type": "debug", "args": [{"value": marker + "not json"}]})
    collector.handle_event("Runtime.consoleAPICalled", {"type": "debug", "args": [{"value": marker + json.dumps({"kind": "support", "longtask": False})}]})
    collector.handle_event("Runtime.consoleAPICalled", {"type": "debug", "args": [{"value": marker + json.dumps({"kind": "longtask", "duration": "nope"})}]})
    collector.handle_event("Runtime.consoleAPICalled", {"type": "debug", "args": [{"value": marker + json.dumps({"kind": "longtask", "startTime": 1, "duration": 49.9})}]})
    assert collector.performance_observer_supported is False
    assert collector.issues == []


def test_tracing_fallback_records_only_long_run_tasks_and_timing_correlates_clicks():
    collector = DiagnosticCollector("tab-5")
    collector.add_trace_events(
        [
            {"name": "EventDispatch", "ph": "X", "ts": 1_000_000, "dur": 350_000, "args": {"data": {"type": "click"}}},
            {"name": "EventDispatch", "ph": "X", "ts": 1_100_000, "dur": 10, "args": "malformed"},
            {"name": "RunTask", "ph": "X", "ts": 1_000_100, "dur": 350_000},
            {"name": "RunTask", "ph": "X", "ts": 2_000_000, "dur": 49_000},
            {"name": "RunTask", "ph": "X", "ts": "bad", "dur": 350_000},
        ],
        "http://localhost:8000/",
    )
    issue = collector.issues[0]
    assert issue.evidence["source"] == "CDP Tracing fallback"
    assert issue.evidence["duration_ms"] == 350
    assert issue.evidence["action_association"] == "timing_correlated"
    assert issue.evidence["actions"][0]["name"] == "click"


def test_non_local_debugging_endpoints_are_rejected():
    try:
        _validate_local_http_endpoint("http://192.0.2.1:9222")
    except BrowserConnectionError as error:
        assert "localhost" in str(error)
    else:
        raise AssertionError("Non-local CDP endpoints must be rejected")


@pytest.mark.asyncio
async def test_missing_target_returns_actionable_connection_error(monkeypatch):
    monkeypatch.setattr(cdp.asyncio, "to_thread", lambda function, *args: _return_empty_targets())
    with pytest.raises(BrowserConnectionError, match="List targets"):
        await BrowserSession().connect("http://127.0.0.1:9222", "missing")


async def _return_empty_targets():
    return []


@pytest.mark.asyncio
async def test_cdp_connection_failure_is_reported(monkeypatch):
    target = {
        "id": "tab-1",
        "type": "page",
        "title": "Fixture",
        "url": "http://localhost:8000/",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/tab-1",
    }
    monkeypatch.setattr(cdp.asyncio, "to_thread", lambda function, *args: _return_targets(target))

    async def fail_connect(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(cdp, "connect", fail_connect)
    with pytest.raises(BrowserConnectionError, match="Could not connect"):
        await BrowserSession().connect("http://127.0.0.1:9222", "tab-1")


async def _return_targets(target):
    return [target]


@pytest.mark.asyncio
async def test_local_cdp_session_enables_domains_collects_events_and_closes(monkeypatch):
    commands = []

    async def fake_chrome(websocket):
        async for raw_message in websocket:
            message = json.loads(raw_message)
            commands.append(message["method"])
            await websocket.send(json.dumps({"id": message["id"], "result": {}}))
            if message["method"] == "Network.enable":
                await websocket.send(
                    json.dumps(
                        {
                            "method": "Runtime.consoleAPICalled",
                            "params": {"type": "error", "args": [{"value": "fixture failure"}]},
                        }
                    )
                )

    server = await serve(fake_chrome, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    target = {
        "id": "tab-1",
        "type": "page",
        "title": "Fixture",
        "url": "http://localhost:8000/",
        "webSocketDebuggerUrl": f"ws://127.0.0.1:{port}/devtools/page/tab-1",
    }
    monkeypatch.setattr(cdp, "discover_targets", lambda endpoint: [target])
    session = BrowserSession()
    try:
        status = await session.connect(f"http://127.0.0.1:{port}", "tab-1")
        assert status["connected"] is True
        assert commands == [
            "Runtime.enable", "Network.enable", "Page.enable", "Performance.enable",
            "Page.addScriptToEvaluateOnNewDocument", "Runtime.evaluate", "Tracing.start",
        ]
        assert session.diagnostics("console")[0].explanation == "fixture failure"
        await session.disconnect()
        assert session.status()["connected"] is False
    finally:
        await session.disconnect()
        server.close()
        await server.wait_closed()
