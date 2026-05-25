"""Challenge-response liveness with nonce and anti-replay (Phase 4 demo)."""
import secrets
from datetime import timedelta

from django.utils import timezone


def build_challenge_payload(challenge_type: str, instructions_data: dict) -> dict:
    """Attach nonce and timestamp for anti-replay validation."""
    return {
        **instructions_data,
        'nonce': secrets.token_hex(16),
        'issued_at': timezone.now().isoformat(),
        'min_recording_seconds': 10,
        'type': challenge_type,
    }


def validate_stop_recording(session, chunk_count: int, total_bytes: int) -> tuple[bool, str]:
    """
    Validate session can proceed to analysis.
    Returns (ok, error_message).
    """
    if chunk_count < 1:
        return False, 'No video data received'

    if total_bytes < 10_000:
        return False, 'Video too short — record at least 10 seconds'

    challenge = session.challenge_data or {}
    nonce = challenge.get('nonce')
    if session.challenge_type != 'none' and not nonce:
        return False, 'Invalid challenge — missing nonce'

    issued_at = challenge.get('issued_at')
    if issued_at:
        from django.utils.dateparse import parse_datetime
        issued = parse_datetime(issued_at)
        if issued and timezone.now() - issued > timedelta(minutes=15):
            return False, 'Challenge expired — start a new session'

    metadata = session.metadata or {}
    if not metadata.get('consent_given'):
        return False, 'Consent required before recording'

    return True, ''
