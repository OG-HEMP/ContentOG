from config.config import settings


def get_db():
    """Establish a connection to the Supabase PostgreSQL database."""
    try:
        import psycopg2
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"psycopg2 is not installed: {exc}") from exc

    # Prioritize the full connection URL from Settings
    connection_url = settings.postgresql_url
    if connection_url:
        return psycopg2.connect(connection_url, sslmode="require")
    
    raise RuntimeError("POSTGRESQL connection string is not configured in settings.")
