<template>
  <section class="page full-page">
    <div class="page-head">
      <h2>商品上架</h2>
      <p>在同一页完成：申请条形码 → 提交卡片 → 校验 nmID → 上传图片 → 检查错误</p>
    </div>

    <div class="steps">
      <div class="step" :class="{ done: stepDone.barcode }"><i>1</i>条形码</div>
      <div class="step" :class="{ done: stepDone.upload }"><i>2</i>提交卡片</div>
      <div class="step" :class="{ done: stepDone.verify }"><i>3</i>校验状态</div>
      <div class="step" :class="{ done: stepDone.image }"><i>4</i>上传图片</div>
      <div class="step" :class="{ done: stepDone.errors }"><i>5</i>错误检查</div>
    </div>

    <div style="display:flex;justify-content:flex-end;margin-bottom:6px;">
      <button type="button" class="btn" @click="$emit('reset-form')">清空全部内容</button>
    </div>

    <div class="card">
      <h3>基本信息</h3>
      <div class="form-grid">
        <label>
          <span>类目 subjectID</span>
          <input v-model.number="form.subjectID" type="number" />
        </label>
        <label>
          <span>货号 vendorCode</span>
          <div class="inline">
            <input v-model="form.vendorCode" type="text" placeholder="可点击生成" />
            <button type="button" class="btn" @click="$emit('gen-vendor-code')">生成</button>
          </div>
        </label>
        <label class="full">
          <span>标题 title</span>
          <input v-model="form.title" type="text" placeholder="商品标题" />
        </label>
        <label>
          <span>品牌 brand</span>
          <input v-model="form.brand" type="text" placeholder="可留空" />
        </label>
        <label>
          <span>条形码 skus</span>
          <div class="inline">
            <input v-model="form.skusText" type="text" placeholder="点击申请自动填入" />
            <button type="button" class="btn primary" :disabled="loading" @click="$emit('generate-barcode')">申请</button>
          </div>
        </label>
        <label class="full">
          <span>描述 description</span>
          <textarea v-model="form.description" rows="3" placeholder="可选" />
        </label>
      </div>
    </div>

    <div v-if="false" class="card">
      <h3>JSON 上架（已弃用）</h3>
      <p class="muted">JSON 上架功能已迁移到"商品中心"，系统会自动扫描 output 文件夹下的 w_*.json 文件。</p>
    </div>

    <div v-if="uploadResult" class="modal-mask" @click.self="$emit('close-upload-result')">
      <div class="modal-card">
        <h3>上架商品信息</h3>
        <div class="kv">
          <div><span>nmID</span><b>{{ uploadResult.nmID || '-' }}</b></div>
          <div><span>imtID</span><b>{{ uploadResult.imtID || '-' }}</b></div>
          <div><span>nmUUID</span><b>{{ uploadResult.nmUUID || '-' }}</b></div>
          <div><span>vendorCode</span><b>{{ uploadResult.vendorCode || '-' }}</b></div>
          <div><span>标题</span><b>{{ uploadResult.title || '-' }}</b></div>
        </div>
        <div class="actions-bar" style="margin-top: 12px; justify-content:flex-end;">
          <button type="button" class="btn primary" @click="$emit('close-upload-result')">关闭</button>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>商品主图</h3>
      <div class="mode-switch">
        <button type="button" class="mode-btn" :class="{ active: imageMode === 'file' }" @click="$emit('set-image-mode', 'file')">本地文件</button>
        <button type="button" class="mode-btn" :class="{ active: imageMode === 'url' }" @click="$emit('set-image-mode', 'url')">URL 上架</button>
      </div>

      <div class="form-grid">
        <label>
          <span>官方编号 nmID</span>
          <input v-model="nmIdModel" type="text" placeholder="校验后自动填入" />
        </label>
        <label v-if="imageMode === 'file'">
          <span>起始图片序号</span>
          <input v-model.number="form.photoOrder" type="number" min="1" max="30" />
        </label>
        <label v-if="imageMode === 'file'" class="full">
          <span>选择图片（可多选）</span>
          <input type="file" multiple accept="image/*" @change="$emit('file-change', $event)" />
        </label>
        <label v-else class="full">
          <span>图片 URL（多个用换行或逗号分隔，第一张为主图）</span>
          <textarea v-model="imageUrlsTextModel" rows="3" placeholder="https://example.com/photo1.jpg" />
        </label>
      </div>
      <p v-if="imageMode === 'url'" class="hint-warn">
        注意：URL 上架会整体替换该商品已有图片，请使用可直接访问的图片直链。
      </p>
      <div v-if="imageMode === 'file' && imagePreview" class="preview">
        <img :src="imagePreview" alt="预览" />
      </div>
      <div v-if="imageMode === 'file' && imageFile && imageFile.name" class="muted" style="margin-top: 8px;">
        已选择文件：{{ imageFile.name }}（{{ Math.round(imageFile.size / 1024) }} KB），上传时使用序号 {{ Number(form.photoOrder) || 1 }}
      </div>
    </div>

    <div class="actions-bar">
      <button type="button" class="btn primary lg" :disabled="loading" @click="$emit('run-all')">一键上架</button>
      <button type="button" class="btn" :disabled="loading" @click="$emit('upload-card')">仅提交卡片</button>
      <button type="button" class="btn" :disabled="loading" @click="$emit('verify-card')">校验状态</button>
      <button type="button" class="btn" :disabled="loading" @click="$emit('upload-image')">上传图片</button>
      <button type="button" class="btn" :disabled="loading" @click="$emit('check-errors')">检查错误</button>
    </div>

    <div class="result-row">
      <div class="card flex1">
        <h3>校验结果</h3>
        <div v-if="verifiedCard" class="kv">
          <div><span>货号</span><b>{{ verifiedCard.vendorCode }}</b></div>
          <div><span>nmID</span><b>{{ verifiedCard.nmID }}</b></div>
          <div><span>subjectID</span><b>{{ verifiedCard.subjectID }}</b></div>
          <div><span>标题</span><b>{{ verifiedCard.title }}</b></div>
        </div>
        <p v-else class="muted">暂无数据，请先提交卡片并校验</p>
      </div>
      <div class="card flex1">
        <h3>错误日志</h3>
        <pre v-if="errors !== null" class="log-box">{{ errorsJson || '[]' }}</pre>
        <p v-else class="muted">点击「检查错误」拉取后台日志</p>
      </div>
    </div>

    <div class="card">
      <h3>操作记录</h3>
      <ul class="timeline">
        <li v-for="(item, idx) in logs" :key="idx" :class="item.type">
          <time>{{ item.time }}</time>
          <span>{{ item.text }}</span>
        </li>
        <li v-if="!logs.length" class="muted">暂无记录</li>
      </ul>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  form: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  stepDone: { type: Object, required: true },
  uploadResult: { type: Object, default: null },
  imageMode: { type: String, default: 'file' },
  imagePreview: { type: String, default: '' },
  imageFile: { type: Object, default: null },
  imageUrlsText: { type: String, default: '' },
  nmId: { type: String, default: '' },
  verifiedCard: { type: Object, default: null },
  errors: { type: [Object, Array, null], default: null },
  errorsJson: { type: String, default: '' },
  logs: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'reset-form',
  'gen-vendor-code',
  'generate-barcode',
  'close-upload-result',
  'set-image-mode',
  'file-change',
  'run-all',
  'upload-card',
  'verify-card',
  'upload-image',
  'check-errors',
  'update:image-urls-text',
  'update:nm-id',
])

const imageUrlsTextModel = computed({
  get: () => props.imageUrlsText,
  set: (v) => emit('update:image-urls-text', v),
})
const nmIdModel = computed({
  get: () => props.nmId,
  set: (v) => emit('update:nm-id', v),
})
</script>
