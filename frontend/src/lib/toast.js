import { shallowRef } from 'vue'

// Transient feedback only; errors that need action stay next to the control that failed.
export const toasts = shallowRef([])
let sequence = 0

export function toast({ title, desc = '', type = 'info', duration = 4000 }) {
  const id = ++sequence
  toasts.value = [...toasts.value, { id, title, desc, type, duration }]
  return id
}

export function dismissToast(id) {
  toasts.value = toasts.value.filter(item => item.id !== id)
}
