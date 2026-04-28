<script setup lang="ts">
import { computed } from 'vue'
import { useRuntimeLiveData } from '../composables/useRuntimeLiveData'
import { useRuntimeActions } from '../composables/useRuntimeActions'
import type { RuntimeSession } from '../types/runtime'
import RuntimeMetricGrid from '../components/runtime/RuntimeMetricGrid.vue'
import RuntimeReasonList from '../components/runtime/RuntimeReasonList.vue'
import RuntimeExplainCard from '../components/runtime/RuntimeExplainCard.vue'
import RuntimeSessionTable from '../components/runtime/RuntimeSessionTable.vue'
import RuntimeSessionInspector from '../components/runtime/RuntimeSessionInspector.vue'
import RuntimeActionConfirm from '../components/runtime/RuntimeActionConfirm.vue'
import RuntimeActionAudit from '../components/runtime/RuntimeActionAudit.vue'
import { RefreshCw, AlertTriangle } from 'lucide-vue-next'

const liveData = useRuntimeLiveData()
const actions = useRuntimeActions(() => liveData.refreshAll())

function loadSamples() {
  liveData.loadSampleData()
  actions.clearMessages()
}

function explainTask(taskId: string) {
  liveData.setExplainTaskId(taskId)
  liveData.loadLiveExplain(taskId)
}

function viewSessionEvents(session: RuntimeSession) {
  liveData.loadLiveSessionEvents(session)
}

function handleInterveneRequest(session: RuntimeSession) {
  actions.requestInterveneConfirm(session)
}

function handleCompleteRequest(session: RuntimeSession) {
  actions.requestCompleteConfirm(session)
}

function handleFailRequest(session: RuntimeSession) {
  actions.requestFailConfirm(session)
}

const plan = computed(() => liveData.plan.value)
const explain = computed(() => liveData.explain.value)
const dispatch = computed(() => liveData.dispatch.value)
</script>

