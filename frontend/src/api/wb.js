let currentApiKey = ''
const POLL_BASE_MS = 3000

async function request(url, options = {}) {
  const headers = new Headers(options.headers || {})
  if (currentApiKey) {
    headers.set('Authorization', currentApiKey)
  }
  const res = await fetch(url, { ...options, headers })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`)
  }
  return data
}

export const wbApi = {
  setApiKey(token) {
    currentApiKey = String(token || '').trim()
  },
  hasApiKey() {
    return Boolean(currentApiKey)
  },
  generateBarcodes(count) {
    return request('/api/wb/barcodes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count }),
    })
  },
  uploadCard(payload) {
    return request('/api/wb/cards/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
  uploadImage({ nmId, photoOrder, file }) {
    const form = new FormData()
    form.append('nmId', String(nmId))
    form.append('photoOrder', String(photoOrder))
    form.append('file', file)
    return request('/api/wb/media/file', { method: 'POST', body: form })
  },
  uploadImageByUrls({ nmId, urls }) {
    return request('/api/wb/media/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nmId, data: urls }),
    })
  },
  checkErrors() { return request('/api/wb/cards/errors', { method: 'POST' }) },
  checkErrorsDetailed() { return request('/api/wb/cards/errors/detailed', { method: 'POST' }) },
  setPrices(data) {
    return request('/api/wb/prices', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data }),
    })
  },
  verifyCard(vendorCode) {
    return request('/api/wb/cards/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vendorCode }),
    })
  },
  queryPrices(filterNmID = []) {
    return request('/api/wb/prices/query', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filterNmID }),
    })
  },
  getCardsList(limit = 100) {
    return request(`/api/wb/cards/list?limit=${encodeURIComponent(limit)}`, { method: 'GET' })
  },
  getWarehouseStocksByWarehouse(skus = []) {
    return request('/api/wb/stocks/warehouses', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ skus }),
    })
  },
  getWarehouseStocks(skus = []) {
    return request('/api/wb/stocks/warehouse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skus }),
    })
  },
  getWarehouses() { return request('/api/wb/warehouses', { method: 'GET' }) },
  // stocks 项里建议使用 { sku, amount }；后端也兼容 { chrtId, amount }
  updateStocks(warehouseId, stocks) {
    return request(`/api/wb/stocks/${encodeURIComponent(warehouseId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stocks }),
    })
  },

  // ====== output 文件夹相关 ======
  getOutputInfo() { return request('/api/output/info', { method: 'GET' }) },
  listOutput() { return request('/api/output/list', { method: 'GET' }) },
  pageOutput(page = 1, size = 10, shopName = '') {
    const q = shopName ? `&shopName=${encodeURIComponent(shopName)}` : ''
    return request(`/api/output/page?page=${page}&size=${size}${q}`, { method: 'GET' })
  },
  pollOutput(since = 0) {
    return request(`/api/output/poll?since=${since}`, { method: 'GET' })
  },
  markOutputHit(sourceRef, shopName) {
    return request('/api/output/mark', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sourceRef, shopName }),
    })
  },
}

export const POLL_INTERVAL_MS = POLL_BASE_MS