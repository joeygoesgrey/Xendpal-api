from pydantic import EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ENGINE : str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    EMAIL_PORT: int
    EMAIL_HOST_USER: EmailStr  # Replace with your email address
    EMAIL_HOST_PASSWORD: str  # Replace with your email password
    USER_INFO_URL: str
    TOKEN_URL: str
    REDIRECT_URI: str
    CLIENT_SECRET: str
    CLIENT_ID: str

    class Config:
        env_file = ".env"


settings = Settings()
