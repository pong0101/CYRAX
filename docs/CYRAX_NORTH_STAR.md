# CYRAX North Star

## Ultimate Goal

CYRAX aims to become a **local-first personal autonomous intelligence**: a long-lived AI system that can understand the owner's goals, maintain durable project knowledge, distinguish current reality from stale memory, plan multi-step work, execute through controlled local tools, verify results, and learn from outcomes — while keeping the owner in control.

> **Perceive → Remember → Verify → Reason → Plan → Act → Verify → Learn**

This loop is the core product. New capabilities should strengthen this loop, not merely make the model answer more questions.

## Product Definition

CYRAX is not primarily an LLM wrapper, chatbot, or collection of tools. It is a **cognitive orchestration system** around local models, memory, evidence, planning, and execution.

### Non-negotiable principles

1. **Local-first** — private project knowledge and core operation should remain local whenever practical.
2. **Truth-first** — current authoritative evidence outranks stale memory or model knowledge.
3. **Evidence-backed** — important claims should be traceable to runtime, tools, project files, user statements, or memory.
4. **Persistent context** — durable knowledge survives individual conversations and remains human-readable.
5. **Controlled autonomy** — CYRAX may act, but destructive, external, or consequential actions require explicit approval boundaries.
6. **Verifiable execution** — completing an action is not enough; CYRAX should check whether the intended result actually happened.
7. **Debuggability** — deterministic components, logs, tests, and clear source attribution take priority over opaque cleverness.

## Target End State

```text
Owner / Goals
      ↓
CYRAX Cognitive Core
      ├── Perception / machine reality
      ├── Memory / project knowledge
      ├── Truth & evidence policy
      ├── Reasoning
      ├── Planning
      ├── Tool execution
      └── Verification / feedback
              ↓
       Learning / memory update
              └──────────→ next task
```

## Roadmap

### Phase 1 — Reliable Agent Core
**Status: substantially complete**

- Local Ollama/Qwen runtime
- Native tool bridge
- Live machine-state routing
- File read/write tools
- Conservative automatic memory policy
- Semantic memory retrieval
- Explicit truth-authority policy
- Integration and routing verification

**Exit criterion:** runtime facts, tools, memory, and routing behave deterministically enough to debug.

### Phase 2 — Truth-Aware Second Brain
**Next priority**

- Add memory metadata: source, timestamp, confidence, type, and provenance.
- Attach evidence to important memories and answers.
- Detect contradictions between live state, project files, user statements, and memory.
- Mark stale evidence instead of silently overwriting history.
- Add memory promotion: repeated/validated observations can become durable knowledge.
- Add duplicate, stale, and contradiction cleanup.
- Build tests for temporal and source-priority behavior.

**Exit criterion:** CYRAX can explain not only *what* it believes, but *why*, *from which evidence*, and *how current that evidence is*.

### Phase 3 — Planning & Reliable Task Execution

- Introduce explicit task/plan objects.
- Break goals into observable steps and checkpoints.
- Track dependencies, progress, failures, and retries.
- Verify tool results against expected outcomes.
- Add rollback/recovery where practical.
- Require approval for destructive or consequential actions.
- Persist useful task state without polluting long-term memory.

**Exit criterion:** CYRAX can complete a bounded multi-step task end-to-end and provide an evidence-backed result report.

### Phase 4 — Multimodal & Computer Agency

- Vision for screenshots and application state.
- Browser/application interaction through controlled tools.
- Better codebase understanding and repository operations.
- Optional voice interface.
- Hardware/local-device integrations where useful.

**Exit criterion:** CYRAX can perceive and operate across the owner's real digital workspace while retaining safety and verification boundaries.

### Phase 5 — Personal Autonomous Intelligence

- Long-running goals and projects.
- Proactive monitoring with explicit user-defined boundaries.
- Continuous project-state synthesis.
- Learned preferences and workflows with provenance.
- Self-diagnosis and maintenance of its own agent subsystems.
- Capability discovery without uncontrolled self-modification.

**Exit criterion:** CYRAX reliably behaves like a persistent technical partner rather than a turn-by-turn assistant.

## Priority Order

When choosing the next feature, use this order:

1. Correctness
2. Observability
3. Truth and evidence
4. Memory quality
5. Safe action
6. Planning
7. New capabilities

A flashy capability that makes CYRAX less reliable is a regression, not progress.

## Immediate Execution Plan

1. Implement structured memory metadata and provenance.
2. Add evidence objects to memory retrieval and answer construction.
3. Add contradiction/staleness handling to the runtime path.
4. Add focused verification scripts for memory provenance and temporal conflicts.
5. Integrate the new memory layer without breaking the existing 10/10 integration, 10/10 routing, 8/8 truth-policy, and 7/7 truth-runtime verification suites.
6. Only after the above is green, begin the task-planning subsystem.

## Definition of Success

The project succeeds when the owner can give CYRAX a meaningful goal and trust it to:

- understand the goal in context,
- retrieve the right long-term knowledge,
- inspect current reality instead of guessing,
- identify uncertainty and conflicting evidence,
- create a sensible plan,
- execute approved actions,
- verify the result,
- recover from failures when possible,
- explain what it did and why,
- and retain only useful, well-sourced knowledge for future work.

The final measure is therefore not model benchmark score. It is **trustworthy, useful autonomy under owner control**.
