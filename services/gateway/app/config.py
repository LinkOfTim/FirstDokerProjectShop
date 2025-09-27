from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "gateway"
    debug: bool = True
    port: int = 8000

    auth_url: str = "http://auth:8000"
    catalog_url: str = "http://catalog:8000"
    cart_url: str = "http://cart:8000"
    order_url: str = "http://order:8000"
    secret_key: str = "dev-secret-change-me"  # for optional JWT decode

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings(_env_file=Settings.Config.env_file, _env_file_encoding="utf-8")
