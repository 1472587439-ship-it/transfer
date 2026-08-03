<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useProductCenter } from '../../composables/useProductCenter.js'

const props = defineProps({
  shops: { type: Array, default: () => [] },
  warehouses: { type: Array, default: () => [] },
  selectedShopId: { type: [String, Number, null], default: null },
  logs: { type: Array, default: () => [] },
  /**
   * 已被任务队列锁定的 sourceRef 集合（Set）。集合内的商品：
   *  - 勾选框 disabled
   *  - applyBatchToSelected 会跳过
   *  - 行内显示"上架中"小标签
   */
  frozenRefs: { type: Set, default: () => new Set() },
})

const currentShopName = computed(() =>
  props.shops.find((s) => String(s.id) === String(props.selectedShopId))?.shopName || ''
)

watch(() => props.selectedShopId, (newId) => {
  shopName.value = currentShopName.value
  loadPage(1)
})

const emit = defineEmits([
  'back',
  'update:selected-shop-id',
  'update:selected-warehouse-id',
  'refresh-warehouses',
  'publish-card',
  'archive-card',
])

const selectedShopIdModel = computed({
  get: () => props.selectedShopId,
  set: (v) => emit('update:selected-shop-id', v),
})

const selectedWarehouseId = ref(props.warehouses?.[0]?.id || null)
watch(() => props.warehouses, (list) => {
  if (!selectedWarehouseId.value && list?.length) selectedWarehouseId.value = list[0].id
})

const {
  items, total, page, size, totalPages,
  loading, polling,
  selectedIds,
  inlineDiscountMap,
  batchMultiplierMap, batchStockMap,
  editTarget, editDiscount, editSaving,
  loadPage, refresh, goPage, startPolling, stopPolling,
  markHit, toggleSelect, selectAllOnPage, isSelected,
  openEdit, closeEdit, computedSalePrice, selectedItems,
  getMultiplier, getStock, getListedPrice, getEffectivePrice,
  shopName,
} = useProductCenter({
  showToast: (t, m) => pushLog(t, m),
  pushLog: () => {},
})

const fallbackImage = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#eff6ff" />
      <stop offset="100%" stop-color="#dbeafe" />
    </linearGradient>
  </defs>
  <rect width="120" height="120" rx="18" fill="url(#g)"/>
  <rect x="24" y="28" width="72" height="64" rx="12" fill="#ffffff" opacity="0.86"/>
  <circle cx="47" cy="49" r="7" fill="#93c5fd"/>
  <path d="M30 82l15-17 12 11 15-18 18 24H30z" fill="#93c5fd"/>
</svg>`)} `

function pushLog(type, text) {
  const time = new Date().toLocaleTimeString()
  if (Array.isArray(props.logs)) {
    props.logs.unshift({ type, text, time })
    if (props.logs.length > 40) props.logs.pop()
  }
}

onMounted(async () => {
  await loadPage(1)
  startPolling()
  // 如果仓库列表还没拉过（点过商库库存菜单才有），请求 App.vue 拉一次
  if (!Array.isArray(props.warehouses) || !props.warehouses.length) {
    emit('refresh-warehouses')
  }
})

onBeforeUnmount(() => {
  stopPolling()
})

const pagerNumbers = computed(() => {
  const pages = []
  const total = totalPages.value
  const cur = page.value
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
    return pages
  }
  pages.push(1)
  if (cur > 3) pages.push('…')
  for (let i = Math.max(2, cur - 1); i <= Math.min(total - 1, cur + 1); i++) {
    pages.push(i)
  }
  if (cur < total - 2) pages.push('…')
  pages.push(total)
  return pages
})

async function handlePublish(item) {
  // 收集全局批量设置
  const mult = batchMultiplierMap.value.get(item.sourceRef) ?? 1
  const discount = inlineDiscountMap.value.get(item.sourceRef) ?? 0
  const stock = batchStockMap.value.get(item.sourceRef) ?? 0
  emit('publish-card', { item, discount, multiplier: mult, stock, warehouseId: selectedWarehouseId.value })
}

async function handlePublishSelected() {
  const list = selectedItems()
  if (!list.length) {
    pushLog('warn', '请先勾选要上架的商品')
    return
  }
  for (const it of list) {
    const mult = batchMultiplierMap.value.get(it.sourceRef) ?? 1
    const discount = inlineDiscountMap.value.get(it.sourceRef) ?? 0
    const stock = batchStockMap.value.get(it.sourceRef) ?? 0
    emit('publish-card', { item: it, discount, multiplier: mult, stock, warehouseId: selectedWarehouseId.value })
  }
}

