<script setup lang="ts">
import type { Checkpoint } from '../services/api'

const props = defineProps<{
  checkpoints: Checkpoint[]
}>()

const emit = defineEmits<{
  revert: [checkpointId: string]
}>()

function handleRevert(checkpointId: string) {
  if (confirm('确认回退到此Checkpoint？')) {
    emit('revert', checkpointId)
  }
}
</script>

<template>
  <div class="checkpoint-timeline">
    <h3>Checkpoint 历史</h3>

    <div v-if="checkpoints.length === 0" class="empty">
      暂无Checkpoint记录
    </div>

    <div v-else class="timeline">
      <div
        v-for="cp in checkpoints"
        :key="cp.id"
        class="checkpoint-item"
        :class="{ current: cp.isCurrent }"
      >
        <div class="timeline-dot"></div>
        <div class="checkpoint-content">
          <div class="checkpoint-info">
            <span class="checkpoint-id">{{ cp.id }}</span>
            <span class="checkpoint-phase">{{ cp.phase }}</span>
          </div>
          <div class="checkpoint-summary">{{ cp.summary }}</div>
          <div class="checkpoint-time">{{ cp.gmtCreate }}</div>
        </div>
        <button
          v-if="!cp.isCurrent"
          class="revert-btn"
          @click="handleRevert(cp.id)"
        >
          回退
        </button>
        <span v-else class="current-label">当前</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.checkpoint-timeline {
  margin: 24px 0;
}

.checkpoint-timeline h3 {
  margin-bottom: 16px;
  color: #333;
}

.empty {
  text-align: center;
  color: #999;
  padding: 20px;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.checkpoint-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
  border-left: 3px solid #ccc;
}

.checkpoint-item.current {
  background: #e3f2fd;
  border-left-color: #2196f3;
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ccc;
}

.checkpoint-item.current .timeline-dot {
  background: #2196f3;
}

.checkpoint-content {
  flex: 1;
}

.checkpoint-info {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}

.checkpoint-id {
  font-weight: bold;
  color: #333;
}

.checkpoint-phase {
  color: #666;
}

.checkpoint-summary {
  font-size: 14px;
  color: #333;
  margin-bottom: 4px;
}

.checkpoint-time {
  font-size: 12px;
  color: #999;
}

.revert-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #f5f5f5;
  color: #333;
  cursor: pointer;
}

.current-label {
  padding: 4px 12px;
  background: #2196f3;
  color: white;
  border-radius: 12px;
  font-size: 12px;
}
</style>