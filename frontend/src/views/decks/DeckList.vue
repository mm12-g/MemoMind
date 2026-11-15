<template>
  <div>
    <!-- 头部 -->
    <div style="display: flex; justify-content: flex-end; margin-bottom: 20px">
      <el-button type="primary" :icon="Plus" @click="openCreate">新建知识库</el-button>
    </div>

    <!-- 筛选 -->
    <el-card style="margin-bottom: 16px">
      <div style="display: flex; gap: 12px">
        <el-input
          v-model="keyword"
          placeholder="搜索知识库名称"
          clearable
          :prefix-icon="Search"
          style="width: 240px"
          @keyup.enter="load"
        />
        <el-select
          v-model="category"
          placeholder="全部分类"
          clearable
          style="width: 180px"
          @change="load"
        >
          <el-option label="通用" value="general" />
          <el-option label="面试" value="interview" />
          <el-option label="考试" value="exam" />
          <el-option label="英语" value="vocabulary" />
        </el-select>
        <el-button @click="load">查询</el-button>
      </div>
    </el-card>

    <!-- 列表 -->
    <el-row :gutter="16" v-if="decks.length > 0">
      <el-col :span="8" v-for="deck in decks" :key="deck.id" style="margin-bottom: 16px">
        <el-card shadow="hover" class="deck-card" @click="$router.push(`/decks/${deck.id}`)">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 600">{{ deck.name }}</span>
              <el-tag :type="categoryTagType(deck.category)" size="small">
                {{ categoryLabel(deck.category) }}
              </el-tag>
            </div>
          </template>
          <p style="color: #909399; font-size: 13px; margin: 0; min-height: 40px">
            {{ deck.description || '暂无描述' }}
          </p>
          <div style="display: flex; justify-content: space-between; margin-top: 12px; font-size: 13px; color: #606266">
            <span><strong style="color: #303133; font-size: 18px">{{ deck.card_count }}</strong> 张卡片</span>
            <div>
              <el-button size="small" text :icon="Edit" @click.stop="openEdit(deck)" />
              <el-button size="small" text :icon="Delete" type="danger" @click.stop="handleDelete(deck)" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-else description="还没有知识库，点右上角创建一个吧" />

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑知识库' : '新建知识库'" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="例如: Python 面试题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="通用" value="general" />
            <el-option label="面试" value="interview" />
            <el-option label="考试" value="exam" />
            <el-option label="英语" value="vocabulary" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Edit, Delete } from '@element-plus/icons-vue'
import { deckApi, type DeckData } from '../../api/decks'

const router = useRouter()

const decks = ref<DeckData[]>([])
const keyword = ref('')
const category = ref<string | undefined>(undefined)

const dialogVisible = ref(false)
const editing = ref<DeckData | null>(null)
const saving = ref(false)
const form = ref({ name: '', description: '', category: 'general' as 'general' | 'interview' | 'exam' | 'vocabulary' })

function categoryLabel(c: string) {
  return ({ general: '通用', interview: '面试', exam: '考试', vocabulary: '英语' } as Record<string, string>)[c] || c
}
function categoryTagType(c: string) {
  return ({ general: 'info', interview: '', exam: 'warning', vocabulary: 'success' } as Record<string, string>)[c] || 'info'
}

async function load() {
  const res = await deckApi.list({ keyword: keyword.value || undefined, category: category.value })
  decks.value = res.data?.items || (res.data as any)?.items || []
}

function openCreate() {
  editing.value = null
  form.value = { name: '', description: '', category: 'general' }
  dialogVisible.value = true
}

function openEdit(deck: DeckData) {
  editing.value = deck
  form.value = { name: deck.name, description: deck.description || '', category: deck.category as any }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await deckApi.update(editing.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await deckApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await load()
  } catch {
    // 错误由拦截器处理
  } finally {
    saving.value = false
  }
}

async function handleDelete(deck: DeckData) {
  try {
    await ElMessageBox.confirm(`确定删除知识库「${deck.name}」吗？其中的卡片也会被删除。`, '确认', {
      type: 'warning',
    })
    await deckApi.remove(deck.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    // 用户取消
  }
}

onMounted(load)
</script>

<style scoped>
.deck-card {
  cursor: pointer;
  transition: all 0.2s;
}
.deck-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
</style>
