from rest_framework import serializers

from .models import (
    EvalDataset, EvalCase, GraderConfig, EvalRun, EvalResult,
    EvalTrace, EvalTraceStep, EvalPlan, KnowledgeDoc, EvalSchedule, SkillVersion,
    EdgeCaseRule, JudgeStrengthRecord,
)


class EvalCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalCase
        fields = ('id', 'dataset', 'code', 'input_text', 'expected', 'is_edge',
                  'case_role', 'meta', 'created_at')
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
            'model_config_name', 'status', 'is_baseline', 'repeat_k',
            'min_confidence',
            'mean_score', 'pass_rate', 'edge_pass_rate',
            'capability_pass_rate', 'regression_pass_rate',
            'pass_k_rate',
            'cost_tokens_total', 'cost_calls_total', 'latency_avg', 'latency_max',
            'created_at', 'created_by',
        )
        read_only_fields = (
            'id', 'organization', 'status', 'is_baseline', 'mean_score', 'pass_rate',
            'edge_pass_rate', 'capability_pass_rate', 'regression_pass_rate',
            'pass_k_rate',
            'cost_tokens_total', 'cost_calls_total', 'latency_avg', 'latency_max',
            'created_at', 'created_by',
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
            'judges', 'agg_method', 'agg_score', 'agg_passed',
            'repeat_results', 'pass_k',
            'faithfulness_score', 'red_flags', 'confidence',
            'cost_tokens', 'cost_calls', 'latency_first', 'latency_total',
            'review_status', 'reviewer', 'reviewer_name', 'review_note', 'reviewed_at',
        )
        read_only_fields = (
            'id', 'run', 'case', 'case_input', 'case_expected',
            'score', 'passed', 'judge', 'reason',
            'judges', 'agg_method', 'agg_score', 'agg_passed',
            'repeat_results', 'pass_k',
            'faithfulness_score', 'red_flags', 'confidence',
            'cost_tokens', 'cost_calls', 'latency_first', 'latency_total',
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


class EvalPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalPlan
        fields = (
            'id', 'organization', 'title', 'req_text', 'plan_json',
            'status', 'resolved_run_ids', 'created_by', 'created_at',
        )
        read_only_fields = (
            'id', 'organization', 'status', 'resolved_run_ids', 'created_by', 'created_at',
        )


class KnowledgeDocSerializer(serializers.ModelSerializer):
    """P3-13 知识文档：content 写入即自动分块（model.save 计算 chunks）。"""

    chunk_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KnowledgeDoc
        fields = (
            'id', 'organization', 'title', 'source_type', 'content',
            'chunks', 'status', 'chunk_count', 'created_by', 'created_at',
        )
        read_only_fields = (
            'id', 'organization', 'chunks', 'status', 'chunk_count',
            'created_by', 'created_at',
        )

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['created_by'] = user
        return super().create(validated_data)


class EvalScheduleSerializer(serializers.ModelSerializer):
    """P3-16 定时评测调度：租户隔离经 create 注入 organization/created_by。"""

    class Meta:
        model = EvalSchedule
        fields = (
            'id', 'organization', 'name', 'dataset', 'grader', 'agent_config',
            'trigger_type', 'cron', 'interval_minutes', 'daily_at', 'timezone_name',
            'notify_channels', 'enabled', 'repeat_k', 'min_confidence',
            'last_run_at', 'last_run_id', 'last_status', 'last_error',
            'next_run_at', 'created_by', 'created_at',
        )
        read_only_fields = (
            'id', 'organization', 'last_run_at', 'last_run_id', 'last_status',
            'last_error', 'next_run_at', 'created_by', 'created_at',
        )

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['created_by'] = user
        return super().create(validated_data)


class EdgeCaseRuleSerializer(serializers.ModelSerializer):
    """P3-9 边缘用例规则序列化。

    organization / created_by 由视图集注入（perform_create），不通过请求体写入。
    """

    class Meta:
        model = EdgeCaseRule
        fields = (
            'id', 'organization', 'name', 'code', 'category', 'description',
            'enabled', 'params', 'created_by', 'created_at',
        )
        read_only_fields = ('id', 'organization', 'created_by', 'created_at')

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['created_by'] = user
        return super().create(validated_data)


class SkillVersionSerializer(serializers.ModelSerializer):
    """P3-4 评测技能版本序列化。

    只读展示 version/content/content_hash/is_active；发布(publish)由 ViewSet
    动作处理（自动从磁盘快照或自定义 content + 计算 hash）。
    """

    class Meta:
        model = SkillVersion
        fields = (
            'id', 'organization', 'skill_key', 'version', 'content',
            'content_hash', 'is_active', 'note', 'created_by', 'created_at',
        )
        read_only_fields = (
            'id', 'organization', 'content_hash', 'is_active',
            'created_by', 'created_at',
        )

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['created_by'] = user
        return super().create(validated_data)


class JudgeStrengthRecordSerializer(serializers.ModelSerializer):
    """P3-11 评判模型强度校准记录序列化（只读展示）。"""

    class Meta:
        model = JudgeStrengthRecord
        fields = (
            'id', 'organization', 'model_name', 'strength_score',
            'agreement', 'sample_size', 'created_at',
        )
        read_only_fields = (
            'id', 'organization', 'model_name', 'strength_score',
            'agreement', 'sample_size', 'created_at',
        )
