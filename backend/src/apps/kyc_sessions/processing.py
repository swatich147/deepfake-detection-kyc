"""Synchronous session processing — replaces Celery for demo/local use."""
import logging
import threading

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

logger = logging.getLogger(__name__)


def process_video(session_id: str) -> dict:
    """Process uploaded video chunks and trigger analysis."""
    from .models import KYCSession, VideoChunk

    try:
        session = KYCSession.objects.get(id=session_id)

        if session.status != 'processing':
            logger.warning("Session %s not in processing state", session_id)
            return {'status': 'skipped', 'reason': 'Invalid state'}

        chunks = VideoChunk.objects.filter(session=session).order_by('chunk_index')
        if not chunks.exists():
            logger.error("No video chunks found for session %s", session_id)
            session.status = 'failed'
            session.save(update_fields=['status', 'updated_at'])
            return {'status': 'failed', 'reason': 'No video chunks'}

        total_size = sum(c.size_bytes or 0 for c in chunks)
        session.video_size_bytes = total_size
        session.save(update_fields=['video_size_bytes', 'updated_at'])

        return analyze_session(session_id)

    except KYCSession.DoesNotExist:
        logger.error("Session %s not found", session_id)
        return {'status': 'failed', 'reason': 'Session not found'}


def analyze_session(session_id: str) -> dict:
    """Run AI analysis on a KYC session."""
    from .models import KYCSession
    from apps.analysis.services import AnalysisService

    try:
        session = KYCSession.objects.get(id=session_id)
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f'session_{session_id}',
            {
                'type': 'analysis_update',
                'data': {'status': 'analyzing', 'progress': 0},
            },
        )

        result = AnalysisService().analyze(session)

        session.status = 'completed' if result.verdict != 'fake' else 'flagged'
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at', 'updated_at'])

        session.refresh_from_db()
        from .webhooks import send_session_webhook
        send_session_webhook(session)

        async_to_sync(channel_layer.group_send)(
            f'session_{session_id}',
            {
                'type': 'analysis_complete',
                'result': {
                    'overall_score': float(result.overall_score),
                    'verdict': result.verdict,
                    'session_id': str(session_id),
                },
            },
        )

        logger.info("Analysis completed for session %s: %s", session_id, result.verdict)
        return {'status': 'success', 'verdict': result.verdict}

    except KYCSession.DoesNotExist:
        logger.error("Session %s not found for analysis", session_id)
        return {'status': 'failed', 'reason': 'Session not found'}

    except Exception as exc:
        logger.error("Error analyzing session %s: %s", session_id, exc)
        try:
            session = KYCSession.objects.get(id=session_id)
            session.status = 'failed'
            session.save(update_fields=['status', 'updated_at'])
        except KYCSession.DoesNotExist:
            pass
        raise


def schedule_processing(session_id: str) -> None:
    """Run processing without blocking the WebSocket handler."""
    thread = threading.Thread(
        target=process_video,
        args=(str(session_id),),
        daemon=True,
        name=f'kyc-process-{session_id}',
    )
    thread.start()
