# Multilingual routing

## Why routing exists

The English checkpoint (ModernBERT-large, English BPE) does not degrade gently off English. Upstream-cited MASSIVE figures in `router.py`: Hindi 0.100 / Korean 0.103 at 20 options (random ≈ 0.050) with high confidence. Script is the primary signal. The multilingual checkpoint (mmBERT-base, 1024 context) is the safe default for non-English and non-Latin text.

Typed-decisions is a third checkpoint fine-tuned on four synthetic workflows. It is **never** selected automatically unless you opt in.

## `Router`

```python
from laya_mlx import Router, DEFAULT_MODELS

router = Router(
    models=None,
    device=None,
    token=None,            # or HF_TOKEN
    max_loaded=1,
    default="english",
    auto_task_detection=False,
    standalone_repos=False,
    preload=False,
    dtype="float16",
)
```

Default `DEFAULT_MODELS` (bundled original repo):

```python
{
  "english": ("convaiinnovations/laya", None),
  "multilingual": ("convaiinnovations/laya", "multilingual"),
  "typed-decisions": ("convaiinnovations/laya", "typed-decisions"),
}
```

`standalone_repos=True` uses `convaiinnovations/laya`, `.../laya-multilingual`, `.../laya-typed-decisions`.

To use published MLX repos:

```python
Router(models={
    "english": "aac6fef/laya-mlx",
    "multilingual": "aac6fef/laya-multilingual-mlx",
    "typed-decisions": "aac6fef/laya-typed-decisions-mlx",
})
```

Name aliases: `en`/`laya`/`default` → english; `multi`/`ml`/`laya-multilingual` → multilingual; `typed`/`typed_decisions`/`decisions`/`laya-typed-decisions` → typed-decisions.

### Lifecycle

| Method | Behavior |
|---|---|
| `load(name)` | Build Agent on first use; concurrent callers share one instance |
| `attach(name, agent)` | Register an already-built Agent; raises `max_loaded` to fit |
| `preload(names=None)` | Load all configured models, or the given list. `preload([])` loads nothing. Incremental preload keeps residents |
| `unload(name=None)` | Drop one or all |
| `loaded` | LRU order of resident names |

`max_loaded` defaults to 1 (LRU eviction). `Router(preload=True)` keeps all three (~1.16B params). Model lifecycle uses a re-entrant lock; **inference is not serialized**.

`device` is passed to `Agent`. Use `"gpu"` / `"metal"` / `"cpu"` / `None`. The Router docstring still mentions `"cuda"` from upstream; that value is rejected by `Agent`.

### `route` / `predict` precedence

```python
decision = router.route(state, questions, model=None, task=None, lang=None)
result = router.predict(state, questions, model=None, task=None, lang=None)
```

Precedence, first match wins:

1. explicit `model=`
2. explicit `task=` (`"typed_decisions"` / `"typed-decisions"` selects that checkpoint; other values go through `normalise_name`)
3. question-id set equals a typed-decisions workflow **and** `auto_task_detection=True`
4. explicit `lang=` if it is a usable language code
5. `detect_language(state)` script / English heuristic
6. `default` (usually `"english"`)

`lang` accepts `"en"`, `"en-US"`, `"en_US.UTF-8"`, etc. Blank, `None`, and language-agnostic codes (`C`, `POSIX`, `und`, `zxx`, `mul`) fall through to detection. Non-English codes select multilingual.

### Automatic typed-decisions workflows

Exact id-set match only (`match_typed_decisions_workflow`):

| Workflow | Question ids |
|---|---|
| `agent_trace_observability` | action, needs_review, outcome, risk, urgency |
| `customer_service` | action, category, churn_risk, needs_human, urgency |
| `invoice_processing` | discrepancy_severity, disposition, duplicate, matches_order, urgency |
| `security_incidents` | credential_compromise, disposition, severity, true_positive, urgency |

A schema that merely contains `urgency` is not captured.

## Detection (`detect_language` / `analyse`)

- Reads string **values**, not keys (keys are often English field names).
- Caps flattened text at 4000 characters for the whole-state pass; mixed-language tickets still scan lines/fields.
- Non-Latin scripts → not English.
- Unidentified Latin-script languages with a non-English diacritic rate ≥ 0.02 route away from English rather than being assumed English.
- `is_english(state)` is `bool(analyse(state)["is_english"])`.
- Best-effort stopword lists exist for several Latin languages; they are not a general LID model. Pass `lang=` or `model=` when you already know.

## English checkpoint limitation

Do not send Hindi, Korean, Arabic, CJK, or unidentified diacritic-heavy Latin text to `aac6fef/laya-mlx` / `convaiinnovations/laya` and trust the confidence. Use the multilingual checkpoint or `Router`.
