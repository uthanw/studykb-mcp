import { ref } from 'vue'

type TaskEvent = 'connect' | 'startTask'
type TaskHandler = (payload?: string) => void

const handlers = ref<Map<TaskEvent, TaskHandler>>(new Map())

export function useTaskBridge() {
  function emit(event: TaskEvent, payload?: string) {
    const handler = handlers.value.get(event)
    handler?.(payload)
  }

  function on(event: TaskEvent, handler: TaskHandler) {
    handlers.value.set(event, handler)
  }

  function off(event: TaskEvent) {
    handlers.value.delete(event)
  }

  return { emit, on, off }
}
