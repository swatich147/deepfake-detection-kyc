"""
FastAPI AI Inference Service for Deepfake Detection
"""
import logging
import time
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from pipelines.inference import InferencePipeline

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Deepfake Detection AI Service",
    version="1.0.0",
    description="AI inference service for video KYC deepfake detection"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize inference pipeline
pipeline: Optional[InferencePipeline] = None


class AnalyzeRequest(BaseModel):
    """Request schema for video analysis."""
    session_id: str
    video_chunks: List[str]


class FrameScoreResponse(BaseModel):
    """Frame-level score response."""
    frame_number: int
    timestamp_ms: int
    face_detected: bool
    face_bbox: Optional[dict] = None
    face_confidence: Optional[float] = None
    manipulation_score: float
    is_anomaly: bool


class AnalyzeResponse(BaseModel):
    """Response schema for video analysis."""
    session_id: str
    face_manipulation_score: float
    face_manipulation_confidence: float
    lipsync_score: float
    lipsync_offset_ms: Optional[int] = None
    rppg_quality: float
    rppg_heart_rate: Optional[float] = None
    av_correlation_score: float
    frame_consistency_score: float
    faces_detected: int
    frames_analyzed: int
    frame_scores: List[FrameScoreResponse]
    model_versions: dict
    processing_time_ms: int


@app.on_event("startup")
async def startup():
    """Initialize models on startup."""
    global pipeline
    logger.info("Initializing AI inference pipeline...")
    
    try:
        pipeline = InferencePipeline(
            device=settings.DEVICE,
            model_dir=settings.MODEL_DIR
        )
        logger.info(f"Pipeline initialized on device: {settings.DEVICE}")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        # Continue without pipeline for development
        pipeline = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "pipeline_ready": pipeline is not None,
        "device": settings.DEVICE,
        "mock_inference": settings.MOCK_INFERENCE,
    }


@app.get("/models")
async def model_registry():
    """Model versions and ensemble config (Phase 4)."""
    config_path = Path(__file__).parent / "model_config.yaml"
    if config_path.is_file():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {"version": "unknown", "models": {}}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest):
    """
    Analyze video for deepfake detection.
    
    This endpoint accepts video chunk paths and returns comprehensive
    analysis results including face manipulation, lip-sync, rPPG, and
    audio-visual correlation scores.
    """
    start_time = time.time()
    
    if pipeline is None:
        # Return mock results for development
        logger.warning("Pipeline not initialized, returning mock results")
        return create_mock_response(request.session_id, start_time)
    
    try:
        # Run inference pipeline
        result = await pipeline.analyze(
            session_id=request.session_id,
            video_chunks=request.video_chunks
        )
        
        result['processing_time_ms'] = int((time.time() - start_time) * 1000)
        return AnalyzeResponse(**result)
    
    except Exception as e:
        logger.error(f"Analysis failed for session {request.session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_mock_response(session_id: str, start_time: float) -> AnalyzeResponse:
    """Create mock response for development/testing."""
    import random
    
    num_frames = 50
    base_score = random.uniform(0.05, 0.25)
    
    # Occasionally generate suspicious/fake
    if random.random() < 0.1:
        base_score = random.uniform(0.6, 0.9)
    
    frame_scores = []
    for i in range(num_frames):
        score = base_score + random.uniform(-0.1, 0.1)
        score = max(0, min(1, score))
        
        frame_scores.append(FrameScoreResponse(
            frame_number=i,
            timestamp_ms=i * 200,
            face_detected=random.random() > 0.05,
            face_bbox={'x': 100, 'y': 80, 'width': 200, 'height': 250},
            face_confidence=random.uniform(0.9, 0.99),
            manipulation_score=score,
            is_anomaly=score > 0.7
        ))
    
    return AnalyzeResponse(
        session_id=session_id,
        face_manipulation_score=base_score,
        face_manipulation_confidence=random.uniform(0.8, 0.95),
        lipsync_score=base_score + random.uniform(-0.1, 0.1),
        lipsync_offset_ms=random.randint(-50, 50),
        rppg_quality=random.uniform(0.6, 0.9),
        rppg_heart_rate=random.uniform(60, 100),
        av_correlation_score=base_score + random.uniform(-0.15, 0.1),
        frame_consistency_score=1 - random.uniform(0, 0.2),
        faces_detected=1,
        frames_analyzed=num_frames,
        frame_scores=frame_scores,
        model_versions={
            'face_detector': 'retinaface-r50-mock',
            'deepfake_detector': 'efficientnet-b4-mock',
            'lipsync': 'syncnet-mock',
        },
        processing_time_ms=int((time.time() - start_time) * 1000)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
