"""
Configuration module for the agent.

This module defines the configuration for the agent, loading settings from
environment variables using pydantic-settings for robust and type-safe
configuration management.
"""

from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


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

    # Slack Configuration
    SLACK_BOT_TOKEN: Optional[str] = Field(default=None, alias="SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET: Optional[str] = Field(
        default=None, alias="SLACK_SIGNING_SECRET"
    )
    SLACK_APP_TOKEN: Optional[str] = Field(default=None, alias="SLACK_APP_TOKEN")
    SLACK_CHANNEL_ID: str = Field(
        default="#incident-response", alias="SLACK_CHANNEL_ID"
    )
    SLACK_APPROVAL_TIMEOUT: int = Field(default=300, alias="SLACK_APPROVAL_TIMEOUT")

    # Kubernetes Configuration
    KUBECONFIG_PATH: Optional[str] = Field(default=None, alias="KUBECONFIG_PATH")

    # LLM Configuration
    GOOGLE_API_KEY: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    TAVILY_API_KEY: Optional[str] = Field(default=None, alias="TAVILY_API_KEY")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", alias="HOST")
    PORT: int = Field(default=3000, alias="PORT")

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


# Validation
def validate_slack_config():
    """Validate that required Slack configuration is present"""
    if not config.SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not config.SLACK_SIGNING_SECRET:
        raise ValueError("SLACK_SIGNING_SECRET environment variable is required")
    if not config.SLACK_APP_TOKEN:
        raise ValueError("SLACK_APP_TOKEN environment variable is required")
    if not config.SLACK_CHANNEL_ID:
        raise ValueError("SLACK_CHANNEL_ID environment variable is required")


def validate_llm_config():
    """Validate that required LLM configuration is present"""
    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    if not config.TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY environment variable is required")
