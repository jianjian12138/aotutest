<template>
  <BasePage title="Agent 测评 · LLM 测试舱">
    <div style="padding: 8px 4px;">
      <!-- 数据集选择器 -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
          <span style="font-weight: 600;">评测数据集</span>
          <el-select
            v-model="selectedDatasetId"
            placeholder="选择数据集"
            filterable
            style="width: 320px;"
            @change="onDatasetChange"
          >
            <el-option
              v-for="d in datasets"
              :key="d.id"
              :label="`${d.name}@${d.version} (${d.case_count} 用例 / 边缘 ${d.edge_ratio})`"
              :value="d.id"
            />
          </el-select>
          <el-button type="primary" :loading="loadingDatasets" @click="fetchDatasets">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <el-tag v-if="selectedDataset" type="info">
            {{ selectedDataset.organization }} · {{ selectedDataset.case_count }} 用例 · 边缘占比 {{ selectedDataset.edge_ratio }}
          </el-tag>
        </div>
      </el-card>

      <!-- P3-14 Copilot · 评测方案设计器（自然语言 → 结构化方案 → 一键落地运行） -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <template #header>
          <div style="display:flex;align-items:center;gap:8px;">
            <el-icon><MagicStick /></el-icon>
            <b>Copilot · 评测方案设计器</b>
            <el-tag size="small" type="success">自然语言 → 结构化方案</el-tag>
          </div>
        </template>
        <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap;">
          <el-input
            v-model="planReqText" type="textarea" :rows="2" style="flex:1;min-width:320px;"
            placeholder="用一句话描述评测需求，例如：评测智能体的工具调用正确性与目标达成度，要求可靠性重复 3 次"
          />
          <div style="display:flex;flex-direction:column;gap:8px;">
            <el-select v-model="planMode" style="width:180px;">
              <el-option label="离线规则（零外送）" value="offline" />
              <el-option label="LLM 增强（租户模型）" value="llm" />
            </el-select>
            <el-button type="primary" :loading="planLoading" @click="doDesignPlan">
              <el-icon><MagicStick /></el-icon> 生成方案
            </el-button>
          </div>
        </div>
        <el-alert v-if="planResult" type="info" :closable="false" style="margin-top:12px;">
          <template #default>
            <div style="font-size:13px;">
              <div>
                <b>{{ planResult.title }}</b>
                <el-tag v-if="planResult.llm_used" size="small" type="warning">LLM 增强</el-tag>
                <el-tag v-else size="small">规则模板</el-tag>
              </div>
              <div style="margin-top:6px;color:#475569;">{{ planResult.summary }}</div>
              <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                <span>数据集：</span>
                <el-tag v-for="id in planResult.dataset_ids" :key="id" size="small">{{ id }}</el-tag>
                <span style="margin-left:8px;">维度：</span>
                <el-tag v-for="m in planResult.metrics" :key="m" size="small" type="info">{{ m }}</el-tag>
              </div>
              <div style="margin-top:6px;font-size:12px;color:#64748b;">
                门禁阈值：{{ JSON.stringify(planResult.gate_thresholds) }} ·
                重复 {{ planResult.repeat_k }} 次 · 基线运行 #{{ planResult.baseline_run_id ?? '无' }}
              </div>
              <el-button
                size="small" type="success" style="margin-top:10px;"
                :loading="planConfirming" @click="doConfirmPlan"
              >确认并创建运行</el-button>
              <span v-if="planRunIds.length" style="margin-left:10px;font-size:13px;color:#16a34a;">
                已创建运行 #{{ planRunIds.join(' / #') }}
              </span>
            </div>
          </template>
        </el-alert>
      </el-card>

      <!-- P3-13 知识中枢 RAG（需求文档/Confluence/飞书 辅助 B1 用例生成） -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <template #header>
          <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:8px;">
              <el-icon><MagicStick /></el-icon>
              <b>知识中枢 · RAG 上下文</b>
              <el-tag size="small" type="success">离线词法检索 · 零外送</el-tag>
            </div>
            <el-button size="small" @click="fetchKnowledge">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </template>

        <!-- 入库表单 -->
        <el-input v-model="kbTitle" placeholder="知识文档标题，如：订单接口需求文档" style="max-width:320px;" />
        <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;align-items:flex-start;">
          <el-select v-model="kbSource" style="width:150px;">
            <el-option label="需求文档" value="REQUIREMENT" />
            <el-option label="Confluence" value="CONFLUENCE" />
            <el-option label="飞书文档" value="FEISHU" />
            <el-option label="上传文件" value="UPLOAD" />
            <el-option label="笔记/手动" value="NOTE" />
          </el-select>
          <el-input
            v-model="kbContent" type="textarea" :rows="3" style="flex:1;min-width:320px;"
            placeholder="粘贴需求 / 接口 / 产品文档正文。保存后自动分块，供 RAG 检索辅助用例生成。"
          />
          <el-button type="primary" :loading="kbIngesting" @click="doIngest">
            <el-icon><MagicStick /></el-icon> 入库
          </el-button>
        </div>

        <!-- 文档列表 + 检索 -->
        <el-divider content-position="left">已入库知识（{{ knowledgeDocs.length }}）</el-divider>
        <div v-if="knowledgeDocs.length" style="display:flex;flex-direction:column;gap:8px;">
          <div
            v-for="d in knowledgeDocs" :key="d.id"
            style="display:flex;align-items:center;gap:10px;border:1px solid #e2e8f0;border-radius:8px;padding:8px 10px;"
          >
            <el-tag size="small" type="info">{{ d.source_type }}</el-tag>
            <span style="flex:1;font-weight:600;">{{ d.title }}</span>
            <el-tag size="small">{{ d.chunk_count }} 块</el-tag>
            <el-button link type="danger" size="small" @click="doDeleteKb(d.id)">删除</el-button>
          </div>
        </div>
        <el-empty v-else description="暂无知识文档，先入库一份需求文档" :image-size="60" />

        <el-divider content-position="left">RAG 检索预览</el-divider>
        <div style="display:flex;gap:10px;align-items:flex-start;">
          <el-input
            v-model="kbQuery" type="textarea" :rows="2" style="flex:1;min-width:280px;"
            placeholder="输入检索词（如：订单接口 支付状态），预览命中的知识片段"
          />
          <el-button :loading="kbSearching" @click="doSearchKb">
            <el-icon><Search /></el-icon> 检索
          </el-button>
        </div>
        <div v-if="kbHits.length" style="margin-top:10px;display:flex;flex-direction:column;gap:8px;">
          <div
            v-for="(h, i) in kbHits" :key="i"
            style="border:1px solid #e2e8f0;border-radius:8px;padding:8px 10px;background:#f8fafc;"
          >
            <div style="font-size:12px;color:#475569;margin-bottom:4px;">
              <b>{{ h.doc_title }}</b> · 相似度 {{ h.score }} · #{{ h.chunk_idx }}
            </div>
            <div style="font-size:13px;white-space:pre-wrap;">{{ h.text }}</div>
          </div>
        </div>
      </el-card>

      <!-- P3-16 定时评测（平台内部调度模型）+ IM 通知（飞书/企微/钉钉） -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <template #header>
          <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:8px;">
              <el-icon><Timer /></el-icon>
              <b>定时评测 + IM 通知</b>
              <el-tag size="small" type="success">平台内部调度守护</el-tag>
              <el-tag size="small" type="warning">飞书 / 企微 / 钉钉 三端打通</el-tag>
            </div>
            <div style="display:flex;gap:8px;">
              <el-button size="small" @click="fetchSchedules">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
              <el-button size="small" type="primary" @click="openSchedDialog">
                <el-icon><Plus /></el-icon> 新建调度
              </el-button>
            </div>
          </div>
        </template>

        <el-table :data="schedules" size="small" v-loading="schedLoading" style="width:100%;">
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column label="触发" width="200">
            <template #default="{ row }">
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
                {{ triggerLabel(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="下次运行" width="170">
            <template #default="{ row }">
              <span style="font-size:12px;">{{ fmtTime(row.next_run_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="statusType(row.last_status)">{{ row.last_status || 'IDLE' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="80">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" @change="(v) => toggleSched(row, v)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="200">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="fireSched(row)">立即执行</el-button>
              <el-button link type="warning" size="small" @click="openNotifyDialog(row)">测试通知</el-button>
              <el-button link type="danger" size="small" @click="deleteSched(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!schedLoading && !schedules.length" description="暂无定时调度，点击「新建调度」创建一条" :image-size="60" />

        <!-- 新建 / 编辑调度 -->
        <el-dialog v-model="showSchedDialog" title="新建定时评测调度" width="640px" append-to-body @close="resetSchedForm">
          <el-form label-width="110px" size="small">
            <el-form-item label="名称" required>
              <el-input v-model="schedForm.name" placeholder="如：每日冒烟评测" />
            </el-form-item>
            <el-form-item label="数据集" required>
              <el-select v-model="schedForm.dataset" filterable placeholder="选择数据集" style="width:100%;">
                <el-option v-for="d in datasets" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="评分器" required>
              <el-select v-model="schedForm.grader" filterable placeholder="选择评分器" style="width:100%;">
                <el-option v-for="g in graders" :key="g.id" :label="g.name" :value="g.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="Agent 配置">
              <el-select v-model="schedForm.agent_config" filterable clearable placeholder="可选：被评测的 agent/模型（自动产出 outputs）" style="width:100%;">
                <el-option v-for="m in agentModels" :key="m.id" :label="m.name" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="触发类型">
              <el-radio-group v-model="schedForm.trigger_type">
                <el-radio value="interval">间隔(分钟)</el-radio>
                <el-radio value="daily">每日定时</el-radio>
                <el-radio value="cron">Cron 表达式</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="间隔(分钟)" v-if="schedForm.trigger_type === 'interval'">
              <el-input-number v-model="schedForm.interval_minutes" :min="1" :max="10080" />
            </el-form-item>
            <el-form-item label="每日时间" v-if="schedForm.trigger_type === 'daily'">
              <el-time-picker v-model="schedForm.daily_at" format="HH:mm" value-format="HH:mm" placeholder="选择时间" />
            </el-form-item>
            <el-form-item label="Cron" v-if="schedForm.trigger_type === 'cron'">
              <el-input v-model="schedForm.cron" placeholder="如：*/5 * * * *" />
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="schedForm.enabled" />
            </el-form-item>
            <el-form-item label="IM 通知渠道">
              <div style="width:100%;display:flex;flex-direction:column;gap:8px;">
                <div
                  v-for="(ch, i) in schedForm.notify_channels" :key="i"
                  style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;border:1px dashed #e2e8f0;padding:8px;border-radius:8px;"
                >
                  <el-select v-model="ch.type" style="width:120px;">
                    <el-option label="飞书" value="feishu" />
                    <el-option label="企业微信" value="wecom" />
                    <el-option label="钉钉" value="dingtalk" />
                  </el-select>
                  <el-input v-model="ch.webhook" placeholder="Webhook 地址" style="flex:1;min-width:200px;" />
                  <el-input v-model="ch.secret" placeholder="签名 secret（可选）" style="width:180px;" />
                  <el-button link type="danger" @click="schedForm.notify_channels.splice(i, 1)">移除</el-button>
                </div>
                <el-button size="small" @click="schedForm.notify_channels.push({ type: 'feishu', webhook: '', secret: '' })">
                  <el-icon><Plus /></el-icon> 添加渠道
                </el-button>
              </div>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showSchedDialog = false">取消</el-button>
            <el-button type="primary" :loading="schedSaving" @click="saveSchedule">保存</el-button>
          </template>
        </el-dialog>

        <!-- 测试 IM 通知 -->
        <el-dialog v-model="showNotifyDialog" title="测试 IM 通知" width="560px" append-to-body>
          <div style="display:flex;flex-direction:column;gap:8px;">
            <div
              v-for="(ch, i) in testChannels" :key="i"
              style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;border:1px dashed #e2e8f0;padding:8px;border-radius:8px;"
            >
              <el-select v-model="ch.type" style="width:120px;">
                <el-option label="飞书" value="feishu" />
                <el-option label="企业微信" value="wecom" />
                <el-option label="钉钉" value="dingtalk" />
              </el-select>
              <el-input v-model="ch.webhook" placeholder="Webhook 地址" style="flex:1;min-width:200px;" />
              <el-input v-model="ch.secret" placeholder="签名 secret（可选）" style="width:180px;" />
              <el-button link type="danger" @click="testChannels.splice(i, 1)">移除</el-button>
            </div>
            <el-button size="small" @click="testChannels.push({ type: 'feishu', webhook: '', secret: '' })">
              <el-icon><Plus /></el-icon> 添加渠道
            </el-button>
          </div>
          <el-alert
            v-if="notifyTestResult"
            :type="notifyTestResult.ok ? 'success' : 'error'"
            :closable="false" style="margin-top:12px;"
          >
            <template #default>
              <div style="font-size:12px;">
                <div v-for="(r, i) in notifyTestResult.results" :key="i">
                  [{{ r.type }}] {{ r.ok ? '成功' : '失败' }} · {{ r.detail || r.status }}
                </div>
              </div>
            </template>
          </el-alert>
          <template #footer>
            <el-button @click="showNotifyDialog = false">关闭</el-button>
            <el-button type="primary" :loading="notifyTesting" @click="sendTestNotify">发送测试</el-button>
          </template>
        </el-dialog>
      </el-card>

      <!-- P3-4 评测技能版本化 -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <template #header>
          <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:8px;">
              <el-icon><Files /></el-icon>
              <b>评测技能版本化</b>
              <el-tag size="small" type="success">可复现</el-tag>
              <el-tag size="small" type="warning">审计溯源</el-tag>
            </div>
            <div style="display:flex;gap:8px;">
              <el-button size="small" @click="fetchSkillVersions">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
              <el-button size="small" type="primary" :loading="publishing" @click="publishDiskVersion">
                <el-icon><Upload /></el-icon> 发布当前技能（磁盘快照）
              </el-button>
            </div>
          </div>
        </template>

        <el-alert
          v-if="!versions.length && !versionsLoading"
          type="info" :closable="false"
          title="尚未发布任何技能版本。每次评测运行都会绑定一个技能版本以保证可复现与审计；点击「发布当前技能」从磁盘 SKILL.md 快照首个版本。"
          style="margin-bottom:12px;"
        />
        <el-table v-else :data="versions" size="small" v-loading="versionsLoading" style="width:100%;">
          <el-table-column prop="skill_key" label="技能" width="140" />
          <el-table-column label="版本" width="100">
            <template #default="{ row }">
              <b>{{ row.version }}</b>
              <el-tag v-if="row.is_active" size="small" type="success" style="margin-left:4px;">生效</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="内容指纹" min-width="120">
            <template #default="{ row }">
              <span style="font-family:monospace;font-size:11px;">{{ (row.content_hash || '').slice(0, 12) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="note" label="说明" min-width="140" />
          <el-table-column label="创建" width="120">
            <template #default="{ row }">
              <span style="font-size:12px;">{{ fmtTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button link type="primary" size="small" :disabled="row.is_active" :loading="row._activating" @click="setActive(row)">设为生效</el-button>
              <el-button link type="info" size="small" @click="openDiff(row)">差异</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="svShowDiffDialog" title="技能版本差异" width="760px" append-to-body>
          <div v-if="svDiffTarget" style="margin-bottom:10px;font-size:12px;color:#64748b;">
            对比：<b>{{ svDiffTarget.from }}</b> → <b>{{ svDiffTarget.to }}</b>
          </div>
          <pre v-if="svDiffText" style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:8px;max-height:420px;overflow:auto;font-size:12px;white-space:pre-wrap;">{{ svDiffText }}</pre>
          <el-empty v-else description="无差异" :image-size="50" />
          <template #footer>
            <el-button @click="svShowDiffDialog = false">关闭</el-button>
          </template>
        </el-dialog>
      </el-card>

      <!-- P3-5 冷启动标准：新租户首次运行引导 -->
      <el-card v-if="coldStart.is_cold_start" class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <template #header>
          <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:8px;">
              <el-icon color="#e6a23c"><Warning /></el-icon>
              <b>冷启动引导</b>
              <el-tag size="small" type="warning">新租户</el-tag>
            </div>
            <el-button size="small" type="primary" :loading="applyingCold" @click="applyColdStartDefaults">
              <el-icon><MagicStick /></el-icon> 一键应用默认评分器
            </el-button>
          </div>
        </template>
        <el-alert type="warning" :closable="false" style="margin-bottom:12px;"
          :title="`尚未配置任何评分器（冷启动状态）。已为你准备 ${coldStart.template_count} 套默认评分器模板与推荐质量门，点击右上角一键初始化即可立即开始评测；未配置 LLM 的评分器会自动降级为确定性启发式（数据不出域）。`" />
        <div style="font-size:13px;color:#606266;margin-bottom:8px;"><b>推荐默认质量门（C1 分层门禁）</b></div>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="核心·均分 mean_score">≥ {{ coldStart.default_gate?.thresholds?.mean_score }}</el-descriptions-item>
          <el-descriptions-item label="核心·通过率 pass_rate">≥ {{ coldStart.default_gate?.thresholds?.pass_rate }}</el-descriptions-item>
          <el-descriptions-item label="基线劣化 regress_delta">≤ {{ coldStart.default_gate?.regress_delta }}</el-descriptions-item>
          <el-descriptions-item label="辅助·边缘通过率 edge_pass_rate">≥ {{ coldStart.default_gate?.aux_thresholds?.edge_pass_rate }}</el-descriptions-item>
          <el-descriptions-item label="辅助·Pass^k 可靠性">≥ {{ coldStart.default_gate?.aux_thresholds?.pass_k_rate }}</el-descriptions-item>
          <el-descriptions-item label="基线策略">首个 DONE 运行自动设为基线</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- P3-9 边缘用例规则 -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <template #header>
          <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:8px;">
              <el-icon color="#409eff"><MagicStick /></el-icon>
              <b>P3-9 边缘用例规则</b>
              <el-tag size="small" type="info">对抗 / 异常 / 长尾</el-tag>
            </div>
            <div style="display:flex;gap:8px;">
              <el-button size="small" :loading="seedingEdge" @click="seedDefaultEdgeRules">
                <el-icon><MagicStick /></el-icon> 一键应用默认规则
              </el-button>
              <el-button size="small" type="primary" @click="openEdgeApply">
                <el-icon><Plus /></el-icon> 对数据集生成边缘用例
              </el-button>
            </div>
          </div>
        </template>
        <div style="font-size:13px;color:#606266;margin-bottom:8px;">
          边缘用例规则把数据集中的「普通用例」派生为异常输入 / 对抗样本 / 长尾场景等边缘用例
          （标记 <b>is_edge=True</b>），让门禁的 <b>edge_pass_rate</b> 指标真正有数据可算。
        </div>
        <el-table v-if="edgeRules.length" :data="edgeRules" size="small" border max-height="240">
          <el-table-column prop="name" label="规则" min-width="140" />
          <el-table-column prop="code" label="代码" width="180" />
          <el-table-column prop="category" label="类别" width="120">
            <template #default="{ row }">{{ row.category === 'INPUT_MUTATION' ? '输入变异' : '输出约束' }}</template>
          </el-table-column>
          <el-table-column label="启用" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
        </el-table>
        <el-empty v-else description="尚未配置边缘用例规则，点击右上角「一键应用默认规则」" :image-size="80" />
      </el-card>

      <!-- P3-11 评判模型强度自校准 -->
      <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b>P3-11 评判模型强度自校准</b>
            <el-button size="small" type="primary" :loading="assessingJudge" @click="doAssessJudge">一键评估裁判强度</el-button>
          </div>
        </template>
        <el-alert type="info" :closable="false" style="margin-bottom:12px;">
          基于内置金标准校准集（8 个无歧义样本）评估本租户评判模型与人工标注的一致性；
          强度分越低代表裁判越「不可信」，建议人工复核或换模型（零外送，数据不出域）。
        </el-alert>
        <el-table :data="judgeStrengths" size="small" v-loading="judgeLoading">
          <el-table-column prop="model_name" label="评判模型" />
          <el-table-column prop="strength_score" label="强度分(0-1)" />
          <el-table-column prop="agreement" label="一致样本" />
          <el-table-column prop="sample_size" label="样本总数" />
          <el-table-column prop="created_at" label="评估时间" />
        </el-table>
        <el-empty v-if="!judgeLoading && judgeStrengths.length === 0" description="尚未评估，点击右上角按钮开始" :image-size="80" />
      </el-card>

      <!-- P3-9 生成边缘用例对话框 -->
      <el-dialog v-model="edgeApplyVisible" title="对数据集生成边缘用例" width="560px">
        <el-form label-width="110px">
          <el-form-item label="目标数据集">
            <el-select v-model="edgeApplyForm.dataset_id" filterable placeholder="选择数据集" style="width:100%">
              <el-option v-for="d in datasetOptions" :key="d.id" :label="`${d.name} (${d.version || '-'})`" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="选用规则">
            <el-select v-model="edgeApplyForm.rule_ids" multiple collapse-tags placeholder="留空 = 全部启用规则" style="width:100%">
              <el-option v-for="r in edgeRules" :key="r.id" :label="`${r.name} (${r.code})`" :value="r.id" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="edgeApplyVisible=false">取消</el-button>
          <el-button type="primary" :loading="applyingEdge" @click="doApplyEdgeRules">生成</el-button>
        </template>
      </el-dialog>

      <el-row :gutter="16" v-if="selectedDataset">
        <!-- 左：概览卡片 + 报告 -->
        <el-col :span="14">
          <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
            <template #header><b>报告概览</b></template>
            <el-skeleton v-if="reportLoading" :rows="4" />
            <template v-else>
              <el-row :gutter="12">
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.total_runs }}</div><div class="m-label">运行数</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.avg_mean_score ?? '—' }}</div><div class="m-label">平均分数</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.avg_pass_rate ?? '—' }}</div><div class="m-label">平均通过率</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ report.latest ? report.latest.mean_score : '—' }}</div><div class="m-label">最近分数</div></div></el-col>
              </el-row>
              <el-table :data="report.grader_breakdown" size="small" style="margin-top: 12px;">
                <el-table-column prop="grader_type" label="评分器" />
                <el-table-column prop="run_count" label="运行数" />
                <el-table-column prop="avg_mean_score" label="均分" />
              </el-table>
              <!-- P3-10：能力/回归集分离 —— 最近一次运行按用例角色拆分通过率 -->
              <div v-if="roleSplit" style="display:flex;gap:12px;margin-top:14px;flex-wrap:wrap;">
                <div class="metric" style="flex:1;min-width:140px;">
                  <div class="m-val">{{ roleSplit.capability_pass_rate != null ? roleSplit.capability_pass_rate : '—' }}</div>
                  <div class="m-label">能力集通过率 (CAPABILITY)</div>
                </div>
                <div class="metric" style="flex:1;min-width:140px;">
                  <div class="m-val">{{ roleSplit.regression_pass_rate != null ? roleSplit.regression_pass_rate : '—' }}</div>
                  <div class="m-label">回归集通过率 (REGRESSION)</div>
                </div>
              </div>
              <!-- P3-2：成本 / 时延概览（取最近一次运行） -->
              <div v-if="latestCost" style="display:flex;gap:12px;margin-top:14px;flex-wrap:wrap;">
                <div class="metric" style="flex:1;min-width:120px;">
                  <div class="m-val">{{ latestCost.tokens }}</div><div class="m-label">最近运行 Token 总耗</div>
                </div>
                <div class="metric" style="flex:1;min-width:120px;">
                  <div class="m-val">{{ latestCost.calls }}</div><div class="m-label">工具调用数</div>
                </div>
                <div class="metric" style="flex:1;min-width:120px;">
                  <div class="m-val">{{ latestCost.latAvg }}</div><div class="m-label">平均时延 (s)</div>
                </div>
                <div class="metric" style="flex:1;min-width:120px;">
                  <div class="m-val">{{ latestCost.latMax }}</div><div class="m-label">最长时延 (s)</div>
                </div>
              </div>
              <!-- P3-7：评测集饱和指数（区分度低 → 告警） -->
              <el-alert
                v-if="report.saturation"
                :title="saturationTitle"
                :type="report.saturation.saturated ? 'warning' : 'success'"
                :closable="false" style="margin-top:12px;"
              >
                <template #default>
                  <span style="font-size:13px;">
                    饱和指数 {{ report.saturation.saturation_index ?? '—' }}
                    （运行间分数标准差 {{ report.saturation.score_std ?? '—' }}）· {{ report.saturation.reason }}
                  </span>
                </template>
              </el-alert>
            </template>
          </el-card>

          <!-- P3-17 分层报告产物（最近一次 DONE 运行的 L0/L1/L2） -->
          <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
            <template #header>
              <b>P3-17 分层报告产物</b>
              <span style="font-size:12px;color:#909399;margin-left:8px;">（最近一次运行 · 按层下钻）</span>
            </template>
            <el-skeleton v-if="layeredLoading" :rows="5" />
            <template v-else-if="layered && layered.L0">
              <!-- L0 总览 -->
              <div class="lb-title">L0 · 总览（{{ layered.L0.model_name }} · {{ layered.L0.status }}<span v-if="layered.L0.is_baseline"> · 基线</span>）</div>
              <el-row :gutter="12">
                <el-col :span="4"><div class="metric"><div class="m-val">{{ layered.L0.total }}</div><div class="m-label">用例数</div></div></el-col>
                <el-col :span="4"><div class="metric"><div class="m-val" style="color:#67c23a;">{{ layered.L0.passed }}</div><div class="m-label">通过</div></div></el-col>
                <el-col :span="4"><div class="metric"><div class="m-val" :style="{color: layered.L0.failed ? '#f56c6c' : '#67c23a'}">{{ layered.L0.failed }}</div><div class="m-label">失败</div></div></el-col>
                <el-col :span="4"><div class="metric"><div class="m-val">{{ layered.L0.mean_score != null ? layered.L0.mean_score : '—' }}</div><div class="m-label">均分</div></div></el-col>
                <el-col :span="4"><div class="metric"><div class="m-val">{{ layered.L0.pass_rate != null ? layered.L0.pass_rate : '—' }}</div><div class="m-label">通过率</div></div></el-col>
                <el-col :span="4"><div class="metric"><div class="m-val" :style="{color: layered.L0.red_line_hits ? '#e6a23c' : '#67c23a'}">{{ layered.L0.red_line_hits }}</div><div class="m-label">红线命中</div></div></el-col>
              </el-row>
              <el-row :gutter="12" style="margin-top:10px;">
                <el-col :span="6"><div class="metric"><div class="m-val">{{ layered.L0.edge_pass_rate != null ? layered.L0.edge_pass_rate : '—' }}</div><div class="m-label">边缘通过率</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ layered.L0.capability_pass_rate != null ? layered.L0.capability_pass_rate : '—' }}</div><div class="m-label">能力集通过率</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ layered.L0.regression_pass_rate != null ? layered.L0.regression_pass_rate : '—' }}</div><div class="m-label">回归集通过率</div></div></el-col>
                <el-col :span="6"><div class="metric"><div class="m-val">{{ layered.L0.pass_k_rate != null ? layered.L0.pass_k_rate : '—' }}</div><div class="m-label">Pass^k 可靠性</div></div></el-col>
              </el-row>

              <!-- L1 分类 -->
              <div class="lb-title" style="margin-top:16px;">L1 · 分类（角色 / 边缘 / 评分器）</div>
              <el-row :gutter="12">
                <el-col :span="8">
                  <div class="lb-sub">按角色</div>
                  <el-table :data="layerRoleRows" size="small">
                    <el-table-column prop="key" label="角色" />
                    <el-table-column prop="count" label="数" width="46" />
                    <el-table-column prop="passed" label="通过" width="46" />
                    <el-table-column prop="failed" label="失败" width="46" />
                    <el-table-column prop="pass_rate" label="通过率" />
                  </el-table>
                </el-col>
                <el-col :span="8">
                  <div class="lb-sub">按边缘</div>
                  <el-table :data="layerEdgeRows" size="small">
                    <el-table-column prop="key" label="类型" />
                    <el-table-column prop="count" label="数" width="46" />
                    <el-table-column prop="passed" label="通过" width="46" />
                    <el-table-column prop="failed" label="失败" width="46" />
                    <el-table-column prop="pass_rate" label="通过率" />
                  </el-table>
                </el-col>
                <el-col :span="8">
                  <div class="lb-sub">按评分器</div>
                  <el-table :data="layerJudgeRows" size="small">
                    <el-table-column prop="key" label="评分器" />
                    <el-table-column prop="count" label="数" width="46" />
                    <el-table-column prop="passed" label="通过" width="46" />
                    <el-table-column prop="failed" label="失败" width="46" />
                    <el-table-column prop="pass_rate" label="通过率" />
                  </el-table>
                </el-col>
              </el-row>

              <!-- L2 失败 TopN -->
              <div class="lb-title" style="margin-top:16px;">
                L2 · 失败用例 TopN（按分数升序，最差在前）· 共 {{ layered.L2.failed_count }} 条
              </div>
              <el-table :data="layered.L2.failed" size="small" max-height="300">
                <el-table-column prop="case_id" label="用例" width="56" />
                <el-table-column prop="code" label="code" width="90" />
                <el-table-column prop="score" label="分数" width="64" />
                <el-table-column prop="judge" label="裁判" width="84" />
                <el-table-column prop="input_text" label="输入" show-overflow-tooltip />
                <el-table-column label="红线" width="130">
                  <template #default="{ row }">
                    <el-tag v-for="f in (row.red_flags || [])" :key="f" type="danger" size="small" style="margin-right:3px;">{{ f }}</el-tag>
                    <span v-if="!row.red_flags || !row.red_flags.length" style="color:#909399;">—</span>
                  </template>
                </el-table-column>
              </el-table>
            </template>
            <el-empty v-else description="该数据集尚无 DONE 运行，无法生成分层报告" :image-size="80" />
          </el-card>

          <!-- 运行列表 + 运行级动作 -->
          <el-card class="premium-card" shadow="never">
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="display:flex;align-items:center;gap:10px;">
                  <el-switch v-model="realtime" size="small" active-text="实时刷新" @change="onRealtimeChange" />
                  <b>运行记录</b>
                </div>
                <el-button size="small" type="success" @click="openRunDialog(null)">
                  <el-icon><VideoPlay /></el-icon> 执行评测
                </el-button>
              </div>
            </template>
            <el-table :data="datasetRuns" size="small" v-loading="runsLoading">
              <el-table-column prop="id" label="ID" width="70" />
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'DONE' ? 'success' : (row.status === 'FAILED' ? 'danger' : 'info')" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="mean_score" label="分数" />
              <el-table-column prop="pass_rate" label="通过率" />
              <el-table-column prop="model_config_name" label="模型" />
              <el-table-column label="基线" width="70">
                <template #default="{ row }">
                  <el-tag v-if="row.is_baseline" type="warning" size="small">基线</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openRunDialog(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <!-- 右：生成用例 + 版本 Diff -->
        <el-col :span="10">
          <el-card class="premium-card" shadow="never" style="margin-bottom: 16px;">
            <template #header><b>B1 用例生成 Agent</b></template>
            <el-input
              v-model="reqText"
              type="textarea"
              :rows="5"
              placeholder="粘贴需求 / 接口描述，按换行或分号拆分条目。例如：输入：问天气&#10;期望：返回晴&#10;输入：攻击越权&#10;期望：拒绝"
            />
            <div style="display:flex;align-items:center;gap:12px;margin-top:12px;flex-wrap:wrap;">
              <el-select v-model="genMode" style="width: 160px;">
                <el-option label="离线（零外送·默认）" value="offline" />
                <el-option label="LLM 升级（租户模型）" value="llm" />
              </el-select>
              <el-select
                v-model="genKnowledgeIds" multiple collapse-tags placeholder="接入知识库（RAG）"
                style="min-width: 220px;" :disabled="!knowledgeDocs.length"
              >
                <el-option
                  v-for="d in knowledgeDocs" :key="d.id" :label="`${d.title}（${d.source_type}）`" :value="d.id"
                />
              </el-select>
              <el-button type="primary" :loading="genLoading" @click="doGenerate">
                <el-icon><MagicStick /></el-icon> 生成并写入
              </el-button>
            </div>
            <div v-if="genKnowledgeIds.length" style="margin-top:8px;font-size:12px;color:#64748b;">
              已接入 {{ genKnowledgeIds.length }} 份知识库，RAG 上下文将辅助生成接地用例
            </div>
            <el-alert
              v-if="genResult"
              :title="`已生成 ${genResult.generated_count} 条用例（llm_used=${genResult.llm_used}）`"
              type="success" :closable="false" style="margin-top:12px;"
            />
          </el-card>

          <el-card class="premium-card" shadow="never">
            <template #header><b>A3 版本化 / Diff</b></template>
            <el-button size="small" @click="doClone">克隆为新版本</el-button>
            <div style="display:flex;align-items:center;gap:8px;margin-top:12px;flex-wrap:wrap;">
              <el-select v-model="diffBase" placeholder="基准版本" style="width:140px;">
                <el-option v-for="v in versionsOfName" :key="v.id" :label="`${v.version}`" :value="v.id" />
              </el-select>
              <span>→</span>
              <el-select v-model="diffTarget" placeholder="目标版本" style="width:140px;">
                <el-option v-for="v in versionsOfName" :key="v.id" :label="`${v.version}`" :value="v.id" />
              </el-select>
              <el-button size="small" type="primary" @click="doDiff">对比</el-button>
            </div>
            <el-skeleton v-if="diffLoading" :rows="3" style="margin-top:12px;" />
            <div v-else-if="diffResult" style="margin-top:12px;">
              <el-tag type="success">+{{ diffResult.summary.added }}</el-tag>
              <el-tag type="danger">-{{ diffResult.summary.removed }}</el-tag>
              <el-tag type="warning">~{{ diffResult.summary.changed }}</el-tag>
              <el-tag>{{ diffResult.summary.unchanged }} 不变</el-tag>
              <el-collapse style="margin-top:10px;">
                <el-collapse-item v-if="diffResult.changed.length" title="变更明细">
                  <div v-for="c in diffResult.changed" :key="c.code" style="font-size:13px;margin-bottom:6px;">
                    <b>{{ c.code }}</b>
                    <div v-for="(d, k) in c.diffs" :key="k" style="color:#909399;">
                      {{ k }}: {{ d.base }} → <span style="color:#f56c6c;">{{ d.target }}</span>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-card>

          <el-card class="premium-card" shadow="never" style="margin-top: 16px;">
            <template #header><b>E7 标准 Benchmark 模板</b></template>
            <el-select v-model="templateKey" placeholder="选择模板" style="width:100%;">
              <el-option v-for="t in BENCHMARK_TEMPLATES" :key="t.key" :label="t.name" :value="t.key" />
            </el-select>
            <div v-if="templateKey" style="font-size:12px;color:#909399;margin:8px 0;">
              {{ selectedTemplate.dims }}<span v-if="selectedTemplate.measures_pass_k"> · 专测 Pass^k</span>
            </div>
            <el-button size="small" type="primary" :loading="tplLoading" :disabled="!templateKey" @click="doCreateFromTemplate">
              从模板新建数据集
            </el-button>
          </el-card>
        </el-col>
      </el-row>

      <!-- 全局榜单 -->
      <el-card class="premium-card" shadow="never" style="margin-top: 16px;">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b>A4 全局榜单（本租户）</b>
            <div style="display:flex;align-items:center;gap:10px;">
              <el-switch v-model="lbSortCost" size="small" active-text="按成本排序" @change="fetchLeaderboard" />
              <el-button size="small" @click="fetchLeaderboard"><el-icon><Refresh /></el-icon> 刷新</el-button>
            </div>
          </div>
        </template>
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="lb-title">模型排名</div>
            <el-table :data="leaderboard.model_ranking" size="small" v-loading="lbLoading">
              <el-table-column prop="model" label="模型" />
              <el-table-column prop="run_count" label="运行数" width="90" />
              <el-table-column prop="avg_mean_score" label="均分" />
              <el-table-column prop="avg_pass_rate" label="通过率" />
              <el-table-column prop="avg_cost_tokens" label="均 token" />
              <el-table-column prop="avg_cost_calls" label="均调用" />
            </el-table>
          </el-col>
          <el-col :span="12">
            <div class="lb-title">数据集排名</div>
            <el-table :data="leaderboard.dataset_ranking" size="small" v-loading="lbLoading">
              <el-table-column prop="dataset_name" label="数据集" />
              <el-table-column prop="run_count" label="运行数" width="90" />
              <el-table-column prop="avg_mean_score" label="均分" />
            </el-table>
          </el-col>
        </el-row>
        <!-- U1/E3：Elo 排名 -->
        <div v-if="leaderboard.elo_ranking && leaderboard.elo_ranking.length" style="margin-top:16px;">
          <div class="lb-title">Elo 排名（跨运行 pairwise 对战，位置交换消偏）</div>
          <el-table :data="leaderboard.elo_ranking" size="small">
            <el-table-column prop="model_name" label="模型" />
            <el-table-column prop="rating" label="Elo" width="100">
              <template #default="{ row }"><b>{{ Math.round(row.rating) }}</b></template>
            </el-table-column>
            <el-table-column prop="wins" label="胜" width="70" />
            <el-table-column prop="losses" label="负" width="70" />
            <el-table-column prop="draws" label="平" width="70" />
          </el-table>
        </div>
      </el-card>
    </div>

    <!-- 运行详情抽屉：B4 基线 / 对比 / B3 分析 / C1 门禁 / C2 导出 -->
    <el-drawer v-model="runDrawer" title="运行详情 · 基线/分析/门禁" size="46%">
      <template v-if="currentRun">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="运行 ID">{{ currentRun.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentRun.status }}</el-descriptions-item>
          <el-descriptions-item label="分数">{{ currentRun.mean_score }}</el-descriptions-item>
          <el-descriptions-item label="通过率">{{ currentRun.pass_rate }}</el-descriptions-item>
          <el-descriptions-item label="边缘通过率">{{ currentRun.edge_pass_rate }}</el-descriptions-item>
          <el-descriptions-item label="能力集通过率(P3-10)">
            <span v-if="currentRun.capability_pass_rate != null">{{ currentRun.capability_pass_rate }}</span>
            <span v-else style="color:#909399;">—</span>
          </el-descriptions-item>
          <el-descriptions-item label="回归集通过率(P3-10)">
            <span v-if="currentRun.regression_pass_rate != null">{{ currentRun.regression_pass_rate }}</span>
            <span v-else style="color:#909399;">—</span>
          </el-descriptions-item>
          <el-descriptions-item label="基线">{{ currentRun.is_baseline ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="重复次数 k">{{ currentRun.repeat_k ?? 1 }}</el-descriptions-item>
          <el-descriptions-item label="Pass^k 可靠性">
            <span v-if="currentRun.pass_k_rate != null">{{ currentRun.pass_k_rate }}</span>
            <span v-else style="color:#909399;">—</span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- P3-2：成本 / 时延卡片 -->
        <el-divider content-position="left">P3-2 成本 / 时延</el-divider>
        <el-row :gutter="12">
          <el-col :span="6">
            <div class="metric">
              <div class="m-val">{{ currentRun.cost_tokens_total ?? '—' }}</div>
              <div class="m-label">Token 总耗</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric">
              <div class="m-val">{{ currentRun.cost_calls_total ?? '—' }}</div>
              <div class="m-label">工具调用数</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric">
              <div class="m-val">{{ currentRun.latency_avg != null ? currentRun.latency_avg.toFixed(2) : '—' }}</div>
              <div class="m-label">平均时延 (s)</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric">
              <div class="m-val">{{ currentRun.latency_max != null ? currentRun.latency_max.toFixed(2) : '—' }}</div>
              <div class="m-label">最长时延 (s)</div>
            </div>
          </el-col>
        </el-row>

        <div style="margin: 16px 0; display:flex; gap:8px; flex-wrap:wrap;">
          <el-button size="small" @click="doSetBaseline">设为基线</el-button>
          <el-button size="small" @click="doCompare">对比基线</el-button>
          <el-button size="small" @click="doAnalyze">B3 分析</el-button>
          <el-button size="small" type="warning" @click="doGate">C1 门禁</el-button>
          <el-button size="small" @click="doExportTrace">C2 导出 Trace</el-button>
          <el-button size="small" type="danger" @click="doOpenTraceReplay">P3-15 失败回放</el-button>
          <el-button size="small" type="primary" plain @click="openImportOtel">P3-8 导入 OTel Trace</el-button>
        </div>

        <!-- P3-8 OTel 回流：把外部 agent 框架导出的 OTLP/JSON trace 回流为内部 EvalTrace -->
        <el-dialog v-model="otelImportVisible" title="P3-8 导入 OTel Trace" width="640px" append-to-body>
          <el-form label-width="90px" size="small">
            <el-form-item label="关联用例">
              <el-select v-model="otelForm.caseId" filterable placeholder="选择本次 trace 对应的用例" style="width:100%;">
                <el-option
                  v-for="c in otelCaseOptions"
                  :key="c.id"
                  :label="`#${c.id} ${c.input_text ? c.input_text.slice(0, 30) : ''}${c.is_edge ? ' [边缘]' : ''}`"
                  :value="c.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="OTel/JSON">
              <el-input
                v-model="otelForm.payload"
                type="textarea"
                :rows="12"
                placeholder='粘贴 OTLP/JSON（标准 {"resourceSpans":[...]}、{"spans":[...]} 或裸 span 列表）'
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button size="small" @click="otelImportVisible = false">取消</el-button>
            <el-button size="small" type="primary" :loading="otelImporting" @click="doImportOtel">导入</el-button>
          </template>
        </el-dialog>

        <el-alert
          v-if="compareResult"
          :title="compareResult.regressed ? '相对基线存在劣化' : '相对基线无劣化'"
          :type="compareResult.regressed ? 'error' : 'success'"
          :closable="false" style="margin-bottom:12px;"
        >
          <template #default>
            <div v-for="(d, k) in compareResult.diffs" :key="k" style="font-size:13px;">
              {{ k }}: {{ d.baseline }} → {{ d.current }}（Δ {{ d.delta }}）
            </div>
          </template>
        </el-alert>

        <el-alert
          v-if="analyzeResult"
          :title="`共 ${analyzeResult.total} 条结果${analyzeResult.patterns.length ? '，发现系统性失败模式' : '，无系统性失败模式'}`"
          :type="analyzeResult.patterns.length ? 'warning' : 'success'"
          :closable="false" style="margin-bottom:12px;"
        >
          <template #default>
            <div v-for="p in analyzeResult.patterns" :key="p.judge" style="font-size:13px;">
              [{{ p.judge }}] 失败率 {{ p.fail_rate }} — {{ p.hint }}
            </div>
          </template>
        </el-alert>

        <!-- U4/E5：长程崩溃模式归因 -->
        <el-alert
          v-if="analyzeResult && analyzeResult.crash_modes && analyzeResult.crash_modes.length"
          :title="`长程崩溃模式（${analyzeResult.crash_modes.length}）`"
          type="warning" :closable="false" style="margin-bottom:12px;"
        >
          <template #default>
            <div v-for="(cm, i) in analyzeResult.crash_modes" :key="i" style="font-size:13px;margin-bottom:4px;">
              <b>{{ cm.mode || cm }}</b>
              <span v-if="cm.count != null">（{{ cm.count }} 次）</span>
              <span v-if="cm.detail"> — {{ cm.detail }}</span>
            </div>
            <div v-if="analyzeResult.crash_details" style="color:#909399;margin-top:4px;">{{ analyzeResult.crash_details }}</div>
          </template>
        </el-alert>

        <!-- U3/E4：报告富化（校准卡 + 模型×场景热力图） -->
        <div v-if="runReportEnrich" style="margin-bottom:12px;">
          <template v-if="runReportEnrich.calibration && runReportEnrich.calibration.length">
            <div class="lb-title" style="margin:8px 0 6px;">校准卡（预测分桶 vs 实际通过率）</div>
            <el-table :data="runReportEnrich.calibration" size="small">
              <el-table-column prop="bucket" label="分桶" width="100" />
              <el-table-column prop="count" label="样本数" width="90" />
              <el-table-column prop="actual_pass" label="实际通过率" />
            </el-table>
          </template>
          <template v-if="runReportEnrich.heatmap && runReportEnrich.heatmap.length">
            <div class="lb-title" style="margin:12px 0 6px;">模型 × 场景 热力图（均分）</div>
            <el-table :data="runReportEnrich.heatmap" size="small">
              <el-table-column prop="model" label="模型" />
              <el-table-column prop="edge" label="边缘场景均分" />
              <el-table-column prop="normal" label="常规场景均分" />
            </el-table>
          </template>
        </div>

        <div v-if="gateResult" style="margin-bottom:12px;">
          <el-alert
            :title="gateResult.passed ? '门禁通过 ✅' : '门禁未通过 ❌'"
            :type="gateResult.passed ? 'success' : 'error'" :closable="false"
          >
            <template #default>
              <div v-if="gateResult.failed_thresholds.length" style="font-size:13px;">
                阈值未达：
                <span v-for="f in gateResult.failed_thresholds" :key="f.metric">
                  {{ f.metric }}（{{ f.value }} < {{ f.threshold }}） </span>
              </div>
              <div v-if="gateResult.regressed_metrics.length" style="font-size:13px;">
                回归掉点：
                <span v-for="r in gateResult.regressed_metrics" :key="r.metric">
                  {{ r.metric }}（Δ {{ r.delta }}） </span>
              </div>
              <!-- P3-1：死循环/幻觉红线零容忍硬门可视化 -->
              <div v-if="gateResult.red_line_cases && gateResult.red_line_cases.length" style="font-size:13px;color:#f56c6c;margin-top:4px;">
                红线零容忍（死循环/幻觉）：
                <template v-for="r in gateResult.red_line_cases" :key="r.case_id">
                  <el-tag v-for="f in r.red_flags" :key="f" size="small" type="danger" effect="dark" style="margin:0 4px 4px 0;">{{ f }}</el-tag>
                  <span style="margin-right:10px;">用例#{{ r.case_id }}</span>
                </template>
              </div>
              <!-- P3-3：Agent-as-Judge 置信度门可视化 -->
              <div v-if="gateResult.low_confidence && gateResult.low_confidence.length" style="font-size:13px;color:#e6a23c;margin-top:4px;">
                低置信复核（置信度 &lt; 阈值）：
                <span v-for="r in gateResult.low_confidence" :key="r.case_id" style="margin-right:10px;">
                  用例#{{ r.case_id }}（{{ r.confidence }}）
                </span>
              </div>
              <!-- P3-7：辅助指标仅告警（不阻断合并） -->
              <div v-if="gateResult.aux_warnings && gateResult.aux_warnings.length" style="font-size:13px;color:#909399;margin-top:4px;">
                辅助指标告警（不阻断）：
                <span v-for="w in gateResult.aux_warnings" :key="w.metric" style="margin-right:10px;">
                  {{ w.metric }}（{{ w.value }} < {{ w.threshold }}）
                </span>
              </div>
              <div v-if="gateResult.aux_regressed && gateResult.aux_regressed.length" style="font-size:13px;color:#909399;margin-top:4px;">
                辅助指标回归（不阻断）：
                <span v-for="r in gateResult.aux_regressed" :key="r.metric" style="margin-right:10px;">
                  {{ r.metric }}（Δ {{ r.delta }}）
                </span>
              </div>
            </template>
          </el-alert>
          <div style="margin-top:10px;">
            <span style="font-size:13px;">门禁阈值（JSON）：</span>
            <el-input v-model="gateThresholds" type="textarea" :rows="2" style="margin-top:6px;"
              placeholder='{"mean_score": 0.7, "pass_rate": 0.8}' />
            <el-input v-model="gateRegressDelta" style="margin-top:6px;width:160px;" placeholder="回归阈值 0.05" />
            <div style="margin-top:8px;font-size:13px;color:#909399;">辅助指标（仅告警，不阻断合并）：</div>
            <el-input v-model="gateAuxThresholds" type="textarea" :rows="2" style="margin-top:6px;"
              placeholder='{"latency_avg": 1.0, "cost_tokens_total": 500}' />
            <el-input v-model="gateAuxMetrics" style="margin-top:6px;" placeholder="基线回归监控指标（逗号分隔）：latency_avg,cost_tokens_total" />
            <el-button size="small" type="warning" style="margin-top:6px;" @click="doGate">重新校验</el-button>
          </div>
        </div>

        <!-- P3-6 E2E Harness：Mock / Real 端到端驱动被测 agent 并评测 -->
        <el-divider content-position="left">P3-6 E2E Harness（Mock / Real 端到端）</el-divider>
        <div class="harness-card" style="border:1px solid #ebeef5;border-radius:8px;padding:12px;margin-bottom:12px;">
          <el-radio-group v-model="harnessMode" size="small" style="margin-bottom:8px;">
            <el-radio-button label="mock">Mock（确定性零外送）</el-radio-button>
            <el-radio-button label="real">Real（真实 agent）</el-radio-button>
          </el-radio-group>

          <template v-if="harnessMode === 'mock'">
            <div style="font-size:13px;color:#606266;margin-bottom:6px;">Mock 模式：</div>
            <el-radio-group v-model="harnessMockMode" size="small" style="margin-bottom:8px;">
              <el-radio-button label="expected">expected（全通过）</el-radio-button>
              <el-radio-button label="echo">echo（回显）</el-radio-button>
              <el-radio-button label="fail">fail（全失败）</el-radio-button>
            </el-radio-group>
          </template>

          <template v-else>
            <div style="font-size:13px;color:#606266;margin-bottom:6px;">
              真实 agent 配置（留空则用本租户激活的 AIModelConfig）：
            </div>
            <el-input v-model="harnessAgentConfigId" style="margin-bottom:8px;"
              placeholder="agent_config_id（可选，整数）" />
          </template>

          <el-button size="small" type="primary" :loading="harnessLoading"
            @click="doRunHarness">运行 Harness 评测</el-button>

          <div v-if="harnessResult" style="margin-top:10px;">
            <el-alert
              :title="harnessResult.status === 'DONE' ? 'Harness 评测完成 ✅' : 'Harness 评测失败 ❌'"
              :type="harnessResult.status === 'DONE' ? 'success' : 'error'" :closable="false"
            >
              <template #default>
                <div style="font-size:13px;">
                  pass_rate：<b>{{ harnessResult.pass_rate != null ? harnessResult.pass_rate : '—' }}</b>；
                  mean_score：<b>{{ harnessResult.mean_score != null ? harnessResult.mean_score : '—' }}</b>；
                  基线：<b>{{ harnessResult.is_baseline ? '是' : '否' }}</b>
                </div>
                <div style="font-size:12px;color:#909399;margin-top:4px;">
                  Trace 已落盘（每条用例 PLAN→TOOL→OBSERVE→OUTPUT），可在「Trace 回放」查看归因。
                </div>
              </template>
            </el-alert>
          </div>
        </div>

        <!-- P3-17 分层报告（本运行 L0/L1/L2） -->
        <el-divider content-position="left">P3-17 分层报告（本运行）</el-divider>
        <template v-if="runLayered && runLayered.L0">
          <el-row :gutter="12">
            <el-col :span="6"><div class="metric"><div class="m-val">{{ runLayered.L0.total }}</div><div class="m-label">用例数</div></div></el-col>
            <el-col :span="6"><div class="metric"><div class="m-val" :style="{color: runLayered.L0.failed ? '#f56c6c' : '#67c23a'}">{{ runLayered.L0.failed }}</div><div class="m-label">失败</div></div></el-col>
            <el-col :span="6"><div class="metric"><div class="m-val">{{ runLayered.L0.mean_score != null ? runLayered.L0.mean_score : '—' }}</div><div class="m-label">均分</div></div></el-col>
            <el-col :span="6"><div class="metric"><div class="m-val" :style="{color: runLayered.L0.red_line_hits ? '#e6a23c' : '#67c23a'}">{{ runLayered.L0.red_line_hits }}</div><div class="m-label">红线命中</div></div></el-col>
          </el-row>
          <el-row :gutter="12" style="margin-top:10px;">
            <el-col :span="8">
              <div class="lb-sub">按角色</div>
              <el-table :data="runRoleRows" size="small">
                <el-table-column prop="key" label="角色" />
                <el-table-column prop="count" label="数" width="42" />
                <el-table-column prop="passed" label="通过" width="42" />
                <el-table-column prop="failed" label="失败" width="42" />
                <el-table-column prop="pass_rate" label="通过率" />
              </el-table>
            </el-col>
            <el-col :span="8">
              <div class="lb-sub">按边缘</div>
              <el-table :data="runEdgeRows" size="small">
                <el-table-column prop="key" label="类型" />
                <el-table-column prop="count" label="数" width="42" />
                <el-table-column prop="passed" label="通过" width="42" />
                <el-table-column prop="failed" label="失败" width="42" />
                <el-table-column prop="pass_rate" label="通过率" />
              </el-table>
            </el-col>
            <el-col :span="8">
              <div class="lb-sub">按评分器</div>
              <el-table :data="runJudgeRows" size="small">
                <el-table-column prop="key" label="评分器" />
                <el-table-column prop="count" label="数" width="42" />
                <el-table-column prop="passed" label="通过" width="42" />
                <el-table-column prop="failed" label="失败" width="42" />
                <el-table-column prop="pass_rate" label="通过率" />
              </el-table>
            </el-col>
          </el-row>
          <div class="lb-sub" style="margin-top:14px;">
            L2 · 失败用例 TopN（按分数升序）· 共 {{ runLayered.L2.failed_count }} 条
          </div>
          <el-table :data="runLayered.L2.failed" size="small" max-height="300" style="margin-top:6px;">
            <el-table-column prop="case_id" label="用例" width="52" />
            <el-table-column prop="code" label="code" width="80" />
            <el-table-column prop="score" label="分数" width="58" />
            <el-table-column prop="judge" label="裁判" width="76" />
            <el-table-column prop="input_text" label="输入" show-overflow-tooltip />
            <el-table-column label="红线" width="120">
              <template #default="{ row }">
                <el-tag v-for="f in (row.red_flags || [])" :key="f" type="danger" size="small" style="margin-right:3px;">{{ f }}</el-tag>
                <span v-if="!row.red_flags || !row.red_flags.length" style="color:#909399;">—</span>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-else description="本运行暂无结果，无法生成分层报告" :image-size="70" />

        <el-dialog v-model="traceDialog" title="C2 Trace 导出（Langfuse/OTel 风格）" width="70%" append-to-body>
          <pre style="max-height:420px;overflow:auto;background:#f5f7fa;padding:12px;border-radius:6px;">{{ traceJson }}</pre>
          <el-button size="small" @click="downloadTrace">下载 JSON</el-button>
        </el-dialog>

        <!-- P3-15 失败 case Trace 回放（对标 UI 视频回放） -->
        <el-dialog v-model="traceReplayDialog" title="P3-15 失败 case Trace 回放" width="82%" append-to-body @close="stopPlay">
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="lb-title" style="margin-bottom:8px;">用例 Trace 可用性（失败优先）</div>
              <el-table
                :data="caseTraces" size="small" v-loading="caseTracesLoading"
                highlight-current-row style="cursor:pointer;" @row-click="onPickCase"
              >
                <el-table-column label="用例" width="62">
                  <template #default="{ row }">#{{ row.case_id }}</template>
                </el-table-column>
                <el-table-column label="结果" width="64">
                  <template #default="{ row }">
                    <el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '失败' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Trace" width="66">
                  <template #default="{ row }">
                    <el-tag v-if="row.has_trace" type="warning" size="small">可回放</el-tag>
                    <span v-else style="color:#c0c4cc;font-size:12px;">无</span>
                  </template>
                </el-table-column>
              </el-table>
              <div v-if="caseTraces.length" style="font-size:12px;color:#909399;margin-top:8px;">
                共 {{ caseTraces.length }} 用例 · 失败 {{ caseTracesFailed }} · 可回放 {{ caseTracesPlayable }}
              </div>
            </el-col>
            <el-col :span="16">
              <div v-if="replayTrace" style="border:1px solid #e2e8f0;border-radius:8px;padding:12px;background:#fafcff;">
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
                  <el-button size="small" :type="playing ? '' : 'primary'" @click="togglePlay">
                    <el-icon>{{ playing ? VideoPause : VideoPlay }}</el-icon>{{ playing ? '暂停' : '播放' }}
                  </el-button>
                  <el-button size="small" @click="replayReset">重置</el-button>
                  <el-tag size="small" :type="replayTrace.status === 'ERROR' ? 'danger' : 'info'">{{ replayTrace.status }}</el-tag>
                  <span style="font-size:12px;color:#909399;">总时延 {{ replayTrace.total_latency_ms }} ms · {{ replayTrace.step_count }} 步</span>
                </div>
                <el-progress :percentage="replayProgress" :show-text="false" style="margin-bottom:12px;" />
                <div style="max-height:430px;overflow:auto;">
                  <div
                    v-for="(s, i) in replayTrace.steps" :key="s.step_index"
                    :class="['trace-step', { 'step-active': i <= playIndex, 'step-error': s.is_error, 'step-failpoint': s.is_failure_point }]"
                  >
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                      <span class="step-idx">{{ i + 1 }}</span>
                      <el-tag size="small" :type="typeTag(s.step_type)">{{ s.type_label }}</el-tag>
                      <b>{{ s.name }}</b>
                      <span style="font-size:12px;color:#909399;">累计 +{{ s.cumulative_ms }} ms</span>
                      <el-tag v-if="s.is_failure_point" type="danger" size="small" effect="dark">失败点</el-tag>
                    </div>
                    <div v-if="s.input_data" class="step-io">输入：{{ json(s.input_data) }}</div>
                    <div v-if="s.output_data" class="step-io">输出：{{ json(s.output_data) }}</div>
                    <div v-if="s.error" class="step-err">错误：{{ s.error }}</div>
                  </div>
                </div>
              </div>
              <el-empty v-else description="选择左侧带 Trace 的失败用例开始回放" :image-size="80" />
            </el-col>
          </el-row>
        </el-dialog>

        <!-- 执行评测对话框 -->
        <el-dialog v-model="runDialog" title="执行评测（提交各用例输出）" width="60%" append-to-body>
          <p style="font-size:13px;color:#909399;">
            请输入 outputs 映射 JSON：<code>{"&lt;case_id&gt;": "&lt;模型输出&gt;", ...}</code>
          </p>
          <el-input v-model="runOutputs" type="textarea" :rows="8" placeholder='{"1": "模型输出1", "2": "模型输出2"}' />
          <div style="margin-top:8px;">
            <span style="font-size:13px;margin-right:8px;">置信度门阈值</span>
            <el-input v-model="runMinConfidence" style="width:160px;" placeholder="留空=关闭" />
            <span style="font-size:12px;color:#909399;margin-left:8px;">低于此值的用例将标记需人工复核</span>
          </div>
          <template #footer>
            <el-button @click="runDialog = false">取消</el-button>
            <el-button type="primary" :loading="runLoading" @click="submitRun">执行</el-button>
          </template>
        </el-dialog>
      </template>
    </el-drawer>
  </BasePage>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, VideoPlay, VideoPause, MagicStick, Search, Timer, Plus, Files, Upload, Warning } from '@element-plus/icons-vue'
import {
  listDatasets, getDatasetReport, cloneDatasetVersion, diffDatasets,
  generateCases, getLeaderboard, listRuns, runEval, setBaseline,
  compareRun, analyzeRun, gateRun, exportTrace,
  getRunElo, getRunReport, createFromTemplate,
  designPlan, confirmPlan,
  listKnowledge, createKnowledge, deleteKnowledge, searchKnowledge,
  getRunCaseTraces, getTraceReplay,
  listGraders, listSchedules, createSchedule, updateSchedule,
  deleteSchedule, fireSchedule, testScheduleNotify, listAgentModels,
  listSkillVersions, publishSkillVersion, setActiveSkillVersion,
  diffSkillVersion, currentSkillVersion,
  getColdStartStatus, applyColdStart,
  listEdgeRules, seedEdgeRules, applyEdgeRules,
  listCases, ingestOtelTrace,
  listJudgeStrengths, assessJudgeStrength,
  getRunLayeredReport, getDatasetLayeredReport,
  runHarness,
} from '@/api/eval'

// E7：平台级标准 Benchmark 模板（与后端 benchmarks.CATALOG 对齐）
const BENCHMARK_TEMPLATES = [
  { key: 'swe-bench', name: 'SWE-bench（代码修复）', dims: '完成率/补丁正确性/测试通过率' },
  { key: 'gaia', name: 'GAIA（通用 AI 助手）', dims: '完成率/工具准确率/推理正确性' },
  { key: 'webarena', name: 'WebArena（网页智能体）', dims: '完成率/操作正确性/状态一致性' },
  { key: 'tau-bench', name: 'τ-bench（可靠性）', dims: 'Pass^k 可靠性/工具准确率/策略遵循', measures_pass_k: true },
  { key: 'agentbench', name: 'AgentBench（多环境智能体）', dims: '完成率/环境适配/规划质量' },
  { key: 'osworld', name: 'OSWorld（桌面 GUI 智能体）', dims: '完成率/GUI 操作/长程规划' },
]

// ---- 数据集 ----
const datasets = ref([])
const loadingDatasets = ref(false)
const selectedDatasetId = ref(null)
const selectedDataset = ref(null)
const report = ref({ grader_breakdown: [], runs: [] })
const reportLoading = ref(false)

const fetchDatasets = async () => {
  loadingDatasets.value = true
  try {
    const res = await listDatasets()
    datasets.value = (res.data.results || res.data || []).filter(d => d.name === (selectedDataset.value?.name) || true)
  } catch (e) {
    ElMessage.error('加载数据集失败')
  } finally {
    loadingDatasets.value = false
  }
}

const onDatasetChange = async (id) => {
  selectedDataset.value = datasets.value.find(d => d.id === id) || null
  await Promise.all([fetchReport(), fetchRuns(), fetchLayeredReport()])
}

const fetchReport = async () => {
  if (!selectedDatasetId.value) return
  reportLoading.value = true
  try {
    const res = await getDatasetReport(selectedDatasetId.value)
    report.value = res.data
  } catch (e) {
    ElMessage.error('加载报告失败')
  } finally {
    reportLoading.value = false
  }
}

// P3-17：分层报告产物（数据集最近一次 DONE 运行）
const layered = ref(null)
const layeredLoading = ref(false)
const fetchLayeredReport = async () => {
  if (!selectedDatasetId.value) return
  layeredLoading.value = true
  try {
    const res = await getDatasetLayeredReport(selectedDatasetId.value)
    layered.value = res.data
  } catch (e) {
    layered.value = null
  } finally {
    layeredLoading.value = false
  }
}

// ---- 运行 ----
const runs = ref([])
const runsLoading = ref(false)
const datasetRuns = computed(() =>
  runs.value.filter(r => r.dataset === selectedDatasetId.value)
)
const fetchRuns = async () => {
  runsLoading.value = true
  try {
    const res = await listRuns()
    runs.value = res.data.results || res.data || []
  } catch (e) {
    ElMessage.error('加载运行失败')
  } finally {
    runsLoading.value = false
  }
}

// ---- P3-2：实时刷新（轻量 5s 轮询，静默更新不触发 loading 闪烁）----
const realtime = ref(true)
let pollTimer = null

const pollRuns = async () => {
  try {
    const res = await listRuns()
    const data = res.data.results || res.data || []
    runs.value = data
    // 抽屉打开时同步刷新当前运行细节
    if (runDrawer.value && currentRun.value?.id != null) {
      const updated = data.find(r => r.id === currentRun.value.id)
      if (updated) currentRun.value = updated
    }
  } catch (e) { /* 轮询失败静默 */ }
}
const pollReport = async () => {
  if (!selectedDatasetId.value) return
  try {
    const res = await getDatasetReport(selectedDatasetId.value)
    report.value = res.data
  } catch (e) { /* 轮询失败静默 */ }
}
const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!selectedDatasetId.value) return
    if (runDrawer.value) {
      await pollRuns()
    } else {
      await Promise.all([pollRuns(), pollReport()])
    }
  }, 5000)
}
const stopPolling = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}
const onRealtimeChange = (val) => {
  if (val) startPolling()
  else stopPolling()
}

