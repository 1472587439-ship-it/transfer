import { computed, reactive, ref, watch } from 'vue'
import { wbApi } from '../api/wb.js'
import { extractSkuList } from '../utils/cards.js'

const STORAGE_KEY = 'wb-admin-shops'

function genId() {
  return Date.now() ^ (Math.random() * 0xFFFFFFFF)
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      return JSON.parse(raw)
    }
  } catch (e) {
    console.warn('加载店铺数据失败', e)
  }
  return []
}

function saveToStorage(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch (e) {
    console.warn('保存店铺数据失败', e)
  }
}

export function useShop({ cards, stocksBySku, showToast, pushLog }) {
  const shopList = ref(loadFromStorage())
  const shopDialog = reactive({
    show: false,
    mode: 'create',
    id: null,
    shopName: '',
    apiKey: '',
  })
  const shopDetail = ref(null)
  const shopCardDetail = ref(null)
  const shopSelectedId = ref(null)
  const shopCardsSearch = ref('')
  const shopCardsPage = ref(1)
  const shopCardsPageSize = ref(10)
  const shopJumpPageInput = ref('')

  const currentApiKey = ref('')
  const currentShopName = ref('')

  const selectedShop = computed(() => shopList.value.find((s) => s.id === shopSelectedId.value) || null)

  let hasInitSelection = false
  watch(shopSelectedId, (id) => {
    const shop = shopList.value.find((s) => String(s.id) === String(id))
    if (shop) {
      currentApiKey.value = shop.apiKey || ''
      currentShopName.value = shop.shopName || ''
      wbApi.setApiKey(currentApiKey.value)
      if (hasInitSelection) {
        showToast('ok', `已切换到店铺：${currentShopName.value}`)
      }
      pushLog('ok', `已切换到店铺：${currentShopName.value}，API 密钥已更新`)
      hasInitSelection = true
    } else {
      currentApiKey.value = ''
      currentShopName.value = ''
      wbApi.setApiKey('')
    }
  })

  watch(shopList, (list) => {
    saveToStorage(list)
  }, { deep: true })

  // 把当前选中店铺的 token 注入到 fetch；不做任何自动选中/切换
  function syncTokenFromList() {
    if (!Array.isArray(shopList.value) || shopList.value.length === 0) {
      wbApi.setApiKey('')
      currentApiKey.value = ''
      currentShopName.value = ''
      return
    }
    const current = shopList.value.find((s) => String(s.id) === String(shopSelectedId.value))
    if (current && current.apiKey) {
      wbApi.setApiKey(String(current.apiKey).trim())
      currentApiKey.value = current.apiKey
      currentShopName.value = current.shopName || ''
    } else {
      // 未选中或选中店铺无 token：清空，由用户去店铺管理手动选择
      wbApi.setApiKey('')
      currentApiKey.value = ''
      currentShopName.value = ''
    }
  }

  const shopFilteredCards = computed(() => {
    const keyword = shopCardsSearch.value.trim().toLowerCase()
    const list = cards.value.map((card) => ({
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

  const shopTotalPages = computed(() => Math.max(1, Math.ceil(shopFilteredCards.value.length / shopCardsPageSize.value)))
  const shopPagedCards = computed(() => {
    const start = (shopCardsPage.value - 1) * shopCardsPageSize.value
    return shopFilteredCards.value.slice(start, start + shopCardsPageSize.value)
  })

  const shopPagerPages = computed(() => {
    const current = shopCardsPage.value
    const total = shopTotalPages.value
    const pages = []
    if (total <= 7) {
      for (let i = 1; i <= total; i++) pages.push({ type: 'page', value: i, label: String(i) })
      return pages
    }
    pages.push({ type: 'page', value: 1, label: '1' })
    if (current > 4) pages.push({ type: 'ellipsis', label: '…' })
    const start = Math.max(2, current - 1)
    const end = Math.min(total - 1, current + 1)
    for (let i = start; i <= end; i++) pages.push({ type: 'page', value: i, label: String(i) })
    if (current < total - 3) pages.push({ type: 'ellipsis', label: '…' })
    pages.push({ type: 'page', value: total, label: String(total) })
    return pages
  })

  function goToShopCardsPage(page) {
    shopCardsPage.value = Math.min(Math.max(1, page), shopTotalPages.value)
    shopJumpPageInput.value = String(shopCardsPage.value)
  }

  function refreshShopCardsPage() {
    if (shopCardsPage.value > shopTotalPages.value) shopCardsPage.value = shopTotalPages.value
  }

  function jumpToShopPage() {
    const target = Number(shopJumpPageInput.value)
    if (!Number.isFinite(target) || target < 1) return
    goToShopCardsPage(target)
  }

  function initDefaultShop() {
    const defaultShop = {
      id: '__default_jinjiang__',
      shopName: '晋江',
      apiKey: 'eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjYwMzAydjEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjMsImVudCI6MSwiZXhwIjoxNzk5OTc0OTgyLCJmb3IiOiJzZWxmIiwiaWQiOiIwMTlmNmIwNS1mYmQ0LTc3MjUtOTZjMy03MWJmOTdkN2Y2MzgiLCJpaWQiOjMxNDQxNzg4MSwib2lkIjoyNTAxNDM2NzMsInMiOjgxNjYyLCJzaWQiOiI4ZDg3YTE1Zi02OTY1LTRmMjMtOGI2ZC02ZmZkMWJkZGZkNjciLCJ0IjpmYWxzZSwidWlkIjozMTQ0MTc4ODF9.0BBOu_OpwhLMaZemdCe3Mo2ZGBSEsuRZJu5B8H-7quFIVwXaB7Ig4YHaETwaN3S-JedlKhxEYtS3uGNFn6fNVA',
      createdAt: new Date().toISOString(),
    }
    // 1) 如果已有同名「晋江」店铺：合并到唯一一条，补回默认 id 和 token
    const sameName = shopList.value.filter((s) => s.shopName === '晋江')
    if (sameName.length) {
      // 把所有「晋江」店铺的字段合并到第一条，再删除其他
      const primary = sameName[0]
      sameName.slice(1).forEach((dup) => {
        Object.entries(dup).forEach(([k, v]) => {
          if ((primary[k] === undefined || primary[k] === null || primary[k] === '') && v) primary[k] = v
        })
      })
      primary.id = defaultShop.id
      if (!primary.apiKey) primary.apiKey = defaultShop.apiKey
      primary.shopName = '晋江'
      // 删除其他同名的（包括老版本随机 id 的「晋江」）
      shopList.value = shopList.value.filter((s) => s.shopName !== '晋江' || s.id === primary.id)
      saveToStorage(shopList.value)
      return
    }
    // 2) 没有「晋江」：把默认店铺插到首位
    shopList.value.unshift(defaultShop)
    saveToStorage(shopList.value)
  }

  // 自动初始化默认店铺
  initDefaultShop()

  // 默认店铺就位后立即同步注入 token
  syncTokenFromList()

  watch(shopList, () => syncTokenFromList(), { deep: true })

  async function createShop(data) {
    const shopName = (data.shopName || '').trim()
    const apiKey = (data.apiKey || '').trim()
    if (!shopName) {
      showToast('err', '请填写店铺名称')
      return false
    }
    if (!apiKey) {
      showToast('err', '请填写 API 密钥')
      return false
    }
    if (shopList.value.some((s) => s.shopName === shopName)) {
      showToast('err', '店铺名称已存在：' + shopName)
      return false
    }
    const shop = {
      id: genId(),
      shopName,
      apiKey,
      createdAt: new Date().toISOString(),
    }
    shopList.value.push(shop)
    showToast('ok', '新增店铺成功')
    pushLog('ok', '新增店铺：' + shopName)
    return true
  }

  async function updateShop(id, data) {
    const shopName = (data.shopName || '').trim()
    const apiKey = (data.apiKey || '').trim()
    if (!shopName) {
      showToast('err', '请填写店铺名称')
      return false
    }
    if (!apiKey) {
      showToast('err', '请填写 API 密钥')
      return false
    }
    const idx = shopList.value.findIndex((s) => String(s.id) === String(id))
    if (idx < 0) {
      showToast('err', '店铺不存在')
      return false
    }
    shopList.value[idx].shopName = shopName
    shopList.value[idx].apiKey = apiKey
    showToast('ok', '修改店铺成功')
    pushLog('ok', '修改店铺：' + shopName)
    return true
  }

  async function deleteShop(idOrName) {
    if (!idOrName) return false
    const id = typeof idOrName === 'number' ? idOrName : null
    const name = typeof idOrName === 'string' ? idOrName : null
    const idx = id != null
      ? shopList.value.findIndex((s) => String(s.id) === String(id))
      : shopList.value.findIndex((s) => s.shopName === name)
    if (idx < 0) {
      showToast('err', '店铺不存在')
      return false
    }
    const removed = shopList.value.splice(idx, 1)[0]
    if (shopSelectedId.value === removed.id) {
      shopSelectedId.value = shopList.value[0]?.id || null
    }
    showToast('ok', '解绑删除成功')
    pushLog('ok', '已解绑删除店铺：' + removed.shopName)
    return true
  }

  function openShopDialog() {
    shopDialog.mode = 'create'
    shopDialog.id = null
    shopDialog.shopName = ''
    shopDialog.apiKey = ''
    shopDialog.show = true
  }

  function openShopDetail(item) { shopDetail.value = item }
  function openShopCardDetail(card) { shopCardDetail.value = card }
  function closeShopCardDetail() { shopCardDetail.value = null }
  function closeShopDetail() { shopDetail.value = null }

  function openEditShopDialog(item) {
    shopDialog.mode = 'edit'
    shopDialog.id = item?.id ?? null
    shopDialog.shopName = item?.shopName || ''
    shopDialog.apiKey = item?.apiKey || ''
    shopDialog.show = true
  }

  function confirmDeleteShop(item) {
    if (!item) return false
    const ok = typeof window !== 'undefined' ? window.confirm(`确定删除店铺「${item.shopName}」？该操作不可恢复。`) : true
    if (!ok) return false
    return deleteShop(item.id)
  }

  async function submitShopDialog() {
    if (shopDialog.mode === 'edit') {
      const ok = await updateShop(shopDialog.id, { shopName: shopDialog.shopName, apiKey: shopDialog.apiKey })
      if (ok) shopDialog.show = false
      return ok
    } else {
      const ok = await createShop({ shopName: shopDialog.shopName, apiKey: shopDialog.apiKey })
      if (ok) {
        shopDialog.show = false
        shopDialog.shopName = ''
        shopDialog.apiKey = ''
      }
      return ok
    }
  }

  return {
    shopList,
    shopDialog,
    shopDetail,
    shopCardDetail,
    shopSelectedId,
    shopCardsSearch,
    shopCardsPage,
    shopCardsPageSize,
    shopJumpPageInput,
    shopFilteredCards,
    shopTotalPages,
    shopPagedCards,
    shopPagerPages,
    currentApiKey,
    currentShopName,
    goToShopCardsPage,
    refreshShopCardsPage,
    jumpToShopPage,
    loadShopList: () => { /* localStorage 自动同步，无需加载 */ },
    createShop,
    updateShop,
    deleteShop,
    openShopDialog,
    openShopDetail,
    openShopCardDetail,
    closeShopCardDetail,
    closeShopDetail,
    openEditShopDialog,
    confirmDeleteShop,
    submitShopDialog,
    syncToken: syncTokenFromList,
  }
}
