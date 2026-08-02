"""sql_guard 回归测试（纯 Python，无需 Django）。

覆盖：
- 只读语句校验 / 写操作拒绝
- INSERT 需人工确认（allow_insert）
- 标识符白名单（防表名拼接注入）
- enforce_limit 追加 LIMIT
"""
import pytest

from backend.utils.sql_guard import (
    SQLGuardError,
    enforce_limit,
    validate_identifier,
    validate_readonly,
    validate_statements,
)


def test_readonly_select_ok():
    assert validate_readonly("SELECT * FROM t") == ["SELECT * FROM t"]


def test_readonly_rejects_drop():
    with pytest.raises(SQLGuardError):
        validate_readonly("SELECT * FROM t; DROP TABLE t")


def test_readonly_rejects_write():
    with pytest.raises(SQLGuardError):
        validate_readonly("UPDATE t SET a=1")


def test_validate_statements_allows_insert_with_flag():
    stmts = validate_statements("INSERT INTO t(a) VALUES (1)", allow_insert=True)
    assert stmts


def test_validate_statements_blocks_insert_without_flag():
    with pytest.raises(SQLGuardError):
        validate_statements("INSERT INTO t(a) VALUES (1)")


def test_validate_statements_blocks_ddl():
    with pytest.raises(SQLGuardError):
        validate_statements("CREATE TABLE t (a int)")


def test_validate_identifier_ok():
    assert validate_identifier("my_table_1") == "my_table_1"


def test_validate_identifier_rejects_injection():
    with pytest.raises(SQLGuardError):
        validate_identifier("t; DROP TABLE users --")


def test_validate_identifier_rejects_spaces():
    with pytest.raises(SQLGuardError):
        validate_identifier("my table")


def test_enforce_limit_appends():
    assert enforce_limit("SELECT * FROM t") == "SELECT * FROM t LIMIT 200"


def test_enforce_limit_keeps_existing():
    assert enforce_limit("SELECT * FROM t LIMIT 10") == "SELECT * FROM t LIMIT 10"
