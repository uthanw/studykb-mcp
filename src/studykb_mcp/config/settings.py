"""Application settings using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Settings can be configured via environment variables with STUDYKB_ prefix.
    Example: STUDYKB_KB_PATH=./my_kb
    """

    model_config = SettingsConfigDict(
        env_prefix="STUDYKB_",
        env_file=".env",
        extra="ignore",
    )

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8080

    # Path configuration (relative to working directory)
    kb_path: Path = Path("./kb")
    progress_path: Path = Path("./progress")
    workspaces_path: Path = Path("./workspaces")

    # Limits
    max_read_lines: int = 500
    max_grep_matches: int = 100
    max_file_size: int = 1024 * 1024  # 1MB, 防止读取/写入过大文件

    # History
    max_history_versions: int = 50  # per-file snapshot cap

    # Review algorithm configuration (Ebbinghaus)
    review_initial_interval: int = 7  # days
    review_multiplier: float = 1.5
    review_max_interval: int = 90  # days


# Singleton instance
settings = Settings()
