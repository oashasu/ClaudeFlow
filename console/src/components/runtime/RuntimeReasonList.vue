<script setup lang="ts">
defineProps<{
  title: string
  emptyText: string
  items: Array<{ task_id: string; priority?: string; reason_code?: string; reason?: string; session_id?: string; owner_role?: string }>
  variant?: 'default' | 'blocked'
}>()
</script>

<template>
  <div class="list-block">
    <h3>{{ title }}</h3>
    <div v-if="items.length === 0" class="empty">{{ emptyText }}</div>
    <div
      v-for="item in items"
      :key="`${item.task_id}-${item.reason_code ?? item.session_id ?? title}`"
      class="row-card"
      :class="{ blocked: variant === 'blocked' }"
    >
      <strong>{{ item.task_id }}</strong>
      <span v-if="item.priority">{{ item.priority }}</span>
      <span v-if="item.owner_role">{{ item.owner_role }}</span>
      <span v-if="item.reason_code">{{ item.reason_code }}</span>
      <code v-if="item.session_id">{{ item.session_id }}</code>
      <p v-if="item.reason">{{ item.reason }}</p>
    </div>
  </div>
</template>

<style scoped>
.list-block + .list-block {
  margin-top: 16px;
}

.list-block h3 {
  margin: 0 0 10px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #556452;
}

.row-card {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f7f9f5;
  border: 1px solid #e1e8de;
}

.row-card + .row-card {
  margin-top: 10px;
}

.row-card.blocked {
  background: #fff4e8;
  border-color: #f0cf9f;
}

.row-card strong {
  color: #18271c;
}

.row-card span,
.row-card p {
  margin: 0;
  font-size: 13px;
  color: #556452;
}

.empty {
  padding: 12px 14px;
  border-radius: 14px;
  background: #eef3ec;
  color: #6a7767;
  font-size: 13px;
}
</style>
