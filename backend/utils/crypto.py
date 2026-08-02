"""
敏感字段加密存储。

提供 EncryptedTextField —— 底层仍为 TextField（无需破坏性迁移），
写入时用 Fernet 对称加密，读取时自动解密；对历史明文数据向下兼容
（解密失败时按明文返回，便于平滑迁移）。

密钥来源（优先级）：
1. 环境变量 FIELD_ENCRYPTION_KEY（标准 Fernet key，urlsafe base64 32 bytes）
2. 从 Django SECRET_KEY 派生（SHA256 → urlsafe_b64encode）

生产环境必须显式设置 FIELD_ENCRYPTION_KEY，避免轮换 SECRET_KEY 导致数据不可读。
"""
import base64
import hashlib
import logging
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)

_PREFIX = 'enc:v1:'  # 密文标记前缀，用于区分历史明文


def _get_fernet():
    from cryptography.fernet import Fernet

    key = os.environ.get('FIELD_ENCRYPTION_KEY')
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    # 生产环境必须显式配置 FIELD_ENCRYPTION_KEY：
    # 若回退 SECRET_KEY 派生，则未来轮换 SECRET_KEY 会导致全部历史密文静默不可解密。
    if not getattr(settings, 'DEBUG', False):
        raise ImproperlyConfigured(
            '生产环境必须设置环境变量 FIELD_ENCRYPTION_KEY（标准 Fernet key）。'
            '禁止回退到由 SECRET_KEY 派生的密钥，否则轮换 SECRET_KEY 会令'
            '既有加密凭据全部失效。'
        )
    # 开发环境：从 SECRET_KEY 派生（兜底，方便本地无配置启动）
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_value(plaintext: str) -> str:
    if plaintext is None:
        return plaintext
    token = _get_fernet().encrypt(str(plaintext).encode('utf-8')).decode('utf-8')
    return _PREFIX + token


def decrypt_value(stored: str) -> str:
    if stored is None:
        return stored
    if not str(stored).startswith(_PREFIX):
        # 历史明文数据，原样返回（下次保存时会被加密）
        return stored
    token = str(stored)[len(_PREFIX):]
    # 先获取 Fernet 实例（生产缺 FIELD_ENCRYPTION_KEY 时此处会抛出
    # ImproperlyConfigured，必须向上传播以实现 fail-fast，不可静默吞掉）。
    fernet = _get_fernet()
    from cryptography.fernet import InvalidToken
    try:
        return fernet.decrypt(token.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        logger.error('EncryptedTextField 解密失败（密文可能已被篡改或密钥已轮换）')
        return ''
    except Exception as exc:  # noqa: BLE001
        logger.error('EncryptedTextField 解密异常：%s', exc)
        return ''


class EncryptedTextField(models.TextField):
    """透明加解密的 TextField。"""

    description = 'TextField encrypted at rest with Fernet'

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ''):
            return value
        if str(value).startswith(_PREFIX):
            return value  # 已是密文
        return encrypt_value(value)

    def from_db_value(self, value, expression, connection):
        if value in (None, ''):
            return value
        return decrypt_value(value)

    def to_python(self, value):
        if value in (None, ''):
            return value
        if str(value).startswith(_PREFIX):
            return decrypt_value(value)
        return value


def mask_secret(value: str, keep: int = 4) -> str:
    """脱敏展示：sk-5e83****42e。"""
    if not value:
        return ''
    value = str(value)
    if len(value) <= keep * 2:
        return '*' * len(value)
    return f'{value[:keep]}****{value[-3:]}'
