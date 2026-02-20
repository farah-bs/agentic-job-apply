import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.2):
    """
    Returns a LangChain-compatible Mistral LLM.

    Environment variables:
        MISTRAL_API_KEY : Required for Mistral AI
        LLM_MODEL       : Override default model (default: mistral-large-2512)
    """
    from langchain_mistralai import ChatMistralAI
    
    model = os.getenv("LLM_MODEL", "mistral-large-2512")
    print(f"Using Mistral AI ({model})")
    
    return ChatMistralAI(
        model=model,
        temperature=temperature,
        mistral_api_key=os.getenv("MISTRAL_API_KEY")
    )
