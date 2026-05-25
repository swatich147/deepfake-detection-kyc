"""JWT authentication middleware for WebSocket connections."""
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from urllib.parse import parse_qs


class JWTAuthMiddleware(BaseMiddleware):
    """JWT authentication for WebSocket connections."""
    
    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]
        
        if token:
            scope['user'] = await self.get_user(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, token_str):
        from apps.users.models import User
        
        try:
            token = AccessToken(token_str)
            user_id = token.payload.get('user_id')
            return User.objects.select_related('organization').get(id=user_id)
        except (TokenError, User.DoesNotExist):
            return AnonymousUser()
