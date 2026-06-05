# Question Sources and Verification Policy

## What is loaded automatically

| Source | Status | Why |
|--------|--------|-----|
| **OpenSAT JSON** (`opensat_community`) | Loaded | Structured digital SAT MCQs with 4 choices, explanations, and College Board-style domains. Validated before insert. |
| **College Board Educator Question Bank** | Manual CSV only | Official, but PDF export only — no public API. |
| **Reddit r/SAT megathreads** | Not loaded | Memory reconstructions, debated answers, incomplete stems. |
| **Discord / Telegram "leaks"** | Not loaded | Often scams or recycled Bluebook content; violates College Board security rules. |
| **Tutor blogs compiling Reddit posts** | Not loaded | Transcribed live-test items; not licensed for redistribution; single-source recap. |

## Forum verification gates (all must pass)

A forum-derived question is imported only if:

1. Four distinct answer choices are present.
2. The keyed answer appears in the choices.
3. Explanation is at least 50 characters and justifies the answer.
4. **At least two independent public sources agree** on the answer (forum posts alone do not count).
5. Provenance is not `reddit_memory`, `discord`, `telegram`, `leak`, or `transcribed_live_test`.
6. It is not a duplicate of an existing bank row.

As of the latest review, **zero forum candidates passed** these gates.

## Recommended official practice for students

- College Board **Bluebook** app (official practice tests)
- College Board **Educator Question Bank** (export PDF → convert → Admin CSV import)
- Khan Academy Official SAT Practice

## Reload command

```bash
python scripts/reload_exam_questions.py
```
