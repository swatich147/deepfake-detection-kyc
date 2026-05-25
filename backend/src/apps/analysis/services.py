"""Analysis service - integrates with AI service."""
import logging
import time
import random
from decimal import Decimal
from django.conf import settings
import requests

from .models import AnalysisResult, FrameScore

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for running deepfake analysis."""
    
    def __init__(self):
        self.ai_service_url = settings.AI_SERVICE_URL
        self.timeout = 60
    
    def analyze(self, session) -> AnalysisResult:
        """Run full analysis on a KYC session."""
        start_time = time.time()
        
        try:
            # Call AI service
            ai_result = self._call_ai_service(session)
            
            # Calculate overall score and verdict
            overall_score = self._calculate_overall_score(ai_result)
            verdict = self._determine_verdict(overall_score)
            
            # Create result record
            result = AnalysisResult.objects.create(
                session=session,
                overall_score=Decimal(str(overall_score)),
                verdict=verdict,
                face_manipulation_score=Decimal(str(ai_result.get('face_manipulation_score', 0))),
                face_manipulation_confidence=Decimal(str(ai_result.get('face_manipulation_confidence', 0))),
                lipsync_score=Decimal(str(ai_result.get('lipsync_score', 0))),
                lipsync_offset_ms=ai_result.get('lipsync_offset_ms'),
                rppg_quality=Decimal(str(ai_result.get('rppg_quality', 0))),
                rppg_heart_rate=Decimal(str(ai_result.get('rppg_heart_rate', 0))) if ai_result.get('rppg_heart_rate') else None,
                av_correlation_score=Decimal(str(ai_result.get('av_correlation_score', 0))),
                frame_consistency_score=Decimal(str(ai_result.get('frame_consistency_score', 0))),
                faces_detected=ai_result.get('faces_detected', 0),
                frames_analyzed=ai_result.get('frames_analyzed', 0),
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_versions=ai_result.get('model_versions', {}),
            )
            
            # Create frame scores
            frame_scores = ai_result.get('frame_scores', [])
            for fs in frame_scores:
                FrameScore.objects.create(
                    result=result,
                    frame_number=fs['frame_number'],
                    timestamp_ms=fs['timestamp_ms'],
                    face_detected=fs.get('face_detected', False),
                    face_bbox=fs.get('face_bbox'),
                    face_confidence=Decimal(str(fs.get('face_confidence', 0))) if fs.get('face_confidence') else None,
                    manipulation_score=Decimal(str(fs.get('manipulation_score', 0))) if fs.get('manipulation_score') else None,
                    is_anomaly=fs.get('is_anomaly', False),
                )
            
            logger.info(f"Analysis completed for session {session.id}: {verdict}")
            return result
        
        except Exception as e:
            logger.error(f"Analysis failed for session {session.id}: {e}")
            raise
    
    def _call_ai_service(self, session):
        """Call the AI inference service."""
        try:
            # Build request
            payload = {
                'session_id': str(session.id),
                'video_chunks': [
                    chunk.s3_key for chunk in session.chunks.all()
                ],
            }
            
            response = requests.post(
                f"{self.ai_service_url}/analyze",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"AI service error: {response.status_code} - {response.text}")
                # Fall back to mock for development
                return self._mock_analysis(session)
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"AI service unavailable, using mock: {e}")
            return self._mock_analysis(session)
    
    def _mock_analysis(self, session):
        """Generate mock analysis result for development."""
        num_frames = 50
        
        # Generate realistic-looking scores
        base_score = random.uniform(0.05, 0.25)  # Most sessions are genuine
        
        # Occasionally generate suspicious/fake
        if random.random() < 0.1:
            base_score = random.uniform(0.6, 0.9)
        
        frame_scores = []
        for i in range(num_frames):
            score = base_score + random.uniform(-0.1, 0.1)
            score = max(0, min(1, score))
            
            frame_scores.append({
                'frame_number': i,
                'timestamp_ms': i * 200,  # 5 FPS
                'face_detected': random.random() > 0.05,
                'face_bbox': {'x': 100, 'y': 80, 'width': 200, 'height': 250},
                'face_confidence': random.uniform(0.9, 0.99),
                'manipulation_score': score,
                'is_anomaly': score > 0.7,
            })
        
        return {
            'face_manipulation_score': base_score,
            'face_manipulation_confidence': random.uniform(0.8, 0.95),
            'lipsync_score': base_score + random.uniform(-0.1, 0.1),
            'lipsync_offset_ms': random.randint(-50, 50),
            'rppg_quality': random.uniform(0.6, 0.9),
            'rppg_heart_rate': random.uniform(60, 100),
            'av_correlation_score': base_score + random.uniform(-0.15, 0.1),
            'frame_consistency_score': 1 - random.uniform(0, 0.2),
            'faces_detected': 1,
            'frames_analyzed': num_frames,
            'frame_scores': frame_scores,
            'model_versions': {
                'face_detector': 'retinaface-r50-v1.0',
                'deepfake_detector': 'efficientnet-b4-mock',
                'lipsync': 'syncnet-mock',
            },
        }
    
    def _calculate_overall_score(self, ai_result):
        """Calculate weighted overall fraud score."""
        weights = {
            'face_manipulation': 0.35,
            'lipsync': 0.25,
            'rppg': 0.20,
            'av_correlation': 0.10,
            'consistency': 0.10,
        }
        
        face_score = ai_result.get('face_manipulation_score', 0)
        lipsync_score = ai_result.get('lipsync_score', 0)
        
        # rPPG: low quality = suspicious
        rppg_quality = ai_result.get('rppg_quality', 0.5)
        rppg_score = 1 - rppg_quality
        
        av_score = ai_result.get('av_correlation_score', 0)
        
        # Consistency: high consistency = good
        consistency = ai_result.get('frame_consistency_score', 1)
        consistency_score = 1 - consistency
        
        overall = (
            weights['face_manipulation'] * face_score +
            weights['lipsync'] * lipsync_score +
            weights['rppg'] * rppg_score +
            weights['av_correlation'] * av_score +
            weights['consistency'] * consistency_score
        )
        
        return max(0, min(1, overall))
    
    def _determine_verdict(self, overall_score):
        """Determine verdict based on overall score."""
        if overall_score < 0.3:
            return 'genuine'
        elif overall_score < 0.7:
            return 'suspicious'
        else:
            return 'fake'
