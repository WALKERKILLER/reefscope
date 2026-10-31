<template>
  <AlertDialogRoot :open="dialog?.kind === 'confirm'" @update:open="open => !open && settle(false)">
    <AlertDialogPortal>
      <AlertDialogOverlay class="ui-overlay" />
      <AlertDialogContent v-if="dialog?.kind === 'confirm'" class="ui-dialog">
        <AlertDialogTitle class="ui-dialog-title">{{ dialog.title }}</AlertDialogTitle>
        <AlertDialogDescription class="ui-dialog-desc" :class="{ 'sr-only': !dialog.description }">{{ dialog.description || '确认后立即执行。' }}</AlertDialogDescription>
        <div class="ui-dialog-actions">
          <AlertDialogCancel class="btn btn-ghost">{{ dialog.cancelLabel || '取消' }}</AlertDialogCancel>
          <button type="button" class="btn" :class="dialog.danger ? 'btn-danger-solid' : 'btn-primary'" @click="settle(true)">{{ dialog.confirmLabel }}</button>
        </div>
      </AlertDialogContent>
    </AlertDialogPortal>
  </AlertDialogRoot>

  <DialogRoot :open="dialog?.kind === 'prompt'" @update:open="open => !open && settle(null)">
    <DialogPortal>
      <DialogOverlay class="ui-overlay" />
      <DialogContent v-if="dialog?.kind === 'prompt'" class="ui-dialog" @open-auto-focus="focusInput">
        <DialogTitle class="ui-dialog-title">{{ dialog.title }}</DialogTitle>
        <DialogDescription class="ui-dialog-desc" :class="{ 'sr-only': !dialog.description }">{{ dialog.description || '按回车确认，按 Esc 取消。' }}</DialogDescription>
        <form class="ui-dialog-form" @submit.prevent="submit">
          <label class="field"><span>{{ dialog.label }}</span><input ref="inputRef" v-model="draft" class="input" :placeholder="dialog.placeholder" required /></label>
          <p v-if="dialog.hint" class="note">{{ dialog.hint }}</p>
          <div class="ui-dialog-actions">
            <DialogClose type="button" class="btn btn-ghost">{{ dialog.cancelLabel || '取消' }}</DialogClose>
            <button class="btn btn-primary" :disabled="!draft.trim()">{{ dialog.confirmLabel }}</button>
          </div>
        </form>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { AlertDialogRoot, AlertDialogPortal, AlertDialogOverlay, AlertDialogContent, AlertDialogTitle, AlertDialogDescription, AlertDialogCancel, DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import { activeDialog, settleDialog } from '../../lib/dialogs'

const dialog = computed(() => activeDialog.value)
const draft = ref('')
const inputRef = ref(null)
watch(dialog, value => { draft.value = value?.value || '' })
function settle(value) { if (activeDialog.value) settleDialog(value) }
function submit() { if (draft.value.trim()) settle(draft.value.trim()) }
function focusInput(event) {
  event.preventDefault()
  inputRef.value?.focus()
  inputRef.value?.select()
}
</script>
