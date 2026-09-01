"""Application configuration loaded from environment variables or a local ``.env`` file.

The :class:`Settings` class is instantiated once at import time as ``settings``.
All modules that need configuration values import ``settings`` from this module.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from the environment (or ``.env`` file).
    Unknown environment variables are silently ignored.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ScaDS.AI LLM API — required for making chat-completion requests.
    scadsai_api_key: str = ""
    scadsai_api_base: str = "https://llm.scads.ai/v1"
    scadsai_chat_model: str = "alias-vision"
    scadsai_request_timeout: int = 60

    # MCP server connection details (used when the server runs standalone).
    mcp_server_host: str = "127.0.0.1"
    mcp_server_port: int = 8000

    # Backend web server (serves the frontend and API endpoints).
    backend_host: str = "127.0.0.1"
    backend_port: int = 8080


settings = Settings()
