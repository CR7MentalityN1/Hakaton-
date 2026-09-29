"""Sustained load with independent Keycloak PKCE sessions; never persist tokens.

Run against a disposable/demo deployment. This creates sessions and report audit
entries, but does not mutate universities or interactions.
"""

import argparse
import asyncio
import base64
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import httpx


class LoginForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("id") == "kc-form-login":
            self.action = attrs.get("action")


def summary(samples):
    durations = sorted(s["duration_ms"] for s in samples)
    return {
        "requests": len(samples),
        "errors": sum(not s["ok"] for s in samples),
        "statuses": dict(Counter(str(s["status"]) for s in samples)),
        "p50_ms": round(durations[int((len(durations) - 1) * 0.50)]),
        "p95_ms": round(durations[int((len(durations) - 1) * 0.95)]),
        "max_ms": round(durations[-1]),
    }


async def login(config, discovery, username, password, limiter):
    async with limiter, httpx.AsyncClient(timeout=30, trust_env=False) as client:
        verifier = secrets.token_urlsafe(48)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        state = secrets.token_urlsafe(24)
        response = await client.get(
            discovery["authorization_endpoint"],
            params={
                "client_id": config["clientId"],
                "redirect_uri": "http://localhost:3000/",
                "response_type": "code",
                "response_mode": "query",
                "scope": "openid",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
            },
        )
        response.raise_for_status()
        form = LoginForm()
        form.feed(response.text)
        if not form.action:
            raise RuntimeError("Keycloak did not return a login form")
        # Browsers treat HTTP localhost as a secure context. httpx does not apply
        # that exception to Secure cookies, so mirror it ONLY for loopback tests.
        if urlsplit(form.action).scheme == "http" and urlsplit(
            form.action
        ).hostname in ("localhost", "127.0.0.1"):
            for cookie in client.cookies.jar:
                cookie.secure = False
        response = await client.post(
            form.action,
            data={"username": username, "password": password, "credentialId": ""},
        )
        query = parse_qs(urlsplit(response.headers.get("location", "")).query)
        if (
            response.status_code not in (302, 303)
            or query.get("state") != [state]
            or "code" not in query
        ):
            raise RuntimeError(
                f"Keycloak login returned HTTP {response.status_code}; callback fields={sorted(query)}; state_matches={query.get('state') == [state]}"
            )
        response = await client.post(
            discovery["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "client_id": config["clientId"],
                "code": query["code"][0],
                "redirect_uri": "http://localhost:3000/",
                "code_verifier": verifier,
            },
        )
        response.raise_for_status()
        return response.json()


async def run(args):
    api = args.api.rstrip("/")
    async with httpx.AsyncClient(
        timeout=45,
        trust_env=False,
        limits=httpx.Limits(
            max_connections=args.users + 10, max_keepalive_connections=args.users + 10
        ),
    ) as client:
        config = (await client.get(api + "/api/v1/auth/config")).json()
        discovery = (
            await client.get(
                config["url"]
                + "/realms/"
                + config["realm"]
                + "/.well-known/openid-configuration"
            )
        ).json()
        health = (await client.get(api + "/health")).json()
        limiter = asyncio.Semaphore(3)
        username = os.environ.get("LOAD_USERNAME", "admin")
        password = os.environ.get("LOAD_PASSWORD", "admin123")
        print(f"Creating {args.users} independent PKCE sessions", flush=True)
        sessions = await asyncio.gather(
            *(
                login(config, discovery, username, password, limiter)
                for _ in range(args.users)
            )
        )

        async def request(index, path, payload=None):
            start = time.perf_counter()
            try:
                response = await client.request(
                    "POST" if payload else "GET",
                    api + "/api/v1" + path,
                    headers={
                        "Authorization": "Bearer " + sessions[index]["access_token"]
                    },
                    json=payload,
                )
                return {
                    "path": path,
                    "ok": response.is_success,
                    "status": response.status_code,
                    "duration_ms": (time.perf_counter() - start) * 1000,
                }
            except httpx.HTTPError:
                return {
                    "path": path,
                    "ok": False,
                    "status": "transport_error",
                    "duration_ms": (time.perf_counter() - start) * 1000,
                }

        try:
            warmup = await asyncio.gather(
                *(request(i, "/auth/me") for i in range(args.users))
            )
            if any(not s["ok"] for s in warmup):
                raise RuntimeError("Authenticated warmup failed")
            print("Warmup complete; running synchronized rounds", flush=True)
            samples = []
            for round_index in range(args.rounds):
                batch = await asyncio.gather(
                    *(
                        request(
                            i,
                            ["/universities", "/interactions", "/dashboard"][
                                (i + round_index) % 3
                            ],
                        )
                        for i in range(args.users)
                    )
                )
                samples.extend(batch)
                print(
                    f"Round {round_index + 1}/{args.rounds}: {json.dumps(summary(batch))}",
                    flush=True,
                )
            reports = await asyncio.gather(
                *(
                    request(
                        i % args.users,
                        "/reports/export",
                        {
                            "format": ["pdf", "xlsx", "xls", "json"][i % 4],
                            "columns": ["university", "program", "product", "stage"]
                            if i % 2
                            else [
                                "university",
                                "direction",
                                "program",
                                "product",
                                "stage",
                                "responsible",
                                "contract_number",
                                "license_end_date",
                            ],
                        },
                    )
                    for i in range(10)
                )
            )
            groups = defaultdict(list)
            for sample in samples:
                groups[sample["path"]].append(sample)
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api": api,
                "independent_pkce_sessions": args.users,
                "rounds": args.rounds,
                "warmup": "one authenticated request per session",
                "health": health,
                "concurrent_users": summary(samples),
                "by_endpoint": {path: summary(items) for path, items in groups.items()},
                "reports_10": summary(reports),
                "interface_p95_under_1s": summary(samples)["p95_ms"] <= 1000,
            }
            Path(args.output).write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result["concurrent_users"]["errors"] or result["reports_10"]["errors"]:
                raise SystemExit(1)
        finally:
            # End all test sessions; refresh tokens remain only in process memory.
            await asyncio.gather(
                *(
                    client.post(
                        discovery["end_session_endpoint"],
                        data={
                            "client_id": config["clientId"],
                            "refresh_token": s["refresh_token"],
                        },
                    )
                    for s in sessions
                ),
                return_exceptions=True,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--output", default="docs/load-sessions-results.json")
    args = parser.parse_args()
    if not 1 <= args.users <= 100 or not 1 <= args.rounds <= 100:
        parser.error("users and rounds must be between 1 and 100")
    asyncio.run(run(args))
