"""阶段1.4 缺陷跟踪 序列化器。"""
from rest_framework import serializers
from django.apps import apps
from apps.core_platform.serializers.users import UserSimpleSerializer
from apps.core_platform.serializers.projects import ProjectSimpleSerializer
from .models import Defect, DefectHistory, DEFECT_STATUS_CHOICES, SEVERITY_CHOICES, PRIORITY_CHOICES, TRANSITIONS


# 允许的目标状态（前端流转按钮用）
ALLOWED_TRANSITIONS = {k: sorted(v) for k, v in TRANSITIONS.items()}


class DefectHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True, default='')

    class Meta:
        model = DefectHistory
        fields = ('id', 'from_status', 'to_status', 'actor', 'actor_name', 'comment', 'created_at')
        read_only_fields = fields


class DefectSerializer(serializers.ModelSerializer):
    reporter = UserSimpleSerializer(read_only=True)
    assignee = UserSimpleSerializer(read_only=True)
    project = ProjectSimpleSerializer(read_only=True)
    allowed_transitions = serializers.SerializerMethodField()
    history = DefectHistorySerializer(many=True, read_only=True)
    related_execution_id = serializers.IntegerField(source='related_execution_id', read_only=True)
    related_api_execution_id = serializers.IntegerField(source='related_api_execution_id', read_only=True)

    class Meta:
        model = Defect
        fields = (
            'id', 'title', 'description', 'steps', 'severity', 'priority', 'status',
            'reporter', 'assignee', 'project', 'related_execution_id',
            'related_api_execution_id', 'related_case_info', 'environment',
            'attachments', 'extra', 'allowed_transitions', 'history',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'reporter', 'status', 'allowed_transitions', 'history',
            'created_at', 'updated_at',
        )

    def get_allowed_transitions(self, obj):
        return ALLOWED_TRANSITIONS.get(obj.status, [])


class DefectCreateSerializer(serializers.ModelSerializer):
    related_execution_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    related_api_execution_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Defect
        fields = (
            'id', 'title', 'description', 'steps', 'severity', 'priority',
            'assignee', 'project', 'related_execution_id', 'related_api_execution_id',
            'related_case_info', 'environment', 'attachments',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        rei = attrs.pop('related_execution_id', None)
        raei = attrs.pop('related_api_execution_id', None)
        if rei:
            TestRunCase = apps.get_model('executions', 'TestRunCase')
            attrs['related_execution'] = TestRunCase.objects.filter(pk=rei).first()
        if raei:
            ApiTestCaseExecution = apps.get_model('api_testing', 'ApiTestCaseExecution')
            attrs['related_api_execution'] = ApiTestCaseExecution.objects.filter(pk=raei).first()
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        validated_data['reporter'] = request.user
        validated_data['organization'] = getattr(request.user, 'organization', None)
        defect = super().create(validated_data)
        # 向后兼容：写入 TestRunCase.defects 列表
        if defect.related_execution_id:
            trc = defect.related_execution
            ids = list(trc.defects or [])
            did = str(defect.id)
            if did not in ids:
                ids.append(did)
            trc.defects = ids
            trc.save(update_fields=['defects'])
        return defect


class DefectTransitionSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(choices=[c[0] for c in DEFECT_STATUS_CHOICES])
    comment = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_to_status(self, value):
        defect = self.context['defect']
        if not defect.can_transition(value):
            raise serializers.ValidationError(
                f"非法流转：{defect.status} → {value}（允许：{sorted(TRANSITIONS.get(defect.status, set()))}）"
            )
        return value
