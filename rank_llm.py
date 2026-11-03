"""LLM reranking of an already-retrieved shortlist (D-19, D-16).

Stage 2 of a two-stage ranker. `rank.py` retrieves candidates with TF-IDF; this
module asks Claude to reorder *those candidates only* and write the one-line
`reason` the ERD already has a column for.

THE RULE THAT MATTERS
---------------------
F-26: both AI users in the elicitation reported that an AI recommended courses
that were not offered that semester. D-16 makes grounding in the real offered
list the differentiator. So the model is never asked what to take -- it is handed
a list of real CRNs and allowed only to reorder them. Every CRN it returns is
checked against the input set and silently dropped if it was not in it
(`_validate`). A hallucinated course cannot reach the student.

PRIVACY
-------
Only the typed phrase, the outstanding gen-ed bucket names, and public catalog
text leave this machine. No student name, no ID, no completed coursework, no
grades. See `build_prompt`.

REQUIREMENTS
------------
`anthropic>=1.0` and a credential (ANTHROPIC_API_KEY, or `ant auth login`).
With neither, `available()` returns False and the caller falls back to TF-IDF.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(HERE, ".env")


def load_env(path=ENV_FILE):
    """Read KEY=value lines from a gitignored .env into os.environ.

    Env vars set in a shell do not survive between separate invocations, and on
    Windows `setx` needs a restart before running processes see it. A file next
    to the app sidesteps both. Existing environment values always win.
    """
    if not os.path.exists(path):
        return []
    loaded = []
    # utf-8-sig, not utf-8: PowerShell's Out-File / Set-Content write a BOM,
    # which would otherwise become part of the first key name and never match.
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and not os.environ.get(key):
                os.environ[key] = value
                loaded.append(key)
    return loaded


load_env()

MODEL = os.environ.get("NAVIGATOR_MODEL", "claude-opus-5")

# Effort is a latency choice, not a cost one: this sits in an interactive search
# path. Reranking a pre-filtered shortlist is well-scoped work, so "medium"
# keeps a click responsive. Raise it with NAVIGATOR_EFFORT if quality lags.
EFFORT = os.environ.get("NAVIGATOR_EFFORT", "medium")

# Only the current generation accepts output_config.effort and adaptive
# thinking; Haiku 4.5 and older reject them with a 400. Keep this list in sync
# if you point NAVIGATOR_MODEL at something older.
EFFORT_MODELS = ("claude-opus-5", "claude-opus-4-", "claude-fable-5",
                 "claude-sonnet-5", "claude-sonnet-4-6", "claude-mythos-5")

MAX_CANDIDATES = 80
DESC_CHARS = 320

SYSTEM = """You rank university course sections for a New College student at \
the University of Alabama who is designing their own major.

You will be given:
  - the requirement buckets the student still has outstanding
  - a short interest phrase they typed
  - a numbered list of REAL sections offered this term, each with a CRN

Rank the sections by how well they serve the student, weighing two things:
  1. whether the section closes one of their outstanding requirements
  2. how well the course actually fits the interest phrase

A section that does BOTH must rank above one that does only one of them.

Hard rules:
  - Return ONLY CRNs from the list you were given. Never invent a course, a CRN,
    or a section. If nothing fits the phrase, rank on requirements alone.
  - Do not drop candidates for being a poor fit; rank them lower instead.
  - A section marked TOPIC-ROTATES has a generic catalog description, so you
    cannot tell what it is about. Still rank it on what it closes, and say in
    the reason that the topic varies and the advisor should confirm.
  - Each reason is ONE short sentence, under 20 words, addressed to the student.
    Say what it closes and why it fits. Never claim a course is offered at a
    time or place that is not in the data given."""


def available():
    """True when an import and a credential are both present."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.path.isdir(os.path.expanduser("~/.config/anthropic"))
    )


def _supports_effort(model):
    return any(model.startswith(p) for p in EFFORT_MODELS)


def build_prompt(results, phrase, outstanding):
    """Build the user turn. Public catalog text + the phrase only.

    Deliberately excludes every student identifier -- the model needs the
    requirement names to rank, not who the person is.
    """
    open_names = sorted({
        b["name"] for r in outstanding if not r["satisfied"] for b in r["buckets"]
    })

    lines = [
        "Outstanding requirement buckets: "
        + (", ".join(open_names) if open_names else "none"),
        'Interest phrase: "{}"'.format(phrase),
        "",
        "Sections offered this term:",
    ]
    for r in results:
        o = r["offering"]
        closes = ", ".join(b["name"] for b in r["buckets_closed"]) or "nothing outstanding"
        desc = (o.get("description") or "").strip()
        if len(desc) > DESC_CHARS:
            desc = desc[:DESC_CHARS].rsplit(" ", 1)[0] + "..."
        flag = " [TOPIC-ROTATES]" if r["flag"] == "topic_uncertain" else ""
        lines.append(
            "- CRN {crn}{flag} | {subj} {num} {title} | closes: {closes}\n"
            "  {desc}".format(
                crn=o["crn"], flag=flag, subj=o["subject"], num=o["course_number"],
                title=o["title"], closes=closes, desc=desc or "(no description available)")
        )
    return "\n".join(lines)


SCHEMA = {
    "type": "object",
    "properties": {
        "ranked": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "crn": {"type": "string",
                            "description": "A CRN copied exactly from the input list."},
                    "reason": {"type": "string",
                               "description": "One sentence under 20 words, to the student."},
                },
                "required": ["crn", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ranked"],
    "additionalProperties": False,
}


def _validate(ranked, results):
    """Keep only CRNs that were in the input. This is the F-26 / D-16 guard.

    Returns (ordered results, number of invented CRNs dropped). Any candidate
    the model omitted is appended afterwards in its original order, so a section
    can never vanish just because the model forgot it.
    """
    by_crn = {r["offering"]["crn"]: r for r in results}
    out, seen, dropped = [], set(), 0
    for item in ranked:
        crn = str(item.get("crn", "")).strip()
        if crn in by_crn and crn not in seen:
            r = by_crn[crn]
            reason = (item.get("reason") or "").strip()
            if reason:
                r = dict(r)
                r["reason"] = reason
                r["reason_source"] = "llm"
            out.append(r)
            seen.add(crn)
        else:
            dropped += 1
    for r in results:                       # anything the model left out
        if r["offering"]["crn"] not in seen:
            out.append(r)
    return out, dropped


def rerank(results, phrase, outstanding, model=None, limit=MAX_CANDIDATES):
    """Reorder `results` with Claude. Raises on API failure; caller falls back.

    Returns (results, meta). meta carries what actually happened so the UI and
    the write-up can show it rather than assert it.
    """
    import anthropic

    model = model or MODEL
    candidates = results[:limit]
    if not candidates:
        return results, {"ranker": "llm", "reranked": 0, "dropped": 0}

    kwargs = {
        "model": model,
        "max_tokens": 8000,
        "system": SYSTEM,
        "messages": [{"role": "user",
                      "content": build_prompt(candidates, phrase, outstanding)}],
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
    }
    if _supports_effort(model):
        kwargs["output_config"]["effort"] = EFFORT
        kwargs["thinking"] = {"type": "adaptive"}

    client = anthropic.Anthropic()
    response = client.messages.create(**kwargs)

    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("model declined to rank: {}".format(
            getattr(response, "stop_details", None)))

    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)
    ordered, dropped = _validate(data.get("ranked", []), candidates)

    usage = getattr(response, "usage", None)
    return ordered + results[limit:], {
        "ranker": "llm",
        "model": model,
        "reranked": len(ordered),
        "dropped": dropped,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
