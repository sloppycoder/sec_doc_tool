# ruff: noqa: RUF001

import re

import spacy

MANAGER_JOB_PATTERNS = [
    r"\bportfolio manager\b",
    r"\bfund manager\b",
    r"\bindependent trustee\b",
    r"\binterested person\b",
]
MANAGER_REGEX = re.compile("|".join(MANAGER_JOB_PATTERNS), re.I)

TRUSTEE_JOB_PATTERNS = [
    r"\bindependent trustee\b",
    r"\binterested person\b",
    r"\bchairman of board\b",
    r"\bchairman of .* committee\b",
]
TRUSTEE_REGEX = re.compile("|".join(TRUSTEE_JOB_PATTERNS), re.I)


nlp = spacy.load("en_core_web_sm")


DOLLAR_RANGES = [
    r"\$?\s*10,?000",
    r"\$?\s*50,?000",
    r"\$?\s*100,?000",
    r"\$?\s*500,?000",
    r"\$?\s*1,?000,?000",
    r"over\s+\$?\s*[0-9,]+",
    r"\$?\s*[0-9,]+\s*[-–]\s*\$?\s*[0-9,]+",
]
RANGE_REGEX = re.compile("|".join(f"(?:{p})" for p in DOLLAR_RANGES), re.I)


def _unique_person_entities(doc) -> set[str]:
    """
    Return a *set* of unique PERSON strings, lightly filtered to
    drop obvious tickers (e.g. 'IBM') or 1-char tokens.
    """
    names = set()
    for ent in doc.ents:
        if ent.label_ != "PERSON":
            continue
        name = ent.text.strip("|,.;:").strip()
        if len(name) < 2:
            continue
        # skip ALL-CAPS ≤5 letters (often ticker symbols)
        if name.isupper() and len(name) <= 5:
            continue
        names.add(name.lower())
    return names


def _unique_money_entities(doc) -> set[str]:
    """
    Return a *set* of unique MONEY entity strings.
    """
    monies = set()
    for ent in doc.ents:
        if ent.label_ == "MONEY":
            monies.add(ent.text.strip())
    return monies


def tag_with_ner(text: str) -> dict:
    doc = nlp(text)
    persons = _unique_person_entities(doc)
    money = _unique_money_entities(doc)
    tags = {
        "manager_count": len(MANAGER_REGEX.findall(text)),
        "trustee_count": len(TRUSTEE_REGEX.findall(text)),
        "person_unique": len(persons),
        "money_count": len(money),
        "range_count": len(RANGE_REGEX.findall(text)),
        "none_count": text.lower().count("none"),
    }
    return tags
