<template>
  <div v-loading="initializing">
    <div style="margin-bottom: 20px">
      <el-button text :icon="ArrowLeft" @click="goBack">返回</el-button>
      <h2 style="margin: 8px 0 0 0">{{ isEdit ? '编辑卡片' : '新建卡片' }}</h2>
    </div>

    <el-card>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <!-- 所属知识库 -->
        <el-form-item label="知识库" prop="deck_id">
          <el-select v-model="form.deck_id" placeholder="选择知识库" style="width: 100%" :disabled="isEdit">
            <el-option
              v-for="d in myDecks"
              :key="d.id"
              :label="d.name"
              :value="d.id"
            />
          </el-select>
        </el-form-item>

        <!-- 卡片类型 -->
        <el-form-item label="卡片类型" prop="card_type">
          <el-segmented v-model="form.card_type" :disabled="isEdit">
            <el-segmented-item label="Basic 基础" value="basic" />
            <el-segmented-item label="Interview 面试" value="interview" />
            <el-segmented-item label="Choice 选择" value="choice" />
            <el-segmented-item label="Vocabulary 单词" value="vocabulary" />
          </el-segmented>
        </el-form-item>

        <!-- ================ Basic 基础 ================ -->
        <template v-if="form.card_type === 'basic'">
          <el-form-item label="问题/正面">
            <el-input
              v-model="form.front_content.content"
              type="textarea"
              :rows="3"
              placeholder="卡片正面显示的问题或内容"
            />
          </el-form-item>
          <el-form-item label="答案/背面">
            <el-input
              v-model="form.back_content.content"
              type="textarea"
              :rows="4"
              placeholder="卡片背面显示的答案"
            />
          </el-form-item>
        </template>

        <!-- ================ Interview 面试 ================ -->
        <template v-else-if="form.card_type === 'interview'">
          <el-form-item label="问题">
            <el-input
              v-model="form.front_content.question"
              type="textarea"
              :rows="3"
              placeholder="技术面试问题"
            />
          </el-form-item>
          <el-form-item label="关键词">
            <el-select
              v-model="form.front_content.keywords"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="回车添加关键词"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="参考答案">
            <el-input
              v-model="form.back_content.answer"
              type="textarea"
              :rows="6"
              placeholder="参考答案内容"
            />
          </el-form-item>
          <el-form-item label="难度">
            <el-rate v-model="form.back_content.difficulty" :max="5" show-text />
          </el-form-item>
        </template>

        <!-- ================ Choice 选择 ================ -->
        <template v-else-if="form.card_type === 'choice'">
          <el-form-item label="题目">
            <el-input
              v-model="form.front_content.question"
              type="textarea"
              :rows="3"
              placeholder="考试题目"
            />
          </el-form-item>
          <el-form-item label="选项">
            <div style="width: 100%">
              <div v-for="(opt, idx) in form.front_content.options" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px">
                <el-input v-model="form.front_content.options[idx]" :placeholder="`选项 ${String.fromCharCode(65 + idx)}`" />
                <el-button
                  type="danger"
                  :icon="Delete"
                  circle
                  :disabled="form.front_content.options.length <= 2"
                  @click="removeOption(idx)"
                />
              </div>
              <el-button size="small" :icon="Plus" @click="addOption">添加选项</el-button>
            </div>
          </el-form-item>
          <el-form-item label="正确答案">
            <div style="width: 100%">
              <el-checkbox v-model="form.front_content.is_multiple">多选题（可多选）</el-checkbox>
              <div style="margin-top: 8px">
                <el-checkbox-group v-model="form.back_content.correct_answer">
                  <el-checkbox
                    v-for="(_, idx) in form.front_content.options"
                    :key="idx"
                    :value="idx"
                    :label="idx"
                  >
                    {{ String.fromCharCode(65 + idx) }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="解析">
            <el-input
              v-model="form.back_content.explanation"
              type="textarea"
              :rows="3"
              placeholder="题目解析（可选）"
            />
          </el-form-item>
        </template>

        <!-- ================ Vocabulary 单词 ================ -->
        <template v-else-if="form.card_type === 'vocabulary'">
          <el-form-item label="单词">
            <el-input v-model="form.front_content.word" placeholder="ephemeral" />
          </el-form-item>
          <el-form-item label="音标">
            <el-input v-model="form.front_content.phonetic" placeholder="/ɪˈfemərəl/" />
          </el-form-item>
          <el-form-item label="中文释义">
            <el-input v-model="form.back_content.cn_meaning" placeholder="短暂的" />
          </el-form-item>
          <el-form-item label="英文释义">
            <el-input v-model="form.back_content.en_meaning" placeholder="lasting a very short time" />
          </el-form-item>
          <el-form-item label="例句">
            <div style="width: 100%">
              <div v-for="(ex, idx) in form.back_content.examples" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px">
                <el-input v-model="form.back_content.examples[idx]" />
                <el-button
                  type="danger"
                  :icon="Delete"
                  circle
                  @click="form.back_content.examples.splice(idx, 1)"
                />
              </div>
              <el-button size="small" :icon="Plus" @click="form.back_content.examples.push('')">添加例句</el-button>
            </div>
          </el-form-item>
          <el-form-item label="词根词缀">
            <el-select
              v-model="form.back_content.roots"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="回车添加"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="同义词">
            <el-select
              v-model="form.back_content.synonyms"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="回车添加"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="反义词">
            <el-select
              v-model="form.back_content.antonyms"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="回车添加"
              style="width: 100%"
            />
          </el-form-item>
        </template>

        <!-- 公共：补充说明 + 标签 -->
        <el-form-item label="补充说明">
          <el-input
            v-model="form.explanation"
            type="textarea"
            :rows="2"
            placeholder="可选"
          />
        </el-form-item>

        <el-form-item label="标签">
          <el-select
            v-model="form.tag_ids"
            multiple
            filterable
            placeholder="选择或创建标签"
            style="width: 100%"
          >
            <el-option
              v-for="t in allTags"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '创建卡片' }}
          </el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { ArrowLeft, Plus, Delete } from '@element-plus/icons-vue'
