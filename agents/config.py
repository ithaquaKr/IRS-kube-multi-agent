"""
Configuration module for the agent.

This module defines the configuration for the agent, loading settings from
environment variables using pydantic-settings for robust and type-safe
configuration management.
"""

from typing import Any, Dict

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """
    Main configuration class for the application.

    Attributes:
        llm_api_key (str): The API key for the Gemini service.
        llm_base_url (str): The base URL for the Gemini API.
        temperature (float): The default temperature for LLM calls.
        require_human_approval (bool): Whether to require human approval for actions.
        debug_mode (bool): Enables or disables debug mode.
    """

    # Configure pydantic-settings to handle environment variables.
    # `alias` is used to map environment variables to field names.
    model_config = SettingsConfigDict(extra="ignore")

    llm_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    llm_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        alias="GEMINI_BASE_URL",
    )
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE")

    # Default application settings
    temperature: float = 0.1
    require_human_approval: bool = True

    def get_llm_settings(self) -> Dict[str, Any]:
        """Get the settings for LLM initialization."""
        return {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "temperature": self.temperature,
        }

    def update(self, **kwargs: Any) -> None:
        """Update configuration with provided values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


# Global config instance
config = Config()
