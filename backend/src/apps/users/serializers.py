"""User serializers."""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    """Organization serializer."""
    
    class Meta:
        model = Organization
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    """User serializer."""
    organization = OrganizationSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'organization', 'created_at']
        read_only_fields = ['id', 'created_at']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data."""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user data to response
        data['user'] = UserSerializer(self.user).data
        data['expires_in'] = int(self.token_class.lifetime.total_seconds())
        
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """User registration serializer."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    organization_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'organization_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        org_name = validated_data.pop('organization_name', None)
        
        # Create or get organization
        if org_name:
            org = Organization.objects.create(name=org_name, api_secret_hash='pending')
        else:
            org, _ = Organization.objects.get_or_create(
                name='Default Organization',
                defaults={'api_secret_hash': 'demo'},
            )
        
        user = User.objects.create_user(
            organization=org,
            role='admin' if org_name else 'operator',
            **validated_data
        )
        return user
