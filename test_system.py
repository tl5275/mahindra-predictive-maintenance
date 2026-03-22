#!/usr/bin/env python3
"""Smoke-test the deployed REST and WebSocket telemetry pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import SplitResult, urlsplit, urlunsplit

import requests
import websockets


DEFAULT_BASE_URL = "https://mahindra-predictive-maintenance-1.onrender.com"
DEFAULT_REST_TIMEOUT_SECONDS = 10
DEFAULT_WEBSOCKET_TIMEOUT_SECONDS = 10
DEFAULT_POLL_INTERVAL_SECONDS = 2
DEFAULT_POLL_ATTEMPTS = 3
DEFAULT_RETRIES = 2


class CheckStatus:
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    label: str
    status: str
    message: str
    details: list[str] = field(default_factory=list)


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def _supports_unicode_output() -> bool:
    encoding = (sys.stdout.encoding or "").lower()
    return "utf" in encoding


def _colorize(text: str, status: str) -> str:
    if not _supports_color():
        return text

    color_map = {
        CheckStatus.PASS: "\033[92m",
        CheckStatus.WARN: "\033[93m",
        CheckStatus.FAIL: "\033[91m",
    }
    reset = "\033[0m"
    return f"{color_map.get(status, '')}{text}{reset}"


def _status_prefix(status: str) -> str:
    if _supports_unicode_output():
        icon_map = {
            CheckStatus.PASS: "✔",
            CheckStatus.WARN: "⚠",
            CheckStatus.FAIL: "❌",
        }
    else:
        icon_map = {
            CheckStatus.PASS: "[PASS]",
            CheckStatus.WARN: "[WARN]",
            CheckStatus.FAIL: "[FAIL]",
        }
    return _colorize(icon_map.get(status, "-"), status)


def print_result(result: CheckResult) -> None:
    print(f"{_status_prefix(result.status)} {result.label} {result.message}")
    for detail in result.details:
        print(f"   - {detail}")


def normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {value!r}")
    return normalized


def build_url(base_url: str, path: str) -> str:
    parsed = urlsplit(base_url)
    path_prefix = parsed.path.rstrip("/")
    next_path = path if path.startswith("/") else f"/{path}"
    return urlunsplit(
        SplitResult(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            path=f"{path_prefix}{next_path}",
            query="",
            fragment="",
        )
    )


def build_websocket_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunsplit(
        SplitResult(
            scheme=ws_scheme,
            netloc=parsed.netloc,
            path=f"{parsed.path.rstrip('/')}/ws/fleet",
            query="",
            fragment="",
        )
    )


def request_json(
    session: requests.Session,
    url: str,
    timeout_seconds: int,
    retries: int,
) -> tuple[int, Any]:
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout_seconds)
            if response.status_code != 200:
                raise requests.HTTPError(
                    f"Expected HTTP 200 from {url}, received {response.status_code}",
                    response=response,
                )
            return response.status_code, response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(attempt)

    if last_error is None:
        raise RuntimeError(f"Request to {url} failed without an error.")
    raise last_error


def validate_fleet_response(payload: Any) -> tuple[CheckResult, dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("/fleet did not return a JSON object.")
    if "vehicles" not in payload:
        raise ValueError("/fleet response is missing the 'vehicles' key.")

    vehicles = payload.get("vehicles")
    vehicle_count = len(vehicles) if isinstance(vehicles, list) else 0
    details = [f"vehicles={vehicle_count}"]
    if vehicle_count == 0:
        details.append("Fleet is currently empty.")

    return (
        CheckResult(
            label="GET /fleet",
            status=CheckStatus.PASS,
            message="returned HTTP 200 with valid JSON.",
            details=details,
        ),
        payload,
    )


def validate_system_status_response(payload: Any) -> CheckResult:
    if not isinstance(payload, dict):
        raise ValueError("/system-status did not return a JSON object.")

    details = [f"keys={', '.join(list(payload.keys())[:5])}"]
    return CheckResult(
        label="GET /system-status",
        status=CheckStatus.PASS,
        message="returned HTTP 200 with valid JSON.",
        details=details,
    )


def poll_fleet_for_data(
    session: requests.Session,
    base_url: str,
    timeout_seconds: int,
    retries: int,
    interval_seconds: int,
    attempts: int,
) -> CheckResult:
    fleet_url = build_url(base_url, "/fleet")
    observations: list[str] = []
    timestamps: set[str] = set()

    for poll_index in range(1, attempts + 1):
        _, payload = request_json(session, fleet_url, timeout_seconds, retries)
        vehicles = payload.get("vehicles", []) if isinstance(payload, dict) else []
        vehicle_count = len(vehicles) if isinstance(vehicles, list) else 0
        timestamp = payload.get("timestamp") if isinstance(payload, dict) else None
        if isinstance(timestamp, str) and timestamp:
            timestamps.add(timestamp)

        observations.append(
            f"poll {poll_index}: vehicles={vehicle_count}, timestamp={timestamp or 'n/a'}"
        )

        if vehicle_count > 0:
            return CheckResult(
                label="Data Streaming Active",
                status=CheckStatus.PASS,
                message=f"fleet returned {vehicle_count} vehicles during polling.",
                details=observations,
            )

        if poll_index < attempts:
            time.sleep(interval_seconds)

    if len(timestamps) > 1:
        observations.append("Fleet timestamp changed across polls, but no vehicles were present.")

    return CheckResult(
        label="Data Streaming Active",
        status=CheckStatus.WARN,
        message="no vehicles were returned during polling.",
        details=observations,
    )


def parse_websocket_message(raw_message: Any) -> dict[str, Any]:
    if not isinstance(raw_message, str):
        raise ValueError("WebSocket payload is not a text frame.")

    payload = json.loads(raw_message)
    if not isinstance(payload, dict):
        raise ValueError("WebSocket payload is not a JSON object.")
    if "vehicles" not in payload and "type" not in payload:
        raise ValueError("WebSocket message is missing both 'vehicles' and 'type'.")
    return payload


async def test_websocket_and_data_flow(
    session: requests.Session,
    base_url: str,
    websocket_url: str,
    websocket_timeout_seconds: int,
    rest_timeout_seconds: int,
    retries: int,
    poll_interval_seconds: int,
    poll_attempts: int,
) -> tuple[CheckResult, CheckResult]:
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            async with websockets.connect(
                websocket_url,
                open_timeout=websocket_timeout_seconds,
                close_timeout=5,
                ping_interval=20,
                ping_timeout=10,
                max_size=2_000_000,
            ) as websocket:
                raw_message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=websocket_timeout_seconds,
                )
                payload = parse_websocket_message(raw_message)
                vehicles = payload.get("vehicles", [])
                vehicle_count = len(vehicles) if isinstance(vehicles, list) else 0

                websocket_result = CheckResult(
                    label="WebSocket Connected",
                    status=CheckStatus.PASS,
                    message="connection opened and a message was received.",
                    details=[
                        f"url={websocket_url}",
                        f"type={payload.get('type', 'n/a')}",
                        f"vehicles={vehicle_count}",
                    ],
                )

                flow_result = await asyncio.to_thread(
                    poll_fleet_for_data,
                    session,
                    base_url,
                    rest_timeout_seconds,
                    retries,
                    poll_interval_seconds,
                    poll_attempts,
                )
                return websocket_result, flow_result
        except Exception as error:
            last_error = error
            if attempt < retries:
                await asyncio.sleep(attempt)

    if last_error is None:
        raise RuntimeError("WebSocket test failed without an error.")
    raise last_error


def aggregate_api_result(results: list[CheckResult]) -> CheckResult:
    if all(result.status == CheckStatus.PASS for result in results):
        return CheckResult(
            label="Backend API OK",
            status=CheckStatus.PASS,
            message="REST endpoints responded successfully.",
        )

    return CheckResult(
        label="Backend API OK",
        status=CheckStatus.FAIL,
        message="one or more REST endpoint checks failed.",
    )


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "mahindra-system-test/1.0",
        }
    )
    return session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Mahindra backend REST and WebSocket pipeline.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("BACKEND_URL", DEFAULT_BASE_URL),
        help="Backend base URL to test.",
    )
    parser.add_argument(
        "--rest-timeout",
        type=int,
        default=DEFAULT_REST_TIMEOUT_SECONDS,
        help="Timeout in seconds for REST requests.",
    )
    parser.add_argument(
        "--ws-timeout",
        type=int,
        default=DEFAULT_WEBSOCKET_TIMEOUT_SECONDS,
        help="Timeout in seconds for the first WebSocket message.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds between /fleet polling attempts after the WebSocket connects.",
    )
    parser.add_argument(
        "--poll-attempts",
        type=int,
        default=DEFAULT_POLL_ATTEMPTS,
        help="Number of /fleet polls to perform during the data-flow check.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="How many times to retry failed network operations.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = normalize_base_url(args.base_url)
    websocket_url = build_websocket_url(base_url)
    print(f"Testing backend: {base_url}")

    session = build_session()
    results: list[CheckResult] = []

    try:
        fleet_status_code, fleet_payload = request_json(
            session,
            build_url(base_url, "/fleet"),
            args.rest_timeout,
            args.retries,
        )
        if fleet_status_code != 200:
            raise ValueError(f"/fleet returned unexpected status code: {fleet_status_code}")
        fleet_result, _ = validate_fleet_response(fleet_payload)
        results.append(fleet_result)
    except Exception as error:
        results.append(
            CheckResult(
                label="GET /fleet",
                status=CheckStatus.FAIL,
                message=str(error),
            )
        )

    try:
        status_code, status_payload = request_json(
            session,
            build_url(base_url, "/system-status"),
            args.rest_timeout,
            args.retries,
        )
        if status_code != 200:
            raise ValueError(f"/system-status returned unexpected status code: {status_code}")
        results.append(validate_system_status_response(status_payload))
    except Exception as error:
        results.append(
            CheckResult(
                label="GET /system-status",
                status=CheckStatus.FAIL,
                message=str(error),
            )
        )

    api_results = [result for result in results if result.label.startswith("GET /")]
    results.insert(0, aggregate_api_result(api_results))

    try:
        websocket_result, flow_result = asyncio.run(
            test_websocket_and_data_flow(
                session,
                base_url,
                websocket_url,
                args.ws_timeout,
                args.rest_timeout,
                args.retries,
                args.poll_interval,
                args.poll_attempts,
            )
        )
        results.append(websocket_result)
        results.append(flow_result)
    except Exception as error:
        results.append(
            CheckResult(
                label="WebSocket Connected",
                status=CheckStatus.FAIL,
                message=f"connection or message validation failed: {error}",
                details=[f"url={websocket_url}"],
            )
        )
        results.append(
            CheckResult(
                label="Data Streaming Active",
                status=CheckStatus.FAIL,
                message="skipped because the WebSocket test failed.",
            )
        )
    finally:
        session.close()

    print()
    for result in results:
        print_result(result)

    failed = any(result.status == CheckStatus.FAIL for result in results)
    warned = any(result.status == CheckStatus.WARN for result in results)

    print()
    if failed:
        print(_colorize("Overall result: FAIL", CheckStatus.FAIL))
        return 1
    if warned:
        print(_colorize("Overall result: WARN", CheckStatus.WARN))
        return 0

    print(_colorize("Overall result: PASS", CheckStatus.PASS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
