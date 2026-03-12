import os
import logging
import yaml
from typing import Optional, Any, Dict, Type, List, Tuple
from dotenv import load_dotenv

# Ensure .env is loaded into os.environ for custom sources
load_dotenv()

from pydantic_settings import (
    BaseSettings, 
    PydanticBaseSettingsSource, 
    SettingsConfigDict
)
from pydantic import Field, ValidationError

logger = logging.getLogger(__name__)

class YAMLSettingsSource(PydanticBaseSettingsSource):
    """
    A custom settings source that reads from config/settings.yaml.
    """
    def __call__(self) -> Dict[str, Any]:
        yaml_path = "config/settings.yaml"
        if not os.path.exists(yaml_path):
            return {}
        
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except Exception as exc:
            logger.warning(f"Failed to load settings.yaml: {exc}")
            return {}

        d = {}
        # Crawler
        crawler = raw.get("crawler", {})
        d["crawler_provider"] = crawler.get("provider")
        d["crawler_timeout"] = crawler.get("timeout")
        d["crawler_retry_attempts"] = crawler.get("retry_attempts")
        d["crawler_backoff_seconds"] = crawler.get("backoff_seconds")
        
        # SERP
        serp = raw.get("serp", {})
        d["serp_results_per_keyword"] = serp.get("results_per_keyword")
        d["serp_region"] = serp.get("region")
        d["serp_language"] = serp.get("language")
        d["serp_timeout"] = serp.get("timeout")
        
        # Embeddings
        embeddings = raw.get("embeddings", {})
        d["embeddings_model"] = embeddings.get("model_name")
        d["embeddings_timeout"] = embeddings.get("timeout")
        
        # Clustering
        clustering = raw.get("clustering", {})
        d["clustering_min_cluster_size"] = clustering.get("min_cluster_size")
        d["clustering_metric"] = clustering.get("metric")
        
        # LLM
        llm = raw.get("llm", {})
        d["openai_strategy_model"] = llm.get("model_name")
        d["llm_timeout"] = llm.get("timeout")
        
        return {k: v for k, v in d.items() if v is not None}

    def get_field_value(self, field_name: str, field_alias: Optional[str]) -> Tuple[Any, str, bool]:
        return None, field_name, False

    def prepare_field_value(self, field_name: str, field_alias: Optional[str], value: Any, value_is_complex: bool) -> Any:
        return value

SENSITIVE_KEYWORDS = ["KEY", "SECRET", "POSTGRESQL", "URL"]

def is_sensitive(field_name: str) -> bool:
    """Return True if the field name implies it contains a sensitive record."""
    return any(k in field_name.upper() for k in SENSITIVE_KEYWORDS)

class GCPSecretSource(PydanticBaseSettingsSource):
    """
    A custom settings source that fetches secrets from Google Cloud Secret Manager.
    Only active if GCP_PROJECT_ID is set in the environment.
    """
    def get_field_value(self, field_name: str, field_alias: Optional[str]) -> Tuple[Any, str, bool]:
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            return None, field_name, False
        
        secret_name = field_alias or field_name
        if not is_sensitive(secret_name):
            return None, field_name, False

        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            val = response.payload.data.decode("UTF-8")
            return val, field_name, True
        except Exception as exc:
            logger.debug(f"Could not fetch secret {secret_name} from GCP: {exc}")
            return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            val, key, found = self.get_field_value(field_name, field.alias)
            if found:
                d[field_name] = val
        return d

class StrictSourceFilter(PydanticBaseSettingsSource):
    """
    Wraps another source and filters out sensitive fields if a GCP project is active.
    This effectively "stops fallback" for secrets.
    """
    def __init__(self, settings_cls: type[BaseSettings], base_source: PydanticBaseSettingsSource):
        super().__init__(settings_cls)
        self.base_source = base_source

    def __call__(self) -> Dict[str, Any]:
        data = self.base_source()
        project_id = os.getenv("GCP_PROJECT_ID")
        
        # If no project ID, act as a transparent proxy (standard local behavior)
        if not project_id:
            return data
        
        filtered = {}
        for key, value in data.items():
            field = self.settings_cls.model_fields.get(key)
            alias = field.alias if field else key
            
            # If it's sensitive and we're in GCP mode, we DON'T want the fallback value
            if not is_sensitive(alias):
                filtered[key] = value
            else:
                logger.debug(f"Strict mode: ignoring local fallback for sensitive field '{alias}'")
        
        return filtered

    def get_field_value(self, field_name: str, field_alias: Optional[str]) -> Tuple[Any, str, bool]:
        return None, field_name, False

    def prepare_field_value(self, field_name: str, field_alias: Optional[str], value: Any, value_is_complex: bool) -> Any:
        return value

