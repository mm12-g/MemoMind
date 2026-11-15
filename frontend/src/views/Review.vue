<template>
  <div>
    <!-- 空闲状态：还没有到期卡片 -->
    <div v-if="phase === 'idle'" style="max-width: 600px; margin: 60px auto; text-align: center">
      <el-result
        icon="success"
        title="太棒了！"
        sub-title="暂无到期的复习卡片，继续保持吧 ✨"
      >
        <template #extra>
          <el-button type="primary" @click="forceRefresh">刷新</el-button>
          <el-button @click="$router.push('/decks')">去添加卡片</el-button>
        </template>
      </el-result>
    </div>

    <!-- 复习中 -->
    <div v-else-if="phase === 'reviewing' && currentCard" style="max-width: 680px; margin: 0 auto">
      <!-- 顶部进度条 -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
        <div style="color: #606266; font-size: 14px">
          进度：<strong>{{ reviewedCount }}</strong> / {{ totalCount }}
        </div>
        <el-button text @click="quitSession" :icon="Close">退出</el-button>
      </div>
      <el-progress
        :percentage="progressPercent"
        :stroke-width="8"
        :show-text="false"
        color="#409eff"
        style="margin-bottom: 32px"
      />

      <!-- 卡片主体 -->
      <el-card shadow="never" class="review-card">
        <!-- 正面 -->
        <div class="card-front" :class="{ 'card-front--large': currentCard.front_content.word }">
          <!-- Basic -->
          <template v-if="currentCard.card_type === 'basic'">
            {{ currentCard.front_content.content }}
          </template>
          <!-- Interview -->
          <template v-else-if="currentCard.card_type === 'interview'">
            <div class="question-tag">面试题</div>
            <div>{{ currentCard.front_content.question }}</div>
            <div v-if="currentCard.front_content.keywords?.length" class="keywords">
              <el-tag v-for="kw in currentCard.front_content.keywords" :key="kw" size="small" style="margin-right: 6px">
                {{ kw }}
              </el-tag>
            </div>
          </template>
          <!-- Choice（正面就是测试题，选项可点） -->
          <template v-else-if="currentCard.card_type === 'choice'">
            <div class="question-tag">{{ currentCard.front_content.is_multiple ? '多选题' : '单选题' }}</div>
            <div style="margin-bottom: 12px">{{ currentCard.front_content.question }}</div>
            <div class="choice-interactive" style="width: 100%">
              <div
                v-for="(opt, i) in currentCard.front_content.options"
                :key="i"
                class="choice-pick-item"
                :class="choicePickClass(i)"
                @click="handleChoicePick(i)"
              >
                <span class="choice-letter">{{ String.fromCharCode(65 + i) }}</span>
                <span>{{ opt }}</span>
                <i
                  v-if="choiceIsCorrectOption(i)"
                  class="fa-solid fa-check choice-icon choice-icon-correct"
                ></i>
                <i
                  v-else-if="choiceIsWrongPick(i)"
                  class="fa-solid fa-xmark choice-icon choice-icon-wrong"
                ></i>
              </div>
            </div>

            <!-- 判定结果提示 -->
            <div v-if="choiceSettled" class="choice-result" :class="choiceIsCorrectPick ? 'choice-result-correct' : 'choice-result-wrong'">
              <template v-if="choiceIsCorrectPick">
                ✅ 选对啦！四档评分或直接下一题 ✨
              </template>
              <template v-else>
                ❌ 不对哦，正确答案是 <strong>{{ correctAnswerLabels }}</strong>
                <el-button size="small" text style="margin-left: 8px" @click="choiceResetPick">重新选</el-button>
              </template>
            </div>
          </template>
          <!-- Vocabulary -->
          <template v-else-if="currentCard.card_type === 'vocabulary'">
            <div class="vocab-word">{{ currentCard.front_content.word }}</div>
            <div v-if="currentCard.front_content.phonetic" class="vocab-phonetic">
              {{ currentCard.front_content.phonetic }}
            </div>
          </template>
        </div>

        <el-divider />

        <!-- 用户回答区 -->
        <el-input
          v-if="currentCard.card_type !== 'vocabulary'"
          v-model="userAnswer"
          type="textarea"
          :rows="2"
          placeholder="输入你的回答（可选），按 Ctrl+Enter 显示答案"
          @keydown="handleKeydown"
          style="margin-bottom: 16px"
        />

        <!-- 显示答案 / 反馈按钮 -->
        <div v-if="!showingAnswer">
          <!-- Choice 类型：选项直接可测 -->
          <template v-if="currentCard?.card_type === 'choice'">
            <!-- 还没判定：提示让用户选 -->
            <div v-if="!choiceSettled" style="text-align: center; color: #909399; margin: 12px 0">
              请选择后系统自动判定 ✨
            </div>

            <!-- 判定后：选对了 → 自动 Good 下一题 -->
            <div v-else-if="choiceIsCorrectPick" style="display: flex; gap: 12px; justify-content: center">
              <el-button
                type="primary"
                size="large"
                class="next-quick-btn"
                :disabled="submitting"
                @click="submit(3)"
              >
                <i class="fa-solid fa-check" style="margin-right: 6px"></i>
                下一题<br /><small class="rating-sub">自动 Good</small>
              </el-button>
            </div>

            <!-- 判定后：选错了 → 自动 Again 重来 -->
            <div v-else style="display: flex; gap: 12px; justify-content: center">
              <el-button
                type="danger"
                size="large"
                class="next-quick-btn"
                :disabled="submitting"
                @click="submit(1)"
              >
                <i class="fa-solid fa-rotate-left" style="margin-right: 6px"></i>
                再练一次<br /><small class="rating-sub">自动 Again</small>
              </el-button>
              <el-button
                size="large"
                :disabled="submitting"
                @click="choiceResetPick"
              >
                <i class="fa-solid fa-eraser" style="margin-right: 6px"></i>
                重新选答案
              </el-button>
            </div>

            <!-- 也能看完整解析 -->
            <div style="margin-top: 12px; text-align: center">
              <el-button text @click="revealAnswer">
                <i class="fa-solid fa-eye" style="margin-right: 4px"></i>
                查看完整答案解析（Space）
              </el-button>
            </div>
          </template>
          <!-- 其他类型：只有"显示答案" -->
          <template v-else>
            <el-button
              type="primary"
              size="large"
              style="width: 100%"
              :disabled="submitting"
              @click="revealAnswer"
            >
              显示答案（Space）
            </el-button>
          </template>
        </div>
        <div v-else>
          <!-- 背面答案展示 -->
          <div class="card-back">
            <!-- Basic -->
            <template v-if="currentCard.card_type === 'basic'">
              <div>{{ currentCard.back_content.content }}</div>
            </template>
            <!-- Interview -->
            <template v-else-if="currentCard.card_type === 'interview'">
              <div class="answer-label">参考答案</div>
              <div style="white-space: pre-wrap">{{ currentCard.back_content.answer }}</div>
              <div style="margin-top: 8px">
                <span style="color: #909399; font-size: 13px">难度：</span>
                <el-rate :model-value="currentCard.back_content.difficulty || 3" disabled size="small" />
              </div>
            </template>
            <!-- Choice 背面：完整答案 + 解析（判定在正面已做过） -->
            <template v-else-if="currentCard.card_type === 'choice'">
              <div class="answer-label">正确答案</div>
              <div style="font-size: 18px; font-weight: 600; color: #67c23a">
                {{ correctAnswerLabels }}
              </div>
              <div v-if="currentCard.back_content.explanation" style="margin-top: 14px; color: #606266; line-height: 1.7">
                <span class="answer-label">解析：</span>{{ currentCard.back_content.explanation }}
              </div>
            </template>
            <!-- Vocabulary -->
            <template v-else-if="currentCard.card_type === 'vocabulary'">
              <div v-if="currentCard.back_content.cn_meaning" class="meaning-row">
                <span class="meaning-label">中文</span>
                <span>{{ currentCard.back_content.cn_meaning }}</span>
              </div>
              <div v-if="currentCard.back_content.en_meaning" class="meaning-row">
                <span class="meaning-label">英文</span>
                <span style="color: #606266; font-style: italic">{{ currentCard.back_content.en_meaning }}</span>
              </div>
              <div v-if="currentCard.back_content.examples?.length" style="margin-top: 12px">
                <div class="meaning-label">例句</div>
                <div v-for="(ex, i) in currentCard.back_content.examples" :key="i" class="example">• {{ ex }}</div>
              </div>
              <div style="display: flex; gap: 24px; margin-top: 12px" v-if="currentCard.back_content.synonyms?.length || currentCard.back_content.antonyms?.length">
                <div v-if="currentCard.back_content.synonyms?.length">
                  <span class="meaning-label">同</span>
                  <el-tag v-for="s in currentCard.back_content.synonyms" :key="s" size="small" style="margin-right: 4px">{{ s }}</el-tag>
                </div>
                <div v-if="currentCard.back_content.antonyms?.length">
                  <span class="meaning-label">反</span>
                  <el-tag v-for="a in currentCard.back_content.antonyms" :key="a" size="small" type="danger" style="margin-right: 4px">{{ a }}</el-tag>
                </div>
              </div>
            </template>

            <div v-if="currentCard.explanation" style="margin-top: 12px; color: #909399; font-size: 13px">
              <strong>补充：</strong>{{ currentCard.explanation }}
            </div>
          </div>

          <!-- 🧠 AI 帮我理解 -->
          <div style="margin: 16px 0 4px; display: flex; justify-content: center">
            <el-button
              v-if="!aiHelpResult"
              plain
              :loading="aiHelpLoading"
              :disabled="aiHelpLoading"
              @click="askAiHelp"
            >
              <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 6px"></i>
              {{ aiHelpLoading ? 'AI 思考中…' : '没太懂？让 AI 帮你理解一下' }}
            </el-button>
          </div>

          <!-- AI 帮助结果 -->
          <div
            v-if="aiHelpResult && !aiHelpLoading"
            class="ai-help-card"
          >
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px">
              <i class="fa-solid fa-robot" style="color: var(--el-color-primary)"></i>
              <span style="font-weight: 500; font-size: 14px">AI 帮你理解</span>
              <el-button
                text
                size="small"
                style="margin-left: auto; color: #909399"
                @click="aiHelpResult = null"
              >收起</el-button>
            </div>

            <!-- 通俗解释 -->
            <div class="ai-help-section">
              <div class="ai-help-label">💡 通俗解释</div>
              <p class="ai-help-text">{{ aiHelpResult.simple_explanation }}</p>
            </div>

            <!-- 类比 -->
            <div v-if="aiHelpResult.analogy" class="ai-help-section">
              <div class="ai-help-label">🎯 生活类比</div>
              <p class="ai-help-text ai-help-analogy">{{ aiHelpResult.analogy }}</p>
            </div>

            <!-- 要点 -->
            <div v-if="aiHelpResult.key_points?.length" class="ai-help-section">
              <div class="ai-help-label">📌 关键要点</div>
              <ul class="ai-help-list">
                <li v-for="(p, i) in aiHelpResult.key_points" :key="i">{{ p }}</li>
              </ul>
            </div>

            <!-- 常见误区 -->
            <div v-if="aiHelpResult.common_misconceptions?.length" class="ai-help-section">
              <div class="ai-help-label">⚠️ 容易搞错的地方</div>
              <ul class="ai-help-list ai-help-warn">
                <li v-for="(m, i) in aiHelpResult.common_misconceptions" :key="i">{{ m }}</li>
              </ul>
            </div>

            <!-- 记忆技巧 -->
            <div v-if="aiHelpResult.memory_tip" class="ai-help-section">
              <div class="ai-help-label">🧠 记忆小技巧</div>
              <p class="ai-help-text ai-help-tip">{{ aiHelpResult.memory_tip }}</p>
            </div>
          </div>

          <el-divider />

          <!-- 相关联想 -->
          <div v-if="cardLinks.length > 0" style="margin-bottom: 14px">
            <div style="font-size: 13px; color: var(--color-muted); margin-bottom: 8px">
              <i class="fa-solid fa-link" style="margin-right: 6px"></i>相关联想
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px">
              <el-tag
                v-for="link in cardLinks"
                :key="link.id"
                effect="plain"
                style="cursor: pointer"
              >
                <span style="color: var(--color-muted); margin-right: 4px; font-size: 11px">{{ link.relation_label }} →</span>
                {{ link.target_card_preview }}
              </el-tag>
            </div>
          </div>

          <!-- 反馈按钮区 -->
          <template v-if="currentCard?.card_type === 'choice'">
            <!-- Choice：判定后自动 rating -->
            <div style="display: flex; gap: 12px; justify-content: center">
              <el-button
                v-if="choiceIsCorrectPick"
                type="primary"
                size="large"
                class="next-quick-btn"
                :disabled="submitting"
                @click="submit(3)"
              >
                <i class="fa-solid fa-check" style="margin-right: 6px"></i>
                下一题<br /><small class="rating-sub">自动 Good</small>
              </el-button>
              <template v-else>
                <el-button
                  type="danger"
                  size="large"
                  class="next-quick-btn"
                  :disabled="submitting"
                  @click="submit(1)"
                >
                  <i class="fa-solid fa-rotate-left" style="margin-right: 6px"></i>
                  再练一次<br /><small class="rating-sub">自动 Again</small>
                </el-button>
                <el-button
                  size="large"
                  :disabled="submitting"
                  @click="choiceResetPick"
                >
                  <i class="fa-solid fa-eraser" style="margin-right: 6px"></i>
                  重新选
                </el-button>
              </template>
            </div>
          </template>
          <template v-else>
            <!-- 非 Choice：四档评分 -->
            <div class="rating-row">
              <el-button size="large" :disabled="submitting" @click="submit(1)">
                Again<br /><small class="rating-sub">重来</small>
              </el-button>
              <el-button size="large" :disabled="submitting" @click="submit(2)">
                Hard<br /><small class="rating-sub">难</small>
              </el-button>
              <el-button type="primary" size="large" :disabled="submitting" @click="submit(3)">
                Good<br /><small class="rating-sub">好</small>
              </el-button>
              <el-button type="success" size="large" :disabled="submitting" @click="submit(4)">
                Easy<br /><small class="rating-sub">易</small>
              </el-button>
            </div>
          </template>
        </div>
      </el-card>
    </div>

    <!-- 结束总结 -->
    <div v-else-if="phase === 'finished'" style="max-width: 560px; margin: 60px auto">
      <div class="finish-wrap">
        <div class="finish-hero">
          <div class="finish-emoji">{{ accuracy >= 80 ? '🌟' : accuracy >= 50 ? '💪' : '🌱' }}</div>
          <h2 class="finish-title">复习完成！</h2>
          <p class="finish-sub">{{ encouragement }}</p>
        </div>

        <div class="finish-stats">
          <div class="fs-card fs-rose">
            <div class="fs-num">{{ reviewedCount }}</div>
            <div class="fs-label">本次复习</div>
          </div>
          <div class="fs-card fs-mint">
            <div class="fs-num">{{ accuracy }}%</div>
            <div class="fs-label">正确率</div>
          </div>
          <div class="fs-card fs-peach">
            <div class="fs-num">{{ avgTimePerCard }}</div>
            <div class="fs-label">单卡平均</div>
          </div>
          <div class="fs-card fs-wood">
            <div class="fs-num">{{ formatDuration(stats.totalMs) }}</div>
            <div class="fs-label">总用时</div>
          </div>
        </div>

        <div class="finish-breakdown">
          <div class="fb-item fb-again"><span>Again</span><strong>{{ stats.again }}</strong></div>
          <div class="fb-item fb-hard"><span>Hard</span><strong>{{ stats.hard }}</strong></div>
          <div class="fb-item fb-good"><span>Good</span><strong>{{ stats.good }}</strong></div>
          <div class="fb-item fb-easy"><span>Easy</span><strong>{{ stats.easy }}</strong></div>
        </div>

        <div class="finish-actions">
          <el-button type="primary" size="large" @click="restart">
            继续复习
          </el-button>
          <el-button size="large" @click="$router.push('/dashboard')">
            返回首页
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Close } from '@element-plus/icons-vue'
import { reviewApi, type DueCardData, type ReviewSubmitResult, type AiHelpResult } from '../api/reviews'
import { associateApi, type CardLinkOut } from '../api/associate'

