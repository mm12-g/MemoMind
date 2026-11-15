<template>
  <div v-if="!session">
    <el-form label-width="80px" inline>
      <el-form-item label="知识库">
        <el-select v-model="deckId" placeholder="全部 vocabulary 卡片" clearable style="width: 240px">
          <el-option v-for="d in decks" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="模式">
        <el-radio-group v-model="mode">
          <el-radio-button value="cn2en">中文 → 英文</el-radio-button>
          <el-radio-button value="en2cn">英文 → 中文</el-radio-button>
          <el-radio-button value="spelling">拼写模式</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="数量">
        <el-input-number v-model="count" :min="5" :max="50" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="starting" @click="start">开始</el-button>
      </el-form-item>
    </el-form>
  </div>

  <div v-else style="max-width: 600px; margin: 0 auto">
    <div style="display: flex; justify-content: space-between; margin-bottom: 12px">
      <span>第 {{ index + 1 }} / {{ session.cards.length }} 题</span>
      <el-tag :type="showAnswer ? 'success' : 'warning'">
        {{ showAnswer ? (correct ? '✓ 正确' : '✗ 错误') : '等待作答' }}
      </el-tag>
    </div>
    <el-progress :percentage="progressPct" :show-text="false" style="margin-bottom: 24px" />

    <el-card shadow="never" style="text-align: center">
      <!-- 拼写模式：显示音标 + 中文，让用户写单词 -->
      <template v-if="mode === 'spelling'">
        <div class="word-display">{{ current.phonetic || '—' }}</div>
        <div style="color: #909399; margin-bottom: 20px">{{ current.cn_meaning || current.en_meaning }}</div>
      </template>
      <!-- 中→英：显示中文释义 -->
      <template v-else-if="mode === 'cn2en'">
        <div class="word-display">{{ current.cn_meaning || '—' }}</div>
        <div style="color: #909399; margin-bottom: 20px; font-size: 14px">请写出英文单词</div>
      </template>
      <!-- 英→中：显示英文释义 -->
      <template v-else>
        <div class="word-display">{{ current.en_meaning || '—' }}</div>
        <div style="color: #909399; margin-bottom: 20px; font-size: 14px">请写出中文释义</div>
      </template>

      <!-- 用户作答 -->
      <el-input
        v-model="userAnswer"
        size="large"
        :placeholder="answerPlaceholder"
        :disabled="showAnswer"
        @keydown.enter="check"
        style="max-width: 320px; margin: 0 auto"
      />

      <!-- 显示答案后的反馈 -->
      <div v-if="showAnswer" style="margin-top: 20px; text-align: left">
        <div style="color: #303133; font-size: 18px; font-weight: 600">{{ current.word }}</div>
        <div v-if="current.phonetic" style="color: #909399">{{ current.phonetic }}</div>
        <div v-if="current.cn_meaning" style="margin-top: 8px">
          <strong>中文：</strong>{{ current.cn_meaning }}
        </div>
        <div v-if="current.en_meaning" style="margin-top: 4px">
          <strong>英文：</strong>{{ current.en_meaning }}
        </div>
        <div v-if="current.examples?.length" style="margin-top: 12px">
          <div style="color: #909399; font-size: 13px; margin-bottom: 4px">例句</div>
          <div v-for="(e, i) in current.examples" :key="i" style="font-size: 13px; color: #606266">• {{ e }}</div>
        </div>
      </div>

      <!-- 按钮 -->
      <div style="margin-top: 20px">
        <el-button v-if="!showAnswer" type="primary" size="large" :disabled="!userAnswer.trim()" @click="check">
          确认
        </el-button>
        <el-button v-else-if="index < session.cards.length - 1" type="primary" size="large" @click="next">
          下一个
        </el-button>
        <el-button v-else type="success" size="large" @click="finish">
          完成训练
        </el-button>
      </div>
    </el-card>

    <!-- 结果 -->
    <el-result v-if="showResult" icon="success" title="英语训练完成！" :sub-title="`正确率 ${(correctCount / session.cards.length * 100).toFixed(1)}%  答对 ${correctCount} / ${session.cards.length}`">
      <template #extra>
        <el-button type="primary" @click="$router.push('/practice')">返回专项训练</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { practiceApi, type VocabStartResult } from '../../api/practice'
import { deckApi, type DeckData } from '../../api/decks'

const decks = ref<DeckData[]>([])
const deckId = ref<number | undefined>(undefined)
const mode = ref<'spelling' | 'cn2en' | 'en2cn'>('spelling')
const count = ref(10)
const starting = ref(false)

const session = ref<VocabStartResult | null>(null)
const index = ref(0)
const userAnswer = ref('')
const showAnswer = ref(false)
const correct = ref(false)
const correctCount = ref(0)
const showResult = ref(false)

const current = computed(() => session.value?.cards[index.value])
const progressPct = computed(() => {
  if (!session.value) return 0
  return Math.round(index.value / session.value.cards.length * 100)
})
const answerPlaceholder = computed(() => {
  if (mode.value === 'spelling' || mode.value === 'cn2en') return '请输入英文单词'
  return '请输入中文释义'
})

function check() {
  if (!current.value) return
  let target = ''
  if (mode.value === 'spelling' || mode.value === 'cn2en') {
    target = current.value.word
  } else {
    target = current.value.cn_meaning || current.value.en_meaning || ''
  }

  correct.value = userAnswer.value.trim().toLowerCase() === target.trim().toLowerCase()
  if (correct.value) correctCount.value++
  showAnswer.value = true
}

function next() {
  index.value++
  userAnswer.value = ''
  showAnswer.value = false
  correct.value = false
}

function finish() {
  showResult.value = true
}

async function start() {
  starting.value = true
  try {
    const res = await practiceApi.startVocab({ deck_id: deckId.value, mode: mode.value, count: count.value })
    session.value = (res.data as any) as VocabStartResult
    index.value = 0
    showResult.value = false
    showAnswer.value = false
    correctCount.value = 0
    userAnswer.value = ''
  } finally {
    starting.value = false
  }
}

onMounted(async () => {
  try {
    const res = await deckApi.list()
    decks.value = res.data?.items || (res.data as any)?.items || []
  } catch { /* noop */ }
})
</script>

<style scoped>
.word-display {
  font-size: 36px;
  font-weight: 700;
  color: #409eff;
  margin: 20px 0;
}
</style>
