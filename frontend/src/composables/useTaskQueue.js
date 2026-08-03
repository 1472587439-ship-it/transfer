import { computed, reactive, ref } from 'vue'

/**
 * 任务队列 composable
 *
 * 行为约定：
 *  - 每个任务属于一个 "店铺" (key)；同一店铺的任务严格按入队顺序串行执行
 *  - 不同店铺之间互不阻塞（可并行）
 *  - 任务可以是 async function；执行中产生的异常被捕获并通过 status='fail' 记录
 *  - UI 通过 reactive.queues[shopKey] 实时观察每个店铺的进行中/等待/失败任务
 *  - 全局 hasRunning 表示是否还有任务在跑，用于显示/隐藏状态栏
 *
 * 队列状态机：
 *   waiting  -> running -> success
 *           \-> running -> fail
 */
export function useTaskQueue() {
  /** queues[shopKey] = { running: Task|null, waiting: Task[], recent: Task[] } */
  const queues = reactive({})

  /** task 内部对象 */
  function createTask(shopKey, label, run, meta = {}) {
    return {
      id: `t_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      shopKey,
      label,
      run,
      status: 'waiting', // waiting | running | success | fail
      startedAt: null,
      finishedAt: null,
      error: null,
      meta,
    }
  }

  function ensureQueue(shopKey) {
    if (!queues[shopKey]) {
      // 用 Vue reactive 包装一下，让新增 key 也能被追踪
      queues[shopKey] = reactive({
        running: null,
        waiting: [],
        recent: [], // 最近 5 条已完成任务（status=success/fail），用于 UI 展示
      })
    }
    return queues[shopKey]
  }

  /**
   * 入队一个新任务
   * @param {string} shopKey  店铺标识（用于分组串行）
   * @param {string} label    任务显示名称，如 "上架 BCS-xxx"
   * @param {Function} run    实际要执行的 async 函数
   * @param {Object} meta     任意元数据，会被复制到 task 上
   * @returns {Promise}      resolve 当任务执行完成（成功或失败均会 resolve；失败通过 task.error 体现）
   */
  function enqueue(shopKey, label, run, meta = {}) {
    shopKey = String(shopKey || '__default__')
    const q = ensureQueue(shopKey)
    const task = createTask(shopKey, label, run, meta)
    q.waiting.push(task)
    return new Promise((resolve) => {
      task._resolve = resolve
      pump(shopKey)
    })
  }

  /**
   * 立即从队列中移除一个 waiting 任务（用户取消等场景）
   * 仅能取消还没开始执行的。
   */
  function cancel(shopKey, taskId) {
    shopKey = String(shopKey || '__default__')
    const q = queues[shopKey]
    if (!q) return false
    const idx = q.waiting.findIndex((t) => t.id === taskId)
    if (idx >= 0) {
      const t = q.waiting.splice(idx, 1)[0]
      t.status = 'cancelled'
      t._resolve?.()
      return true
    }
    return false
  }

  function pump(shopKey) {
    const q = queues[shopKey]
    if (!q) return
    if (q.running) return           // 同店铺已有任务在跑
    const next = q.waiting.shift()
    if (!next) return               // 没排队了
    q.running = next
    next.status = 'running'
    next.startedAt = Date.now()
    // 让浏览器有机会先渲染 UI（特别是首次入队时立刻能看见状态栏）
    setTimeout(async () => {
      try {
        await next.run(next)
        next.status = 'success'
        next.finishedAt = Date.now()
      } catch (e) {
        next.status = 'fail'
        next.error = e?.message || String(e)
        next.finishedAt = Date.now()
        // 异常仍 resolve，让上层不阻塞后续任务
      } finally {
        q.recent.unshift(next)
        if (q.recent.length > 5) q.recent.pop()
        q.running = null
        const resolveFn = next._resolve
        next._resolve = null
        // 触发下一任务
        pump(shopKey)
        resolveFn?.(next)
      }
    }, 0)
  }

  /** 给定店铺当前是否有任务在进行（running 或 waiting） */
  function isShopBusy(shopKey) {
    shopKey = String(shopKey || '__default__')
    const q = queues[shopKey]
    if (!q) return false
    return !!q.running || q.waiting.length > 0
  }

  /** 全局是否有任意任务在跑或排队 */
  const hasRunning = computed(() => {
    return Object.values(queues).some((q) => q.running || q.waiting.length > 0)
  })

  /** 全部店铺的"待执行 + 进行中"任务总数（用于 UI 计数） */
  const pendingCount = computed(() => {
    let n = 0
    for (const q of Object.values(queues)) {
      if (q.running) n++
      n += q.waiting.length
    }
    return n
  })

  /** 列出所有店铺的实时状态（用于状态栏 UI） */
  const shopSummaries = computed(() => {
    const out = []
    for (const [shopKey, q] of Object.entries(queues)) {
      if (!q.running && q.waiting.length === 0 && q.recent.length === 0) continue
      const last = q.recent[0]
      out.push({
        shopKey,
        running: q.running,
        waiting: q.waiting,
        waitingCount: q.waiting.length,
        recent: q.recent,
        lastFailed: last?.status === 'fail',
        lastSuccess: last?.status === 'success',
      })
    }
    // 正在跑的优先；然后按最近活动时间
    out.sort((a, b) => {
      const aRun = a.running ? 1 : 0
      const bRun = b.running ? 1 : 0
      if (aRun !== bRun) return bRun - aRun
      const at = a.running?.startedAt || a.recent[0]?.finishedAt || 0
      const bt = b.running?.startedAt || b.recent[0]?.finishedAt || 0
      return bt - at
    })
    return out
  })

  return {
    queues,
    enqueue,
    cancel,
    isShopBusy,
    hasRunning,
    pendingCount,
    shopSummaries,
  }
}