class Settings(BaseSettings):
    # --- Infrastructure ---
    gcp_project_id: Optional[str] = Field(default=None, alias="GCP_PROJECT_ID")

    # --- Supabase / Database ---
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_key: str = Field(alias="SUPABASE_KEY")
    postgresql_url: str = Field(alias="POSTGRESQL")
    disable_db_fallback: bool = Field(default=True, alias="CONTENTOG_DISABLE_DB_FALLBACK")

    # --- AI Providers & External APIs ---
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    serp_api_key: str = Field(alias="SERP_API_KEY")
    firecrawl_api_key: Optional[str] = Field(default=None, alias="FIRECRAWL_API_KEY")

    # --- Crawler Settings ---
    # ... (rest of settings suppressed for brevity in tool call, but preserved in file write)
    crawler_provider: str = Field(default="http", alias="CRAWLER_PROVIDER")
    crawler_timeout: int = Field(default=30, alias="CRAWLER_TIMEOUT")
    crawler_retry_attempts: int = Field(default=3, alias="CRAWLER_RETRY_ATTEMPTS")
    crawler_backoff_seconds: float = Field(default=1.0, alias="CRAWLER_BACKOFF_SECONDS")
    crawler_limit_per_domain: int = Field(default=50, alias="CRAWLER_LIMIT_PER_DOMAIN")
    crawler_max_depth: int = Field(default=2, alias="CRAWLER_MAX_DEPTH")

    serp_results_per_keyword: int = Field(default=10, alias="SERP_RESULTS_PER_KEYWORD")
    serp_region: str = Field(default="us", alias="SERP_REGION")
    serp_language: str = Field(default="en", alias="SERP_LANGUAGE")
    serp_timeout: int = Field(default=30, alias="SERP_TIMEOUT")
    serp_retry_attempts: int = Field(default=3, alias="SERP_RETRY_ATTEMPTS")
    serp_backoff_seconds: float = Field(default=1.0, alias="SERP_BACKOFF_SECONDS")

    embeddings_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    embeddings_timeout: int = Field(default=60, alias="EMBEDDINGS_TIMEOUT")
    embeddings_retry_attempts: int = Field(default=3, alias="EMBEDDINGS_RETRY_ATTEMPTS")
    embeddings_backoff_seconds: float = Field(default=1.0, alias="EMBEDDINGS_BACKOFF_SECONDS")

    clustering_min_cluster_size: int = Field(default=2, alias="CLUSTERING_MIN_CLUSTER_SIZE")
    clustering_metric: str = Field(default="cosine", alias="CLUSTERING_METRIC")

    openai_strategy_model: str = Field(default="gpt-4o-mini", alias="OPENAI_STRATEGY_MODEL")
    llm_timeout: int = Field(default=90, alias="LLM_TIMEOUT")
    llm_retry_attempts: int = Field(default=3, alias="LLM_RETRY_ATTEMPTS")
    llm_backoff_seconds: float = Field(default=1.0, alias="LLM_BACKOFF_SECONDS")

    keyword_limit: int = Field(default=3, alias="CONTENT_OG_KEYWORD_LIMIT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            GCPSecretSource(settings_cls),
            StrictSourceFilter(settings_cls, env_settings),
            StrictSourceFilter(settings_cls, dotenv_settings),
            StrictSourceFilter(settings_cls, YAMLSettingsSource(settings_cls)),
            file_secret_settings,
        )

    def validate_config(self) -> None:
        """Perform manual checks for critical integration secrets."""
        missing = []
        critical_fields = [
            ("supabase_url", "SUPABASE_URL"),
            ("supabase_key", "SUPABASE_KEY"),
            ("openai_api_key", "OPENAI_API_KEY"),
            ("serp_api_key", "SERP_API_KEY")
        ]
        for attr, env_name in critical_fields:
            if not getattr(self, attr, None):
                missing.append(env_name)
        
        if missing:
            raise RuntimeError(f"Missing critical configuration: {', '.join(missing)}")
        
        logger.info("Configuration validated successfully")

try:
    settings = Settings()
except ValidationError as e:
    project_id = os.getenv("GCP_PROJECT_ID")
    if project_id:
        print("\n" + "="*70)
        print("🚨  CONFIGURATION ERROR: MISSING GCP SECRETS  🚨")
        print(f"Project ID: {project_id}")
        print("-" * 70)
        print("The following sensitive fields were NOT found in Secret Manager.")
        print("Since you are in 'Cloud Mode', fallback to .env is disabled for security.")
        print("-" * 70)
        
        for error in e.errors():
            loc = error.get("loc", [])
            field_name = loc[-1] if loc else "unknown"
            
            # Try to find the alias for better user experience
            field_obj = Settings.model_fields.get(str(field_name))
            alias = field_obj.alias if field_obj and field_obj.alias else field_name
            
            print(f"❌ Missing Secret: {alias}")
            print(f"   How to fix: Add this secret to Google Cloud Secret Manager.")
            print(f"   Quick Command: \n   gcloud secrets create {alias} --replication-policy=\"automatic\" --data-file=\"-\"")
            print("")
            
        print("-" * 70)
        print("Once added, verify the 'Secret Manager Secret Accessor' role is granted.")
        print("="*70 + "\n")
    raise
