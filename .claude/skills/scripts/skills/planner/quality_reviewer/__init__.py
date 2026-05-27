"""Quality-reviewer scripts for the planner skill.

Decompose/verify modules dispatched by orchestrator/planner.py
(plan-design / plan-code / plan-docs phases):
- plan_design_qr_decompose.py / plan_design_qr_verify.py
- plan_code_qr_decompose.py   / plan_code_qr_verify.py
- plan_docs_qr_decompose.py   / plan_docs_qr_verify.py

Decompose-as-entrypoint modules dispatched by orchestrator/executor.py
(impl phases; executor uses single-script dispatch — decompose is the
entrypoint and emits guidance inline):
- impl_code_qr_decompose.py / impl_code_qr_verify.py
- impl_docs_qr_decompose.py / impl_docs_qr_verify.py
- exec_reconcile.py (reconciliation step)

Shared:
- qr_verify_base.py: VerifyBase class (item loading, step routing,
  CLI dispatch) inherited by per-phase QR verify scripts.
- prompts/decompose.py: Shared decompose utilities + prompt fragments
  (`dispatch_step`, `write_qr_state`, atomicity/coverage prompts).
"""