<template>
  <div class="runtime-console">
    <section class="hero">
      <div>
        <p class="eyebrow">Runtime Console</p>
        <h1>ClaudeFlow Runtime</h1>
        <p class="subtitle">
          现有 Dashboard 更偏旧的任务流；这个视图单独面向 runtime 的
          <code>plan / dispatch / explain</code> JSON。
        </p>
      </div>
      <div class="hero-actions">
        <button class="sample-btn" @click="loadSamples">加载示例数据</button>
        <button class="sample-btn secondary" @click="liveData.loadLivePlan">读取 Live Plan</button>
      </div>
    </section>

    <section class="polling-bar">
      <label class="toggle">
        <input v-model="liveData.autoRefreshEnabled.value" type="checkbox" />
        <span>自动刷新</span>
      </label>
      <label class="interval">
        轮询间隔
        <select v-model="liveData.autoRefreshSeconds.value">
          <option :value="3">3s</option>
          <option :value="5">5s</option>
          <option :value="10">10s</option>
          <option :value="15">15s</option>
        </select>
      </label>
      <span class="hint">
        开启后会自动刷新 live plan，并在有 task_id 时刷新 explain。
      </span>
      <span class="hint status">
        最近刷新:
        <strong>{{ liveData.state.value.lastRefreshedAt || '未刷新' }}</strong>
      </span>
      <button
        v-if="liveData.state.value.liveError"
        class="retry-btn"
        @click="liveData.refreshAll"
      >
        <RefreshCw :size="14" />
        重试 Live 读取
      </button>
    </section>

    <div v-if="liveData.state.value.parseError" class="error-banner parse">
      <AlertTriangle :size="16" />
      {{ liveData.state.value.parseError }}
    </div>
    <div v-if="liveData.state.value.liveError" class="error-banner live">
      <AlertTriangle :size="16" />
      {{ liveData.state.value.liveError }}
    </div>

    <section class="overview">
      <div class="overview-head">
        <div>
          <p class="eyebrow">Runtime Overview</p>
          <h2>运行时总览</h2>
        </div>
        <button class="sample-btn secondary" @click="liveData.loadLiveStatus">读取 Live 总览</button>
      </div>
      <RuntimeMetricGrid
        v-if="liveData.state.value.status"
        :items="[
          { label: 'Active', value: liveData.state.value.status.active_agents },
          { label: 'Queued', value: liveData.state.value.status.queued_tasks },
          { label: 'Completed', value: liveData.state.value.status.completed_tasks }
        ]"
      />
      <RuntimeMetricGrid
        v-if="liveData.state.value.status"
        :items="[
          { label: 'Failed', value: liveData.state.value.status.failed_tasks },
          { label: 'Intervention', value: liveData.state.value.status.intervention_required ? 'Yes' : 'No' },
          { label: 'Running IDs', value: liveData.state.value.status.running_tasks.length }
        ]"
      />
      <div class="repo-line" v-if="liveData.state.value.status">
        <strong>Repo:</strong>
        <code>{{ liveData.state.value.status.repo_path }}</code>
      </div>
      <RuntimeSessionTable
        :sessions="liveData.state.value.sessions"
        @explain-task="explainTask"
        @view-events="viewSessionEvents"
        @intervene-session="handleInterveneRequest"
        @complete-task="handleCompleteRequest"
        @fail-task="handleFailRequest"
      />
      <RuntimeSessionInspector
        :session="liveData.state.value.selectedSession"
        :events="liveData.state.value.sessionEvents"
        :loading="liveData.state.value.sessionEventsLoading"
        :error="liveData.state.value.sessionEventsError"
        :source="liveData.state.value.sessionEventsSource"
        :last-loaded-at="liveData.state.value.sessionEventsLoadedAt"
        :action-loading="actions.state.value.loading"
        :action-error="actions.state.value.error"
        :action-success="actions.state.value.success"
        :intervene-prompt="actions.confirmState.value.intervenePrompt"
        :complete-summary="actions.confirmState.value.completeSummary"
        :fail-reason="actions.confirmState.value.failReason"
        @update:intervene-prompt="actions.setIntervenePrompt($event)"
        @update:complete-summary="actions.setCompleteSummary($event)"
        @update:fail-reason="actions.setFailReason($event)"
        @intervene="liveData.state.value.selectedSession && handleInterveneRequest(liveData.state.value.selectedSession)"
        @complete="liveData.state.value.selectedSession && handleCompleteRequest(liveData.state.value.selectedSession)"
        @fail="liveData.state.value.selectedSession && handleFailRequest(liveData.state.value.selectedSession)"
      />
      <RuntimeActionAudit
        :history="actions.state.value.actionHistory"
        :last-result="actions.state.value.lastActionResult"
      />
    </section>

    <section class="grid">
      <article class="panel">
        <header class="panel-head">
          <h2>Plan</h2>
          <p>查看 runnable / blocked / running 三类任务。</p>
          <div class="panel-meta">
            <span class="source-badge" :class="liveData.state.value.planSource">{{ liveData.state.value.planSource }}</span>
          </div>
        </header>
        <div v-if="plan" class="summary">
          <RuntimeMetricGrid
            :items="[
              { label: 'Runnable', value: plan.runnable.length },
              { label: 'Blocked', value: plan.blocked.length },
              { label: 'Running', value: plan.running.length }
            ]"
          />
          <RuntimeReasonList
            title="Runnable"
            empty-text="暂无可运行任务"
            :items="plan.runnable"
          />
          <RuntimeReasonList
            title="Blocked"
            empty-text="暂无阻塞任务"
            :items="plan.blocked"
            variant="blocked"
          />
          <details class="json-details">
            <summary>查看原始 JSON</summary>
            <textarea v-model="liveData.planInput.value" class="json-box" spellcheck="false" />
          </details>
        </div>
      </article>

      <article class="panel">
        <header class="panel-head">
          <h2>Explain</h2>
          <p>单任务为什么能跑，或为什么被阻塞。</p>
          <div class="panel-meta">
            <span class="source-badge" :class="liveData.state.value.explainSource">{{ liveData.state.value.explainSource }}</span>
          </div>
        </header>
        <div class="toolbar">
          <input v-model="liveData.explainTaskId.value" class="task-input" placeholder="输入 task_id" />
          <button class="toolbar-btn" @click="liveData.loadLiveExplain()">读取 Live Explain</button>
        </div>
        <div v-if="explain" class="summary">
          <RuntimeExplainCard :explain="explain" />
          <details class="json-details">
            <summary>查看原始 JSON</summary>
            <textarea v-model="liveData.explainInput.value" class="json-box" spellcheck="false" />
          </details>
        </div>
      </article>

      <article class="panel">
        <header class="panel-head">
          <h2>Dispatch</h2>
          <p>查看调度结果、槽位和 blocked/skip 明细。</p>
          <div class="panel-meta">
            <span class="source-badge" :class="liveData.state.value.dispatchSource">{{ liveData.state.value.dispatchSource }}</span>
          </div>
        </header>
        <div class="toolbar">
          <button class="toolbar-btn" @click="liveData.runLiveDispatch(2)">执行 Live Dispatch</button>
        </div>
        <div v-if="dispatch" class="summary">
          <RuntimeMetricGrid
            :items="[
              { label: 'Active', value: dispatch.active_agents },
              { label: 'Slots', value: dispatch.available_slots },
              { label: 'Started', value: dispatch.started.length }
            ]"
          />
          <RuntimeReasonList
            title="Started"
            empty-text="暂无启动任务"
            :items="dispatch.started"
          />
          <RuntimeReasonList
            title="Blocked / Skipped"
            empty-text="暂无阻塞或跳过任务"
            :items="[...dispatch.blocked, ...dispatch.skipped]"
            variant="blocked"
          />
          <details class="json-details">
            <summary>查看原始 JSON</summary>
            <textarea v-model="liveData.dispatchInput.value" class="json-box" spellcheck="false" />
          </details>
        </div>
      </article>
    </section>

    <RuntimeActionConfirm
      :show-intervene="actions.confirmState.value.showInterveneConfirm"
      :show-complete="actions.confirmState.value.showCompleteConfirm"
      :show-fail="actions.confirmState.value.showFailConfirm"
      :session="actions.confirmState.value.pendingSession"
      :intervene-prompt="actions.confirmState.value.intervenePrompt"
      :complete-summary="actions.confirmState.value.completeSummary"
      :fail-reason="actions.confirmState.value.failReason"
      :loading="actions.state.value.loading"
      @update:intervene-prompt="actions.setIntervenePrompt($event)"
      @update:complete-summary="actions.setCompleteSummary($event)"
      @update:fail-reason="actions.setFailReason($event)"
      @confirm-intervene="actions.executeIntervene"
      @confirm-complete="actions.executeComplete"
      @confirm-fail="actions.executeFail"
      @cancel="actions.cancelConfirm"
    />
  </div>
