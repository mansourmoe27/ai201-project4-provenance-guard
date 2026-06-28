LABELS = {
    "likely_ai": "This content shows strong signs of being AI-generated. This label is based on automated signals and may be appealed by the creator.",
    "uncertain": "We could not confidently determine whether this content was human-written or AI-generated. This label is uncertain and should not be treated as proof.",
    "likely_human": "This content appears likely to be human-written based on the available signals. This is not a guarantee, but the system found low evidence of AI generation.",
}


def attribution_from_score(score: float) -> str:
    if score >= 0.70:
        return "likely_ai"
    if score >= 0.40:
        return "uncertain"
    return "likely_human"


def label_for_attribution(attribution: str) -> str:
    return LABELS.get(attribution, LABELS["uncertain"])