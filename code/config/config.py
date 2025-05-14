# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Basic config services, including loading config from config_llm.yaml, config_embedding.yaml, config_retrieval.yaml, 
config_webserver.yaml, config_nlweb.yaml
WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import os
import yaml
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Dict, Optional, Any, List

# Define constants for base directories based on environment
def get_base_directories():
    """
    Returns appropriate base directories for different types of files
    based on the current environment (local dev or Azure App Service)
    """
    # Check if running in Azure App Service
    if os.environ.get('WEBSITE_SITE_NAME'):
        # In Azure App Service with ZIP deployment
        data_dir = '/home/data/nlweb_data'  # Persistent storage across restarts
        logs_dir = '/home/LogFiles/nlweb_logs'  # Azure recommended logs location
        temp_dir = '/tmp/nlweb_temp'  # Temporary storage
        
        # Add symlinks for backward compatibility with code expecting paths in app directory
        try:
            app_dir = '/home/site/wwwroot'
            if not os.path.exists(os.path.join(app_dir, 'data')):
                os.symlink(data_dir, os.path.join(app_dir, 'data'))
            if not os.path.exists(os.path.join(app_dir, 'logs')):
                os.symlink(logs_dir, os.path.join(app_dir, 'logs'))
        except Exception as e:
            print(f"Warning: Failed to create symlinks: {e}")
    else:
        # Local development environment
        app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(app_root, 'data')
        logs_dir = os.path.join(app_root, 'logs')
        temp_dir = os.path.join(app_root, 'temp')
    
    # Ensure directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    return {
        'data': data_dir,
        'logs': logs_dir,
        'temp': temp_dir
    }

# Initialize the base directories
BASE_DIRS = get_base_directories()

@dataclass
class ModelConfig:
    high: str
    low: str

@dataclass
class LLMProviderConfig:
    api_key: Optional[str] = None
    models: Optional[ModelConfig] = None
    endpoint: Optional[str] = None
    api_version: Optional[str] = None

@dataclass
class EmbeddingProviderConfig:
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    api_version: Optional[str] = None
    model: Optional[str] = None

@dataclass
class RetrievalProviderConfig:
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    database_path: Optional[str] = None
    index_name: Optional[str] = None
    db_type: Optional[str] = None  

@dataclass
class SSLConfig:
    enabled: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None

@dataclass
class LoggingConfig:
    level: str = "info"
    file: str = "./logs/webserver.log"

@dataclass
class StaticConfig:
    enable_cache: bool = True
    cache_max_age: int = 3600
    gzip_enabled: bool = True

@dataclass
class ServerConfig:
    host: str = "localhost"
    enable_cors: bool = True
    max_connections: int = 100
    timeout: int = 30
    ssl: Optional[SSLConfig] = None
    logging: Optional[LoggingConfig] = None
    static: Optional[StaticConfig] = None

@dataclass
class NLWebConfig:
    sites: List[str]  # List of allowed sites
    json_data_folder: str = "./data/json"  # Default folder for JSON data
    json_with_embeddings_folder: str = "./data/json_with_embeddings"  # Default folder for JSON with embeddings

