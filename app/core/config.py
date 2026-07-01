from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Abastos JBot"
    SECRET_KEY: str = "CAMBIAR_ESTA_CLAVE"
    DATABASE_URL: str
    ADMIN_PASSWORD: str = "admin123"

    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    WAREHOUSE_NAME: str = 'Distribuidora de Chiles "Hernández"'
    PUBLIC_PICKUP_ADDRESS: str = "Mercado de Abastos, Morelia"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

