# agents/

LLM integration layer: client wrapper, prompt templates, and LangChain tool bindings.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `client.py` | LLM client wrapper — provider switching between mock and OpenAI | Changing LLM provider, debugging LLM calls |
| `prompts.py` | System and user prompt templates for draft generation | Tuning AI output style, clinical register, or content |
| `tools.py` | LangChain tool bindings — exposes data-fetch tools to the LLM | Adding tool use, changing which tools LLM can call |
