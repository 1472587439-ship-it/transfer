<script setup>
import { computed, inject, ref } from 'vue'

const props = defineProps({
  shopList: { type: Array, required: true },
  shopDialog: { type: Object, required: true },
  shopDetail: { type: Object, default: null },
  shopCardDetail: { type: Object, default: null },
  shopSelectedId: { type: [String, Number, null], default: null },
  shopCardsSearch: { type: String, default: '' },
  shopCardsPage: { type: Number, required: true },
  shopCardsPageSize: { type: Number, required: true },
  shopJumpPageInput: { type: String, default: '' },
  shopPagedCards: { type: Array, required: true },
  shopPagerPages: { type: Array, required: true },
  shopTotalPages: { type: Number, required: true },
  cardsLoading: { type: Boolean, default: false },
  cardsError: { type: String, default: '' },
  resolveStock: { type: Function, required: true },
})

const emit = defineEmits([
  'open-shop-dialog',
  'open-shop-detail',
  'close-shop-detail',
  'open-edit-shop-dialog',
  'confirm-delete-shop',
  'submit-shop-dialog',
  'update:shop-selected-id',
  'update:shop-cards-search',
  'update:shop-cards-page',
  'update:shop-cards-page-size',
  'update:shop-jump-page-input',
  'refresh-shop-cards-page',
  'go-to-shop-cards-page',
  'jump-to-shop-page',
  'open-shop-card-detail',
  'update-selected-stock',
  'close-shop-card-detail',
  'load-cards',
])

const formatChangedAt = inject('formatChangedAt')
const extractImage = inject('extractImage')
const extractAllImages = inject('extractAllImages')
const extractSkuList = inject('extractSkuList')
const extractSizes = inject('extractSizes')
const closeShopCardDetail = () => emit('close-shop-card-detail')
const closeShopDialog = () => {
  if (props.shopDialog) props.shopDialog.show = false
}
const shopCardsSearchModel = computed({
  get: () => props.shopCardsSearch,
  set: (v) => emit('update:shop-cards-search', v),
})
const selectedCards = ref(new Set())
const batchStock = ref(null)

const shopSelectedIdModel = computed({
  get: () => props.shopSelectedId,
  set: (v) => emit('update:shop-selected-id', v),
})
const shopCardsPageSizeModel = computed({
  get: () => props.shopCardsPageSize,
  set: (v) => emit('update:shop-cards-page-size', v),
})
</script>

