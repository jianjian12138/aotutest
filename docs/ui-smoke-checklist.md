# 全模块 UI 冒烟清单（F4）

> 目的：任何本地部署 / 升级合并后，**逐模块点开**确认能进、无 JS 报错、接口非 5xx。
> 触发：部署完成、分支合并、前端路由/守卫/导航改动后。
> 后端校验脚本（不用开浏览器）：见文末「后端 API 冒烟（curl 版）」。

## 0. 登录前置
- [ ] `/login` 可登录，token 写入内存（Pinia），刷新后由 httpOnly cookie 续期。
- [ ] 登录后停在首页 `/`（星球轨道卡片页）。
- [ ] 右上角显示用户名；下拉有「个人中心 / 退出登录」。

## 1. 首页轨道卡片（Home.vue）
逐一点击以下卡片，确认能跳转且目标页非 403/500：
- [ ] 需求与用例 → `/ai-generation/requirements`
- [ ] 接口测试 → `/api-testing/dashboard`
- [ ] UI自动化 → `/ui-automation/dashboard`
- [ ] 智能化测试 → `/natural-language-testing/web-testing`
- [ ] 安全测试 → `/strix-security/dashboard`
- [ ] 知识图谱 → `/knowledge-graph/dashboard`
- [ ] 专项测试 → `/special-testing/dashboard`（本期为友好提示，**不应再报「服务器错误」**）
- [ ] 数据工厂 → `/data-factory/dashboard`
- [ ] 性能测试 → `/performance-test/dashboard`
- [ ] 配置中心 → `/configuration/ai-model`
- [ ] 统一管理 → `/unified/projects`
- [ ] **Agent 测评 → `/eval`**（F3 新增，确认可达且标题为「Agent 测评 · LLM 测试舱」）

## 2. 系统管理（原 4×403 重灾区）
用 **admin 超管**登录，逐项确认**不再跳 403**：
- [ ] 缺陷管理 → `/system/defects`
- [ ] 角色与权限 → `/system/roles`
- [ ] 审计管理 → `/system/audit`
- [ ] 租户管理 → `/system/tenants`
- [ ] 用户管理 → `/configuration/users`
- [ ] 进入后左侧「当前模块」菜单正确高亮，面包屑显示模块名。

## 3. Agent 测评舱（/eval，重点）
- [ ] 进入后左侧显示「评测看板」且模块名显示「Agent 测评」。
- [ ] 数据集列表 `/api/eval/datasets/` 返回 200（空列表也可）。
- [ ] 运行列表 `/api/eval/runs/` 200；榜单 `/api/eval/runs/leaderboard/` 200。
- [ ] 若显示 403：检查该用户所属租户是否开通 `AGENT_EVAL` 功能开关
      （`TenantFeature(tenant, AGENT_EVAL, enabled=True)`，超管**不豁免**此开关）。

## 4. 专项测试（F2 友好化验收）
- [ ] 进入看板有「本期未交付」友好提示，无「服务器错误」弹窗。
- [ ] 子页（MQTT/Monkey/Redis/Kafka）不再调不存在的接口导致 5xx。

## 5. 控制台错误
- [ ] 打开浏览器 DevTools Console，逐项点开时无红色 `Uncaught` / `403/500` 网络错误。
- [ ] Network 面板确认关键 GET 均为 2xx（除预期 404 的静态资源）。

---

## 后端 API 冒烟（curl 版，无需浏览器）
```bash
BASE=http://127.0.0.1:8686/api
TOKEN=$(curl -s -X POST "$BASE/users/login/" -H "Content-Type: application/json" \
        -d '{"username":"<admin>","password":"<pwd>"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")

# 系统管理（应全 200）
for p in users/me roles audit user-roles organizations users/list; do
  printf "%-18s -> %s\n" "$p" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/$p/" -H "Authorization: Bearer $TOKEN")"
done

# Agent 测评（应全 200；403=租户未开通 AGENT_EVAL）
for p in eval/datasets eval/runs eval/runs/leaderboard eval/graders eval/cases; do
  printf "%-30s -> %s\n" "$p" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/$p/" -H "Authorization: Bearer $TOKEN")"
done
```
