<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">ClaudeFlow Console</div>
      <nav class="nav">
        <RouterLink to="/">任务视图</RouterLink>
        <RouterLink to="/runtime">Runtime 视图</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<style>
body {
  margin: 0;
}

#app {
  min-height: 100vh;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 22px;
  background: #13261d;
  color: #f4f8f3;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand {
  font-size: 14px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.nav {
  display: flex;
  gap: 14px;
}

.nav a {
  color: rgba(244, 248, 243, 0.72);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 999px;
}

.nav a.router-link-active {
  color: #13261d;
  background: #e4f0d8;
}
</style>
