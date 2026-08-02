
class YoudaoConnector:
    """
    Connector for Youdao Cloud Note.
    真实对接能力本期未交付；原 mock 假数据已按整改要求移除，
    调用时显式报错，避免伪造笔记数据静默充真。
    """
    def __init__(self, access_token):
        self.access_token = access_token

    def fetch_notes(self):
        """Fetch notes from Youdao."""
        raise NotImplementedError('该能力本期未交付')
