"""Ensemble scoring for multi-modal deepfake detection."""
from typing import Dict


WEIGHTS = {
    'face_manipulation': 0.35,
    'lipsync': 0.25,
    'rppg': 0.20,
    'av_correlation': 0.10,
    'consistency': 0.10,
}


def compute_ensemble(scores: Dict[str, float]) -> Dict[str, float]:
    """Combine modality scores into overall fraud score and consistency."""
    face = scores.get('face_manipulation', 0.0)
    lipsync = scores.get('lipsync', 0.0)
    rppg_quality = scores.get('rppg_quality', 0.5)
    rppg_risk = 1.0 - rppg_quality
    av = scores.get('av_correlation', 0.0)
    consistency = scores.get('frame_consistency', 1.0)
    consistency_risk = 1.0 - consistency

    overall = (
        WEIGHTS['face_manipulation'] * face
        + WEIGHTS['lipsync'] * lipsync
        + WEIGHTS['rppg'] * rppg_risk
        + WEIGHTS['av_correlation'] * av
        + WEIGHTS['consistency'] * consistency_risk
    )
    overall = max(0.0, min(1.0, overall))

    return {
        'overall_score': overall,
        'face_manipulation_score': face,
        'lipsync_score': lipsync,
        'rppg_quality': rppg_quality,
        'av_correlation_score': av,
        'frame_consistency_score': consistency,
    }


def verdict_from_score(score: float) -> str:
    if score < 0.3:
        return 'genuine'
    if score < 0.7:
        return 'suspicious'
    return 'fake'
