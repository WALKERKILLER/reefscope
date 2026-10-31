<template>
  <SwitchRoot :id="id" :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" :disabled="disabled" class="ui-switch">
    <SwitchThumb class="ui-switch-thumb" />
  </SwitchRoot>
</template>

<script setup>
import { SwitchRoot, SwitchThumb } from 'reka-ui'
defineProps({ modelValue: Boolean, disabled: Boolean, id: String })
const emit = defineEmits(['update:modelValue'])
</script>