// ---- 榜单 ----
const leaderboard = ref({ model_ranking: [], dataset_ranking: [] })
const lbLoading = ref(false)
const lbSortCost = ref(false)  // P3-2：按成本升序排序开关

// P3-2：成本 / 时延概览（取最近一次运行的聚合值）
const latestCost = computed(() => {
  const r = report.value && report.value.latest
  if (!r) return null
  if (r.cost_tokens_total == null && r.latency_avg == null) return null
    return {
        tokens: r.cost_tokens_total != null ? Math.round(r.cost_tokens_total) : '—',
        calls: r.cost_calls_total != null ? r.cost_calls_total : '—',
        latAvg: r.latency_avg != null ? r.latency_avg.toFixed(2) : '—',
        latMax: r.latency_max != null ? r.latency_max.toFixed(2) : '—',
    }
})

// P3-7：饱和指数标题
const saturationTitle = computed(() => {
    const s = report.value && report.value.saturation
    if (!s) return ''
    return s.saturated ? '评测集已饱和（区分度低）' : '评测集区分度正常'
})
// P3-10：能力/回归集分离 —— 最近运行按角色拆分通过率
const roleSplit = computed(() => {
    const r = report.value && report.value.latest
    if (!r) return null
    return {
        capability_pass_rate: r.capability_pass_rate,
        regression_pass_rate: r.regression_pass_rate,
    }
})

