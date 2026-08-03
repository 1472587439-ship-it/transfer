import { computed, ref } from 'vue'
import { wbApi } from '../api/wb.js'
import { extractSkuList } from '../utils/cards.js'

export function useCards({ showToast, pushLog }) {
  const cards = ref([])
  const stocksBySku = ref({})
  const cardsLoading = ref(false)
  const cardsError = ref('')
  const cardsSearch = ref('')
  const cardsLimit = ref(1000)
  const cardsPage = ref(1)
  const cardsPageSize = ref(20)

  const filteredCards = computed(() => {
    const keyword = cardsSearch.value.trim().toLowerCase()
    const list = cards.value.map((card, index) => ({
      ...card,
      __rowBarcode: extractSkuList(card)[0] || '-',
    }))
    if (!keyword) return list
    return list.filter((card) => {
      return [card.vendorCode, card.title, String(card.nmID ?? ''), String(card.subjectID ?? ''), card.__rowBarcode]
        .join(' ')
        .toLowerCase()
        .includes(keyword)
    })
  })

  const totalPages = computed(() => Math.max(1, Math.ceil(filteredCards.value.length / cardsPageSize.value)))
  const pagedCards = computed(() => {
    const start = (cardsPage.value - 1) * cardsPageSize.value
    return filteredCards.value.slice(start, start + cardsPageSize.value)
  })
  const cardsMeta = computed(() => ({ total: cards.value.length, showing: filteredCards.value.length }))

  function goToCardsPage(page) {
    cardsPage.value = Math.min(Math.max(1, page), totalPages.value)
  }

  function refreshCardsPage() {
    if (cardsPage.value > totalPages.value) cardsPage.value = totalPages.value
  }

  async function loadCards() {
    cardsLoading.value = true
    cardsError.value = ''
    try {
      if (!wbApi.hasApiKey()) {
        cardsError.value = '当前店铺未设置有效 API Token，请先在店铺管理中保存 Token'
        showToast('err', cardsError.value)
        pushLog('err', cardsError.value)
        return
      }
      const cardsRes = await wbApi.getCardsList(cardsLimit.value)
      if (!cardsRes.success) {
        cardsError.value = cardsRes.message || '获取商品列表失败'
        showToast('err', cardsError.value)
        pushLog('err', cardsError.value)
        return
      }
      cards.value = Array.isArray(cardsRes.data) ? cardsRes.data : []
      const nmIds = cards.value.map((card) => Number(card.nmID)).filter((id) => id > 0)
      if (nmIds.length) {
        const priceRes = await wbApi.queryPrices(nmIds)
        if (priceRes.success) {
          const priceBody = priceRes.data || {}
          const rows = Array.isArray(priceBody)
            ? priceBody
            : Array.isArray(priceBody.listGoods)
              ? priceBody.listGoods
              : Array.isArray(priceBody.data?.listGoods)
                ? priceBody.data.listGoods
                : Array.isArray(priceBody.data)
                  ? priceBody.data
                  : []
          const pricesByNmId = new Map()
          rows.forEach((row) => {
            const priceRow = Array.isArray(row.sizes) && row.sizes.length
              ? { ...row, ...row.sizes[0] }
              : row
            const id = priceRow.nmID ?? priceRow.nmId ?? row.nmID ?? row.nmId
            if (id != null) pricesByNmId.set(String(id), priceRow)
          })
          cards.value = cards.value.map((card) => ({ ...card, __priceInfo: pricesByNmId.get(String(card.nmID)) || null }))
          pushLog('ok', `商品价格已加载：请求 ${nmIds.length} 个，返回 ${pricesByNmId.size} 个`)
        } else {
          pushLog('warn', `商品价格查询失败：${priceRes.message || '未知错误'}`)
        }
      }
      cardsPage.value = 1
      cards.value = cards.value.map((card) => ({
        ...card,
        __rowBarcode: extractSkuList(card)[0] || '-',
      }))
      const skus = cards.value.flatMap((card) => extractSkuList(card))
      const stocksRes = skus.length ? await wbApi.getWarehouseStocks(skus).catch(() => ({ success: false, data: {} })) : null
      if (stocksRes?.success && stocksRes.data) {
        const source = stocksRes.data.data || stocksRes.data
        stocksBySku.value = source && typeof source === 'object' ? source : {}
      } else {
        stocksBySku.value = {}
      }
      showToast('ok', `已加载 ${cards.value.length} 个商品`)
      pushLog('ok', `商品列表已加载，共 ${cards.value.length} 个`)
    } catch (e) {
      cardsError.value = e.message
      showToast('err', e.message)
      pushLog('err', e.message)
    } finally {
      cardsLoading.value = false
    }
  }

  return {
    cards,
    stocksBySku,
    cardsLoading,
    cardsError,
    cardsSearch,
    cardsLimit,
    cardsPage,
    cardsPageSize,
    filteredCards,
    totalPages,
    pagedCards,
    cardsMeta,
    goToCardsPage,
    refreshCardsPage,
    loadCards,
  }
}
