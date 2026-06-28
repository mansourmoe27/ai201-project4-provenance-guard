import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def groq_llm_score(text: str) -> float:
    """
    Returns a score from 0.0 to 1.0.
    0.0 = strongly human-written
    1.0 = strongly AI-generated
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        # Fallback for local testing if API key is missing.
        return 0.50

    client = Groq(api_key=api_key)

    prompt = f"""
You are an AI content provenance detector.

Analyze the text and estimate whether it appears AI-generated or human-written.

Return ONLY a decimal number between 0 and 1.

0 means strongly human-written.
1 means strongly AI-generated.

Text:
{text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        raw = response.choices[0].message.content.strip()
        match = re.search(r"0(?:\.\d+)?|1(?:\.0+)?", raw)
        if not match:
            return 0.50
        return clamp_score(float(match.group()))
    except Exception:
        return 0.50


def stylometric_score(text: str) -> float:
    """
    Heuristic score from 0.0 to 1.0.
    Higher score = more AI-like structural pattern.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"\b\w+\b", text.lower())

    if len(words) < 20:
        return 0.45

    sentence_lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences] or [len(words)]
    avg_sentence_len = sum(sentence_lengths) / len(sentence_lengths)

    if len(sentence_lengths) > 1:
        variance = sum((x - avg_sentence_len) ** 2 for x in sentence_lengths) / len(sentence_lengths)
    else:
        variance = 0

    unique_words = len(set(words))
    type_token_ratio = unique_words / len(words)

    punctuation_count = len(re.findall(r"[,:;!?]", text))
    punctuation_density = punctuation_count / max(len(words), 1)

    # AI-like writing often has moderate sentence lengths, lower variance,
    # lower punctuation irregularity, and less vocabulary surprise.
    uniformity_score = max(0.0, 1.0 - min(variance / 40, 1.0))
    sentence_score = 1.0 if 12 <= avg_sentence_len <= 28 else 0.45
    vocabulary_score = 1.0 - min(type_token_ratio, 1.0)
    punctuation_score = 1.0 - min(punctuation_density * 4, 1.0)

    final_score = (
        0.35 * uniformity_score
        + 0.25 * sentence_score
        + 0.25 * vocabulary_score
        + 0.15 * punctuation_score
    )

    return clamp_score(final_score)


def combined_confidence(llm_score: float, style_score: float) -> float:
    return clamp_score((0.65 * llm_score) + (0.35 * style_score))


def analyze_text(text: str) -> dict:
    llm = groq_llm_score(text)
    style = stylometric_score(text)
    combined = combined_confidence(llm, style)

    return {
        "llm_score": round(llm, 4),
        "stylometric_score": round(style, 4),
        "confidence": round(combined, 4),
    }