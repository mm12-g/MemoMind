<template>
  <div>
    <el-row :gutter="16">
      <!-- 面试 -->
      <el-col :span="8">
        <el-card class="mode-card" shadow="hover" @click="$router.push('/practice/interview')">
          <div class="mode-icon" style="background: linear-gradient(135deg, #667eea, #764ba2)">💬</div>
          <h3>面试专项</h3>
          <p style="color: #909399; font-size: 13px">
            模拟技术面试，用 AI 评分你的回答，发现知识盲区
          </p>
          <el-button type="primary" text style="margin-top: 8px">开始训练 →</el-button>
        </el-card>
      </el-col>

      <!-- 考试 -->
      <el-col :span="8">
        <el-card class="mode-card" shadow="hover" @click="$router.push('/practice/exam')">
          <div class="mode-icon" style="background: linear-gradient(135deg, #f093fb, #f5576c)">📝</div>
          <h3>模拟考试</h3>
          <p style="color: #909399; font-size: 13px">
            从 choice 卡片随机抽题，计时答题 + 即时批改
          </p>
          <el-button type="primary" text style="margin-top: 8px">开始考试 →</el-button>
        </el-card>
      </el-col>

      <!-- 英语 -->
      <el-col :span="8">
        <el-card class="mode-card" shadow="hover" @click="$router.push('/practice/vocab')">
          <div class="mode-icon" style="background: linear-gradient(135deg, #4facfe, #00f2fe)">📚</div>
          <h3>英语专项</h3>
          <p style="color: #909399; font-size: 13px">
            Vocabulary 单词训练，拼写模式 + 释义回忆
          </p>
          <el-button type="primary" text style="margin-top: 8px">开始训练 →</el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近考试记录 -->
    <el-card style="margin-top: 24px" v-if="examHistory.length > 0">
      <template #header><strong>最近考试记录</strong></template>
      <el-table :data="examHistory" size="small">
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column label="成绩" width="120">
          <template #default="{ row }">
            <el-tag :type="scoreTag(row.score)" size="large">{{ row.score }} 分</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="答对/总" width="120">
          <template #default="{ row }">{{ row.correct_count }} / {{ row.total_count }}</template>
        </el-table-column>
        <el-table-column label="用时">
          <template #default="{ row }">{{ formatDuration(row.duration_seconds) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { practiceApi, type ExamHistoryItem } from '../../api/practice'

const examHistory = ref<ExamHistoryItem[]>([])

function scoreTag(s: number) {
  if (s >= 80) return 'success'
  if (s >= 60) return 'warning'
  return 'danger'
}
function formatDuration(sec: number | null) {
  if (!sec) return '—'
  const m = Math.floor(sec / 60)
  return `${m} 分 ${sec % 60} 秒`
}

onMounted(async () => {
  try {
    const res = await practiceApi.listExams()
    examHistory.value = Array.isArray(res.data) ? res.data : []
  } catch {
    // 拦截
  }
})
</script>

<style scoped>
.mode-card {
  cursor: pointer;
  transition: transform 0.2s;
  text-align: center;
}
.mode-card:hover {
  transform: translateY(-4px);
}
.mode-icon {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #fff;
}
h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #303133;
}
</style>
