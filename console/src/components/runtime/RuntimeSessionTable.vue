<script setup lang="ts">
import type { RuntimeSession } from '../../services/runtimeApi'

defineProps<{
  sessions: Array<{
    task_id: string
    session_id: string
    status: string
    priority: string
    owner_role?: string
    task_type?: string
    summary?: string
  }>
}>()

const emit = defineEmits<{
  explainTask: [taskId: string]
  viewEvents: [session: RuntimeSession]
}>()
</script>

<template>
  <div class="session-table">
    <div class="table-head">
      <span>Task</span>
      <span>Status</span>
      <span>Priority</span>
      <span>Role</span>
      <span>Actions</span>
    </div>
    <div v-if="sessions.length === 0" class="empty">暂无 session</div>
    <div v-for="session in sessions" :key="session.session_id" class="table-row">
      <div>
        <strong>{{ session.task_id }}</strong>
        <code>{{ session.session_id }}</code>
      </div>
      <span>{{ session.status }}</span>
      <span>{{ session.priority }}</span>
      <span>{{ session.owner_role || '-' }}</span>
      <div class="actions">
        <button class="action-btn" @click="emit('explainTask', session.task_id)">解释任务</button>
        <button class="action-btn secondary" @click="emit('viewEvents', session as RuntimeSession)">查看事件</button>
      </div>
      <p v-if="session.summary">{{ session.summary }}</p>
    </div>
  </div>
</template>

<style scoped>
.session-table {
  margin-top: 16px;
}

.table-head,
.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1.3fr;
  gap: 12px;
  align-items: start;
}

.table-head {
  padding: 0 0 8px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #647262;
}

.table-row {
  padding: 12px 14px;
  border-radius: 14px;
  background: #f7f9f5;
  border: 1px solid #e1e8de;
}

.table-row + .table-row {
  margin-top: 10px;
}

.table-row strong {
  display: block;
  color: #18271c;
}

.table-row code,
.table-row span,
.table-row p {
  margin: 0;
  font-size: 13px;
  color: #556452;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #36503b;
  background: #1f3828;
  color: #f6f8f4;
  cursor: pointer;
  font-size: 12px;
}

.action-btn.secondary {
  background: #f3ead5;
  color: #183024;
  border-color: #c6b58d;
}

.empty {
  padding: 12px 14px;
  border-radius: 14px;
  background: #eef3ec;
  color: #6a7767;
  font-size: 13px;
}

@media (max-width: 900px) {
  .table-head,
  .table-row {
    grid-template-columns: 1fr;
  }
}
</style>
