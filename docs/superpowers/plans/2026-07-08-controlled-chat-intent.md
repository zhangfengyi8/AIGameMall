# Controlled Chat Intent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a controlled conversation intent layer so non-product chat does not trigger stale account recommendations or forced shopping guidance.

**Architecture:** Add a small rules-based intent classifier before `requirement_intake`. Only product-buying or valid follow-up messages enter the existing search/recommendation pipeline; identity, general chat, not-buying, unsafe, and unclear messages return controlled replies with empty recommendations.

**Tech Stack:** Python, pytest, existing `services/agent-orchestrator` modules.

---

### Task 1: Intent Classifier

**Files:**
- Create: `services/agent-orchestrator/app/skills/conversation_intent.py`
- Test: `services/agent-orchestrator/tests/test_conversation_intent.py`

- [ ] Write tests for assistant identity, not-buying, unsafe requests, product requests, contextual numeric follow-up, and standalone numeric input.
- [ ] Implement `classify_conversation_intent(user_message, history)` returning a dictionary with `intent`, `reply`, and `should_search`.
- [ ] Keep replies short and controlled; do not call a general LLM for off-domain chat.

### Task 2: Agent Routing

**Files:**
- Modify: `services/agent-orchestrator/app/agent.py`
- Test: `services/agent-orchestrator/tests/test_agent_intent_routing.py`

- [ ] Write async tests that mock LLM/search dependencies and assert non-product inputs return empty recommendations.
- [ ] Call `classify_conversation_intent` before `rule_intake` in both normal and stream paths.
- [ ] Ensure `buy_account` and valid contextual follow-ups continue into existing recommendation flow.

### Task 3: Documentation Progress

**Files:**
- Modify: `docs/PROGRESS.md`

- [ ] Add a completed progress item under Agent orchestration for controlled non-product chat routing.
- [ ] Run focused tests for new classifier and routing behavior.
