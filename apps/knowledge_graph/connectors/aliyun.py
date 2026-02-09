
class AliyunConnector:
    """
    Connector for Aliyun (Aliyun Xiao).
    Should implement methods to fetch documents/wiki.
    """
    def __init__(self, api_key, project_id):
        self.api_key = api_key
        self.project_id = project_id
        
    def fetch_documents(self):
        """Fetch documents from Aliyun."""
        # Mock implementation for demo
        return [
            {
                "id": "aliyun_doc_001",
                "title": "Project Requirements Specification",
                "content": "This document describes the requirements for the new e-commerce platform...",
                "source": "aliyun_xiao",
                "url": f"https://devops.aliyun.com/project/{self.project_id}/doc/1"
            },
            {
                "id": "aliyun_doc_002",
                "title": "API Documentation",
                "content": "The platform provides RESTful APIs for user management, product catalog...",
                "source": "aliyun_xiao",
                "url": f"https://devops.aliyun.com/project/{self.project_id}/doc/2"
            }
        ]
        
    def fetch_logs(self, limit=100):
        """Fetch interface request logs from Aliyun."""
        # In a real scenario, this would call Aliyun Log Service API
        # Mocking for now
        return [
            {
                "url": "/api/v1/contract/create",
                "method": "POST",
                "request_body": {"name": "Test Contract", "type": "purchase"},
                "response_body": {"id": "contract_123", "status": "pending"},
                "status_code": 201,
                "trace_id": "trace_001"
            },
            {
                "url": "/api/v1/contract/approve",
                "method": "POST",
                "request_body": {"contract_id": "contract_123"},
                "response_body": {"success": True},
                "status_code": 200,
                "trace_id": "trace_002"
            }
        ]
