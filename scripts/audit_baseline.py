"""四合一全量安全审计扫描器（第六轮收敛轮基线工具）。

替代人工抽样审计，对 apps/ 下全部代码做 AST 静态分析，一次性输出完整问题基线。

四个检测维度：
  D1 @action / 自定义方法内直连 Model.objects  → 绕过租户隔离（get_queryset 不生效）
  D2 序列化器敏感字段暴露                      → fields='__all__' 或显式暴露密钥/PII
  D3 生产代码模拟实现残留                      → mock / 模拟 / 伪造数据
  D4 视图租户隔离接入覆盖                      → 未接入任何隔离机制的 ViewSet

用法：
  python scripts/audit_baseline.py                 # 纯静态扫描（不需要 Django）
  DEBUG=true python scripts/audit_baseline.py --orm  # 额外校验租户过滤路径可被 ORM 编译
  python scripts/audit_baseline.py --ci            # CI 门禁模式：有 P0 则退出码 1

输出：
  scripts/audit_baseline.json  机器可读基线
  安全审计基线.md               人读基线报告
"""
import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(ROOT, 'apps')

# ---------------------------------------------------------------- 配置

# 隔离机制基类名（命中任一即视为已接入）
TENANT_MIXINS = {
    'TenantAwareViewSetMixin',
    'TenantScopedViewSetMixin',
    'OwnedQuerySetMixin',
    'BaseProjectViewSet',
}

# 视图基类特征（用于识别一个类是不是 DRF 视图）
VIEW_BASE_HINTS = ('ViewSet', 'APIView', 'ListAPIView', 'CreateAPIView', 'RetrieveAPIView',
                   'UpdateAPIView', 'DestroyAPIView', 'ListCreateAPIView',
                   'RetrieveUpdateAPIView', 'RetrieveUpdateDestroyAPIView', 'GenericAPIView')

# 敏感字段名（出现在序列化器/模型中即需脱敏）
SENSITIVE_FIELDS = {
    'password', 'passwd', 'secret', 'token', 'api_key', 'apikey', 'access_key',
    'secret_key', 'private_key', 'credential', 'credentials', 'webhook', 'webhook_bots',
    'webhook_url', 'auth_token', 'refresh_token', 'client_secret', 'db_password',
}
# PII 字段名
PII_FIELDS = {
    'email', 'phone', 'mobile', 'id_card', 'idcard', 'real_name', 'recipient_info',
    'sender_email', 'address', 'birthday',
}

# 序列化器名/模型名命中这些词时，fields='__all__' 风险升级为 P0
SENSITIVE_MODEL_HINTS = ('config', 'server', 'credential', 'notification', 'user',
                         'profile', 'account', 'auth', 'source', 'datasource')

# D3 模拟实现关键词
MOCK_PATTERNS = [
    (re.compile(r'\bmock[_\s]*(data|result|response|task|pipeline|impl)', re.I), 'mock 数据/结果'),
    # 第六轮批次2 补漏：静默降级为假实例/假元素（minium_engine 曾以此伪造"全部通过"）
    (re.compile(r'\bmock[_\s]*(instance|element|client|engine|driver|server|session|device)', re.I),
     'mock 假实例/假对象'),
    (re.compile(r'\[\s*Mock\s*\]'), 'Mock 结果标记'),
    (re.compile(r'(使用|降级|回退|切换)(到|为|至)?\s*[Mm]ock|[Mm]ock\s*模式|模拟模式'), 'Mock 降级模式'),
    (re.compile(r'Mock implementation', re.I), 'Mock implementation 标记'),
    (re.compile(r'模拟(执行|数据|结果|返回|生成|测试|分析|调用|连接|响应)'), '中文"模拟X"'),
    (re.compile(r'(假|伪造)(数据|结果|日志|截图)'), '假数据/伪造'),
    (re.compile(r'\bfake_\w+'), 'fake_ 前缀'),
    (re.compile(r'random\.(uniform|randint|choice)\s*\('), 'random 造数'),
    (re.compile(r'time\.sleep\s*\('), 'time.sleep 伪装耗时'),
    (re.compile(r'TODO.*(实现|implement)', re.I), 'TODO 未实现'),
]

