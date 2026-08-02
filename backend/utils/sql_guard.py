"""
SQL 安全防护层。

用于所有"平台代为执行 SQL"的场景（Text-to-SQL、数据库断言、元数据扫描）。
策略：
1. 只读模式（默认）：仅允许 SELECT / WITH ... SELECT / SHOW / DESCRIBE / EXPLAIN；
2. 禁止多语句注入（默认单语句）；
3. 禁止注释穿透（-- /* */ 剥离后再校验）；
4. 结果集行数上限；
5. 标识符（表名/库名）白名单正则校验，防止拼接注入。
"""
import re
import logging

logger = logging.getLogger(__name__)

# 允许的只读语句前缀
READONLY_PREFIXES = ('select', 'with', 'show', 'describe', 'desc', 'explain')

# 危险关键字（即使出现在子句中也直接拒绝——防止 CTE 夹带写操作）
FORBIDDEN_KEYWORDS = re.compile(
    r'\b(insert|update|delete|drop|truncate|alter|create|grant|revoke|'
    r'replace|merge|call|exec(ute)?|load\s+data|outfile|dumpfile|'
    r'into\s+(out|dump)file|shutdown|set\s+global)\b',
    re.IGNORECASE,
)

# 合法标识符：字母数字下划线，可含 $，长度限制
IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_$]{0,63}$')

DEFAULT_MAX_ROWS = 200


class SQLGuardError(Exception):
    """SQL 校验失败。"""


def strip_comments(sql: str) -> str:
    """去除 SQL 注释，防止注释绕过关键字检测。"""
    sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.DOTALL)
    sql = re.sub(r'--[^\n]*', ' ', sql)
    sql = re.sub(r'#[^\n]*', ' ', sql)
    return sql.strip()


def split_statements(sql: str):
    """按分号拆分语句（简单实现，不处理字符串内分号——校验层宁可误杀）。"""
    return [s.strip() for s in sql.split(';') if s.strip()]


def validate_readonly(sql: str, allow_multiple: bool = False) -> list:
    """
    校验 SQL 为只读，返回通过校验的语句列表。
    :raises SQLGuardError: 校验失败
    """
    cleaned = strip_comments(sql)
    if not cleaned:
        raise SQLGuardError('SQL 为空。')

    statements = split_statements(cleaned)
    if not statements:
        raise SQLGuardError('SQL 为空。')
    if len(statements) > 1 and not allow_multiple:
        raise SQLGuardError('禁止一次执行多条 SQL 语句。')

    for stmt in statements:
        lowered = stmt.lower().lstrip('( \t\n\r')
        if not lowered.startswith(READONLY_PREFIXES):
            raise SQLGuardError(
                f'仅允许只读查询（SELECT/WITH/SHOW/DESCRIBE/EXPLAIN），已拒绝: {stmt[:80]}...'
            )
        if FORBIDDEN_KEYWORDS.search(stmt):
            raise SQLGuardError(
                f'语句中包含被禁止的写操作/危险关键字，已拒绝: {stmt[:80]}...'
            )
    return statements


def validate_identifier(name: str, kind: str = '标识符') -> str:
    """校验表名/库名/列名等标识符合法性，返回原值。"""
    if not name or not IDENTIFIER_RE.match(str(name)):
        raise SQLGuardError(f'非法{kind}: {name!r}')
    return name


# 造数场景专用：允许 INSERT，但仍禁止 UPDATE/DELETE/DDL 等
_FORBIDDEN_EXCEPT_INSERT = re.compile(
    r'\b(update|delete|drop|truncate|alter|create|grant|revoke|'
    r'replace|merge|call|exec(ute)?|load\s+data|outfile|dumpfile|'
    r'into\s+(out|dump)file|shutdown|set\s+global)\b',
    re.IGNORECASE,
)


def validate_statements(sql: str, allow_insert: bool = False) -> list:
    """
    校验 SQL 语句列表：
    - 只读语句始终允许；
    - INSERT 仅在 allow_insert=True（造数场景 + 人工确认）时允许；
    - UPDATE/DELETE/DDL 一律拒绝。
    :raises SQLGuardError: 校验失败
    """
    cleaned = strip_comments(sql)
    if not cleaned:
        raise SQLGuardError('SQL 为空。')

    statements = split_statements(cleaned)
    if not statements:
        raise SQLGuardError('SQL 为空。')

    for stmt in statements:
        lowered = stmt.lower().lstrip('( \t\n\r')
        if lowered.startswith(READONLY_PREFIXES):
            if FORBIDDEN_KEYWORDS.search(stmt):
                raise SQLGuardError(f'只读语句中夹带危险关键字，已拒绝: {stmt[:80]}...')
        elif lowered.startswith('insert'):
            if not allow_insert:
                raise SQLGuardError('INSERT 语句需要人工确认后才能执行（confirm_write=true）。')
            if _FORBIDDEN_EXCEPT_INSERT.search(stmt):
                raise SQLGuardError(f'INSERT 语句中夹带危险关键字，已拒绝: {stmt[:80]}...')
        else:
            raise SQLGuardError(
                f'仅允许只读查询与（经确认的）INSERT 造数语句，已拒绝: {stmt[:80]}...'
            )
    return statements


def enforce_limit(sql: str, max_rows: int = DEFAULT_MAX_ROWS) -> str:
    """为 SELECT 语句追加 LIMIT（若语句本身不含 LIMIT）。"""
    stripped = sql.rstrip().rstrip(';')
    if re.search(r'\blimit\s+\d+', stripped, re.IGNORECASE):
        return stripped
    lowered = stripped.lower().lstrip('( \t\n\r')
    if lowered.startswith(('select', 'with')):
        return f'{stripped} LIMIT {max_rows}'
    return stripped
