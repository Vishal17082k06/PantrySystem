# Pantry Matcher

Tell the app what is in your kitchen; it recommends **real recipes** from a public dataset, ranked by fit, and explains what you have, what is missing, and what could substitute. Two sliders (Strictness, Effort) and dietary filters let you steer the results. Ranking is deterministic and explainable; an LLM can optionally reword the explanation but never ranks.

Quick start: see [docs/README.md](docs/README.md).

```
pip install -r requirements.txt
streamlit run app.py
python -m pytest
```

More: [report](docs/report.md) | [evaluation](docs/eval.md) | [how it works](docs/explain.md) | [slides outline](docs/presentation_outline.md) | [dev log](docs/DEVLOG.md)
