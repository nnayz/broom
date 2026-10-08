# Common errors and troubleshooting

Messages below are from `laya_mlx` 0.3.0 source. Quote them when diagnosing; do not paraphrase into a different API.

## Install / platform

| Symptom | Cause | What to do |
|---|---|---|
| `mlx` does not install | Not Darwin arm64 | This package is Apple Silicon only |
| `torch` / `transformers` imported at inference | Wrong extra or wrong package | Runtime deps do not include them. Do not `pip install laya` when you meant `laya-mlx` |
| First call is slow | Hub download | Expected. Later loads use the Hub cache |

## Load failures

| Exception | Typical message / trigger |
|---|---|
| `FileNotFoundError` | `Local model directory does not exist: ...` |
| `FileNotFoundError` | `Not a complete Laya checkpoint: {path} is missing` (`model.safetensors`, `rl_agent_config.json`, or `encoder/config.json`) |
| `ValueError` | `subfolder must be a relative path inside the model repository` |
| `ValueError` | `dtype must be one of ['float32', 'float16', 'bfloat16']` |
| `ValueError` | `MLX device must be 'gpu', 'metal', or 'cpu'` (includes `"cuda"`) |
| `ValueError` | `batch_size must be a positive integer` |
| `ValueError` | `pad_to_multiple must be a positive integer or None` |
| `ValueError` | `Laya config must specify encoder and head_layers` |
| `ValueError` | `Expected 4 < head_max_len < max_len <= max_position_embeddings` |
| `ValueError` | `Calibration temperatures must be finite and positive` |
| `ValueError` | `Unsupported encoder: ...; expected modernbert` |
| `ValueError` | `Only default (unscaled) ModernBERT RoPE is supported` |
| `ValueError` | Missing or misshaped weights (`load_weights` strict) |
| `RuntimeWarning` | Checkpoint temperatures outside `[0.5, 5.0]` were clamped |

Hub downloads need network. Pass `token=` / `HF_TOKEN` if the repo is gated.

## Predict / question errors

All invalid question dicts raise `ValueError`, usually prefixed `Question {qid!r}: ...`.

| Trigger | Error |
|---|---|
| `state is None` | `state must not be None` |
| questions not a dict | `questions must be a dictionary keyed by question id` |
| bad id | `Question id must be a nonempty string or integer` |
| unknown `type` | `Unknown question type ...; expected choice, score, or noul` |
| missing instructions | `Question is missing instructions` |
| empty / blank instructions | `instructions must not be empty or None` / `must not be blank` |
| empty choice criteria or non-unique labels | `Choice criteria must be a nonempty dictionary or list` / `Choice labels must be unique` |
| score criteria not a nonempty list or contains `None` | corresponding `ValueError` |
| noul criteria not a false/true dict | `Noul criteria must be keyed only 'false'/'true'; use labels to change display text` |
| `labels` on choice/score | `labels is only supported for noul questions` |
| too many options for `head_max_len` | `Question {qid!r} has too many options for the token budget` |
| non-finite tensors | `FloatingPointError: Non-finite model outputs; retry with dtype='float32'` |

## Convert

`FileExistsError: Output already exists: ...` — pick a new directory. Partial failed exports are deleted; existing dirs are never overwritten.

## Router

`ValueError: unknown model ...; choose one of ...` — name is not in `{english, multilingual, typed-decisions}` or aliases.

Wrong language with high confidence: you used the English checkpoint on non-English text. Use `Router` or `aac6fef/laya-multilingual-mlx`. Detection is heuristic; pass `lang=` or `model=` when known.

`max_loaded=1` plus alternating languages reloads on every switch (seconds). `preload=True` or `max_loaded=2`.

## Shortlist

| Error | Trigger |
|---|---|
| `TypeError: questions must be a dict ...` | not a dict |
| `ValueError: k must be a positive integer` | bad `k` |
| `ValueError: question {qid} is a choice but has no criteria` | missing criteria |
| `TypeError: embed_fn must be callable` | |
| `ValueError: embed_fn must return an array of shape (n, dim)` | |
| `TypeError: agent must provide predict or system_one` | |

## Confidence pitfalls

- `confidence` ≠ `answer_confidence`. Entropy vs max probability (noul overwrites `confidence` to `max(p, 1-p)`).
- Clamped `choice:11+` temperatures: do not gate production on 0.99 from a 11+ way choice without reading `temperature_raw`.
- `usage.options` means labels collided in the token budget. Shortlist or fewer labels; the model will not invent missing distinctions.
- Truncation: conversation **lists** drop oldest tokens; strings/dicts drop the tail. Check `usage.truncated` / `truncated_questions` / `state_tokens_dropped`.

## Email cleaning

`clean_email_body` removes quotes, sign-offs, device footers, and disclaimer sentences. Ordinary sentences that merely mention "confidential" or start with `From:` without an address are kept. If a request lives only after the 3000-character cut, raise `max_chars`. There is **no** `predict_long` in this package to scan windows.

## Demo (`laya-snake`)

Needs `pip install 'laya-mlx[demo]'`, a cached checkpoint (`hf download aac6fef/laya-multilingual-mlx`), and a terminal ≥ 104×35. Unrelated to email classification.
