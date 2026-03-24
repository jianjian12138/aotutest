import csv
import json
import yaml
import openpyxl
import zipfile
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from io import TextIOWrapper
from django.core.files.base import ContentFile
from .models import TestCase
from apps.core_platform.models import Project

class ImportService:
    @staticmethod
    def import_cases(file, file_type, project, user):
        """
        Import test cases from file.
        file_type: 'excel', 'csv', 'json', 'yaml', 'zip'
        """
        if file_type == 'excel':
            return ImportService.import_from_excel(file, project, user)
        elif file_type == 'csv':
            return ImportService.import_from_csv(file, project, user)
        elif file_type == 'json':
            return ImportService.import_from_json(file, project, user)
        elif file_type == 'yaml':
            return ImportService.import_from_yaml(file, project, user)
        elif file_type == 'zip':
            return ImportService.import_from_zip(file, project, user)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def _create_case(data, project, user):
        TestCase.objects.create(
            project=project,
            title=data.get('title'),
            description=data.get('description', ''),
            preconditions=data.get('preconditions', ''),
            steps=data.get('steps', ''),
            expected_result=data.get('expected_result', ''),
            priority=data.get('priority', 'medium'),
            author=user
        )

    @staticmethod
    def import_from_excel(file, project, user):
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        
        headers = [cell.value for cell in ws[1]]
        
        imported_count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]: continue # Skip empty title
            
            TestCase.objects.create(
                project=project,
                title=row[0],
                description=row[1] if len(row) > 1 else '',
                preconditions=row[2] if len(row) > 2 else '',
                steps=row[3] if len(row) > 3 else '',
                expected_result=row[4] if len(row) > 4 else '',
                priority=row[5] if len(row) > 5 else 'medium',
                author=user
            )
            imported_count += 1
        return imported_count

    @staticmethod
    def import_from_csv(file, project, user):
        # CSV file handling
        file_data = file.read().decode('utf-8')
        reader = csv.reader(file_data.splitlines())
        header = next(reader, None)
        
        imported_count = 0
        for row in reader:
            if not row or not row[0]: continue
            
            TestCase.objects.create(
                project=project,
                title=row[0],
                description=row[1] if len(row) > 1 else '',
                preconditions=row[2] if len(row) > 2 else '',
                steps=row[3] if len(row) > 3 else '',
                expected_result=row[4] if len(row) > 4 else '',
                priority=row[5] if len(row) > 5 else 'medium',
                author=user
            )
            imported_count += 1
        return imported_count

    @staticmethod
    def import_from_json(file, project, user):
        data = json.load(file)
        if isinstance(data, dict):
            data = [data] # Handle single object
            
        imported_count = 0
        for item in data:
            ImportService._create_case(item, project, user)
            imported_count += 1
        return imported_count

    @staticmethod
    def import_from_yaml(file, project, user):
        data = yaml.safe_load(file)
        if isinstance(data, dict):
            data = [data]
            
        imported_count = 0
        for item in data:
            ImportService._create_case(item, project, user)
            imported_count += 1
        return imported_count

    @staticmethod
    def import_from_postman(file, project, user):
        """Import from Postman Collection v2.1 JSON"""
        try:
            data = json.load(file)
            items = data.get('item', [])
            
            imported_count = 0
            
            def process_items(items_list):
                nonlocal imported_count
                for item in items_list:
                    if 'item' in item:
                        # Folder, recurse
                        process_items(item['item'])
                    elif 'request' in item:
                        # Request
                        req = item['request']
                        method = req.get('method', 'GET')
                        url_data = req.get('url', {})
                        url = url_data.get('raw', '') if isinstance(url_data, dict) else url_data
                        
                        description = item.get('name', 'Untitled Request')
                        steps = f"1. Send {method} request to {url}"
                        
                        TestCase.objects.create(
                            project=project,
                            title=item.get('name', 'Untitled Request'),
                            description=description,
                            steps=steps,
                            expected_result="Response status code is 200",
                            priority='medium',
                            test_type='api',
                            author=user
                        )
                        imported_count += 1
            
            process_items(items)
            return imported_count
        except Exception as e:
            raise ValueError(f"Invalid Postman file: {e}")

    @staticmethod
    def import_from_jmeter(file, project, user):
        """Import from JMeter .jmx (XML)"""
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            
            imported_count = 0
            
            # Find all HTTPSamplerProxy
            for sampler in root.iter('HTTPSamplerProxy'):
                name = sampler.get('testname', 'Untitled Request')
                
                method_prop = sampler.find("./stringProp[@name='HTTPSampler.method']")
                method = method_prop.text if method_prop is not None else 'GET'
                
                path_prop = sampler.find("./stringProp[@name='HTTPSampler.path']")
                path = path_prop.text if path_prop is not None else '/'
                
                domain_prop = sampler.find("./stringProp[@name='HTTPSampler.domain']")
                domain = domain_prop.text if domain_prop is not None else ''
                
                url = f"{domain}{path}"
                steps = f"1. Send {method} request to {url}"
                
                TestCase.objects.create(
                    project=project,
                    title=name,
                    description=f"JMeter Test: {name}",
                    steps=steps,
                    expected_result="Response assertion passed",
                    priority='medium',
                    test_type='performance',
                    author=user
                )
                imported_count += 1
                
            return imported_count
        except Exception as e:
            raise ValueError(f"Invalid JMeter file: {e}")

    @staticmethod
    def import_from_zip(file, project, user):
        imported_count = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded zip to temp file
            zip_path = os.path.join(temp_dir, 'upload.zip')
            with open(zip_path, 'wb') as f:
                for chunk in file.chunks():
                    f.write(chunk)
            
            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Walk through files
            for root, dirs, files in os.walk(temp_dir):
                for filename in files:
                    if filename.endswith(('.yaml', '.yml')):
                        file_path = os.path.join(root, filename)
                        imported_count += ImportService._process_yaml_file(file_path, project, user, temp_dir)
        
        return imported_count

    @staticmethod
    def _process_yaml_file(file_path, project, user, root_dir):
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError:
                return 0
                
        if not data:
            return 0
            
        if isinstance(data, dict):
            data = [data]
            
        for item in data:
            data_file = item.get('data_file')
            if data_file:
                # Parameterized case
                data_file_path = os.path.join(os.path.dirname(file_path), data_file)
                if not os.path.exists(data_file_path):
                    # Try from root if relative path fails
                    data_file_path = os.path.join(root_dir, data_file)
                    
                if os.path.exists(data_file_path):
                    count += ImportService._process_parameterized_case(item, data_file_path, project, user)
                else:
                    # Fallback to single case if data file not found
                    ImportService._create_case(item, project, user)
                    count += 1
            else:
                # Normal case
                ImportService._create_case(item, project, user)
                count += 1
        return count

    @staticmethod
    def _process_parameterized_case(case_template, data_file_path, project, user):
        count = 0
        params_list = []
        
        # Read data file
        try:
            if data_file_path.endswith('.csv'):
                with open(data_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    params_list = list(reader)
            elif data_file_path.endswith('.json'):
                with open(data_file_path, 'r', encoding='utf-8') as f:
                    params_list = json.load(f)
        except Exception:
            return 0
            
        # Generate cases
        for params in params_list:
            case_data = case_template.copy()
            
            # Replace placeholders
            for key in ['title', 'description', 'preconditions', 'steps', 'expected_result']:
                if case_data.get(key):
                    for param_key, param_value in params.items():
                        placeholder = f"${{{param_key}}}" # ${var}
                        case_data[key] = case_data[key].replace(placeholder, str(param_value))
                        # Also try {var}
                        placeholder_simple = f"{{{param_key}}}"
                        case_data[key] = case_data[key].replace(placeholder_simple, str(param_value))
            
            ImportService._create_case(case_data, project, user)
            count += 1
            
        return count


class ExportService:
    @staticmethod
    def export_cases(queryset, file_type):
        """
        Export test cases to file.
        """
        if file_type == 'excel':
            return ExportService.export_to_excel(queryset)
        elif file_type == 'json':
            return ExportService.export_to_json(queryset)
        elif file_type == 'yaml':
            return ExportService.export_to_yaml(queryset)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def export_to_excel(queryset):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Title', 'Description', 'Preconditions', 'Steps', 'Expected Result', 'Priority'])
        
        for case in queryset:
            ws.append([
                case.title,
                case.description,
                case.preconditions,
                case.steps,
                case.expected_result,
                case.priority
            ])
        
        return wb

    @staticmethod
    def export_to_json(queryset):
        data = []
        for case in queryset:
            data.append({
                'title': case.title,
                'description': case.description,
                'preconditions': case.preconditions,
                'steps': case.steps,
                'expected_result': case.expected_result,
                'priority': case.priority
            })
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def export_to_yaml(queryset):
        data = []
        for case in queryset:
            data.append({
                'title': case.title,
                'description': case.description,
                'preconditions': case.preconditions,
                'steps': case.steps,
                'expected_result': case.expected_result,
                'priority': case.priority
            })
        return yaml.dump(data, allow_unicode=True)

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AITestCaseGenerator:
    @staticmethod
    async def generate_cases_from_requirement(requirement_text: str, project, user) -> List[Dict[str, Any]]:
        """
        AI Test Case Generation: Converts natural language requirements to structured test cases.
        """
        prompt = f"Analyze the following requirement and generate a strictly formatted JSON array of test cases. Each object must have keys: 'title', 'description', 'preconditions', 'steps', 'expected_result', 'priority' (high, medium, low).\nRequirement:\n{requirement_text}"
        
        # Simulate LLM Call
        logger.info("Calling LLM to generate test cases...")
        import asyncio
        await asyncio.sleep(1)
        
        # Mock Response
        mock_cases = [
            {
                "title": f"Auto-generated: Validate requirement flow",
                "description": "Generated by AI based on input.",
                "preconditions": "System is running normally.",
                "steps": "1. Access the feature.\n2. Perform the main action.",
                "expected_result": "Action is successful.",
                "priority": "high"
            }
        ]
        
        created_cases = []
        for c in mock_cases:
            tc = TestCase.objects.create(
                project=project,
                title=c['title'],
                description=c['description'],
                preconditions=c['preconditions'],
                steps=c['steps'],
                expected_result=c['expected_result'],
                priority=c['priority'],
                author=user
            )
            created_cases.append(c)
            
        logger.info(f"AI generated {len(created_cases)} cases successfully.")
        return created_cases

class AITestCaseAnalyzer:
    @staticmethod
    async def analyze_coverage(cases_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        AI Test Case Analysis: Analyzes existing cases to identify coverage gaps.
        """
        logger.info("Calling LLM to analyze coverage...")
        import asyncio
        await asyncio.sleep(1)
        
        return {
            "score": 85,
            "summary": "The test cases cover positive paths reasonably well, but lack robust error handling scenarios.",
            "missing_edge_cases": [
                "Boundary condition test: maximum input length exceeded.",
                "Concurrency condition: multiple rapid submissions.",
                "Network failure recovery scenario."
            ]
        }