type Phase = 'loading' | 'idle' | 'reviewing' | 'finished'

const phase = ref<Phase>('loading')
const cards = ref<DueCardData[]>([])
const currentIndex = ref(0)
const sessionId = ref<number | null>(null)
const userAnswer = ref('')
const showingAnswer = ref(false)
const submitting = ref(false)
const reviewedCount = ref(0)
const startTimeMs = ref(Date.now())
const cardLinks = ref<CardLinkOut[]>([])

const aiHelpLoading = ref(false)
const aiHelpResult = ref<AiHelpResult | null>(null)

// Choice 交互状态
const choicePick = ref<number[]>([])         // 用户点的选项索引
const choiceSettled = ref(false)             // 是否已判定过

const stats = ref({ again: 0, hard: 0, good: 0, easy: 0, totalMs: 0 })

const route = useRoute()

const currentCard = computed(() => cards.value[currentIndex.value] || null)
const totalCount = computed(() => cards.value.length)
const progressPercent = computed(() => {
  if (!totalCount.value) return 0
  return Math.round((reviewedCount.value / totalCount.value) * 100)
})

// 结束总结用
const accuracy = computed(() => {
  const total = stats.value.again + stats.value.hard + stats.value.good + stats.value.easy
  if (!total) return 0
  return Math.round(((stats.value.good + stats.value.easy) / total) * 100)
})
const avgTimePerCard = computed(() => {
  if (!reviewedCount.value) return '--'
  const avg = stats.value.totalMs / reviewedCount.value
  return avg < 1000 ? `${Math.round(avg)}ms` : `${(avg / 1000).toFixed(1)}s`
})
const encouragement = computed(() => {
  const a = accuracy.value
  if (a >= 90) return '太棒了！几乎都掌握了，继续保持这种节奏 ✨'
  if (a >= 70) return '很不错！大部分都记住了，再加把劲就完美啦 🌿'
  if (a >= 50) return '可以的，有些卡还需要再看看，加油 💪'
  if (reviewedCount.value >= 3) return '没关系，学习就是一个慢慢来的过程 🫂'
  return '迈出第一步就赢了，下次复习会更好 🌱'
})

