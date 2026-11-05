<template>
  <template v-for="(part, index) in parts" :key="index">
    <span v-if="part.metric" class="seg-metric" :title="metrics[part.metric]?.label">{{ part.text }}</span>
    <a v-else-if="part.citation" class="ui-link" :href="`#ref-${part.citation}`">{{ part.text }}</a>
    <mark v-else-if="part.unverified" class="seg-unverified" title="模型自行写出的数字，未经平台核对">{{ part.text }}</mark>
    <span v-else-if="part.unknown" class="seg-unknown" title="模型引用了不存在的指标，已移除">{{ part.text }}</span>
    <template v-else>{{ part.text }}</template>
  </template>
</template>

<script setup>
defineProps({ parts: { type: Array, default: () => [] }, metrics: { type: Object, default: () => ({}) } })
</script>

<style scoped>
.seg-metric { font-weight: 500; font-variant-numeric: tabular-nums; color: var(--ink); text-decoration: underline dotted; text-decoration-color: var(--line-strong); text-underline-offset: 3px; cursor: help; }
.seg-unverified { padding: 0 2px; border-radius: 3px; color: var(--warn); background: var(--warn-soft); cursor: help; }
.seg-unknown { color: var(--ink-3); cursor: help; }
</style>
