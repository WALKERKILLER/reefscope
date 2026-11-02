<template>
  <section class="wall-panel" :aria-labelledby="id">
    <header class="panel-head">
      <span class="code mono" aria-hidden="true">{{ code }}</span>
      <h3 :id="id">{{ title }}</h3>
      <span v-if="meta || $slots.meta" class="meta"><slot name="meta">{{ meta }}</slot></span>
    </header>
    <div class="panel-body"><slot /></div>
  </section>
</template>

<script setup>
const props = defineProps({ code: { type: String, required: true }, title: { type: String, required: true }, meta: String })
const id = `wall-panel-${props.code.toLowerCase()}`
</script>

<style scoped>
/* Corner ticks mark each panel's extent without drawing a full frame, as on control-room walls. */
.wall-panel {
  --tick: color-mix(in oklch, var(--accent) 55%, transparent);
  position: relative; display: flex; flex-direction: column; min-height: 0; min-width: 0;
  border-radius: var(--radius); background: var(--surface); box-shadow: 0 0 0 1px var(--line);
  background-image:
    linear-gradient(var(--tick), var(--tick)), linear-gradient(var(--tick), var(--tick)),
    linear-gradient(var(--tick), var(--tick)), linear-gradient(var(--tick), var(--tick));
  background-size: 10px 1px, 1px 10px, 10px 1px, 1px 10px;
  background-position: top left, top left, bottom right, bottom right;
  background-repeat: no-repeat;
}
.panel-head { display: flex; align-items: center; gap: 8px; height: 32px; flex: none; padding: 0 12px; box-shadow: inset 0 -1px 0 var(--line); white-space: nowrap; }
.code { flex: none; font-size: 10.5px; font-weight: 600; letter-spacing: 0.04em; color: var(--accent); }
h3 { min-width: 0; overflow: hidden; text-overflow: ellipsis; font-size: var(--text-small); font-weight: 600; color: var(--ink); }
.meta { display: inline-flex; align-items: center; gap: 6px; min-width: 0; margin-inline-start: auto; overflow: hidden; text-overflow: ellipsis; font-size: var(--text-caption); color: var(--ink-3); }
.panel-body { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 10px 12px; }
</style>