// ---------- Choice 交互 helpers ----------
const _correctAnswerIndices = computed<number[]>(() => {
  const raw = currentCard.value?.back_content?.correct_answer || []
  return [...raw].sort((a, b) => a - b)
})

const correctAnswerLabels = computed(() =>
  _correctAnswerIndices.value.map((i) => String.fromCharCode(65 + i)).join(', ')
)

const choiceIsCorrectPick = computed(() => {
  if (!choiceSettled.value) return false
  const pick = [...choicePick.value].sort((a, b) => a - b)
  const ans = _correctAnswerIndices.value
  if (pick.length !== ans.length) return false
  return pick.every((v, i) => v === ans[i])
})

function choiceIsCorrectOption(i: number): boolean {
  // 判定后：正确答案的选项显示绿色勾
  return choiceSettled.value && _correctAnswerIndices.value.includes(i)
}

function choiceIsWrongPick(i: number): boolean {
  // 判定后：用户选了但不是正确答案的显示红色叉
  return choiceSettled.value && choicePick.value.includes(i) && !_correctAnswerIndices.value.includes(i)
}

function choicePickClass(i: number): string {
  const classes: string[] = []
  if (choicePick.value.includes(i)) classes.push('choice-picked')
  if (choiceIsCorrectOption(i)) classes.push('choice-picked-correct')
  if (choiceIsWrongPick(i)) classes.push('choice-picked-wrong')
  return classes.join(' ')
}

