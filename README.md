# CYRAX

**CYRAX** is a local-first AI agent built around **Qwen3 + Ollama**, **Open Interpreter**, and **Obsidian** as a persistent second brain.

The project is designed to keep the agent practical, inspectable, and local: current machine facts come from live tools, durable knowledge lives in Obsidian, and the LLM is used for reasoning and language rather than being treated as the final authority on reality.

## Current Status

🚀 **Foundation complete — Runtime / Memory / Tools / Truth Policy are integrated.**

Current main model:

- **LLM:** `qwen3:8b`
- **Runtime:** Ollama
- **Semantic memory model:** `qwen3-embedding:0.6b`
- **Execution layer:** Open Interpreter
- **Long-term memory:** Obsidian Markdown vault

The current verification baseline is:

```text
Unicode Source       3/3 PASS
Truth Runtime        7/7 PASS
Truth Policy         8/8 PASS
Integration          10/10 PASS
Request Routing      10/10 PASS
--------------------------------
Total                38/38 PASS
```

## Vision

CYRAX is intended to become a dependable local AI agent that can:

- reason with a local LLM
- inspect the real state of the machine
- use narrow native tools instead of guessing
- execute approved actions
- remember durable project knowledge
- distinguish current reality from historical memory
- remain understandable and debuggable by its owner

## Architecture

```text
                         ┌──────────────────────┐
                         │        User          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Deterministic      │
                         │    Request Router    │
                         └──────────┬───────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
        LIVE / RUNTIME           MEMORY                 ACTION
             │                      │                      │
             ▼                      ▼                      ▼
       Native Tools          Obsidian Search        Native Tools
       Ollama / Files        + Memory Manager       / PowerShell
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                                    ▼
                              Qwen3:8b
                                    │
                                    ▼
                           Truth / Source Policy
                                    │
                                    ▼
                              Final Answer
```

### Source authority

When facts conflict, CYRAX uses an explicit deterministic authority order:

```text
live_tool
  > runtime
  > project_file
  > user_statement
  > memory
  > history
  > llm_knowledge
```

This means a live machine observation can override stale Obsidian memory, while general LLM knowledge remains the lowest-authority source for current machine state.

## Core Components

### Qwen3 + Ollama

Ollama provides the local model runtime. `qwen3:8b` is the primary CYRAX model, while `qwen3-embedding:0.6b` is used for semantic memory retrieval.

### Open Interpreter

Open Interpreter is retained as the computer/code execution layer. CYRAX prefers narrower native tools first and uses PowerShell as a fallback when a dedicated tool is not available.

### Native Tool Bridge

CYRAX currently exposes narrow tools for:

- `ollama_models` — live installed-model inventory and size
- `read_file` — authoritative local file reads
- `write_file` — approved file writes
- `list_directory` — live directory state
- `execute_powershell` — approved fallback machine actions
- `memory_search` — persistent Obsidian recall
- `memory_save` — explicit durable memory

### Obsidian Second Brain

Obsidian stores readable Markdown notes for durable project knowledge. Memory is treated as context, not unquestionable truth. Runtime and live evidence can supersede stale memories.

### Truth Policy

`agent/truth_policy.py` provides a small deterministic evidence-ranking layer. It is now wired into the CYRAX runtime rather than existing only as documentation or tests.

### Memory Policy

`agent/memory/memory_policy.py` keeps ephemeral runtime observations out of durable memory and promotes durable facts, preferences, decisions, and project information when appropriate.

## Repository Layout

```text
CYRAX/
├── agent/
│   ├── cyrax.py
│   ├── request_router.py
│   ├── tool_bridge.py
│   ├── truth_policy.py
│   └── memory/
│       └── memory_policy.py
├── scripts/
│   ├── verify_request_routing.py
│   ├── verify_integration.py
│   ├── verify_truth_policy.py
│   ├── verify_truth_runtime.py
│   └── verify_unicode_source.py
├── config/
├── tests/
├── docs/
├── requirements.txt
└── README.md
```

## Verification

Run the following from the CYRAX virtual environment:

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_unicode_source.py
.\.venv\Scripts\python.exe .\scripts\verify_truth_runtime.py
.\.venv\Scripts\python.exe .\scripts\verify_truth_policy.py
.\.venv\Scripts\python.exe .\scripts\verify_integration.py
.\.venv\Scripts\python.exe .\scripts\verify_request_routing.py
```

The repository's current local baseline is **38/38 tests passing**.

## Design Principles

1. **Live reality beats stale memory.**
2. **Native narrow tools beat broad shell execution when possible.**
3. **Tool results are authoritative evidence for the facts they directly observe.**
4. **The LLM should not invent machine state or reinterpret exact tool units.**
5. **Durable memory should be selective, not a transcript dump.**
6. **Everything important should be testable without depending on model intuition.**
7. **Local-first is a design constraint, not a marketing phrase.**

## Roadmap

### Phase 1 — Reliable Agent Core

- [x] Local Ollama + Qwen runtime
- [x] Open Interpreter integration
- [x] Native tool bridge
- [x] Deterministic request routing
- [x] Obsidian semantic memory
- [x] Conservative auto-memory policy
- [x] Truth/source authority policy
- [x] Live-tool priority over memory
- [x] File read/write execution with approval
- [x] Unit normalization and evidence integrity guards
- [x] UTF-8 source regression protection

### Phase 2 — Truth-Aware Second Brain

Next priorities:

1. **Truth-aware retrieval** — attach source, timestamp, and confidence metadata to recalled memories.
2. **Conflict detection in normal conversations** — automatically surface stale memory when live/project evidence disagrees.
3. **Evidence-backed answers** — let CYRAX expose why a fact was chosen without dumping internal implementation details.
4. **Memory promotion** — consolidate repeated observations into durable project knowledge instead of saving raw interactions.
5. **Memory maintenance** — detect duplicates, stale notes, and contradictory project facts.

### Phase 3 — Agent Planning

- structured task planning
- multi-step tool execution
- checkpoints and recovery
- approval boundaries by risk level
- resumable tasks
- explicit action logs

### Phase 4 — Local Multimodal / Computer Agent

- stronger computer-use workflows
- local vision capabilities
- richer filesystem and application integrations
- project-aware automation
- optional voice interface

### Phase 5 — Evaluation and Hardening

- end-to-end scenario suites
- adversarial hallucination tests
- tool misuse tests
- memory poisoning/conflict tests
- performance and latency benchmarks
- regression CI for routing, truth, memory, and tools

## Development Rule

The project should evolve in this order:

```text
correctness
   ↓
observability
   ↓
truth / memory reliability
   ↓
action reliability
   ↓
planning
   ↓
more capability
```

Do not add more tools just because they are available. Every new capability should come with a clear source-of-truth rule and an executable verification test.

## License

TBD
