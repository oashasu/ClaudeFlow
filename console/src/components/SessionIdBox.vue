<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  sessionId: string
}>()

const copied = ref(false)

function copySessionId() {
  navigator.clipboard.writeText(props.sessionId)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
}
</script>

<template>
  <div class="session-id-box">
    <div class="session-header">
      <span class="icon">🔗</span>
      <span>CLI会话</span>
    </div>

    <div class="session-content">
      <span class="label">会话ID:</span>
      <code class="session-id">{{ sessionId }}</code>
      <button class="copy-btn" @click="copySessionId">
        {{ copied ? '已复制 ✓' : '📋 复制会话ID' }}
      </button>
    </div>

    <div class="session-hint">
      💡 复制后可用 <code>claude --resume {{ sessionId }}</code> 继续
    </div>
  </div>
</template>

<style scoped>
.session-id-box {
  padding: 16px;
  background: #fff3e0;
  border: 2px solid #ff9800;
  border-radius: 12px;
  margin: 16px 0;
}

.session-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: bold;
  color: #333;
}

.session-content {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.label {
  color: #666;
}

.session-id {
  font-family: monospace;
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 6px;
  color: #333;
}

.copy-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #ff9800;
  color: white;
  cursor: pointer;
}

.copy-btn:hover {
  background: #f57c00;
}

.session-hint {
  font-size: 14px;
  color: #666;
}

.session-hint code {
  font-family: monospace;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}
</style>