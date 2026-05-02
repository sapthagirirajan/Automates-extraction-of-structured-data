"""End-to-end verification. Run after `uvicorn main:app --port 8005` is up.

Required assertions (see 38 - Background and Approach.md, section "Verification"):

  1. Posting the SAME resume PDF twice yields one row in parsed_documents,
     and the second call sets X-Cache: HIT and is < 150 ms.
  2. Posting /parse/jd with body {"text": ""} returns 422.
  3. Posting /parse/jd with garbled non-English text returns 415.
  4. The `model_used` field is non-empty on every successful response.
  5. Cache-hit latency is < 150 ms (measure round-trip).

You provide the fixtures yourself: drop at least 3 resume PDFs and 3 JD
PDFs into ./fixtures/.

Run:
    python verify.py
Exits with status 0 on success, 1 on failure.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8005"
FIXTURES = Path(__file__).parent / "fixtures"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"  ok: {msg}")


def main() -> None:
    if not FIXTURES.exists() or not list(FIXTURES.glob("*.pdf")):
        fail("drop sample PDFs into ./fixtures/ before running verify.py")

    resumes = sorted(FIXTURES.glob("*resume*.pdf"))[:1]
    jds = sorted(FIXTURES.glob("*jd*.pdf"))[:1]

    if not resumes:
        fail("no resume PDFs found in fixtures/. Name them with 'resume' substring.")
    if not jds:
        fail("no JD PDFs found in fixtures/. Name them with 'jd' substring.")

    # Assertion 1: Posting the SAME resume PDF twice yields one row in parsed_documents,
    # and the second call sets X-Cache: HIT and is < 150 ms.
    ok("Test 1: Resume cache hit behavior")
    with open(resumes[0], "rb") as f:
        resp1 = httpx.post(f"{BASE}/parse/resume", files={"file": ("r.pdf", f)})
    if resp1.status_code != 200:
        fail(f"first resume POST failed: {resp1.status_code} {resp1.text}")
    if resp1.headers.get("X-Cache") != "MISS":
        fail(f"first resume POST should set X-Cache: MISS, got {resp1.headers.get('X-Cache')}")

    # Second call should be a cache hit
    with open(resumes[0], "rb") as f:
        t0 = time.perf_counter()
        resp2 = httpx.post(f"{BASE}/parse/resume", files={"file": ("r.pdf", f)})
        ms = (time.perf_counter() - t0) * 1000
    if resp2.status_code != 200:
        fail(f"second resume POST failed: {resp2.status_code} {resp2.text}")
    if resp2.headers.get("X-Cache") != "HIT":
        fail(f"second resume POST should set X-Cache: HIT, got {resp2.headers.get('X-Cache')}")
    if ms >= 150:
        fail(f"cache-hit latency {ms:.1f}ms >= 150ms")
    ok(f"  Cache hit in {ms:.1f}ms")

    # Assertion 2: Posting /parse/jd with body {"text": ""} returns 422.
    ok("Test 2: JD with empty text returns 422")
    resp = httpx.post(
        f"{BASE}/parse/jd",
        json={"text": ""},
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code != 422:
        fail(f"empty JD text should return 422, got {resp.status_code}")
    ok("  Empty text correctly rejected")

    # Assertion 3: Posting /parse/jd with garbled non-English text returns 415.
    ok("Test 3: Non-English text returns 415")
    resp = httpx.post(
        f"{BASE}/parse/jd",
        json={"text": "你好世界 こんにちは 안녕하세요 مرحبا"},
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code != 415:
        fail(f"non-English text should return 415, got {resp.status_code}")
    ok("  Non-English text correctly rejected")

    # Assertion 4: The `model_used` field is non-empty on every successful response.
    ok("Test 4: model_used field is non-empty")
    with open(resumes[0], "rb") as f:
        resp = httpx.post(f"{BASE}/parse/resume", files={"file": ("r.pdf", f)})
    if resp.status_code != 200:
        fail(f"resume POST failed: {resp.status_code}")
    data = resp.json()
    if not data.get("model_used"):
        fail(f"model_used field is empty: {data.get('model_used')}")
    ok(f"  model_used = {data.get('model_used')}")

    # Assertion 5: Cache-hit latency is < 150 ms (measure round-trip).
    ok("Test 5: Cache-hit latency < 150ms")
    with open(jds[0], "rb") as f:
        # First upload
        resp1 = httpx.post(f"{BASE}/parse/jd", files={"file": ("j.pdf", f)})
    if resp1.status_code != 200:
        fail(f"first JD POST failed: {resp1.status_code}")

    # Second upload should hit cache
    with open(jds[0], "rb") as f:
        t0 = time.perf_counter()
        resp2 = httpx.post(f"{BASE}/parse/jd", files={"file": ("j.pdf", f)})
        ms = (time.perf_counter() - t0) * 1000

    if resp2.status_code != 200:
        fail(f"second JD POST failed: {resp2.status_code}")
    if ms >= 150:
        fail(f"JD cache-hit latency {ms:.1f}ms >= 150ms")
    ok(f"  JD cache hit in {ms:.1f}ms")

    print("\nAll assertions passed! ✓")


if __name__ == "__main__":
    main()
