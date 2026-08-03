from rest_framework import serializers

from .models import TenantFeature


class TenantFeatureSerializer(serializers.ModelSerializer):
    feature_name = serializers.CharField(read_only=True)

    class Meta:
        model = TenantFeature
        fields = (
            'id',
            'tenant',
            'feature_code',
            'feature_name',
            'enabled',
            'quota',
            'expires_at',
            'updated_at',
        )
        read_only_fields = ('id', 'tenant', 'feature_name', 'updated_at')
