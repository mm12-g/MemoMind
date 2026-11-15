<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <!-- 左：今日进度 -->
      <el-col :span="14">
        <el-card style="margin-bottom: 16px">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <strong>今日目标</strong>
              <el-tag type="success" size="small" v-if="daily?.progress?.review_pct >= 100 && daily?.progress?.new_pct >= 100">
                🎉 全部完成！
              </el-tag>
            </div>
          </template>

          <div class="goal-row">
            <div class="goal-info">
              <i class="fa-solid fa-seedling" style="color: #7ca982; margin-right: 8px"></i>
              <span>新增卡片</span>
              <span class="goal-target">{{ daily?.goals?.daily_new_limit ?? 0 }} 张 / 天</span>
            </div>
            <div class="goal-progress">
              <el-progress
                :percentage="daily?.progress?.new_pct ?? 0"
                :stroke-width="14"
                :color="daily?.progress?.new_pct >= 100 ? '#7ca982' : '#e69faf'"
                :format="() => `${daily?.actual?.new_today ?? 0} / ${daily?.goals?.daily_new_limit ?? 0}`"
              />
            </div>
          </div>

          <div class="goal-row">
            <div class="goal-info">
              <i class="fa-solid fa-rotate" style="color: #e69faf; margin-right: 8px"></i>
              <span>复习卡片</span>
              <span class="goal-target">{{ daily?.goals?.daily_review_limit ?? 0 }} 张 / 天</span>
            </div>
            <div class="goal-progress">
              <el-progress
                :percentage="daily?.progress?.review_pct ?? 0"
                :stroke-width="14"
                :color="daily?.progress?.review_pct >= 100 ? '#7ca982' : '#e69faf'"
                :format="() => `${daily?.actual?.reviewed_today ?? 0} / ${daily?.goals?.daily_review_limit ?? 0}`"
              />
            </div>
          </div>

          <div class="goal-row">
            <div class="goal-info">
              <i class="fa-solid fa-bullseye" style="color: #e6b88a; margin-right: 8px"></i>
              <span>今日到期</span>
              <span class="goal-target">{{ daily?.actual?.due_today ?? 0 }} 张待复习</span>
            </div>
            <div style="display: flex; gap: 8px">
              <el-tag size="small" type="primary">正确率 {{ daily?.actual?.accuracy_pct ?? 0 }}%</el-tag>
              <el-button type="primary" size="small" :icon="ArrowRight" @click="$router.push('/review')">
                去复习
              </el-button>
            </div>
          </div>
        </el-card>

        <!-- 错题本 -->
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <strong>错题本</strong>
              <div style="display: flex; align-items: center; gap: 12px">
                <span style="font-size: 12px; color: #9a9590">共 {{ mistakes.length }} 条</span>
                <el-button
                  v-if="mistakes.length > 0"
                  type="danger"
                  size="small"
                  :icon="ArrowRight"
                  @click="jumpReviewAll"
                >
                  复习全部错题
                </el-button>
              </div>
            </div>
          </template>
          <el-table :data="mistakes" size="small" v-if="mistakes.length > 0">
            <el-table-column type="index" label="#" width="30" />
            <el-table-column prop="front_preview" label="题目" show-overflow-tooltip min-width="180" />
            <el-table-column prop="deck_name" label="知识库" width="100" show-overflow-tooltip />
            <el-table-column prop="reviewed_at" label="时间" width="140">
              <template #default="{ row }">
                {{ formatTime(row.reviewed_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90" align="center">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click="jumpReview(row.card_id)">
                  重做
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="还没有错题，真棒！" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 右：目标设置 -->
      <el-col :span="10">
        <el-card>
          <template #header><strong>目标设置</strong></template>
          <el-form :model="goalForm" label-width="120px">
            <el-form-item label="每日新增上限">
              <el-input-number v-model="goalForm.daily_new_limit" :min="1" :max="200" />
              <span class="form-hint">每天最多新增多少张新卡</span>
            </el-form-item>
            <el-form-item label="每日复习上限">
              <el-input-number v-model="goalForm.daily_review_limit" :min="1" :max="1000" />
              <span class="form-hint">每天最多复习多少张卡</span>
            </el-form-item>
            <el-form-item label="每日时长目标">
              <el-input-number v-model="goalForm.daily_minutes_goal" :min="5" :max="300" :step="5" />
              <span class="form-hint">分钟</span>
            </el-form-item>
            <el-form-item label="期望保持率">
              <el-slider v-model="goalForm.desired_retention" :min="0.5" :max="0.98" :step="0.02" show-input :marks="{ 0.7: '70%', 0.85: '85%', 0.95: '95%' }" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveGoal">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header><strong>小贴士</strong></template>
          <div class="tip-list">
            <div class="tip-item">
              <i class="fa-solid fa-leaf" style="color: #7ca982"></i>
              <span>温和地坚持比激进地冲刺更有效</span>
            </div>
            <div class="tip-item">
              <i class="fa-solid fa-repeat" style="color: #e69faf"></i>
              <span>每天至少复习 10 张，记忆曲线会越来越平滑</span>
            </div>
            <div class="tip-item">
              <i class="fa-solid fa-lightbulb" style="color: #e6b88a"></i>
              <span>遇到 Again 的卡 → 点击「费曼学习法」给小白讲一遍</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { goalApi, type GoalData, type DailyProgress } from '../api/goals'
import { practiceApi, type MistakeItem } from '../api/practice'

const loading = ref(false)
const saving = ref(false)
const daily = ref<DailyProgress | null>(null)
const mistakes = ref<MistakeItem[]>([])
const goalForm = reactive({
  daily_new_limit: 20,
  daily_review_limit: 200,
  daily_minutes_goal: 30,
  desired_retention: 0.9,
})
const router = useRouter()

function formatTime(iso: string) {
  try {
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch { return iso }
}

function jumpReview(cardId: number) {
  router.push({ path: '/review', query: { card_id: String(cardId) } })
}

function jumpReviewAll() {
  if (mistakes.value.length === 0) return
  const ids = mistakes.value.map((m) => m.card_id).join(',')
  router.push({ path: '/review', query: { card_ids: ids } })
}

async function loadAll() {
  loading.value = true
  try {
    const [g, d, m] = await Promise.all([
      goalApi.get(),
      goalApi.daily(),
      practiceApi.listMistakes({ limit: 20 }),
    ])
    const goal = g.data as GoalData
    goalForm.daily_new_limit = goal.daily_new_limit
    goalForm.daily_review_limit = goal.daily_review_limit
    goalForm.daily_minutes_goal = goal.daily_minutes_goal
    goalForm.desired_retention = goal.desired_retention

    daily.value = d.data as DailyProgress
    mistakes.value = Array.isArray(m.data) ? m.data as MistakeItem[] : []
  } finally {
    loading.value = false
  }
}

async function saveGoal() {
  saving.value = true
  try {
    await goalApi.update({
      daily_new_limit: goalForm.daily_new_limit,
      daily_review_limit: goalForm.daily_review_limit,
      daily_minutes_goal: goalForm.daily_minutes_goal,
      desired_retention: goalForm.desired_retention,
    })
    ElMessage.success('目标已保存 ✨')
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.goal-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px dashed rgba(242,198,208,0.4);
}
.goal-row:last-child { border-bottom: none; }
.goal-info { font-size: 14px; color: #3d2e2a; font-weight: 500; }
.goal-target { color: #9a9590; font-size: 12px; margin-left: 10px; font-weight: 400; }
.goal-progress { flex: 1; margin-left: 24px; }

.form-hint { display: block; font-size: 12px; color: #9a9590; margin-top: 4px; }

.tip-list { display: flex; flex-direction: column; gap: 12px; }
.tip-item {
  display: flex;
  gap: 10px;
  font-size: 13px;
  color: #6b6660;
  padding: 8px 12px;
  background: rgba(242,198,208,0.12);
  border-radius: 8px;
}
</style>
