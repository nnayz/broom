# Installation and environment

Verified against `laya-mlx` **0.3.0**, git `ca5940aa9286dbbdfaacbecbdb7b337295ad36a2`.

## Supported environment

From `pyproject.toml` and the README:

| Requirement | Value |
|---|---|
| OS | macOS (`Operating System :: MacOS`) |
| CPU | Apple Silicon (`mlx` extra is gated on `sys_platform == 'darwin' and platform_machine == 'arm64'`) |
| Python | `>=3.11` |
| MLX | `mlx>=0.32.2,<0.33` (Darwin arm64 only) |
| Other deps | `numpy>=1.26`, `huggingface-hub>=0.34,<2`, `tokenizers>=0.21,<1` |
| Documented macOS floor | macOS 14+ |
| Measured README environment | macOS 27.2, Python 3.12.13, MLX 0.32.2 |

`laya-mlx` does not depend on PyTorch or Transformers at runtime. Importing the installed package must not pull them in.

Linux, Windows, Intel Macs, and CUDA are not supported by this package.

## Install

```bash
pip install laya-mlx
```

From git:

```bash
pip install 'git+https://github.com/mizorewww/laya-mlx.git'
```

Development checkout:

```bash
gh repo clone mizorewww/laya-mlx
cd laya-mlx
uv sync --extra demo
```

Optional extras (from `pyproject.toml`):

| Extra | Packages | When |
|---|---|---|
| `dev` | pytest, ruff, build | tests / lint |
| `reference` | torch, transformers, safetensors | parity tests against upstream |
| `benchmark` | matplotlib, pyarrow | local benches |
| `demo` | rich, Pillow | `laya-snake` |

Weights are **not** in the wheel. First `laya.load(...)` calls `huggingface_hub.snapshot_download`.

## Auth

`Agent(..., token=...)` and `Router(..., token=...)` pass a Hub token. `Router` also reads `HF_TOKEN` from the environment. Public `aac6fef/*` MLX repos do not require a token.

## Entry points

| Command | Module |
|---|---|
| `laya-mlx` | `laya_mlx.cli:main` |
| `laya-snake` | `laya_mlx.snake.cli:main` |

```bash
laya-mlx --version
laya-mlx predict --model aac6fef/laya-mlx --state 'text' --questions questions.json
laya-mlx predict --model aac6fef/laya-mlx --state-file state.json --questions questions.json --device gpu --batch-size 16
laya-mlx convert --model convaiinnovations/laya --dtype float16 --output models/laya-mlx-fp16
```

`--state` and `--state-file` are mutually exclusive. Convert never overwrites `--output`.

## License

Apache-2.0. Weights are Convai Innovations / upstream Laya, downloaded separately. Prompt construction, routing, email helpers and presets are adapted from [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya) at `573e5b62696ba441230cd6be71d593331b5d23af`, with selected input/routing/email fixes from `4aa6761`.
