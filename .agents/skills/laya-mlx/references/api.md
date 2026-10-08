# Prediction API

Public names from `laya_mlx.__all__` (v0.3.0). Anything not listed here is internal.

```text
Agent, RLAgent, load
Router, RouteDecision, DEFAULT_MODELS
shortlist_choice, predict_shortlist, embed_fn_from_agent
detect_language, detect_script, is_english
clean_email_body, email_state
email_questions, guard_questions, moderation_questions, router_questions, triage_questions
```

`system_one` is a method alias of `predict` on both `Agent` and `Router`.

## `Agent.predict(state, questions)`

```python
result = agent.predict(state, questions)
# same:
result = agent.system_one(state, questions)
```

- `state`: `str`, JSON-like `dict`, or conversation `list`. `None` raises.
- `questions`: `dict` keyed by question id (`str` or nonempty `int`). Values are question dicts.

Empty `questions` returns `answers: {}` and `usage.input_tokens == 0`.

Questions in one call are independent rows. They are chunked by `agent.batch_size`. The encoder representation of each row depends on **both** state and that question. This runtime does not encode the state once and reuse hidden states across arbitrary questions.

### Other Agent methods

| Method | Role |
|---|---|
| `prepare(state, questions)` | CPU tokenization + per-question diagnostics; used internally |
| `forward(batch)` | One collated batch → evaluated MLX logits |

Callers should use `predict`, not `forward`, unless reproducing internals.

## Question dict

Required:

- `type`: `"choice"` \| `"score"` \| `"noul"`
- `instructions`: nonempty JSON-serializable value. `None`, `""`, blank string, or empty container raises. Non-strings are `json.dumps(..., ensure_ascii=False)`.

### `choice`

- `criteria`: nonempty `dict[str, ...]` **or** `list[str]` of unique labels
- List form becomes `dict.fromkeys(criteria)` (labels with no description)
- Duplicate labels raise
- Non-string labels raise

### `score`

- `criteria`: nonempty `list` of levels
- A `None` level raises
- Answer `score` is the expected value `sum(i * p_i)` over zero-based indices

### `noul`

- No `criteria` required
- If present, must be a dict whose keys (after `str(k).lower()`) are only `"false"` and/or `"true"` (Python `True`/`False` keys work)
- `labels` is **only** allowed on `noul`: exactly `{"false": str, "true": str}` mapping to distinct nonempty stripped strings. Display text changes; the answer is still P(true) at index 1
- Invalid noul keys raise rather than being ignored

Errors from `_to_internal` are re-raised as `ValueError(f"Question {qid!r}: {error}")`.

## Result payload

Top-level keys from `Agent.predict`:

```python
{
  "model": "laya-rl-agent",  # constant string, not the Hub id
  "answers": { <qid>: <answer> },
  "usage": { ... },
}
```

`Router.predict` adds `"routing"`. `predict_shortlist` adds `"shortlist"`.

Probabilities and scores are rounded to **four decimals**, matching upstream.

See [schemas.md](schemas.md) for every answer field.

## Presets (`laya_mlx.presets`)

| Function | Typical state keys mentioned in instructions |
|---|---|
| `triage_questions()` | `message` |
| `email_questions(categories=None)` | `body` |
| `guard_questions()` | `prompt` |
| `moderation_questions()` | `post` |
| `router_questions()` | `request` |

`email_questions(categories)` replaces the default category dict if you pass one.

These are ordinary question dicts. They do not load a model.

## Email helpers

```python
clean_email_body(body: str, max_chars: int = 3000) -> str
email_state(subject, body, sender=None, clean=True, max_chars=3000, **extra) -> dict
```

`email_state` returns `{"subject", "body"}`, plus `"from"` if `sender` is truthy, plus any other non-`None` keyword (typos become extra fields; they are not errors). `clean=False` skips stripping and ignores `max_chars`.

## Language helpers

```python
detect_language(state) -> dict   # alias of lang.analyse
detect_script(text: str) -> str
is_english(state) -> bool
```

`detect_language` keys include `script`, `script_profile`, `language`, `is_english`, `language_undecided`, `diacritic_rate`, `non_latin_fraction`, `mixed_segment`. Heuristic, not a language-id model.

## Shortlist

```python
shortlist_choice(state, criteria, embed_fn, k=20, *, instructions=None) -> list
predict_shortlist(agent, state, questions, embed_fn, k=20, **predict_kwargs) -> dict
embed_fn_from_agent(agent, max_length=512, batch_size=32) -> callable
```

`k` must be a positive `int`. `embed_fn(texts) -> (len(texts), dim)`. A dedicated bi-encoder usually ranks better than `embed_fn_from_agent`. Probabilities after shortlisting are over **kept labels only**.

`Agent.predict` does not shortlist.

## Router

See [multilingual.md](multilingual.md). `predict` kwargs: `model`, `task`, `lang`. Extra kwargs on `predict_shortlist` are forwarded (e.g. `model=` when `agent` is a `Router`).

## CLI mapping

`laya-mlx predict` constructs `Agent(model, device, dtype, revision, subfolder, batch_size)` then `json.dumps(agent.predict(...))`. It does not expose compile / cache / pad flags.
