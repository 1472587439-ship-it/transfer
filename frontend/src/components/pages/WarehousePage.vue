<template>
  <section class="page">
    <div class="page-head">
      <h2>商库库存页面</h2>
      <p>通过 WB 仓库接口查看仓库信息，并按仓库/商品维度查看库存。</p>
    </div>

    <div class="card cards-shell">
      <div class="cards-toolbar">
        <div class="cards-search">
          <input v-model="warehouseSearchModel" type="text" placeholder="搜索仓库名称、ID、地址" />
          <span class="search-icon">⌕</span>
        </div>
        <div class="cards-actions">
          <button type="button" class="btn primary" :disabled="warehouseLoading" @click="$emit('refresh-warehouses')">
            {{ warehouseLoading ? '加载中…' : '刷新仓库' }}
          </button>
          <button type="button" class="btn" :disabled="warehouseLoading" @click="$emit('refresh-stocks')">
            刷新库存
          </button>
        </div>
      </div>

      <p v-if="warehouseError" class="hint-warn">{{ warehouseError }}</p>

      <div class="warehouse-grid">
        <div class="warehouse-panel">
          <div class="warehouse-head">仓库列表</div>
          <div class="warehouse-list">
            <button
              v-for="item in filteredWarehouses"
              :key="item.id || item.warehouseId || item.name"
              type="button"
              class="warehouse-item"
              :class="{ active: String(warehouseSelectedModel?.id || warehouseSelectedModel?.warehouseId) === String(item.id || item.warehouseId) }"
              @click="warehouseSelectedModel = item"
            >
              <div class="warehouse-title">{{ item.name || item.warehouseName || '未命名仓库' }}</div>
              <div class="warehouse-meta">ID：{{ item.id || item.warehouseId || '-' }}</div>
            </button>
          </div>
        </div>

        <div class="warehouse-panel flex-fill">
          <div class="warehouse-head">库存明细</div>
          <div class="warehouse-summary">
            <span>当前仓库：{{ warehouseSelectedModel?.name || warehouseSelectedModel?.warehouseName || '-' }}</span>
            <span>ID：{{ warehouseSelectedModel?.id || warehouseSelectedModel?.warehouseId || '-' }}</span>
          </div>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>商品</th>
                  <th>SKU</th>
                  <th v-for="warehouse in warehouseList" :key="warehouse.id">{{ warehouse.name || warehouse.warehouseName || warehouse.id }}</th>
                  <th>总库存</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in pagedWarehouseStocks" :key="item.sku">
                  <td>{{ item.title || item.vendorCode || '-' }}</td>
                  <td>{{ item.sku }}</td>
                  <td v-for="warehouse in warehouseList" :key="warehouse.id">{{ item.warehouses?.[warehouse.id]?.quantity ?? 0 }}</td>
                  <td><b>{{ item.total }}</b></td>
                </tr>
                <tr v-if="!pagedWarehouseStocks.length">
                  <td :colspan="warehouseList.length + 3" class="empty-row">暂无库存数据，请先刷新库存</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  warehouseSearch: { type: String, default: '' },
  warehouseSelected: { type: Object, default: null },
  warehouseLoading: { type: Boolean, default: false },
  warehouseError: { type: String, default: '' },
  filteredWarehouses: { type: Array, required: true },
  warehouseList: { type: Array, required: true },
  pagedWarehouseStocks: { type: Array, required: true },
})

const emit = defineEmits(['refresh-warehouses', 'refresh-stocks', 'update:warehouse-search', 'update:warehouse-selected'])

const warehouseSearchModel = computed({
  get: () => props.warehouseSearch,
  set: (v) => emit('update:warehouse-search', v),
})
const warehouseSelectedModel = computed({
  get: () => props.warehouseSelected,
  set: (v) => emit('update:warehouse-selected', v),
})
</script>