# D3 白名单：这些路径下的命中不算问题
MOCK_PATH_WHITELIST = (
    os.sep + 'tests' + os.sep, os.sep + 'migrations' + os.sep,
    'test_', '_test.py', 'conftest.py', 'factories.py', 'seed',
    # 造数/模拟本身就是产品能力的模块
    os.sep + 'test_data' + os.sep, 'data_factory.py', 'variable_resolver.py',
    'device_simulator', 'data_explorer_service.py',
)

# ---------------------------------------------------------------- 工具


def iter_py_files(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__', '.git', 'node_modules')]
        for fn in filenames:
            if fn.endswith('.py'):
                yield os.path.join(dirpath, fn)


def rel(path):
    return os.path.relpath(path, ROOT).replace('\\', '/')


def base_names(node):
    """取 ClassDef 的基类名字列表（含属性形式 a.b.C 取 C）。"""
    out = []
    for b in node.bases:
        if isinstance(b, ast.Name):
            out.append(b.id)
        elif isinstance(b, ast.Attribute):
            out.append(b.attr)
    return out


def is_view_class(node):
    return any(any(h in bn for h in VIEW_BASE_HINTS) for bn in base_names(node))


def decorator_names(fn):
    out = []
    for d in fn.decorator_list:
        t = d.func if isinstance(d, ast.Call) else d
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Attribute):
            out.append(t.attr)
    return out


UNTRUSTED_SRC = re.compile(
    r'request\.(data|query_params|GET|POST)|serializer\.validated_data|kwargs\.get')

READ_METHODS = {'filter', 'get', 'all', 'exclude', 'first', 'last', 'count',
                'aggregate', 'annotate', 'values', 'values_list', 'exists'}
WRITE_METHODS = {'create', 'update', 'delete', 'bulk_create', 'bulk_update',
                 'get_or_create', 'update_or_create'}


# 过滤键是主键/外键 ID —— 用用户给的 ID 直接定位对象是核心越权模式
ID_LOOKUP = re.compile(r'\b(id|pk|\w+_id)\s*(__in\s*)?=')
# create/update 时把用户输入写进外键字段
FK_KWARG = re.compile(r'\b(\w+_id)\s*=')
OBJ_LOOKUP = re.compile(r'^([A-Z]\w*)\.objects\.(get|filter|get_or_create)\((.*)\)$', re.S)


def _collect_var_taint(fn_node):
    """扫描函数体，返回 (已校验变量集, 不可信变量集, 不可信对象变量集)。

    已校验    ：赋值自 self.get_object() / self.get_queryset()
    不可信    ：赋值自 request.data / query_params / serializer.validated_data
    不可信对象：赋值自 Model.objects.get(id=<不可信>) —— 用用户给的 ID 取到的对象
    """
    trusted, untrusted, untrusted_obj = set(), set(), set()
    assigns = []
    for n in ast.walk(fn_node):
        if not isinstance(n, ast.Assign) or not isinstance(n.targets[0], ast.Name):
            continue
        try:
            assigns.append((n.targets[0].id, ast.unparse(n.value)))
        except Exception:
            continue

    for var, val_src in assigns:
        if re.search(r'self\.get_object\s*\(|self\.get_queryset\s*\(', val_src):
            trusted.add(var)
        elif UNTRUSTED_SRC.search(val_src):
            untrusted.add(var)

    for _ in range(2):  # 迭代传播（b = A.objects.get(id=x) 依赖 x 先被标记）
        for var, val_src in assigns:
            m = OBJ_LOOKUP.match(val_src.strip())
            if not m:
                continue
            args = m.group(3)
            refs = set(re.findall(r'\b([A-Za-z_]\w*)\b', args))
            if ID_LOOKUP.search(args) and (UNTRUSTED_SRC.search(args) or (refs & untrusted)):
                untrusted_obj.add(var)
    return trusted, untrusted, untrusted_obj