// P3-17：把 L1 的 {key:{count,passed,failed,pass_rate}} 字典转为表格行数组
const toRows = (obj) => {
    if (!obj) return []
    return Object.keys(obj).map(k => ({ key: k, ...obj[k] }))
}
// 数据集级（最近一次 DONE 运行）分层行
const layerRoleRows = computed(() => toRows(layered.value?.L1?.by_role))
const layerEdgeRows = computed(() => toRows(layered.value?.L1?.by_edge))
const layerJudgeRows = computed(() => toRows(layered.value?.L1?.by_judge))
// 运行抽屉级分层行
const runRoleRows = computed(() => toRows(runLayered.value?.L1?.by_role))
const runEdgeRows = computed(() => toRows(runLayered.value?.L1?.by_edge))
const runJudgeRows = computed(() => toRows(runLayered.value?.L1?.by_judge))
const fetchLeaderboard = async () => {
  lbLoading.value = true
  try {
    const params = { with_elo: 1 }
    if (lbSortCost.value) params.sort = 'cost'
    const res = await getLeaderboard(params)
    leaderboard.value = res.data
  } catch (e) {
    ElMessage.error('加载榜单失败')
  } finally {
    lbLoading.value = false
  }
}

// ---- B1 生成 ----
const reqText = ref('')
const genMode = ref('offline')
const genLoading = ref(false)
const genResult = ref(null)
const doGenerate = async () => {
  if (!selectedDatasetId.value) return ElMessage.warning('请先选择数据集')
  if (!reqText.value.trim()) return ElMessage.warning('请输入需求文本')
  genLoading.value = true
  genResult.value = null
  try {
    const payload = { req_text: reqText.value, mode: genMode.value }
    if (genKnowledgeIds.value.length) payload.knowledge_ids = genKnowledgeIds.value
    const res = await generateCases(selectedDatasetId.value, payload)
    genResult.value = res.data
    ElMessage.success(`生成 ${res.data.generated_count} 条用例（RAG 接入 ${genKnowledgeIds.value.length} 份）`)
    await fetchDatasets()
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    genLoading.value = false
  }
}

