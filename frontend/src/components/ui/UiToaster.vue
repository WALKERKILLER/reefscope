<template>
  <ToastProvider swipe-direction="right">
    <ToastRoot v-for="item in toasts" :key="item.id" :duration="item.duration" class="ui-toast" :data-type="item.type" @update:open="open => !open && dismissToast(item.id)">
      <component :is="icons[item.type] || icons.info" class="ui-toast-icon" />
      <div class="ui-toast-body">
        <ToastTitle class="ui-toast-title">{{ item.title }}</ToastTitle>
        <ToastDescription v-if="item.desc" class="ui-toast-desc">{{ item.desc }}</ToastDescription>
      </div>
      <ToastClose class="btn btn-ghost btn-sm btn-icon" aria-label="关闭通知"><IconX /></ToastClose>
    </ToastRoot>
    <ToastViewport class="ui-toast-viewport" />
  </ToastProvider>
</template>

<script setup>
import { ToastProvider, ToastRoot, ToastTitle, ToastDescription, ToastClose, ToastViewport } from 'reka-ui'
import { IconX, IconInfoCircle, IconCircleCheck, IconAlertTriangle } from '@tabler/icons-vue'
import { toasts, dismissToast } from '../../lib/toast'
const icons = { info: IconInfoCircle, success: IconCircleCheck, warn: IconAlertTriangle, alert: IconAlertTriangle }
</script>
