from rest_framework import serializers

from .models import (
    EvalDataset, EvalCase, GraderConfig, EvalRun, EvalResult,
    EvalTrace, EvalTraceStep,
)


class EvalCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalCase
        fields = ('id', 'dataset', 'code', 'input_text', 'expected', 'is_edge', 'meta', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_is_edge(self, value):
        return value


class EvalDatasetSerializer(serializers.ModelSerializer):
    edge_ratio = serializers.FloatField(read_only=True)
    case_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EvalDataset
        fields = (
            'id', 'organization', 'name', 'description', 'version',
            'edge_ratio', 'case_count', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'organization', 'edge_ratio', 'case_count', 'created_at', 'updated_at',
        )

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['created_by'] = user
        return super().create(validated_data)


class GraderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraderConfig
        fields = (
            'id', 'organization', 'name', 'grader_type', 'rubric',
            'pass_threshold', 'created_at',
        )
        read_only_fields = ('id', 'organization', 'created_at')

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['created_by'] = user
        return super().create(validated_data)


class EvalRunSerializer(serializers.ModelSerializer):
    model_config_name = serializers.CharField(
        source='model_config.model_name', read_only=True, default=None
    )

    class Meta:
        model = EvalRun
        fields = (
            'id', 'organization', 'dataset', 'grader', 'model_config',
            'model_config_name', 'status',
            'mean_score', 'pass_rate', 'edge_pass_rate', 'created_at', 'created_by',
        )
        read_only_fields = (
            'id', 'organization', 'status', 'mean_score', 'pass_rate',
            'edge_pass_rate', 'created_at', 'created_by',
        )


class EvalResultSerializer(serializers.ModelSerializer):
    case_input = serializers.CharField(source='case.input_text', read_only=True)
    case_expected = serializers.CharField(source='case.expected', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)

    class Meta:
        model = EvalResult
        fields = (
            'id', 'run', 'case', 'case_input', 'case_expected',
            'score', 'passed', 'judge', 'reason',
            'review_status', 'reviewer', 'reviewer_name', 'review_note', 'reviewed_at',
        )
        read_only_fields = (
            'id', 'run', 'case', 'case_input', 'case_expected',
            'score', 'passed', 'judge', 'reason',
            'reviewer', 'reviewer_name', 'reviewed_at',
        )


class EvalTraceStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalTraceStep
        fields = (
            'id', 'step_index', 'step_type', 'name',
            'input_data', 'output_data', 'latency_ms', 'error',
        )
        read_only_fields = ('id',)


class EvalTraceSerializer(serializers.ModelSerializer):
    steps = EvalTraceStepSerializer(many=True, required=False)

    class Meta:
        model = EvalTrace
        fields = (
            'id', 'run', 'case', 'status', 'total_latency_ms',
            'steps', 'created_at', 'finished_at',
        )
        read_only_fields = ('id', 'created_at', 'finished_at')

    def create(self, validated_data):
        user = self.context['request'].user
        # 防止越权：trace 只能挂在当前用户所属租户拥有的 run 上
        run = validated_data.get('run')
        if run is None or run.organization_id != getattr(user.organization, 'id', None):
            from rest_framework.serializers import ValidationError
            raise ValidationError('trace 只能关联到本租户拥有的评测运行')
        steps = validated_data.pop('steps', []) or []
        trace = EvalTrace.objects.create(**validated_data)
        for s in steps:
            EvalTraceStep.objects.create(trace=trace, **s)
        return trace