function handleChoicePick(i: number) {
  if (!currentCard.value || choiceSettled.value) return
  const isMultiple = !!currentCard.value.front_content.is_multiple
  if (isMultiple) {
    // 多选：toggle
    const idx = choicePick.value.indexOf(i)
    if (idx === -1) {
      choicePick.value.push(i)
    } else {
      choicePick.value.splice(idx, 1)
    }
    // 选完了（数量对得上）就判定
    if (choicePick.value.length >= _correctAnswerIndices.value.length) {
      choiceSettled.value = true
    }
  } else {
    // 单选：直接锁定
    choicePick.value = [i]
    choiceSettled.value = true
  }
}

function choiceResetPick() {
  choicePick.value = []
  choiceSettled.value = false
}

async function load() {
  phase.value = 'loading'
  try {
    const deckIdParam = route.query.deck_id
    const cardIdParam = route.query.card_id
    const cardIdsParam = route.query.card_ids
    const mistakesOnlyParam = route.query.mistakes
    const params: Record<string, any> = {}
    if (deckIdParam) params.deck_id = Number(deckIdParam)
    if (cardIdParam) params.card_id = Number(cardIdParam)
    if (cardIdsParam) params.card_ids = String(cardIdsParam)
    if (mistakesOnlyParam) params.mistake_only = true
    const sessionRes = await reviewApi.start(Object.keys(params).length ? params : undefined)
    const data = sessionRes.data as any
    sessionId.value = data.session_id
    cards.value = data.cards || []
    currentIndex.value = 0
    reviewedCount.value = 0
    showingAnswer.value = false
    userAnswer.value = ''
    stats.value = { again: 0, hard: 0, good: 0, easy: 0, totalMs: 0 }
    startTimeMs.value = Date.now()

    if (cards.value.length === 0) {
      phase.value = 'idle'
    } else {
      phase.value = 'reviewing'
    }
  } catch {
    phase.value = 'idle'
  }
}