<template>
  <section class="page shop-page full-page">
    <div class="shop-hero card">
      <div class="shop-hero-main">
        <div class="shop-hero-title">Wildberries</div>
        <div class="shop-hero-subtitle">Token 管理、商品卡片浏览、店铺商品信息查看。</div>
        <div class="shop-hero-meta">
          <span class="shop-pill">已绑定 {{ shopList.length }} 个店铺</span>
          <span class="shop-pill soft">商品信息直接展示在店铺页</span>
        </div>
      </div>
      <div class="shop-hero-actions">
        <button type="button" class="btn primary" @click="$emit('open-shop-dialog')">+ 添加 Token</button>
      </div>
    </div>

    <div class="card shop-toolbar">
      <div class="shop-toolbar-left">
        <label class="shop-select-label">
          <span>选择店铺</span>
          <select v-model="shopSelectedIdModel" class="shop-select">
            <option :value="null">全部店铺</option>
            <option v-for="item in shopList" :key="item.id" :value="item.id">{{ item.shopName }}</option>
          </select>
        </label>
        <div class="shop-search-wrap">
          <span class="search-label">搜索</span>
          <div class="cards-search shop-search">
            <input v-model="shopCardsSearchModel" type="text" placeholder="搜索 vendorCode / 标题 / 条形码" @input="$emit('refresh-shop-cards-page')" />
            <span class="search-icon">⌕</span>
          </div>
        </div>
      </div>
      <div class="shop-toolbar-right">
        <span class="selection-count">已选择 {{ selectedCards.size }} 个商品</span>
        <button type="button" class="btn primary" :disabled="cardsLoading" @click="$emit('load-cards')">
          {{ cardsLoading ? '加载中…' : '刷新商品' }}
        </button>
        <label class="stock-batch-input">
          <span>库存数量</span>
          <input v-model.number="batchStock" type="number" min="0" step="1" placeholder="输入数量" />
        </label>
        <button type="button" class="btn" :disabled="selectedCards.size === 0 || batchStock == null" @click="$emit('update-selected-stock', batchStock)">一键设置库存</button>
      </div>
    </div>

    <div v-if="shopList.length" class="card shop-list-card">
      <div class="shop-list-head">
        <h3>已绑定店铺（{{ shopList.length }}）</h3>
        <span class="muted">点击「查看」可显示完整 API Key</span>
      </div>
      <div class="shop-list-grid">
        <article v-for="shop in shopList" :key="shop.id" class="shop-list-item" :class="{ active: String(shop.id) === String(props.shopSelectedId) }">
          <div class="shop-list-main">
            <div class="shop-list-name">{{ shop.shopName }}</div>
            <div class="shop-list-meta">
              <span>创建：{{ shop.createdAt || '-' }}</span>
              <span class="muted">Key：{{ shop.apiKey ? shop.apiKey.slice(0, 12) + '…' : '-' }}</span>
            </div>
          </div>
          <div class="shop-list-actions">
            <button type="button" class="btn" @click="$emit('open-shop-detail', shop)">查看</button>
            <button type="button" class="btn" @click="$emit('open-edit-shop-dialog', shop)">编辑</button>
            <button type="button" class="btn danger" @click="$emit('confirm-delete-shop', shop)">删除</button>
          </div>
        </article>
      </div>
    </div>

    <div class="card cards-shell shop-products-card">
      <p v-if="cardsError" class="hint-warn">{{ cardsError }}</p>

      <div class="cards-table-head shop-cards-head">
        <div class="col-select"><input type="checkbox" disabled /></div>
        <div class="col-product">商品</div>
        <div class="col-price">价格</div>
        <div class="col-stock">库存</div>
        <div class="col-size">尺寸/尺码</div>
        <div class="col-barcode">条形码</div>
        <div class="col-updated">更改时间</div>
        <div class="col-detail">详细</div>
      </div>

      <div class="cards-list shop-cards-list">
        <article v-for="card in (shopPagedCards || []).filter(Boolean)" :key="card?.nmID || card?.vendorCode || JSON.stringify(card)" class="cards-row shop-cards-row">
          <div class="col-select"><input type="checkbox" :checked="selectedCards.has(card.nmID)" @change="selectedCards[$event.target.checked ? 'add' : 'delete'](card.nmID); card.__selected = $event.target.checked" /></div>
          <div class="col-product product-block">
            <div class="thumb-wrap">
              <img
                v-if="extractImage(card)"
                :src="extractImage(card)"
                alt="商品图片"
                class="thumb"
                @error="$event.target.style.display = 'none'; $event.target.nextElementSibling.style.display = 'flex'"
              />
              <div v-if="!extractImage(card)" class="thumb placeholder">WB</div>
              <div v-else class="thumb placeholder" style="display:none;">WB</div>
            </div>
            <div class="product-meta">
              <div class="title-line">{{ card.title || '-' }}</div>
              <div class="meta-line">WB 商品编号: {{ card.nmID || '-' }}</div>
              <div class="meta-line">条形码: {{ card.__rowBarcode || '-' }}</div>
            </div>
          </div>
          <div class="col-price">
            <div v-if="card.__priceInfo" class="price-cell">
              <div>原价：{{ card.__priceInfo.price ?? '-' }} ₽</div>
              <div>折扣：{{ card.__priceInfo.discount ?? 0 }}%</div>
              <strong>现价：{{ card.__priceInfo.salePrice ?? card.__priceInfo.discountedPrice ?? '-' }} ₽</strong>
            </div>
            <span v-else class="muted">暂无价格</span>
          </div>
          <div class="col-stock">
            <span class="stock-num">{{ resolveStock(card) }}</span>
          </div>
          <div class="col-size">
            <span v-if="extractSizes(card)" class="stock-num">{{ extractSizes(card) }}</span>
            <span v-else class="muted">-</span>
          </div>
          <div class="col-barcode"><span class="barcode-text">{{ card.__rowBarcode || '-' }}</span></div>
          <div class="col-updated"><span class="updated-text">{{ formatChangedAt(card) }}</span></div>
          <div class="col-detail"><button type="button" class="btn" @click="$emit('open-shop-card-detail', card)">详细</button></div>
        </article>

        <div v-if="!shopPagedCards.length" class="empty-cards">暂无商品数据，请点击“刷新商品”</div>
      </div>

      <div class="pager pager-modern">
        <button class="pager-btn" :disabled="shopCardsPage <= 1" @click="$emit('go-to-shop-cards-page', shopCardsPage - 1)">上一页</button>
        <button
          v-for="p in shopPagerPages"
          :key="`${p.type}-${p.value ?? p.label}`"
          class="pager-btn"
          :class="{ active: p.type === 'page' && p.value === shopCardsPage, ellipsis: p.type === 'ellipsis' }"
          :disabled="p.type === 'ellipsis'"
          @click="p.type === 'page' && $emit('go-to-shop-cards-page', p.value)"
        >
          {{ p.label }}
        </button>
        <button class="pager-btn" :disabled="shopCardsPage >= shopTotalPages" @click="$emit('go-to-shop-cards-page', shopCardsPage + 1)">下一页</button>
        <label class="pager-jump">
          跳至
          <input
            type="number"
            min="1"
            :max="shopTotalPages"
            class="pager-jump-input"
            :value="props.shopJumpPageInput"
            @input="$emit('update:shop-jump-page-input', $event.target.value)"
            @keyup.enter="$emit('jump-to-shop-page')"
          />
          页
          <button type="button" class="pager-btn" :disabled="!props.shopJumpPageInput" @click="$emit('jump-to-shop-page')">Go</button>
        </label>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="shopCardDetail" class="modal-mask" @click.self="closeShopCardDetail">
        <div class="modal-card shop-detail-modal">
          <h3>{{ shopCardDetail.title || '-' }}</h3>
          <div class="shop-detail-subtitle">平台侧 Content API 返回的商品卡信息</div>
          <div class="detail-actions">
            <button type="button" class="btn" @click="$emit('close-shop-card-detail')">关闭</button>
          </div>

          <div class="detail-grid">
            <div><span>nmID</span><b>{{ shopCardDetail.nmID || '-' }}</b></div>
            <div><span>vendorCode</span><b>{{ shopCardDetail.vendorCode || '-' }}</b></div>
            <div><span>品牌</span><b>{{ shopCardDetail.brand || shopCardDetail.extra?.brand || '—' }}</b></div>
            <div><span>更新时间</span><b>{{ formatChangedAt(shopCardDetail) }}</b></div>
          </div>

          <div class="detail-block">
            <div class="detail-block-title">商品信息</div>
            <pre class="json-pre">{{ JSON.stringify({
  subjectID: shopCardDetail.subjectID,
  vendorCode: shopCardDetail.vendorCode,
  nmID: shopCardDetail.nmID,
  title: shopCardDetail.title,
  brand: shopCardDetail.brand || shopCardDetail.extra?.brand,
  description: shopCardDetail.description || shopCardDetail.extra?.description,
  skus: extractSkuList(shopCardDetail),
}, null, 2) }}</pre>
          </div>

          <div class="detail-block">
            <div class="detail-block-title">媒体</div>
            <div class="media-grid">
              <a v-for="(img, idx) in extractAllImages(shopCardDetail)" :key="img + idx" :href="img" target="_blank" rel="noreferrer" class="media-item">
                <img :src="img" alt="媒体" />
              </a>
            </div>
          </div>

          <div class="detail-block">
            <div class="detail-block-title">返回原 JSON 格式</div>
            <pre class="json-pre">{{ JSON.stringify(shopCardDetail, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="shopDetail" class="modal-mask" @click.self="$emit('close-shop-detail')">
        <div class="modal-card">
          <h3>店铺密钥详情</h3>
          <div class="kv">
            <div><span>店铺名称</span><b>{{ shopDetail.shopName }}</b></div>
            <div class="shop-detail-key">
              <span>API 密钥</span>
              <b>{{ shopDetail.apiKey }}</b>
            </div>
            <div><span>新增时间</span><b>{{ shopDetail.createdAt }}</b></div>
          </div>
          <div class="actions-bar" style="margin-top: 12px; justify-content:flex-end;">
            <button type="button" class="btn primary" @click="$emit('close-shop-detail')">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="shopDialog?.show" class="modal-mask" @click.self="closeShopDialog">
        <div class="modal-card">
          <h3>{{ shopDialog.mode === 'edit' ? '编辑店铺 Token' : '添加店铺 Token' }}</h3>
          <div class="kv" style="grid-template-columns: 1fr;">
            <label class="form-row">
              <span>店铺名称</span>
              <input
                type="text"
                class="batch-input"
                :value="shopDialog.shopName"
                @input="shopDialog.shopName = $event.target.value"
                placeholder="例如：晋江 / 抖音-A店"
              />
            </label>
            <label class="form-row">
              <span>API 密钥</span>
              <textarea
                class="batch-input"
                rows="4"
                :value="shopDialog.apiKey"
                @input="shopDialog.apiKey = $event.target.value"
                placeholder="eyJhbGciOi..."
              />
            </label>
          </div>
          <div class="actions-bar" style="margin-top: 12px; justify-content:flex-end; gap:8px;">
            <button type="button" class="btn" @click="closeShopDialog">取消</button>
            <button type="button" class="btn primary" @click="$emit('submit-shop-dialog')">保存</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>
