from app.core.config import Settings


def test_neon_url_is_adapted_for_asyncpg_and_psycopg() -> None:
    settings = Settings(
        database_url=(
            "postgresql://owner:secret@example-pooler.neon.tech/neondb"
            "?sslmode=require&channel_binding=require"
        )
    )

    assert settings.async_database_url == (
        "postgresql+asyncpg://owner:secret@example-pooler.neon.tech/neondb"
        "?ssl=require"
    )
    assert settings.sync_database_url == (
        "postgresql+psycopg://owner:secret@example-pooler.neon.tech/neondb"
        "?channel_binding=require&sslmode=require"
    )


def test_local_async_url_remains_compatible() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:password@localhost:5432/app"
    )

    assert settings.async_database_url == (
        "postgresql+asyncpg://user:password@localhost:5432/app"
    )
    assert settings.sync_database_url == (
        "postgresql+psycopg://user:password@localhost:5432/app"
    )
