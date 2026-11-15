<template>
  <div v-loading="loading">
    <!-- 选卡区（会话未开始） -->
    <div v-if="!session" class="glass-card" style="padding: 28px 32px; margin-bottom: 20px">
      <h2 style="font-size: 22px; font-weight: 500; margin: 0 0 6px">
        <i class="fa-solid fa-lightbulb" style="color: var(--el-color-primary); margin-right: 10px"></i>
        费曼学习法
      </h2>
      <p style="color: var(--color-muted); margin: 0 0 24px; font-size: 14px; font-weight: 300">
        选一批卡，假装你在给一个小白讲解这个知识点。AI 会帮你找出卡壳的地方——那些说不清、说不准、容易混淆的，就是真正没掌握的。
      </p>

      <el-form label-position="top" style="max-width: 560px">
        <el-form-item label="从知识库选卡">
          <el-select v-model="selectedDeckId" placeholder="选择一个知识库" clearable style="width: 100%">
            <el-option v-for="d in decks" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="每次选几张">
          <el-slider v-model="cardCount" :min="3" :max="15" :step="1" style="max-width: 400px" />
          <span style="margin-left: 12px; color: var(--color-muted); font-size: 13px">{{ cardCount }} 张</span>
        </el-form-item>
        <button class="gradient-btn" :disabled="starting" @click="startSession">
          <i class="fa-solid fa-play" style="margin-right: 8px"></i>
          {{ starting ? '开始中…' : '开始费曼学习' }}
        </button>
      </el-form>

      <!-- 历史会话 -->
      <div v-if="history.length > 0" style="margin-top: 28px; padding-top: 20px; border-top: 1px solid rgba(242,198,208,0.2)">
        <h3 style="font-size: 15px; margin: 0 0 12px; color: var(--color-text-soft)">最近学习记录</h3>
        <el-table :data="history" size="small" style="width: 100%">
          <el-table-column prop="title" label="标题" min-width="150" />
          <el-table-column label="完成" width="80" align="center">
            <template #default="{ row }">{{ row.explained_count }}/{{ row.card_count }}</template>
          </el-table-column>
          <el-table-column label="卡壳" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.stuck_count" type="danger" size="small">{{ row.stuck_count }}</el-tag>
              <span v-else style="color: var(--color-muted)">-</span>
            </template>
          </el-table-column>
          <el-table-column label="流畅度" width="90" align="center">
            <template #default="{ row }">
              <span v-if="row.avg_clarity != null" style="color: var(--color-primary)">{{ row.avg_clarity.toFixed(1) }}</span>
              <span v-else style="color: var(--color-muted)">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="started_at" label="开始时间" width="160" />
        </el-table>
      </div>
    </div>

    <!-- 会话进行中 -->
    <template v-else>
      <!-- 进度条 -->
      <div class="glass-card" style="padding: 16px 28px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center">
        <div>
          <span style="font-weight: 500">{{ session.title }}</span>
          <span style="color: var(--color-muted); margin-left: 12px; font-size: 13px">
            已解释 {{ explainedIndex + 1 }} / {{ session.cards.length }}
          </span>
        </div>
        <el-button size="small" @click="confirmAbandon" plain>
          <i class="fa-solid fa-right-from-bracket" style="margin-right: 6px"></i>放弃
        </el-button>
      </div>

      <!-- 当前卡 -->
      <div class="glass-card" style="padding: 32px; margin-bottom: 16px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
          <span class="color-badge mint">
            <i class="fa-regular fa-lightbulb" style="margin-right: 6px"></i>
            第 {{ currentAttempt }} 次解释
          </span>
          <el-tag :type="cardTypeTag(currentCard.card_type)" size="small">{{ currentCard.card_type }}</el-tag>
        </div>

        <h3 style="font-size: 20px; font-weight: 500; margin: 0 0 4px">{{ currentCard.preview }}</h3>
        <p style="color: var(--color-muted); font-size: 13px; margin: 0 0 20px; white-space: pre-wrap">{{ currentCard.concept }}</p>

        <el-input
          v-model="userExplanation"
          type="textarea"
          :rows="6"
          placeholder="假装你在给一个完全不懂的小白解释这个知识点。越朴素、越清楚越好，能用生活例子就用。写完点下方按钮让 AI 评分。"
        />

        <div style="margin-top: 16px; display: flex; gap: 12px">
          <button class="gradient-btn" :disabled="!userExplanation.trim() || submitting" @click="submitExplain">
            <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 8px"></i>
            {{ submitting ? 'AI 评分中…' : '让 AI 评分' }}
          </button>
          <button class="ghost-btn" :disabled="!userExplanation.trim() || submitting" @click="submitExplain(true)">
            <i class="fa-solid fa-rotate" style="margin-right: 8px"></i>重新解释（追加次数）
          </button>
        </div>
      </div>

      <!-- AI 评分结果 -->
      <div v-if="lastResult" class="glass-card" style="padding: 28px; margin-bottom: 16px"
           :style="lastResult.is_stuck ? 'border-color: rgba(217,143,143,0.4)' : ''">
        <h3 style="margin: 0 0 14px; font-size: 16px; font-weight: 500; display: flex; align-items: center; gap: 8px">
          <i class="fa-solid fa-robot" style="color: var(--el-color-primary)"></i>AI 反馈
          <el-tag v-if="lastResult.is_stuck" type="danger" size="small" style="margin-left: auto">卡壳了！</el-tag>
          <el-tag v-else type="success" size="small" style="margin-left: auto">解释得不错</el-tag>
        </h3>

        <!-- 分数 -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px">
          <ScoreBox label="流畅度" :score="lastResult.clarity_score" color="#e69faf" />
          <ScoreBox label="简单度" :score="lastResult.simplicity_score" color="#8fbf9d" />
          <ScoreBox label="准确度" :score="lastResult.accuracy_score" color="#d9a87a" />
          <ScoreBox label="综合" :score="lastResult.overall_score" color="#a793c4" big />
        </div>

        <!-- 卡壳点 -->
        <div v-if="lastResult.stuck_spots && lastResult.stuck_spots.length" style="margin-bottom: 14px">
          <div style="font-size: 13px; color: var(--color-muted); margin-bottom: 6px">
            <i class="fa-solid fa-triangle-exclamation" style="color: #d98f8f; margin-right: 4px"></i>
            没说清楚的地方：
          </div>
          <ul style="margin: 0; padding-left: 20px; color: var(--color-text); font-size: 14px; line-height: 1.7">
            <li v-for="(spot, i) in lastResult.stuck_spots" :key="i">{{ spot }}</li>
          </ul>
        </div>

        <p style="color: var(--color-text-soft); font-size: 14px; margin: 0; font-style: italic">
          <i class="fa-regular fa-comment" style="margin-right: 6px; color: var(--el-color-primary)"></i>
          {{ lastResult.ai_feedback }}
        </p>

        <!-- 下一张 / 重试 -->
        <div style="margin-top: 20px; display: flex; gap: 12px; justify-content: flex-end">
          <button v-if="lastResult.is_stuck" class="ghost-btn" @click="retryThis">
            <i class="fa-solid fa-rotate-left" style="margin-right: 6px"></i>再试一次（用不同说法）
          </button>
          <button class="gradient-btn" @click="nextCard">
            {{ isLastCard ? '结束会话' : '下一张' }}
            <i class="fa-solid fa-arrow-right" style="margin-left: 6px"></i>
          </button>
        </div>
      </div>

      <!-- 会话结束 -->
      <div v-if="showComplete" class="glass-card" style="padding: 32px; text-align: center">
        <i class="fa-solid fa-seedling" style="font-size: 40px; color: var(--mint-green); margin-bottom: 12px"></i>
        <h3 style="margin: 0 0 6px; font-size: 20px">会话结束</h3>
        <p style="color: var(--color-muted); margin: 0 0 20px">温柔地回顾一下这次学习吧</p>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; text-align: center">
          <div>
            <div style="font-size: 28px; font-weight: 500; color: var(--color-primary)">{{ session.card_count }}</div>
            <div style="font-size: 13px; color: var(--color-muted)">总卡数</div>
          </div>
          <div>
            <div style="font-size: 28px; font-weight: 500; color: var(--mint-green)">{{ session.cards.length - stuckCardIds.length }}</div>
            <div style="font-size: 13px; color: var(--color-muted)">通过</div>
          </div>
          <div>
            <div style="font-size: 28px; font-weight: 500; color: #d98f8f">{{ stuckCardIds.length }}</div>
            <div style="font-size: 13px; color: var(--color-muted)">卡壳</div>
          </div>
          <div>
            <div style="font-size: 28px; font-weight: 500; color: var(--color-text)">{{ session.card_count }}</div>
            <div style="font-size: 13px; color: var(--color-muted)">解释次数</div>
          </div>
        </div>

        <div style="display: flex; gap: 12px; justify-content: center">
          <button class="ghost-btn" @click="backToStart">再开一会话</button>
          <button class="gradient-btn" @click="$router.push('/dashboard')">
            返回首页<i class="fa-solid fa-house" style="margin-left: 6px"></i>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { feynmanApi, type FeynmanCard, type FeynmanExplainResult } from '../api/feynman'