function forceRefresh() {
  load()
}

function revealAnswer() {
  showingAnswer.value = true
  aiHelpResult.value = null
  choicePick.value = []
  choiceSettled.value = false
  // 加载这张卡的联想
  if (currentCard.value) {
    associateApi.list(currentCard.value.card_id)
      .then((res: any) => { cardLinks.value = res.data || res || [] })
      .catch(() => { cardLinks.value = [] })
  }
}

async function askAiHelp() {
  if (!currentCard.value || aiHelpLoading.value) return
  aiHelpLoading.value = true
  aiHelpResult.value = null
  try {
    const res = await reviewApi.aiHelp(currentCard.value.card_id)
    aiHelpResult.value = (res.data as AiHelpResult) || null
  } catch {
    ElMessage.error('AI 暂时没响应，稍后再试试～')
  } finally {
    aiHelpLoading.value = false
  }
}

async function submit(rating: 1 | 2 | 3 | 4) {
  if (!currentCard.value || submitting.value) return
  submitting.value = true

  // 统计
  const key = (['again', 'hard', 'good', 'easy'] as const)[rating - 1]
  stats.value[key]++

  const duration = Date.now() - startTimeMs.value
  stats.value.totalMs += duration
  startTimeMs.value = Date.now()

  try {
    await reviewApi.submit(currentCard.value.card_id, {
      session_id: sessionId.value ?? undefined,
      rating,
      response_time_ms: duration,
      answer_text: userAnswer.value || null,
      idempotency_key: `rev-${currentCard.value.card_id}-${Date.now()}`,
    })
  } catch {
    // 已拦截
  } finally {
    reviewedCount.value++
    userAnswer.value = ''
    showingAnswer.value = false
    cardLinks.value = []
    aiHelpResult.value = null
    choicePick.value = []
    choiceSettled.value = false
    submitting.value = false

    // 下一张 or 结束
    if (currentIndex.value + 1 < cards.value.length) {
      currentIndex.value++
    } else {
      phase.value = 'finished'
    }
  }
}

