<template>
  <div v-loading="loading">
    <!-- 顶部：总览卡片 -->
    <div class="overview-cards">
      <div class="ov-card c-rose">
        <div class="ov-label">累计复习</div>
        <div class="ov-value">{{ stats?.total_reviews ?? 0 }}</div>
        <div class="ov-hint">覆盖 {{ stats?.unique_cards_reviewed ?? 0 }} 张卡 · 活跃 {{ stats?.days_active ?? 0 }} 天</div>
      </div>
      <div class="ov-card c-mint">
        <div class="ov-label">整体正确率</div>
        <div class="ov-value">{{ stats?.accuracy_pct ?? 0 }}%</div>
        <div class="ov-hint">按 Good/Easy 统计</div>
      </div>
      <div class="ov-card c-peach">
        <div class="ov-label">平均耗时</div>
        <div class="ov-value">
          {{ stats?.avg_response_ms ? (stats.avg_response_ms / 1000).toFixed(1) + 's' : '--' }}
        </div>
        <div class="ov-hint">有记录的复习均值</div>
      </div>
      <div class="ov-card c-wood">
        <div class="ov-label">记忆保持率预估</div>
        <div class="ov-value">{{ retention?.avg_retention_7d ?? '--' }}%</div>
        <div class="ov-hint">7 天后预估保持</div>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左：趋势 + 掌握度 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span><strong>详细趋势</strong></span>
              <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
                <el-radio-button :value="7">7 天</el-radio-button>
                <el-radio-button :value="30">30 天</el-radio-button>
                <el-radio-button :value="90">90 天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart class="chart-lg" :option="trendOption" autoresize />
        </el-card>
      </el-col>

      <!-- 右：保持率分布 + Rating 分布 -->
      <el-col :span="10">
        <el-card style="margin-bottom: 16px">
          <template #header><strong>保持率变化</strong></template>
          <v-chart class="chart-sm" :option="retentionOption" autoresize />
        </el-card>

        <el-card>
          <template #header><strong>Rating 分布</strong></template>
          <v-chart class="chart-sm" :option="ratingOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 知识库掌握度 + 薄弱点 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card>
          <template #header><strong>各知识库掌握情况</strong></template>
          <el-table :data="deckStats" size="small" style="width: 100%">
            <el-table-column prop="name" label="知识库" min-width="140" />
            <el-table-column prop="card_count" label="总卡片" width="80" align="center" />
            <el-table-column prop="learning" label="学习中" width="80" align="center" />
            <el-table-column prop="review" label="已复习" width="80" align="center" />
            <el-table-column prop="mastered_pct" label="掌握率" width="180">
              <template #default="{ row }">
                <el-progress :percentage="row.mastered_pct" :stroke-width="8" />
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="deckStats.length === 0" description="还没有知识库" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header><strong>薄弱知识点 Top 10</strong></template>
          <el-table :data="weakPoints" size="small" style="width: 100%">
            <el-table-column type="index" label="#" width="30" />
            <el-table-column prop="front_preview" label="内容" show-overflow-tooltip />
            <el-table-column label="Again" width="60" align="center">
              <template #default="{ row }">
                <el-tag size="small" type="danger">{{ row.again_count }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="weakPoints.length === 0" description="暂无薄弱点" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, GaugeChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import { analyticsApi, type ReviewStatistics, type RetentionData } from '../api/analytics'

use([CanvasRenderer, LineChart, BarChart, PieChart, GaugeChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const loading = ref(false)
const trendDays = ref(7)
const stats = ref<ReviewStatistics | null>(null)
const retention = ref<RetentionData | null>(null)
const trend = ref<any>(null)
const deckStats = ref<any[]>([])
const weakPoints = ref<any[]>([])

const trendOption = computed(() => {
  if (!trend.value) return { title: { text: '加载中...', left: 'center' } }
  const items = trend.value.items
  const dates = items.map((i: any) => i.date.slice(5))
  const reviewed = items.map((i: any) => i.reviewed)
  const accuracy = items.map((i: any) => i.accuracy ?? 0)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['已复习', '正确率%'], textStyle: { color: '#6b6660' } },
    grid: { left: 40, right: 50, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(242,198,208,0.4)' } },
      axisLabel: { color: '#9a9590' },
    },
    yAxis: [
      { type: 'value', min: 0, axisLine: { show: false }, splitLine: { lineStyle: { color: 'rgba(242,198,208,0.15)' } }, axisLabel: { color: '#9a9590' } },
      { type: 'value', min: 0, max: 100, axisLine: { show: false }, splitLine: { show: false }, axisLabel: { color: '#9a9590', formatter: '{value}%' } },
    ],
    series: [
      { name: '已复习', type: 'bar', data: reviewed, barWidth: '60%', itemStyle: { color: '#e69faf', borderRadius: [3, 3, 0, 0] } },
      { name: '正确率%', type: 'line', yAxisIndex: 1, data: accuracy, smooth: true, symbol: 'circle', symbolSize: 5, itemStyle: { color: '#7ca982' }, lineStyle: { width: 2 } },
    ],
  }
})

const retentionOption = computed(() => {
  if (!retention.value) return { title: { text: '无数据', left: 'center' } }
  const r = retention.value
  const data = [
    { name: '1 天后', value: r.avg_retention_1d ?? 0 },
    { name: '7 天后', value: r.avg_retention_7d ?? 0 },
    { name: '30 天后', value: r.avg_retention_30d ?? 0 },
  ]
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: data.map((d) => d.name), axisLine: { lineStyle: { color: 'rgba(242,198,208,0.4)' } }, axisLabel: { color: '#9a9590' } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#9a9590', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(242,198,208,0.15)' } } },
    series: [{
      type: 'bar',
      data: data.map((d) => d.value),
      barWidth: '45%',
      itemStyle: { color: '#b48fa0', borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', formatter: '{c}%', color: '#6b6660', fontSize: 12 },
    }],
  }
})

const ratingOption = computed(() => {
  if (!stats.value) return { title: { text: '无数据', left: 'center' } }
  const dist = stats.value.rating_distribution
  const data = [
    { name: 'Again', value: dist.Again, itemStyle: { color: '#f56c6c' } },
    { name: 'Hard', value: dist.Hard, itemStyle: { color: '#e6a23c' } },
    { name: 'Good', value: dist.Good, itemStyle: { color: '#7ca982' } },
    { name: 'Easy', value: dist.Easy, itemStyle: { color: '#8fbf9d' } },
  ]
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { color: '#6b6660' } },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      data: data.filter((d) => d.value > 0),
      label: { show: true, color: '#6b6660', fontSize: 12 },
    }],
  }
})