import { deckApi } from '../api/decks'

const loading = ref(false)
const starting = ref(false)
const submitting = ref(false)
const session = ref<{ session_id: number; title: string; card_count: number; cards: FeynmanCard[] } | null>(null)
const explainedIndex = ref(0)
const currentAttempt = ref(1)
const userExplanation = ref('')
const lastResult = ref<FeynmanExplainResult | null>(null)
const stuckCardIds = ref<Set<number>>(new Set())
const showComplete = ref(false)
const history = ref<any[]>([])

const selectedDeckId = ref<number | undefined>(undefined)
const cardCount = ref(6)
const decks = ref<any[]>([])

const currentCard = computed<FeynmanCard>(() => session.value!.cards[explainedIndex.value])
const isLastCard = computed(() => explainedIndex.value >= session.value!.cards.length - 1)

function cardTypeTag(t: string) {
  return ({ basic: 'info', interview: 'warning', choice: 'primary', vocabulary: 'success' } as any)[t] || 'info'
}

onMounted(async () => {
  try {
    const res = await deckApi.list({ page: 1, page_size: 50 })
    decks.value = res.data.items || res.data || []
  } catch {}
  try {
    history.value = (await feynmanApi.list()).data || []
  } catch {}
})

async function startSession() {
  starting.value = true
  try {
    const payload: any = { count: cardCount.value }
    if (selectedDeckId.value) payload.deck_id = selectedDeckId.value
    session.value = (await feynmanApi.start(payload)).data
    explainedIndex.value = 0
    currentAttempt.value = 1
    userExplanation.value = ''
    lastResult.value = null
    stuckCardIds.value = new Set()
    showComplete.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '开始失败')
  } finally {
    starting.value = false
  }
}

