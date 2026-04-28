<script setup lang="ts">
defineProps<{
  items: Array<{ label: string; value: string | number }>
}>()
</script>

<template>
  <div class="stats">
    <div v-for="item in items" :key="item.label" class="metric">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
    </div>
  </div>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.metric {
  padding: 12px;
  border-radius: 14px;
  background: #eef3ec;
}

.metric span {
  display: block;
  font-size: 12px;
  color: #637160;
}

.metric strong {
  font-size: 26px;
  color: #173320;
}
</style>