async function loadAll() {
  loading.value = true
  try {
    const [s, r, t, d, w] = await Promise.all([
      analyticsApi.reviewStats(),
      analyticsApi.retention(),
      analyticsApi.trend({ days: trendDays.value }),
      analyticsApi.decks(),
      analyticsApi.weakPoints({ limit: 10 }),
    ])
    stats.value = s.data as ReviewStatistics
    retention.value = r.data as RetentionData
    trend.value = t.data as any
    deckStats.value = Array.isArray(d.data) ? d.data as any[] : []
    weakPoints.value = Array.isArray(w.data) ? w.data as any[] : []
  } finally {
    loading.value = false
  }
}

async function loadTrend() {
  const t = await analyticsApi.trend({ days: trendDays.value })
  trend.value = t.data as any
}

onMounted(loadAll)
</script>

<style scoped>
.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.ov-card {
  padding: 18px 22px;
  border-radius: 14px;
  backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.65);
  box-shadow: 0 2px 10px rgba(180, 110, 140, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.7);
}
.ov-label { font-size: 13px; color: #9a9590; margin-bottom: 6px; }
.ov-value { font-size: 28px; font-weight: 600; color: #3d2e2a; letter-spacing: -0.5px; }
.ov-hint { font-size: 12px; color: #b0a090; margin-top: 4px; }
.c-rose { border-top: 3px solid #e69faf; }
.c-mint { border-top: 3px solid #7ca982; }
.c-peach { border-top: 3px solid #e6b88a; }
.c-wood { border-top: 3px solid #a08070; }

.chart-lg { height: 280px; width: 100%; }
.chart-sm { height: 200px; width: 100%; }
</style>
