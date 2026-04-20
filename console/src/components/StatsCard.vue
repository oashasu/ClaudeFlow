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
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stats-card.green {
  background: #4caf50;
  color: white;
}

.stats-card.gray {
  background: #9e9e9e;
  color: white;
}

.stats-card.orange {
  background: #ff9800;
  color: white;
}

.stats-card.red {
  background: #f44336;
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
}

.count {
  font-size: 32px;
  font-weight: bold;
}
</style>