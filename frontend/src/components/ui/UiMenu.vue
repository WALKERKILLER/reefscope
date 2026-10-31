<template>
  <DropdownMenuRoot :modal="false">
    <DropdownMenuTrigger as-child><slot /></DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent class="ui-popover ui-menu" :side-offset="4" :align="align">
        <template v-for="(item, index) in items" :key="item.key || index">
          <DropdownMenuSeparator v-if="item.separator" class="ui-menu-separator" />
          <DropdownMenuItem v-else class="ui-option" :class="{ 'ui-option-danger': item.danger }" :disabled="item.disabled" @select="emit('select', item)">
            <component :is="item.icon" v-if="item.icon" />
            <span>{{ item.label }}</span>
          </DropdownMenuItem>
        </template>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>

<script setup>
import { DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuPortal, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from 'reka-ui'
defineProps({ items: { type: Array, default: () => [] }, align: { type: String, default: 'end' } })
const emit = defineEmits(['select'])
</script>
