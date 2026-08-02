
class AliyunConnector:
    """
    Connector for Aliyun (Aliyun Xiao).
    真实对接能力本期未交付；原 mock 假数据已按整改要求移除，
    调用时显式报错，避免伪造文档/日志静默充真。
    """
    def __init__(self, api_key, project_id):
        self.api_key = api_key
        self.project_id = project_id

    def fetch_documents(self):
        """Fetch documents from Aliyun."""
        raise NotImplementedError('该能力本期未交付')

    def fetch_logs(self, limit=100):
        """Fetch interface request logs from Aliyun."""
        raise NotImplementedError('该能力本期未交付')
