<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  phase?: string
  progress?: number
  size?: 'small' | 'large'
  expanded?: string | null
}>()

const emit = defineEmits<{
  phaseClick: [phase: string]
}>()

// 7阶段定义
const phases = [
  { id: 'Phase0', name: '拆分', index: 0 },
  { id: 'Phase1', name: '规划', index: 1 },
  { id: 'Phase2', name: '准备', index: 2 },
  { id: 'Phase3', name: '开发', index: 3 },
  { id: 'Phase4', name: '审查', index: 4 },
  { id: 'Phase5', name: '测试', index: 5 },
  { id: 'Phase6', name: '完成', index: 6 },
]

// 计算每个阶段的状态
function getPhaseStatus(phaseIndex: number): 'completed' | 'running' | 'pending' {
  if (!props.phase) return 'pending'

  const currentPhaseIndex = phases.findIndex(p => p.id === props.phase)

  if (phaseIndex < currentPhaseIndex) return 'completed'
  if (phaseIndex === currentPhaseIndex) return 'running'
  return 'pending'
}

// 当前阶段进度
const currentProgress = computed(() => {
  if (!props.progress) return { current: 0, total: 100 }
  return { current: props.progress, total: 100 }
})
</script>

<template>
  <div class="workflow-progress" :class="size">
    <div class="phase-container">
      <div
        v-for="phase in phases"
        :key="phase.id"
        class="phase-node"
        :class="getPhaseStatus(phase.index)"
        @click="emit('phaseClick', phase.id)"
      >
        <div class="node-circle">
          <span v-if="getPhaseStatus(phase.index) === 'completed'">✓</span>
          <span v-else-if="getPhaseStatus(phase.index) === 'running'">▶</span>
          <span v-else>○</span>
        </div>
        <div class="phase-name">{{ phase.name }}</div>
        <div class="phase-status">
          <template v-if="getPhaseStatus(phase.index) === 'completed'">已完成</template>
          <template v-else-if="getPhaseStatus(phase.index) === 'running'">
            进行中 {{ currentProgress.current }}%
          </template>
          <template v-else>待执行</template>
        </div>
      </div>

      <!-- 连接线 -->
      <div class="connectors">
        <div
          v-for="i in 6"
          :key="i"
          class="connector"
          :class="{
            active: getPhaseStatus(i - 1) === 'completed' || getPhaseStatus(i) === 'running'
          }"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.workflow-progress {
  padding: 16px;
}

.workflow-progress.small {
  padding: 8px;
}

.workflow-progress.small .phase-node {
  padding: 8px;
}

.workflow-progress.small .node-circle {
  width: 24px;
  height: 24px;
  font-size: 12px;
}

.phase-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.phase-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  cursor: pointer;
  transition: transform 0.2s;
}

.phase-node:hover {
  transform: scale(1.05);
}

.node-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-bottom: 8px;
}

.phase-node.completed .node-circle {
  background: #4caf50;
  color: white;
}

.phase-node.running .node-circle {
  background: #2196F3;
  color: white;
  box-shadow: 0 0 12px rgba(33, 150, 243, 0.5);
}

.phase-node.pending .node-circle {
  background: #e0e0e0;
  color: #999;
}

.phase-name {
  font-size: 14px;
  font-weight: bold;
  color: #333;
}

.phase-status {
  font-size: 12px;
  color: #666;
}

.connectors {
  position: absolute;
  top: 32px;
  left: 60px;
  right: 60px;
  display: flex;
  justify-content: space-between;
}

.connector {
  width: calc(100% / 6 - 40px);
  height: 2px;
  background: #e0e0e0;
}

.connector.active {
  background: #4caf50;
}
</style>