# Examples

Runnable email script: [../scripts/email_classify.py](../scripts/email_classify.py).

All snippets use public 0.3.0 APIs only.

## 1. Email triage (choice + score + noul)

```python
import laya_mlx as laya
from laya_mlx import email_state, email_questions

raw_body = """
We were billed twice for March on invoice #4411.
Please refund the duplicate today or we will cancel our plan.

Regards,
Alex
"""

agent = laya.load("aac6fef/laya-mlx")
state = email_state(
    subject="Duplicate charge on invoice #4411",
    body=raw_body,
    sender="user@example.com",
)
result = agent.predict(state, email_questions())
answers = result["answers"]
print(answers["category"]["choice"])
print(answers["urgency"]["score"], answers["urgency"]["legend"])
print(answers["is_phishing"]["noul"], answers["needs_reply"]["noul"])
```

Default `email_questions()` ids: `category`, `is_spam`, `is_phishing`, `urgency`, `needs_reply`.

Custom categories:

```python
qs = email_questions({
    "billing": "invoices, payments, refunds",
    "legal": "contracts, DSAR, terms",
    "other": "everything else",
})
```

## 2. Ticket triage preset

```python
from laya_mlx import load, triage_questions

agent = load("aac6fef/laya-mlx")
result = agent.predict(
    {"message": "I was billed twice. Please refund the duplicate today."},
    triage_questions(),
)
```

Instructions on this preset read `message`. Put the customer text in that key.

## 3. Multilingual email via Router

```python
from laya_mlx import Router, email_state, email_questions

router = Router(dtype="float16", max_loaded=2)
state = email_state("重复扣款", "发票被重复扣款，请退款。")
result = router.predict(state, email_questions())
print(result["routing"]["reason"])
print(result["answers"]["category"]["choice"])
```

## 4. Explicit noul labels

```python
result = agent.predict(
    "Please send the money back.",
    {
        "refund": {
            "type": "noul",
            "instructions": "Does the customer ask for money back?",
            "criteria": {"true": "refund or chargeback", "false": "no money movement"},
            "labels": {"false": "no", "true": "yes"},
        }
    },
)
print(result["answers"]["refund"]["noul"])
```

## 5. Conversation list (keep newest tokens)

```python
state = [
    {"role": "user", "content": "old context that may be dropped"},
    {"role": "user", "content": "I need a refund on invoice 4411 today."},
]
result = agent.predict(
    state,
    {"intent": {"type": "choice", "instructions": "Intent?", "criteria": ["refund", "other"]}},
)
print(result["usage"]["truncated"])
```

## 6. Shortlist a large category set

```python
from laya_mlx import load, predict_shortlist, embed_fn_from_agent

agent = load("aac6fef/laya-mlx")
questions = {
    "queue": {
        "type": "choice",
        "instructions": "Which queue?",
        "criteria": {f"q{i}": f"queue {i}" for i in range(80)},
    }
}
result = predict_shortlist(
    agent,
    {"body": "Duplicate invoice, please refund."},
    questions,
    embed_fn_from_agent(agent),
    k=20,
)
print(result["shortlist"]["queue"]["labels"][:5])
print(result["answers"]["queue"]["choice"])
```

## 7. Guard / moderation presets

```python
from laya_mlx import guard_questions, moderation_questions

agent.predict({"prompt": user_text}, guard_questions())
agent.predict({"post": user_text}, moderation_questions())
```

## 8. Convert then load locally

```python
from laya_mlx.convert import convert
from laya_mlx import load

out = convert("convaiinnovations/laya", "models/laya-mlx-fp16", dtype="float16")
agent = load(out, dtype="float16")
```

## Not examples (upstream only)

These are **not** available in `laya-mlx` 0.3.0:

```python
agent.predict_long(...)   # does not exist
laya.serve(...)           # does not exist
agent.train(...)          # does not exist
```
