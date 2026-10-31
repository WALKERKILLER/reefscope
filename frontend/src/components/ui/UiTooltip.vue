<template>
  <TooltipRoot>
    <TooltipTrigger as-child><slot /></TooltipTrigger>
    <TooltipPortal>
      <TooltipContent class="ui-tooltip" :side="side" :side-offset="6">
        {{ text }}<span v-if="shortcut" class="kbd">{{ shortcut }}</span>
      </TooltipContent>
    </TooltipPortal>
  </TooltipRoot>
</template>

<script setup>
import { TooltipRoot, TooltipTrigger, TooltipPortal, TooltipContent } from 'reka-ui'
defineProps({ text: { type: String, required: true }, shortcut: String, side: { type: String, default: 'bottom' } })
</script>
