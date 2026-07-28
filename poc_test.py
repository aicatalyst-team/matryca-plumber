#!/usr/bin/env python3
"""PoC validation tests for matryca-plumber deployment on OpenShift.

Tests the Sovereign UI FastAPI server endpoints via the Kubernetes service URL.
Uses only Python stdlib (urllib.request) for portability.
"""

import json
import sys
import time
import urllib.error
import urllib.request


def make_request(url: str, timeout: int = 15,
                 extra_headers: dict[str, str] | None = None) -> tuple[int, str, dict[str, str]]:
    """Make an HTTP GET request and return (status_code, body, headers)."""
    req = urllib.request.Request(url)
    if extra_headers:
        for key, val in extra_headers.items():
            req.add_header(key, val)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            headers = dict(resp.headers)
            return resp.status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, dict(e.headers) if e.headers else {}
    except urllib.error.URLError as e:
        return 0, str(e.reason), {}
    except Exception as e:
        return 0, str(e), {}


def retry_request(url: str, max_retries: int = 5, delay: float = 3.0,
                  timeout: int = 15,
                  extra_headers: dict[str, str] | None = None) -> tuple[int, str, dict[str, str]]:
    """Retry a request with exponential backoff."""
    for attempt in range(max_retries):
        status, body, headers = make_request(url, timeout, extra_headers)
        if status > 0:
            return status, body, headers
        if attempt < max_retries - 1:
            wait = delay * (2 ** attempt)
            print(f"  Retry {attempt + 1}/{max_retries} after {wait:.1f}s...",
                  file=sys.stderr)
            time.sleep(wait)
    return status, body, headers


def run_tests(base_url: str) -> list[dict]:
    """Run all PoC test scenarios and return results."""
    results = []

    # Scenario 1: Health Check
    print("Testing: Health Check (/api/health)...", file=sys.stderr)
    start = time.time()
    status, body, headers = retry_request(f"{base_url}/api/health")
    duration = time.time() - start
    passed = status == 200
    try:
        data = json.loads(body) if passed else None
    except (json.JSONDecodeError, TypeError):
        data = None
    results.append({
        "scenario_name": "Health Check",
        "status": "pass" if passed else "fail",
        "output": f"HTTP {status}" + (f" - {json.dumps(data)}" if data else f" - {body[:200]}"),
        "error_message": None if passed else f"Expected 200, got {status}",
        "duration_seconds": round(duration, 2)
    })

    # Scenario 2: Homepage / Dashboard
    print("Testing: Homepage Dashboard (/)...", file=sys.stderr)
    start = time.time()
    status, body, headers = retry_request(f"{base_url}/")
    duration = time.time() - start
    is_html = "text/html" in headers.get("content-type", "")
    has_content = len(body) > 100
    passed = status == 200 and (is_html or has_content)
    results.append({
        "scenario_name": "Homepage Dashboard",
        "status": "pass" if passed else "fail",
        "output": f"HTTP {status}, content-type={headers.get('content-type', 'unknown')}, body_length={len(body)}",
        "error_message": None if passed else f"Expected 200 with HTML, got {status}",
        "duration_seconds": round(duration, 2)
    })

    # Scenario 3: API Preflight (requires x-matryca-token auth)
    print("Testing: API Preflight (/api/preflight)...", file=sys.stderr)
    auth_headers = {"x-matryca-token": "poc-demo-token-2026"}
    start = time.time()
    status, body, headers = retry_request(
        f"{base_url}/api/preflight", extra_headers=auth_headers
    )
    duration = time.time() - start
    passed = status == 200
    try:
        data = json.loads(body) if body else None
    except (json.JSONDecodeError, TypeError):
        data = None
    results.append({
        "scenario_name": "API Preflight",
        "status": "pass" if passed else "fail",
        "output": f"HTTP {status}" + (f" - keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}" if data else f" - {body[:200]}"),
        "error_message": None if passed else f"Expected 200, got {status}",
        "duration_seconds": round(duration, 2)
    })

    # Scenario 4: API Config (requires auth, tests authenticated API access)
    print("Testing: API Config (/api/config)...", file=sys.stderr)
    start = time.time()
    status, body, headers = retry_request(
        f"{base_url}/api/config", extra_headers=auth_headers
    )
    duration = time.time() - start
    passed = status == 200
    try:
        data = json.loads(body) if body else None
    except (json.JSONDecodeError, TypeError):
        data = None
    results.append({
        "scenario_name": "API Config",
        "status": "pass" if passed else "fail",
        "output": f"HTTP {status}" + (f" - keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}" if data else f" - {body[:200]}"),
        "error_message": None if passed else f"Expected 200 with config data, got {status}",
        "duration_seconds": round(duration, 2)
    })

    return results


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python poc_test.py <service-url>", file=sys.stderr)
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    print(f"Running PoC tests against: {base_url}", file=sys.stderr)

    results = run_tests(base_url)

    # Output structured JSON
    output = {
        "project": "matryca-plumber",
        "base_url": base_url,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "pass"),
            "failed": sum(1 for r in results if r["status"] == "fail"),
        }
    }

    print(json.dumps(output, indent=2))

    # Exit with non-zero if any test failed
    if output["summary"]["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
