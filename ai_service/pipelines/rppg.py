"""Remote photoplethysmography (rPPG) — simplified POS-style signal for demo."""
import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def analyze_rppg(
    frames: List[np.ndarray],
    face_bboxes: List[Optional[list]],
) -> Tuple[float, Optional[float]]:
    """
    Extract pulse signal quality and estimated heart rate from face ROI.
    Returns (quality 0-1, heart_rate bpm or None).
    """
    signal = _extract_green_channel_signal(frames, face_bboxes)
    if signal is None or len(signal) < 10:
        return 0.4, None

    signal = signal - np.mean(signal)
    if np.std(signal) < 1e-6:
        return 0.3, None

    # Bandpass via FFT (0.75–3 Hz ≈ 45–180 BPM at 5 FPS sampling)
    fps = 5.0
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / fps)
    spectrum = np.abs(np.fft.rfft(signal))
    mask = (freqs >= 0.75) & (freqs <= 3.0)
    if not np.any(mask):
        return 0.35, None

    band = spectrum.copy()
    band[~mask] = 0
    peak_idx = int(np.argmax(band))
    peak_freq = float(freqs[peak_idx])
    heart_rate = peak_freq * 60.0

    total_power = float(np.sum(spectrum[1:]) + 1e-8)
    band_power = float(np.sum(band[1:]))
    quality = min(1.0, band_power / total_power * 2.5)

    if heart_rate < 45 or heart_rate > 180:
        quality *= 0.5
        return quality, None

    return quality, round(heart_rate, 1)


def _extract_green_channel_signal(
    frames: List[np.ndarray],
    face_bboxes: List[Optional[list]],
) -> Optional[np.ndarray]:
    values = []
    for frame, bbox in zip(frames, face_bboxes):
        if not bbox:
            continue
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h = max(1, y2 - y1)
        # Forehead/cheek ROI — less motion than mouth
        roi = frame[y1 + int(h * 0.2): y1 + int(h * 0.55), x1:x2]
        if roi.size == 0:
            continue
        values.append(float(np.mean(roi[:, :, 1])))

    if len(values) < 5:
        return None
    return np.array(values, dtype=np.float32)
