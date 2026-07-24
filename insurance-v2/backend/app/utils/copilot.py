"""
Insurance Copilot -- deliberately NOT an LLM/agent-framework based system,
per the brief ("no unnecessary LangChain or Agent Framework"). It answers
an agent's question by matching keywords against the sections of
`claim.ai_analysis` (fraud, coverage, policy_eligibility, classification,
damage_detection, decision) and returning the relevant section(s)
verbatim. This makes it structurally impossible to hallucinate: the
answer is always literally a piece of data already computed for this
claim, never a generated guess.
"""
import re

SECTION_KEYWORDS = {
    "fraud": ["fraud", "suspicious", "risk"],
    "coverage": ["coverage", "payable", "payout", "deduct", "amount"],
    "policy_eligibility": ["eligible", "eligibility", "waiting period", "clause", "cover"],
    "classification": ["classify", "classification", "type", "category", "triage"],
    "damage_detection": ["damage", "vehicle", "photo", "severity"],
    "decision": ["decision", "recommend", "approve", "reject", "escalate"],
    "document_quality": ["document", "documents", "missing", "blurry", "quality"],
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def ask_copilot(question: str, ai_analysis: dict) -> dict:
    question_tokens = _tokenize(question)
    matched_sections = []

    for section, keywords in SECTION_KEYWORDS.items():
        if section not in ai_analysis:
            continue
        keyword_tokens = set()
        for kw in keywords:
            keyword_tokens.update(_tokenize(kw))
        if question_tokens & keyword_tokens:
            matched_sections.append(section)

    if not matched_sections:
        # No keyword match -- fall back to whatever sections exist rather
        # than returning nothing.
        matched_sections = list(ai_analysis.keys())

    if not matched_sections:
        return {"answer": "No AI analysis has been run for this claim yet.", "sources": []}

    lines = []
    for section in matched_sections:
        lines.append(f"[{section}] {ai_analysis[section]}")

    return {"answer": "\n\n".join(lines), "sources": matched_sections}
