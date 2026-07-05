import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Protein Domain Prediction API"
    VERSION: str = "1.0.0"
    
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/proteindomainfinder")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "protein_db")
    
    # FASTA file path – you can set this in .env
    FASTA_FILE_PATH: str = os.getenv("FASTA_FILE_PATH", "data/proteins.fasta")
    
    # Sequence matching threshold
    SEQUENCE_MATCH_THRESHOLD: float = 0.8
    MAX_SEQUENCE_LENGTH: int = 5000

    # Optional password reset email settings
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8501")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    ADMIN_SETUP_CODE: str = os.getenv("ADMIN_SETUP_CODE", "")

settings = Settings()
