---
name: laya-mlx
description: >
  Native MLX inference for Laya typed decision models on Apple Silicon. Use when
  classifying email, triaging tickets, scoring rubrics, estimating P(true), routing
  multilingual text, shortlisting large choice sets, converting Laya checkpoints, or
  when the user mentions laya-mlx, typed decisions, choice/score/noul,
  aac6fef/laya-mlx, or Apple Silicon Laya inference. Do not use for Laya training,
  RLCD, laya-serve, predict_long, hooks, or other upstream-only APIs.
compatibility: Apple Silicon macOS 14+, Python 3.11+, MLX 0.32.x. Not for Linux/Windows/CUDA.
license: Apache-2.0
metadata:
  package: laya-mlx
  package_version: "0.3.0"
  verified_commit: ca5940aa9286dbbdfaacbecbdb7b337295ad36a2
  repository: https://github.com/mizorewww/laya-mlx
  upstream: https://github.com/NandhaKishorM/laya
---

# laya-mlx

Open-weight **typed decisions** on Apple Silicon. One bidirectional forward pass returns a choice, a rubric score, or P(true). No output tokens, no generated JSON, no PyTorch at inference.

This skill documents **`laya-mlx` 0.3.0** only. Features that exist solely in upstream [`NandhaKishorM/laya`](https://github.com/NandhaKishorM/laya) are listed under [Upstream vs this port](#upstream-vs-this-port). Do not invent them.

Verified against git commit `ca5940aa9286dbbdfaacbecbdb7b337295ad36a2` (tag `v0.3.0`).

## When to load

Load this skill when the task is local Laya inference on a Mac with Apple Silicon: email/ticket triage, guardrails, moderation, model routing questions, multilingual checkpoint selection, or converting a Laya checkpoint to MLX.

Do **not** load it for training, fine-tuning, RLCD, a Laya HTTP server, long-document sliding windows, or CUDA/PyTorch serving.

## Requirements

- macOS 14+ on **arm64** (Apple Silicon)
- Python **3.11+**
- `pip install laya-mlx` (pulls `mlx>=0.32.2,<0.33` on Darwin arm64, plus numpy, huggingface-hub, tokenizers)

First `load()` downloads weights. Later calls are local. Optional Hub token: `token=` or `HF_TOKEN`.

Details: [references/install.md](references/install.md)

## Quick start

```python
import laya_mlx as laya

agent = laya.load("aac6fef/laya-mlx")  # FP16 MLX weights; default dtype is float16
result = agent.predict(
    "I was billed twice. Please refund the duplicate.",
    {
        "department": {
            "type": "choice",
            "instructions": "Who should handle this?",
            "criteria": ["billing", "technical", "sales"],
        }
    },
)
print(result["answers"]["department"]["choice"])
```

`system_one` is an alias of `predict`. `RLAgent` is an alias of `Agent`.

## Decision types (only these three)

| `type` | Criteria | Reported answer |
|---|---|---|
| `choice` | nonempty unique string labels: `list` or `dict` | `choice` + `probabilities` |
| `score` | nonempty list of rubric levels (no `None`) | expected zero-based `score` + `legend` |
| `noul` | optional `{false, true}` descriptions; optional `labels` | `noul` = P(true) |

Unknown types raise. There is no generation, ranking, or extraction type.

Schemas: [references/schemas.md](references/schemas.md). Full signatures: [references/api.md](references/api.md).

## Load a checkpoint

```python
agent = laya.load("aac6fef/laya-mlx", dtype="float16")
agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
agent = laya.load("./models/laya", dtype="float32", batch_size=32, device="gpu")
```

| Checkpoint | Hub (MLX FP16) | Original ID | Context |
|---|---|---|---:|
| English 421M | `aac6fef/laya-mlx` | `convaiinnovations/laya` | 512 |
| Multilingual 322M | `aac6fef/laya-multilingual-mlx` | `convaiinnovations/laya-multilingual` or `convaiinnovations/laya` + `subfolder="multilingual"` | 1024 |
| Typed-decisions 421M | `aac6fef/laya-typed-decisions-mlx` | `convaiinnovations/laya-typed-decisions` | 1024 |

`device` is `None` (MLX default), `"gpu"`, `"metal"`, or `"cpu"`. Not `"cuda"`.

Details: [references/models.md](references/models.md)

## Email classification

Prefer `email_state` + `email_questions` over raw MIME:

```python
from laya_mlx import load, email_state, email_questions

agent = load("aac6fef/laya-mlx")
state = email_state(
    subject="Duplicate charge on invoice #4411",
    body=raw_body,
    sender="user@example.com",
)
result = agent.predict(state, email_questions())
```

Runnable copy: [scripts/email_classify.py](scripts/email_classify.py). More recipes: [references/examples.md](references/examples.md).

## Multilingual routing

```python
from laya_mlx import Router, triage_questions

router = Router(dtype="float16", max_loaded=2)
result = router.predict({"message": "发票被重复扣款，请退款。"}, triage_questions())
print(result["routing"]["model"])  # multilingual
```

Default route never picks `typed-decisions` unless `task="typed_decisions"` or `auto_task_detection=True`. English checkpoints are not substitutes for the multilingual one.

Details: [references/multilingual.md](references/multilingual.md)

## Batching and speed

- `batch_size=16` (default) is questions per forward pass, not documents.
- Opt-in only: `compile=True`, `pad_to_multiple=16`, `cache_prompts=True` (prefix cache capacity 128). Encoder hidden states are **not** reused across questions.
- Large choice sets: `predict_shortlist` / `embed_fn_from_agent` (opt-in; `predict` still scores every label).

Details: [references/performance.md](references/performance.md)

## CLI

```bash
laya-mlx predict --model aac6fef/laya-mlx --state-file state.json --questions questions.json
laya-mlx convert --model convaiinnovations/laya --dtype float16 --output models/laya-mlx-fp16
```

`convert` refuses to overwrite an existing directory. It is a parameter-name/dtype export, not quantization.

## Upstream vs this port

**In `laya-mlx`:** MLX `Agent`/`load`, three decision types, Router, language heuristics, email helpers, presets, shortlist, `convert`, `laya-mlx` / `laya-snake` CLIs, compile/pad/cache flags.

**Upstream only (do not call here):** RLCD training and fine-tuning, `predict_long` / long-document windows, hooks, `laya-serve` and other server APIs, a separate batch-documents API, CUDA. Neural parity is tested against upstream `573e5b6`. Selected input/routing/email fixes come from `4aa6761` (v0.3.23); that is not full API parity.

## Errors

Read [references/troubleshooting.md](references/troubleshooting.md) before guessing. Common hard failures: missing checkpoint files, unsupported encoder/`rope_type`, empty instructions, duplicate choice labels, `noul` keys other than false/true, non-finite logits (`dtype="float32"`), `FileExistsError` on convert.

Confidence (`confidence` vs `answer_confidence`) is not accuracy. Clamped calibration temperatures can make large choice sets over-confident; see `agent.temperature_raw`.

## Smoke test

```bash
python .agents/skills/laya-mlx/scripts/smoke_test.py
```

Downloads a published MLX checkpoint on first run.
