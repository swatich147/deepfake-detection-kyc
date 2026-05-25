"""Lip-sync analysis using audio energy vs mouth-region motion (CPU demo)."""
import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def analyze_lipsync(
    frames: List[np.ndarray],
    face_bboxes: List[Optional[list]],
    audio_path: Optional[str] = None,
) -> Tuple[float, Optional[int]]:
    """
    Estimate lip-sync mismatch score in [0, 1].
    Lower is better (more in sync). Uses mouth-region motion when audio unavailable.
    """
    mouth_motion = _mouth_region_motion(frames, face_bboxes)
    if mouth_motion is None:
        return 0.15, None

    if audio_path:
        try:
            audio_energy = _load_audio_energy(audio_path, len(frames))
            if audio_energy is not None and len(audio_energy) == len(mouth_motion):
                corr = np.corrcoef(
                    _normalize(mouth_motion),
                    _normalize(audio_energy),
                )[0, 1]
                if np.isnan(corr):
                    corr = 0.0
                # Poor correlation => high mismatch score
                return float(max(0.0, min(1.0, 1.0 - (corr + 1) / 2))), None
        except Exception as exc:
            logger.debug("Audio lipsync fallback: %s", exc)

    # Without audio: low motion during "speech" window is mildly suspicious
    motion_std = float(np.std(mouth_motion))
    if motion_std < 0.5:
        return 0.35, None
    return 0.12, None


def _mouth_region_motion(
    frames: List[np.ndarray],
    face_bboxes: List[Optional[list]],
) -> Optional[np.ndarray]:
    values = []
    prev_roi = None

    for frame, bbox in zip(frames, face_bboxes):
        if not bbox:
            values.append(0.0)
            prev_roi = None
            continue

        x1, y1, x2, y2 = [int(v) for v in bbox]
        h = max(1, y2 - y1)
        mouth_y1 = y1 + int(h * 0.6)
        roi = frame[mouth_y1:y2, x1:x2]
        if roi.size == 0:
            values.append(0.0)
            continue

        gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        if prev_roi is not None and prev_roi.shape == gray.shape:
            diff = cv2.absdiff(gray, prev_roi)
            values.append(float(np.mean(diff)))
        else:
            values.append(0.0)
        prev_roi = gray

    if not values:
        return None
    return np.array(values, dtype=np.float32)


def _load_audio_energy(audio_path: str, num_frames: int) -> Optional[np.ndarray]:
    import librosa

    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    if len(y) == 0:
        return None

    frame_length = max(1, len(y) // max(num_frames, 1))
    energies = []
    for i in range(num_frames):
        start = i * frame_length
        end = min(len(y), start + frame_length)
        segment = y[start:end]
        energies.append(float(np.sqrt(np.mean(segment ** 2))) if len(segment) else 0.0)
    return np.array(energies, dtype=np.float32)


def _normalize(values: np.ndarray) -> np.ndarray:
    std = np.std(values)
    if std < 1e-6:
        return values - np.mean(values)
    return (values - np.mean(values)) / std
