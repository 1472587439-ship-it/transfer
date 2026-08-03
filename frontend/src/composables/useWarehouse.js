import { computed, ref } from 'vue'
import { wbApi } from '../api/wb.js'
import { extractSkuList, extractChrtIdList } from '../utils/cards.js'

export function useWarehouse({ cards, stocksBySku, loadCards, showToast, pushLog }) {
  const warehouseLoading = ref(false)
  const warehouseError = ref('')
  const warehouseSearch = ref('')
  const warehouseList = ref([])
  const warehouseSelected = ref(null)
  const warehouseStocks = ref([])
  const warehousePage = ref(1)
  const warehousePageSize = ref(20)

  const filteredWarehouses = computed(() => warehouseList.value.filter((item) => JSON.stringify(item).toLowerCase().includes(warehouseSearch.value.trim().toLowerCase())))
  const filteredWarehouseStocks = computed(() => {
    const keyword = warehouseSearch.value.trim().toLowerCase()
    return warehouseStocks.value.filter((item) => !keyword || [item.title, item.sku, item.vendorCode, item.nmID].join(' ').toLowerCase().includes(keyword))
  })
  const warehouseTotalPages = computed(() => Math.max(1, Math.ceil(filteredWarehouseStocks.value.length / warehousePageSize.value)))
  const pagedWarehouseStocks = computed(() => filteredWarehouseStocks.value.slice((warehousePage.value - 1) * warehousePageSize.value, warehousePage.value * warehousePageSize.value))
  function goToWarehousePage(page) { warehousePage.value = Math.min(Math.max(1, page), warehouseTotalPages.value) }
  function refreshWarehousePage() { if (warehousePage.value > warehouseTotalPages.value) warehousePage.value = warehouseTotalPages.value }

  async function loadWarehouses() {
    warehouseLoading.value = true; warehouseError.value = ''
    try {
      if (!wbApi.hasApiKey()) {
        throw new Error('请先在「店铺管理」中手动选择一个店铺')
      }
      const res = await wbApi.getWarehouses()
      if (!res.success || !Array.isArray(res.data)) throw new Error(res.message || '获取仓库列表失败')
      warehouseList.value = res.data
      warehouseSelected.value = res.data[0] || null
      // 关键：如果商品列表（cards）还没拉，主动拉一次
      // 否则 loadWarehouseStocks 拿不到 queryKeys，库存查询永远是空
      if (!Array.isArray(cards.value) || cards.value.length === 0) {
        try {
          pushLog('ok', '商库库存：自动加载商品列表以构建查询 keys…')
          if (typeof loadCards === 'function') {
            await loadCards()
          } else {
            pushLog('warn', '商库库存：loadCards 未注入，跳过自动加载商品列表')
          }
        } catch (e) {
          pushLog('warn', `商库库存：自动加载商品列表失败：${e.message}`)
        }
      }
      await loadWarehouseStocks()
    } catch (e) { warehouseError.value = e.message; pushLog('err', `库存页面加载失败：${e.message}`) } finally { warehouseLoading.value = false }
  }

  async function loadWarehouseStocks() {
    warehouseError.value = ''
    try {
      // 库存写入用的是 chrtId（WB 官方接口也是按 chrtId 索引），
      // 因此查询时优先用 chrtId 列表；barcode 作为兜底。
      const chrtList = cards.value.flatMap((card) => extractChrtIdList(card))
      const skuList = cards.value.flatMap((card) => extractSkuList(card))
      const queryKeys = [...new Set([...chrtList, ...skuList])]
      pushLog('ok', `🔍 商库库存查询：cards=${cards.value.length} 个，chrtId=${chrtList.length} 个，sku=${skuList.length} 个，去重后 keys=${queryKeys.length} 个`)
      if (queryKeys.length === 0) {
        pushLog('warn', '⚠️ 没有可查询的 key（cards 为空或所有卡片都没有 chrtId/sku）')
        warehouseStocks.value = []
        return
      }
      const res = await wbApi.getWarehouseStocksByWarehouse(queryKeys)
      if (!res.success) throw new Error(res.message || '获取库存失败')
      const rows = res.data || []
      const bySku = new Map()
      rows.forEach((warehouse) => Object.entries(warehouse.stocks || {}).forEach(([sku, quantity]) => {
        // 关键：先按 chrtId 查找，因为后端写入的就是 chrtId；找不到再按 barcode
        const matchCard = cards.value.find((card) => extractChrtIdList(card).includes(String(sku)))
          || cards.value.find((card) => extractSkuList(card).includes(String(sku)))
        const row = bySku.get(sku) || {
          sku,
          title: matchCard?.title || '',
          vendorCode: matchCard?.vendorCode || '',
          nmID: matchCard?.nmID || '',
          warehouses: {},
          total: 0,
        }
        row.warehouses[warehouse.warehouseId] = { name: warehouse.warehouseName, quantity: Number(quantity) || 0 }
        row.total += Number(quantity) || 0
        bySku.set(sku, row)
      }))
      warehouseStocks.value = [...bySku.values()]
      stocksBySku.value = Object.fromEntries(warehouseStocks.value.map((row) => [row.sku, row.total]))
      warehousePage.value = 1
    } catch (e) { warehouseStocks.value = []; warehouseError.value = e.message; pushLog('err', `库存查询失败：${e.message}`) }
  }

  return { warehouseLoading, warehouseError, warehouseSearch, warehouseList, warehouseSelected, warehouseStocks, warehousePage, warehousePageSize, filteredWarehouses, filteredWarehouseStocks, warehouseTotalPages, pagedWarehouseStocks, goToWarehousePage, refreshWarehousePage, loadWarehouses, loadWarehouseStocks }
}
