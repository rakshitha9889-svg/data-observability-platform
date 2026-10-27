import os

SUPPORTED_PROVIDERS = ("claude", "ollama")


def get_provider_name(provider: str | None = None) -> str:
    name = (provider or os.getenv("LLM_PROVIDER", "claude")).lower()

    if name not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unknown LLM provider '{name}'. "
            f"Use one of: {', '.join(SUPPORTED_PROVIDERS)}."
        )

    return name


def get_chat_model(provider: str | None = None):  # pragma: no cover
    name = get_provider_name(provider)

    if name == "claude":
        from langchain_anthropic import ChatAnthropic

        model = os.getenv("CLAUDE_MODEL")
        if not model:
            raise RuntimeError(
                "CLAUDE_MODEL is missing. Add a model ID from "
                "docs.claude.com to the project .env file."
            )

        return ChatAnthropic(model=model, temperature=0, max_tokens=800)

    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        temperature=0,
    )
