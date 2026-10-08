#!/usr/bin/env python3
"""Smoke-test the installed laya-mlx package against this skill's documented API.

Records package version and (when available) the git commit used to write the skill.
Downloads a published MLX checkpoint on first predict unless --skip-predict.

Usage:
  python smoke_test.py
  python smoke_test.py --model aac6fef/laya-multilingual-mlx
  python smoke_test.py --skip-predict
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
import traceback

SKILL_PACKAGE_VERSION = "0.3.0"
SKILL_VERIFIED_COMMIT = "ca5940aa9286dbbdfaacbecbdb7b337295ad36a2"
DEFAULT_MODEL = "aac6fef/laya-multilingual-mlx"

PUBLIC_API = (
    "Agent",
    "RLAgent",
    "load",
    "Router",
    "RouteDecision",
    "DEFAULT_MODELS",
    "shortlist_choice",
    "predict_shortlist",
    "embed_fn_from_agent",
    "detect_language",
    "detect_script",
    "is_english",
    "clean_email_body",
    "email_state",
    "email_questions",
    "guard_questions",
    "moderation_questions",
    "router_questions",
    "triage_questions",
)


def _fail(message: str) -> int:
    print("FAIL:", message, file=sys.stderr)
    return 1


def check_platform() -> list[str]:
    warnings = []
    if sys.platform != "darwin":
        warnings.append(f"sys.platform={sys.platform!r}; laya-mlx targets Darwin")
    if platform.machine() != "arm64":
        warnings.append(f"machine={platform.machine()!r}; MLX extra is Darwin arm64")
    return warnings


def check_import() -> tuple[object, str]:
    import laya_mlx as laya

    version = getattr(laya, "__version__", None) or importlib.metadata.version("laya-mlx")
    return laya, version


def check_public_api(laya) -> list[str]:
    missing = [name for name in PUBLIC_API if not hasattr(laya, name)]
    return missing


def check_email_helpers(laya) -> None:
    cleaned = laya.clean_email_body(
        "Please refund invoice 4411.\n\nThis email is confidential and intended solely for the named addressee."
    )
    if "refund" not in cleaned.lower():
        raise AssertionError(f"clean_email_body dropped the request: {cleaned!r}")
    if "confidential" in cleaned.lower():
        raise AssertionError(f"clean_email_body kept disclaimer: {cleaned!r}")
    state = laya.email_state("Locked out", "My account is locked.", sender="a@b.c")
    if state["subject"] != "Locked out" or "from" not in state:
        raise AssertionError(f"unexpected email_state: {state!r}")
    qs = laya.email_questions()
    for key in ("category", "is_spam", "is_phishing", "urgency", "needs_reply"):
        if key not in qs:
            raise AssertionError(f"email_questions missing {key}")
    if qs["category"]["type"] != "choice":
        raise AssertionError("category should be choice")
    if qs["is_phishing"]["type"] != "noul":
        raise AssertionError("is_phishing should be noul")
    if qs["urgency"]["type"] != "score":
        raise AssertionError("urgency should be score")


def check_language_helpers(laya) -> None:
    if not laya.is_english("Please refund the duplicate charge today."):
        raise AssertionError("English sample not detected as English")
    det = laya.detect_language("发票被重复扣款，请退款。")
    if det.get("is_english") is True:
        raise AssertionError(f"CJK sample marked English: {det!r}")
    script = laya.detect_script("发票")
    if script == "latin":
        raise AssertionError(f"Han sample reported latin: {script!r}")


def check_question_validation(laya) -> None:
    try:
        laya.Agent._to_internal({"type": "choice", "instructions": "x", "criteria": ["a", "a"]})
    except ValueError:
        return
    raise AssertionError("duplicate choice labels must raise ValueError")


def run_predict(laya, model: str, dtype: str) -> dict:
    from laya_mlx import email_questions, email_state

    agent = laya.load(model, dtype=dtype)
    state = email_state(
        subject="Duplicate charge on invoice #4411",
        body="We were billed twice for March. Please refund the duplicate today.",
        sender="user@example.com",
    )
    result = agent.predict(state, email_questions())
    answers = result.get("answers") or {}
    required = ("category", "is_spam", "is_phishing", "urgency", "needs_reply")
    missing = [k for k in required if k not in answers]
    if missing:
        raise AssertionError(f"predict missing answers {missing}: {list(answers)}")
    if answers["category"]["type"] != "choice" or "choice" not in answers["category"]:
        raise AssertionError(f"bad category answer: {answers['category']!r}")
    if "noul" not in answers["is_phishing"]:
        raise AssertionError(f"bad noul answer: {answers['is_phishing']!r}")
    if "score" not in answers["urgency"]:
        raise AssertionError(f"bad score answer: {answers['urgency']!r}")
    if result.get("usage", {}).get("output_tokens") != 0:
        raise AssertionError(f"output_tokens should be 0: {result.get('usage')}")
    if result.get("model") != "laya-rl-agent":
        raise AssertionError(f"unexpected result model field: {result.get('model')!r}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dtype", default="float16", choices=("float16", "float32", "bfloat16"))
    parser.add_argument("--skip-predict", action="store_true")
    args = parser.parse_args(argv)

    report = {
        "skill_package_version": SKILL_PACKAGE_VERSION,
        "skill_verified_commit": SKILL_VERIFIED_COMMIT,
        "python": sys.version.split()[0],
        "platform": f"{sys.platform}-{platform.machine()}",
    }

    for warning in check_platform():
        print("WARN:", warning)

    try:
        laya, installed = check_import()
    except Exception as exc:
        traceback.print_exc()
        return _fail(f"import laya_mlx failed: {exc}")
    report["installed_version"] = installed
    print(f"installed laya-mlx {installed} (skill documented {SKILL_PACKAGE_VERSION})")
    print(f"skill verified commit {SKILL_VERIFIED_COMMIT}")

    if installed != SKILL_PACKAGE_VERSION:
        print(
            f"WARN: installed version {installed} != documented {SKILL_PACKAGE_VERSION}",
            file=sys.stderr,
        )

    missing = check_public_api(laya)
    if missing:
        return _fail(f"public API missing: {missing}")

    try:
        check_email_helpers(laya)
        check_language_helpers(laya)
        check_question_validation(laya)
    except Exception as exc:
        traceback.print_exc()
        return _fail(str(exc))

    if args.skip_predict:
        report["predict"] = "skipped"
        print(json.dumps(report, indent=2))
        print("OK (skipped predict)")
        return 0

    try:
        result = run_predict(laya, args.model, args.dtype)
    except Exception as exc:
        traceback.print_exc()
        return _fail(f"predict smoke failed: {exc}")

    category = result["answers"]["category"]
    report["predict"] = {
        "model_arg": args.model,
        "dtype": args.dtype,
        "category": category.get("choice"),
        "refund_noul": result["answers"]["is_phishing"]["noul"],
        "urgency_score": result["answers"]["urgency"]["score"],
        "input_tokens": result["usage"]["input_tokens"],
    }
    print("category:", category.get("choice"), "probs:", category.get("probabilities"))
    print("urgency score:", result["answers"]["urgency"]["score"])
    print("needs_reply noul:", result["answers"]["needs_reply"]["noul"])
    print(json.dumps(report, indent=2))
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
