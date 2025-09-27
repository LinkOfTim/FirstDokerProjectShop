from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "cart-service"
    debug: bool = True
    port: int = 8000

    redis_url: str = "redis://cart-redis:6379/0"
    secret_key: str = "dev-secret-change-me"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings(_env_file=Settings.Config.env_file, _env_file_encoding="utf-8")

