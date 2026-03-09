from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    debug_sql: bool = Field(default=False, validation_alias="DEBUG_SQL")
    allowed_origins: str = Field(default="http://localhost:3000", validation_alias="ALLOWED_ORIGINS")

    auth_secret_key: str = Field(validation_alias="AUTH_SECRET_KEY")
    auth_algorithm: str = Field(default="HS256", validation_alias="AUTH_ALGORITHM")
    auth_access_token_expire_minutes: int = Field(
        default=30,
        validation_alias="AUTH_ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    email_provider: Literal["console", "resend"] = Field(
        default="console",
        validation_alias="EMAIL_PROVIDER",
    )
    email_from: str | None = Field(default=None, validation_alias="EMAIL_FROM")
    frontend_verify_url: str = Field(
        default="http://localhost:3000/verify-email",
        validation_alias="FRONTEND_VERIFY_URL",
    )
    resend_api_key: str | None = Field(default=None, validation_alias="RESEND_API_KEY")
    email_test_recipient: str | None = Field(default=None, validation_alias="EMAIL_TEST_RECIPIENT")

    @property
    def allowed_origins_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return origins or ["http://localhost:3000"]

    @model_validator(mode="after")
    def validate_email_provider_config(self) -> "Settings":
        if self.email_provider == "resend":
            if not self.resend_api_key:
                raise ValueError("RESEND_API_KEY is required when EMAIL_PROVIDER=resend")
            if not self.email_from:
                raise ValueError("EMAIL_FROM is required when EMAIL_PROVIDER=resend")
        if self.email_test_recipient and self.app_env != "development":
            raise ValueError("EMAIL_TEST_RECIPIENT is allowed only when APP_ENV=development")
        return self


settings = Settings()
