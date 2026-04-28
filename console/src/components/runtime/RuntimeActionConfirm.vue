<script setup lang="ts">
import type { RuntimeSession } from '../../types/runtime'
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-vue-next'

interface Props {
  showIntervene: boolean
  showComplete: boolean
  showFail: boolean
  session: RuntimeSession | null
  intervenePrompt: string
  completeSummary: string
  failReason: string
  loading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:intervenePrompt', value: string): void
  (e: 'update:completeSummary', value: string): void
  (e: 'update:failReason', value: string): void
  (e: 'confirmIntervene'): void
  (e: 'confirmComplete'): void
  (e: 'confirmFail'): void
  (e: 'cancel'): void
}>()

function handleInterveneConfirm() {
  emit('confirmIntervene')
}

function handleCompleteConfirm() {
  emit('confirmComplete')
}

function handleFailConfirm() {
  emit('confirmFail')
}

function handleCancel() {
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="showIntervene || showComplete || showFail" class="confirm-overlay" @click.self="handleCancel">
      <div class="confirm-modal">
        <div v-if="showIntervene" class="confirm-content">
          <header class="confirm-header intervene">
            <AlertTriangle :size="24" />
            <h3>确认干预</h3>
          </header>
          <div class="target-summary">
            <p><strong>Task:</strong> {{ session?.task_id }}</p>
            <p><strong>Session:</strong> {{ session?.session_id }}</p>
            <p><strong>Status:</strong> {{ session?.status }}</p>
          </div>
          <div class="input-group">
            <label>干预内容</label>
            <textarea
              :value="intervenePrompt"
              @input="emit('update:intervenePrompt', ($event.target as HTMLTextAreaElement).value)"
              rows="4"
              placeholder="输入干预指令..."
            />
          </div>
          <footer class="confirm-actions">
            <button class="btn-cancel" @click="handleCancel" :disabled="loading">取消</button>
            <button class="btn-confirm intervene" @click="handleInterveneConfirm" :disabled="loading || !intervenePrompt.trim()">
              {{ loading ? '执行中...' : '确认干预' }}
            </button>
          </footer>
        </div>

        <div v-if="showComplete" class="confirm-content">
          <header class="confirm-header complete">
            <CheckCircle :size="24" />
            <h3>确认完成任务</h3>
          </header>
          <div class="target-summary">
            <p><strong>Task:</strong> {{ session?.task_id }}</p>
            <p><strong>Session:</strong> {{ session?.session_id }}</p>
            <p><strong>Status:</strong> {{ session?.status }}</p>
          </div>
          <div class="input-group">
            <label>完成摘要</label>
            <textarea
              :value="completeSummary"
              @input="emit('update:completeSummary', ($event.target as HTMLTextAreaElement).value)"
              rows="3"
              placeholder="输入完成摘要..."
            />
          </div>
          <footer class="confirm-actions">
            <button class="btn-cancel" @click="handleCancel" :disabled="loading">取消</button>
            <button class="btn-confirm complete" @click="handleCompleteConfirm" :disabled="loading">
              {{ loading ? '执行中...' : '确认完成' }}
            </button>
          </footer>
        </div>

        <div v-if="showFail" class="confirm-content">
          <header class="confirm-header fail">
            <XCircle :size="24" />
            <h3>确认标记失败</h3>
          </header>
          <div class="target-summary">
            <p><strong>Task:</strong> {{ session?.task_id }}</p>
            <p><strong>Session:</strong> {{ session?.session_id }}</p>
            <p><strong>Status:</strong> {{ session?.status }}</p>
          </div>
          <div class="input-group">
            <label>失败原因</label>
            <textarea
              :value="failReason"
              @input="emit('update:failReason', ($event.target as HTMLTextAreaElement).value)"
              rows="3"
              placeholder="输入失败原因..."
            />
          </div>
          <footer class="confirm-actions">
            <button class="btn-cancel" @click="handleCancel" :disabled="loading">取消</button>
            <button class="btn-confirm fail" @click="handleFailConfirm" :disabled="loading || !failReason.trim()">
              {{ loading ? '执行中...' : '确认失败' }}
            </button>
          </footer>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.confirm-modal {
  width: 420px;
  max-width: 90vw;
  border-radius: 16px;
  background: var(--bg-elevated, #fffdf8);
  border: 1px solid var(--border-subtle, #d8d0c2);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.2);
}

.confirm-content {
  padding: 20px;
}

.confirm-header {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.confirm-header h3 {
  margin: 0;
  font-size: 18px;
}

.confirm-header.intervene {
  color: var(--accent-warning, #b7791f);
}

.confirm-header.complete {
  color: var(--accent-primary, #1f6b5b);
}

.confirm-header.fail {
  color: var(--accent-danger, #a63f2f);
}

.target-summary {
  padding: 12px 16px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}

.target-summary p {
  margin: 4px 0;
  font-size: 13px;
  color: var(--text-muted, #5e574d);
}

.target-summary strong {
  color: var(--text-strong, #1f1d1a);
}

.input-group {
  margin-bottom: 16px;
}

.input-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-strong, #1f1d1a);
}

.input-group textarea {
  width: 100%;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #d8d0c2);
  background: var(--bg-panel, #fbf8f2);
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

.confirm-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #d8d0c2);
  background: var(--bg-panel, #fbf8f2);
  color: var(--text-muted, #5e574d);
  cursor: pointer;
}

.btn-cancel:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.06);
}

.btn-confirm {
  padding: 10px 16px;
  border-radius: 10px;
  border: none;
  color: white;
  cursor: pointer;
}

.btn-confirm.intervene {
  background: var(--accent-warning, #b7791f);
}

.btn-confirm.complete {
  background: var(--accent-primary, #1f6b5b);
}

.btn-confirm.fail {
  background: var(--accent-danger, #a63f2f);
}

.btn-confirm:hover:not(:disabled) {
  filter: brightness(1.1);
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>