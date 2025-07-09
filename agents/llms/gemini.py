"""Module for creating Gemini language model clients."""

from langchain_google_genai import ChatGoogleGenerativeAI

from config import config


def create_gemini_client():
    """
    Create a new Gemini language model instance using the ChatGoogleGenerativeAI client.

    This function reads configuration settings and initializes the Gemini client.
    """
    settings = config.get_llm_settings()

    return ChatGoogleGenerativeAI(
        model=settings.get("model", "gemini-1.5-flash"),
        temperature=settings.get("temperature", 0.7),
        google_api_key=settings.get("api_key"),
    )
