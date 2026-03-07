from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Polymarket CLOB
    polymarket_api_key: str = ""
    polymarket_api_secret: str = ""
    polymarket_private_key: str = ""
    polymarket_host: str = "https://clob.polymarket.com"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Bot defaults
    risk_per_trade_usd: float = 10.0
    confidence_threshold: float = 0.55
    default_strategy: str = "both"  # tech | ml | both

    # Database
    database_url: str = "sqlite:///./polytrip.db"


settings = Settings()