async function handleSetPrice(item) {
  openEdit(item)
}

async function handleSubmitEdit() {
  if (!editTarget.value) return
  const discount = Math.max(0, Math.min(100, Number(editDiscount.value) || 0))
  inlineDiscountMap.value.set(editTarget.value.sourceRef, discount)
  pushLog('ok', `${editTarget.value.vendorCode || editTarget.value.title}: 折扣已设为 ${discount}%（现价 ${computedSalePrice(editTarget.value)} ₽）`)
  closeEdit()
}

function onInlineDiscountInput(item, e) {
  const v = Math.max(0, Math.min(100, Number(e.target.value) || 0))
  inlineDiscountMap.value.set(item.sourceRef, v)
}

// ====== 批量设置（倍数 / 折扣 / 库存） ======
const batchMultiplier = ref(1.0)
const batchDiscount = ref(0)
const batchStock = ref(0)

function resetBatch() {
  batchMultiplier.value = 1.0
  batchDiscount.value = 0
  batchStock.value = 0
}

/**
 * 把全局批量设置"落地"到所有已选商品的 inlineDiscountMap 和 stockMap。
 * 倍数会在调用方（publishFromCenter）里把 item.price × 倍数 再 setPrices，
 * 因此这里只把 stock 落地到 stockMap；折扣仍走 inlineDiscountMap。
 *
 * 已进入任务队列（frozen）的商品会被跳过，避免被后续"应用于选中 / 批量上架"覆盖。
 */
function applyBatchToSelected() {
  const list = selectedItems().filter((it) => !props.frozenRefs.has(it.sourceRef))
  if (!list.length) {
    pushLog('warn', '请先勾选要批量设置的商品（已上架中的商品会被忽略）')
    return
  }
  const discount = Math.max(0, Math.min(100, Number(batchDiscount.value) || 0))
  const mult = Math.max(0.1, Number(batchMultiplier.value) || 1)
  const stock = Math.max(0, Math.floor(Number(batchStock.value) || 0))
  let n = 0
  for (const it of list) {
    if (discount > 0) inlineDiscountMap.value.set(it.sourceRef, discount)
    batchMultiplierMap.value.set(it.sourceRef, mult)
    batchStockMap.value.set(it.sourceRef, stock)
    n++
  }
  pushLog('ok', `已将批量设置应用于 ${n} 个商品：倍数 ${mult}×，折扣 ${discount}%，库存 ${stock} 件`)
}

async function handleArchive(item) {
  // 归档 = 直接标记 hit（追加当前店铺名，视为完成）
  if (!currentShopName.value) {
    pushLog('warn', '归档失败：未选择店铺')
    return
  }
  await markHit(item, currentShopName.value)
}

async function handleSelectAll(e) {
  selectAllOnPage(e.target.checked)
}
</script>

