from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str
    AWS_REGION: str
    S3_BUCKET: str
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    AI_MODEL_PROVIDER: str = "openai" # gemini, openai, anthropic
    
    @property
    def BUCKET_NAME(self) -> str:
        """Return S3_BUCKET as BUCKET_NAME for compatibility"""
        return self.S3_BUCKET
    
    # Email Provider Settings
    EMAIL_PROVIDER: str = "aws_ses"  # aws_ses or termii
    TERMII_API_KEY: str = ""
    TERMII_SENDER_ID: str = ""
    DEFAULT_FROM_EMAIL: str = ""

    
    # SMS Provider Settings
    SMS_PROVIDER: str = "termii"  # termii or twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # WhatsApp Provider Settings
    WHATSAPP_PROVIDER: str = "twilio"  # termii or twilio


    class Config:
        env_file = ".env"


settings = Settings()