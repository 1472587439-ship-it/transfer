import { reactive, ref } from 'vue'

export function useToast() {
  const loading = ref(false)
  const toast = reactive({ show: false, type: 'ok', text: '' })
  const logs = ref([])

  function showToast(type, text) {
    toast.type = type
    toast.text = text
    toast.show = true
    window.clearTimeout(showToast._t)
    showToast._t = window.setTimeout(() => {
      toast.show = false
    }, 4000)
  }

  function pushLog(type, text) {
    const time = new Date().toLocaleTimeString()
    logs.value.unshift({ type, text, time })
    if (logs.value.length > 40) logs.value.pop()
  }

  return { loading, toast, logs, showToast, pushLog }
}
