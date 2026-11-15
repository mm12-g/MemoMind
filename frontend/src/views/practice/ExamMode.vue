<template>
  <div v-if="!started">
    <el-form label-width="80px" inline>
      <el-form-item label="知识库">
        <el-select v-model="deckId" placeholder="全部 choice 卡片" clearable style="width: 220px">
          <el-option v-for="d in decks" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="题目数">
        <el-input-number v-model="count" :min="1" :max="50" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="starting" @click="start">开始考试</el-button>
      </el-form-item>
    </el-form>
  </div>

  <!-- 答题中 -->
  <div v-else-if="!submitted" style="max-width: 720px; margin: 0 auto">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <span>第 {{ index + 1 }} / {{ exam.cards.length }} 题</span>
      <el-tag type="warning">
        <el-icon><Timer /></el-icon>
        {{ formatTime(remaining) }}
      </el-tag>
    </div>
    <el-progress :percentage="progressPct" :show-text="false" style="margin-bottom: 24px" />

    <el-card shadow="never">
      <div style="margin-bottom: 12px">
        <el-tag size="small" :type="current.is_multiple ? 'warning' : ''">
          {{ current.is_multiple ? '多选题' : '单选题' }}
        </el-tag>
      </div>
      <h3 style="margin: 0 0 16px">{{ current.question }}</h3>

      <el-radio-group
        v-if="!current.is_multiple"
        v-model="answers[current.card_id]"
        @change="saveAnswer"
      >
        <el-radio
          v-for="(opt, i) in current.options"
          :key="i"
          :value="i"
          style="display: flex; margin-bottom: 12px"
        >
          <strong style="margin-right: 8px">{{ String.fromCharCode(65 + i) }}.</strong>{{ opt }}
        </el-radio>
      </el-radio-group>

      <el-checkbox-group
        v-else
        v-model="answers[current.card_id]"
        @change="saveAnswer"
      >
        <el-checkbox
          v-for="(opt, i) in current.options"
          :key="i"
          :value="i"
          :label="i"
          style="display: flex; margin-bottom: 12px"
        >
          <strong style="margin-right: 8px">{{ String.fromCharCode(65 + i) }}.</strong>{{ opt }}
        </el-checkbox>
      </el-checkbox-group>
    </el-card>

    <!-- 题号导航 -->
    <div style="margin-top: 16px; display: flex; flex-wrap: wrap; gap: 6px; justify-content: center">
      <el-button
        v-for="(c, i) in exam.cards"
        :key="c.card_id"
        size="small"
        :type="i === index ? 'primary' : answered(c.card_id) ? 'success' : 'default'"
        @click="index = i"
      >{{ i + 1 }}</el-button>
    </div>

    <div style="display: flex; justify-content: space-between; margin-top: 16px">
      <el-button :disabled="index === 0" @click="index--">上一题</el-button>
      <el-button v-if="index < exam.cards.length - 1" type="primary" @click="index++">下一题</el-button>
      <el-button v-else type="success" :loading="submitting" @click="submit">提交试卷</el-button>
    </div>
  </div>

  <!-- 成绩 -->
  <div v-else-if="result" style="max-width: 720px; margin: 0 auto">
    <el-result
      :icon="result.score >= 60 ? 'success' : 'warning'"
      :title="`考试完成！得分 ${result.score} 分`"
      :sub-title="`答对 ${result.correct} / ${result.total} 题 · 用时 ${formatDuration(result.duration_seconds)}`"
    />

    <el-card style="margin-top: 16px">
      <template #header><strong>答题详情</strong></template>
      <el-table :data="result.details" size="small">
        <el-table-column label="#" width="40" type="index" />
        <el-table-column prop="question" label="题目" show-overflow-tooltip />
        <el-table-column label="你的答案" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.is_correct ? '#67c23a' : '#f56c6c' }">
              {{ formatAnswer(row.answer, row.options) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="正确答案" width="100">
          <template #default="{ row }">
            {{ formatAnswer(row.correct_answer, row.options) }}
          </template>
        </el-table-column>
        <el-table-column label="结果" width="60">
          <template #default="{ row }">
            <el-tag :type="row.is_correct ? 'success' : 'danger'" size="small">
              {{ row.is_correct ? '✓' : '✗' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div style="text-align: center; margin-top: 20px">
      <el-button type="primary" @click="$router.push('/practice')">返回专项训练</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer } from '@element-plus/icons-vue'
import { practiceApi, type ExamStartResult, type ExamSubmitResult } from '../../api/practice'
import { deckApi, type DeckData } from '../../api/decks'

const decks = ref<DeckData[]>([])
const deckId = ref<number | undefined>(undefined)
const count = ref(10)
const starting = ref(false)

const exam = ref<ExamStartResult | null>(null)
const examId = ref<number | null>(null)
const index = ref(0)
const answers = ref<Record<number, number | number[]>>({})
const submitted = ref(false)
const submitting = ref(false)
const result = ref<ExamSubmitResult | null>(null)

const remaining = ref(0)
let timer: number | null = null

const current = computed(() => exam.value?.cards[index.value])
const progressPct = computed(() => {
  if (!exam.value) return 0
  return Math.round(index.value / exam.value.cards.length * 100)
})

function answered(cardId: number) {
  const a = answers.value[cardId]
  return Array.isArray(a) ? a.length > 0 : a !== undefined && a !== null
}

function saveAnswer() {
  // 答案直接绑在 v-model 上
}

async function start() {
  starting.value = true
  try {
    const res = await practiceApi.startExam({ deck_id: deckId.value, count: count.value })
    exam.value = (res.data as any) as ExamStartResult
    examId.value = (res.data as any).exam_id
    index.value = 0
    submitted.value = false
    result.value = null
    answers.value = {}
    remaining.value = exam.value!.total_count * 90 // 每题 90 秒
    startTimer()
  } catch {
    // 拦截
  } finally {
    starting.value = false
  }
}

function startTimer() {
  stopTimer()
  timer = window.setInterval(() => {
    remaining.value--
    if (remaining.value <= 0) {
      stopTimer()
      submit() // 自动提交
    }
  }, 1000)
}

function stopTimer() {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
}

async function submit() {
  if (submitted.value) return
  submitting.value = true
  submitted.value = true
  stopTimer()

  const list: { card_id: number; answer: number[] }[] = []
  for (const card of exam.value!.cards) {
    const a = answers.value[card.card_id]
    if (a === undefined || a === null) {
      list.push({ card_id: card.card_id, answer: [] })
    } else if (Array.isArray(a)) {
      list.push({ card_id: card.card_id, answer: a })
    } else {
      list.push({ card_id: card.card_id, answer: [a] })
    }
  }

  try {
    const res = await practiceApi.submitExam(examId.value!, list)
    result.value = (res.data as any) as ExamSubmitResult
  } catch {
    submitted.value = false
  } finally {
    submitting.value = false
  }
}

function formatAnswer(idxs: number[], options: string[]) {
  if (!idxs || idxs.length === 0) return '—'
  return idxs.map(i => String.fromCharCode(65 + i)).join(', ')
}
function formatTime(s: number) {
  const m = Math.floor(s / 60), sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}
function formatDuration(s: number | null) {
  if (!s) return '—'
  return `${Math.floor(s / 60)} 分 ${s % 60} 秒`
}

onMounted(async () => {
  try {
    const res = await deckApi.list()
    decks.value = res.data?.items || (res.data as any)?.items || []
  } catch { /* noop */ }
})
onUnmounted(stopTimer)
</script>
