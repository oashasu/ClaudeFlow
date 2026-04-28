<script setup lang="ts">
import type { RuntimeParsedEvent, RuntimeSession } from '../../services/runtimeApi'

defineProps<{
  session: RuntimeSession | null
  events: RuntimeParsedEvent[]
  loading: boolean
  error: string | null
  source: 'sample' | 'live'
  lastLoadedAt: string | null
  actionLoading: boolean
  actionError: string | null
  actionSuccess: string | null
  intervenePrompt: string
  completeSummary: string
  failReason: string
}>()

const emit = defineEmits<{
  'update:intervenePrompt': [value: string]
  'update:completeSummary': [value: string]
  'update:failReason': [value: string]
  intervene: []
  complete: []
  fail: []
}>()

function formatToolInput(input: unknown): string {
  if (!input) {
    return ''
  }

  try {
    return JSON.stringify(input, null, 2)
  } catch {
    return String(input)
  }
}
</script>

<template>
  <section class="inspector">
    <div class="head">
      <div>
        <p class="eyebrow">Session Inspector</p>
        <h3>Session 事件查看</h3>
      </div>
      <div class="meta">
        <span class="source" :class="source">{{ source }}</span>
        <span class="loaded-at">最近读取: <strong>{{ lastLoadedAt || '未读取' }}</strong></span>
      </div>
    </div>

    <div v-if="!session" class="empty">从上方 session 列表选择一个任务后，可在这里查看运行事件。</div>
    <template v-else>
      <div class="session-summary">
        <div>
          <span class="label">Task</span>
          <strong>{{ session.task_id }}</strong>
        </div>
        <div>
          <span class="label">Session</span>
          <code>{{ session.session_id }}</code>
        </div>
        <div>
          <span class="label">Status</span>
          <span>{{ session.status }}</span>
        </div>
        <div>
          <span class="label">Priority</span>
          <span>{{ session.priority }}</span>
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="actionError" class="error">{{ actionError }}</div>
      <div v-if="actionSuccess" class="success">{{ actionSuccess }}</div>

      <div v-if="session.status === 'running'" class="action-grid">
        <div class="action-card">
          <div class="action-head">
            <strong>Session 干预</strong>
            <span>向当前 Claude session 发送新的指令。</span>
          </div>
          <textarea
            :value="intervenePrompt"
            class="action-input"
            placeholder="例如：请先补齐支付网关的回归测试，再继续实现。"
            @input="emit('update:intervenePrompt', ($event.target as HTMLTextAreaElement).value)"
          />
          <button class="action-btn accent" :disabled="actionLoading" @click="emit('intervene')">
            {{ actionLoading ? '提交中...' : '发送干预' }}
          </button>
        </div>

        <div class="action-card">
          <div class="action-head">
            <strong>标记完成</strong>
            <span>为运行中的 task 写入 summary 并结束 runtime 节点。</span>
          </div>
          <textarea
            :value="completeSummary"
            class="action-input"
            placeholder="例如：支付网关骨架和测试已完成，准备进入集成阶段。"
            @input="emit('update:completeSummary', ($event.target as HTMLTextAreaElement).value)"
          />
          <button class="action-btn success" :disabled="actionLoading" @click="emit('complete')">
            {{ actionLoading ? '提交中...' : '标记完成' }}
          </button>
        </div>

        <div class="action-card">
          <div class="action-head">
            <strong>标记失败</strong>
            <span>写入失败原因并将 runtime 标记为需要人工介入。</span>
          </div>
          <textarea
            :value="failReason"
            class="action-input"
            placeholder="例如：发现上游协议缺字段，需先回流设计。"
            @input="emit('update:failReason', ($event.target as HTMLTextAreaElement).value)"
          />
          <button class="action-btn danger" :disabled="actionLoading" @click="emit('fail')">
            {{ actionLoading ? '提交中...' : '标记失败' }}
          </button>
        </div>
      </div>

      <div v-else-if="loading" class="empty">正在加载 session 事件...</div>
      <div v-else-if="events.length === 0" class="empty">当前 session 暂无事件。</div>
      <div v-else class="event-list">
        <article v-for="(event, index) in events" :key="`${session.session_id}-${index}`" class="event-card" :class="event.type">
          <div class="event-head">
            <span class="event-type">{{ event.type }}</span>
            <span class="event-index">#{{ index + 1 }}</span>
          </div>
          <p v-if="event.type !== 'tool_use'" class="event-text">{{ event.text || '-' }}</p>
          <pre v-else class="event-text">{{ formatToolInput(event.tool_input) }}</pre>
          <p v-if="event.type === 'tool_use'" class="tool-name">Tool: {{ event.tool_name || '-' }}</p>
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
.inspector {
  margin-top: 18px;
  padding: 18px;
  border-radius: 20px;
  background: rgba(248, 250, 246, 0.82);
  border: 1px solid rgba(44, 62, 49, 0.1);
}

.head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
  margin-bottom: 14px;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #7a5d2f;
}

.head h3 {
  margin: 0;
}

.meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
  font-size: 12px;
  color: #556452;
}

.source {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.source.sample {
  background: #efe4c8;
  color: #6c5422;
}

.source.live {
  background: #d9efe3;
  color: #245b3a;
}

.session-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.session-summary > div {
  padding: 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e3e9df;
}

.label {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7869;
}

.empty,
.error,
.success {
  padding: 14px;
  border-radius: 14px;
  font-size: 13px;
}

.empty {
  background: #f0f4ee;
  color: #62715f;
}

.error {
  background: #ffe3de;
  color: #8c2d21;
  border: 1px solid #f0a295;
}

.success {
  margin-top: 10px;
  background: #e5f6e9;
  color: #215a33;
  border: 1px solid #9fd0ac;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 14px 0;
}

.action-card {
  padding: 14px;
  border-radius: 14px;
  background: #fffdf8;
  border: 1px solid #e6dec8;
}

.action-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.action-head strong {
  color: #1d2c1f;
}

.action-head span {
  font-size: 12px;
  color: #5d6b5a;
}

.action-input {
  width: 100%;
  min-height: 92px;
  resize: vertical;
  border-radius: 12px;
  border: 1px solid #d7ddd3;
  padding: 10px 12px;
  font: inherit;
  box-sizing: border-box;
  background: #ffffff;
}

.action-btn {
  margin-top: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
}

.action-btn:disabled {
  opacity: 0.65;
  cursor: wait;
}

.action-btn.accent {
  background: #ebefff;
  color: #214089;
  border-color: #95a8e0;
}

.action-btn.success {
  background: #e5f4e7;
  color: #1d5a2d;
  border-color: #8cc09c;
}

.action-btn.danger {
  background: #ffe8e2;
  color: #8a2f26;
  border-color: #e2a49a;
}

.event-list {
  display: grid;
  gap: 10px;
}

.event-card {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid #dde5d9;
  background: #ffffff;
}

.event-card.thinking {
  background: #f4efe4;
}

.event-card.tool_use {
  background: #edf5ff;
}

.event-card.text {
  background: #eef6ef;
}

.event-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #5c6a59;
}

.event-type {
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.event-text,
.tool-name {
  margin: 0;
  color: #273226;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}

.tool-name {
  margin-top: 8px;
  font-size: 12px;
  color: #456186;
}

@media (max-width: 900px) {
  .head {
    flex-direction: column;
  }

  .meta {
    align-items: flex-start;
  }

  .session-summary {
    grid-template-columns: 1fr;
  }

  .action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
