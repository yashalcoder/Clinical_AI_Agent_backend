from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL:                str

    # JWT
    SECRET_KEY:                  str
    ALGORITHM:                   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Google OAuth
    GOOGLE_CLIENT_ID:            str = ""
    GOOGLE_CLIENT_SECRET:        str = ""
    GOOGLE_REDIRECT_URI:         str = "http://localhost:8000/api/auth/google/callback"
    FRONTEND_URL:                str = "http://localhost:3000"

    # Twilio
    TWILIO_ACCOUNT_SID:          str = ""
    TWILIO_AUTH_TOKEN:           str = ""
    TWILIO_WHATSAPP_FROM:        str = ""

    # OpenAI
    OPENAI_API_KEY:              str = ""
    
    #assembly AI(STT)
    ASSEMBLYAI_API_KEY: str = ""
    # App
    APP_NAME:                    str = "ClinicFlow AI"
    DEBUG:                       bool = True

    class Config:
        env_file = ".env"

settings = Settings()