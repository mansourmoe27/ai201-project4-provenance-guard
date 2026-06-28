# Provenance Guard

## Project Overview

Provenance Guard is a Flask backend system for a creative writing platform. It analyzes submitted text and estimates whether the content appears AI-generated, human-written, or uncertain.

The goal is not to make perfect AI-detection claims. Instead, the system gives readers a clear transparency label, gives creators a confidence score, and provides an appeals process when a creator believes their work was misclassified.

## Architecture

### Submission Flow

```text
POST /submit
→ validate text and creator_id
→ run Groq LLM signal
→ run stylometric heuristic signal
→ combine scores
→ assign attribution category
→ generate transparency label
→ write audit log entry
→ return JSON response
```

### Appeal Flow

```text
POST /appeal
→ receive content_id and creator reasoning
→ find original classification
→ update status to under_review
→ write appeal entry to audit log
→ return confirmation response
```

## API Endpoints

### POST /submit

Accepts a text submission and returns an attribution result.

Required JSON:

```json
{
  "text": "Creative writing text here",
  "creator_id": "test-user-1"
}
```

Example response:

```json
{
  "content_id": "1750aa3a-ff74-41ae-945f-cff968affa03",
  "creator_id": "test-user-1",
  "attribution": "uncertain",
  "confidence": 0.6924,
  "label": "We could not confidently determine whether this content was human-written or AI-generated. This label is uncertain and should not be treated as proof.",
  "signals": {
    "llm_score": 0.8,
    "stylometric_score": 0.4926
  },
  "status": "classified"
}
```

### POST /appeal

Allows a creator to contest a classification.

Required JSON:

```json
{
  "content_id": "1750aa3a-ff74-41ae-945f-cff968affa03",
  "creator_reasoning": "I wrote this myself from personal experience."
}
```

Example response:

```json
{
  "content_id": "1750aa3a-ff74-41ae-945f-cff968affa03",
  "creator_id": "test-user-1",
  "message": "Appeal received and logged for review.",
  "status": "under_review"
}
```

### GET /log

Returns recent structured audit log entries.

## Detection Signals

The system uses two detection signals.

### Signal 1: Groq LLM Attribution Score

This signal uses Groq's `llama-3.3-70b-versatile` model to estimate whether the text appears AI-generated or human-written.

It captures broad writing qualities such as tone, polish, generic phrasing, naturalness, and whether the writing sounds overly uniform.

What it misses: polished human writing may be mistaken for AI-generated writing. Heavily edited AI writing may also appear more human than it really is.

### Signal 2: Stylometric Heuristic Score

This signal uses pure Python heuristics to measure structural features of the writing, including:

* sentence length variance
* vocabulary diversity
* punctuation density
* repetition and uniformity

It captures measurable writing patterns that may differ between human and AI-generated text.

What it misses: poetry, formal essays, and experimental writing may have unusual structure that confuses the heuristic score.

## Confidence Scoring

Each signal returns a score from `0.0` to `1.0`.

* `0.0` means strongly human-written
* `1.0` means strongly AI-generated

The combined score is calculated using a weighted average:

```text
combined_score = (0.65 * llm_score) + (0.35 * stylometric_score)
```

I weighted the LLM signal more heavily because it captures meaning, tone, and writing style more broadly. The stylometric score is still useful, but it is more likely to misread unusual human writing.

## Attribution Thresholds

| Combined Score | Attribution  |
| -------------: | ------------ |
|    0.70 – 1.00 | likely_ai    |
|    0.40 – 0.69 | uncertain    |
|    0.00 – 0.39 | likely_human |

A score near `0.50` means the system does not have enough evidence to make a strong claim. This matters because false positives can harm creators by wrongly suggesting their work was AI-generated.

## Confidence Score Examples

### Higher-confidence AI-like example

Input:

```text
Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment.
```

Output:

```json
{
  "llm_score": 0.8,
  "stylometric_score": 0.4926,
  "confidence": 0.6924,
  "attribution": "uncertain"
}
```

This example landed close to the `likely_ai` threshold, but the final label remained uncertain because the combined score was just below `0.70`.

### Lower-confidence human-like example

Input:

```text
ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after.
```

Expected behavior:

This type of writing should receive a lower score because it has informal phrasing, uneven rhythm, personal detail, and casual punctuation.

## Transparency Labels

| Attribution  | Label Text                                                                                                                                                     |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| likely_ai    | "This content shows strong signs of being AI-generated. This label is based on automated signals and may be appealed by the creator."                          |
| uncertain    | "We could not confidently determine whether this content was human-written or AI-generated. This label is uncertain and should not be treated as proof."       |
| likely_human | "This content appears likely to be human-written based on the available signals. This is not a guarantee, but the system found low evidence of AI generation." |

