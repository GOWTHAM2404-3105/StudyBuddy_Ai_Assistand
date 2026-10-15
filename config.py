import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# Ensure database and upload directories exist
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = (DB_DIR / "studybuddy.db").as_posix()

# Resolve SQLite URL to absolute path
env_db_url = os.getenv("DATABASE_URL")
if not env_db_url or "sqlite:///" in env_db_url:
    # Always resolve sqlite to absolute path to prevent Windows relative path errors
    SQLALCHEMY_DB_URI = f"sqlite:///{DEFAULT_DB_PATH}"
else:
    SQLALCHEMY_DB_URI = env_db_url


class Config:
    """Base application configuration."""

    SECRET_KEY = os.getenv(
        "SECRET_KEY", "studybuddy-dev-secret-key-2026-secure-college-demo"
    )

    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads configuration
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"pdf"}

    # AI & Ollama configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

    # Embeddings & RAG configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RAG_CHUNK_SIZE = 500  # characters per chunk
    RAG_CHUNK_OVERLAP = 100  # overlap
    RAG_TOP_K = 4  # top similar chunks to retrieve

    # ML Model configuration
    DATA_DIR = BASE_DIR / "data"
    ML_MODEL_PATH = DATA_DIR / "student_performance_model.joblib"
    DATASET_PATH = DATA_DIR / "student-mat.csv"


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
