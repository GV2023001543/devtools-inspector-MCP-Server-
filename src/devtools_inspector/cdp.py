from __future__ import annotations

import asyncio
import ipaddress
import json
import urllib.error
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlsplit

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from .models import Issue, SourceLocation, build_issue
from .redaction import redact_text, redact_url


_PERFORMANCE_MARKER = "__DEVTOOLS_INSPECTOR_PERFORMANCE__:"
_PERFORMANCE_OBSERVER_SOURCE = r"""
(() => {
  const marker = "__DEVTOOLS_INSPECTOR_PERFORMANCE__:";
  const installedKey = "__devtoolsInspectorPerformanceObserverInstalled";
  if (globalThis[installedKey]) return;
  globalThis[installedKey] = true;
  const supports = (type) => Array.isArray(PerformanceObserver?.supportedEntryTypes)
    && PerformanceObserver.supportedEntryTypes.includes(type);
  const emit = (entry) => console.debug(marker + JSON.stringify(entry));
  const longtaskSupported = typeof PerformanceObserver !== "undefined" && supports("longtask");
  const eventSupported = typeof PerformanceObserver !== "undefined" && supports("event");
  emit({kind: "support", longtask: longtaskSupported, event: eventSupported});
  const attribution = (items) => Array.from(items || [], (item) => ({
    containerId: item.containerId || "",
    containerName: item.containerName || "",
    containerSrc: item.containerSrc || "",
  }));
  if (longtaskSupported) {
    try {
      new PerformanceObserver((list) => list.getEntries().forEach((entry) => emit({
        kind: "longtask", url: location.href, startTime: entry.startTime,
        duration: entry.duration, name: entry.name || "unknown",
        attribution: attribution(entry.attribution),
      }))).observe({type: "longtask", buffered: true});
    } catch (_) { emit({kind: "support", longtask: false, event: eventSupported}); }
  }
  if (eventSupported) {
    try {
      new PerformanceObserver((list) => list.getEntries().forEach((entry) => emit({
        kind: "action", url: location.href, name: entry.name || "unknown",
        startTime: entry.startTime, processingStart: entry.processingStart,
        processingEnd: entry.processingEnd, duration: entry.duration,
      }))).observe({type: "event", buffered: true, durationThreshold: 16});
    } catch (_) { /* Event Timing is optional evidence only. */ }
  }
})()
"""


