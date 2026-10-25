"""'Why this recipe' text.

The default explanation is a template filled with facts from the ranker, so it
is always accurate. An LLM can optionally REWRITE those same facts in friendlier
words (set PANTRY_LLM=1 and ANTHROPIC_API_KEY). The LLM never ranks and is not
given anything except the facts below; if the call fails we fall back to the
template.
"""
import os

from src.rank import Result


def join_words(items: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b and c'."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def build_facts(r: Result, subs: dict) -> dict:
    """Collect every fact the explanation may mention."""
    return {
        "recipe": r.title,
        "you_have": r.have,
        "assumed_staples": r.assumed,
        "missing": r.missing,
        "substitutions": subs,   # {missing item: [suggestion text, ...]}
        "key_ingredients_covered": f"{len(r.key_have)} of {r.key_total}",
        "steps": r.steps,
    }


def template_why(r: Result, subs: dict) -> str:
    """Plain-language line that cites the user's own ingredients."""
    total = len(r.have) + len(r.assumed) + len(r.missing)
    if r.have:
        text = f"Uses your {join_words(r.have)} - {len(r.have) + len(r.assumed)} of its {total} ingredients are covered."
    else:
        text = "Shares no ingredients with your pantry."
    if r.key_total and r.key_have:
        text += f" It covers {len(r.key_have)} of {r.key_total} title ingredients ({join_words(r.key_have)})."
    if not r.missing:
        text += " You need nothing else."
    else:
        text += f" You still need {join_words(r.missing)}."
        covered = [m for m in r.missing if subs.get(m)]
        if covered:
            text += f" Possible swaps exist for {join_words(covered)}."
    return text


def llm_enabled() -> bool:
    return os.environ.get("PANTRY_LLM") == "1" and bool(os.environ.get("ANTHROPIC_API_KEY"))


def llm_why(facts: dict) -> str | None:
    """Ask the model to reword the facts. Returns None on any problem."""
    try:
        import anthropic  # optional dependency, imported only when the flag is on
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=os.environ.get("PANTRY_LLM_MODEL", "claude-haiku-5-5"),
            max_tokens=150,
            messages=[{"role": "user", "content": (
                "Write 1-2 friendly sentences explaining why this recipe suits "
                "the user's pantry. Use ONLY the facts in this JSON; do not add "
                "ingredients, steps, health or nutrition claims.\n" + str(facts))}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None


def explain(r: Result, subs: dict, use_llm: bool = False) -> str:
    """Final explanation: LLM rewrite if enabled and working, else the template."""
    if use_llm and llm_enabled():
        text = llm_why(build_facts(r, subs))
        if text:
            return text
    return template_why(r, subs)
