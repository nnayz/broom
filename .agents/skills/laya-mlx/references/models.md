# Loading models and checkpoints

## `laya.load` / `Agent`

```python
from laya_mlx import load, Agent

agent = load(
    model_id_or_path="convaiinnovations/laya",
    device=None,
    token=None,
    subfolder=None,
    *,
    dtype="float16",
    revision=None,
    batch_size=16,
    compile=False,
    pad_to_multiple=None,
    cache_prompts=False,
)
```

`load(...)` is `return Agent(...)`. `RLAgent` is `Agent`.

### Arguments (source: `laya_mlx/agent.py`)

| Name | Default | Rules |
|---|---|---|
| `model_id_or_path` | `"convaiinnovations/laya"` | Local directory or Hub repo id |
| `device` | `None` | `None` → `mx.default_device()`; `"cpu"` → CPU; `"gpu"` or `"metal"` → GPU. Anything else, including `"cuda"`, raises `ValueError` |
| `token` | `None` | Hugging Face token for `snapshot_download` |
| `subfolder` | `None` | Relative path inside the repo. Absolute paths and `..` raise `ValueError` |
| `dtype` | `"float16"` | `"float32"`, `"float16"`, or `"bfloat16"`. BF16 is accepted but not in the published validation matrix |
| `revision` | `None` | Hub revision / commit |
| `batch_size` | `16` | Positive `int` (not `bool`) |
| `compile` | `False` | If true, wraps the model with `mx.compile` |
| `pad_to_multiple` | `None` | Positive `int` or `None` |
| `cache_prompts` | `False` | Bounded CPU prefix cache, capacity 128 |

Local paths that look like paths (`/`, `./`, `../`, `~`, or a `Path`) raise `FileNotFoundError` if missing. Bare Hub ids are downloaded.

A complete checkpoint must contain:

- `model.safetensors`
- `rl_agent_config.json` (must include `encoder` and `head_layers`)
- `encoder/config.json`
- tokenizer files under `tokenizer/`

Config must satisfy `4 < head_max_len < max_len <= max_position_embeddings`. Encoder `model_type` must be `"modernbert"`, activation `"gelu"`, RoPE `rope_type` default/unscaled. Other encoders fail at load.

Loading validates every parameter name and shape (`load_weights(..., strict=True)`).

## Published checkpoints

Pre-converted FP16 MLX weights:

- [aac6fef/laya-mlx](https://huggingface.co/aac6fef/laya-mlx)
- [aac6fef/laya-multilingual-mlx](https://huggingface.co/aac6fef/laya-multilingual-mlx)
- [aac6fef/laya-typed-decisions-mlx](https://huggingface.co/aac6fef/laya-typed-decisions-mlx)

Original upstream ids also load (`sanitize_weights` maps PyTorch names). Prefer the `aac6fef/*` repos for MLX.

| Role | Parameters | Encoder | `max_len` | Purpose |
|---|---:|---|---:|---|
| English | 421M | ModernBERT-large | 512 | English Latin text |
| Multilingual | 322M | mmBERT-base | 1024 | Non-English / non-Latin |
| Typed-decisions | 421M | ModernBERT-large | 1024 | Four synthetic workflows; not an automatic default |

Context includes instructions, options, **and** state.

### Bundled original repo

`convaiinnovations/laya` can hold subfolders:

```python
laya.load("convaiinnovations/laya", subfolder="multilingual")
laya.load("convaiinnovations/laya", revision="c5d78730f3493e4fe16d61507ef4b78eef7318cf")
```

## Calibration temperatures

Fitted temperatures are clamped to `[0.5, 5.0]` before use (`TEMP_MIN` / `TEMP_MAX`). The shipped `choice:11+` bucket is 0.1006 and would otherwise sharpen logits ~10×.

Inspect:

- `agent.temperature` / `agent.temperature_by_options` — clamped values actually applied
- `agent.temperature_raw` / `agent.temperature_by_options_raw` — checkpoint values

A `RuntimeWarning` at load names every clamped bucket. Treat confidence from those buckets as uncalibrated.

## Convert to MLX

```python
from laya_mlx.convert import convert
convert("convaiinnovations/laya", "models/laya-mlx-fp16", dtype="float16")
```

Writes `model.safetensors`, `rl_agent_config.json`, `encoder/config.json`, `tokenizer/`, `mlx_config.json`. Existing output paths raise `FileExistsError`. This is not quantization or retraining.

## What loading does not do

No training, no LoRA, no 4-bit/8-bit product quantization, no CUDA device map. Research quantization lives in `docs/ENGINEERING_10X_RESEARCH.md` and is not a runtime API.
