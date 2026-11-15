<template>
  <div v-loading="loading">
    <!-- 头部 -->
    <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center">
      <div>
        <el-button text :icon="ArrowLeft" @click="$router.push('/decks')">返回知识库列表</el-button>
        <h2 style="margin: 8px 0 0 0">{{ deck?.name }}</h2>
        <p style="color: #909399; margin: 4px 0 0 0; font-size: 14px">
          {{ deck?.description || '暂无描述' }} · {{ total }} 张卡片
        </p>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button :icon="Upload" @click="importDialogVisible = true">批量导入</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateCard">添加卡片</el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-input
        v-model="keyword"
        placeholder="搜索卡片内容"
        clearable
        :prefix-icon="Search"
        style="width: 280px"
        @keyup.enter="loadCards"
        @clear="loadCards"
      />
      <el-select v-model="cardType" placeholder="全部类型" clearable style="width: 160px" @change="loadCards">
        <el-option label="Basic 基础" value="basic" />
        <el-option label="Interview 面试" value="interview" />
        <el-option label="Choice 选择" value="choice" />
        <el-option label="Vocabulary 单词" value="vocabulary" />
      </el-select>
      <el-button @click="loadCards">查询</el-button>
    </div>

    <!-- 卡片列表 -->
    <div v-if="selectedCards.length > 0" class="batch-bar">
      <span>已选择 <strong>{{ selectedCards.length }}</strong> 张</span>
      <el-button size="small" @click="clearSelection">清除选择</el-button>
      <el-button
        size="small"
        type="danger"
        :icon="Delete"
        :loading="batchDeleting"
        @click="handleBatchDelete"
      >
        批量删除（{{ selectedCards.length }}）
      </el-button>
    </div>
    <el-table :data="cards" stripe style="width: 100%" row-key="id" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="44" />
      <el-table-column label="#" width="60" type="index" />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">
          <el-tag :type="typeTag(row.card_type)" size="small">{{ typeLabel(row.card_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="正面" min-width="200">
        <template #default="{ row }">
          <span>{{ frontText(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="背面" min-width="200">
        <template #default="{ row }">
          <span style="color: #606266">{{ backText(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="标签" width="200">
        <template #default="{ row }">
          <el-tag v-for="t in row.tags" :key="t.id" :color="t.color" size="small" style="margin-right: 4px">
            {{ t.name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" text :icon="View" @click="showDetail(row)">查看</el-button>
          <el-button size="small" text :icon="Link" @click="openAssociateDialog(row)">联想</el-button>
          <el-button size="small" text :icon="Edit" @click="$router.push(`/cards/${row.id}/edit`)">编辑</el-button>
          <el-button size="small" text :icon="Delete" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="display: flex; justify-content: center; margin-top: 16px">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="loadCards"
        @current-change="loadCards"
      />
    </div>

    <!-- 详情 Dialog -->
    <el-dialog v-model="detailVisible" title="卡片详情" width="600px">
      <div v-if="currentCard">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="类型">{{ typeLabel(currentCard.card_type) }}</el-descriptions-item>
          <el-descriptions-item label="正面">
            <pre style="white-space: pre-wrap; font-family: inherit; margin: 0">{{ JSON.stringify(currentCard.front_content, null, 2) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="背面">
            <pre style="white-space: pre-wrap; font-family: inherit; margin: 0">{{ JSON.stringify(currentCard.back_content, null, 2) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="补充">{{ currentCard.explanation || '—' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- 联想管理 Dialog -->
    <el-dialog v-model="associateVisible" title="联想管理" width="680px" @open="loadAssociateData">
      <div v-if="associateCurrentCard">
        <!-- 当前卡预览 -->
        <div style="padding: 12px 16px; background: rgba(255,248,245,0.8); border-radius: 10px; margin-bottom: 18px">
          <div style="font-size: 12px; color: var(--color-muted, #909399); margin-bottom: 4px">当前卡片</div>
          <div style="font-weight: 500">{{ frontText(associateCurrentCard) }}</div>
        </div>

        <!-- 已有联想列表 -->
        <div style="margin-bottom: 20px">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px">
            <span style="font-size: 14px; font-weight: 500">
              <i class="fa-solid fa-link" style="color: var(--el-color-primary); margin-right: 6px"></i>
              已有联想 ({{ associateLinks.length }})
            </span>
          </div>

          <div v-if="associateLinks.length === 0" style="text-align: center; padding: 24px; color: #909399; font-size: 13px">
            还没有关联，在下方添加第一条吧 ✨
          </div>

          <div v-else style="display: flex; flex-direction: column; gap: 8px">
            <div
              v-for="link in associateLinks"
              :key="link.id"
              style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: #faf9f7; border-radius: 8px; border: 1px solid #f0ebe6"
            >
              <div style="flex: 1; min-width: 0; display: flex; align-items: center; gap: 10px">
                <el-tag size="small" effect="light" type="primary" style="flex-shrink: 0">{{ link.relation_label }}</el-tag>
                <span style="color: #303133; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                  {{ link.target_card_preview }}
                </span>
                <span v-if="link.note" style="color: #909399; font-size: 12px; flex-shrink: 0; margin-left: auto">
                  备注：{{ link.note }}
                </span>
              </div>
              <el-button
                size="small"
                text
                type="danger"
                :icon="Delete"
                style="flex-shrink: 0; margin-left: 8px"
                @click="handleDeleteLink(link)"
              />
            </div>
          </div>
        </div>

        <el-divider style="margin: 18px 0" />

        <!-- 添加新联想 -->
        <div>
          <div style="font-size: 14px; font-weight: 500; margin-bottom: 12px">
            <i class="fa-solid fa-plus" style="color: var(--mint-green, #67c23a); margin-right: 6px"></i>
            添加新联想
          </div>

          <el-form :model="newLink" label-position="top">
            <div style="display: grid; grid-template-columns: 1fr 180px; gap: 14px">
              <el-form-item label="目标卡片">
                <el-select
                  v-model="newLink.target_card_id"
                  placeholder="选一张要关联的卡片"
                  filterable
                  :loading="allCardsLoading"
                  style="width: 100%"
                >
                  <el-option
                    v-for="c in allCards"
                    :key="c.id"
                    :label="frontText(c)"
                    :value="c.id"
                    :disabled="c.id === associateCurrentCard?.id"
                  >
                    <span>{{ frontText(c) }}</span>
                    <span style="float: right; color: #909399; font-size: 12px; margin-right: 8px">
                      {{ typeLabel(c.card_type) }}
                    </span>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="关系类型">
                <el-select v-model="newLink.relation_type" style="width: 100%">
                  <el-option label="相似" value="similar" />
                  <el-option label="前置知识" value="prerequisite" />
                  <el-option label="包含" value="contains" />
                  <el-option label="对比" value="contrast" />
                  <el-option label="自定义" value="custom" />
                </el-select>
              </el-form-item>
            </div>

            <el-form-item label="备注（可选）">
              <el-input
                v-model="newLink.note"
                placeholder="补充说明一下为什么关联"
                maxlength="100"
                show-word-limit
              />
            </el-form-item>

            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px">
              <el-button @click="resetNewLink">重置</el-button>
              <el-button type="primary" :disabled="!newLink.target_card_id" @click="handleCreateLink">
                <i class="fa-solid fa-link" style="margin-right: 5px"></i>创建关联
              </el-button>
            </div>
          </el-form>
        </div>
      </div>
    </el-dialog>

    <!-- 批量导入 Dialog -->
    <el-dialog v-model="importDialogVisible" title="批量导入卡片" width="620px" destroy-on-close>
      <div style="margin-bottom: 16px; padding: 12px; background: #f7f4f0; border-radius: 8px; font-size: 13px; color: #7a6f68; line-height: 1.8">
        <div style="font-weight: 600; margin-bottom: 6px; color: #5c4d45">
          <i class="fa-solid fa-circle-info" style="margin-right: 6px; color: var(--el-color-primary)"></i>
          支持 JSON 数组格式
        </div>
        <div>每行一张卡片对象，字段说明：</div>
        <code style="display: block; margin-top: 6px; background: #fff; padding: 8px 10px; border-radius: 6px; font-size: 12px; color: #6b5b95">
          { "card_type": "basic", "front_content": "问题", "back_content": "答案", "explanation": "可选解释" }
        </code>
        <div style="margin-top: 8px">card_type 可选值：<code>basic</code>（基础）、<code>interview</code>（面试）、<code>choice</code>（选择）、<code>vocabulary</code>（单词）</div>
      </div>

      <!-- 方式 1：粘贴 JSON -->
      <div style="margin-bottom: 12px">
        <div style="font-size: 13px; color: #7a6f68; margin-bottom: 6px">① 粘贴 JSON：</div>
        <el-input
          v-model="importJsonText"
          type="textarea"
          :rows="6"
          placeholder='[{"card_type":"basic","front_content":"Q","back_content":"A"}]'
        />
      </div>

      <div style="text-align: center; color: #c4b8b0; font-size: 12px; margin: 4px 0 12px">— 或者 —</div>

      <!-- 方式 2：上传 JSON 文件 -->
      <div>
        <div style="font-size: 13px; color: #7a6f68; margin-bottom: 6px">② 上传 .json 文件：</div>
        <el-upload
          :auto-upload="false"
          :show-file-list="true"
          :on-change="handleImportFileChange"
          :limit="1"
          accept=".json"
        >
          <el-button :icon="Upload">选择文件</el-button>
        </el-upload>
      </div>

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImportSubmit">
          <i class="fa-solid fa-upload" style="margin-right: 5px"></i>
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Plus, Search, View, Edit, Delete, Link, Upload } from '@element-plus/icons-vue'
import { deckApi, type DeckData } from '../../api/decks'
import { cardApi, type CardData } from '../../api/cards'
import { associateApi, type CardLinkOut } from '../../api/associate'

const route = useRoute()
const router = useRouter()
const deckId = computed(() => Number(route.params.id))

const deck = ref<DeckData | null>(null)
const loading = ref(false)
const cards = ref<CardData[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const cardType = ref<string | undefined>(undefined)

// 批量选择
const selectedCards = ref<CardData[]>([])
const batchDeleting = ref(false)
function handleSelectionChange(selection: CardData[]) {
  selectedCards.value = selection
}
function clearSelection() {
  selectedCards.value = []
}
async function handleBatchDelete() {
  if (selectedCards.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedCards.value.length} 张卡片吗？此操作不可恢复。`,
      '批量删除确认',
      { type: 'warning' }
    )
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const ids = selectedCards.value.map((c) => c.id)
    await cardApi.batchDelete(ids)
    ElMessage.success(`已删除 ${ids.length} 张卡片`)
    selectedCards.value = []
    await loadCards()
  } finally {
    batchDeleting.value = false
  }
}

// ===== 批量导入 =====
const importDialogVisible = ref(false)
const importJsonText = ref('')
const importing = ref(false)

function handleImportFileChange(file: any) {
  const raw = file.raw
  if (!raw) return
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = String(e.target?.result || '')
    importJsonText.value = text
  }
  reader.readAsText(raw)
}

async function handleImportSubmit() {
  let cards: any[]
  try {
    cards = JSON.parse(importJsonText.value)
  } catch (err: any) {
    ElMessage.error('JSON 解析失败：' + err.message)
    return
  }
  if (!Array.isArray(cards) || cards.length === 0) {
    ElMessage.error('请提供有效的卡片数组')
    return
  }

  importing.value = true
  try {
    await cardApi.import({ deck_id: deckId.value, cards })
    ElMessage.success(`🎉 成功导入 ${cards.length} 张卡片`)
    importDialogVisible.value = false
    importJsonText.value = ''
    await loadCards()
  } finally {
    importing.value = false
  }
}

const detailVisible = ref(false)
const currentCard = ref<CardData | null>(null)

// 联想管理状态
const associateVisible = ref(false)
const associateCurrentCard = ref<CardData | null>(null)
const associateLinks = ref<CardLinkOut[]>([])
const allCards = ref<CardData[]>([])
const allCardsLoading = ref(false)
const newLink = ref<{ target_card_id: number | null; relation_type: string; note: string }>({
  target_card_id: null,
  relation_type: 'similar',
  note: '',
})

function typeLabel(t: string) {
  return ({ basic: '基础', interview: '面试', choice: '选择', vocabulary: '单词' } as Record<string, string>)[t] || t
}
function typeTag(t: string) {
  return ({ basic: 'info', interview: '', choice: 'warning', vocabulary: 'success' } as Record<string, string>)[t] || 'info'
}
function frontText(c: CardData): string {
  const f = c.front_content
  if (c.card_type === 'basic') return f.content || '—'
  if (c.card_type === 'interview') return f.question || '—'
  if (c.card_type === 'choice') return f.question || '—'
  if (c.card_type === 'vocabulary') return f.word || '—'
  return JSON.stringify(f).slice(0, 60)
}
function backText(c: CardData): string {
  const b = c.back_content
  if (c.card_type === 'basic') return b.content || '—'
  if (c.card_type === 'interview') return b.answer?.slice(0, 60) || '—'
  if (c.card_type === 'choice') {
    const ans = b.correct_answer?.join(',') || '—'
    const exp = b.explanation || ''
    return `答案: ${ans} ${exp}`.trim()
  }
  if (c.card_type === 'vocabulary') return b.cn_meaning || b.en_meaning || '—'
  return JSON.stringify(b).slice(0, 60)
}

async function loadDeck() {
  loading.value = true
  try {
    const res = await deckApi.get(deckId.value)
    deck.value = res.data || (res.data as any)
  } finally {
    loading.value = false
  }
}

async function loadCards() {
  loading.value = true
  try {
    const res = await cardApi.list({
      deck_id: deckId.value,
      card_type: cardType.value,
      keyword: keyword.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    const data = res.data || (res.data as any)
    cards.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

function openCreateCard() {
  router.push(`/cards/new?deck_id=${deckId.value}`)
}

function showDetail(card: CardData) {
  currentCard.value = card
  detailVisible.value = true
}

async function handleDelete(card: CardData) {
  try {
    await ElMessageBox.confirm('确定删除这张卡片吗？', '确认', { type: 'warning' })
    await cardApi.remove(card.id)
    ElMessage.success('已删除')
    await loadCards()
  } catch {
    // 用户取消
  }
}

// ---------- 联想管理 ----------
async function openAssociateDialog(card: CardData) {
  associateCurrentCard.value = card
  associateVisible.value = true
}

async function loadAssociateData() {
  if (!associateCurrentCard.value) return
  // 加载已有联想
  try {
    const res = await associateApi.list(associateCurrentCard.value.id)
    associateLinks.value = (res.data as any) || []
  } catch {
    associateLinks.value = []
  }
  // 加载所有卡片（供下拉选择）
  await loadAllCards()
  resetNewLink()
}

async function loadAllCards() {
  allCardsLoading.value = true
  try {
    // 传 page_size=100 拿足够多的卡片做下拉（后端限制 max=100）
    const res = await cardApi.list({ page_size: 100 })
    const data = (res.data as any)
    allCards.value = data.items || []
  } catch {
    allCards.value = []
  } finally {
    allCardsLoading.value = false
  }
}

function resetNewLink() {
  newLink.value = { target_card_id: null, relation_type: 'similar', note: '' }
}

async function handleCreateLink() {
  if (!associateCurrentCard.value || !newLink.value.target_card_id) return
  try {
    await associateApi.create(
      associateCurrentCard.value.id,
      newLink.value.target_card_id,
      newLink.value.relation_type,
      newLink.value.note || undefined,
    )
    ElMessage.success('关联已创建')
    // 刷新列表
    const res = await associateApi.list(associateCurrentCard.value.id)
    associateLinks.value = (res.data as any) || []
    resetNewLink()
  } catch (e: any) {
    // 拦截器已弹过 toast
  }
}

async function handleDeleteLink(link: CardLinkOut) {
  try {
    await ElMessageBox.confirm(
      `移除这条「${link.relation_label} → ${link.target_card_preview}」关联？`,
      '移除联想',
      { type: 'warning' },
    )
    if (!associateCurrentCard.value) return
    await associateApi.delete(associateCurrentCard.value.id, link.id)
    ElMessage.success('已移除')
    // 乐观更新
    associateLinks.value = associateLinks.value.filter(l => l.id !== link.id)
  } catch {
    // 用户取消
  }
}

onMounted(async () => {
  await loadDeck()
  await loadCards()
})

watch(() => route.params.id, () => {
  loadDeck()
  loadCards()
})
</script>

<style scoped>
.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #fff5f0 0%, #f0f5ff 100%);
  border: 1px solid rgba(230, 159, 175, 0.3);
  border-radius: 10px;
  margin-bottom: 12px;
  animation: slide-down 0.2s ease-out;
}
.batch-bar span { font-size: 13px; color: #6b6660; }
.batch-bar strong { color: #e27a7a; }
@keyframes slide-down {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