def find_objects_access(fn_node):
    """查找 `Model.objects.<m>(...)` 直连访问并做数据流定性。

    返回 [(model, lineno, method, verdict)]
    verdict ∈ {'idlookup','fkwrite','global','trusted','unknown'}
    """
    trusted, untrusted, untrusted_obj = _collect_var_taint(fn_node)
    hits = []
    for n in ast.walk(fn_node):
        if not (isinstance(n, ast.Attribute) and n.attr == 'objects'
                and isinstance(n.value, ast.Name) and n.value.id[:1].isupper()):
            continue
        model = n.value.id
        # 向上找到调用方法名与实参
        method, call_src = None, ''
        for p in ast.walk(fn_node):
            if (isinstance(p, ast.Call) and isinstance(p.func, ast.Attribute)
                    and p.func.value is n):
                method = p.func.attr
                try:
                    call_src = ast.unparse(p)
                except Exception:
                    call_src = ''
                break
        if method is None:
            continue

        arg_src = call_src[call_src.find('(') + 1:] if '(' in call_src else ''
        refs = set(re.findall(r'\b([A-Za-z_]\w*)\b', arg_src))

        tainted = bool(UNTRUSTED_SRC.search(arg_src) or (refs & untrusted))

        if method in READ_METHODS and tainted and ID_LOOKUP.search(arg_src):
            verdict = 'idlookup'           # 用用户给的 ID 直接定位对象 —— 核心越权
        elif method in WRITE_METHODS and (
                (refs & untrusted_obj) or (tainted and FK_KWARG.search(arg_src))):
            verdict = 'fkwrite'            # 把用户可控外键写入新对象 —— 可挂载到他人数据
        elif refs & trusted:
            verdict = 'trusted'            # 派生自 get_object()，已过租户校验
        elif not arg_src.strip() and method in READ_METHODS:
            verdict = 'global'             # 无条件全表访问
        elif method in WRITE_METHODS:
            verdict = 'trusted'            # 仅写入内容字段，非越权
        else:
            verdict = 'unknown'
        hits.append((model, n.lineno, method, verdict))
    return hits


def class_source_segment(src_lines, node):
    return '\n'.join(src_lines[node.lineno - 1: getattr(node, 'end_lineno', node.lineno)])


# ---------------------------------------------------------------- D1 + D4


