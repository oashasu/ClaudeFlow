<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { PhaseStep } from '../services/api'

const props = defineProps<{
  steps: PhaseStep[]
}>()

const scrollerRef = ref<HTMLElement | null>(null)
const isDragging = ref(false)
const startX = ref(0)

// 鼠标拖拽逻辑
function startDrag(e: MouseEvent) {
  if (!scrollerRef.value) return
  isDragging.value = true
  startX.value = e.pageX - scrollerRef.value.scrollLeft
  scrollerRef.value.style.cursor = 'grabbing'
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value || !scrollerRef.value) return
  e.preventDefault()
  scrollerRef.value.scrollLeft = e.pageX - startX.value
}

function endDrag() {
  if (!scrollerRef.value) return
  isDragging.value = false
  scrollerRef.value.style.cursor = 'grab'
}

// 触摸支持
function startTouch(e: TouchEvent) {
  if (!scrollerRef.value) return
  isDragging.value = true
  startX.value = e.touches[0].pageX - scrollerRef.value.scrollLeft
}

function onTouch(e: TouchEvent) {
  if (!isDragging.value || !scrollerRef.value) return
  scrollerRef.value.scrollLeft = e.touches[0].pageX - startX.value
}

function endTouch() {
  isDragging.value = false
}

onMounted(() => {
  if (scrollerRef.value) {
    scrollerRef.value.style.cursor = 'grab'
  }
})
</script>

<template>
  <div class="step-scroller-wrapper">
    <div class="scroll-hint">◀ 左右滑动查看更多 ▶</div>

    <div
      ref="scrollerRef"
      class="step-scroller"
      @mousedown="startDrag"
      @mousemove="onDrag"
      @mouseup="endDrag"
      @mouseleave="endDrag"
      @touchstart="startTouch"
      @touchmove="onTouch"
      @touchend="endTouch"
    >
      <div class="step-container">
        <div
          v-for="step in steps"
          :key="step.id"
          class="step-card"
          :class="step.status"
        >
          <div class="step-index">步骤 {{ step.stepIndex + 1 }}</div>
          <div class="step-name">{{ step.stepName || '进行中' }}</div>
          <div class="step-icon">
            <span v-if="step.status === 'completed'">✓</span>
            <span v-else-if="step.status === 'running'">▶</span>
            <span v-else>○</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.step-scroller-wrapper {
  margin: 20px 0;
}

.scroll-hint {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-bottom: 8px;
}

.step-scroller {
  overflow-x: auto;
  white-space: nowrap;
  user-select: none;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 12px;
}

.step-scroller::-webkit-scrollbar {
  height: 8px;
}

.step-scroller::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 4px;
}

.step-container {
  display: inline-flex;
  gap: 16px;
}

.step-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 120px;
  padding: 16px;
  border-radius: 8px;
  background: white;
}

.step-card.completed {
  background: #e8f5e9;
  border: 1px solid #4caf50;
}

.step-card.running {
  background: #e3f2fd;
  border: 1px solid #2196f3;
  box-shadow: 0 0 8px rgba(33, 150, 243, 0.3);
}

.step-card.pending {
  background: white;
  border: 1px solid #e0e0e0;
}

.step-index {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.step-name {
  font-size: 14px;
  color: #333;
  text-align: center;
  white-space: normal;
}

.step-icon {
  margin-top: 8px;
  font-size: 20px;
}

.step-card.completed .step-icon { color: #4caf50; }
.step-card.running .step-icon { color: #2196f3; }
.step-card.pending .step-icon { color: #999; }
</style>