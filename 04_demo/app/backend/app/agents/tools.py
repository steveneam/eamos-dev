def build_langchain_tools(tool_registry: dict) -> list[object]:
    return list(tool_registry.values())
