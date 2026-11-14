import argparse
import asyncio
import json
import re
import statistics
import time

import httpx

from copilot.config import settings

PROVIDERS = {
    "groq": (
        "https://api.groq.com/openai/v1",
        settings.groq_api_key,
        settings.groq_model,
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        settings.openrouter_api_key,
        settings.openrouter_model,
    ),
    "ollama": (
        "http://localhost:11434/v1",
        "ollama",
        settings.ollama_model,
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        settings.gemini_api_key,
        settings.gemini_model,
    ),
}

TRANSCRIPT = """[0] Priya: Okay, so the pricing page.
I'll send the draft by Friday.
[1] Sam: Cool. Someone should probably check legal
on the refund wording.
[2] Dan: Actually scratch that, I'll do the legal check.
Next Tuesday."""

PROMPT_TEMPLATE = """
Extract action items from this meeting transcript.

Return ONLY JSON in this exact shape:
{{
  "action_items": [
    {{
      "title": "short action description",
      "owner_raw": "exact speaker name or null",
      "deadline_raw": "exact deadline phrase or null"
    }}
  ]
}}

Rules:
- owner_raw must be the speaker's name, copied from the transcript.
- Do not assign an owner based on a suggestion from another speaker.
- Use null if no speaker explicitly accepts responsibility.
- Preserve deadline wording. Do not convert it into a date.
- Do not include Markdown fences or explanations.

Transcript:
{transcript}
"""


def make_long_transcript():
    filler = (
        "The team reviewed the dashboard layout, discussed navigation, "
        "checked the weekly progress report, and agreed to continue "
        "reviewing the implementation during the next meeting."
    )

    # Approximately 15,000+ additional characters of synthetic discussion.
    sections = [f"[{i}] Speaker{i % 4}: {filler}" for i in range(100)]

    # Put the real action items in the middle of the longer transcript.
    sections.insert(50, TRANSCRIPT)
    return "\n".join(sections)


def check_owner_instructions(parsed):
    items = parsed.get("action_items", [])

    pricing = next(
        (
            item
            for item in items
            if "pricing" in item.get("title", "").lower()
            or "draft" in item.get("title", "").lower()
        ),
        None,
    )

    legal = next(
        (
            item
            for item in items
            if "legal" in item.get("title", "").lower() or "refund" in item.get("title", "").lower()
        ),
        None,
    )

    return (
        pricing is not None
        and pricing.get("owner_raw") == "Priya"
        and legal is not None
        and legal.get("owner_raw") == "Dan"
    )


async def call(client, name, base, key, model, transcript, timeout):
    started = time.perf_counter()

    prompt = PROMPT_TEMPLATE.format(transcript=transcript)

    try:
        response = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 400,
            },
            timeout=timeout,
        )
    except httpx.TimeoutException:
        return {
            "ok": False,
            "error": "timeout",
            "seconds": time.perf_counter() - started,
        }
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "error": f"network:{type(exc).__name__}",
            "seconds": time.perf_counter() - started,
        }

    elapsed = time.perf_counter() - started

    if response.status_code != 200:
        return {
            "ok": False,
            "error": f"http{response.status_code}",
            "seconds": elapsed,
            "retry_after": response.headers.get("retry-after"),
            "rate_remaining": response.headers.get("x-ratelimit-remaining-requests"),
            "body": response.text[:200],
        }

    try:
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return {
            "ok": False,
            "error": "empty_or_invalid_response",
            "seconds": elapsed,
        }

    if not content or not content.strip():
        return {
            "ok": False,
            "error": "empty_response",
            "seconds": elapsed,
        }

    fenced = content.strip().startswith("```")
    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        content.strip(),
        flags=re.IGNORECASE,
    ).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "bad_json",
            "seconds": elapsed,
            "fenced": fenced,
        }

    if not isinstance(parsed, dict) or not isinstance(parsed.get("action_items"), list):
        return {
            "ok": False,
            "error": "bad_shape",
            "seconds": elapsed,
            "fenced": fenced,
        }

    return {
        "ok": True,
        "error": None,
        "seconds": elapsed,
        "fenced": fenced,
        "owner_ok": check_owner_instructions(parsed),
        "rate_remaining": response.headers.get("x-ratelimit-remaining-requests"),
    }


async def run_phase(phase, names, count, transcript):
    results = {}

    limits = httpx.Limits(
        max_connections=40,
        max_keepalive_connections=20,
    )

    async with httpx.AsyncClient(limits=limits) as client:
        for name in names:
            base, key, model = PROVIDERS[name]

            if not key or not model:
                print(f"{name}: skipped (not configured)")
                continue

            timeout = httpx.Timeout(
                connect=10,
                read=180 if name == "ollama" else 60,
                write=20,
                pool=10,
            )

            print(f"{phase}: testing {name} ({count} request(s))...")

            tasks = [
                call(
                    client,
                    name,
                    base,
                    key,
                    model,
                    transcript,
                    timeout,
                )
                for _ in range(count)
            ]

            # Concurrent requests for the burst test.
            # Sequential requests for baseline and long tests.
            if phase == "burst":
                provider_results = await asyncio.gather(*tasks)
            else:
                provider_results = []
                for task in tasks:
                    provider_results.append(await task)

            results[name] = provider_results

            successful = [r for r in provider_results if r["ok"]]
            errors = [r["error"] for r in provider_results if not r["ok"]]
            latencies = [r["seconds"] for r in provider_results]

            fenced_count = sum(r.get("fenced", False) for r in successful)
            owner_pass = sum(r.get("owner_ok", False) for r in successful)

            print(
                f"{name}: "
                f"success={len(successful)}/{count} "
                f"median_s={statistics.median(latencies):.2f} "
                f"fenced={fenced_count} "
                f"owner_pass={owner_pass}/{len(successful)} "
                f"errors={errors}"
            )

            retry_values = [r.get("retry_after") for r in provider_results if r.get("retry_after")]
            if retry_values:
                print(f"  retry-after headers: {retry_values}")

    return results


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Send 30 concurrent requests to hosted providers.",
    )
    parser.add_argument(
        "--long",
        action="store_true",
        help="Test one long synthetic transcript per hosted provider.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Test Ollama once with a longer timeout.",
    )
    args = parser.parse_args()

    if sum([args.burst, args.long, args.local]) != 1:
        parser.error("Choose exactly one: --burst, --long, or --local")

    hosted = ["groq", "gemini", "openrouter"]

    if args.burst:
        await run_phase(
            "burst",
            hosted,
            30,
            TRANSCRIPT,
        )
    elif args.long:
        await run_phase(
            "long",
            hosted,
            1,
            make_long_transcript(),
        )
    elif args.local:
        await run_phase(
            "local",
            ["ollama"],
            1,
            TRANSCRIPT,
        )


if __name__ == "__main__":
    asyncio.run(main())