</template>

<style scoped>
.runtime-console {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(255, 210, 120, 0.24), transparent 28%),
    radial-gradient(circle at top right, rgba(76, 175, 80, 0.16), transparent 22%),
    linear-gradient(180deg, #f5efe2 0%, #f8f7f3 50%, #f1f3ef 100%);
  color: #1f2620;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 12px;
  color: #7a5d2f;
}

.hero h1 {
  margin: 0;
  font-size: 44px;
  line-height: 1;
}

.subtitle {
  max-width: 760px;
  margin-top: 12px;
  color: #495746;
}

.polling-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
  margin-bottom: 20px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(44, 62, 49, 0.1);
}

.toggle,
.interval {
  display: flex;
  gap: 8px;
  align-items: center;
  color: #324531;
  font-size: 14px;
}

.interval select {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #d2d8d0;
  background: #fbfcfa;
}

.hint {
  font-size: 13px;
  color: #5a6957;
}

.hint.status strong {
  color: #1d3525;
}

.retry-btn {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid #8eaedb;
  background: #edf5ff;
  color: #214d84;
  cursor: pointer;
}

.overview {
  margin-bottom: 20px;
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(44, 62, 49, 0.12);
  box-shadow: 0 16px 40px rgba(55, 78, 63, 0.1);
}

.overview-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 14px;
}

.overview-head h2 {
  margin: 0;
}

.repo-line {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 8px;
  color: #445541;
  font-size: 13px;
}

.sample-btn {
  padding: 12px 18px;
  border: 1px solid #38523e;
  background: #1f3828;
  color: #f5f7f3;
  border-radius: 999px;
  cursor: pointer;
}

.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.sample-btn.secondary {
  background: #f4ead5;
  color: #183024;
  border-color: #b7a67e;
}

.error-banner {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 20px;
  padding: 14px 16px;
  border-radius: 12px;
}

.error-banner.parse {
  background: #ffe2de;
  color: #8c2d21;
  border: 1px solid #f0a295;
}

.error-banner.live {
  background: #e7f2ff;
  color: #214d84;
  border-color: #9ebce6;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.panel {
  border-radius: 22px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(44, 62, 49, 0.12);
  box-shadow: 0 16px 40px rgba(55, 78, 63, 0.12);
}

.panel-head {
  padding: 18px 20px 0;
}

.panel-head h2 {
  margin: 0;
}

.panel-head p {
  margin: 8px 0 0;
  color: #5c6a59;
  font-size: 14px;
}

.panel-meta {
  margin-top: 12px;
}

.source-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.source-badge.sample {
  background: #f4ead5;
  color: #6b5325;
}

.source-badge.live {
  background: #dff2e2;
  color: #21522c;
}

.json-box {
  width: calc(100% - 32px);
  min-height: 220px;
  margin: 16px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid #d2d8d0;
  background: #0f1511;
  color: #d7e4da;
  font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
  resize: vertical;
}

.json-details {
  margin-top: 16px;
  border-top: 1px dashed #d5dcd1;
  padding-top: 12px;
}

.json-details summary {
  cursor: pointer;
  color: #41523f;
  font-size: 13px;
  user-select: none;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 0 16px;
}

.task-input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #d2d8d0;
  background: #fbfcfa;
}

.toolbar-btn {
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid #cad7c9;
  background: #eef4ed;
  color: #1d3525;
  cursor: pointer;
}

.summary {
  padding: 0 16px 18px;
}

@media (max-width: 1180px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .hero {
    flex-direction: column;
    align-items: start;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .polling-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .overview-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>