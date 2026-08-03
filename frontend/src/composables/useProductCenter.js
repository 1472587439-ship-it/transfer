import { computed, reactive, ref } from 'vue'
import { wbApi, POLL_INTERVAL_MS } from '../api/wb.js'

/**
 * 商品中心 composable
 * - 通过 /api/output/page 拉取分页数据
 * - 通过 /api/output/poll 长轮询，自动感知 output 文件夹变更
 * - 上架成功后调用 /api/output/mark 给对应 JSON 商品打 hit=1
 */
export function useProductCenter({ showToast, pushLog }) {
  const items = ref([])            // 当前页商品
  const total = ref(0)
  const page = ref(1)
  const size = ref(10)
  const totalPages = ref(1)
  const loading = ref(false)
  const polling = ref(false)
  const lastServerTime = ref(0)
  const selectedIds = ref(new Set())
  const inlineDiscountMap = ref(new Map()) // sourceRef -> discount%(0~100)
  const batchMultiplierMap = ref(new Map()) // sourceRef -> price 倍数
  const batchStockMap = ref(new Map())      // sourceRef -> 上架后库存件数
  const stockChrtMap = ref(new Map())       // sourceRef -> { chrtId, nmID } 上架后回填
  const shopName = ref('')                  // 当前店铺名，供 loadPage 过滤用
  /**
   * frozenRefs：已进入任务队列（waiting 或 running）的商品 sourceRef 集合。
   * 一旦进入，勾选框会被禁用，并且其倍数/折扣/库存不会被后续"应用于选中"覆盖。
   * 取消队列任务后会从集合中移除。
   */
  const frozenRefs = ref(new Set())

  let pollTimer = null
  let pollAbort = null

  async function loadPage(targetPage = page.value) {
    if (targetPage < 1) targetPage = 1
    if (targetPage > totalPages.value && totalPages.value > 0) targetPage = totalPages.value
    loading.value = true
    try {
      const res = await wbApi.pageOutput(targetPage, size.value, shopName.value)
      if (!res.success) {
        pushLog('warn', res.message || '加载商品中心失败')
        return
      }
      const data = res.data || {}
      items.value = Array.isArray(data.items) ? data.items : []
      total.value = data.total || 0
      page.value = data.page || 1
      totalPages.value = data.totalPages || 1
      // 清理已不存在的选中
      const currentIds = new Set(items.value.map((it) => it.sourceRef))
      for (const id of [...selectedIds.value]) {
        if (!currentIds.has(id)) selectedIds.value.delete(id)
      }
    } catch (e) {
      pushLog('err', '加载商品中心失败：' + e.message)
    } finally {
      loading.value = false
    }
  }

  async function refresh() {
    await loadPage(1)
  }

  function goPage(p) {
    if (p < 1 || p > totalPages.value) return
    loadPage(p)
  }

  /**
   * 开始长轮询，后台不断检查 output 文件夹是否有新内容
   */
  function startPolling() {
    if (polling.value) return
    polling.value = true
    const tick = async () => {
      if (!polling.value) return
      try {
        pollAbort = new AbortController()
        const res = await wbApi.pollOutput(lastServerTime.value)
        if (res.success && res.data) {
          lastServerTime.value = res.data.serverTime || Date.now()
          if (res.data.changed > 0) {
            pushLog('ok', `output 文件夹有 ${res.data.changed} 个变更，重新加载商品中心`)
            await loadPage(page.value)
          }
        }
      } catch (e) {
        // 静默失败，继续轮询
      }
      if (polling.value) {
        pollTimer = setTimeout(tick, POLL_INTERVAL_MS)
      }
    }
    tick()
  }

  function stopPolling() {
    polling.value = false
    if (pollTimer) clearTimeout(pollTimer)
    pollTimer = null
    if (pollAbort) pollAbort.abort()
    pollAbort = null
  }

  /**
   * 标记某个商品已在指定店铺上架（在 hit 列表中追加店铺名）
   */
  async function markHit(item, shopName) {
    if (!item || !item.sourceRef) return false
    try {
      const res = await wbApi.markOutputHit(item.sourceRef, shopName || '')
      if (res.success) {
        pushLog('ok', `已标记：${item.sourceRef}`)
        // 从当前列表移除
        items.value = items.value.filter((it) => it.sourceRef !== item.sourceRef)
        // 总数减 1
        total.value = Math.max(0, total.value - 1)
        // 选中清理
        selectedIds.value.delete(item.sourceRef)
        // 如果当前页空了且还有下一页，自动加载下一页
        if (items.value.length === 0 && page.value < totalPages.value) {
          await loadPage(page.value)
        } else if (items.value.length === 0 && page.value > 1 && total.value === 0) {
          page.value = 1
        } else {
          // 重新计算 totalPages（可能减页）
          totalPages.value = Math.max(1, Math.ceil(total.value / size.value))
        }
        return true
      } else {
        pushLog('warn', '标记失败：' + (res.message || ''))
        return false
      }
    } catch (e) {
      pushLog('err', '标记失败：' + e.message)
      return false
    }
  }

  function toggleSelect(item) {
    if (!item?.sourceRef) return
    if (frozenRefs.value.has(item.sourceRef)) return  // 冻结中，不允许切换勾选
    if (selectedIds.value.has(item.sourceRef)) selectedIds.value.delete(item.sourceRef)
    else selectedIds.value.add(item.sourceRef)
  }

  function selectAllOnPage(value) {
    items.value.forEach((it) => {
      if (frozenRefs.value.has(it.sourceRef)) return  // 全选时跳过冻结中的
      if (value) selectedIds.value.add(it.sourceRef)
      else selectedIds.value.delete(it.sourceRef)
    })
  }

  function isSelected(item) {
    return selectedIds.value.has(item?.sourceRef)
  }

  /** 判断某商品是否处于"上架队列中"（waiting 或 running） */
  function isFrozen(item) {
    return frozenRefs.value.has(item?.sourceRef)
  }

  /** 标记 sourceRef 为冻结：进入任务队列时调用 */
  function freeze(sourceRef) {
    if (!sourceRef) return
    if (!frozenRefs.value.has(sourceRef)) {
      frozenRefs.value.add(sourceRef)
      // 触发响应式更新（Set 本身已是 reactive，但其变更需要触发 effect）
      frozenRefs.value = new Set(frozenRefs.value)
    }
  }

  /** 解除冻结：任务完成/失败/被取消后调用 */
  function unfreeze(sourceRef) {
    if (!sourceRef) return
    if (frozenRefs.value.has(sourceRef)) {
      frozenRefs.value.delete(sourceRef)
      frozenRefs.value = new Set(frozenRefs.value)
    }
  }

  // ====== 折扣配置弹窗 ======
  const editTarget = ref(null)        // 当前正在编辑的商品
  const editDiscount = ref(0)         // 0~100
  const editSaving = ref(false)

  /**
   * 打开折扣编辑弹窗
   * 优先使用已就地填的折扣（inlineDiscountMap），否则默认 0
   */
  function openEdit(item) {
    editTarget.value = item
    const inline = inlineDiscountMap.value.get(item.sourceRef)
    editDiscount.value = inline != null ? inline : 0
  }

  function closeEdit() {
    editTarget.value = null
    editDiscount.value = 0
    editSaving.value = false
  }

  /**
   * 提交折扣：调用后端 /api/wb/prices
   * 需要外部把弹窗里填的折扣落地到 inlineDiscountMap，前端立即看到现价
   */
  function applyDiscountToItem(item, discount) {
    if (!item) return
    inlineDiscountMap.value.set(item.sourceRef, Math.max(0, Math.min(100, Number(discount) || 0)))
  }

  function getMultiplier(item) {
    return batchMultiplierMap.value.get(item.sourceRef) ?? 1
  }

  function getStock(item) {
    return batchStockMap.value.get(item.sourceRef) ?? 0
  }

  /**
   * 挂牌价 = 原价 × 倍数
   */
  function getListedPrice(item) {
    const base = Number(item?.price) || 0
    const mult = getMultiplier(item)
    return Math.round(base * mult)
  }

  /**
   * 折后价 = 挂牌价 × (100 - 折扣)/100
   * 倍数和折扣均来源于全局批量设置 + 行内折扣
   */
  function getEffectivePrice(item) {
    const listed = getListedPrice(item)
    const discount = inlineDiscountMap.value.get(item.sourceRef) ?? 0
    return Math.round(listed * (100 - Math.max(0, Math.min(100, discount))) * 100) / 10000
  }

  function computedSalePrice(item) {
    return getEffectivePrice(item)
  }

  /**
   * 批量上架辅助：返回当前页所有 selectedIds 对应的 items 列表
   */
  function selectedItems() {
    return items.value.filter((it) => selectedIds.value.has(it.sourceRef))
  }

  /**
   * 挂牌价 = 原价 × 倍数
   */
  function getListedPrice(item) {
    const base = Number(item?.price) || 0
    const mult = getMultiplier(item)
    return Math.round(base * mult)
  }

  /**
   * 折后价 = 挂牌价 × (100 - 折扣)/100
   * 倍数和折扣均来源于全局批量设置 + 行内折扣
   */
  function getEffectivePrice(item) {
    const listed = getListedPrice(item)
    const discount = inlineDiscountMap.value.get(item.sourceRef) ?? 0
    return Math.round(listed * (100 - Math.max(0, Math.min(100, discount))) * 100) / 10000
  }

  function recordStock(item, chrtId, nmID) {
    if (!item || !chrtId) return
    stockChrtMap.value.set(item.sourceRef, { chrtId: Number(chrtId), nmID: Number(nmID) || 0 })
  }

  function getStockChrt(item) {
    return stockChrtMap.value.get(item.sourceRef) || null
  }

  return {
    items,
    total,
    page,
    size,
    totalPages,
    loading,
    polling,
    selectedIds,
    frozenRefs,
    inlineDiscountMap,
    batchMultiplierMap,
    batchStockMap,
    stockChrtMap,
    editTarget,
    editDiscount,
    editSaving,
    loadPage,
    refresh,
    goPage,
    startPolling,
    stopPolling,
    markHit,
    toggleSelect,
    selectAllOnPage,
    isSelected,
    isFrozen,
    freeze,
    unfreeze,
    openEdit,
    closeEdit,
    applyDiscountToItem,
    computedSalePrice,
    selectedItems,
    getMultiplier,
    getStock,
    getListedPrice,
    getEffectivePrice,
    recordStock,
    getStockChrt,
    shopName,
  }
}