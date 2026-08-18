"""Tests for environment-derived settings behavior."""

from backend.config.settings import Settings


def test_allowed_origins_accepts_one_comma_separated_value():
    settings = Settings.model_construct(
        allowed_origins=(
            "https://insightdocs.vercel.app/, http://localhost:3000, "
            "http://127.0.0.1:3000, https://insightdocs.vercel.app"
        )
    )

    assert settings.allowed_origins_list == [
        "https://insightdocs.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
