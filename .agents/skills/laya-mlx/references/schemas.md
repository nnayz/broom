# Input and output schemas

All field names below are from `laya_mlx/agent.py` and `laya_mlx/common.py` in 0.3.0.

## State

Accepted by `predict`:

| Python type | Serialization | Truncation when over `max_len` |
|---|---|---|
| `str` | as-is | keep the **beginning** |
| `dict` (JSON object) | `json.dumps(state, ensure_ascii=False)` | keep the beginning |
| `list` (conversation) | `json.dumps(...)` | keep the **newest** tokens (`truncate_left=True`) |
| `None` | rejected | `ValueError: state must not be None` |

`[MASK]` / the tokenizer mask token in state or instructions is replaced with a space so it cannot inject option markers. Option markers are the only mask tokens in the sequence.

Nested email/ticket dicts are fine. Preset instructions refer to keys such as `body`, `message`, `prompt` — put the text under those keys if you use the presets.

## Questions object

```json
{
  "<id>": {
    "type": "choice | score | noul",
    "instructions": "...",
    "criteria": {},
    "labels": {"false": "no", "true": "yes"}
  }
}
```

- Keys must be nonempty strings or integers.
- `labels` only on `noul`.
- `criteria` shapes: see [api.md](api.md).

Option text rendering (`render_options`):

- choice with description: `"label: description"`; without: `"label"`
- score: `"level {i}: {level text}"`
- noul default: `"false: no, the statement does not hold"` and `"true: yes, the statement holds"` unless criteria/labels override

Structured criterion values become compact JSON, not Python reprs.

## Answer objects

Every answer includes:

| Field | Meaning |
|---|---|
| `type` | `"choice"`, `"score"`, or `"noul"` |
| `confidence` | choice/score: `1 - H(p)/log(k)` (entropy). noul: **overwritten** to `max(P(true), 1-P(true))` |
| `answer_confidence` | `max(p)` after temperature scaling, four decimals |
| `action.act_probability` | softmax of the action head, index 0, four decimals |

### choice

```python
{
  "type": "choice",
  "confidence": 0.0,
  "answer_confidence": 0.0,
  "action": {"act_probability": 0.0},
  "choice": "<winning label>",
  "probabilities": {"<label>": 0.0, "...": 0.0},
}
```

Winning label is `labels[argmax(p)]` in criteria insertion order.

### score

```python
{
  "type": "score",
  "confidence": 0.0,
  "answer_confidence": 0.0,
  "action": {"act_probability": 0.0},
  "score": 0.0,
  "legend": {"0": "<level0>", "1": "<level1>"},
  "probabilities": {"0": 0.0, "1": 0.0},
}
```

`score` is the expected index `sum(i * p_i)`, not an integer. Range is `[0, k-1]`.

### noul

```python
{
  "type": "noul",
  "confidence": 0.0,
  "answer_confidence": 0.0,
  "action": {"act_probability": 0.0},
  "noul": 0.0
}
```

`noul` is `p[1]` (true). There is no `choice` field.

Neither `confidence` nor `answer_confidence` guarantees accuracy on a new task.

## Usage object

```python
{
  "input_tokens": 0,
  "output_tokens": 0,
  "state_tokens": 0,
  "state_tokens_dropped": 0,
  "truncated": false,
  "truncated_questions": ["..."],
  "options": {  # only if some question's option token spans collided
    "<qid>": {
      "total": 0,
      "distinct": 0,
      "tokens_per_option": 0
    }
  }
}
```

- `output_tokens` is always `0`.
- `state_tokens` is the tokenized state length **before** per-question clipping (taken from the first question's stats; the same state is reused).
- `state_tokens_dropped` is the **largest** drop across questions.
- `truncated` is `dropped > 0`.
- `truncated_questions` lists question ids whose state slice was clipped.
- `usage.options` appears only when `options_distinct < options` for a question. It reports lost distinctions; it does not recover them.

## Router extra: `routing`

A `RouteDecision` dict:

```python
{
  "model": "english | multilingual | typed-decisions",
  "repo": "convaiinnovations/laya[/subfolder]",
  "reason": "...",
  "detection": { ... } | None,
  "workflow": "<workflow name>" | None,
}
```

## Shortlist extra: `shortlist`

```python
{
  "<qid>": {
    "labels": ["..."],
    "scores": [0.0, ...] | None,
    "k": 20,
    "n": 100,
    "passthrough": false
  }
}
```

`scores` is `None` and `passthrough` is `True` when nothing was dropped (`k >= n` or non-choice).