class AppConfig:
    config_paths = ["config.yaml", "config_llm.yaml", "config_embedding.yaml", "config_retrieval.yaml", 
                   "config_webserver.yaml", "config_nlweb.yaml"]

    def __init__(self):
        load_dotenv()
        # Create required directories
        self._ensure_app_directories()
        # Load configurations
        self.load_llm_config()
        self.load_embedding_config()
        self.load_retrieval_config()
        self.load_webserver_config()
        self.load_nlweb_config()
    
    def _ensure_app_directories(self):
        """Ensure all required application directories exist"""
        # Create subdirectories for various data types
        os.makedirs(os.path.join(BASE_DIRS['data'], 'json'), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIRS['data'], 'json_with_embeddings'), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIRS['data'], 'indexes'), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIRS['logs']), exist_ok=True)
    
    def _get_config_value(self, value: Any, default: Any = None) -> Any:
        """
        Get configuration value. If value is a string, return it directly.
        Otherwise, treat it as an environment variable name and fetch from environment.
        Returns default if environment variable is not set or value is None.
        """
        if value is None:
            return default
            
        if isinstance(value, str):
            # If it's clearly an environment variable name (e.g., "OPENAI_API_KEY_ENV")
            if value.endswith('_ENV') or value.isupper():
                return os.getenv(value, default)
            # Otherwise, treat it as a literal string value
            else:
                return value
        
        # For non-string values, return as-is
        return value

    def load_llm_config(self, path: str = "config_llm.yaml"):
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        with open(full_path, "r") as f:
            data = yaml.safe_load(f)

            self.preferred_llm_provider: str = data["preferred_provider"]
            self.llm_providers: Dict[str, LLMProviderConfig] = {}

            for name, cfg in data.get("providers", {}).items():
                m = cfg.get("models", {})
                models = ModelConfig(
                    high=self._get_config_value(m.get("high")),
                    low=self._get_config_value(m.get("low"))
                ) if m else None
                
                # Extract configuration values from the YAML with the new method
                api_key = self._get_config_value(cfg.get("api_key_env"))
                api_endpoint = self._get_config_value(cfg.get("api_endpoint_env"))
                api_version = self._get_config_value(cfg.get("api_version_env"))
                # Create the LLM provider config - no longer include embedding model
                self.llm_providers[name] = LLMProviderConfig(
                    api_key=api_key,
                    models=models,
                    endpoint=api_endpoint,
                    api_version=api_version
                )

    def load_embedding_config(self, path: str = "config_embedding.yaml"):
        """Load embedding model configuration."""
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        try:
            with open(full_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            # If config file doesn't exist, use defaults
            print(f"Warning: {path} not found. Using default embedding configuration.")
            data = {
                "preferred_provider": "openai",
                "providers": {}
            }
        
        self.preferred_embedding_provider: str = data["preferred_provider"]
        self.embedding_providers: Dict[str, EmbeddingProviderConfig] = {}

        for name, cfg in data.get("providers", {}).items():
            # Extract configuration values from the YAML
            api_key = self._get_config_value(cfg.get("api_key_env"))
            api_endpoint = self._get_config_value(cfg.get("api_endpoint_env"))
            api_version = self._get_config_value(cfg.get("api_version_env"))
            model = self._get_config_value(cfg.get("model"))

            # Create the embedding provider config
            self.embedding_providers[name] = EmbeddingProviderConfig(
                api_key=api_key,
                endpoint=api_endpoint,
                api_version=api_version,
                model=model
            )

    def load_retrieval_config(self, path: str = "config_retrieval.yaml"):
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        try:
            with open(full_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            # If config file doesn't exist, use defaults
            print(f"Warning: {path} not found. Using default retrieval configuration.")
            data = {
                "preferred_endpoint": "default",
                "endpoints": {}
            }

        # Changed from preferred_provider to preferred_endpoint
        self.preferred_retrieval_endpoint: str = data["preferred_endpoint"]
        self.retrieval_endpoints: Dict[str, RetrievalProviderConfig] = {}

        # Changed from providers to endpoints
        for name, cfg in data.get("endpoints", {}).items():
            # Use the new method for all configuration values
            self.retrieval_endpoints[name] = RetrievalProviderConfig(
                api_key=self._get_config_value(cfg.get("api_key_env")),
                api_endpoint=self._get_config_value(cfg.get("api_endpoint_env")),
                database_path=self._get_config_value(cfg.get("database_path")),
                index_name=self._get_config_value(cfg.get("index_name")),
                db_type=self._get_config_value(cfg.get("db_type"))  # Add db_type
            )
    
    def load_webserver_config(self, path: str = "config_webserver.yaml"):
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        try:
            with open(full_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            # If config file doesn't exist, use defaults
            print(f"Warning: {path} not found. Using default webserver configuration.")
            data = {
                "port": 8080,
                "static_directory": "./static",
                "server": {}
            }
        
        # Load basic configurations with the new method
        self.port: int = self._get_config_value(data.get("port"), 8080)
        self.static_directory: str = self._get_config_value(data.get("static_directory"), "./static")
        self.mode: str = self._get_config_value(data.get("mode"), "production")
        
        # Convert relative paths to absolute paths based on config file location
        if not os.path.isabs(self.static_directory):
            self.static_directory = os.path.abspath(os.path.join(config_dir, self.static_directory))
        
        # Load server configurations
        server_data = data.get("server", {})
        
        # SSL configuration
        ssl_data = server_data.get("ssl", {})
        ssl_config = SSLConfig(
            enabled=self._get_config_value(ssl_data.get("enabled"), False),
            cert_file=self._get_config_value(ssl_data.get("cert_file_env")),
            key_file=self._get_config_value(ssl_data.get("key_file_env"))
        )
        
        # Logging configuration
        logging_data = server_data.get("logging", {})
        log_file_path = self._get_config_value(logging_data.get("file"), "webserver.log")
        # If it's a relative path, make it absolute using the logs directory
        if not os.path.isabs(log_file_path):
            log_file_path = os.path.join(BASE_DIRS['logs'], os.path.basename(log_file_path))
        
        logging_config = LoggingConfig(
            level=self._get_config_value(logging_data.get("level"), "info"),
            file=log_file_path
        )
        
        # Convert logging file path to absolute if relative
        if not os.path.isabs(logging_config.file):
            logging_config.file = os.path.abspath(os.path.join(config_dir, logging_config.file))
        
        # Static file configuration
        static_data = server_data.get("static", {})
        static_config = StaticConfig(
            enable_cache=self._get_config_value(static_data.get("enable_cache"), True),
            cache_max_age=self._get_config_value(static_data.get("cache_max_age"), 3600),
            gzip_enabled=self._get_config_value(static_data.get("gzip_enabled"), True)
        )
        
        # Create the server config
        self.server = ServerConfig(
            host=self._get_config_value(server_data.get("host"), "localhost"),
            enable_cors=self._get_config_value(server_data.get("enable_cors"), True),
            max_connections=self._get_config_value(server_data.get("max_connections"), 100),
            timeout=self._get_config_value(server_data.get("timeout"), 30),
            ssl=ssl_config,
            logging=logging_config,
            static=static_config
        )

    def load_nlweb_config(self, path: str = "config_nlweb.yaml"):
        """Load Natural Language Web configuration."""
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        try:
            with open(full_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            # If config file doesn't exist, use defaults
            print(f"Warning: {path} not found. Using default NLWeb configuration.")
            data = {
                "sites": "",
                "data_folders": {
                    "json_data": "./data/json",
                    "json_with_embeddings": "./data/json_with_embeddings"
                }
            }
        
        # Parse the comma-separated sites string into a list
        sites_str = self._get_config_value(data.get("sites"), "")
        sites_list = [site.strip() for site in sites_str.split(",") if site.strip()]
        
        # Get data folder paths from config
        json_data_folder = "./data/json"
        json_with_embeddings_folder = "./data/json_with_embeddings"
        
        if "data_folders" in data:
            json_data_path = self._get_config_value(data["data_folders"].get("json_data"), "json")
            json_with_embeddings_path = self._get_config_value(
                data["data_folders"].get("json_with_embeddings"), 
                "json_with_embeddings"
            )
            
            # If paths are not absolute, make them absolute using BASE_DIRS
            if not os.path.isabs(json_data_path):
                json_data_folder = os.path.join(BASE_DIRS['data'], os.path.basename(json_data_path))
            if not os.path.isabs(json_with_embeddings_path):
                json_with_embeddings_folder = os.path.join(BASE_DIRS['data'], os.path.basename(json_with_embeddings_path))
        
        # Convert relative paths to absolute paths based on config file location
        if not os.path.isabs(json_data_folder):
            json_data_folder = os.path.abspath(os.path.join(config_dir, json_data_folder))
        if not os.path.isabs(json_with_embeddings_folder):
            json_with_embeddings_folder = os.path.abspath(os.path.join(config_dir, json_with_embeddings_folder))
        
        # Ensure directories exist
        os.makedirs(json_data_folder, exist_ok=True)
        os.makedirs(json_with_embeddings_folder, exist_ok=True)
        
        self.nlweb = NLWebConfig(
            sites=sites_list,
            json_data_folder=json_data_folder,
            json_with_embeddings_folder=json_with_embeddings_folder
        )
    
    def get_ssl_cert_path(self) -> Optional[str]:
        """Get the SSL certificate file path."""
        if self.server.ssl:
            return self.server.ssl.cert_file
        return None
    
    def get_ssl_key_path(self) -> Optional[str]:
        """Get the SSL key file path."""
        if self.server.ssl:
            return self.server.ssl.key_file
        return None
    
    def is_ssl_enabled(self) -> bool:
        """Check if SSL is enabled and properly configured."""
        return (self.server.ssl and 
                self.server.ssl.enabled and 
                self.server.ssl.cert_file is not None and 
                self.server.ssl.key_file is not None)
    
    def is_production_mode(self) -> bool:
        """Returns True if the system is running in production mode."""
        return getattr(self, 'mode', 'production').lower() == 'production'
    
    def is_development_mode(self) -> bool:
        """Returns True if the system is running in development mode."""
        return getattr(self, 'mode', 'production').lower() == 'development'
    
    def get_allowed_sites(self) -> List[str]:
        """Get the list of allowed sites from NLWeb configuration."""
        return self.nlweb.sites if hasattr(self, 'nlweb') else []
    
    def is_site_allowed(self, site: str) -> bool:
        """Check if a site is in the allowed sites list."""
        allowed_sites = self.get_allowed_sites()
        # If no sites are configured, allow all sites
        if not allowed_sites:
            return True
        return site in allowed_sites
    
    def get_embedding_provider(self, provider_name: Optional[str] = None) -> Optional[EmbeddingProviderConfig]:
        """Get the specified embedding provider config or the preferred one if not specified."""
        if not hasattr(self, 'embedding_providers'):
            return None
            
        if provider_name and provider_name in self.embedding_providers:
            return self.embedding_providers[provider_name]
            
        if hasattr(self, 'preferred_embedding_provider') and self.preferred_embedding_provider in self.embedding_providers:
            return self.embedding_providers[self.preferred_embedding_provider]
            
        return None
            
    def get_llm_provider(self, provider_name: Optional[str] = None) -> Optional[LLMProviderConfig]:
        """Get the specified LLM provider config or the preferred one if not specified."""
        if not hasattr(self, 'llm_providers'):
            return None
            
        if provider_name and provider_name in self.llm_providers:
            return self.llm_providers[provider_name]
            
        if hasattr(self, 'preferred_llm_provider') and self.preferred_llm_provider in self.llm_providers:
            return self.llm_providers[self.preferred_llm_provider]
            
        return None

# Global singleton
CONFIG = AppConfig()
