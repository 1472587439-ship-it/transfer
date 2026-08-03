export function pickText(value) {
  if (value == null) return ''
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  return ''
}

export function extractSkuList(card) {
  const candidates = [
    card?.sizes,
    card?.extra?.sizes,
    card?.characteristics?.sizes,
    card?.extra?.characteristics?.sizes,
  ]
  for (const value of candidates) {
    if (Array.isArray(value)) {
      return value.flatMap((size) => {
        const list = size?.skus
        if (Array.isArray(list)) return list.map((v) => String(v).trim()).filter(Boolean)
        if (typeof list === 'string' || typeof list === 'number') return [String(list).trim()].filter(Boolean)
        return []
      })
    }
  }
  return []
}

/**
 * 提取每张卡的 chrtId 列表（数字字符串）。
 * 与 extractSkuList 的区别：库存写入按 chrtId 为 key，
 * 商库库存页面也应优先以 chrtId 为主键反查商品。
 */
export function extractChrtIdList(card) {
  const candidates = [
    card?.sizes,
    card?.extra?.sizes,
    card?.characteristics?.sizes,
    card?.extra?.characteristics?.sizes,
  ]
  for (const value of candidates) {
    if (Array.isArray(value)) {
      return value.flatMap((size) => {
        const id = size?.chrtId ?? size?.chrtID
        if (id == null) return []
        const n = Number(id)
        return Number.isFinite(n) && n > 0 ? [String(n)] : []
      })
    }
  }
  return []
}

export function extractBarcode(card) {
  const skus = extractSkuList(card)
  if (skus.length) return skus.join('，')
  return '-'
}

export function extractDescription(card) {
  return pickText(card?.description || card?.extra?.description) || '暂无描述'
}

export function extractAllImages(card) {
  const candidates = [
    card?.imageUrl,
    card?.photo,
    card?.img,
    card?.url,
    card?.photos,
    card?.mediaFiles,
    card?.extra?.imageUrl,
    card?.extra?.photo,
    card?.extra?.img,
    card?.extra?.url,
    card?.extra?.photos,
    card?.extra?.mediaFiles,
    card?.extra?.images,
  ]
  const urls = []
  for (const value of candidates) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (typeof item === 'string') {
          urls.push(item)
        } else if (item && typeof item === 'object') {
          const url = item.url || item.big || item.small || item.img || item.src || item.imageUrl || item.photo || ''
          if (url) urls.push(url)
        }
      }
    } else if (typeof value === 'string') {
      urls.push(value)
    } else if (value && typeof value === 'object') {
      const url = value.url || value.big || value.small || value.img || value.src || value.imageUrl || value.photo || ''
      if (url) urls.push(url)
    }
  }
  return [...new Set(urls)].filter(Boolean)
}

export function extractImage(card) {
  const candidates = [
    card?.imageUrl,
    card?.photo,
    card?.img,
    card?.url,
    card?.photos,
    card?.mediaFiles,
    card?.extra?.imageUrl,
    card?.extra?.photo,
    card?.extra?.img,
    card?.extra?.url,
    card?.extra?.photos,
    card?.extra?.mediaFiles,
    card?.extra?.images,
  ]
  for (const value of candidates) {
    if (Array.isArray(value) && value.length) {
      const first = value[0]
      if (typeof first === 'string') return first
      if (first && typeof first === 'object') {
        return first.url || first.big || first.small || first.img || first.src || first.imageUrl || first.photo || ''
      }
    }
    if (typeof value === 'string') return value
    if (value && typeof value === 'object') {
      return value.url || value.big || value.small || value.img || value.src || value.imageUrl || value.photo || ''
    }
  }
  return ''
}

export function extractSizes(card) {
  const sizes = card?.sizes || card?.extra?.sizes || card?.characteristics?.sizes || card?.extra?.characteristics?.sizes
  if (!Array.isArray(sizes) || !sizes.length) return ''
  const webSize = String(sizes[0]?.webSize ?? '').trim()
  if (!webSize || webSize === '0') return ''
  return webSize
}

export function formatChangedAt(card) {
  return pickText(card?.updatedAt || card?.createdAt || card?.extra?.updatedAt || card?.extra?.createdAt) || '-'
}

export function resolveStock(card, stocksBySku) {
  const skuList = extractSkuList(card)
  if (skuList.length) {
    return skuList.reduce((sum, sku) => sum + (Number(stocksBySku?.[String(sku)] ?? 0) || 0), 0)
  }
  const byCard = card?.stock ?? card?.extra?.stock
  if (byCard != null) return Number(byCard) || 0
  return 0
}

export function resolveStockBySku(sku, stocksBySku) {
  if (!sku) return 0
  const bySku = stocksBySku?.[String(sku)] ?? stocksBySku?.[sku]
  return Number(bySku ?? 0) || 0
}