class BrowserConnectionError(RuntimeError):
    """The local Chrome debugging endpoint could not be used."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _validate_local_http_endpoint(endpoint: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname
        port = parsed.port or 80
        is_local = host == "localhost" or (host is not None and ipaddress.ip_address(host).is_loopback)
    except (ValueError, TypeError):
        raise BrowserConnectionError("Use a valid local Chrome endpoint such as http://127.0.0.1:9222.") from None
    if parsed.scheme != "http" or not is_local or parsed.username or parsed.password or parsed.path not in ("", "/"):
        raise BrowserConnectionError("Only an unauthenticated localhost HTTP debugging endpoint is allowed.")
    return host or "", port


def discover_targets(endpoint: str, timeout: float = 3.0) -> list[dict[str, Any]]:
    _validate_local_http_endpoint(endpoint)
    url = endpoint.rstrip("/") + "/json/list"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        opener = urllib.request.build_opener(_NoRedirectHandler)
        with opener.open(request, timeout=timeout) as response:
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            raise BrowserConnectionError("Chrome returned an oversized target list.")
        targets = json.loads(payload)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise BrowserConnectionError(f"Could not read Chrome targets at {endpoint}: {error}") from error
    if not isinstance(targets, list):
        raise BrowserConnectionError("Chrome returned an invalid target list.")
    return [target for target in targets if isinstance(target, dict) and target.get("type") == "page"]


def _validate_websocket_target(ws_url: str, endpoint: str) -> None:
    _, endpoint_port = _validate_local_http_endpoint(endpoint)
    try:
        parsed = urlsplit(ws_url)
        ws_host = parsed.hostname
        ws_port = parsed.port or 80
        ws_local = ws_host == "localhost" or (ws_host is not None and ipaddress.ip_address(ws_host).is_loopback)
    except (ValueError, TypeError):
        raise BrowserConnectionError("Chrome provided an invalid page WebSocket URL.") from None
    if parsed.scheme != "ws" or not ws_local or ws_port != endpoint_port or not parsed.path.startswith("/devtools/page/"):
        raise BrowserConnectionError("Chrome provided a page WebSocket outside the selected local debugging endpoint.")


class CDPClient:
    def __init__(self, ws_url: str, on_event: Callable[[str, dict[str, Any]], None]):
        self._ws_url = ws_url
        self._on_event = on_event
        self._socket: ClientConnection | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._next_id = 0
        self._trace_events: list[dict[str, Any]] = []
        self._tracing_complete = asyncio.Event()
        self._tracing_active = False

    @property
    def connected(self) -> bool:
        return self._socket is not None and self._reader_task is not None and not self._reader_task.done()

    async def open(self) -> None:
        try:
            self._socket = await connect(self._ws_url, open_timeout=5, close_timeout=2, max_size=1_000_000)
        except (OSError, TimeoutError, ConnectionClosed) as error:
            raise BrowserConnectionError(f"Could not connect to the selected Chrome tab: {error}") from error
        self._reader_task = asyncio.create_task(self._read_messages())
        try:
            await self.command("Runtime.enable")
            await self.command("Network.enable", {"maxTotalBufferSize": 1_000_000})
            await self.command("Page.enable")
            try:
                await self.command("Performance.enable")
            except BrowserConnectionError:
                # The observer below is the long-task source. Some CDP versions do not expose Performance.
                pass
        except Exception:
            await self.close()
            raise

    async def command(self, method: str, params: dict[str, Any] | None = None, timeout: float = 5.0) -> dict[str, Any]:
        if not self.connected or self._socket is None:
            raise BrowserConnectionError("The selected browser tab is disconnected.")
        self._next_id += 1
        command_id = self._next_id
        future = asyncio.get_running_loop().create_future()
        self._pending[command_id] = future
        try:
            await self._socket.send(json.dumps({"id": command_id, "method": method, "params": params or {}}))
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError as error:
            raise BrowserConnectionError(f"Chrome did not answer {method} within {timeout:g}s.") from error
        finally:
            self._pending.pop(command_id, None)

    async def install_performance_observer(self) -> bool:
        """Install a document-start long-task observer and attach it to the current page."""
        try:
            await self.command("Page.addScriptToEvaluateOnNewDocument", {"source": _PERFORMANCE_OBSERVER_SOURCE})
            await self.command(
                "Runtime.evaluate",
                {"expression": _PERFORMANCE_OBSERVER_SOURCE, "returnByValue": True},
            )
        except BrowserConnectionError:
            return False
        return True

    async def start_performance_tracing(self) -> bool:
        """Begin a bounded CDP tracing fallback for future main-thread tasks."""
        if self._tracing_active:
            return True
        self._trace_events.clear()
        self._tracing_complete.clear()
        try:
            await self.command(
                "Tracing.start",
                {
                    "categories": "devtools.timeline,disabled-by-default-devtools.timeline,toplevel",
                    "transferMode": "ReportEvents",
                },
            )
        except BrowserConnectionError:
            return False
        self._tracing_active = True
        return True

    async def stop_performance_tracing(self) -> list[dict[str, Any]]:
        """Stop tracing and return only events received for this collection window."""
        if not self._tracing_active:
            return []
        try:
            await self.command("Tracing.end")
            await asyncio.wait_for(self._tracing_complete.wait(), timeout=5)
        except (BrowserConnectionError, TimeoutError):
            return []
        finally:
            self._tracing_active = False
        events = self._trace_events
        self._trace_events = []
        return events

    async def close(self) -> None:
        socket = self._socket
        self._socket = None
        if socket is not None:
            await socket.close()
        task = self._reader_task
        self._reader_task = None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for future in self._pending.values():
            if not future.done():
                future.set_exception(BrowserConnectionError("The browser connection closed."))
        self._pending.clear()

    async def _read_messages(self) -> None:
        assert self._socket is not None
        try:
            async for raw_message in self._socket:
                message = json.loads(raw_message)
                if "id" in message:
                    future = self._pending.get(message["id"])
                    if future is not None and not future.done():
                        if "error" in message:
                            future.set_exception(BrowserConnectionError(message["error"].get("message", "CDP command failed.")))
                        else:
                            future.set_result(message.get("result", {}))
                elif isinstance(message.get("method"), str):
                    if message["method"] == "Tracing.dataCollected":
                        values = message.get("params", {}).get("value", [])
                        if isinstance(values, list):
                            self._trace_events.extend(item for item in values if isinstance(item, dict))
                    elif message["method"] == "Tracing.tracingComplete":
                        self._tracing_complete.set()
                    try:
                        self._on_event(message["method"], message.get("params", {}))
                    except Exception:
                        continue
        except (ConnectionClosed, OSError, json.JSONDecodeError):
            pass
        finally:
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(BrowserConnectionError("The browser debugging connection was lost."))


@dataclass
class _Request:
    url: str
    method: str
    resource_type: str | None
    start_time: float
    initiator: str | None


class DiagnosticCollector:
    def __init__(self, target_id: str, max_issues: int = 1000):
        self.target_id = target_id
        self.monitoring = True
        self._issues: OrderedDict[str, Issue] = OrderedDict()
        self._requests: dict[str, _Request] = {}
        self._performance_actions: list[dict[str, Any]] = []
        self.performance_observer_supported: bool | None = None
        self._max_issues = max_issues

    @property
    def issues(self) -> list[Issue]:
        return list(self._issues.values())

    def handle_event(self, method: str, params: dict[str, Any]) -> None:
        if not self.monitoring:
            return
        if method == "Runtime.consoleAPICalled":
            self._console(params)
        elif method == "Runtime.exceptionThrown":
            self._exception(params)
        elif method == "Network.requestWillBeSent":
            self._request(params)
        elif method == "Network.responseReceived":
            self._response(params)
        elif method == "Network.loadingFailed":
            self._loading_failed(params)

    def _add(self, issue: Issue) -> None:
        self._issues.setdefault(issue.issue_id, issue)
        self._issues.move_to_end(issue.issue_id)
        while len(self._issues) > self._max_issues:
            self._issues.popitem(last=False)

    @staticmethod
    def _location(stack: dict[str, Any] | None) -> SourceLocation | None:
        frames = (stack or {}).get("callFrames", [])
        if not frames:
            return None
        frame = frames[0]
        url = frame.get("url")
        if not url:
            return None
        return SourceLocation(
            url=redact_url(url),
            line=frame.get("lineNumber", 0) + 1,
            column=frame.get("columnNumber", 0) + 1,
            function=redact_text(frame.get("functionName") or "", 120) or None,
        )

    def _console(self, params: dict[str, Any]) -> None:
        level = params.get("type", "log")
        raw_text = " ".join(
            str(item.get("description", item.get("value", "")))
            for item in params.get("args", [])
            if isinstance(item, dict)
        )
        if level == "debug" and raw_text.startswith(_PERFORMANCE_MARKER):
            self._performance_message(raw_text.removeprefix(_PERFORMANCE_MARKER))
            return
        if level not in ("error", "warning"):
            return
        text = redact_text(raw_text or "Console reported an empty message.")
        location = self._location(params.get("stackTrace"))
        self._add(
            build_issue(
                category="console",
                severity="error" if level == "error" else "warning",
                confidence="confirmed",
                title=f"Console {level}: {text[:160]}",
                explanation=text,
                url=location.url if location else None,
                target_id=self.target_id,
                source_location=location,
                evidence={"console_type": level},
            )
        )

    def add_trace_events(self, events: list[dict[str, Any]], page_url: str | None) -> None:
        """Add CDP trace fallback findings after a trace has been explicitly collected."""
        trace_actions: list[dict[str, Any]] = []
        for event in events:
            if event.get("name") != "EventDispatch" or event.get("ph") != "X":
                continue
            start = self._number(event.get("ts"))
            duration = self._number(event.get("dur"))
            if start is None or duration is None:
                continue
            args = event.get("args")
            data = args.get("data") if isinstance(args, dict) else None
            event_type = data.get("type", "unknown") if isinstance(data, dict) else "unknown"
            trace_actions.append({"name": redact_text(str(event_type), 80), "start": start, "end": start + duration})
        for event in events:
            if event.get("name") != "RunTask" or event.get("ph") != "X":
                continue
            start = self._number(event.get("ts"))
            duration_us = self._number(event.get("dur"))
            if start is None or duration_us is None or duration_us < 50_000:
                continue
            end = start + duration_us
            actions = [action for action in trace_actions if action["start"] <= end and action["end"] >= start]
            duration_ms = duration_us / 1000
            evidence: dict[str, Any] = {
                "source": "CDP Tracing fallback",
                "trace_timestamp_us": start,
                "duration_ms": duration_ms,
                "trace_event": "RunTask",
            }
            if actions:
                evidence["action_association"] = "timing_correlated"
                evidence["actions"] = actions
            self._add(
                build_issue(
                    category="performance",
                    severity="warning",
                    confidence="confirmed",
                    title=f"Long main-thread task: {duration_ms:.1f} ms at trace {start:.0f} us",
                    explanation=f"CDP tracing observed a main-thread RunTask lasting {duration_ms:.1f} ms.",
                    url=page_url,
                    target_id=self.target_id,
                    evidence=evidence,
                )
            )

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None

    def _performance_message(self, payload: str) -> None:
        try:
            message = json.loads(payload)
        except json.JSONDecodeError:
            return
        if not isinstance(message, dict):
            return
        kind = message.get("kind")
        if kind == "support":
            supported = message.get("longtask")
            self.performance_observer_supported = supported if isinstance(supported, bool) else False
            return
        if kind == "action":
            start = self._number(message.get("processingStart"))
            end = self._number(message.get("processingEnd"))
            if start is None or end is None or end < start:
                return
            self._performance_actions.append({"name": redact_text(str(message.get("name") or "unknown"), 80), "start": start, "end": end})
            self._performance_actions = self._performance_actions[-100:]
            return
        if kind != "longtask":
            return
        start = self._number(message.get("startTime"))
        duration = self._number(message.get("duration"))
        if start is None or duration is None or duration < 50:
            return
        end = start + duration
        actions = [action for action in self._performance_actions if action["start"] <= end and action["end"] >= start]
        url = redact_url(str(message.get("url") or "")) or None
        attribution = message.get("attribution")
        evidence: dict[str, Any] = {
            "source": "PerformanceObserver.longtask",
            "start_time_ms": start,
            "duration_ms": duration,
            "attribution_name": redact_text(str(message.get("name") or "unknown"), 120),
        }
        if isinstance(attribution, list):
            evidence["attribution"] = [
                {key: redact_text(str(item.get(key) or ""), 240) for key in ("containerId", "containerName", "containerSrc")}
                for item in attribution[:10]
                if isinstance(item, dict)
            ]
        if actions:
            evidence["action_association"] = "timing_correlated"
            evidence["actions"] = actions
        self._add(
            build_issue(
                category="performance",
                severity="warning",
                confidence="confirmed",
                title=f"Long main-thread task: {duration:.1f} ms at {start:.1f} ms",
                explanation=f"The page main thread was busy for {duration:.1f} ms.",
                url=url,
                target_id=self.target_id,
                evidence=evidence,
            )
        )

    def _exception(self, params: dict[str, Any]) -> None:
        details = params.get("exceptionDetails", {})
        exception = details.get("exception", {})
        raw_text = exception.get("description") or details.get("text") or "Uncaught JavaScript exception"
        text = redact_text(str(raw_text))
        location = self._location(details.get("stackTrace"))
        url = redact_url(details["url"]) if details.get("url") else (location.url if location else None)
        self._add(
            build_issue(
                category="runtime",
                severity="error",
                confidence="confirmed",
                title=f"Uncaught exception: {text[:160]}",
                explanation=text,
                url=url,
                target_id=self.target_id,
                source_location=location,
                evidence={"exception_text": text[:1000]},
            )
        )

    def _request(self, params: dict[str, Any]) -> None:
        request = params.get("request", {})
        request_id = params.get("requestId")
        if not request_id:
            return
        initiator = params.get("initiator", {}).get("type")
        self._requests[request_id] = _Request(
            url=redact_url(request.get("url", "")),
            method=request.get("method", "GET"),
            resource_type=params.get("type"),
            start_time=float(params.get("timestamp", 0)),
            initiator=initiator,
        )
        if len(self._requests) > 1000:
            self._requests.pop(next(iter(self._requests)))

    def _response(self, params: dict[str, Any]) -> None:
        response = params.get("response", {})
        status = int(response.get("status", 0))
        if status < 400:
            return
        request = self._requests.get(params.get("requestId"), _Request(redact_url(response.get("url", "")), "GET", None, 0, None))
        self._add(
            build_issue(
                category="network",
                severity="error" if status >= 500 else "warning",
                confidence="confirmed",
                title=f"HTTP {status} response",
                explanation=f"{request.method} {request.url} returned HTTP {status}.",
                url=request.url,
                target_id=self.target_id,
                evidence={
                    "status": status,
                    "resource_type": params.get("type") or request.resource_type,
                    "initiator": request.initiator,
                },
            )
        )

    def _loading_failed(self, params: dict[str, Any]) -> None:
        request = self._requests.get(params.get("requestId"))
        if request is None:
            return
        canceled = bool(params.get("canceled"))
        reason = redact_text(params.get("errorText", "Network request failed"), 240)
        self._add(
            build_issue(
                category="network",
                severity="warning" if canceled else "error",
                confidence="correlated" if canceled else "confirmed",
                title=f"Request {'aborted' if canceled else 'failed'}: {request.method} {request.url}",
                explanation=f"{request.method} {request.url} failed: {reason}.",
                url=request.url,
                target_id=self.target_id,
                evidence={"error_text": reason, "resource_type": request.resource_type, "initiator": request.initiator},
            )
        )


class BrowserSession:
    def __init__(self):
        self.endpoint: str | None = None
        self.target: dict[str, Any] | None = None
        self.collector: DiagnosticCollector | None = None
        self.client: CDPClient | None = None
        self._lock = asyncio.Lock()

    async def list_targets(self, endpoint: str) -> list[dict[str, str]]:
        targets = await asyncio.to_thread(discover_targets, endpoint)
        return [
            {"target_id": target.get("id", ""), "title": target.get("title", ""), "url": redact_url(target.get("url", ""))}
            for target in targets
        ]

    async def connect(self, endpoint: str, target_id: str) -> dict[str, Any]:
        async with self._lock:
            await self.disconnect()
            targets = await asyncio.to_thread(discover_targets, endpoint)
            target = next((item for item in targets if item.get("id") == target_id), None)
            if target is None:
                raise BrowserConnectionError(f"Page target {target_id!r} is unavailable. List targets and select an open page.")
            ws_url = target.get("webSocketDebuggerUrl")
            if not isinstance(ws_url, str):
                raise BrowserConnectionError("The selected page does not expose a CDP WebSocket URL.")
            _validate_websocket_target(ws_url, endpoint)
            collector = DiagnosticCollector(target_id)
            client = CDPClient(ws_url, collector.handle_event)
            await client.open()
            await client.install_performance_observer()
            await client.start_performance_tracing()
            self.endpoint = endpoint
            self.target = {"target_id": target_id, "title": target.get("title", ""), "url": redact_url(target.get("url", ""))}
            self.collector = collector
            self.client = client
            return self.status()

    async def disconnect(self) -> dict[str, Any]:
        client = self.client
        self.client = None
        if client is not None:
            await client.close()
        self.endpoint = None
        self.target = None
        self.collector = None
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "connected": bool(self.client and self.client.connected),
            "endpoint": self.endpoint,
            "target": self.target,
            "monitoring": bool(self.collector and self.collector.monitoring),
        }

    def diagnostics(self, category: str | None = None) -> list[Issue]:
        if self.collector is None:
            raise BrowserConnectionError("Connect to a browser target before requesting diagnostics.")
        issues = self.collector.issues
        return [issue for issue in issues if category is None or issue.category == category]

    async def performance_diagnostics(self) -> list[Issue]:
        if self.collector is None or self.client is None:
            raise BrowserConnectionError("Connect to a browser target before requesting performance diagnostics.")
        events = await self.client.stop_performance_tracing()
        page_url = self.target.get("url") if self.target else None
        self.collector.add_trace_events(events, page_url)
        await self.client.start_performance_tracing()
        return self.diagnostics("performance")
