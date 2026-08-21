from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    scadsai_api_key: str = ""
    scadsai_api_base: str = "https://llm.scads.ai/v1"
    scadsai_chat_model: str = "alias-vision"
    scadsai_request_timeout: int = 60

    mcp_server_host: str = "127.0.0.1"
    mcp_server_port: int = 8000

    backend_host: str = "127.0.0.1"
    backend_port: int = 8080


settings = Settings()
