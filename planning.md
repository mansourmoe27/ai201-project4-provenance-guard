# Provenance Guard Planning

## Project Overview

Provenance Guard is a backend system for a creative writing platform. Its purpose is to analyze submitted text and estimate whether the writing appears AI-generated, human-written, or uncertain.

The goal is not to punish creators or make perfect AI detection claims. Instead, the system provides a transparency label, a confidence score, and an appeals process so creators can contest a decision if they believe their work was misclassified.

---

## Architecture

### Submission Flow

```text
User submits text
      |
      v
POST /submit
      |
      v
Input validation
      |
      v
Signal 1: Groq LLM attribution score
      |
      v
Signal 2: Stylometric heuristic score
      |
      v
Confidence scoring
      |
      v
Transparency label generation
      |
      v
Structured audit log
      |
      v
JSON response returned to user
```

### Appeal Flow

```text
Creator submits appeal
      |
      v
POST /appeal
      |
      v
Find original content_id
      |
      v
Capture creator reasoning
      |
      v
Update status to "under_review"
      |
      v
Write appeal event to audit log
      |
      v
Return appeal confirmation
```

The submission flow begins when a creator sends text to the `/submit` endpoint. The system validates the input, runs two separate detection signals, combines the scores into one confidence score, generates a plain-language transparency label, records the decision in the audit log, and returns a structured JSON response.

The appeal flow begins when a creator submits a `content_id` and a reason for contesting the classification. The system updates the content status to `under_review`, stores the appeal reasoning, writes the appeal event to the audit log, and returns a confirmation.

---

## API Endpoints

### POST /submit

Accepts a text submission for attribution analysis.

Required JSON fields:

```json
{
  "text": "The submitted creative writing text.",
  "creator_id": "creator-123"
}
```

Returns:

```json
{
  "content_id": "unique-id",
  "creator_id": "creator-123",
  "attribution": "likely_ai | uncertain | likely_human",
  "confidence": 0.82,
  "label": "Plain-language transparency label",
  "signals": {
    "llm_score": 0.86,
    "stylometric_score": 0.78
  },
  "status": "classified"
}
```

### POST /appeal

Accepts an appeal for a previous classification.

Required JSON fields:

```json
{
  "content_id": "existing-content-id",
  "creator_reasoning": "I wrote this myself..."
}
```

Returns:

```json
{
  "content_id": "existing-content-id",
  "status": "under_review",
  "message": "Appeal received and logged for review."
}
```

### GET /log

Returns recent structured audit log entries.

---

## Detection Signals

### Signal 1: Groq LLM Attribution Score

This signal uses Groq's `llama-3.3-70b-versatile` model to evaluate whether a piece of text reads as AI-generated or human-written.

It captures broad semantic and stylistic patterns such as generic phrasing, overly polished structure, repetitive transitions, lack of personal detail, and naturalness of voice.

Output:

```text
0.0 = strongly human-written
1.0 = strongly AI-generated
```

Why I chose it:

A large language model can evaluate writing holistically in a way that simple rules cannot. It can notice tone, flow, and general writing patterns.

Blind spots:

The LLM signal may misclassify polished human writing as AI-generated. It may also miss AI-generated writing that has been heavily edited to sound casual or personal.

---

### Signal 2: Stylometric Heuristic Score

This signal uses measurable writing features calculated directly from the text.

It checks:

* sentence length variance
* vocabulary diversity
* punctuation density
* repetition / uniformity

Output:

```text
0.0 = strongly human-written
1.0 = strongly AI-generated
```

Why I chose it:

AI writing often has more uniform sentence structure and smoother repetition, while human writing often has more variation, uneven pacing, slang, typos, and irregular punctuation.

Blind spots:

Stylometric heuristics can misclassify formal human writing, essays, professional writing, or poetry with repeated structure as AI-generated. They can also miss AI text that intentionally imitates casual writing.

---

## Confidence Scoring

Both signals return a score from 0.0 to 1.0, where higher means stronger evidence of AI generation.

The combined score will use a weighted average:

```text
combined_score = (0.65 * llm_score) + (0.35 * stylometric_score)
```

The LLM signal receives more weight because it captures meaning, tone, and overall writing style. The stylometric signal receives less weight because it is useful but more likely to misread unusual human writing.

---

## Uncertainty Thresholds

The system will map the combined score into three attribution categories:

| Combined Score | Attribution  |
| -------------: | ------------ |
|    0.70 – 1.00 | likely_ai    |
|    0.40 – 0.69 | uncertain    |
|    0.00 – 0.39 | likely_human |

A score around 0.50 means the system does not have enough evidence to make a strong attribution claim. This is important because false positives are harmful on creative platforms. Labeling a real human creator as AI-generated can damage trust and unfairly question their work.

---

## Transparency Label Design

The system will show one of three plain-language label variants.