def scan_views(findings):
    """D1：@action/自定义方法直连 Model.objects；D4：视图未接入隔离机制。"""
    for path in iter_py_files(APPS_DIR):
        fname = os.path.basename(path)
        if not (fname == 'views.py' or 'views' in path.split(os.sep) or fname.endswith('_views.py')):
            continue
        if any(w in path for w in ('tests', 'migrations', 'test_')):
            continue
        try:
            src = open(path, encoding='utf-8').read()
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        src_lines = src.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not is_view_class(node):
                continue

            bases = base_names(node)
            has_mixin = any(b in TENANT_MIXINS for b in bases)
            cls_src = class_source_segment(src_lines, node)
            uses_scope_call = '_apply_tenant_scope' in cls_src

            methods = [m for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            method_names = {m.name for m in methods}
            has_custom_qs = 'get_queryset' in method_names

            # ---- D4：隔离接入覆盖
            has_queryset_attr = any(
                isinstance(s, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == 'queryset' for t in s.targets)
                for s in node.body)
            # 显式声明解析：tenant_scope_exempt / tenant_scope_self_managed（均须给出 reason）
            decls = {}
            for s in node.body:
                if not isinstance(s, ast.Assign) or not isinstance(s.value, ast.Constant):
                    continue
                for t in s.targets:
                    if isinstance(t, ast.Name):
                        decls[t.id] = s.value.value
            exempt_flag = decls.get('tenant_scope_exempt') is True
            exempt_reason = str(decls.get('tenant_scope_exempt_reason') or '')
            selfmgr_flag = decls.get('tenant_scope_self_managed') is True
            selfmgr_reason = str(decls.get('tenant_scope_self_managed_reason') or '')

            def _record(sev, issue, fix):
                findings.append({
                    'detector': 'D4', 'severity': sev,
                    'file': rel(path), 'line': node.lineno,
                    'target': node.name, 'issue': issue, 'fix': fix,
                })

            if exempt_flag and selfmgr_flag:
                _record('P1', '同时声明 tenant_scope_exempt 与 tenant_scope_self_managed，语义互斥',
                        '二选一：平台级公共资源用 exempt，自定义 get_queryset 已隔离用 self_managed')
            elif (has_queryset_attr or has_custom_qs) and not (has_mixin or uses_scope_call):
                if exempt_flag:
                    # 豁免不等于免检：降级为 P2 台账留痕，人工复核理由是否成立
                    _record('P2', f'已显式声明租户豁免（tenant_scope_exempt=True），理由：{exempt_reason or "【缺失，需补】"}',
                            '人工复核该豁免理由是否成立；若资源实际含租户数据，须撤销豁免并接入隔离')
                else:
                    _record('P1', '视图未接入任何租户隔离机制（无 TenantAware/Scoped/Owned 基类，也未调 _apply_tenant_scope）',
                            '加 TenantAwareViewSetMixin 为第一基类，或在自定义 get_queryset 末尾调 self._apply_tenant_scope(qs)')
            elif has_mixin and has_custom_qs and not uses_scope_call and not exempt_flag:
                # 形式挂靠：继承了 mixin 却用自定义 get_queryset 完全覆盖其实现，
                # mixin 的隔离逻辑一行都不会执行 —— 这是"看起来接了、实际没接"。
                _record('P1', '继承租户基类但自定义 get_queryset 覆盖了其实现，且未调用 self._apply_tenant_scope —— 隔离实际未生效（形式挂靠）',
                        '在自定义 get_queryset 的每个 return 分支收口为 self._apply_tenant_scope(qs)；'
                        '若该 get_queryset 本身已实现等效或更严格的租户边界，改为显式声明 '
                        'tenant_scope_self_managed = True 并填写 reason')
            elif selfmgr_flag:
                # 自管过滤：已显式声明，入 P2 台账，人工复核其边界是否真的等效
                _record('P2', f'已显式声明自管租户过滤（tenant_scope_self_managed=True），理由：{selfmgr_reason or "【缺失，需补】"}',
                        '人工复核自定义 get_queryset 的过滤是否真正覆盖全部读取路径且不弱于组织级隔离')
            elif exempt_flag:
                # 既接了隔离又声明豁免 —— 语义矛盾，必须澄清
                _record('P1', '同时接入租户隔离与 tenant_scope_exempt=True，语义矛盾，实际行为不可预期',
                        '二选一：确需全局可见则移除隔离调用，否则删除 tenant_scope_exempt 声明')

            # ---- D1：方法内直连 Model.objects（数据流定性）
            for m in methods:
                if m.name == 'get_queryset':
                    continue  # get_queryset 内直连由 D4 覆盖
                is_action = 'action' in decorator_names(m)
                for model, lineno, method, verdict in find_objects_access(m):
                    if verdict == 'trusted':
                        continue  # 派生自已校验对象 / 仅写入内容字段 —— 非越权，不入基线
                    if verdict == 'idlookup':
                        sev = 'P0'
                        desc = (f'{model}.objects.{method}() 用用户提供的 ID 直接定位对象，'
                                f'未校验归属 —— 可读取/操作他租户数据')
                    elif verdict == 'fkwrite':
                        sev = 'P0'
                        desc = (f'{model}.objects.{method}() 将用户可控外键写入新对象 —— '
                                f'可把数据挂载到他租户')
                    elif verdict == 'global':
                        sev = 'P1'
                        desc = f'{model}.objects.{method}() 无条件全表访问，跨租户泄露'
                    else:
                        sev = 'P2'
                        desc = f'{model}.objects.{method}() 绕过 get_queryset，租户过滤依赖来源待人工确认'
                    findings.append({
                        'detector': 'D1', 'severity': sev,
                        'file': rel(path), 'line': lineno,
                        'target': f'{node.name}.{m.name}' + (' @action' if is_action else ''),
                        'issue': desc,
                        'fix': f'改用 self.get_queryset() 派生，或对 {model} 显式补租户过滤后再按 ID 取用',
                    })


# ---------------------------------------------------------------- D2


def scan_serializers(findings):
    for path in iter_py_files(APPS_DIR):
        fname = os.path.basename(path)
        if not (fname == 'serializers.py' or 'serializers' in path.split(os.sep)):
            continue
        if any(w in path for w in ('tests', 'migrations')):
            continue
        try:
            src = open(path, encoding='utf-8').read()
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        src_lines = src.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not any('Serializer' in b for b in base_names(node)):
                continue
            meta = next((s for s in node.body
                         if isinstance(s, ast.ClassDef) and s.name == 'Meta'), None)
            if meta is None:
                continue

            cls_src = class_source_segment(src_lines, node)
            fields_val, model_name, extra_kwargs_src = None, None, ''
            explicit_fields = []
            for s in meta.body:
                if not isinstance(s, ast.Assign):
                    continue
                tname = s.targets[0].id if isinstance(s.targets[0], ast.Name) else None
                if tname == 'fields':
                    if isinstance(s.value, ast.Constant):
                        fields_val = s.value.value
                    elif isinstance(s.value, (ast.List, ast.Tuple)):
                        fields_val = 'explicit'
                        explicit_fields = [e.value for e in s.value.elts
                                           if isinstance(e, ast.Constant)]
                elif tname == 'model':
                    model_name = s.value.id if isinstance(s.value, ast.Name) else None
                elif tname == 'extra_kwargs':
                    extra_kwargs_src = ast.unparse(s.value) if hasattr(ast, 'unparse') else ''

            protected = ('write_only' in cls_src) or ('write_only' in extra_kwargs_src)

            if fields_val == '__all__':
                hint = (model_name or node.name).lower()
                risky = any(h in hint for h in SENSITIVE_MODEL_HINTS)
                findings.append({
                    'detector': 'D2',
                    'severity': 'P0' if (risky and not protected) else 'P2',
                    'file': rel(path), 'line': node.lineno,
                    'target': f'{node.name}(model={model_name})',
                    'issue': "fields='__all__' 全字段输出"
                             + ('，且模型名提示含密钥/PII 且未见 write_only 保护' if risky and not protected
                                else '，建议显式白名单'),
                    'fix': '改为显式 fields 白名单，敏感字段设 write_only=True 或提供掩码字段',
                })
            elif fields_val == 'explicit':
                leaked = [f for f in explicit_fields
                          if f.lower() in SENSITIVE_FIELDS or f.lower() in PII_FIELDS]
                leaked = [f for f in leaked if f'"{f}"' not in extra_kwargs_src
                          and f"'{f}'" not in extra_kwargs_src]
                if leaked and not protected:
                    # 显式 PII 掩码声明：继承 PIIMaskMixin 且 pii_masked_fields 覆盖全部泄露字段
                    has_mask_mixin = any('PIIMaskMixin' in b for b in base_names(node))
                    masked_fields = []
                    for s in node.body:
                        if not isinstance(s, ast.Assign):
                            continue
                        for t in s.targets:
                            if isinstance(t, ast.Name) and t.id == 'pii_masked_fields' \
                                    and isinstance(s.value, (ast.List, ast.Tuple)):
                                masked_fields = [e.value for e in s.value.elts
                                                 if isinstance(e, ast.Constant)]
                    uncovered = [f for f in leaked if f not in masked_fields]

                    if has_mask_mixin and not uncovered:
                        # 掩码不等于免检：降 P2 台账留痕，人工复核掩码强度与覆盖面
                        findings.append({
                            'detector': 'D2', 'severity': 'P2',
                            'file': rel(path), 'line': node.lineno,
                            'target': f'{node.name}(model={model_name})',
                            'issue': f'PII 字段 {leaked} 已声明掩码（PIIMaskMixin，本人/管理员明文，他人掩码）',
                            'fix': '人工复核：掩码强度是否足够、是否存在其他未声明的 PII 字段',
                        })
                    elif has_mask_mixin and uncovered:
                        findings.append({
                            'detector': 'D2', 'severity': 'P1',
                            'file': rel(path), 'line': node.lineno,
                            'target': f'{node.name}(model={model_name})',
                            'issue': f'继承 PIIMaskMixin 但 {uncovered} 未列入 pii_masked_fields，仍明文输出',
                            'fix': f'把 {uncovered} 补进 pii_masked_fields',
                        })
                    else:
                        is_secret = any(f.lower() in SENSITIVE_FIELDS for f in leaked)
                        findings.append({
                            'detector': 'D2',
                            'severity': 'P0' if is_secret else 'P1',
                            'file': rel(path), 'line': node.lineno,
                            'target': f'{node.name}(model={model_name})',
                            'issue': f'显式输出敏感字段 {leaked} 且未见 write_only 保护',
                            'fix': '对上述字段设 write_only=True，或改为掩码只读字段',
                        })


# ---------------------------------------------------------------- D3


def _docstring_line_ranges(src):
    """收集所有文档字符串/裸字符串表达式占用的行号集合。

    整改说明性注释（如"原 mock 假数据已按整改要求移除"）本身含关键词，
    会被 D3 误报为 P1。这类命中降级为 P2 台账留痕，而不是直接消失。
    """
    ranges = set()
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return ranges
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            start = node.lineno
            end = getattr(node, 'end_lineno', start) or start
            ranges.update(range(start, end + 1))
    return ranges


# 可审计豁免标记：真实现被关键词误伤时，在该行或上一行写
#   # audit: real-impl <理由>
# 扫描器降为 P2 台账留痕，仍会被人工复核，不会消失。
REAL_IMPL_MARK = re.compile(r'#\s*audit:\s*real-impl\b(.*)', re.I)


def scan_mocks(findings):
    for path in iter_py_files(APPS_DIR):
        low = path.lower()
        if any(w.lower() in low for w in MOCK_PATH_WHITELIST):
            continue
        try:
            src = open(path, encoding='utf-8').read()
        except UnicodeDecodeError:
            continue
        lines = src.splitlines()
        doc_lines = _docstring_line_ranges(src)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            for pat, label in MOCK_PATTERNS:
                if pat.search(line):
                    # 判定严重度：出现在返回值构造或函数定义附近 → 高
                    ctx = '\n'.join(lines[max(0, i - 4): i + 6])
                    is_return = bool(re.search(r'\breturn\b|Response\s*\(', ctx))
                    sev = 'P1' if is_return else 'P2'
                    if label in ('Mock implementation 标记', 'mock 数据/结果', '假数据/伪造',
                                 'mock 假实例/假对象', 'Mock 结果标记', 'Mock 降级模式'):
                        sev = 'P1'

                    issue = f'生产代码疑似模拟实现: {stripped[:90]}'
                    fix = '实现真实逻辑；确实无法实现的返回 501 并显式标注"演示数据"，禁止静默造假'

                    # 降噪 1：命中位于注释行或文档字符串 —— 不是可执行逻辑
                    if stripped.startswith('#') or i in doc_lines:
                        sev = 'P2'
                        issue = f'关键词命中于注释/文档字符串（非可执行代码）: {stripped[:80]}'
                        fix = '人工复核：确认该处只是说明性文字，而非遗留的未实现逻辑'
                    else:
                        # 降噪 2：显式声明真实现（本行或上一行的 # audit: real-impl 理由）
                        mark = REAL_IMPL_MARK.search(line)
                        if mark is None and i >= 2:
                            mark = REAL_IMPL_MARK.search(lines[i - 2])
                        if mark is not None:
                            sev = 'P2'
                            reason = mark.group(1).strip() or '【缺失，需补理由】'
                            issue = f'已声明为真实现（audit: real-impl）：{reason}｜命中行: {stripped[:60]}'
                            fix = '人工复核该声明是否成立；若实为假实现须撤销标记并按 501 处置'

                    findings.append({
                        'detector': 'D3', 'severity': sev,
                        'file': rel(path), 'line': i,
                        'target': label, 'issue': issue, 'fix': fix,
                    })
                    break


# ---------------------------------------------------------------- D5(可选) ORM 路径编译


def scan_orm_paths(findings):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    os.environ.setdefault('DEBUG', 'true')
    sys.path.insert(0, ROOT)
    import django
    django.setup()
    import importlib
    import inspect
    from apps.core_platform.permissions import TenantAwareViewSetMixin

    modules = set()
    for path in iter_py_files(APPS_DIR):
        if os.path.basename(path) == 'views.py':
            modules.add(rel(path)[:-3].replace('/', '.'))

    checked = 0
    for mod_name in sorted(modules):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ != mod_name or not issubclass(cls, TenantAwareViewSetMixin):
                continue
            qs = getattr(cls, 'queryset', None)
            if qs is None:
                continue
            model, org_field = qs.model, getattr(cls, 'org_field', None)
            if org_field:
                filt = org_field
            else:
                fields = model._meta.get_fields()
                fnames = [f.name for f in fields]
                if 'organization' in fnames:
                    filt = 'organization'
                elif any(f.name == 'project' and getattr(f, 'is_relation', False) for f in fields):
                    filt = 'project__organization'
                elif 'created_by' in fnames:
                    filt = 'created_by'
                elif 'creator' in fnames:
                    filt = 'creator'
                else:
                    continue
            checked += 1
            try:
                str(model.objects.filter(**{filt: 1}).query)
            except Exception as e:
                findings.append({
                    'detector': 'D5', 'severity': 'P0',
                    'file': mod_name, 'line': 0, 'target': name,
                    'issue': f'租户过滤路径 {filt} 无法编译: {type(e).__name__}: {e}',
                    'fix': '修正 org_field 为模型实际存在的字段路径',
                })
    return checked


# ---------------------------------------------------------------- 报告


DETECTOR_TITLES = {
    'D1': '@action / 自定义方法绕过租户隔离',
    'D2': '序列化器敏感字段暴露',
    'D3': '生产代码模拟实现残留',
    'D4': '视图未接入租户隔离机制',
    'D5': '租户过滤路径无法编译',
}


def write_reports(findings, orm_checked):
    findings.sort(key=lambda f: ({'P0': 0, 'P1': 1, 'P2': 2}[f['severity']], f['detector'], f['file'], f['line']))

    with open(os.path.join(ROOT, 'scripts', 'audit_baseline.json'), 'w', encoding='utf-8') as f:
        json.dump({'total': len(findings), 'findings': findings}, f, ensure_ascii=False, indent=2)

    by_sev = defaultdict(int)
    by_det = defaultdict(lambda: defaultdict(int))
    by_app = defaultdict(lambda: defaultdict(int))
    for x in findings:
        by_sev[x['severity']] += 1
        by_det[x['detector']][x['severity']] += 1
        app = x['file'].split('/')[1] if x['file'].startswith('apps/') else x['file'].split('/')[0]
        by_app[app][x['severity']] += 1

    out = ['# 安全审计基线（机器全量扫描）', '',
           f"**扫描工具**：`scripts/audit_baseline.py`　**问题总数**：{len(findings)}"
           f"　（P0 {by_sev['P0']} / P1 {by_sev['P1']} / P2 {by_sev['P2']}）",
           f"**ORM 路径编译校验**：{orm_checked} 条" if orm_checked else '', '',
           '> 本基线由机器全量扫描产出，替代人工抽样。此后不再追加新的检查维度——'
           '第六轮整改以本文件为唯一交付标准。', '', '## 一、按检测维度汇总', '',
           '| 维度 | 说明 | P0 | P1 | P2 | 小计 |', '|---|---|---|---|---|---|']
    for d in sorted(by_det):
        c = by_det[d]
        out.append(f"| {d} | {DETECTOR_TITLES[d]} | {c['P0']} | {c['P1']} | {c['P2']} "
                   f"| {sum(c.values())} |")

    out += ['', '## 二、按模块汇总', '', '| 模块 | P0 | P1 | P2 | 小计 |', '|---|---|---|---|---|']
    for a in sorted(by_app, key=lambda k: -sum(by_app[k].values())):
        c = by_app[a]
        out.append(f"| {a} | {c['P0']} | {c['P1']} | {c['P2']} | {sum(c.values())} |")

    for sev in ('P0', 'P1', 'P2'):
        items = [x for x in findings if x['severity'] == sev]
        if not items:
            continue
        out += ['', f'## 三、{sev} 明细（{len(items)} 项）', '']
        cur = None
        for x in items:
            if x['detector'] != cur:
                cur = x['detector']
                out += [f'### {cur} · {DETECTOR_TITLES[cur]}', '']
            out.append(f"- `{x['file']}:{x['line']}` **{x['target']}** — {x['issue']}")
            if sev == 'P0':
                out.append(f"  - 修复：{x['fix']}")

    with open(os.path.join(ROOT, '安全审计基线.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')

    return by_sev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orm', action='store_true', help='额外做 Django ORM 路径编译校验')
    ap.add_argument('--ci', action='store_true', help='CI 门禁模式：P0/P1>0 或存在未登记的 P2 时退出码 1')
    ap.add_argument('--p2-register', default=os.path.join(ROOT, 'scripts', 'p2_governance.json'),
                    help='P2 治理登记表路径（--ci 回归门禁比对用）')
    args = ap.parse_args()

    findings = []
    scan_views(findings)
    scan_serializers(findings)
    scan_mocks(findings)
    orm_checked = scan_orm_paths(findings) if args.orm else 0

    by_sev = write_reports(findings, orm_checked)
    print(f"扫描完成：共 {len(findings)} 项　P0={by_sev['P0']} P1={by_sev['P1']} P2={by_sev['P2']}")
    print('输出：scripts/audit_baseline.json、安全审计基线.md')

    if not args.ci:
        return 0

    # ---- CI 门禁：P0 / P1 硬失败 + P2 回归门禁（必须全部已登记治理）----
    failures = []
    if by_sev['P0']:
        failures.append(f"存在 {by_sev['P0']} 项 P0（致命越权），构建失败")
    if by_sev['P1']:
        failures.append(f"存在 {by_sev['P1']} 项 P1（未接入/形式挂靠隔离），构建失败")

    register_path = args.p2_register
    governed = {}
    if os.path.exists(register_path):
        try:
            governed = json.load(open(register_path, encoding='utf-8')).get('entries', {})
        except Exception as e:
            failures.append(f'读取 P2 治理登记表失败: {e}')
    else:
        failures.append(f'P2 治理登记表缺失: {register_path}')

    if governed:
        # 每条当前 P2 必须在登记簿中存在（按 detector|file|target 比对，抗行号漂移）
        ungoverned = []
        for x in findings:
            if x['severity'] != 'P2':
                continue
            key = f"{x['detector']}|{x['file']}|{x['target']}"
            if key not in governed:
                ungoverned.append(f"  - {x['file']}:{x['line']} {x['target']} [{x['detector']}]")
        if ungoverned:
            failures.append(
                f"存在 {len(ungoverned)} 条 P2 发现未在治理登记表中登记（新增/回归），"
                f"须先治理并写入 {os.path.basename(register_path)} 后方可合入：\n"
                + '\n'.join(ungoverned[:50]))

    if failures:
        print('\n[CI 门禁] 未通过：')
        for f in failures:
            print('  ' + f)
        return 1
    print('[CI 门禁] 通过：P0=0 P1=0，且全部 P2 已登记治理（回归门禁生效）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
