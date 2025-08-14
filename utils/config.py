from dataclasses import dataclass
import os

def _get_vector_store_max_size() -> int | None:
    value = os.getenv("VECTOR_STORE_MAX_SIZE")
    if value is None:
        return 1000
    if value.lower() == "none":
        return None
    try:
        return int(value)
    except ValueError:
        return 1000


@dataclass
class Settings:
    TELEGRAM_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "indiana")
    PINECONE_ENV: str = os.getenv("PINECONE_ENV", "")
    BASE_WEBHOOK_URL: str = os.getenv("BASE_WEBHOOK_URL", "")
    PORT: int = int(os.getenv("PORT", 8080))
    AGENT_GROUP: str = os.getenv("AGENT_GROUP_ID", "-1001234567890")
    GROUP_CHAT: str = os.getenv("GROUP_CHAT", "")
    CREATOR_CHAT: str = os.getenv("CREATOR_CHAT", "")
    PPLX_API_KEY: str = os.getenv("PPLX_API_KEY", os.getenv("PERPLEXITY_API_KEY", ""))
    RATE_LIMIT_COUNT: int = int(os.getenv("RATE_LIMIT_COUNT", 20))
    RATE_LIMIT_PERIOD: float = float(os.getenv("RATE_LIMIT_PERIOD", 60))
    RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", 0))
    VECTOR_STORE_MAX_SIZE: int | None = _get_vector_store_max_size()
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "vector_store.json")

    def __post_init__(self) -> None:
        required = {
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_TOKEN,
            "OPENAI_API_KEY": self.OPENAI_API_KEY,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing)
            )


settings = Settings()
