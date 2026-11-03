#!/usr/bin/env python3
"""Seed and continuously write messages; persist acknowledged writes for comparison."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen
from uuid import uuid4


def call(url: str, token: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    request = Request(
        f"{url.rstrip('/')}/api/messages",
        data=data,
        headers={"Content-Type": "application/json", "X-Demo-Write-Token": token},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def read_latest(url: str) -> None:
    with urlopen(f"{url.rstrip('/')}/api/messages?limit=1", timeout=10) as response:
        json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Source API origin")
    parser.add_argument("--ledger", default="traffic-ledger.jsonl")
    parser.add_argument("--seed", type=int, default=0, help="Write N initial messages then exit")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    token = os.environ.get("DEMO_WRITE_TOKEN")
    if not token:
        parser.error("DEMO_WRITE_TOKEN environment variable is required")
    if args.seed < 0 or args.interval <= 0:
        parser.error("seed must be >= 0 and interval must be > 0")
    ledger = Path(args.ledger)
    index = 0
    with ledger.open("a", encoding="utf-8") as output:
        while args.seed == 0 or index < args.seed:
            request_id = str(uuid4())
            body = f"데이터가 계속 쌓이고 있습니다 #{index + 1} · {datetime.now().astimezone().strftime('%m/%d %H:%M:%S')}"
            try:
                saved = call(args.url, token, {"request_id": request_id, "body": body})
                output.write(json.dumps({"id": saved["id"], "request_id": request_id, "body": body}, ensure_ascii=False) + "\n")
                output.flush()
                os.fsync(output.fileno())
                index += 1
                print(f"acknowledged {index}: {saved['id']}", flush=True)
            except Exception as error:
                print(f"write failed: {type(error).__name__}; retrying same request_id", flush=True)
                # The next request must reuse the same ID until the outcome is known.
                while True:
                    time.sleep(args.interval)
                    try:
                        saved = call(args.url, token, {"request_id": request_id, "body": body})
                        output.write(json.dumps({"id": saved["id"], "request_id": request_id, "body": body}, ensure_ascii=False) + "\n")
                        output.flush()
                        os.fsync(output.fileno())
                        index += 1
                        print(f"acknowledged {index}: {saved['id']}", flush=True)
                        break
                    except Exception:
                        continue
            if args.seed == 0:
                if index % 2 == 0:
                    try:
                        read_latest(args.url)
                    except Exception:
                        print("read failed; write loop continues", flush=True)
                time.sleep(args.interval)


if __name__ == "__main__":
    main()
