#!/usr/bin/env python3
"""Classify one email with laya-mlx public APIs.

Usage:
  python email_classify.py
  python email_classify.py --model aac6fef/laya-mlx --subject "..." --body-file msg.txt
"""

from __future__ import annotations

import argparse
import json
import sys

import laya_mlx as laya
from laya_mlx import email_questions, email_state

DEFAULT_MODEL = "aac6fef/laya-mlx"
DEFAULT_SUBJECT = "Duplicate charge on invoice #4411"
DEFAULT_BODY = """We were billed twice for March. Please refund the duplicate today
or we will cancel our plan.

Regards,
Alex
"""


def classify(
    subject: str,
    body: str,
    sender: str | None = None,
    model: str = DEFAULT_MODEL,
    dtype: str = "float16",
) -> dict:
    agent = laya.load(model, dtype=dtype)
    state = email_state(subject=subject, body=body, sender=sender)
    return agent.predict(state, email_questions())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dtype", choices=("float16", "float32", "bfloat16"), default="float16")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--sender", default="user@example.com")
    parser.add_argument("--body", default=None, help="Raw email body (otherwise --body-file or demo text)")
    parser.add_argument("--body-file", default=None)
    args = parser.parse_args(argv)

    if args.body_file:
        body = Path_read(args.body_file)
    elif args.body is not None:
        body = args.body
    else:
        body = DEFAULT_BODY

    result = classify(args.subject, body, sender=args.sender, model=args.model, dtype=args.dtype)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def Path_read(path: str) -> str:
    from pathlib import Path

    return Path(path).read_text()


if __name__ == "__main__":
    raise SystemExit(main())
