<template>
  <div v-if="!session">
    <el-form label-width="80px" inline>
      <el-form-item label="知识库">
        <el-select v-model="deckId" placeholder="全部 interview 卡片" clearable style="width: 220px">
          <el-option v-for="d in decks" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="题目数">
        <el-input-number v-model="count" :min="1" :max="20" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="starting" @click="start">开始</el-button>
      </el-form-item>
    </el-form>
  </div>

  <div v-else style="max-width: 720px; margin: 0 auto">
    <!-- 进度 -->
    <div style="display: flex; justify-content: space-between; margin-bottom: 12px">
      <span>第 {{ index + 1 }} / {{ session.cards.length }} 题</span>
      <el-button text @click="quit">退出</el-button>
    </div>
    <el-progress :percentage="progressPct" :show-text="false" style="margin-bottom: 24px" />

    <!-- 问题 -->
    <el-card shadow="never">
      <h3 style="margin: 0 0 12px">{{ current.question }}</h3>
      <div style="margin-bottom: 16px">
        <el-tag v-for="kw in current.keywords" :key="kw" size="small" style="margin-right: 6px">
          {{ kw }}
        </el-tag>
        <el-rate :model-value="current.difficulty" disabled size="small" style="margin-left: 8px" />
      </div>

      <el-input
        v-model="userAnswer"
        type="textarea"
        :rows="6"
        placeholder="请写出你的回答，按 Ctrl+Enter 提交评分"
        @keydown.ctrl.enter="doEvaluate"
      />
      <div style="display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end">
        <el-button :disabled="index === 0" @click="prev">上一题</el-button>
        <el-button type="primary" :loading="evaluating" :disabled="!userAnswer.trim()" @click="doEvaluate">
          AI 评分 & 下一题
        </el-button>
      </div>
    </el-card>

    <!-- AI 评分结果 -->
    <el-card v-if="feedback" shadow="never" style="margin-top: 16px" class="feedback-card">
      <template #header>
        <strong>AI 评分结果</strong>
        <el-tag :type="scoreTag(feedback.score)" style="margin-left: 8px">{{ feedback.score }} / 10</el-tag>
      </template>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px">
        <div><span style="color: #909399">正确率</span> {{ (feedback.accuracy * 100).toFixed(0) }}%</div>
        <div><span style="color: #909399">完整度</span> {{ (feedback.completeness * 100).toFixed(0) }}%</div>
      </div>
      <div v-if="feedback.errors?.length" style="margin-top: 12px">
        <strong style="color: #f56c6c; font-size: 13px">错误点：</strong>
        <ul style="margin: 4px 0 0; padding-left: 20px; color: #606266; font-size: 13px">
          <li v-for="(e, i) in feedback.errors" :key="i">{{ e }}</li>
        </ul>
      </div>
      <div v-if="feedback.missing?.length" style="margin-top: 8px">
        <strong style="color: #e6a23c; font-size: 13px">遗漏点：</strong>
        <ul style="margin: 4px 0 0; padding-left: 20px; color: #606266; font-size: 13px">
          <li v-for="(m, i) in feedback.missing" :key="i">{{ m }}</li>
        </ul>
      </div>
      <div style="margin-top: 12px; padding: 10px; background: #f5f7fa; border-radius: 6px; font-size: 13px">
        {{ feedback.feedback }}
      </div>
    </el-card>

    <!-- 完成 -->
    <el-result v-if="showFinish" icon="success" title="面试训练完成！" :sub-title="`平均分 ${avgScore.toFixed(1)}`">
      <template #extra>
        <el-button type="primary" @click="$router.push('/practice')">返回专项训练</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { practiceApi, type InterviewStartResult } from '../../api/practice'
import { deckApi, type DeckData } from '../../api/decks'

const decks = ref<DeckData[]>([])
const deckId = ref<number | undefined>(undefined)
const count = ref(5)
const starting = ref(false)

const session = ref<InterviewStartResult | null>(null)
const sessionId = ref<number | null>(null)
const index = ref(0)
const userAnswer = ref('')
const evaluating = ref(false)
const feedback = ref<any>(null)
const scores = ref<any[]>([])
const showFinish = ref(false)

const current = computed(() => session.value?.cards[index.value])
const progressPct = computed(() => {
  if (!session.value) return 0
  return Math.round(index.value / session.value.cards.length * 100)
})
const avgScore = computed(() => {
  if (!scores.value.length) return 0
  return scores.value.reduce((a, b) => a + (b.score || 0), 0) / scores.value.length
})

function scoreTag(s: number) {
  if (s >= 8) return 'success'
  if (s >= 6) return 'warning'
  return 'danger'
}

async function start() {
  starting.value = true
  try {
    const res = await practiceApi.startInterview({ deck_id: deckId.value, count: count.value })
    session.value = (res.data as any) as InterviewStartResult
    sessionId.value = (res.data as any).session_id
    index.value = 0
    userAnswer.value = ''
    feedback.value = null
  } catch {
    // 拦截
  } finally {
    starting.value = false
  }
}

function prev() {
  if (index.value > 0) {
    index.value--
    userAnswer.value = ''
    feedback.value = scores.value[index.value]?.feedback || null
  }
}

async function doEvaluate() {
  if (!current.value || evaluating.value) return
  evaluating.value = true
  try {
    const res = await practiceApi.evaluateInterview(current.value.card_id, userAnswer.value)
    const data = res.data as any
    feedback.value = data
    scores.value[index.value] = {
      card_id: current.value.card_id,
      score: data.score,
      feedback: data,
    }

    // 下一题 or 完成
    if (index.value + 1 < session.value!.cards.length) {
      index.value++
      userAnswer.value = ''
      feedback.value = null
    } else {
      showFinish.value = true
      await practiceApi.completeInterview(sessionId.value!, scores.value.map(s => ({ card_id: s.card_id, score: s.score })))
    }
  } catch {
    // 拦截
  } finally {
    evaluating.value = false
  }
}

function quit() {
  session.value = null
  showFinish.value = false
  scores.value = []
}

onMounted(async () => {
  try {
    const res = await deckApi.list()
    decks.value = res.data?.items || (res.data as any)?.items || []
  } catch {
    //
  }
})
</script>

<style scoped>
.feedback-card {
  border-left: 4px solid #409eff;
}
</style>
