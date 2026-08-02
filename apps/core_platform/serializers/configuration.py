from rest_framework import serializers
from ..models import GlobalParameter, CommonMethod

class GlobalParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalParameter
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')

class CommonMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommonMethod
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')
