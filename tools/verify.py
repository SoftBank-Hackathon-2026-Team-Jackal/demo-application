#!/usr/bin/env python3
"""Compare acknowledged source writes with the target API after migration."""

import argparse
import json
from pathlib import Path
from urllib.request import urlopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--ledger", default="traffic-ledger.jsonl")
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.ledger).read_text().splitlines() if line.strip()]
    failures = []
    for row in rows:
        try:
            with urlopen(f"{args.target_url.rstrip('/')}/api/messages/{row['id']}", timeout=10) as response:
                actual = json.load(response)
            if actual["request_id"] != row["request_id"] or actual["body"] != row["body"]:
                failures.append(row["request_id"])
        except Exception:
            failures.append(row["request_id"])
    print(json.dumps({"acknowledged": len(rows), "matched": len(rows) - len(failures), "failed_request_ids": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