// ---- P3-13 知识中枢 RAG ----
const kbTitle = ref('')
const kbSource = ref('REQUIREMENT')
const kbContent = ref('')
const kbIngesting = ref(false)
const knowledgeDocs = ref([])
const kbQuery = ref('')
const kbSearching = ref(false)
const kbHits = ref([])
const genKnowledgeIds = ref([])

const fetchKnowledge = async () => {
  try {
    const res = await listKnowledge()
    knowledgeDocs.value = res.data || []
  } catch (e) {
    // 静默失败，知识库为可选增强
  }
}
const doIngest = async () => {
  if (!kbTitle.value.trim()) return ElMessage.warning('请填写知识文档标题')
  if (!kbContent.value.trim()) return ElMessage.warning('请粘贴知识文档正文')
  kbIngesting.value = true
  try {
    await createKnowledge({
      title: kbTitle.value.trim(),
      source_type: kbSource.value,
      content: kbContent.value.trim(),
    })
    ElMessage.success('已入库并自动分块')
    kbTitle.value = ''
    kbContent.value = ''
    kbHits.value = []
    await fetchKnowledge()
  } catch (e) {
    ElMessage.error('入库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    kbIngesting.value = false
  }
}
const doDeleteKb = async (id) => {
  try {
    await deleteKnowledge(id)
    knowledgeDocs.value = knowledgeDocs.value.filter((d) => d.id !== id)
    genKnowledgeIds.value = genKnowledgeIds.value.filter((x) => x !== id)
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}
const doSearchKb = async () => {
  if (!kbQuery.value.trim()) return ElMessage.warning('请输入检索词')
  kbSearching.value = true
  try {
    const res = await searchKnowledge({ query: kbQuery.value.trim(), top_k: 4 })
    kbHits.value = res.data.hits || []
  } catch (e) {
    ElMessage.error('检索失败：' + (e.response?.data?.detail || e.message))
  } finally {
    kbSearching.value = false
  }
}

// ---- P3-16 定时评测（平台内部调度模型）+ IM 通知 ----
const schedules = ref([])
const schedLoading = ref(false)
const showSchedDialog = ref(false)
const schedSaving = ref(false)
const graders = ref([])
const agentModels = ref([])
const schedForm = reactive({
  name: '', dataset: null, grader: null, agent_config: null,
  trigger_type: 'interval', interval_minutes: 60, daily_at: '09:00', cron: '*/5 * * * *',
  enabled: true, notify_channels: [],
})

const fetchSchedules = async () => {
  schedLoading.value = true
  try {
    const res = await listSchedules()
    const data = res.data
    schedules.value = (data && data.results) ? data.results : (data || [])
  } catch (e) {
    // 定时调度为增强能力，失败静默
  } finally {
    schedLoading.value = false
  }
}
const fetchGraders = async () => {
  if (graders.value.length) return
  try {
    const res = await listGraders()
    const data = res.data
    graders.value = (data && data.results) ? data.results : (data || [])
  } catch (e) { /* noop */ }
}
const fetchAgentModels = async () => {
  if (agentModels.value.length) return
  try {
    const res = await listAgentModels()
    const data = res.data
    agentModels.value = (data && data.results) ? data.results : (data || [])
  } catch (e) { /* noop */ }
}
const openSchedDialog = () => {
  resetSchedForm()
  fetchGraders()
  fetchAgentModels()
  showSchedDialog.value = true
}
const resetSchedForm = () => {
  Object.assign(schedForm, {
    name: '', dataset: null, grader: null, agent_config: null,
    trigger_type: 'interval', interval_minutes: 60, daily_at: '09:00', cron: '*/5 * * * *',
    enabled: true, notify_channels: [],
  })
}
const triggerLabel = (row) => {
  if (row.trigger_type === 'interval') return `间隔 ${row.interval_minutes || 60} 分钟`
  if (row.trigger_type === 'daily') return `每日 ${row.daily_at || '--:--'}`
  if (row.trigger_type === 'cron') return `Cron ${row.cron || ''}`
  return row.trigger_type
}
const statusType = (s) => {
  if (s === 'OK') return 'success'
  if (s === 'ERROR') return 'danger'
  return 'info'
}
const fmtTime = (t) => {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 16)
}
const saveSchedule = async () => {
  if (!schedForm.name.trim()) return ElMessage.warning('请填写调度名称')
  if (!schedForm.dataset) return ElMessage.warning('请选择数据集')
  if (!schedForm.grader) return ElMessage.warning('请选择评分器')
  schedSaving.value = true
  const payload = {
    name: schedForm.name.trim(),
    dataset: schedForm.dataset,
    grader: schedForm.grader,
    trigger_type: schedForm.trigger_type,
    enabled: schedForm.enabled,
    notify_channels: schedForm.notify_channels
      .filter((c) => c.webhook && c.webhook.trim())
      .map((c) => ({ type: c.type, webhook: c.webhook.trim(), secret: (c.secret || '').trim() })),
  }
  if (schedForm.agent_config) payload.agent_config = schedForm.agent_config
  if (schedForm.trigger_type === 'interval') payload.interval_minutes = schedForm.interval_minutes
  if (schedForm.trigger_type === 'daily') payload.daily_at = schedForm.daily_at
  if (schedForm.trigger_type === 'cron') payload.cron = schedForm.cron
  try {
    await createSchedule(payload)
    ElMessage.success('调度已创建，平台内部守护将按触发条件自动执行')
    showSchedDialog.value = false
    await fetchSchedules()
  } catch (e) {
    ElMessage.error('创建失败：' + (e.response?.data?.detail || JSON.stringify(e.response?.data) || e.message))
  } finally {
    schedSaving.value = false
  }
}
const toggleSched = async (row, val) => {
  try {
    await updateSchedule(row.id, { enabled: val })
  } catch (e) {
    ElMessage.error('状态更新失败')
    row.enabled = !val
  }
}
const fireSched = async (row) => {
  try {
    const res = await fireSchedule(row.id)
    ElMessage.success(`已立即执行，运行 #${res.data.run_id} · 分数 ${res.data.mean_score}`)
    await fetchSchedules()
  } catch (e) {
    ElMessage.error('执行失败：' + (e.response?.data?.detail || e.message))
  }
}
const deleteSched = async (row) => {
  try {
    await deleteSchedule(row.id)
    ElMessage.success('已删除调度')
    await fetchSchedules()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

// 测试 IM 通知
const showNotifyDialog = ref(false)
const notifyTesting = ref(false)
const notifyTestResult = ref(null)
const testChannels = ref([
  { type: 'feishu', webhook: '', secret: '' },
  { type: 'wecom', webhook: '', secret: '' },
  { type: 'dingtalk', webhook: '', secret: '' },
])
const openNotifyDialog = () => {
  notifyTestResult.value = null
  showNotifyDialog.value = true
}
const sendTestNotify = async () => {
  const channels = testChannels.value
    .filter((c) => c.webhook && c.webhook.trim())
    .map((c) => ({ type: c.type, webhook: c.webhook.trim(), secret: (c.secret || '').trim() }))
  if (!channels.length) return ElMessage.warning('请至少填写一个渠道的 Webhook')
  notifyTesting.value = true
  notifyTestResult.value = null
  try {
    const res = await testScheduleNotify({ channels })
    notifyTestResult.value = { ok: (res.data.results || []).every((r) => r.ok), results: res.data.results || [] }
  } catch (e) {
    notifyTestResult.value = { ok: false, results: [{ type: 'error', ok: false, detail: e.message }] }
  } finally {
    notifyTesting.value = false
  }
}

// ---- P3-4 评测技能版本化 ----
const versions = ref([])
const versionsLoading = ref(false)
const publishing = ref(false)
const fetchSkillVersions = async () => {
  versionsLoading.value = true
  try {
    const res = await listSkillVersions({ skill_key: 'eval-flow' })
    versions.value = res.data.results || []
  } catch (e) {
    ElMessage.error('加载技能版本失败：' + (e.response?.data?.detail || e.message))
  } finally {
    versionsLoading.value = false
  }
}
const publishDiskVersion = async () => {
  publishing.value = true
  try {
    const res = await publishSkillVersion({ skill_key: 'eval-flow', note: '从磁盘 SKILL.md 快照发布' })
    ElMessage.success(`已发布版本 ${res.data.version}`)
    await fetchSkillVersions()
  } catch (e) {
    const d = e.response?.data || {}
    if (e.response?.status === 409 && d.exists_version) {
      ElMessage.warning(`内容已存在于版本 ${d.exists_version}，无需重复发布`)
    } else {
      ElMessage.error('发布失败：' + (d.detail || e.message))
    }
  } finally {
    publishing.value = false
  }
}
const setActive = async (row) => {
  row._activating = true
  try {
    await setActiveSkillVersion(row.id)
    ElMessage.success(`版本 ${row.version} 已设为生效`)
    await fetchSkillVersions()
  } catch (e) {
    ElMessage.error('设置失败：' + (e.response?.data?.detail || e.message))
  } finally {
    row._activating = false
  }
}
const svShowDiffDialog = ref(false)
const svDiffText = ref('')
const svDiffTarget = ref(null)
const openDiff = async (row) => {
  svDiffTarget.value = null
  svDiffText.value = ''
  try {
    const res = await diffSkillVersion(row.id, 'disk')
    svDiffTarget.value = { from: res.data.from, to: res.data.to }
    svDiffText.value = res.data.diff || ''
    svShowDiffDialog.value = true
  } catch (e) {
    ElMessage.error('差异获取失败：' + (e.response?.data?.detail || e.message))
  }
}

// ---- P3-5 冷启动标准 ----
const coldStart = ref({
  is_cold_start: false, template_count: 0, has_baseline: false,
  default_gate: { thresholds: {}, aux_thresholds: {}, regress_delta: 0.05 },
})
const applyingCold = ref(false)
const fetchColdStart = async () => {
  try {
    const res = await getColdStartStatus()
    coldStart.value = res.data
  } catch (e) {
    // 冷启动状态为非关键辅助信息，失败不打断主流程
  }
}
const applyColdStartDefaults = async () => {
  applyingCold.value = true
  try {
    const res = await applyColdStart()
    const created = (res.data.created || []).length
    const skipped = (res.data.skipped || []).length
    ElMessage.success(`冷启动初始化完成：新建 ${created} 套评分器，跳过 ${skipped} 套已存在`)
    await fetchColdStart()
    await fetchGradersSafe()
  } catch (e) {
    ElMessage.error('冷启动应用失败：' + (e.response?.data?.detail || e.message))
  } finally {
    applyingCold.value = false
  }
}

// —— P3-9 边缘用例规则 ——
const edgeRules = ref([])
const seedingEdge = ref(false)
const edgeApplyVisible = ref(false)
const applyingEdge = ref(false)
const datasetOptions = ref([])
const edgeApplyForm = ref({ dataset_id: null, rule_ids: [] })

const fetchEdgeRules = async () => {
  try {
    const res = await listEdgeRules()
    const payload = res.data
    edgeRules.value = Array.isArray(payload) ? payload : (payload.results || [])
  } catch (e) {
    edgeRules.value = []
  }
}

// —— P3-11 评判模型强度自校准 ——
const judgeStrengths = ref([])
const judgeLoading = ref(false)
const assessingJudge = ref(false)

const fetchJudgeStrengths = async () => {
  judgeLoading.value = true
  try {
    const res = await listJudgeStrengths()
    const payload = res.data
    judgeStrengths.value = Array.isArray(payload) ? payload : (payload.results || [])
  } catch (e) {
    judgeStrengths.value = []
  } finally {
    judgeLoading.value = false
  }
}

const doAssessJudge = async () => {
  assessingJudge.value = true
  try {
    const res = await assessJudgeStrength()
    const rec = (res.data && (res.data.data || res.data)) || {}
    ElMessage.success(`裁判强度评估完成，强度分=${rec.strength_score ?? '—'}（一致 ${rec.agreement ?? '-'}/${rec.sample_size ?? '-'}）`)
    await fetchJudgeStrengths()
  } catch (e) {
    ElMessage.error('评估裁判强度失败：' + (e.response?.data?.detail || e.message))
  } finally {
    assessingJudge.value = false
  }
}

const seedDefaultEdgeRules = async () => {
  seedingEdge.value = true
  try {
    await seedEdgeRules()
    ElMessage.success('已应用平台默认边缘用例规则')
    await fetchEdgeRules()
  } catch (e) {
    ElMessage.error('应用默认规则失败：' + (e.response?.data?.detail || e.message))
  } finally {
    seedingEdge.value = false
  }
}

const openEdgeApply = async () => {
  edgeApplyVisible.value = true
  edgeApplyForm.value = { dataset_id: null, rule_ids: [] }
  if (!edgeRules.value.length) await fetchEdgeRules()
  if (!datasetOptions.value.length) {
    try {
      const res = await listDatasets({ page_size: 200 })
      const payload = res.data
      datasetOptions.value = Array.isArray(payload) ? payload : (payload.results || [])
    } catch (e) {
      datasetOptions.value = []
    }
  }
}

const doApplyEdgeRules = async () => {
  if (!edgeApplyForm.value.dataset_id) {
    ElMessage.warning('请选择目标数据集')
    return
  }
  applyingEdge.value = true
  try {
    const res = await applyEdgeRules({
      dataset_id: edgeApplyForm.value.dataset_id,
      rule_ids: edgeApplyForm.value.rule_ids.length ? edgeApplyForm.value.rule_ids : undefined,
    })
    const d = res.data || {}
    ElMessage.success(`生成完成：新建 ${d.created || 0} 个边缘用例，跳过 ${d.skipped || 0} 个已存在`)
    edgeApplyVisible.value = false
  } catch (e) {
    ElMessage.error('生成边缘用例失败：' + (e.response?.data?.detail || e.message))
  } finally {
    applyingEdge.value = false
  }
}
// 评测舱通用：安全刷新评分器列表（避免某些入口未定义 fetchGraders 时崩溃）
const fetchGradersSafe = async () => {
  if (typeof fetchGraders === 'function') {
    try { await fetchGraders() } catch (e) { /* noop */ }
  }
}

// ---- P3-14 Copilot 评测方案设计器 ----
const planReqText = ref('')
const planMode = ref('offline')
const planLoading = ref(false)
const planResult = ref(null)
const planConfirming = ref(false)
const planRunIds = ref([])
const doDesignPlan = async () => {
  if (!planReqText.value.trim()) return ElMessage.warning('请输入评测需求描述')
  planLoading.value = true
  planResult.value = null
  planRunIds.value = []
  try {
    const res = await designPlan({ req_text: planReqText.value, mode: planMode.value })
    planResult.value = res.data
  } catch (e) {
    ElMessage.error('方案生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    planLoading.value = false
  }
}
const doConfirmPlan = async () => {
  if (!planResult.value?.plan_id) return
  planConfirming.value = true
  try {
    const res = await confirmPlan(planResult.value.plan_id)
    planRunIds.value = res.data.run_ids || []
    ElMessage.success(`已创建 ${planRunIds.value.length} 个评测运行`)
    await fetchRuns()
  } catch (e) {
    ElMessage.error('确认失败：' + (e.response?.data?.detail || e.message))
  } finally {
    planConfirming.value = false
  }
}

// ---- A3 版本 / Diff ----
const versionsOfName = computed(() =>
  selectedDataset.value ? datasets.value.filter(d => d.name === selectedDataset.value.name) : []
)
const diffBase = ref(null)
const diffTarget = ref(null)
const diffResult = ref(null)
const diffLoading = ref(false)
const doClone = async () => {
  if (!selectedDatasetId.value) return
  try {
    const res = await cloneDatasetVersion(selectedDatasetId.value, {})
    ElMessage.success(`已克隆为 ${res.data.version}`)
    await fetchDatasets()
  } catch (e) {
    ElMessage.error('克隆失败：' + (e.response?.data?.detail || e.message))
  }
}
const doDiff = async () => {
  if (!diffBase.value || !diffTarget.value) return ElMessage.warning('请选择对比的两个版本')
  diffLoading.value = true
  diffResult.value = null
  try {
    const res = await diffDatasets(diffBase.value, diffTarget.value)
    diffResult.value = res.data
  } catch (e) {
    ElMessage.error('对比失败：' + (e.response?.data?.detail || e.message))
  } finally {
    diffLoading.value = false
  }
}

// ---- E7 标准 Benchmark 模板 ----
const templateKey = ref('')
const tplLoading = ref(false)
const selectedTemplate = computed(() =>
  BENCHMARK_TEMPLATES.find(t => t.key === templateKey.value) || null
)
const doCreateFromTemplate = async () => {
  if (!templateKey.value) return
  tplLoading.value = true
  try {
    const res = await createFromTemplate({ key: templateKey.value })
    const ds = res.data.dataset || {}
    ElMessage.success(`已新建数据集 ${ds.name || ''}@${ds.version || ''}（${res.data.generated_cases} 用例骨架）`)
    await fetchDatasets()
  } catch (e) {
    ElMessage.error('从模板新建失败：' + (e.response?.data?.detail || e.message))
  } finally {
    tplLoading.value = false
  }
}

// ---- 运行抽屉 ----
const runDrawer = ref(false)
const currentRun = ref(null)
const compareResult = ref(null)
const analyzeResult = ref(null)
const gateResult = ref(null)
const runReportEnrich = ref(null)
const gateThresholds = ref('{"mean_score": 0.7, "pass_rate": 0.8}')
const gateRegressDelta = ref('0.05')
// P3-7：辅助指标（仅告警，不阻断合并）
const gateAuxThresholds = ref('')
const gateAuxMetrics = ref('')

const openRunDialog = (row) => {
  currentRun.value = row
  compareResult.value = null
  analyzeResult.value = null
  gateResult.value = null
  runReportEnrich.value = null
  runLayered.value = null
  runDrawer.value = true
  // U3/E4：懒加载报告富化（校准/热力图/Elo），失败不影响主流程
  fetchRunReport(row.id)
  // P3-17：懒加载本运行分层报告（L0/L1/L2）
  fetchRunLayered(row.id)
}

// P3-17：本运行分层报告（L0/L1/L2）
const runLayered = ref(null)
const fetchRunLayered = async (runId) => {
  try {
    const res = await getRunLayeredReport(runId)
    runLayered.value = res.data
  } catch (e) { /* 分层报告为可选项，失败静默 */ }
}

const fetchRunReport = async (runId) => {
  try {
    const res = await getRunReport(runId)
    runReportEnrich.value = res.data
  } catch (e) { /* 富化为可选项，失败静默 */ }
}

const doSetBaseline = async () => {
  try {
    await setBaseline(currentRun.value.id)
    ElMessage.success('已设为基线')
    await fetchRuns()
    currentRun.value = runs.value.find(r => r.id === currentRun.value.id) || currentRun.value
  } catch (e) {
    ElMessage.error('设置基线失败')
  }
}
const doCompare = async () => {
  try {
    const res = await compareRun(currentRun.value.id, parseFloat(gateRegressDelta.value))
    compareResult.value = res.data
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || '对比失败（可能尚未设基线）')
  }
}
const doAnalyze = async () => {
  try {
    const res = await analyzeRun(currentRun.value.id)
    analyzeResult.value = res.data
  } catch (e) {
    ElMessage.error('分析失败')
  }
}
const doGate = async () => {
  let thresholds = {}
  try { thresholds = JSON.parse(gateThresholds.value || '{}') } catch { return ElMessage.warning('阈值 JSON 格式错误') }
  const payload = { thresholds, regress_delta: parseFloat(gateRegressDelta.value) }
  // P3-7：辅助指标（仅告警，不阻断）
  let auxThresholds = {}
  if (gateAuxThresholds.value.trim()) {
    try { auxThresholds = JSON.parse(gateAuxThresholds.value) } catch { return ElMessage.warning('辅助阈值 JSON 格式错误') }
  }
  if (Object.keys(auxThresholds).length) payload.aux_thresholds = auxThresholds
  if (gateAuxMetrics.value.trim()) {
    // 逗号分隔的指标名列表，例如：latency_avg,cost_tokens_total
    payload.aux_metrics = gateAuxMetrics.value.split(',').map(s => s.trim()).filter(Boolean)
  }
  try {
    const res = await gateRun(currentRun.value.id, payload)
    gateResult.value = res.data
  } catch (e) {
    ElMessage.error('门禁校验失败')
  }
}

// ---- C2 导出 Trace ----
const traceDialog = ref(false)
const traceJson = ref('')
const doExportTrace = async () => {
  try {
    const res = await exportTrace({ run: currentRun.value.id })
    traceJson.value = JSON.stringify(res.data, null, 2)
    traceDialog.value = true
  } catch (e) {
    ElMessage.error('导出失败')
  }
}
const downloadTrace = () => {
  const blob = new Blob([traceJson.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `trace-run-${currentRun.value.id}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// ---- P3-8 OTel 回流：把外部 agent 框架导出的 OTLP/JSON trace 回流为内部 EvalTrace ----
const otelImportVisible = ref(false)
const otelImporting = ref(false)
const otelCaseOptions = ref([])
const otelForm = reactive({ caseId: null, payload: '' })

const openImportOtel = async () => {
  if (!currentRun.value?.id) return
  otelImportVisible.value = true
  otelForm.caseId = null
  otelForm.payload = ''
  try {
    const res = await listCases({ dataset: currentRun.value.dataset })
    const payload = res.data.results || res.data || []
    otelCaseOptions.value = Array.isArray(payload) ? payload : []
  } catch (e) {
    otelCaseOptions.value = []
  }
}

const doImportOtel = async () => {
  if (!currentRun.value?.id) return
  if (!otelForm.caseId) return ElMessage.warning('请选择关联用例')
  let parsed
  try {
    parsed = JSON.parse(otelForm.payload)
  } catch {
    return ElMessage.warning('OTel/JSON 解析失败，请检查格式')
  }
  otelImporting.value = true
  try {
    const res = await ingestOtelTrace({
      run: currentRun.value.id,
      case: otelForm.caseId,
      payload: parsed,
    })
    ElMessage.success(
      `导入成功：trace #${res.data.trace_id}，${res.data.step_count} 步骤，状态 ${res.data.status}`
    )
    otelImportVisible.value = false
  } catch (e) {
    ElMessage.error('导入失败：' + (e.response?.data?.detail || e.message))
  } finally {
    otelImporting.value = false
  }
}

// ---- P3-15 失败 case Trace 回放（对标 UI 视频回放）----
const traceReplayDialog = ref(false)
const caseTraces = ref([])
const caseTracesLoading = ref(false)
const caseTracesFailed = computed(() => caseTraces.value.filter(c => !c.passed).length)
const caseTracesPlayable = computed(() => caseTraces.value.filter(c => c.has_trace).length)
const replayTrace = ref(null)
const playIndex = ref(-1)
const playing = ref(false)
let playTimer = null

const replayProgress = computed(() => {
  if (!replayTrace.value || !replayTrace.value.step_count) return 0
  return Math.round(((playIndex.value + 1) / replayTrace.value.step_count) * 100)
})

const doOpenTraceReplay = async () => {
  if (!currentRun.value?.id) return
  traceReplayDialog.value = true
  replayTrace.value = null
  playIndex.value = -1
  stopPlay()
  caseTracesLoading.value = true
  try {
    const res = await getRunCaseTraces(currentRun.value.id)
    caseTraces.value = res.data.cases || []
    // 自动聚焦第一个可回放的失败用例
    const first = caseTraces.value.find(c => !c.passed && c.has_trace)
    if (first) onPickCase(first)
  } catch (e) {
    ElMessage.error('加载用例 Trace 失败：' + (e.response?.data?.detail || e.message))
  } finally {
    caseTracesLoading.value = false
  }
}

const onPickCase = async (row) => {
  if (!row.has_trace) {
    replayTrace.value = null
    stopPlay()
    ElMessage.info(`用例 #${row.case_id} 暂无 Trace 记录`)
    return
  }
  stopPlay()
  try {
    const res = await getTraceReplay(row.trace_id)
    replayTrace.value = res.data
    playIndex.value = -1
    // 打开即自动播放，逐步揭示
    startPlay()
  } catch (e) {
    ElMessage.error('回放加载失败：' + (e.response?.data?.detail || e.message))
  }
}

const startPlay = () => {
  if (!replayTrace.value) return
  playing.value = true
  if (playTimer) clearInterval(playTimer)
  // 若已播放到末尾则从头开始
  if (playIndex.value >= replayTrace.value.step_count - 1) playIndex.value = -1
  playTimer = setInterval(() => {
    if (playIndex.value >= replayTrace.value.step_count - 1) {
      stopPlay()
      return
    }
    playIndex.value += 1
  }, 700)
}

const stopPlay = () => {
  playing.value = false
  if (playTimer) { clearInterval(playTimer); playTimer = null }
}

const togglePlay = () => {
  if (playing.value) stopPlay()
  else startPlay()
}

const replayReset = () => {
  stopPlay()
  playIndex.value = -1
}

const typeTag = (t) => {
  return { PLAN: 'primary', TOOL: 'success', OBSERVE: 'info', OUTPUT: 'warning', ERROR: 'danger' }[t] || 'info'
}

const json = (obj) => {
  try { return JSON.stringify(obj) } catch { return String(obj) }
}

// ---- 执行评测 ----
const runDialog = ref(false)
const runOutputs = ref('')
const runMinConfidence = ref('')
const runLoading = ref(false)
const submitRun = async () => {
  let outputs = {}
  try { outputs = JSON.parse(runOutputs.value || '{}') } catch { return ElMessage.warning('outputs JSON 格式错误') }
  const extra = {}
  if (runMinConfidence.value !== '' && runMinConfidence.value != null) {
    const mc = parseFloat(runMinConfidence.value)
    if (!isNaN(mc)) extra.min_confidence = mc
  }
  runLoading.value = true
  try {
    const res = await runEval(currentRun.value.id, outputs, extra)
    ElMessage.success('评测完成')
    runDialog.value = false
    await fetchRuns()
    await fetchReport()
  } catch (e) {
    ElMessage.error('执行失败：' + (e.response?.data?.detail || e.message))
  } finally {
    runLoading.value = false
  }
}

// P3-6 E2E Harness：Mock / Real 端到端驱动被测 agent 并评测
const harnessMode = ref('mock')
const harnessMockMode = ref('expected')
const harnessAgentConfigId = ref('')
const harnessLoading = ref(false)
const harnessResult = ref(null)
const doRunHarness = async () => {
  if (!currentRun.value) return ElMessage.warning('请先选择一次运行')
  const payload = { harness: harnessMode.value }
  if (harnessMode.value === 'mock') {
    payload.mock_mode = harnessMockMode.value
  } else {
    if (harnessAgentConfigId.value !== '' && harnessAgentConfigId.value != null) {
      const id = parseInt(harnessAgentConfigId.value, 10)
      if (!isNaN(id)) payload.agent_config_id = id
    }
  }
  harnessLoading.value = true
  harnessResult.value = null
  try {
    const res = await runHarness(currentRun.value.id, payload)
    harnessResult.value = res.data
    ElMessage.success('Harness 评测完成')
    await fetchRuns()
    await fetchReport()
  } catch (e) {
    ElMessage.error('Harness 执行失败：' + (e.response?.data?.detail || e.message))
  } finally {
    harnessLoading.value = false
  }
}

onMounted(async () => {
  await fetchDatasets()
  await fetchLeaderboard()
  await fetchKnowledge()
  await fetchSchedules()
  await fetchSkillVersions()
  await fetchColdStart()
  await fetchEdgeRules()
  await fetchJudgeStrengths()
  if (realtime.value) startPolling()
})

onUnmounted(() => {
  stopPolling()
  if (playTimer) { clearInterval(playTimer); playTimer = null }
})
</script>

<style scoped>
.metric { text-align: center; padding: 10px; background: #f5f7fa; border-radius: 8px; }
.m-val { font-size: 22px; font-weight: 700; color: #409eff; }
.m-label { font-size: 12px; color: #909399; margin-top: 4px; }
.lb-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #606266; }
.trace-step {
  border: 1px solid #e2e8f0; border-left: 4px solid #cbd5e1;
  border-radius: 8px; padding: 8px 10px; margin-bottom: 8px;
  opacity: 0.45; transition: all 0.25s ease; background: #fff;
}
.trace-step.step-active { opacity: 1; }
.trace-step.step-error { border-left-color: #f56c6c; background: #fef2f2; }
.trace-step.step-failpoint { border-left-color: #d92020; box-shadow: 0 0 0 2px rgba(217,32,32,0.15); }
.step-idx {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%; background: #409eff; color: #fff;
  font-size: 12px; font-weight: 700;
}
.step-io { font-size: 12px; color: #475569; margin-top: 4px; white-space: pre-wrap; word-break: break-all; }
.step-err { font-size: 12px; color: #f56c6c; margin-top: 2px; }
</style>
