<script setup lang="ts">
defineProps<{
  title: string
  count: number
  color: 'green' | 'gray' | 'orange' | 'red'
  highlight?: boolean
}>()

const emit = defineEmits<{
  click: []
}>()
</script>

<template>
  <div
    class="stats-card"
    :class="[color, { highlight }]"
    @click="emit('click')"
  >
    <div class="title">{{ title }}</div>
    <div class="count">{{ count }}</div>
  </div>
</template>

<style scoped>
.stats-card {
  padding: 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  text-align: center;
  user-select: none;
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.stats-card.green {
  background: linear-gradient(135deg, #4caf50, #43a047);
  color: white;
}

.stats-card.gray {
  background: linear-gradient(135deg, #757575, #616161);
  color: white;
}

.stats-card.orange {
  background: linear-gradient(135deg, #ff9800, #f57c00);
  color: white;
}

.stats-card.red {
  background: linear-gradient(135deg, #f44336, #e53935);
  color: white;
}

.stats-card.highlight {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 152, 0, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(255, 152, 0, 0); }
}

.title {
  font-size: 14px;
  margin-bottom: 8px;
  opacity: 0.9;
}

.count {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}
</style>