"""Deepfake inference pipeline — Phase 1 mock + Phase 2 CPU multi-modal demo."""
import logging
import os
import random
import tempfile
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from config import settings
from pipelines.ensemble import compute_ensemble, verdict_from_score
from pipelines.lipsync import analyze_lipsync
from pipelines.rppg import analyze_rppg

logger = logging.getLogger(__name__)


class InferencePipeline:
    """Multi-modal deepfake detection pipeline (CPU-friendly demo)."""

    def __init__(self, device: str = 'cpu', model_dir: str = './weights'):
        self.device = device
        self.model_dir = model_dir
        self.face_detector = None
        self._load_face_detector()

    def _load_face_detector(self):
        if settings.MOCK_INFERENCE:
            return
        try:
            from insightface.app import FaceAnalysis

            self.face_detector = FaceAnalysis(
                name='buffalo_l',
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider'],
            )
            self.face_detector.prepare(ctx_id=0, det_size=settings.FACE_DET_SIZE)
            logger.info('RetinaFace loaded (InsightFace)')
        except Exception as exc:
            logger.warning('Face detector unavailable, using heuristics: %s', exc)

    async def analyze(self, session_id: str, video_chunks: List[str]) -> dict:
        """Analyze concatenated video chunks and return API response shape."""
        if settings.MOCK_INFERENCE:
            return self._mock_response(session_id)

        video_bytes = self._load_video_bytes(video_chunks)
        if not video_bytes:
            return self._mock_response(session_id, reason='no_video')

        frames = self._decode_video(video_bytes)
        if not frames:
            return self._mock_response(session_id, reason='no_frames')

        face_results = self._detect_faces(frames)
        bboxes = [faces[0]['bbox'] if faces else None for faces in face_results]

        frame_scores = []
        manipulation_scores = []
        for i, (frame, faces) in enumerate(zip(frames, face_results)):
            score = 0.0
            bbox = None
            confidence = None
            if faces:
                bbox_dict = self._bbox_to_dict(faces[0]['bbox'], frame.shape)
                bbox = bbox_dict
                confidence = faces[0]['score']
                score = self._heuristic_manipulation_score(frame, faces[0]['bbox'])

            manipulation_scores.append(score)
            frame_scores.append({
                'frame_number': i,
                'timestamp_ms': int(i * (1000 / settings.FPS_EXTRACTION)),
                'face_detected': bool(faces),
                'face_bbox': bbox,
                'face_confidence': confidence,
                'manipulation_score': round(score, 4),
                'is_anomaly': score > settings.SUSPICIOUS_THRESHOLD,
            })

        face_score = float(np.mean(manipulation_scores)) if manipulation_scores else 0.2
        frame_consistency = 1.0 - float(np.std(manipulation_scores)) if len(manipulation_scores) > 1 else 0.9

        audio_path = self._extract_audio(video_bytes)
        lipsync_score, lipsync_offset = analyze_lipsync(frames, bboxes, audio_path)
        rppg_quality, heart_rate = analyze_rppg(frames, bboxes)
        av_score = max(0.0, min(1.0, (lipsync_score + (1 - rppg_quality)) / 2))

        ensemble = compute_ensemble({
            'face_manipulation': face_score,
            'lipsync': lipsync_score,
            'rppg_quality': rppg_quality,
            'av_correlation': av_score,
            'frame_consistency': frame_consistency,
        })

        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)

        model_versions = {
            'face_detector': 'retinaface-buffalo_l' if self.face_detector else 'heuristic-v1',
            'deepfake_detector': 'heuristic-cpu-v1',
            'lipsync': 'motion-audio-v1',
            'rppg': 'pos-simplified-v1',
            'ensemble': 'weighted-v1',
        }

        return {
            'session_id': session_id,
            'face_manipulation_score': ensemble['face_manipulation_score'],
            'face_manipulation_confidence': min(0.95, 0.7 + rppg_quality * 0.25),
            'lipsync_score': ensemble['lipsync_score'],
            'lipsync_offset_ms': lipsync_offset,
            'rppg_quality': ensemble['rppg_quality'],
            'rppg_heart_rate': heart_rate,
            'av_correlation_score': ensemble['av_correlation_score'],
            'frame_consistency_score': ensemble['frame_consistency_score'],
            'faces_detected': sum(1 for f in face_results if f),
            'frames_analyzed': len(frames),
            'frame_scores': frame_scores,
            'model_versions': model_versions,
            'overall_score': ensemble['overall_score'],
            'verdict': verdict_from_score(ensemble['overall_score']),
        }

    def _load_video_bytes(self, video_chunks: List[str]) -> bytes:
        parts = []
        for chunk_path in sorted(video_chunks, key=lambda p: Path(p).name):
            path = Path(chunk_path)
            candidates = [
                path,
                Path('/app/media') / path.name,
                Path('/app/media/chunks') / path.parent.name / path.name if path.parent.name else path,
            ]
            # Full path like .../chunks/<session_id>/0000.webm
            if 'chunks' in str(path):
                parts_idx = str(path).split('chunks')
                if len(parts_idx) > 1:
                    candidates.append(Path('/app/media/chunks') / parts_idx[-1].lstrip('/'))

            resolved = next((c for c in candidates if c.is_file()), None)
            if resolved:
                parts.append(resolved.read_bytes())
            else:
                logger.warning('Chunk not found: %s', chunk_path)
        return b''.join(parts)

    def _decode_video(self, video_data: bytes) -> List[np.ndarray]:
        frames = []
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            tmp.write(video_data)
            temp_path = tmp.name

        try:
            cap = cv2.VideoCapture(temp_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            interval = max(1, int(fps / settings.FPS_EXTRACTION))
            idx = 0
            while cap.isOpened() and len(frames) < 100:
                ret, frame = cap.read()
                if not ret:
                    break
                if idx % interval == 0:
                    frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                idx += 1
            cap.release()
        finally:
            os.unlink(temp_path)
        return frames

    def _detect_faces(self, frames: List[np.ndarray]) -> list:
        results = []
        for frame in frames:
            if self.face_detector:
                try:
                    faces = self.face_detector.get(frame)
                    results.append([
                        {
                            'bbox': face.bbox.tolist(),
                            'score': float(face.det_score),
                        }
                        for face in faces
                        if face.det_score >= settings.FACE_CONF_THRESHOLD
                    ])
                except Exception:
                    results.append([])
            else:
                h, w = frame.shape[:2]
                results.append([{
                    'bbox': [w * 0.3, h * 0.2, w * 0.7, h * 0.8],
                    'score': 0.95,
                }])
        return results

    def _heuristic_manipulation_score(self, frame: np.ndarray, bbox: list) -> float:
        """Artifact heuristics when no trained model weights are available."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        if crop.size == 0:
            return 0.1

        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0) / edges.size)
        hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
        sat_std = float(np.std(hsv[:, :, 1]) / 100.0)

        score = edge_density * 0.4 + min(sat_std, 1.0) * 0.2
        return max(0.05, min(0.85, score + random.uniform(-0.05, 0.05)))

    def _bbox_to_dict(self, bbox: list, shape: tuple) -> dict:
        x1, y1, x2, y2 = bbox
        return {
            'x': int(x1),
            'y': int(y1),
            'width': int(x2 - x1),
            'height': int(y2 - y1),
        }

    def _extract_audio(self, video_data: bytes) -> Optional[str]:
        try:
            import subprocess

            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as vid:
                vid.write(video_data)
                video_path = vid.name

            audio_path = video_path.replace('.webm', '.wav')
            subprocess.run(
                [
                    'ffmpeg', '-y', '-i', video_path,
                    '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                    audio_path,
                ],
                capture_output=True,
                timeout=30,
                check=False,
            )
            os.unlink(video_path)
            if os.path.exists(audio_path):
                return audio_path
        except Exception as exc:
            logger.debug('Audio extraction skipped: %s', exc)
        return None

    def _mock_response(self, session_id: str, reason: str = '') -> dict:
        if reason:
            logger.warning('Mock fallback for session %s: %s', session_id, reason)

        num_frames = 50
        base_score = random.uniform(0.05, 0.25)
        if random.random() < 0.1:
            base_score = random.uniform(0.6, 0.9)

        frame_scores = []
        for i in range(num_frames):
            score = max(0, min(1, base_score + random.uniform(-0.1, 0.1)))
            frame_scores.append({
                'frame_number': i,
                'timestamp_ms': i * 200,
                'face_detected': random.random() > 0.05,
                'face_bbox': {'x': 100, 'y': 80, 'width': 200, 'height': 250},
                'face_confidence': random.uniform(0.9, 0.99),
                'manipulation_score': score,
                'is_anomaly': score > 0.7,
            })

        lipsync = base_score + random.uniform(-0.1, 0.1)
        rppg_q = random.uniform(0.6, 0.9)
        ensemble = compute_ensemble({
            'face_manipulation': base_score,
            'lipsync': lipsync,
            'rppg_quality': rppg_q,
            'av_correlation': base_score + random.uniform(-0.15, 0.1),
            'frame_consistency': 1 - random.uniform(0, 0.2),
        })

        return {
            'session_id': session_id,
            'face_manipulation_score': ensemble['face_manipulation_score'],
            'face_manipulation_confidence': random.uniform(0.8, 0.95),
            'lipsync_score': ensemble['lipsync_score'],
            'lipsync_offset_ms': random.randint(-50, 50),
            'rppg_quality': ensemble['rppg_quality'],
            'rppg_heart_rate': random.uniform(60, 100),
            'av_correlation_score': ensemble['av_correlation_score'],
            'frame_consistency_score': ensemble['frame_consistency_score'],
            'faces_detected': 1,
            'frames_analyzed': num_frames,
            'frame_scores': frame_scores,
            'model_versions': {
                'face_detector': 'mock',
                'deepfake_detector': 'mock',
                'lipsync': 'mock',
                'rppg': 'mock',
            },
            'overall_score': ensemble['overall_score'],
            'verdict': verdict_from_score(ensemble['overall_score']),
        }