The labels use plain language so that non-technical readers understand the result without needing to know how the model works.

## Appeals Workflow

Creators can submit an appeal using `POST /appeal`.

The appeal must include:

* `content_id`
* `creator_reasoning`

When an appeal is submitted, the system:

1. Looks up the original classification.
2. Stores the creator's explanation.
3. Updates the status to `under_review`.
4. Writes the appeal to the audit log.
5. Returns a confirmation response.

Example appeal log entry:

```json
{
  "appeal_reasoning": "I wrote this myself from personal experience. My writing may look polished because I edited it carefully before submitting.",
  "content_id": "1750aa3a-ff74-41ae-945f-cff968affa03",
  "creator_id": "test-user-1",
  "event_type": "appeal",
  "original_attribution": "uncertain",
  "original_confidence": 0.6924,
  "status": "under_review"
}
```

## Rate Limiting

The `/submit` endpoint uses the following rate limit:

```text
10 submissions per minute
100 submissions per day
```

I chose this because a normal creator on a writing platform is unlikely to submit more than 10 pieces in one minute. This limit still allows normal use while blocking scripts or spam attempts.

Rate limit test output:

```text
200
200
200
200
200
200
200
200
200
200
429
429
```

The `429` responses show that the rate limiter successfully blocked requests after the limit was reached.

## Audit Log

The system writes structured JSON audit logs for both classifications and appeals.

Each classification entry includes:

* timestamp
* event type
* content ID
* creator ID
* attribution result
* confidence score
* LLM score
* stylometric score
* transparency label
* status

Example log entries:

```json
{
  "attribution": "uncertain",
  "confidence": 0.6924,
  "content_id": "1750aa3a-ff74-41ae-945f-cff968affa03",
  "creator_id": "test-user-1",
  "event_type": "classification",
  "llm_score": 0.8,
  "status": "classified",
  "stylometric_score": 0.4926,
  "timestamp": "2026-06-28T02:03:29.496657+00:00"
}
```

```json
{
  "appeal_reasoning": "I wrote this myself from personal experience. My writing may look polished because I edited it carefully before submitting.",
  "content_id": "1750aa3a-ff74-41ae-945f-cff968affa03",
  "creator_id": "test-user-1",
  "event_type": "appeal",
  "original_attribution": "uncertain",
  "original_confidence": 0.6924,
  "status": "under_review",
  "timestamp": "2026-06-28T02:54:30.910158+00:00"
}
```

## Known Limitations

The system may misclassify formal human writing as AI-generated because both the LLM signal and the stylometric signal may interpret polished structure, balanced sentences, and formal vocabulary as AI-like.

Poetry and song lyrics are another weak case. Repetition, short lines, and unusual punctuation are normal in poetry, but the stylometric signal may treat those patterns as suspicious.

The system is also not a proof system. It should be treated as a transparency and review tool, not as a final authority on whether a creator used AI.

## Spec Reflection

The planning spec helped me design the system before writing code. Defining the two signals, confidence thresholds, transparency labels, and appeal flow first made the implementation easier because each file had a clear job.

One way the implementation diverged from the original plan is that the first AI-like test case produced an `uncertain` label instead of `likely_ai`. The score was close to the threshold, but not high enough. I kept this behavior because it reflects the project's safety principle: uncertain cases should not be over-labeled as AI-generated.

## AI Usage

I used ChatGPT in several parts of the project.

1. I asked ChatGPT to help turn the project rubric into an implementation plan. The output gave me a milestone-based checklist, but I revised it to focus first on the required 25 points before considering stretch features.

2. I used ChatGPT to help design the Flask file structure and generate starter code for the API endpoints, detection functions, labels, and audit log. I reviewed and tested the generated code manually, especially the `/submit`, `/appeal`, and `/log` endpoints.

3. I used ChatGPT to help debug local development issues, including the `.env` setup, Groq fallback score, and port 5000 conflict. I verified the fixes myself by running curl tests and checking the JSON responses.

## Running the Project

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```text
GROQ_API_KEY=your_key_here
```

Run the Flask app:

```bash
python app.py
```

Test the API:

```bash
curl -s http://127.0.0.1:5000/ | python -m json.tool
```

## Files

* `app.py` — Flask routes for submit, appeal, and log
* `detector.py` — Groq and stylometric detection signals
* `labels.py` — attribution thresholds and transparency labels
* `audit.py` — structured JSON audit logging
* `planning.md` — system design, architecture, and implementation plan
* `requirements.txt` — project dependencies
