import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.2):
    """
    Returns a LangChain-compatible Gemini LLM.

    Environment variables:
        GOOGLE_API_KEY : Required for Google Generative AI
        LLM_MODEL      : Override default model (default: gemini-1.5-pro)
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    model = os.getenv("LLM_MODEL", "gemini-1.5-pro")
    print(f"Using Google Gemini ({model})")
    
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        convert_system_message_to_human=True
    )
