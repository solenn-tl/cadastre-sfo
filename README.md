# Présentation SFO 16/11/2026

## Installation
```bash
uv venv .quartoenv --python 3.13
uv pip install -r requirements.txt
export QUARTO_PYTHON=$PWD/.quartoenv/bin/python
```

## Render slides
```bash
quarto preview slides/main.qmd  --port 9860 # live preview in the browser, reloads when you save
```