# CYRAX

**CYRAX** is a local-first AI agent built around Open Interpreter, Ollama/Qwen, and Obsidian as a long-term memory layer.

## Vision

CYRAX is designed to be a practical local AI assistant that can reason, use computer tools, execute code, and retain durable project knowledge without requiring a cloud memory service.

## Architecture

```text
User
  ↓
CYRAX Agent
  ↓
Open Interpreter
  ↓
Ollama / Qwen
  ├── Computer / Shell / Python tools
  └── Memory Manager
          ↓
      Obsidian Vault
          ↓
   Long-term Project Memory
```

## Core components

- **Open Interpreter** — execution and tool-use layer
- **Ollama** — local model runtime
- **Qwen** — initial local LLM
- **Obsidian** — human-readable long-term memory
- **Python** — orchestration and memory management

## Initial goals

1. Connect CYRAX to a local Ollama model.
2. Use Open Interpreter as the execution layer.
3. Read and write an Obsidian Markdown vault.
4. Add searchable long-term memory.
5. Maintain project state and useful discoveries.
6. Add memory promotion and conflict protection.
7. Keep the system local-first and easy to debug.

## Planned structure

```text
CYRAX/
├── agent/
│   ├── __init__.py
│   └── cyrax.py
├── memory/
│   ├── __init__.py
│   ├── memory_manager.py
│   ├── search.py
│   └── writer.py
├── config/
│   └── config.example.yaml
├── scripts/
├── tests/
├── docs/
├── .gitignore
├── requirements.txt
└── README.md
```

## Status

🚧 Phase 0 — project bootstrap.

## License

TBD
