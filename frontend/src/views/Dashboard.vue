<template>
  <div v-loading="loading">
    <!-- 顶部 4 张统计卡 -->
    <div class="stat-cards">
        <div class="stat-card c-rose">
          <div class="label">
            <i class="fa-regular fa-clock" style="margin-right: 6px"></i>今日待复习
          </div>
          <div class="value">{{ dashboard?.due_today ?? '--' }}</div>
          <div class="hint" v-if="dashboard?.due_today">
            <router-link to="/review" style="color: var(--el-color-primary); text-decoration: none">
              去复习 →
            </router-link>
          </div>
          <div class="hint" v-else style="color: var(--color-muted)">暂无到期卡片 🌸</div>
        </div>
        <div class="stat-card c-peach">
          <div class="label">
            <i class="fa-solid fa-check" style="margin-right: 6px"></i>今日已复习
          </div>
          <div class="value">{{ dashboard?.reviewed_today ?? '--' }}</div>
          <div class="hint" v-if="dashboard?.today_accuracy !== null">
            正确率 {{ dashboard?.today_accuracy ?? 0 }}% 📈
          </div>
          <div class="hint" v-else style="color: var(--color-muted)">今天还没复习哦</div>
        </div>
        <div class="stat-card c-mint">
          <div class="label">
            <i class="fa-solid fa-award" style="margin-right: 6px"></i>已掌握
          </div>
          <div class="value">{{ dashboard?.mastered_count ?? '--' }}</div>
          <div class="hint">稳定性 > 21 天 🌱</div>
        </div>
        <div class="stat-card c-wood">
          <div class="label">
            <i class="fa-solid fa-fire" style="margin-right: 6px"></i>连续学习
          </div>
          <div class="value">{{ dashboard?.streak_days ?? '--' }} 天</div>
          <div class="hint">坚持就是温柔地前进 ✨</div>
        </div>
      </div>

    <!-- 趋势图 + 薄弱点 -->
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span><strong>学习趋势</strong></span>
              <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
                <el-radio-button :value="7">近 7 天</el-radio-button>
                <el-radio-button :value="30">近 30 天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart class="chart" :option="trendOption" autoresize />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header><strong>薄弱知识点</strong></template>
          <el-table
            :data="weakPoints"
            size="small"
            v-if="weakPoints.length > 0"
            style="width: 100%"
            :row-class-name="'clickable-row'"
            @row-click="jumpReviewWeak"
          >
            <el-table-column prop="front_preview" label="内容" show-overflow-tooltip />
            <el-table-column prop="deck_name" label="知识库" width="100" show-overflow-tooltip />
            <el-table-column label="Again" width="70" align="center">
              <template #default="{ row }">
                <el-tag size="small" type="danger">{{ row.again_count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90" align="center">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click.stop="jumpReviewWeak(row)">
                  去复习
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无薄弱点，继续加油！" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 知识库掌握度 -->
    <el-card style="margin-top: 16px">
      <template #header><strong>知识库掌握情况</strong></template>
      <el-table :data="deckStats" style="width: 100%">
        <el-table-column prop="name" label="知识库" min-width="160" />
        <el-table-column prop="card_count" label="总卡片" width="90" align="center" />
        <el-table-column label="状态分布" min-width="240">
          <template #default="{ row }">
            <div style="display: flex; gap: 4px; flex-wrap: wrap">
              <el-tag size="small" type="warning" v-if="row.learning">学习 {{ row.learning }}</el-tag>
              <el-tag size="small" type="info" v-if="row.relearning">重学 {{ row.relearning }}</el-tag>
              <el-tag size="small" type="primary" v-if="row.review">复习 {{ row.review }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="掌握率" width="200">
          <template #default="{ row }">
            <el-progress :percentage="row.mastered_pct" :stroke-width="10" />
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="deckStats.length === 0" description="还没有知识库" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'

import { analyticsApi, type DashboardData, type TrendData, type DeckStat, type WeakPoint } from '../api/analytics'

// 注册 ECharts 组件
use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const loading = ref(false)
const trendDays = ref(7)
const dashboard = ref<DashboardData | null>(null)
const trend = ref<TrendData | null>(null)
const deckStats = ref<DeckStat[]>([])
const weakPoints = ref<WeakPoint[]>([])

const router = useRouter()

function jumpReviewWeak(row: WeakPoint) {
  // 带 card_id 跳转，Review 页会把该卡置顶（不管是否到期），直接定位复习
  router.push({ path: '/review', query: { card_id: String(row.card_id) } })
}

const trendOption = computed(() => {
  if (!trend.value) {
    return { title: { text: '加载中...', left: 'center' } }
  }
  const items = trend.value.items
  const dates = items.map((i) => i.date.slice(5)) // MM-DD
  const reviewed = items.map((i) => i.reviewed)
  const newCards = items.map((i) => i.new)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['已复习', '新增卡片'], textStyle: { color: '#6b6660' } },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(242,198,208,0.4)' } },
      axisLabel: { color: '#9a9590' },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      min: 0,
      axisLine: { show: false },
      axisLabel: { color: '#9a9590' },
      splitLine: { lineStyle: { color: 'rgba(242,198,208,0.15)' } },
    },
    series: [
      {
        name: '已复习',
        type: 'line',
        data: reviewed,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#e69faf' },
        lineStyle: { width: 2.5, color: '#e69faf' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(242,198,208,0.35)' },
              { offset: 1, color: 'rgba(242,198,208,0.02)' },
            ],
          },
        },
      },
      {
        name: '新增卡片',
        type: 'line',
        data: newCards,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#8fbf9d' },
        lineStyle: { width: 2.5, color: '#8fbf9d' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(212,237,223,0.4)' },
              { offset: 1, color: 'rgba(212,237,223,0.02)' },
            ],
          },
        },
      },
    ],
  }
})

async function loadDashboard() {
  loading.value = true
  try {
    const res = await analyticsApi.dashboard()
    dashboard.value = (res.data as any) as DashboardData
  } finally {
    loading.value = false
  }
}

async function loadTrend() {
  const res = await analyticsApi.trend({ days: trendDays.value })
  trend.value = (res.data as any) as TrendData
}

async function loadDecks() {
  const res = await analyticsApi.decks()
  deckStats.value = Array.isArray(res.data) ? (res.data as DeckStat[]) : []
}

async function loadWeakPoints() {
  const res = await analyticsApi.weakPoints({ limit: 5 })
  weakPoints.value = Array.isArray(res.data) ? (res.data as WeakPoint[]) : []
}

async function loadAll() {
  await Promise.all([loadDashboard(), loadTrend(), loadDecks(), loadWeakPoints()])
}

onMounted(loadAll)
</script>

<style scoped>
.chart {
  height: 300px;
  width: 100%;
}

:deep(.clickable-row) {
  cursor: pointer;
}
:deep(.clickable-row:hover > td) {
  background: rgba(230, 220, 210, 0.3) !important;
}
</style>
