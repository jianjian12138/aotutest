from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.projects.models import Project
from .models import RequirementDocument, RequirementAnalysis, BusinessRequirement, GeneratedTestCase

User = get_user_model()


class RequirementAnalysisTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.project = Project.objects.create(
            name='Test Project',
            description='A test project'
        )

    def test_requirement_document_creation(self):
        """测试需求文档创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.status, 'uploaded')

    def test_requirement_analysis_creation(self):
        """测试需求分析创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report='Test analysis report',
            requirements_count=5
        )
        self.assertEqual(analysis.requirements_count, 5)
        self.assertEqual(analysis.document, doc)

    def test_business_requirement_creation(self):
        """测试业务需求创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report='Test analysis report'
        )
        requirement = BusinessRequirement.objects.create(
            analysis=analysis,
            requirement_id='REQ-001',
            requirement_name='Test Requirement',
            requirement_type='functional',
            module='Test Module',
            requirement_level='high',
            description='Test description',
            acceptance_criteria='Test criteria'
        )
        self.assertEqual(requirement.requirement_id, 'REQ-001')
        self.assertEqual(requirement.requirement_type, 'functional')

    def test_generated_test_case_creation(self):
        """测试生成测试用例创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report='Test analysis report'
        )
        requirement = BusinessRequirement.objects.create(
            analysis=analysis,
            requirement_id='REQ-001',
            requirement_name='Test Requirement',
            requirement_type='functional',
            module='Test Module',
            requirement_level='high',
            description='Test description',
            acceptance_criteria='Test criteria'
        )
        test_case = GeneratedTestCase.objects.create(
            requirement=requirement,
            case_id='TC-001',
            title='Test Case Title',
            priority='P1',
            precondition='Test precondition',
            test_steps='Test steps',
            expected_result='Test result'
        )
        self.assertEqual(test_case.case_id, 'TC-001')
        self.assertEqual(test_case.status, 'generated')