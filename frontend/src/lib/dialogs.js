import { shallowRef } from 'vue'

// One modal at a time. Each call resolves when the reader confirms, cancels, or presses Escape.
export const activeDialog = shallowRef(null)

function open(kind, options) {
  activeDialog.value?.resolve(kind === 'confirm' ? false : null)
  return new Promise(resolve => { activeDialog.value = { kind, ...options, resolve } })
}

export const confirmDialog = options => open('confirm', options)
export const promptDialog = options => open('prompt', options)

export function settleDialog(value) {
  const dialog = activeDialog.value
  activeDialog.value = null
  dialog?.resolve(value)
}
