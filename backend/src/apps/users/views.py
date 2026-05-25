"""User views."""
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    UserSerializer, 
    CustomTokenObtainPairSerializer, 
    RegisterSerializer
)


class LoginView(TokenObtainPairView):
    """Custom login view with user data."""
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """User registration."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'expires_in': int(refresh.access_token.lifetime.total_seconds()),
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """Logout (client-side token discard; no blacklist in demo mode)."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Logged out successfully'})


class MeView(generics.RetrieveUpdateAPIView):
    """Get/update current user."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
