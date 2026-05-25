"""Optional webhook delivery (Phase 3 demo — no external queue)."""
import hashlib
import hmac
import json
import logging
import threading

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_session_webhook(session, event_type: str = 'session.completed') -> None:
    """POST webhook in background if organization has webhook_url configured."""
    org = session.organization
    if not org.webhook_url:
        return

    thread = threading.Thread(
        target=_deliver,
        args=(session, event_type),
        daemon=True,
        name=f'webhook-{session.id}',
    )
    thread.start()


def _deliver(session, event_type: str) -> None:
    org = session.organization
    payload = {
        'event': event_type,
        'timestamp': timezone.now().isoformat(),
        'data': {
            'session_id': str(session.id),
            'external_reference': session.external_reference,
            'status': session.status,
        },
    }

    if hasattr(session, 'analysis_result') and session.analysis_result:
        payload['data']['verdict'] = session.analysis_result.verdict
        payload['data']['overall_score'] = float(session.analysis_result.overall_score)

    payload_json = json.dumps(payload, sort_keys=True)
    timestamp = str(int(timezone.now().timestamp()))
    signature = ''
    if org.webhook_secret:
        signature_payload = f'{timestamp}.{payload_json}'
        signature = hmac.new(
            org.webhook_secret.encode(),
            signature_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    try:
        response = requests.post(
            org.webhook_url,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Webhook-Timestamp': timestamp,
                'X-Webhook-Signature': f'sha256={signature}',
            },
            timeout=10,
        )
        logger.info('Webhook %s for session %s: HTTP %s', event_type, session.id, response.status_code)
    except requests.RequestException as exc:
        logger.warning('Webhook failed for session %s: %s', session.id, exc)
