Create two files for a Python project called technest-eval.

1) docs/PROJECT_CONTEXT.md containing:
- Goal: an LLM evaluation framework for a customer support chatbot for "TechNest", a fictional online electronics store. It tests one LLM with 60 test cases, computes quantitative metrics, identifies failure patterns, and supports a final technical report.
- The chatbot receives a customer conversation and must return ONLY JSON: {"action": "answer|clarify|escalate|refuse", "reply": "<text>"}.
- The chatbot is grounded in data/knowledge_base.md (returns 30 days, shipping, warranty, payments, order changes, mandatory escalation rules, support hours, privacy).
- Test case schema (JSON list): id, category (standard_faq | multi_turn | out_of_scope | escalation | ambiguous | adversarial | robustness), difficulty (easy|medium|hard), conversation (list of {role, content}), expected_action, must_include (list of strings), must_not_include (list of strings), reference_answer, kb_section, notes.
- Pipeline: validate cases -> run each case N=3 times at temperature 0 -> save raw JSONL -> score with rules and an LLM judge -> compute metrics -> tag failures -> make charts -> generate report tables.
- Metrics: action accuracy; precision/recall/F1 for escalate and refuse; must_include pass rate; must_not_include violation rate; JSON format compliance; hallucination rate (judge); prompt-injection success rate; consistency across runs (% of cases where all runs agree on action); mean latency; token cost; per-category breakdown; judge-vs-human agreement (Cohen's kappa).
- Failure categories: hallucinated_policy, over_helpfulness, missed_escalation, over_escalation, injection_compliance, prompt_leakage, context_loss, tone_failure, boundary_error, format_violation.
- Coding rules: Python 3.11, type hints, Pydantic v2, pandas, matplotlib, pytest, no hardcoded API keys, all settings in config.yaml, everything reproducible with fixed seeds/temperature.

2) .github/copilot-instructions.md telling Copilot to always read docs/PROJECT_CONTEXT.md before generating code, keep functions small and documented, and never invent test data or results.