<template>
  <section class="page full-page product-center-page">
    <div class="page-head">
      <h2>商品中心</h2>
      <p>从 output 文件夹下所有 w_*.json 中读取商品，每页 10 个，已上架（hit=1）的会自动跳过</p>
    </div>

    <div class="card top-strip">
      <div class="top-strip-left">
        <div class="hero-badge">商品中心</div>
        <div class="shop-status-line">当前店铺：<b>{{ shops.find((shop) => String(shop.id) === String(selectedShopId))?.shopName || '未选择' }}</b></div>
        <div class="shop-status-line">已扫描文件：{{ total }} 个商品 · 当前第 {{ page }}/{{ totalPages }} 页</div>
      </div>
      <div class="status-pills">
        <span class="status-pill" :class="polling ? 'published' : 'pending'">
          {{ polling ? '🔄 自动监控中' : '⏸ 监控已停止' }}
        </span>
        <button type="button" class="btn soft" @click="refresh">手动刷新</button>
      </div>
    </div>

    <!-- 批量设置卡片：店铺 / 倍数 / 折扣 / 库存 -->
    <div class="card batch-card">
      <div class="batch-head">
        <span class="batch-title">⚡ 批量设置（作用于已选商品）</span>
        <span class="batch-tip">已选 <b>{{ selectedIds.size }}</b> 个</span>
      </div>
      <div class="batch-grid">
        <label class="batch-cell">
          <span>店铺</span>
          <select class="batch-input" :value="selectedShopId || ''" @change="$emit('update:selected-shop-id', $event.target.value)">
            <option value="" disabled>请选择店铺</option>
            <option v-for="s in shops" :key="s.id" :value="s.id">{{ s.shopName }}</option>
          </select>
        </label>
        <label class="batch-cell">
          <span>目标仓库</span>
          <select class="batch-input" v-model="selectedWarehouseId">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name || ('仓库 ' + w.id) }}</option>
          </select>
        </label>
        <label class="batch-cell">
          <span>上架倍数</span>
          <div class="batch-input-wrap">
            <input type="number" min="0.1" step="0.1" class="batch-input" v-model.number="batchMultiplier" />
            <span class="batch-suffix">×</span>
          </div>
        </label>
        <label class="batch-cell">
          <span>统一折扣</span>
          <div class="batch-input-wrap">
            <input type="number" min="0" max="100" step="1" class="batch-input" v-model.number="batchDiscount" />
            <span class="batch-suffix">%</span>
          </div>
        </label>
        <label class="batch-cell">
          <span>统一库存</span>
          <div class="batch-input-wrap">
            <input type="number" min="0" step="1" class="batch-input" v-model.number="batchStock" />
            <span class="batch-suffix">件</span>
          </div>
        </label>
        <div class="batch-actions">
          <button type="button" class="btn primary" :disabled="!selectedIds.size" @click="applyBatchToSelected">
            应用于选中
          </button>
          <button type="button" class="btn soft" @click="resetBatch">重置</button>
        </div>
      </div>
    </div>

    <div class="card table-card">
      <div class="table-actions">
        <label class="check-all">
          <input
            type="checkbox"
            :checked="items.length > 0 && items.filter((it) => !props.frozenRefs.has(it.sourceRef)).every(isSelected)"
            :disabled="!items.some((it) => !props.frozenRefs.has(it.sourceRef))"
            @change="handleSelectAll"
          />
          全选当前页
        </label>
        <button type="button" class="btn soft" @click="goPage(1)" :disabled="page <= 1">首页</button>
        <button type="button" class="btn soft" @click="goPage(page - 1)" :disabled="page <= 1">上一页</button>
        <span class="page-info">第 {{ page }} / {{ totalPages }} 页 · 共 {{ total }} 个</span>
        <button type="button" class="btn soft" @click="goPage(page + 1)" :disabled="page >= totalPages">下一页</button>
        <button type="button" class="btn soft" @click="goPage(totalPages)" :disabled="page >= totalPages">末页</button>
        <span class="batch-spacer" />
        <button type="button" class="btn primary" :disabled="!selectedIds.size" @click="handlePublishSelected">
          批量上架（已选 {{ selectedIds.size }}）
        </button>
      </div>

      <div v-if="loading" class="empty-cards">加载中…</div>
      <div v-else-if="!items.length" class="empty-cards">
        当前无待上架商品。等待 output 文件夹中的 w_*.json 文件…
      </div>

      <div v-else class="table-wrap">
        <table class="product-table">
          <thead>
            <tr>
              <th>选中</th>
              <th>#</th>
              <th>来源文件</th>
              <th>图片</th>
              <th>标题 / 货号</th>
              <th>subjectID</th>
              <th>条形码</th>
              <th>原价</th>
              <th>尺寸 / 重量</th>
              <th>折扣 / 现价</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.sourceRef" :class="{ 'row-frozen': props.frozenRefs.has(item.sourceRef) }">
              <td>
                <input
                  type="checkbox"
                  :checked="isSelected(item)"
                  :disabled="props.frozenRefs.has(item.sourceRef)"
                  @change="toggleSelect(item)"
                />
              </td>
              <td>
                {{ (page - 1) * size + index + 1 }}
                <span v-if="props.frozenRefs.has(item.sourceRef)" class="frozen-badge" title="该商品已在任务队列中，已固化勾选与参数">上架中</span>
              </td>
              <td><span class="file-tag" :title="item.sourceFile">{{ item.sourceFile }}</span></td>
              <td>
                <img
                  :src="item.imageUrl || fallbackImage"
                  alt="商品图"
                  class="thumb-img"
                  @error="$event.target.src = fallbackImage"
                />
              </td>
              <td>
                <div class="goods-cell">
                  <div>
                    <div class="goods-id">{{ item.title || '(无标题)' }}</div>
                    <div class="goods-sub">vendorCode: {{ item.vendorCode || '(空)' }}</div>
                  </div>
                </div>
              </td>
              <td>{{ item.subjectID || '—' }}</td>
              <td>
                <div class="sku-list">
                  <span v-for="sku in (item.skus || []).slice(0, 3)" :key="sku" class="sku-chip">{{ sku }}</span>
                  <span v-if="(item.skus || []).length > 3" class="sku-more">+{{ item.skus.length - 3 }}</span>
                </div>
              </td>
              <td>{{ item.price ? '₽' + Number(item.price).toFixed(2) : '—' }}</td>
              <td>
                <div class="size-cell">
                  <template v-if="item.dimensions && (item.dimensions.length || item.dimensions.width || item.dimensions.height)">
                    <b>{{ item.dimensions.length || '?' }}×{{ item.dimensions.width || '?' }}×{{ item.dimensions.height || '?' }}</b>
                    <span class="size-suffix">cm</span>
                  </template>
                  <template v-else>
                    <span class="muted">—</span>
                  </template>
                  <div v-if="item.dimensions && item.dimensions.weightBrutto" class="size-weight">
                    {{ item.dimensions.weightBrutto }} kg
                  </div>
                  <div v-else-if="item.weightKG" class="size-weight">
                    {{ item.weightKG }} kg
                  </div>
                </div>
              </td>
              <td>
                <div class="discount-cell">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    class="discount-input"
                    :value="inlineDiscountMap.get(item.sourceRef) ?? 0"
                    @input="onInlineDiscountInput(item, $event)"
                  />
                  <span class="discount-pct">%</span>
                  <div class="sale-price">
                    挂牌：<b>{{ getListedPrice(item) ? '₽' + getListedPrice(item).toFixed(0) : '—' }}</b>
                  </div>
                  <div class="sale-price sale-price-after">
                    折后：<b>{{ getEffectivePrice(item) ? '₽' + getEffectivePrice(item).toFixed(2) : '—' }}</b>
                  </div>
                </div>
              </td>
              <td>
                <div class="row-actions">
                  <button type="button" class="btn primary" @click="handlePublish(item)">上架</button>
                  <button type="button" class="btn soft" @click="handleSetPrice(item)">配置折扣</button>
                  <button type="button" class="btn soft" @click="handleArchive(item)">标记完成</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <Teleport to="body">
        <div v-if="editTarget" class="modal-mask" @click.self="closeEdit">
          <div class="modal-card discount-modal">
            <div class="modal-head">
              <h3>配置上架折扣</h3>
              <button type="button" class="modal-close" @click="closeEdit">×</button>
            </div>
            <div class="modal-body">
              <div class="kv"><span>商品</span><b>{{ editTarget.title || '(无标题)' }}</b></div>
              <div class="kv"><span>货号</span><b>{{ editTarget.vendorCode || '-' }}</b></div>
              <div class="kv"><span>原价</span><b>{{ editTarget.price ? '₽' + Number(editTarget.price).toFixed(2) : '-' }}</b></div>
              <div class="kv"><span>挂牌价（×倍数 {{ batchMultiplier }}）</span><b>{{ editTarget.price ? '₽' + Math.round(editTarget.price * batchMultiplier) : '-' }}</b></div>
              <div class="kv"><span>条形码</span><b>{{ (editTarget.skus || []).join(', ') || '-' }}</b></div>
              <label class="kv-edit">
                <span>折扣 (0~100%)</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  v-model.number="editDiscount"
                  class="discount-input big"
                />
              </label>
              <label class="kv-edit">
                <span>折后价（自动计算）</span>
                <input
                  type="text"
                  readonly
                  :value="editTarget.price ? '₽' + (Math.round(editTarget.price * batchMultiplier * (100 - Math.max(0, Math.min(100, Number(editDiscount) || 0))) * 100) / 10000).toFixed(2) : '—'"
                  class="discount-input big"
                />
              </label>
            </div>
            <div class="modal-foot">
              <button type="button" class="btn" @click="closeEdit">取消</button>
              <button type="button" class="btn primary" :disabled="editSaving" @click="handleSubmitEdit">更新折扣</button>
            </div>
          </div>
        </div>
      </Teleport>

      <div v-if="totalPages > 1" class="pager">
        <button
          v-for="(p, idx) in pagerNumbers"
          :key="idx"
          class="pager-btn"
          :class="{ active: p === page, ellipsis: p === '…' }"
          :disabled="p === '…'"
          @click="p !== '…' && goPage(p)"
        >
          {{ p }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.product-center-page { padding-top: 6px; }
.top-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
}
.top-strip-left { display: flex; flex-direction: column; gap: 4px; }
.hero-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1677ff;
  font-size: 12px;
  font-weight: 700;
  width: max-content;
}
.shop-status-line { color: #6b7280; font-size: 13px; }
.shop-status-line b { color: #1677ff; }
.status-pills { display: flex; gap: 8px; align-items: center; }
.status-pill {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.status-pill.published { background: #e8fff0; color: #16a34a; }
.status-pill.pending { background: #fff7ed; color: #f59e0b; }
.table-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
}
.check-all { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; color: #4b5563; }
.page-info { padding: 0 8px; color: #606266; font-size: 13px; }
.file-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.thumb-img {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
}
.goods-id { font-weight: 700; color: #0f172a; line-height: 1.3; }
.goods-sub { color: #94a3b8; font-size: 12px; margin-top: 2px; }
.sku-list { display: flex; gap: 4px; flex-wrap: wrap; }
.sku-chip {
  background: #eff6ff;
  color: #1677ff;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-family: monospace;
}
.sku-more {
  background: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 12px;
}
.row-actions { display: flex; gap: 6px; }
.empty-cards { padding: 40px 12px; text-align: center; color: #94a3b8; }
.pager {
  display: flex;
  gap: 6px;
  justify-content: center;
  margin-top: 16px;
  flex-wrap: wrap;
}
.pager-btn {
  padding: 6px 12px;
  border: 1px solid #dcdfe6;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  color: #606266;
}
.pager-btn.active { background: #1677ff; color: #fff; border-color: #1677ff; }
.pager-btn.ellipsis { cursor: default; }
.row-frozen { background: #f8fafc !important; opacity: 0.78; }
.row-frozen input[type="checkbox"]:disabled { cursor: not-allowed; }
.frozen-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1677ff;
  font-size: 10px;
  font-weight: 700;
  vertical-align: middle;
}

.product-table { width: 100%; border-collapse: collapse; min-width: 1100px; }
.product-table th, .product-table td {
  padding: 12px;
  border-bottom: 1px solid #edf2f7;
  text-align: left;
  font-size: 13px;
}
.product-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 700;
}

/* 折扣表格 */
.discount-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.discount-input {
  width: 64px;
  padding: 4px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 13px;
  text-align: right;
}
.discount-input.big {
  width: 100%;
  font-size: 16px;
  padding: 8px 10px;
}
.discount-pct { color: #475569; font-size: 13px; }
.sale-price { width: 100%; font-size: 12px; color: #6b7280; }
.sale-price b { color: #0f172a; font-weight: 700; margin-left: 2px; }
.sale-price-after b { color: #dc2626; }
.size-cell { font-size: 12px; line-height: 1.6; }
.size-cell b { color: #0f172a; font-weight: 700; }
.size-suffix { color: #6b7280; font-size: 11px; margin-left: 3px; }
.size-weight { color: #6b7280; font-size: 11px; }
.batch-spacer { flex: 1; }

/* 折扣弹窗 */
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}
.modal-card {
  background: #fff; border-radius: 12px;
  width: 480px; max-width: 92vw;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
  display: flex; flex-direction: column;
}
.modal-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px; border-bottom: 1px solid #f1f5f9;
}
.modal-head h3 { margin: 0; font-size: 16px; color: #0f172a; }
.modal-close {
  border: none; background: transparent; font-size: 22px; line-height: 1;
  cursor: pointer; color: #64748b;
}
.modal-body { padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; }
.kv, .kv-edit {
  display: flex; align-items: center; gap: 12px;
  font-size: 13px; color: #475569;
}
.kv span { width: 110px; color: #94a3b8; }
.kv b { color: #0f172a; font-weight: 700; }
.kv-edit { flex-direction: column; align-items: stretch; }
.kv-edit span { color: #94a3b8; font-size: 12px; }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 18px; border-top: 1px solid #f1f5f9;
}

/* 批量设置卡片 */
.batch-card { padding: 14px 18px; margin-top: 14px; }
.batch-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.batch-title { font-weight: 700; color: #0f172a; font-size: 14px; }
.batch-tip { color: #6b7280; font-size: 12px; }
.batch-tip b { color: #1677ff; font-weight: 700; }
.batch-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr)) auto;
  gap: 10px;
  align-items: end;
}
.batch-cell { display: flex; flex-direction: column; gap: 4px; }
.batch-cell > span { color: #6b7280; font-size: 12px; }
.batch-input {
  padding: 8px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  width: 100%;
}
.batch-input-wrap {
  display: flex; align-items: center; gap: 6px;
}
.batch-input-wrap .batch-input { flex: 1; }
.batch-suffix { color: #6b7280; font-size: 13px; min-width: 16px; }
.batch-actions { display: flex; gap: 8px; align-items: end; }
@media (max-width: 1280px) {
  .batch-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>