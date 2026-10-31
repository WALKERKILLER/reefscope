<template>
  <SliderRoot :model-value="[modelValue]" @update:model-value="value => emit('update:modelValue', value[0])" :min="min" :max="max" :step="step" class="ui-slider">
    <SliderTrack class="ui-slider-track"><SliderRange class="ui-slider-range" /></SliderTrack>
    <SliderThumb class="ui-slider-thumb" :aria-label="ariaLabel" />
  </SliderRoot>
</template>

<script setup>
import { SliderRoot, SliderTrack, SliderRange, SliderThumb } from 'reka-ui'
defineProps({ modelValue: { type: Number, default: 0 }, min: { type: Number, default: 0 }, max: { type: Number, default: 1 }, step: { type: Number, default: 0.01 }, ariaLabel: String })
const emit = defineEmits(['update:modelValue'])
</script>
