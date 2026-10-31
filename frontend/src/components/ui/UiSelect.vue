<template>
  <SelectRoot :model-value="inner" @update:model-value="update" :disabled="disabled">
    <SelectTrigger class="ui-select" :aria-label="ariaLabel" :id="id">
      <SelectValue :placeholder="placeholder" class="ui-select-value" />
      <IconSelector class="ui-select-icon" />
    </SelectTrigger>
    <SelectPortal>
      <SelectContent class="ui-popover ui-select-content" position="popper" :side-offset="4" align="start">
        <SelectViewport class="ui-select-viewport">
          <SelectItem v-for="option in options" :key="String(option.value)" :value="encode(option.value)" :disabled="option.disabled" class="ui-option">
            <SelectItemText>{{ option.label }}</SelectItemText>
            <span v-if="option.hint" class="ui-option-hint">{{ option.hint }}</span>
            <SelectItemIndicator class="ui-option-check"><IconCheck /></SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>

<script setup>
import { computed } from 'vue'
import { SelectRoot, SelectTrigger, SelectValue, SelectPortal, SelectContent, SelectViewport, SelectItem, SelectItemText, SelectItemIndicator } from 'reka-ui'
import { IconCheck, IconSelector } from '@tabler/icons-vue'

// Reka reserves '' for "no selection", so an empty option value travels as a sentinel.
const EMPTY = '__empty__'
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '选择' },
  disabled: Boolean,
  ariaLabel: String,
  id: String
})
const emit = defineEmits(['update:modelValue'])
const encode = value => value === '' || value == null ? EMPTY : String(value)
const inner = computed(() => props.options.some(o => encode(o.value) === encode(props.modelValue)) ? encode(props.modelValue) : undefined)
function update(value) {
  const option = props.options.find(o => encode(o.value) === value)
  if (option) emit('update:modelValue', option.value)
}
</script>
