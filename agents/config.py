"""
Configuration
"""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from agents import __version__


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ModelConfig(BaseModel):
    name: str = Field(..., description="Model name")
    provider: str = Field(..., description="Model provider (openai, anthropic, etc.)")
    api_key: Optional[str] = Field(None, description="API key for the model")
    max_tokens: int = Field(4096, ge=1, le=32000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    timeout: int = Field(30, ge=1, le=300)


class AgentConfig(BaseSettings):
    """Main configuration with automatic environment variable loading"""

    version: str = __version__
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    debug: bool = Field(False, description="Enable debug mode")

    # Model configurations
    model: ModelConfig = Field(..., description="LLM model configuration")


class ConfigManager:
    """Configuration manager with multiple loading strategies"""

    def __init__(self):
        self._config: Optional[AgentConfig] = None
        self._config_path: Optional[Path] = None

    @classmethod
    def from_file(cls, config_path: str | Path) -> "ConfigManager":
        """Load configuration from JSON/YAML file"""
        manager = cls()
        manager._config_path = Path(config_path)

        if not manager._config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load based on file extension
        if manager._config_path.suffix.lower() == ".json":
            config_data = json.loads(manager._config_path.read_text())
        elif manager._config_path.suffix.lower() in [".yml", ".yaml"]:
            try:
                import yaml

                config_data = yaml.safe_load(manager._config_path.read_text())
            except ImportError:
                raise ImportError("PyYAML is required for YAML configuration files")
        else:
            raise ValueError(
                f"Unsupported configuration file format: {manager._config_path.suffix}"
            )

        manager._config = AgentConfig(**config_data)
        return manager

    # @classmethod
    # def from_env(cls) -> "ConfigManager":
    #     """Load configuration from environment variables"""
    #     manager = cls()
    #     manager._config = AgentConfig() #: BUG: Report call issue
    #     return manager

    @property
    def config(self) -> AgentConfig:
        """Get the loaded configuration"""
        if self._config is None:
            raise RuntimeError(
                "Configuration not loaded. Use one of the from_* methods first."
            )
        return self._config


class Config:
    """Configuration for agent."""

    def __init__(self):
        self.llm_api_key = os.getenv("GEMINI_API_KEY", "")
        self.llm_base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        # Default temperature for LLM calls
        self.temperature = 0.1

        # Human in the loop settings
        self.require_human_approval = True

        # Logging settings
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

    def get_llm_settings(self) -> Dict[str, Any]:
        """Get the settings for LLM initialization."""
        return {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "temperature": self.temperature,
        }

    def update(self, **kwargs):
        """Update configuration with provided values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


# Global config instance
config = Config()
