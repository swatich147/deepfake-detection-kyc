"""WebSocket consumer for video streaming."""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
logger = logging.getLogger(__name__)


class VideoStreamConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for video chunk streaming."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.user = self.scope.get('user')
        self.room_group_name = f'session_{self.session_id}'
        
        # Validate user
        if not self.user or not self.user.is_authenticated:
            logger.warning(f"Unauthorized WebSocket connection attempt for session {self.session_id}")
            await self.close(code=4001)
            return
        
        # Validate session
        session = await self._get_session()
        if not session:
            logger.warning(f"Session {self.session_id} not found")
            await self.close(code=4004)
            return
        
        if session.organization_id != self.user.organization_id:
            logger.warning(f"User {self.user.id} unauthorized for session {self.session_id}")
            await self.close(code=4003)
            return
        
        if session.status not in ['pending', 'recording']:
            logger.warning(f"Session {self.session_id} in invalid state: {session.status}")
            await self.close(code=4000)
            return
        
        self.session = session
        self.chunk_count = 0
        self.total_bytes = 0
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected for session {self.session_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected for session {self.session_id} with code {close_code}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages."""
        try:
            if bytes_data:
                # Video chunk received
                await self._handle_video_chunk(bytes_data)
            
            elif text_data:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'start_recording':
                    await self._handle_start_recording(data)
                
                elif message_type == 'stop_recording':
                    await self._handle_stop_recording(data)
                
                elif message_type == 'ping':
                    await self.send(text_data=json.dumps({'type': 'pong'}))
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'code': 'PROCESSING_ERROR',
                'message': str(e)
            }))
    
    async def _handle_video_chunk(self, data):
        """Save video chunk to storage."""
        try:
            # Save chunk (in production, use S3)
            chunk_key = await self._save_chunk(data)
            
            self.chunk_count += 1
            self.total_bytes += len(data)
            
            await self.send(text_data=json.dumps({
                'type': 'chunk_received',
                'chunk_index': self.chunk_count - 1,
                'size_bytes': len(data),
                'total_received_bytes': self.total_bytes
            }))
            
            logger.debug(f"Chunk {self.chunk_count} received for session {self.session_id}")
        
        except Exception as e:
            logger.error(f"Error saving chunk: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'code': 'CHUNK_SAVE_ERROR',
                'message': 'Failed to save video chunk'
            }))
    
    async def _handle_start_recording(self, data):
        """Handle start recording — requires consent (Phase 3 GDPR demo)."""
        if not data.get('consent_given'):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'code': 'CONSENT_REQUIRED',
                'message': 'You must accept the privacy consent before recording',
            }))
            return

        await self._save_consent(data.get('consent_given', False))
        await self._update_session_status('recording')
        
        await self.send(text_data=json.dumps({
            'type': 'recording_started',
            'timestamp': self._get_timestamp()
        }))
        
        logger.info(f"Recording started for session {self.session_id}")
    
    async def _handle_stop_recording(self, data):
        """Handle stop recording with challenge anti-replay checks (Phase 4)."""
        from .challenge import validate_stop_recording

        self.session = await self._get_session()
        ok, message = validate_stop_recording(self.session, self.chunk_count, self.total_bytes)
        if not ok:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'code': 'VALIDATION_FAILED',
                'message': message,
            }))
            return

        # Optional client nonce echo
        client_nonce = data.get('nonce')
        challenge = self.session.challenge_data or {}
        if challenge.get('nonce') and client_nonce and client_nonce != challenge.get('nonce'):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'code': 'NONCE_MISMATCH',
                'message': 'Challenge replay detected',
            }))
            return

        await self._update_session_status('processing')
        
        await self.send(text_data=json.dumps({
            'type': 'processing_started',
            'chunks_received': self.chunk_count,
            'total_bytes': self.total_bytes
        }))
        
        await self._trigger_processing()
        
        logger.info(f"Recording stopped, processing started for session {self.session_id}")
    
    # Handler for group messages (from Celery tasks)
    async def analysis_update(self, event):
        """Send analysis update to client."""
        await self.send(text_data=json.dumps({
            'type': 'analysis_update',
            'data': event['data']
        }))
    
    async def analysis_complete(self, event):
        """Send analysis complete to client."""
        await self.send(text_data=json.dumps({
            'type': 'analysis_complete',
            'result': event['result']
        }))
    
    # Database operations
    @database_sync_to_async
    def _get_session(self):
        from .models import KYCSession
        try:
            return KYCSession.objects.select_related('organization').get(id=self.session_id)
        except KYCSession.DoesNotExist:
            return None
    
    @database_sync_to_async
    def _save_consent(self, consent: bool):
        from .models import KYCSession
        session = KYCSession.objects.get(id=self.session_id)
        metadata = session.metadata or {}
        metadata['consent_given'] = consent
        metadata['consent_at'] = self._get_timestamp()
        session.metadata = metadata
        session.save(update_fields=['metadata', 'updated_at'])
        self.session = session

    @database_sync_to_async
    def _update_session_status(self, status):
        from .models import KYCSession
        KYCSession.objects.filter(id=self.session_id).update(status=status)
    
    @database_sync_to_async
    def _save_chunk(self, data):
        from .models import VideoChunk
        from django.conf import settings
        import os
        
        if getattr(settings, 'USE_S3_STORAGE', False):
            import boto3

            s3 = boto3.client('s3')
            chunk_key = f'chunks/{self.session_id}/{self.chunk_count:04d}.webm'
            s3.put_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=chunk_key,
                Body=data,
                ContentType='video/webm',
            )
        else:
            chunk_dir = settings.MEDIA_ROOT / 'chunks' / str(self.session_id)
            os.makedirs(chunk_dir, exist_ok=True)
            chunk_path = chunk_dir / f'{self.chunk_count:04d}.webm'
            with open(chunk_path, 'wb') as f:
                f.write(data)
            chunk_key = str(chunk_path)
        
        # Save chunk record
        VideoChunk.objects.create(
            session_id=self.session_id,
            chunk_index=self.chunk_count,
            s3_key=chunk_key,
            size_bytes=len(data)
        )
        
        return chunk_key
    
    @database_sync_to_async
    def _trigger_processing(self):
        from .processing import schedule_processing
        schedule_processing(str(self.session_id))
    
    def _get_timestamp(self):
        from django.utils import timezone
        return timezone.now().isoformat()
