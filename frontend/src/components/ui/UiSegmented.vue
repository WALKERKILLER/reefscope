<template>
  <ToggleGroupRoot type="single" :model-value="modelValue" @update:model-value="update" class="ui-seg" :class="{ 'ui-seg-block': block }" :aria-label="ariaLabel" :disabled="disabled">
    <ToggleGroupItem v-for="option in options" :key="String(option.value)" :value="option.value" class="ui-seg-item" :disabled="option.disabled">{{ option.label }}</ToggleGroupItem>
  </ToggleGroupRoot>
</template>

<script setup>
import { ToggleGroupRoot, ToggleGroupItem } from 'reka-ui'
defineProps({ modelValue: [String, Number], options: { type: Array, default: () => [] }, ariaLabel: String, block: Boolean, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
// A segmented control always keeps one value; ignore the toggle-off event.
function update(value) { if (value !== undefined && value !== '') emit('update:modelValue', value) }
</script>
