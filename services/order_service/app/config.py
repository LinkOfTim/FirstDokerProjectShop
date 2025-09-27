from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "order-service"
    debug: bool = True
    port: int = 8000

    database_url: str
    secret_key: str = "dev-secret-change-me"
    catalog_url: str = "http://catalog:8000"
    cart_url: str = "http://cart:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings(_env_file=Settings.Config.env_file, _env_file_encoding="utf-8")

