<script setup lang="ts">
import type { RuntimeActionResult } from '../../types/runtime'
import { CheckCircle, XCircle, Clock } from 'lucide-vue-next'

interface Props {
  history: RuntimeActionResult[]
  lastResult: RuntimeActionResult | null
}

defineProps<Props>()
</script>

<template>
  <div class="action-audit">
    <header class="audit-header">
      <Clock :size="16" />
      <h4>动作审计</h4>
    </header>
    <div v-if="lastResult" class="last-result" :class="{ success: lastResult.success, fail: !lastResult.success }">
      <span class="result-icon">
        <CheckCircle v-if="lastResult.success" :size="14" />
        <XCircle v-else :size="14" />
      </span>
      <span class="result-type">{{ lastResult.actionType }}</span>
      <span class="result-message">{{ lastResult.message }}</span>
      <span class="result-time">{{ lastResult.timestamp }}</span>
    </div>
    <div v-else class="empty-state">暂无动作记录</div>
    <details v-if="history.length > 1" class="history-details">
      <summary>查看历史记录 ({{ history.length }})</summary>
      <ul class="history-list">
        <li v-for="item in history.slice(1)" :key="item.timestamp" :class="{ success: item.success, fail: !item.success }">
          <span class="history-type">{{ item.actionType }}</span>
          <span class="history-target">{{ item.targetTaskId }}</span>
          <span class="history-time">{{ item.timestamp }}</span>
        </li>
      </ul>
    </details>
  </div>
</template>

<style scoped>
.action-audit {
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid var(--border-subtle, #d8d0c2);
}

.audit-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  color: var(--text-muted, #5e574d);
}

.audit-header h4 {
  margin: 0;
  font-size: 13px;
}

.last-result {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
}

.last-result.success {
  background: rgba(31, 107, 91, 0.1);
  color: var(--accent-primary, #1f6b5b);
}

.last-result.fail {
  background: rgba(166, 63, 47, 0.1);
  color: var(--accent-danger, #a63f2f);
}

.result-icon {
  display: flex;
}

.result-type {
  font-weight: 500;
  text-transform: uppercase;
  font-size: 11px;
}

.result-message {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-time {
  font-size: 11px;
  opacity: 0.7;
}

.empty-state {
  font-size: 12px;
  color: var(--text-muted, #5e574d);
}

.history-details {
  margin-top: 10px;
  border-top: 1px dashed var(--border-subtle, #d8d0c2);
  padding-top: 8px;
}

.history-details summary {
  cursor: pointer;
  font-size: 12px;
  color: var(--text-muted, #5e574d);
}

.history-list {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.history-list li {
  display: flex;
  gap: 8px;
  font-size: 11px;
  padding: 4px 0;
}

.history-list li.success {
  color: var(--accent-primary, #1f6b5b);
}

.history-list li.fail {
  color: var(--accent-danger, #a63f2f);
}

.history-type {
  font-weight: 500;
  text-transform: uppercase;
}

.history-target {
  flex: 1;
}

.history-time {
  opacity: 0.7;
}
</style>