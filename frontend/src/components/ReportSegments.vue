<template>
  <template v-for="(part, index) in parts" :key="index">
    <button v-if="part.metric && seekable(metrics[part.metric])" type="button" class="seg-metric seg-seek" :title="`跳到这一刻 · ${metrics[part.metric].label}`"
            @click="emit('seek', metrics[part.metric].seek_s)"><IconPlayerPlay aria-hidden="true" />{{ part.text }}</button>
    <span v-else-if="part.metric" class="seg-metric" :title="metrics[part.metric]?.label">{{ part.text }}</span>
    <a v-else-if="part.citation" class="ui-link" :href="`#ref-${part.citation}`">{{ part.text }}</a>
    <mark v-else-if="part.unverified" class="seg-unverified" title="模型自行写出的数字，未经平台核对">{{ part.text }}</mark>
    <span v-else-if="part.unknown" class="seg-unknown" title="模型引用了不存在的指标，已移除">{{ part.text }}</span>
    <template v-else>{{ part.text }}</template>
  </template>
</template>

<script setup>
import { IconPlayerPlay } from '@tabler/icons-vue'

// With `seekTask`, metrics that carry a time in that video become buttons that seek the player.
const props = defineProps({ parts: { type: Array, default: () => [] }, metrics: { type: Object, default: () => ({}) }, seekTask: { type: Number, default: null } })
const emit = defineEmits(['seek'])
const seekable = item => props.seekTask != null && item?.seek_s != null && item.task_id === props.seekTask
</script>

<style scoped>
.seg-metric { font-weight: 500; white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--ink); text-decoration: underline dotted; text-decoration-color: var(--line-strong); text-underline-offset: 3px; cursor: help; }
.seg-seek { display: inline-flex; align-items: baseline; gap: 2px; padding: 0 3px; border: 0; border-radius: var(--radius-sm); font: inherit; font-weight: 500; color: var(--accent); background: var(--accent-soft); text-decoration: none; cursor: pointer; transition: background-color 120ms var(--ease); }
.seg-seek:hover { background: color-mix(in oklch, var(--accent) 22%, transparent); }
.seg-seek .tabler-icon { --icon-size: 11px; align-self: center; }
.seg-unverified { padding: 0 2px; border-radius: 3px; color: var(--warn); background: var(--warn-soft); cursor: help; }
.seg-unknown { color: var(--ink-3); cursor: help; }
</style>
