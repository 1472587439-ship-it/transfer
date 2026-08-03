<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  /** useTaskQueue 返回的 shopSummaries */
  summaries: { type: Array, default: () => [] },
  /** 全局 pendingCount */
  pendingCount: { type: Number, default: 0 },
})

const emit = defineEmits(['cancel-task'])

const collapsed = ref(false)

const headerText = computed(() => {
  const total = props.pendingCount
  if (total === 0) return '任务队列空闲'
  return `正在处理 ${total} 个任务（按店铺串行）`
})

function elapsedSince(t) {
  if (!t) return ''
  const ms = Date.now() - t
  if (ms < 1000) return '刚刚'
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s`
  return `${Math.floor(ms / 60_000)}m${Math.floor((ms % 60_000) / 1000)}s`
}

function statusText(t) {
  if (t.status === 'waiting') return `排队中…`
  if (t.status === 'running') return `执行中（已用 ${elapsedSince(t.startedAt)}）`
  if (t.status === 'success') return `✅ 完成（${elapsedSince(t.finishedAt)} 前）`
  if (t.status === 'fail') return `❌ 失败：${t.error}`
  if (t.status === 'cancelled') return `已取消`
  return ''
}
</script>

<template>
  <Transition name="status-bar">
    <div v-if="summaries.length" class="status-bar" :class="{ collapsed }">
      <div class="status-bar-head" @click="collapsed = !collapsed">
        <span class="dot" />
        <span class="title">{{ headerText }}</span>
        <span class="summary-tags">
          <span
            v-for="s in summaries"
            :key="s.shopKey"
            class="shop-tag"
            :class="{ active: !!s.running, warn: s.lastFailed }"
          >
            {{ s.shopKey }}
            <template v-if="s.running">· 1</template>
            <template v-else-if="s.waitingCount">· {{ s.waitingCount }}</template>
          </span>
        </span>
        <span class="toggle">{{ collapsed ? '展开' : '收起' }}</span>
      </div>

      <div v-if="!collapsed" class="status-bar-body">
        <div v-for="s in summaries" :key="s.shopKey" class="shop-row">
          <div class="shop-row-head">
            <span class="shop-name">🏪 {{ s.shopKey }}</span>
            <span class="shop-meta">
              <template v-if="s.running">执行中 1 · 排队 {{ s.waitingCount }}</template>
              <template v-else-if="s.waitingCount">排队 {{ s.waitingCount }}</template>
              <template v-else>空闲</template>
            </span>
          </div>

          <!-- 当前正在跑的任务 -->
          <div v-if="s.running" class="task task-running">
            <span class="spinner-mini" />
            <span class="task-label">{{ s.running.label }}</span>
            <span class="task-status">{{ statusText(s.running) }}</span>
          </div>

          <!-- 等待中的任务（最多展示 5 条，剩下的折叠） -->
          <div v-if="s.waiting.length" class="waiting-list">
            <div v-for="t in s.waiting.slice(0, 5)" :key="t.id" class="task task-waiting">
              <span class="task-label">⏳ {{ t.label }}</span>
              <button type="button" class="btn-mini" @click.stop="emit('cancel-task', t)">取消</button>
            </div>
            <div v-if="s.waiting.length > 5" class="more">还有 {{ s.waiting.length - 5 }} 个等待中…</div>
          </div>

          <!-- 最近已完成（点击展开看日志） -->
          <details v-if="s.recent.length" class="recent">
            <summary>最近完成 {{ s.recent.length }} 条</summary>
            <ul>
              <li v-for="t in s.recent" :key="t.id" :class="t.status">
                <span class="task-label">{{ t.label }}</span>
                <span class="task-status">{{ statusText(t) }}</span>
              </li>
            </ul>
          </details>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.status-bar {
  position: fixed;
  right: 16px;
  bottom: 16px;
  width: 360px;
  max-width: calc(100vw - 32px);
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
  z-index: 95; /* 低于 modal (9999)，高于 content (auto) */
  font-size: 13px;
  color: #0f172a;
  overflow: hidden;
}

.status-bar-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  cursor: pointer;
  user-select: none;
}

.status-bar-head .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.15);
  animation: pulse 1.6s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.15); }
  50%      { box-shadow: 0 0 0 6px rgba(22, 163, 74, 0.05); }
}

.status-bar-head .title {
  font-weight: 700;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-bar-head .toggle {
  color: #64748b;
  font-size: 12px;
}

.summary-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.shop-tag {
  background: #e2e8f0;
  color: #475569;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
}
.shop-tag.active { background: #dbeafe; color: #1677ff; }
.shop-tag.warn   { background: #fee2e2; color: #b91c1c; }

.status-bar-body {
  max-height: 50vh;
  overflow: auto;
  padding: 6px 12px 12px;
}

.shop-row {
  border-top: 1px dashed #e2e8f0;
  padding: 8px 0;
}
.shop-row:first-child { border-top: none; }

.shop-row-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #475569;
  margin-bottom: 6px;
}
.shop-row-head .shop-name {
  font-weight: 700;
  color: #0f172a;
}
.shop-row-head .shop-meta { color: #64748b; }

.task {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 4px;
}
.task-running  { background: #eff6ff; color: #1e40af; }
.task-waiting  { background: #f8fafc; color: #475569; }
.task-status   { margin-left: auto; color: #64748b; font-size: 11px; }
.task-label    { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.task.success .task-status { color: #16a34a; }
.task.fail    .task-status { color: #b91c1c; }

.spinner-mini {
  width: 12px;
  height: 12px;
  border: 2px solid #bfdbfe;
  border-top-color: #1677ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

.waiting-list { display: flex; flex-direction: column; gap: 2px; }
.more { color: #94a3b8; font-size: 11px; padding: 2px 8px; }

.btn-mini {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: pointer;
}
.btn-mini:hover { color: #b91c1c; border-color: #fbc4c4; }

.recent {
  margin-top: 6px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 4px;
  font-size: 11px;
  color: #64748b;
}
.recent summary { cursor: pointer; padding: 2px 0; }
.recent ul { list-style: none; margin: 4px 0 0; padding: 0; }
.recent li { display: flex; justify-content: space-between; padding: 2px 0; gap: 8px; }

.status-bar-enter-active,
.status-bar-leave-active {
  transition: transform 0.2s, opacity 0.2s;
}
.status-bar-enter-from,
.status-bar-leave-to {
  transform: translateY(20px);
  opacity: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>