function quitSession() {
  load()
}

function restart() {
  load()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.code === 'Space' && !showingAnswer.value) {
    e.preventDefault()
    revealAnswer()
  } else if ((e.ctrlKey || e.metaKey) && e.code === 'Enter' && showingAnswer.value && !submitting.value) {
    e.preventDefault()
    submit(3) // 默认 Good
  }
}

function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s} 秒`
  const m = Math.floor(s / 60)
  return `${m} 分 ${s % 60} 秒`
}

onMounted(load)

onBeforeUnmount(() => {
  // 清理键盘监听
})
</script>

<style scoped>
.review-card {
  background: #fff;
  border-radius: 12px;
}
.review-card :deep(.el-card__body) {
  padding: 32px 40px;
}

.card-front {
  font-size: 20px;
  font-weight: 500;
  text-align: center;
  line-height: 1.6;
  color: #303133;
  padding: 24px 0;
  min-height: 80px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.card-front--large {
  font-size: 42px;
  font-weight: 700;
  color: #409eff;
}

.question-tag {
  display: inline-block;
  font-size: 12px;
  padding: 2px 12px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 10px;
  margin-bottom: 12px;
  font-weight: 400;
}

.keywords {
  margin-top: 12px;
}

.options-preview {
  width: 100%;
}

.option-item {
  padding: 8px 12px;
  border-radius: 6px;
  background: #f5f7fa;
  margin-bottom: 6px;
  font-size: 14px;
  color: #606266;
}

.vocab-word {
  font-size: 56px;
  font-weight: 700;
  color: #409eff;
  letter-spacing: 2px;
}

.vocab-phonetic {
  font-size: 24px;
  color: #909399;
  font-weight: 400;
  margin-top: 8px;
}

.card-back {
  font-size: 15px;
  line-height: 1.7;
  color: #303133;
  text-align: left;
}

.answer-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.meaning-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 4px;
}

.meaning-label {
  font-size: 12px;
  color: #909399;
  width: 32px;
  flex-shrink: 0;
}

.example {
  font-size: 14px;
  color: #606266;
  padding: 2px 0;
}

.rating-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.rating-row .el-button {
  height: 64px;
  font-size: 16px;
}

.rating-sub {
  font-size: 11px;
  opacity: 0.8;
}

/* AI 帮助理解卡片 */
.ai-help-card {
  background: linear-gradient(135deg, rgba(255, 248, 245, 0.9) 0%, rgba(245, 250, 248, 0.9) 100%);
  border: 1px solid rgba(232, 210, 200, 0.5);
  border-radius: 14px;
  padding: 20px 22px;
  margin: 14px 0;
}

.ai-help-section {
  margin-bottom: 14px;
}

.ai-help-section:last-child {
  margin-bottom: 0;
}

.ai-help-label {
  font-size: 13px;
  font-weight: 500;
  color: #7a6f68;
  margin-bottom: 6px;
}

.ai-help-text {
  font-size: 14px;
  line-height: 1.75;
  color: #4a4540;
  margin: 0;
}

.ai-help-analogy {
  font-style: italic;
  color: #6d5f5a;
  background: rgba(255, 245, 240, 0.6);
  padding: 10px 14px;
  border-radius: 8px;
  border-left: 3px solid #e69faf;
}

.ai-help-tip {
  color: #4f7a5d;
  background: rgba(240, 248, 243, 0.7);
  padding: 10px 14px;
  border-radius: 8px;
  border-left: 3px solid #8fbf9d;
}

.ai-help-list {
  margin: 0;
  padding-left: 18px;
  font-size: 14px;
  line-height: 1.8;
  color: #4a4540;
}

.ai-help-list li {
  margin-bottom: 2px;
}

.ai-help-warn li {
  color: #a66565;
}

/* ============ Choice 交互 ============ */
.choice-interactive {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.choice-pick-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-radius: 10px;
  background: #f7f4f0;
  border: 1.5px solid transparent;
  font-size: 14px;
  color: #4a4540;
  cursor: pointer;
  transition: all 0.18s ease;
  user-select: none;
}

.choice-pick-item:hover {
  background: #f2ede6;
  border-color: rgba(230, 159, 175, 0.4);
}

.choice-letter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e8e3dd;
  color: #8a7d75;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.choice-icon {
  margin-left: auto;
  font-size: 14px;
}

/* 用户选中 */
.choice-pick-item.choice-picked {
  background: rgba(230, 220, 210, 0.6);
  border-color: #d4b8a8;
}
.choice-pick-item.choice-picked .choice-letter {
  background: #c49890;
  color: #fff;
}

/* 判定后：正确答案（绿色高亮） */
.choice-pick-item.choice-picked-correct {
  background: rgba(143, 191, 157, 0.2);
  border-color: #8fbf9d;
  color: #3f6e4e;
}
.choice-pick-item.choice-picked-correct .choice-letter {
  background: #8fbf9d;
  color: #fff;
}
.choice-icon-correct {
  color: #5a9b6c;
}

/* 判定后：选错（红色高亮） */
.choice-pick-item.choice-picked-wrong {
  background: rgba(217, 143, 143, 0.15);
  border-color: #d98f8f;
  color: #9a4a4a;
}
.choice-pick-item.choice-picked-wrong .choice-letter {
  background: #d98f8f;
  color: #fff;
}
.choice-icon-wrong {
  color: #b85858;
}

/* 判定结果提示 */
.choice-result {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  margin-top: 12px;
}
.choice-result-correct {
  background: rgba(143, 191, 157, 0.15);
  color: #4a7a5a;
  border-left: 3px solid #8fbf9d;
}
.choice-result-wrong {
  background: rgba(217, 143, 143, 0.12);
  color: #9a4a4a;
  border-left: 3px solid #d98f8f;
}

/* 快捷"下一题"按钮 */
.next-quick-btn {
  height: 64px;
  font-size: 15px;
  min-width: 130px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6fbf85 0%, #4fa070 100%) !important;
  border: none !important;
}

/* ===== 结束总结 ===== */
.finish-wrap {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(16px);
  border-radius: 20px;
  padding: 36px 32px;
  box-shadow: 0 4px 24px rgba(180, 110, 140, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.8);
  text-align: center;
}
.finish-hero { margin-bottom: 28px; }
.finish-emoji { font-size: 52px; margin-bottom: 8px; }
.finish-title {
  font-size: 26px;
  font-weight: 600;
  color: #3d2e2a;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}
.finish-sub {
  font-size: 14px;
  color: #8a7e76;
  margin: 0;
}

.finish-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.fs-card {
  padding: 14px 8px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(242, 198, 208, 0.3);
}
.fs-rose { border-top: 3px solid #e69faf; }
.fs-mint { border-top: 3px solid #7ca982; }
.fs-peach { border-top: 3px solid #e6b88a; }
.fs-wood { border-top: 3px solid #a08070; }
.fs-num {
  font-size: 22px;
  font-weight: 600;
  color: #3d2e2a;
  letter-spacing: -0.5px;
}
.fs-label {
  font-size: 12px;
  color: #9a9590;
  margin-top: 2px;
}

.finish-breakdown {
  display: flex;
  justify-content: space-around;
  margin-bottom: 24px;
  padding: 14px;
  background: #faf7f4;
  border-radius: 12px;
}
.fb-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.fb-item span {
  font-size: 11px;
  color: #9a9590;
}
.fb-item strong {
  font-size: 20px;
  font-weight: 600;
}
.fb-again strong { color: #e27a7a; }
.fb-hard strong { color: #e6b88a; }
.fb-good strong { color: #7ca982; }
.fb-easy strong { color: #4fa070; }

.finish-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}
</style>
