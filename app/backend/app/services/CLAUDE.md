# services/

Business logic layer. Orchestrates tools, rules, and data access; no HTTP concerns.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `auth.py` | Password hashing, JWT creation and verification | Changing auth logic |
| `draft_render.py` | LLM draft generation — invokes agent, applies clinical register rules | Changing AI-generated content |
| `final_report.py` | Assembles and finalises the complete report payload | Changing how the full report is constructed |
| `intake.py` | PDF intake — LLM extraction of structured case from uploaded report | Changing patient report intake |
| `lookup_service.py` | Variant lookup orchestration — runs tools in parallel, calls rules engine | Changing Layer 1 pipeline |
| `recommendation.py` | Generates tiered clinical recommendations (HIGH/MODERATE/ROUTINE) | Changing recommendation logic |
| `report_draft.py` | Composes the Layer 2 draft from intake + lookup results | Changing patient report draft logic |
| `run_chat.py` | Manages chat sessions within a run | Changing run-chat behaviour |
| `search.py` | Search service — delegates to search_index and search_answer | Changing search orchestration |
| `search_answer.py` | Generates LLM-powered search answers | Changing search AI responses |
| `search_index.py` | Builds and updates the search index | Changing indexing strategy |
| `variant_decoder.py` | HGVS plain-language decoder — pure regex, no LLM | Changing the plain-language section |
| `workflow.py` | Top-level pipeline workflow — sequences all phases | Changing the overall pipeline order |
