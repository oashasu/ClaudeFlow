<script setup lang="ts">
defineProps<{
  explain: {
    state: string
    task_id: string
    reason_code: string
    reason: string
    dependencies: string[]
  }
}>()
</script>

<template>
  <div class="explain-card">
    <div class="badge">{{ explain.state }}</div>
    <h3>{{ explain.task_id }}</h3>
    <p class="code">{{ explain.reason_code }}</p>
    <p>{{ explain.reason }}</p>
    <p class="deps">
      依赖:
      <span v-if="explain.dependencies.length">{{ explain.dependencies.join(', ') }}</span>
      <span v-else>-</span>
    </p>
  </div>
</template>

<style scoped>
.explain-card {
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f7fbf6 0%, #edf3ec 100%);
  border: 1px solid #d6e0d4;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #1f3828;
  color: #f4f8f3;
  font-size: 12px;
  margin-bottom: 12px;
}

.code,
.deps,
.explain-card p {
  margin: 0;
  font-size: 13px;
  color: #556452;
}

.explain-card h3 {
  margin: 0 0 8px;
}
</style>
