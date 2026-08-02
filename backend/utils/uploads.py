"""
文件上传安全校验工具。

- 扩展名白名单
- 大小上限
- 文件名消毒（防路径穿越）
"""
import os
import re
import uuid

ALLOWED_DOC_EXTENSIONS = frozenset({
    'txt', 'md', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'json', 'yaml', 'yml',
})
ALLOWED_IMAGE_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'})

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB


class UploadValidationError(Exception):
    pass


def sanitize_filename(filename: str) -> str:
    """去除路径分隔符与危险字符，防止路径穿越。"""
    base = os.path.basename(str(filename).replace('\\', '/'))
    base = re.sub(r'[^\w\u4e00-\u9fff.\-]', '_', base)
    return base[:200] or 'unnamed'


def validate_upload(file_obj, allowed_extensions=ALLOWED_DOC_EXTENSIONS,
                    max_size=MAX_UPLOAD_SIZE):
    """
    校验上传文件，返回（消毒后文件名, 扩展名）。
    :raises UploadValidationError: 校验失败
    """
    if file_obj is None:
        raise UploadValidationError('未接收到文件。')

    name = sanitize_filename(file_obj.name)
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''

    if ext not in allowed_extensions:
        raise UploadValidationError(
            f'不允许的文件类型 .{ext}。允许: {", ".join(sorted(allowed_extensions))}'
        )
    if file_obj.size > max_size:
        raise UploadValidationError(
            f'文件过大（{file_obj.size // (1024*1024)}MB），上限 {max_size // (1024*1024)}MB。'
        )
    return name, ext


def safe_upload_path(upload_dir: str, original_name: str) -> str:
    """生成防冲突且防穿越的落盘路径。"""
    name = sanitize_filename(original_name)
    return os.path.join(upload_dir, f'{uuid.uuid4().hex}_{name}')
