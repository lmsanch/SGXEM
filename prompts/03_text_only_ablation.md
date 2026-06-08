# Prompt 3 — Text-Only Ablation (empirical gatekeeper)

**When to use:** the FINAL gate. Run this as if it were the competing text-only system
(GraphRAG / KET-RAG / plain text RAG). Give the model the question and ALL text sources, but
NOT the non-text artifact. If it answers correctly, the question has a real text shortcut and
must be cut or hardened — no matter what Prompts 1 and 2 said.

**This is the number that defends your whole benchmark.** When a reviewer asks "did you rig a
test only your tool can pass?", your answer is: "every shipped question was verified
unanswerable by a strong text-only model given all text evidence — here is the ablation log."

**Run it like the real baseline:** same model you'll cite as the text-only competitor, same
retrieval budget. Record the raw output verbatim into the ablation log.

---

## SYSTEM

You are a retrieval-augmented question-answering system. You have access to a corpus of TEXT
documents only. Answer the question using the provided text. If the text does not contain
enough information to determine the answer, respond exactly: "INSUFFICIENT EVIDENCE".
Do not guess. Do not use outside world knowledge to fill gaps.

## USER

QUESTION: {paste question}

TEXT CORPUS:
{paste every text source a solver could retrieve — include distractors}

## OUTPUT

<your answer, or "INSUFFICIENT EVIDENCE">

---

## Scoring (you, the human, record this)

| Field | Value |
|---|---|
| ablation_answer | <model output> |
| correct? | yes / no |
| disposition | if correct → DISCARD or ADD_DISTRACTORS; if "INSUFFICIENT EVIDENCE" or wrong → KEEP |

> A question only ships if the text-only ablation returns "INSUFFICIENT EVIDENCE" (or a wrong
> answer). That is the operational definition of "the non-text hop is genuinely necessary."