async function submitExplain(isRetry = false) {
  if (!session.value || !userExplanation.value.trim()) return
  submitting.value = true
  try {
    const res = await feynmanApi.explain(session.value.session_id, currentCard.value.card_id, userExplanation.value)
    lastResult.value = res.data
    if (res.data.is_stuck) stuckCardIds.value.add(currentCard.value.card_id)
    if (isRetry) currentAttempt.value++
    else currentAttempt.value = res.data.attempt
  } catch (e: any) {
    ElMessage.error(e?.message || 'AI 评分失败')
  } finally {
    submitting.value = false
  }
}

function retryThis() {
  userExplanation.value = ''
  lastResult.value = null
}

async function nextCard() {
  if (isLastCard.value) {
    await feynmanApi.complete(session.value!.session_id, 'completed')
    showComplete.value = true
    return
  }
  explainedIndex.value++
  currentAttempt.value = 1
  userExplanation.value = ''
  lastResult.value = null
}

async function confirmAbandon() {
  try {
    await ElMessageBox.confirm('确定放弃这次会话？已解释的记录会保留。', '放弃会话', { type: 'warning' })
    await feynmanApi.complete(session.value!.session_id, 'abandoned')
    session.value = null
    showComplete.value = false
  } catch {}
}

function backToStart() {
  session.value = null
  showComplete.value = false
}

// 分数小组件
import { defineComponent, h } from 'vue'
const ScoreBox = defineComponent({
  props: { label: String, score: Number, color: String, big: Boolean },
  setup(props) {
    return () => h('div', { style: 'text-align: center; padding: 12px; background: rgba(255,251,248,0.6); border-radius: 12px' }, [
      h('div', { style: 'font-size: 12px; color: var(--color-muted)' }, props.label),
      h('div', { style: `font-size: ${props.big ? 32 : 24}px; font-weight: 500; color: ${props.color}; margin-top: 4px` },
        props.score != null ? props.score.toFixed(1) : '-'),
    ])
  },
})
</script>

<style scoped>
:deep(.el-tag) { margin-right: 4px }
</style>
