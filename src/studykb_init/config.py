"""LLM API configuration management for initialization tools."""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    """LLM API configuration."""

    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 4096


class InitSettings(BaseSettings):
    """Initialization tool settings."""

    model_config = SettingsConfigDict(
        env_prefix="STUDYKB_",
        env_file=".env",
        extra="ignore",
    )

    # Config file path for LLM settings
    llm_config_path: Path = Path("./config/llm_config.yaml")

    # Knowledge base path
    kb_path: Path = Path("./kb")

    # Progress data path
    progress_path: Path = Path("./progress")

    # LLM configuration (loaded from file or defaults)
    llm: LLMConfig = Field(default_factory=LLMConfig)


def _expand_env_vars(value: str) -> str:
    """Expand environment variables in string values."""
    pattern = r'\$\{([^}]+)\}'

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replacer, value)


def _process_config_dict(config: dict) -> dict:
    """Recursively process config dict to expand env vars."""
    result = {}
    for key, value in config.items():
        if isinstance(value, str):
            result[key] = _expand_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _process_config_dict(value)
        else:
            result[key] = value
    return result


def load_config(config_path: Optional[Path] = None) -> InitSettings:
    """Load initialization settings from config file."""
    settings = InitSettings()
    path = config_path or settings.llm_config_path

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        config_data = _process_config_dict(config_data)
        if "llm" in config_data:
            settings.llm = LLMConfig(**config_data["llm"])

    return settings


def save_config(settings: InitSettings, config_path: Optional[Path] = None) -> None:
    """Save initialization settings to config file."""
    path = config_path or settings.llm_config_path
    path.parent.mkdir(parents=True, exist_ok=True)

    config_data = {
        "llm": {
            "base_url": settings.llm.base_url,
            "api_key": settings.llm.api_key,
            "model": settings.llm.model,
            "temperature": settings.llm.temperature,
            "max_tokens": settings.llm.max_tokens,
        }
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True)


def ensure_api_configured(settings: InitSettings) -> bool:
    """Check if LLM API is properly configured."""
    return bool(settings.llm.api_key and settings.llm.api_key.strip())
