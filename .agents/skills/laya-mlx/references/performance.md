# Batching and performance

## What `batch_size` means

`batch_size` (default **16**) is the maximum **questions per forward pass**. A request with 50 questions becomes several chunks. It is not a document batch API and not `predict_long`.

The public default is 16 to bound memory. README / BENCHMARKS.md measurements used `batch_size=64` so 50 questions fit in one pass. Larger batches can raise throughput and peak allocation.

Increase it when unified memory allows:

```python
agent = laya.load("aac6fef/laya-mlx", batch_size=64)
```

## Timing definition (BENCHMARKS.md)

End-to-end includes prompt construction, tokenization, tensors, synchronized inference, calibration, and formatting. **Model load is excluded.** `output_tokens` is always 0.

Published one-question FP16 medians on M3 Max (40 GPU cores, 128 GiB), from the README:

| Checkpoint | P50 | P95 | 50-q throughput (`batch_size=64`) | Peak MLX alloc (1 short q) |
|---|---:|---:|---:|---:|
| Laya 421M | 13.42 ms | 13.92 ms | 146.8 q/s | 943.6 MiB |
| Multilingual 322M | 7.39 ms | 7.79 ms | 395.0 q/s | 687.6 MiB |

Different lengths, question counts, and machines change these numbers. Full samples: repository `BENCHMARKS.md`.

Port fidelity on the published fixtures: 63/63 selected-answer matches in FP32 and FP16 for all three checkpoints (378/378). That is fixture fidelity, not task accuracy.

## Opt-in runtime flags

All three default **off**:

```python
agent = laya.load(
    "aac6fef/laya-mlx",
    compile=True,
    pad_to_multiple=16,
    cache_prompts=True,
)
```

| Flag | Effect | Caveat |
|---|---|---|
| `compile=True` | `mx.compile(self.model)` | First-use cost and shape specialization |
| `pad_to_multiple=16` | Pad collated length up to a multiple, capped at `max_len` | Can make some workloads slower |
| `cache_prompts=True` | `PrefixCache(capacity=128)` of **CPU** question prefixes | Shares state tokenization; every question still runs the encoder. Encoder states are never cached |

`laya-snake --optimize --max-speed` enables compilation, 16-token buckets, and prefix reuse for the demo. That path is measured in `docs/SNAKE_OPTIMIZATION.md`; it is not a silent default for `predict`.

## Precision

- Default `dtype="float16"`.
- `dtype="float32"` for closer numerical agreement with upstream PyTorch MPS FP32.
- Selected labels can agree while probabilities differ slightly across dtypes.
- `bfloat16` can be requested; it is not in the published validation matrix.
- Non-finite logits raise `FloatingPointError` and tell you to retry with `float32`.

## Large choice sets

Choice options share one `head_max_len` (typically 192) token budget. Hundreds of labels leave few tokens each. If option token spans collide, `usage.options[qid]` reports `total`, `distinct`, `tokens_per_option`.

Opt-in shortlist (does not change `predict`):

```python
from laya_mlx import predict_shortlist, embed_fn_from_agent

embed_fn = embed_fn_from_agent(agent)  # mean-pool the loaded encoder; no extra weights
result = predict_shortlist(agent, state, questions, embed_fn, k=20)
```

A dedicated bi-encoder usually shortlists better. After shortlisting, probabilities are over the kept labels only.

## What will not 10× this checkpoint

`docs/MATH_10X_RESEARCH.md` and `docs/ENGINEERING_10X_RESEARCH.md` conclude there is no universal extra 10× with the same weights. Measured compile/kernel variants are about 1.03–1.08× in selected paired cases. Do not promise quantization or custom Metal kernels as supported product APIs.

## Device

Run GPU measurements sequentially. `device="gpu"` or `"metal"` uses `mx.gpu`. Hosted CI only runs small-model CPU tests.
