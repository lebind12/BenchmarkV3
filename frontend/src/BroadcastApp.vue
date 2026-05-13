<script setup lang="ts">
</script>

<template>
  <!-- 방송용 페이지: 크로마키 배경 #00B140 (OBS chroma green) -->
  <main class="broadcast">
    <div class="content">
      <h1>방송용 페이지</h1>
      <p>크로마키 합성 송출 데모 (1920×1080)</p>
    </div>
  </main>
</template>

<style scoped>
.broadcast {
  width: 100%;
  min-height: 100vh;
  background-color: #00B140;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: system-ui, -apple-system, sans-serif;
}
.content {
  color: #ffffff;
  text-align: center;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}
h1 {
  font-size: 4rem;
  margin: 0 0 1rem;
}
p {
  font-size: 1.5rem;
  margin: 0;
}
</style>
