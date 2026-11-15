<template>
  <div class="tags-page">
    <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center">
      <div>
        <h2 style="margin: 0; font-size: 22px">🏷️ 标签管理</h2>
        <p style="color: #9a9590; margin: 4px 0 0 0; font-size: 13px">
          统一管理你所有的学习标签，给卡片打上标签可以更灵活地筛选和复习
        </p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建标签</el-button>
    </div>

    <!-- 统计卡 -->
    <div class="stats-row">
      <div class="stat-card rose">
        <div class="stat-num">{{ tags.length }}</div>
        <div class="stat-label">标签总数</div>
      </div>
      <div class="stat-card mint">
        <div class="stat-num">{{ totalCardTagged }}</div>
        <div class="stat-label">被标记卡片</div>
      </div>
      <div class="stat-card peach">
        <div class="stat-num">{{ topTag?.name || '—' }}</div>
        <div class="stat-label">使用最多</div>
      </div>
    </div>

    <!-- 搜索 -->
    <div style="margin: 20px 0 12px">
      <el-input
        v-model="keyword"
        placeholder="搜索标签"
        clearable
        :prefix-icon="Search"
        style="max-width: 320px"
        @keyup.enter="load"
        @clear="load"
      />
    </div>

    <!-- 标签列表 -->
    <el-table v-loading="loading" :data="filteredTags" stripe style="width: 100%">
      <el-table-column label="#" width="60" type="index" />
      <el-table-column label="标签" min-width="200">
        <template #default="{ row }">
          <el-tag :color="row.color || '#e69faf'" :style="{ background: (row.color || '#e69faf') + '22', borderColor: row.color || '#e69faf', color: row.color || '#c76a7a' }" effect="light">
            {{ row.name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="color" label="颜色" width="140">
        <template #default="{ row }">
          <span class="color-dot" :style="{ background: row.color || '#e69faf' }"></span>
          <span style="color: #9a9590; font-size: 12px">{{ row.color || '默认' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="使用次数" width="110">
        <template #default="{ row }">
          <el-badge :value="row.card_count" class="card-count-badge" />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button link size="small" type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && filteredTags.length === 0" description="还没有标签，点击右上角新建一个吧 🏷️" />

    <!-- 新建/编辑 Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑标签' : '新建标签'" width="420px" destroy-on-close>
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="例如：重点、错题、面试高频" maxlength="30" show-word-limit />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="form.color" show-alpha />
          <div style="font-size: 12px; color: #9a9590; margin-top: 6px">选一个喜欢的颜色来区分不同类型的标签</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Edit, Delete } from '@element-plus/icons-vue'
import { tagApi, type TagData } from '../api/tags'

const loading = ref(false)
const submitting = ref(false)
const tags = ref<TagData[]>([])
const keyword = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const form = ref<{ name: string; color: string }>({ name: '', color: '#e69faf' })

const filteredTags = computed(() => {
  if (!keyword.value) return tags.value
  const k = keyword.value.toLowerCase()
  return tags.value.filter((t) => t.name.toLowerCase().includes(k))
})

const totalCardTagged = computed(() => tags.value.reduce((s, t) => s + (t.card_count || 0), 0))
const topTag = computed(() => {
  if (tags.value.length === 0) return null
  return [...tags.value].sort((a, b) => (b.card_count || 0) - (a.card_count || 0))[0]
})

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

async function load() {
  loading.value = true
  try {
    const res = await tagApi.list()
    tags.value = res.data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = { name: '', color: '#e69faf' }
  dialogVisible.value = true
}

function openEdit(t: TagData) {
  isEdit.value = true
  editingId.value = t.id
  form.value = { name: t.name, color: t.color || '#e69faf' }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入标签名称')
    return
  }
  submitting.value = true
  try {
    if (isEdit.value && editingId.value !== null) {
      await tagApi.update(editingId.value, form.value)
      ElMessage.success('✅ 标签已更新')
    } else {
      await tagApi.create(form.value)
      ElMessage.success('✅ 标签已创建')
    }
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(t: TagData) {
  try {
    await ElMessageBox.confirm(`确定删除标签「${t.name}」吗？已标记的卡片不会被删除。`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await tagApi.remove(t.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}
.stat-card {
  padding: 18px 20px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(242, 198, 208, 0.25);
}
.stat-card.rose { border-top: 3px solid #e69faf; }
.stat-card.mint { border-top: 3px solid #7ca982; }
.stat-card.peach { border-top: 3px solid #e6b88a; }
.stat-num {
  font-size: 24px;
  font-weight: 600;
  color: #3d2e2a;
  letter-spacing: -0.5px;
}
.stat-label { font-size: 12px; color: #9a9590; margin-top: 2px; }

.color-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08);
}
.card-count-badge :deep(.el-badge__content) {
  background: linear-gradient(135deg, #e69faf, #d48090);
}
</style>
