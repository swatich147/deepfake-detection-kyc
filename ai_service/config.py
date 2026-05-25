"""AI Service Configuration."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    DEVICE: str = os.getenv('DEVICE', 'cpu')
    MODEL_DIR: str = os.getenv('MODEL_DIR', './weights')
    MOCK_INFERENCE: bool = os.getenv('MOCK_INFERENCE', 'true').lower() == 'true'
    
    # Face detection
    FACE_DET_SIZE: tuple = (640, 640)
    FACE_CONF_THRESHOLD: float = 0.5
    
    # Inference
    BATCH_SIZE: int = 8
    FPS_EXTRACTION: int = 5
    
    # Scores thresholds
    SUSPICIOUS_THRESHOLD: float = 0.3
    FAKE_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"


settings = Settings()
