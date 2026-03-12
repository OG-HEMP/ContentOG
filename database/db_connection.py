import os
from urllib.parse import parse_qs, urlparse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv():
        return False

load_dotenv()


def _postgres_url() -> str:
    for key in ("POSTGRESQL", "POSTGRESQL_URL", "POSTGRES_URL", "DATABASE_URL"):
        value = os.getenv(key)
        if value:
            return value
    return ""


def get_db():
    """Establish a connection to the Supabase PostgreSQL database when driver is available."""
    try:
        import psycopg2
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"psycopg2 is not installed: {exc}") from exc

    # Prioritize the full connection URL if available.
    connection_url = _postgres_url()
    if connection_url:
        parsed = urlparse(connection_url)
        params = parse_qs(parsed.query or "")
        connect_kwargs = {}
        # Supabase pooler typically requires SSL; default to require unless explicitly provided.
        if "sslmode" not in params:
            connect_kwargs["sslmode"] = "require"
        return psycopg2.connect(connection_url, **connect_kwargs)

    # Fall back to individual components
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
    )
    return conn
