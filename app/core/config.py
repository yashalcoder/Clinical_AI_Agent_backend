from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_FROM: str
    OPENAI_API_KEY: str
    APP_NAME: str = "ClinicFlow AI"
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()