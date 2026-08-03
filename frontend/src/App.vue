<script setup>
import { computed, reactive, ref, watch, provide } from 'vue'
import UploadPage from './components/pages/UploadPage.vue'
import ProductCenterPage from './components/pages/ProductCenterPage.vue'
import ShopPage from './components/pages/ShopPage.vue'
import WarehousePage from './components/pages/WarehousePage.vue'
import { wbApi } from './api/wb.js'
import {
  extractAllImages,
  extractImage,
  extractSkuList,
  extractSizes,
  formatChangedAt,
  resolveStock,
} from './utils/cards.js'
import { useToast } from './composables/useToast.js'
import { useCards } from './composables/useCards.js'
import { useWarehouse } from './composables/useWarehouse.js'
import { useShop } from './composables/useShop.js'
import { useTaskQueue } from './composables/useTaskQueue.js'
import TaskStatusBar from './components/TaskStatusBar.vue'

const { loading, toast, logs, showToast, pushLog } = useToast()
const activePage = ref('upload')
const cardsState = useCards({ showToast, pushLog })
const warehouseState = useWarehouse({ cards: cardsState.cards, stocksBySku: cardsState.stocksBySku, loadCards: cardsState.loadCards, showToast, pushLog })
const shopState = useShop({ cards: cardsState.cards, stocksBySku: cardsState.stocksBySku, showToast, pushLog })
// 任务队列：上架/库存等长操作不再触发全屏遮罩，按店铺串行执行
const taskQueue = useTaskQueue()
// 冻结中的商品 sourceRef 集合：进入任务队列即冻结（不被后续勾选 / "应用于选中" 影响）
const frozenRefs = ref(new Set())
function freezeRef(ref) { if (ref && !frozenRefs.value.has(ref)) { frozenRefs.value.add(ref); frozenRefs.value = new Set(frozenRefs.value) } }
function unfreezeRef(ref) { if (ref && frozenRefs.value.has(ref)) { frozenRefs.value.delete(ref); frozenRefs.value = new Set(frozenRefs.value) } }
function isRefFrozen(ref) { return frozenRefs.value.has(ref) }
provide('formatChangedAt', formatChangedAt)
provide('extractImage', extractImage)
provide('extractAllImages', extractAllImages)
provide('extractSkuList', extractSkuList)
provide('extractSizes', extractSizes)

const { stocksBySku, cardsLoading, cardsError, loadCards } = cardsState
const { warehouseList, warehouseSelected, warehouseLoading, warehouseError, warehouseSearch, filteredWarehouses, pagedWarehouseStocks, loadWarehouses, loadWarehouseStocks } = warehouseState
const { shopList, shopDialog, shopDetail, shopCardDetail, shopSelectedId, shopCardsSearch, shopCardsPage, shopCardsPageSize, shopJumpPageInput, shopFilteredCards, shopTotalPages, shopPagedCards, shopPagerPages, goToShopCardsPage, refreshShopCardsPage, jumpToShopPage, openShopDialog, openShopDetail, closeShopDetail, openEditShopDialog, confirmDeleteShop, submitShopDialog, openShopCardDetail, closeShopCardDetail, currentShopName } = shopState

const form = reactive({
  subjectID: 1791,
  vendorCode: '',
  title: '',
  description: '',
  brand: '',
  skusText: '',
  photoOrder: 1,
})
const imageFile = ref(null)
const imagePreview = ref('')
const imageMode = ref('file')
const imageUrlsText = ref('')
const nmId = ref('')
const verifiedCard = ref(null)
const errors = ref(null)
const uploadResult = ref(null)
const stepDone = reactive({ barcode: false, upload: false, verify: false, image: false, errors: false })

function genVendorCode() {
  const rand = Math.random().toString(36).slice(2, 8).toUpperCase()
  const time = Date.now().toString(36).toUpperCase()
  return `BCS-${time}-${rand}`
}

function resetUploadForm() {
  form.subjectID = 1791
  form.vendorCode = ''
  form.title = ''
  form.description = ''
  form.brand = ''
  form.skusText = ''
  form.photoOrder = 1
  imageFile.value = null
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  imagePreview.value = ''
  imageUrlsText.value = ''
  nmId.value = ''
  verifiedCard.value = null
  errors.value = null
  uploadResult.value = null
  stepDone.barcode = false
  stepDone.upload = false
  stepDone.verify = false
  stepDone.image = false
  stepDone.errors = false
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  imageFile.value = file || null
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  imagePreview.value = file ? URL.createObjectURL(file) : ''
}