import { cardApi, type CardData, type CardCreatePayload, type CardUpdatePayload } from '../../api/cards'
import { deckApi, type DeckData } from '../../api/decks'
import { tagApi, type TagData } from '../../api/tags'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => route.name === 'CardEdit')
const editingId = computed(() => Number(route.params.id) || 0)
const initialDeckId = computed(() => Number(route.query.deck_id) || 0)

const formRef = ref<FormInstance>()
const initializing = ref(true)
const saving = ref(false)

const myDecks = ref<DeckData[]>([])
const allTags = ref<TagData[]>([])

function defaultForm(): CardCreatePayload {
  return {
    deck_id: 0,
    card_type: 'basic',
    front_content: { content: '' },
    back_content: { content: '' },
    explanation: '',
    tag_ids: [],
  }
}

const form = reactive<CardCreatePayload>(defaultForm())

const rules = {
  deck_id: [{ required: true, message: '请选择知识库', trigger: 'change' }],
}

function resetContent() {
  const t = form.card_type
  form.front_content = t === 'basic'
    ? { content: '' }
    : t === 'interview'
    ? { question: '', keywords: [] }
    : t === 'choice'
    ? { question: '', options: ['', ''], is_multiple: false }
    : { word: '', phonetic: '', audio_url: null }

  form.back_content = t === 'basic'
    ? { content: '' }
    : t === 'interview'
    ? { answer: '', difficulty: 3 }
    : t === 'choice'
    ? { correct_answer: [], explanation: '' }
    : { cn_meaning: '', en_meaning: '', examples: [], roots: [], synonyms: [], antonyms: [] }
}

watch(() => form.card_type, () => {
  if (!isEdit.value) resetContent()
})

function addOption() {
  form.front_content.options.push('')
}
function removeOption(idx: number) {
  form.front_content.options.splice(idx, 1)
  // 修正 correct_answer 的索引
  form.back_content.correct_answer = form.back_content.correct_answer.filter((i: number) => i !== idx).map((i: number) => (i > idx ? i - 1 : i))
}

async function loadInitial() {
  initializing.value = true
  try {
    // 加载知识库列表
    const decksRes = await deckApi.list()
    myDecks.value = decksRes.data?.items || (decksRes.data as any)?.items || []

    // 加载标签
    const tagsRes = await tagApi.list()
    allTags.value = Array.isArray(tagsRes.data) ? tagsRes.data : []

    if (isEdit.value && editingId.value) {
      const cardRes = await cardApi.get(editingId.value)
      const c: CardData = (cardRes.data || cardRes.data as any) as CardData
      form.deck_id = c.deck_id
      form.card_type = c.card_type
      form.front_content = c.front_content
      form.back_content = c.back_content
      form.explanation = c.explanation || ''
      form.tag_ids = (c.tags || []).map((t) => t.id)
    } else if (initialDeckId.value) {
      form.deck_id = initialDeckId.value
    }
  } finally {
    initializing.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value) {
      const payload: CardUpdatePayload = {
        card_type: form.card_type,
        front_content: form.front_content,
        back_content: form.back_content,
        explanation: form.explanation,
        tag_ids: form.tag_ids,
      }
      await cardApi.update(editingId.value, payload)
      ElMessage.success('保存成功')
      router.push(`/decks/${form.deck_id}`)
    } else {
      const payload: CardCreatePayload = {
        deck_id: form.deck_id,
        card_type: form.card_type,
        front_content: form.front_content,
        back_content: form.back_content,
        explanation: form.explanation || null,
        tag_ids: form.tag_ids,
      }
      await cardApi.create(payload)
      ElMessage.success('创建成功')
      router.push(`/decks/${form.deck_id}`)
    }
  } catch {
    // 错误已拦截
  } finally {
    saving.value = false
  }
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/decks')
}

onMounted(loadInitial)
</script>
