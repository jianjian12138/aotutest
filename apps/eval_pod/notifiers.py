"""P3-16 IM 通知（飞书 / 企业微信 / 钉钉）。

均为 webhook 机器人推送，确定性、无额外依赖（仅 requests）。
- 飞书：可选 secret 签名（timestamp+sign，HMAC-SHA256 base64）
- 企微：webhook 含 key，无签名，纯 text
- 钉钉：可选 secret 签名（timestamp(ms)+sign）
所有发送失败被吞掉并返回结构化结果，不阻断调度主流程。
"""
import base64
import hashlib
import hmac
import time
import urllib.parse

import requests


def _feishu_signed_url(webhook, secret):
    timestamp = str(int(time.time()))
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'),
                         hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    sep = '&' if '?' in webhook else '?'
    return f'{webhook}{sep}timestamp={timestamp}&sign={urllib.parse.quote(sign)}'


def _dingtalk_signed_url(webhook, secret):
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'),
                         hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode('utf-8'))
    sep = '&' if '?' in webhook else '?'
    return f'{webhook}{sep}timestamp={timestamp}&sign={sign}'


def send_to_channel(channel, text):
    """向单个渠道发送文本，返回 {type, ok, status, detail}。"""
    ctype = (channel.get('type') or '').lower()
    webhook = channel.get('webhook') or ''
    secret = channel.get('secret') or ''
    if not webhook:
        return {'type': ctype, 'ok': False, 'status': None, 'detail': '缺少 webhook'}

    try:
        if ctype == 'feishu':
            url = _feishu_signed_url(webhook, secret) if secret else webhook
            payload = {'msg_type': 'text', 'content': {'text': text}}
        elif ctype == 'wecom':
            url = webhook
            payload = {'msgtype': 'text', 'text': {'content': text}}
        elif ctype == 'dingtalk':
            url = _dingtalk_signed_url(webhook, secret) if secret else webhook
            payload = {'msgtype': 'text', 'text': {'content': text}}
        else:
            return {'type': ctype, 'ok': False, 'status': None, 'detail': f'未知渠道类型: {ctype}'}

        resp = requests.post(url, json=payload, timeout=10)
        return {'type': ctype, 'ok': resp.ok, 'status': resp.status_code,
                'detail': resp.text[:200]}
    except Exception as exc:  # noqa: BLE001
        return {'type': ctype, 'ok': False, 'status': None, 'detail': str(exc)[:200]}


def notify_im(channels, title, content):
    """向多个渠道广播一条通知，返回结果列表。"""
    if not channels:
        return []
    body = f'{title}\n\n{content}' if title else content
    results = []
    for ch in channels:
        results.append(send_to_channel(ch, body))
    return results


def build_run_summary(run, schedule=None):
    """构造一次运行完成后的通知文本（纯文本，兼容三端）。"""
    name = schedule.name if schedule else '定时评测'
    lines = [
        f'运行 #{run.id} · 数据集 {run.dataset.name}',
        f'分数 {run.mean_score} · 通过率 {run.pass_rate} · 边缘通过率 {run.edge_pass_rate}',
        f'状态 {run.status}',
    ]
    if run.pass_k_rate is not None:
        lines.append(f'Pass^k 可靠性 {run.pass_k_rate}')
    failed = run.results.filter(passed=False).count()
    if failed:
        lines.append(f'未通过用例 {failed} 条')
    if schedule:
        lines.append(f'下次运行 {schedule.next_run_at}')
    return '\n'.join(lines)