function parseImageUrls() {
  return imageUrlsText.value
    .split(/[\n,，\s\[\]{}"]+/)
    .map((s) => s.trim().replace(/^["'\s]+|["'\s]+$/g, ''))
    .filter((s) => /^https?:\/\//.test(s))
}

function parseSkus() {
  return form.skusText.split(/[\n,，\s]+/).map((s) => s.trim()).filter(Boolean)
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

async function generateBarcode() {
  loading.value = true
  try {
    const res = await wbApi.generateBarcodes(1)
    if (!res.success) {
      showToast('err', res.message || '申请条形码失败')
      pushLog('err', res.message || '申请条形码失败')
      return false
    }
    const code = (res.data || [])[0] || ''
    form.skusText = code
    stepDone.barcode = true
    showToast('ok', res.message)
    pushLog('ok', `条形码：${code}`)
    return true
  } catch (e) {
    showToast('err', e.message)
    pushLog('err', e.message)
    return false
  } finally {
    loading.value = false
  }
}

async function uploadCard() {
  const skus = parseSkus()
  if (!form.vendorCode.trim() || !form.title.trim()) {
    showToast('err', '请填写货号与标题')
    return false
  }
  if (!skus.length) {
    showToast('err', '请先生成或填写条形码')
    return false
  }
  loading.value = true
  try {
    const payload = [{
      subjectID: Number(form.subjectID),
      variants: [{
        vendorCode: form.vendorCode.trim(),
        title: form.title.trim(),
        description: form.description.trim(),
        brand: form.brand.trim(),
        skus,
      }],
    }]
    const res = await wbApi.uploadCard(payload)
    if (!res.success) {
      showToast('err', res.message || '上架失败')
      pushLog('err', res.message || '上架失败')
      return false
    }
    stepDone.upload = true
    showToast('ok', res.message)
    pushLog('ok', `卡片已提交：${form.vendorCode}`)
    return true
  } catch (e) {
    showToast('err', e.message)
    pushLog('err', e.message)
    return false
  } finally {
    loading.value = false
  }
}

async function verifyCard() {
  const code = form.vendorCode.trim()
  if (!code) {
    showToast('err', '请填写货号')
    return false
  }
  loading.value = true
  verifiedCard.value = null
  try {
    const res = await wbApi.verifyCard(code)
    if (!res.success) {
      showToast('warn', res.message)
      pushLog('warn', res.message)
      return false
    }
    verifiedCard.value = res.data
    nmId.value = res.data?.nmID ? String(res.data.nmID) : ''
    stepDone.verify = !!nmId.value
    showToast('ok', res.message + (nmId.value ? `，nmID=${nmId.value}` : ''))
    pushLog('ok', `校验成功 nmID=${nmId.value}`)
    return true
  } catch (e) {
    showToast('err', e.message)
    pushLog('err', e.message)
    return false
  } finally {
    loading.value = false
  }
}

async function uploadImage() {
  const id = Number(nmId.value)
  if (!id) {
    showToast('err', '请先校验状态获取 nmID')
    return false
  }
  if (imageMode.value === 'url') {
    const urls = parseImageUrls()
    if (!urls.length) {
      showToast('err', '请填写至少一个图片 URL')
      return false
    }
    loading.value = true
    try {
      const res = await wbApi.uploadImageByUrls({ nmId: id, urls })
      if (!res.success) {
        showToast('err', res.message)
        pushLog('err', res.message)
        return false
      }
      stepDone.image = true
      showToast('ok', res.message)
      pushLog('ok', `URL 图片已绑定 nmID=${id}，共 ${urls.length} 张`)
      return true
    } catch (e) {
      showToast('err', e.message)
      pushLog('err', e.message)
      return false
    } finally {
      loading.value = false
    }
  }
  if (!imageFile.value) {
    showToast('err', '请选择商品图片')
    return false
  }
  loading.value = true
  try {
    const res = await wbApi.uploadImage({
      nmId: id,
      photoOrder: Number(form.photoOrder) || 1,
      file: imageFile.value,
    })
    if (!res.success) {
      showToast('err', res.message)
      pushLog('err', res.message)
      return false
    }
    stepDone.image = true
    showToast('ok', res.message)
    pushLog('ok', `图片已绑定 nmID=${id}`)
    return true
  } catch (e) {
    showToast('err', e.message)
    pushLog('err', e.message)
    return false
  } finally {
    loading.value = false
  }
}

async function checkErrors() {
  loading.value = true
  try {
    const res = await wbApi.checkErrors()
    if (!res.success) {
      showToast('err', res.message)
      pushLog('err', res.message)
      return false
    }
    errors.value = res.data || []
    stepDone.errors = true
    showToast(errors.value.length ? 'warn' : 'ok', res.message)
    pushLog(errors.value.length ? 'warn' : 'ok', res.message)
    return true
  } catch (e) {
    showToast('err', e.message)
    pushLog('err', e.message)
    return false
  } finally {
    loading.value = false
  }
}

async function runAll() {
  if (!form.vendorCode.trim()) genVendorCode()
  if (!form.title.trim()) {
    showToast('err', '请先填写商品标题')
    return
  }
  const hasFile = imageMode.value === 'file' && imageFile.value
  const hasUrls = imageMode.value === 'url' && parseImageUrls().length > 0
  if (!hasFile && !hasUrls) {
    showToast('err', '请先选择本地图片或填写图片 URL')
    return
  }
  pushLog('ok', '开始一键上架流程…')
  if (!(await generateBarcode())) return
  if (!(await uploadCard())) return
  pushLog('ok', '等待 WB 队列 3 秒…')
  await sleep(3000)
  let ok = false
  let chrtIdFound = null
  for (let i = 1; i <= 5; i++) {
    pushLog('ok', `第 ${i} 次校验状态…`)
    ok = await verifyCard()
    if (ok) {
      chrtIdFound = verifiedCard.value?.chrtId || verifiedCard.value?.sizes?.[0]?.chrtId || null
      // verify 可能不返回 chrtId，再从列表兜底
      if (!chrtIdFound) {
        try {
          const listRes = await wbApi.getCardsList(500)
          if (listRes.success) {
            const match = (listRes.data || []).find((c) => String(c.vendorCode) === String(form.vendorCode.trim()))
            if (match) chrtIdFound = match?.extra?.chrtId || match?.sizes?.[0]?.chrtId || null
          }
        } catch (_) {}
      }
      break
    }
    await sleep(2000)
  }
  if (!ok) {
    showToast('warn', '暂未拿到 nmID，请稍后手动校验后再传图')
    return
  }
  if (!(await uploadImage())) return
  await checkErrors()

  // ===== 一键上架：上架后顺手设置库存（与商品中心 publishFromCenter 对齐） =====
  if (chrtIdFound && Number.isFinite(Number(chrtIdFound))) {
    let whId = null
    if (Array.isArray(warehouseList.value) && warehouseList.value.length) {
      whId = warehouseList.value[0].id
    }
    if (!whId) {
      // 仓库列表还没加载，主动加载一次
      try {
        await loadWarehouses()
        if (Array.isArray(warehouseList.value) && warehouseList.value.length) {
          whId = warehouseList.value[0].id
        }
      } catch (_) {}
    }
    if (whId) {
      const DEFAULT_STOCK = 10
      try {
        const stockRes = await wbApi.updateStocks(whId, [{ chrtId: Number(chrtIdFound), amount: DEFAULT_STOCK }])
        if (stockRes.success) {
          pushLog('ok', `一键上架已设置库存 ${DEFAULT_STOCK} 件（仓库 ${whId}，chrtId=${chrtIdFound}）`)
        } else {
          pushLog('warn', `一键上架库存设置失败：${stockRes.message}`)
        }
      } catch (e) {
        pushLog('warn', `一键上架库存设置异常：${e.message}`)
      }
    } else {
      pushLog('warn', `一键上架未拿到仓库 id，跳过库存设置（chrtId=${chrtIdFound}）`)
    }
  } else {
    pushLog('warn', '一键上架未拿到 chrtId，跳过库存设置')
  }

  showToast('ok', '一键上架流程已完成')
  pushLog('ok', '一键上架流程已完成')
}

const errorsJson = computed(() =>
  errors.value == null ? '' : JSON.stringify(errors.value, null, 2),
)

watch(activePage, (page) => {
  if (page === 'shop') shopState.loadShopList?.()
  if (page === 'warehouse' || page === 'product-center') {
    loadWarehouses()
  }
})

// 切换店铺时，若当前在仓库/商品中心页面，已绑定的 token 变了，需要重新拉仓库
watch(shopSelectedId, (id) => {
  if (!id) return
  if (activePage.value === 'warehouse' || activePage.value === 'product-center') {
    loadWarehouses()
  }
})

// ====== 来自商品中心的操作 ======
async function publishFromCenter(payload) {
  // 兼容两种调用：纯 item 或 { item, discount, multiplier, stock, warehouseId }
  const item = payload?.item || payload
  const discount = Number(payload?.discount) || 0
  const multiplier = Number(payload?.multiplier) || 1
  const stock = Math.max(0, Math.floor(Number(payload?.stock) || 0))
  const warehouseId = payload?.warehouseId || null

  if (!shopSelectedId.value) {
    showToast('err', '请先选择店铺')
    return
  }
  if (!item.vendorCode || !item.title) {
    showToast('err', '货号与标题不能为空')
    return
  }
  if (!item.skus || !item.skus.length) {
    showToast('err', '该商品没有条形码，无法上架')
    return
  }

  // 取一个稳定的店铺标识：优先用 shopName（更直观），否则用 shopId
  const shopKey = currentShopName.value || String(shopSelectedId.value)
  const label = `上架 ${item.vendorCode}（${item.sourceFile || ''}）`

  // 一旦进入任务队列就立即冻结（无论 waiting 还是 running）：
  //  - 勾选框不再可点
  //  - 行内显示"上架中"小标签
  //  - 后续"应用于选中"会跳过它（不会覆盖倍数/折扣/库存）
  freezeRef(item.sourceRef)

  // 入队！同一店铺的任务会按顺序串行执行；不同店铺可并行
  // 不再设置 loading.value，UI 不会被全屏遮罩阻塞
  taskQueue.enqueue(shopKey, label, async () => {
    try {
      const cardPayload = [{
        subjectID: Number(item.subjectID) || 0,
        variants: [{
          vendorCode: item.vendorCode,
          title: item.title,
          description: item.description || '',
          brand: item.brand || '',
          skus: item.skus,
          ...(item.dimensions && Object.keys(item.dimensions).length ? { dimensions: item.dimensions } : {}),
        }],
      }]
      pushLog('ok', `${item.sourceFile} · ${item.vendorCode}：开始提交卡片（倍数 ${multiplier}×，折扣 ${discount}%，库存 ${stock}）`)
      const uploadRes = await wbApi.uploadCard(cardPayload)
      if (!uploadRes.success) {
        pushLog('err', `${item.sourceFile} · ${item.vendorCode}：${uploadRes.message}`)
        showToast('err', uploadRes.message)
        throw new Error(uploadRes.message || '卡片提交失败')
      }
      let nmIdFound = null
      let chrtIdFound = null
      for (let i = 1; i <= 3; i++) {
        await sleep(3000)
        const verifyRes = await wbApi.verifyCard(item.vendorCode)
        if (verifyRes.success && verifyRes.data?.nmID) {
          nmIdFound = Number(verifyRes.data.nmID)
          chrtIdFound = verifyRes.data?.chrtId || verifyRes.data?.sizes?.[0]?.chrtId || null
          // verify 可能不返回 chrtId，再从列表兜底
          if (!chrtIdFound) {
            try {
              const listRes = await wbApi.getCardsList(500)
              if (listRes.success) {
                const match = (listRes.data || []).find((c) => String(c.vendorCode) === String(item.vendorCode))
                if (match) {
                  chrtIdFound = match?.extra?.chrtId || match?.sizes?.[0]?.chrtId || null
                }
              }
            } catch (_) {}
          }
          break
        }
        pushLog('warn', `${item.vendorCode}：第 ${i} 次未找到 nmID`)
      }
      if (nmIdFound) {
        const imageList = [item.imageUrl, ...(item.crawledImages || [])]
          .filter(Boolean)
          .filter((v, i, arr) => arr.indexOf(v) === i)
        if (imageList.length) {
          const imgRes = await wbApi.uploadImageByUrls({ nmId: nmIdFound, urls: imageList })
          if (imgRes.success) {
            pushLog('ok', `${item.vendorCode}：已上传 ${imageList.length} 张图片`)
          } else {
            pushLog('warn', `${item.vendorCode}：图片上传失败：${imgRes.message}`)
          }
        }
        // 倍数 → price（原值 × 倍数，不二次乘折扣）
        // discount → discount%（独立字段，由后端按 discount 从 price 算 salePrice）
        const basePrice = Number(item.price) || 0
        const multipliedPrice = Math.round(basePrice * multiplier)
        const safeDiscount = Math.max(0, Math.min(100, Math.round(discount)))
        if (multipliedPrice > 0 && (multiplier !== 1 || safeDiscount > 0)) {
          const pricePayload = { nmID: nmIdFound, price: multipliedPrice }
          if (safeDiscount > 0) pricePayload.discount = safeDiscount
          const priceRes = await wbApi.setPrices([pricePayload])
          if (priceRes.success) {
            const note = safeDiscount > 0
              ? `已设价格 ₽${multipliedPrice}（原价 × ${multiplier}）+ 折扣 ${safeDiscount}%`
              : `已设价格 ₽${multipliedPrice}（原价 × ${multiplier}）`
            pushLog('ok', `${item.vendorCode}：${note}`)
          } else {
            pushLog('warn', `${item.vendorCode}：价格设置失败：${priceRes.message}`)
          }
        }
        // 上架后批量设置库存：需要 chrtId
        if (stock > 0) {
          if (chrtIdFound) {
            let whId = warehouseId
            if (!whId) {
              // 兜底：用仓库列表第一个
              if (Array.isArray(warehouseList.value) && warehouseList.value.length) {
                whId = warehouseList.value[0].id
              }
            }
            if (whId) {
              try {
                const stockRes = await wbApi.updateStocks(whId, [{ chrtId: Number(chrtIdFound), amount: stock }])
                if (stockRes.success) {
                  pushLog('ok', `${item.vendorCode}：已设置库存 ${stock} 件（仓库 ${whId}，chrtId=${chrtIdFound}）`)
                } else {
                  pushLog('warn', `${item.vendorCode}：库存设置失败：${stockRes.message}`)
                }
              } catch (e) {
                pushLog('warn', `${item.vendorCode}：库存设置异常：${e.message}`)
              }
            } else {
              pushLog('warn', `${item.vendorCode}：未配置默认仓库，跳过库存设置（chrtId=${chrtIdFound}）`)
            }
          } else {
            pushLog('warn', `${item.vendorCode}：未拿到 chrtId，跳过库存设置`)
          }
        }
        pushLog('ok', `${item.vendorCode}：上架成功 nmID=${nmIdFound}`)
        showToast('ok', `上架成功 nmID=${nmIdFound}`)
      } else {
        pushLog('warn', `${item.vendorCode}：未拿到 nmID，但卡片已提交`)
        showToast('warn', '卡片已提交，但未拿到 nmID')
      }
      const markRes = await wbApi.markOutputHit(item.sourceRef, currentShopName.value)
      if (markRes.success) {
        pushLog('ok', `已标记 hit=1：${item.sourceRef}`)
      } else {
        pushLog('warn', '标记 hit=1 失败：' + (markRes.message || ''))
      }
      // 上架完成：商品会从列表中消失（markHit），无需再保留冻结
      unfreezeRef(item.sourceRef)
    } catch (e) {
      // 任务失败时解除冻结，让用户可以重新勾选 / 调整参数后再试
      unfreezeRef(item.sourceRef)
      throw e
    }
  }, { item, discount, multiplier, stock, warehouseId })
  // 立刻给前端一个轻提示，告诉用户已加入队列
  pushLog('ok', `已加入队列（店铺：${shopKey}）：${label}`)
}

function cancelTask(t) {
  if (!t) return
  taskQueue.cancel(t.shopKey, t.id)
  // 取消 waiting 中的任务后，立即解除该商品的冻结（用户可以重新设置参数后再上架）
  const ref = t.meta?.item?.sourceRef
  if (ref) unfreezeRef(ref)
}

function archiveFromCenter(item) {
  if (!currentShopName.value) {
    showToast('err', '请先选择店铺')
    return
  }
  const shopKey = currentShopName.value
  const label = `标记完成 ${item.vendorCode}`
  taskQueue.enqueue(shopKey, label, async () => {
    const res = await wbApi.markOutputHit(item.sourceRef, currentShopName.value)
    if (res.success) {
      pushLog('ok', `已归档 [${currentShopName.value}]：${item.sourceRef}`)
      showToast('ok', '已归档')
    } else {
      pushLog('warn', res.message)
      throw new Error(res.message || '归档失败')
    }
  }, { item })
}

// ====== 库存相关 ======
async function updateSelectedStock(batchStock) {
  if (!Number.isInteger(batchStock) || batchStock < 0) {
    const message = `库存设置失败：输入值"${batchStock ?? ''}"无效`
    pushLog('err', message)
    showToast('err', message)
    return
  }
  const selectedCards = shopPagedCards.value.filter((card) => card.__selected)
  if (!selectedCards.length) {
    const message = '库存设置失败：没有勾选商品'
    pushLog('warn', message)
    showToast('warn', message)
    return
  }
  const warehouse = warehouseList.value[0]
  if (!warehouse?.id) {
    await loadWarehouses()
  }
  const activeWarehouse = warehouseList.value[0]
  if (!activeWarehouse?.id) {
    const message = '库存设置失败：仓库列表加载失败'
    pushLog('err', message)
    showToast('err', message)
    return
  }
  const stocks = selectedCards.flatMap((card) => {
    const sizes = Array.isArray(card.sizes) ? card.sizes : []
    return sizes.map((size) => ({ chrtId: Number(size.chrtID), amount: batchStock }))
      .filter((stock) => stock.chrtId && Number.isFinite(stock.chrtId))
  })
  if (!stocks.length) {
    const message = '库存设置失败：勾选商品中没有有效的 chrtID'
    pushLog('err', message)
    showToast('err', message)
    return
  }
  // 走任务队列：按店铺串行（避免不同店铺的库存请求并发时争抢资源）
  const shopKey = currentShopName.value || String(shopSelectedId.value) || '__default__'
  const label = `设置库存 ${stocks.length} 项（仓库 ${activeWarehouse.id}，每件 ${batchStock}）`
  taskQueue.enqueue(shopKey, label, async () => {
    try {
      const result = await wbApi.updateStocks(activeWarehouse.id, stocks)
      if (!result.success) throw new Error(result.message || '后端未返回成功状态')
      pushLog('ok', `库存更新成功：仓库 ${activeWarehouse.id}，已更新 ${stocks.length} 个尺码`)
      showToast('ok', '库存更新成功')
      await loadCards()
    } catch (e) {
      pushLog('err', '库存更新失败：' + e.message)
      showToast('err', e.message)
      throw e
    }
  }, { stocks, warehouseId: activeWarehouse.id })
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">
        <span class="logo-cube" aria-hidden="true" />
        <span class="logo-text">WB 商品管理系统</span>
      </div>
      <nav class="menu">
        <button type="button" class="menu-item" :class="{ active: activePage === 'upload' }" @click="activePage = 'upload'">
          <span class="ico bag" />商品上架
        </button>
        <button type="button" class="menu-item" :class="{ active: activePage === 'warehouse' }" @click="activePage = 'warehouse'; loadWarehouses()">
          <span class="ico list" />商库库存页面
        </button>
        <button type="button" class="menu-item" :class="{ active: activePage === 'product-center' }" @click="activePage = 'product-center'">
          <span class="ico bag" />商品中心
        </button>
        <button type="button" class="menu-item" :class="{ active: activePage === 'shop' }" @click="activePage = 'shop'">
          <span class="ico bag" />店铺管理
        </button>
        <button type="button" class="menu-item" :class="{ active: activePage === 'logs' }" @click="activePage = 'logs'">
          <span class="ico list" />操作日志
        </button>
      </nav>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="breadcrumb">{{ activePage === 'warehouse' ? '商库库存页面' : activePage === 'shop' ? '店铺管理' : activePage === 'product-center' ? '商品中心' : activePage === 'logs' ? '操作日志' : '商品上架' }}</div>
        <div class="topbar-shop" v-if="currentShopName && activePage === 'shop'">当前店铺：{{ currentShopName }}</div>
        <div class="user">
          <span class="avatar" />
          <span>admin</span>
        </div>
      </header>

      <div class="content">
        <section v-show="activePage === 'upload'" class="page">
          <UploadPage
            :form="form"
            :loading="loading"
            :step-done="stepDone"
            :upload-result="uploadResult"
            :image-mode="imageMode"
            :image-preview="imagePreview"
            :image-file="imageFile"
            :image-urls-text="imageUrlsText"
            :nm-id="nmId"
            :verified-card="verifiedCard"
            :errors="errors"
            :errors-json="errorsJson"
            :logs="logs"
            @reset-form="resetUploadForm"
            @gen-vendor-code="genVendorCode"
            @generate-barcode="generateBarcode"
            @close-upload-result="uploadResult = null"
            @set-image-mode="imageMode = $event"
            @file-change="onFileChange"
            @run-all="runAll"
            @upload-card="uploadCard"
            @verify-card="verifyCard"
            @upload-image="uploadImage"
            @check-errors="checkErrors"
            @update:image-urls-text="imageUrlsText = $event"
            @update:nm-id="nmId = $event"
          />
        </section>

        <section v-show="activePage === 'logs'" class="page logs-page">
          <div class="page-head logs-head">
            <div>
              <h2>操作日志</h2>
              <p>集中查看商品提交、nmID 校验、图片上传、价格设置和错误检查结果。</p>
            </div>
            <button type="button" class="btn" @click="logs.splice(0, logs.length)">清空日志</button>
          </div>
          <div class="card logs-card">
            <div v-if="!logs.length" class="empty-row">暂无操作日志</div>
            <ul v-else class="timeline logs-timeline">
              <li v-for="(item, idx) in logs" :key="idx" :class="item.type">
                <time>{{ item.time }}</time>
                <span>{{ item.text }}</span>
              </li>
            </ul>
          </div>
        </section>

        <section v-show="activePage === 'product-center'" class="page">
          <ProductCenterPage
            :shops="shopList"
            :warehouses="warehouseList"
            :selected-shop-id="shopSelectedId"
            :logs="logs"
            :frozen-refs="frozenRefs"
            @back="activePage = 'upload'"
            @update:selected-shop-id="shopSelectedId = $event"
            @refresh-warehouses="loadWarehouses"
            @publish-card="publishFromCenter"
            @archive-card="archiveFromCenter"
          />
        </section>

        <ShopPage
          v-show="activePage === 'shop'"
          :shop-list="shopList"
          :shop-dialog="shopDialog"
          :shop-detail="shopDetail"
          :shop-card-detail="shopCardDetail"
          :shop-selected-id="shopSelectedId"
          :shop-cards-search="shopCardsSearch"
          :shop-cards-page="shopCardsPage"
          :shop-cards-page-size="shopCardsPageSize"
          :shop-jump-page-input="shopJumpPageInput"
          :shop-paged-cards="shopPagedCards"
          :shop-pager-pages="shopPagerPages"
          :shop-total-pages="shopTotalPages"
          :cards-loading="cardsLoading"
          :cards-error="cardsError"
          :resolve-stock="(card) => resolveStock(card, stocksBySku)"
          @open-shop-dialog="openShopDialog"
          @open-shop-detail="openShopDetail"
          @close-shop-detail="closeShopDetail"
          @open-edit-shop-dialog="openEditShopDialog"
          @confirm-delete-shop="confirmDeleteShop"
          @submit-shop-dialog="submitShopDialog"
          @update:shop-selected-id="shopSelectedId = $event"
          @update:shop-cards-search="shopCardsSearch = $event"
          @update:shop-cards-page-size="shopCardsPageSize = $event"
          @update:shop-jump-page-input="shopJumpPageInput = $event"
          @refresh-shop-cards-page="refreshShopCardsPage"
          @go-to-shop-cards-page="goToShopCardsPage"
          @jump-to-shop-page="jumpToShopPage"
          @open-shop-card-detail="openShopCardDetail"
          @update-selected-stock="updateSelectedStock"
          @close-shop-card-detail="closeShopCardDetail"
          @load-cards="loadCards"
        />

        <WarehousePage
          v-show="activePage === 'warehouse'"
          :warehouse-search="warehouseSearch"
          :warehouse-selected="warehouseSelected"
          :warehouse-loading="warehouseLoading"
          :warehouse-error="warehouseError"
          :filtered-warehouses="filteredWarehouses"
          :warehouse-list="warehouseList"
          :paged-warehouse-stocks="pagedWarehouseStocks"
          @refresh-warehouses="loadWarehouses"
          @refresh-stocks="loadWarehouseStocks"
          @update:warehouse-search="warehouseSearch = $event"
          @update:warehouse-selected="warehouseSelected = $event"
        />
      </div>
    </div>

    <Transition name="toast">
      <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.text }}</div>
    </Transition>

    <!--
      全局 loading 遮罩已移除：上架/库存等长操作走任务队列，状态由底部 TaskStatusBar 显示。
      上架过程中可继续切换店铺、仓库、商品中心分页等，互不阻塞。
    -->
    <TaskStatusBar
      :summaries="taskQueue.shopSummaries.value"
      :pending-count="taskQueue.pendingCount.value"
      @cancel-task="cancelTask"
    />
  </div>
</template>

<style>
.layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg);
}

.sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  background: var(--sidebar-bg);
  border-right: 1px solid #dce3ec;
  display: flex;
  flex-direction: column;
}

.logo {
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid #dce3ec;
  background: #fff;
}

.logo-cube {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: linear-gradient(135deg, #79bbff 0%, #409eff 45%, #337ecc 100%);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.35);
  position: relative;
}

.logo-cube::after {
  content: '';
  position: absolute;
  inset: 6px;
  border: 2px solid rgba(255, 255, 255, 0.85);
  border-radius: 2px;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
}

.menu {
  padding: 10px 8px 20px;
}

.menu-item {
  width: 100%;
  border: none;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
  text-align: left;
  padding: 11px 12px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ico {
  width: 16px;
  height: 16px;
  display: inline-block;
  flex-shrink: 0;
  background: currentColor;
  opacity: 0.75;
  -webkit-mask-size: contain;
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-size: contain;
  mask-repeat: no-repeat;
  mask-position: center;
}

.ico.bag {
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M7 7V6a5 5 0 0110 0v1h3v14H4V7h3zm2 0h6V6a3 3 0 00-6 0v1z'/%3E%3C/svg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M7 7V6a5 5 0 0110 0v1h3v14H4V7h3zm2 0h6V6a3 3 0 00-6 0v1z'/%3E%3C/svg%3E");
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: var(--header-h);
  background: #fff;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.breadcrumb {
  color: var(--text-secondary);
  font-size: 13px;
}

.user {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 30%, #fff 0 18%, transparent 19%),
    linear-gradient(180deg, #a0cfff, #409eff);
}

.content {
  padding: 16px 20px 28px;
  overflow: auto;
}

.page-head h2 {
  margin: 0 0 6px;
  font-size: 18px;
}

.page-head p {
  margin: 0 0 14px;
  color: var(--text-secondary);
  font-size: 13px;
}

.steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 12px;
}

.step i {
  font-style: normal;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e9eef5;
  color: #606266;
  font-size: 11px;
}

.step.done {
  border-color: #b3e19d;
  background: #f0f9eb;
  color: var(--success);
}

.step.done i {
  background: var(--success);
  color: #fff;
}

.card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  margin-bottom: 14px;
  box-shadow: var(--shadow);
}

.card h3 {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 600;
  padding-left: 8px;
  border-left: 3px solid var(--primary);
}

.mode-switch {
  display: inline-flex;
  gap: 0;
  margin-bottom: 14px;
  border: 1px solid #dcdfe6;
  border-radius: var(--radius);
  overflow: hidden;
}

.mode-btn {
  border: none;
  background: #fff;
  color: #606266;
  padding: 7px 14px;
  font-size: 13px;
}

.mode-btn + .mode-btn {
  border-left: 1px solid #dcdfe6;
}

.mode-btn.active {
  background: var(--primary);
  color: #fff;
}

.hint-warn {
  margin: 0 0 8px;
  color: var(--warning);
  font-size: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 18px;
}

.form-grid .full {
  grid-column: 1 / -1;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label > span {
  color: #606266;
  font-size: 13px;
}

input,
textarea {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: var(--radius);
  padding: 8px 10px;
  outline: none;
  transition: border-color 0.15s;
  background: #fff;
  color: var(--text);
}

input:focus,
textarea:focus {
  border-color: var(--primary);
}

.inline {
  display: flex;
  gap: 8px;
}

.btn {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  border-radius: var(--radius);
  padding: 8px 14px;
  white-space: nowrap;
  transition: all 0.15s;
}

.btn:hover:not(:disabled) {
  color: var(--primary);
  border-color: #c6e2ff;
  background: var(--primary-soft);
}

.btn.primary {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.btn.primary:hover:not(:disabled) {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
  color: #fff;
}

.btn.lg {
  padding: 10px 22px;
  font-weight: 600;
}

.actions-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.preview {
  margin-top: 12px;
  width: 140px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.preview img {
  display: block;
  width: 100%;
}

.result-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.flex1 {
  min-width: 0;
}

.kv {
  display: grid;
  gap: 8px;
}

.kv div {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px;
}

.kv span {
  color: var(--text-secondary);
}

.muted {
  color: var(--text-secondary);
  margin: 0;
}

.log-box {
  margin: 0;
  max-height: 180px;
  overflow: auto;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 220px;
  overflow: auto;
}

.timeline li {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
}

.timeline time {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  min-width: 78px;
}

.timeline .ok span {
  color: var(--success);
}
.timeline .warn span {
  color: var(--warning);
}
.timeline .err span {
  color: var(--danger);
}

.json-files {
  margin-top: 12px;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  background: #f8fafc;
}

.json-files-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.json-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 200px;
  overflow: auto;
}

.json-list li {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
  word-break: break-all;
}

.json-list li:last-child {
  border-bottom: none;
}

.json-list li.ok .json-msg {
  color: var(--success);
}

.json-list li.err .json-msg {
  color: var(--danger);
}

.json-name {
  font-weight: 600;
  min-width: 0;
}

.json-msg {
  color: var(--text-secondary);
}

.json-results {
  margin-top: 12px;
}

.json-results h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.toast {
  position: fixed;
  top: 72px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 18px;
  box-shadow: var(--shadow);
  min-width: 240px;
  text-align: center;
}

.toast.ok {
  border-color: #b3e19d;
  color: var(--success);
}
.toast.warn {
  border-color: #f3d19e;
  color: var(--warning);
}
.toast.err {
  border-color: #fbc4c4;
  color: var(--danger);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -8px);
}

/*
.loading-mask 已删除：上架/库存等长操作由 TaskStatusBar 接管，避免全屏遮罩阻塞操作。
如需在某个按钮上单独显示转圈，可以使用 .spinner-mini（在 TaskStatusBar.vue 内定义）。
*/

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 900px) {
  .sidebar {
    display: none;
  }
  .form-grid,
  .result-row {
    grid-template-columns: 1fr;
  }
}
</style>
