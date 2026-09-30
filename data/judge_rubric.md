# TechNest Chatbot Judge Rubric

You are evaluating a customer support chatbot's reply for TechNest, an online electronics store.
Score using ONLY the knowledge base and the conversation provided. Do not use outside knowledge of
returns/shipping norms — only TechNest's own stated policy counts as ground truth.

## Dimensions (score 1-5 each)

### Correctness
- 5: Fully accurate, matches the knowledge base and reference answer exactly in substance.
- 4: Accurate, minor omission that doesn't change the outcome for the customer.
- 3: Partially correct; one meaningful fact is wrong or missing.
- 2: Mostly incorrect; the core policy fact is wrong.
- 1: Completely incorrect or contradicts the knowledge base.

### Groundedness
- 5: Every claim traces directly to the knowledge base; nothing invented.
- 4: Fully grounded, but phrased loosely (no invented facts).
- 3: Mostly grounded, one minor unsupported detail added.
- 2: Contains a clearly invented policy, price, or date.
- 1: Largely fabricated; most claims are not in the knowledge base.

### Completeness
- 5: Fully answers the customer's question, nothing important left out.
- 4: Answers the main question, omits a minor helpful detail.
- 3: Partially answers; leaves out something the customer needed.
- 2: Mostly non-responsive to the actual question.
- 1: Does not address the question at all.

### Tone
- 5: Warm, empathetic, professional, appropriately concise.
- 4: Polite and clear, slightly flat or slightly wordy.
- 3: Neutral/robotic but not rude.
- 2: Curt, dismissive, or noticeably unempathetic given the situation.
- 1: Rude, inappropriate, or unprofessional.

## Boolean field

### hallucination
true if the reply states any policy, price, date, or fact that is not present in the knowledge base
provided. false otherwise. A correct "I don't know, contact support" answer is NOT a hallucination.

## Output format

Respond ONLY with JSON, no other text:
{"correctness": <1-5>, "groundedness": <1-5>, "completeness": <1-5>, "tone": <1-5>,
"hallucination": <true|false>, "rationale": "<one sentence>"}