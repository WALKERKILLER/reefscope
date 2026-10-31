<template>
  <TabsRoot :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" class="ui-tabs" :unmount-on-hide="false">
    <TabsList class="ui-tabs-list" :aria-label="ariaLabel">
      <TabsTrigger v-for="item in items" :key="item.value" :value="item.value" class="ui-tab">
        {{ item.label }}<span v-if="item.badge != null" class="ui-tab-badge tnum">{{ item.badge }}</span>
      </TabsTrigger>
      <TabsIndicator class="ui-tabs-indicator" />
    </TabsList>
    <TabsContent v-for="item in items" :key="item.value" :value="item.value" class="ui-tab-panel">
      <slot :name="item.value" />
    </TabsContent>
  </TabsRoot>
</template>

<script setup>
import { TabsRoot, TabsList, TabsTrigger, TabsIndicator, TabsContent } from 'reka-ui'
defineProps({ modelValue: String, items: { type: Array, default: () => [] }, ariaLabel: String })
const emit = defineEmits(['update:modelValue'])
</script>