| Attribution  | Exact Label Text                                                                                                                                               |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| likely_ai    | "This content shows strong signs of being AI-generated. This label is based on automated signals and may be appealed by the creator."                          |
| uncertain    | "We could not confidently determine whether this content was human-written or AI-generated. This label is uncertain and should not be treated as proof."       |
| likely_human | "This content appears likely to be human-written based on the available signals. This is not a guarantee, but the system found low evidence of AI generation." |

These labels avoid technical language and explain uncertainty clearly to non-technical readers.

---

## Appeals Workflow

Any creator whose content has been classified can submit an appeal.

The creator must provide:

* `content_id`
* `creator_reasoning`

When an appeal is received, the system will:

1. Look up the original content ID.
2. Record the creator's explanation.
3. Update the content status from `classified` to `under_review`.
4. Add an appeal event to the audit log.
5. Return a confirmation response.

A human reviewer would see the original text, original attribution, signal scores, confidence score, transparency label, and creator reasoning.

---

## Rate Limiting Plan

The `/submit` endpoint will use this limit:

```text
10 submissions per minute
100 submissions per day
```

Reasoning:

A normal creator on a writing platform is unlikely to submit more than 10 pieces in one minute. The limit still allows normal testing and legitimate use, but blocks scripts or attackers trying to flood the system with repeated submissions.

---

## Audit Log Design

Every classification and appeal will be written to a structured JSON audit log.

Each classification entry will include:

* timestamp
* event_type
* content_id
* creator_id
* attribution
* confidence
* llm_score
* stylometric_score
* transparency label
* status

Each appeal entry will include:

* timestamp
* event_type
* content_id
* creator_id
* appeal_reasoning
* status

Example classification log:

```json
{
  "timestamp": "2026-06-21T20:15:00Z",
  "event_type": "classification",
  "content_id": "abc-123",
  "creator_id": "creator-1",
  "attribution": "likely_ai",
  "confidence": 0.82,
  "llm_score": 0.86,
  "stylometric_score": 0.78,
  "status": "classified"
}
```

Example appeal log:

```json
{
  "timestamp": "2026-06-21T20:20:00Z",
  "event_type": "appeal",
  "content_id": "abc-123",
  "creator_id": "creator-1",
  "appeal_reasoning": "I wrote this myself from personal experience.",
  "status": "under_review"
}
```

---

## Anticipated Edge Cases

### Edge Case 1: Formal Human Writing

A human-written essay, academic paragraph, or professional blog post may be polished, balanced, and structured. The system may classify it as AI-generated because both the LLM and stylometric signal may see it as too smooth or uniform.

How I will handle it:

Formal writing that lands in the middle range should receive the uncertain label instead of a strong AI label. The appeals workflow also gives creators a way to contest false positives.

---

### Edge Case 2: Poetry or Repetitive Creative Writing

Poetry, song lyrics, or experimental writing may intentionally use repetition, short sentences, or unusual punctuation. The stylometric signal might mistake these patterns for AI-generated uniformity.

How I will handle it:

The LLM signal is weighted more heavily than the heuristic score, and the uncertain range helps avoid overconfident labels when the signals disagree.

---

### Edge Case 3: Edited AI Writing

AI-generated text that has been heavily edited by a human may include personal details, uneven structure, or casual phrasing. The system may score it as human-written even if AI was involved.

How I will handle it:

The transparency labels avoid absolute claims. The system only reports what the signals suggest, not a guaranteed truth.

---

## AI Tool Plan

### M3: Submission Endpoint and First Signal

I will provide the AI tool with:

* Detection Signals section
* Architecture diagram
* API endpoint plan

I will ask it to generate:

* Flask app skeleton
* POST `/submit` route
* Groq LLM signal function
* basic structured response

I will verify the output by:

* running the Flask server locally
* testing `/submit` with curl
* confirming the response includes `content_id`, `attribution`, `confidence`, `label`, and `signals`

---

### M4: Second Signal and Confidence Scoring

I will provide the AI tool with:

* Detection Signals section
* Confidence Scoring section
* Uncertainty Thresholds section
* Architecture diagram

I will ask it to generate:

* stylometric heuristic signal function
* combined confidence scoring function
* attribution threshold logic

I will verify the output by:

* testing clearly AI-generated writing
* testing clearly human-written writing
* testing borderline cases
* checking that different inputs produce noticeably different confidence scores

---

### M5: Production Layer

I will provide the AI tool with:

* Transparency Label Design section
* Appeals Workflow section
* Audit Log Design section
* Rate Limiting Plan
* Architecture diagram

I will ask it to generate:

* label generation function
* POST `/appeal` endpoint
* GET `/log` endpoint
* Flask-Limiter setup
* audit logging helper functions

I will verify the output by:

* submitting content
* submitting an appeal using the returned content ID
* checking that status becomes `under_review`
* checking that the audit log contains both classification and appeal entries
* testing rate limiting until a 429 response appears

```
```
