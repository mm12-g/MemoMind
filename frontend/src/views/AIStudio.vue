<template>
  <div>
    <el-row :gutter="16">
      <!-- 左：上传 + 文本输入 -->
      <el-col :span="10">
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header><strong>方式一：上传文档</strong></template>

          <el-select
            v-model="uploadDeckId"
            placeholder="请选择目标知识库 *"
            style="width: 100%; margin-bottom: 12px"
          >
            <el-option
              v-for="d in decks"
              :key="d.id"
              :label="d.name"
              :value="d.id"
            />
          </el-select>

          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
            drag
            accept=".pdf,.docx,.txt,.md"
            :disabled="!uploadDeckId"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              <template v-if="!uploadDeckId">
                请先选择知识库
              </template>
              <template v-else>
                拖拽文件到此处，或 <em>点击选择</em>
              </template>
            </div>
            <template #tip>
              <div style="color: #909399; font-size: 12px; margin-top: 8px">
                支持 PDF / DOCX / TXT / Markdown，单个最大 10MB
              </div>
            </template>
          </el-upload>

          <!-- 未选知识库时的提示 -->
          <div v-if="!uploadDeckId" class="hint-warn">
            <i class="fa-solid fa-circle-exclamation"></i>
            请先在上方选择一个知识库，然后再上传文件
          </div>

          <!-- 已选文件信息 -->
          <div v-if="selectedFile && !uploading" class="file-info">
            <i class="fa-solid fa-file-lines" style="color: var(--el-color-primary); margin-right: 8px"></i>
            <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
              {{ selectedFile.name }}
            </span>
            <span style="color: #909399; font-size: 12px">{{ formatSize(selectedFile.size) }}</span>
            <el-icon style="margin-left: 6px; cursor: pointer; color: #c0c4cc" @click="selectedFile = null">
              <Close />
            </el-icon>
          </div>

          <!-- 上传进度（HTTP 网络层） -->
          <div v-if="uploading" style="margin-top: 12px">
            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #7a6f68; margin-bottom: 4px">
              <span>{{ uploadStageText }}</span>
              <span>{{ uploadProgress }}%</span>
            </div>
            <el-progress :percentage="uploadProgress" :status="uploadProgress === 100 ? 'success' : undefined" :stroke-width="10" />
          </div>

          <el-button
            v-if="!uploading"
            type="primary"
            style="width: 100%; margin-top: 12px"
            :disabled="!selectedFile || !uploadDeckId"
            @click="doUpload"
          >
            上传并生成卡片
          </el-button>
          <div v-if="currentTask && !['completed', 'failed'].includes(currentTask.status)" class="loading-hint" style="margin-top: 12px">
            <i class="fa-solid fa-robot"></i>
            AI 正在解析文档，可能需要 20-60 秒…（已等待 {{ Math.round(pollElapsed) }}s）
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header><strong>方式二：粘贴文本</strong></template>
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="10"
            placeholder="粘贴任意知识内容..."
          />
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 12px">
            <div style="display: flex; gap: 8px">
              <el-select
                v-model="textDeckId"
                placeholder="请选择知识库 *"
                style="flex: 1"
              >
                <el-option
                  v-for="d in decks"
                  :key="d.id"
                  :label="d.name"
                  :value="d.id"
                />
              </el-select>
              <el-tooltip
                :content="!textDeckId ? '请先选择一个知识库' : '生成卡片'"
                placement="top"
              >
                <span style="display: inline-block">
                  <el-button
                    type="primary"
                    :loading="generating"
                    :disabled="!textDeckId || !inputText.trim()"
                    @click="doGenerate"
                  >
                    AI 生成卡片
                  </el-button>
                </span>
              </el-tooltip>
            </div>
            <div v-if="!textDeckId" class="hint-warn">
              <i class="fa-solid fa-circle-exclamation"></i>
              请先选择一个目标知识库
            </div>
            <div v-if="generating" class="loading-hint">
              <i class="fa-solid fa-robot"></i>
              AI 正在思考，可能需要 15-30 秒…（已等待 {{ Math.round(pollElapsed) }}s）
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右：任务 + 结果 -->
      <el-col :span="14">
        <!-- 当前任务进度 -->
        <el-card v-if="currentTask" shadow="never" style="margin-bottom: 16px">
          <template #header>
            <span>
              <el-tag :type="taskTag(currentTask.status)" size="small" style="margin-right: 8px">
                {{ currentTask.status === 'processing' ? '处理中' : currentTask.status === 'completed' ? '已完成' : currentTask.status === 'failed' ? '失败' : '排队中' }}
              </el-tag>
              任务 #{{ currentTask.id }}（{{ taskTypeLabel(currentTask.task_type) }}）
            </span>
          </template>
          <div style="display: flex; justify-content: space-between; font-size: 13px; color: #606266; margin-bottom: 6px">
            <span><i class="fa-solid fa-rotate" style="margin-right: 4px; color: var(--el-color-primary)"></i>{{ progressStageText(currentTask) }}</span>
            <span style="color: #909399">{{ currentTask.progress }}%</span>
          </div>
          <el-progress
            :percentage="currentTask.progress"
            :status="progressStatus(currentTask.status)"
            :stroke-width="14"
          />
          <div style="margin-top: 12px; font-size: 13px; color: #909399">
            <span v-if="currentTask.generation_counts">
              已生成: {{ Object.values(currentTask.generation_counts).reduce((a: number, b: number) => a + b, 0) }} 张
            </span>
            <span v-if="currentTask.error_message" style="color: #f56c6c">
              {{ currentTask.error_message }}
            </span>
          </div>
        </el-card>

        <!-- 生成结果（卡片审核） -->
        <el-card shadow="never" v-if="generations.length > 0">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span><strong>生成结果</strong>（{{ pendingCount }} 待审核 / {{ generations.length }} 总计）</span>
              <div v-if="pendingCount > 0">
                <el-button type="success" size="small" @click="bulkApproveAll">
                  全部通过
                </el-button>
              </div>
            </div>
          </template>

          <div v-for="(g, idx) in generations" :key="g.id" class="gen-card">
            <template v-if="g.status === 'pending'">
              <div class="gen-body">
                <div class="gen-header">
                  <el-tag size="small" :type="typeTag(g.output.card_type)">
                    {{ typeLabel(g.output.card_type) }}
                  </el-tag>
                  <span class="gen-idx">#{{ idx + 1 }}</span>
                </div>

                <!-- 直观展示：问题 + 答案，按卡片类型格式化 -->
                <div class="gen-qa">
                  <!-- basic / interview -->
                  <template v-if="g.output.card_type === 'basic' || g.output.card_type === 'interview'">
                    <div class="gen-q">
                      <i class="fa-solid fa-circle-question" style="margin-right: 6px; color: #b46e8c"></i>
                      {{ g.output.front_content?.content ?? frontPreview(g.output) }}
                    </div>
                    <div class="gen-a">
                      <i class="fa-solid fa-lightbulb" style="margin-right: 6px; color: #7ca982"></i>
                      {{ g.output.back_content?.content || '（无答案）' }}
                      <div v-if="g.output.explanation" class="gen-expl">
                        💡 {{ g.output.explanation }}
                      </div>
                    </div>
                  </template>

                  <!-- choice -->
                  <template v-else-if="g.output.card_type === 'choice'">
                    <div class="gen-q">
                      <i class="fa-solid fa-circle-question" style="margin-right: 6px; color: #b46e8c"></i>
                      {{ g.output.front_content?.question ?? frontPreview(g.output) }}
                    </div>
                    <div class="gen-options">
                      <div
                        v-for="(opt, iRaw) in (g.output.front_content?.options || [])"
                        :key="iRaw"
                        class="gen-option"
                        :class="{
                          'gen-option-correct': isChoiceAnswer(g.output, Number(iRaw)),
                          'gen-option-wrong': !isChoiceAnswer(g.output, Number(iRaw)),
                        }"
                      >
                        <span class="gen-option-letter">{{ String.fromCharCode(65 + Number(iRaw)) }}.</span>
                        {{ opt }}
                        <i v-if="isChoiceAnswer(g.output, Number(iRaw))" class="fa-solid fa-check" style="color: #67c23a; margin-left: 6px"></i>
                      </div>
                    </div>
                    <div v-if="g.output.back_content?.explanation" class="gen-expl">
                      💡 {{ g.output.back_content.explanation }}
                    </div>
                  </template>

                  <!-- vocabulary -->
                  <template v-else-if="g.output.card_type === 'vocabulary'">
                    <div class="gen-q">
                      <i class="fa-solid fa-language" style="margin-right: 6px; color: #b46e8c"></i>
                      <strong>{{ g.output.front_content?.word || frontPreview(g.output) }}</strong>
                    </div>
                    <div class="gen-a">
                      {{ g.output.back_content?.meaning || '（无释义）' }}
                      <span v-if="g.output.back_content?.phonetic" class="gen-phonetic">
                        /{{ g.output.back_content.phonetic }}/
                      </span>
                    </div>
                    <div v-if="g.output.back_content?.example" class="gen-expl">
                      💬 {{ g.output.back_content.example }}
                    </div>
                  </template>

                  <!-- fallback -->
                  <template v-else>
                    <pre style="background: #f5f7fa; padding: 10px; border-radius: 6px; font-size: 12px; margin: 0; white-space: pre-wrap">{{ JSON.stringify(g.output, null, 2) }}</pre>
                  </template>
                </div>

                <div class="gen-actions">
                  <el-button type="success" size="small" @click="approve(g.id)">
                    <i class="fa-solid fa-check" style="margin-right: 4px"></i>通过
                  </el-button>
                  <el-button type="danger" size="small" text @click="reject(g.id)">
                    <i class="fa-solid fa-xmark" style="margin-right: 4px"></i>拒绝
                  </el-button>
                </div>
              </div>
            </template>
            <template v-else-if="g.status === 'approved'">
              <div class="gen-body gen-approved">
                <el-icon><CircleCheckFilled /></el-icon>
                已保存为卡片 #{{ g.saved_card_id }}
              </div>
            </template>
            <template v-else>
              <div class="gen-body gen-rejected">
                <el-icon><CircleCloseFilled /></el-icon>
                已拒绝
              </div>
            </template>
          </div>
        </el-card>

        <!-- 空 -->
        <el-empty v-else-if="!currentTask" description="暂无任务" :image-size="80" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Close, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { aiApi, type AiTaskData, type AiGenerationData, type SourceDocData } from '../api/ai'
import { deckApi, type DeckData } from '../api/decks'

const decks = ref<DeckData[]>([])
const selectedFile = ref<File | null>(null)
const uploadDeckId = ref<number | undefined>(undefined)
const textDeckId = ref<number | undefined>(undefined)
const inputText = ref('')
const uploading = ref(false)
const generating = ref(false)

// HTTP 网络层上传进度（0-100）
const uploadProgress = ref(0)
const uploadStageText = computed(() => {
  if (uploadProgress.value < 100) return `上传到服务器 ${uploadProgress.value}%`
  return '文件已上传，等待后端解析…'
})

const currentTask = ref<AiTaskData | null>(null)
const generations = ref<AiGenerationData[]>([])
let pollTimer: number | null = null
let pollElapsed = 0           // 轮询已过秒数
let retryCount = 0
const POLL_TIMEOUT = 180      // 超时 3 分钟
const MAX_RETRIES = 1        // 超时后自动重试 1 次

const pendingCount = computed(() => generations.value.filter((g) => g.status === 'pending').length)

function taskTag(s: string) {
  return ({ pending: 'info', processing: 'warning', completed: 'success', failed: 'danger' } as Record<string, string>)[s] || 'info'
}
function progressStatus(s: string) {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'exception'
  return undefined
}
function taskTypeLabel(t: string) {
  return ({ document_parse: '文档解析', card_generate: '卡片生成', question_generate: '出题' } as Record<string, string>)[t] || t
}
function typeLabel(t: string) {
  return ({ basic: '基础', interview: '面试', choice: '选择', vocabulary: '单词' } as Record<string, string>)[t] || t
}
function typeTag(t: string) {
  return ({ basic: 'info', interview: '', choice: 'warning', vocabulary: 'success' } as Record<string, string>)[t] || 'info'
}

function frontPreview(output: Record<string, any>): string {
  const fc = output.front_content || {}
  return fc.content || fc.question || fc.word || JSON.stringify(fc).slice(0, 80)
}

/** choice 类型：判断某个索引 i 是否正确答案 */
function isChoiceAnswer(output: Record<string, any>, i: number): boolean {
  const ans: any = output.back_content?.correct_answer
  if (ans == null) return false
  if (Array.isArray(ans)) return ans.map((n: any) => Number(n)).includes(i)
  return Number(ans) === i
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** 根据 task_type + progress 推导阶段文字 */
function progressStageText(t: AiTaskData): string {
  const isCardGen = t.task_type === 'card_generate'
  const p = t.progress
  if (t.status === 'completed') return '✅ 全部完成'
  if (t.status === 'failed') return `❌ 失败: ${t.error_message || '未知错误'}`
  if (p <= 10) return '准备中…'
  if (p <= 25) return '📖 解析文档中（提取文字）…'
  if (!isCardGen && p <= 50) return '📖 解析文档中…'
  if (p <= 40 && isCardGen) return '📖 准备 AI 生成…'
  if (p <= 55 && isCardGen) return '🤖 AI 生成卡片中…（可能 5-30 秒）'
  if (p <= 75 && isCardGen) return '🤖 AI 生成中…'
  if (p <= 95) return '💾 保存结果中…'
  return '即将完成…'
}

function handleFileChange(file: any) {
  selectedFile.value = file.raw || file
}

async function doUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  uploadProgress.value = 0
  try {
    const res = await aiApi.upload(
      selectedFile.value,
      uploadDeckId.value,
      (pct) => {
        uploadProgress.value = pct
      },
    )
    // HTTP 上传完成 → 100%
    uploadProgress.value = 100
    const taskId = (res.data as any).task_id
    const docId = (res.data as any).source_document_id
    ElMessage.success(`文件上传成功！开始解析…（文档 #${docId}，任务 #${taskId}）`)
    startPolling(taskId)
    selectedFile.value = null
  } catch {
    ElMessage.error('上传失败，请检查文件或网络')
  } finally {
    uploading.value = false
    // 稍等再清零进度条，让用户看到 100%
    setTimeout(() => {
      uploadProgress.value = 0
    }, 800)
  }
}

async function doGenerate() {
  if (!textDeckId.value) return
  generating.value = true
  try {
    const res = await aiApi.generate(textDeckId.value, inputText.value)
    startPolling((res.data as any).task_id)
    inputText.value = ''
  } catch {
    // 拦截
  } finally {
    generating.value = false
  }
}

async function startPolling(taskId: number) {
  stopPolling()
  pollElapsed = 0
  currentTask.value = { id: taskId } as AiTaskData
  generations.value = []

  const tick = async () => {
    pollElapsed += 1.2
    try {
      const t = await aiApi.task(taskId)
      currentTask.value = (t.data as any) as AiTaskData

      if (currentTask.value.status === 'completed' || currentTask.value.status === 'failed') {
        stopPolling()
        retryCount = 0
        await loadGenerations(taskId)
        if (currentTask.value.status === 'completed') {
          const count = generations.value.length
          if (count === 0) {
            ElMessage.success(`✅ 解析完成（纯解析模式）`)
          } else {
            ElMessage.success(`✅ 完成！共生成 ${count} 张待审核卡片`)
          }
        } else {
          ElMessage.error(`❌ 任务失败：${currentTask.value.error_message || '未知错误'}`)
        }
        return
      }
    } catch {
      // 忽略瞬时网络错误
    }

    // 超时处理
    if (pollElapsed >= POLL_TIMEOUT) {
      stopPolling()
      if (retryCount < MAX_RETRIES) {
        retryCount += 1
        ElMessage.warning(`⏳ AI 响应较慢，自动重试（${retryCount}/${MAX_RETRIES}）…`)
        pollElapsed = 0
        pollTimer = window.setInterval(tick, 1200)
      } else {
        retryCount = 0
        ElMessage({
          type: 'warning',
          message: 'AI 生成超时（已等待 3 分钟），结果可能稍后到达。请耐心等待或重试。',
          duration: 8000,
          showClose: true,
        })
      }
    }
  }

  pollTimer = window.setInterval(tick, 1200)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadGenerations(taskId: number) {
  const res = await aiApi.generations({ task_id: taskId, limit: 100 })
  generations.value = (res.data as any) as AiGenerationData[]
}

async function approve(id: number) {
  await aiApi.approve(id)
  const g = generations.value.find((x) => x.id === id)
  if (g) g.status = 'approved'
  ElMessage.success('已保存为卡片')
}

async function reject(id: number) {
  await aiApi.reject(id)
  generations.value = generations.value.filter((x) => x.id !== id)
}

async function bulkApproveAll() {
  const ids = generations.value.filter((g) => g.status === 'pending').map((g) => g.id)
  if (!ids.length) return
  const res = await aiApi.bulkApprove(ids)
  const saved = (res.data as any).saved || 0
  await loadGenerations(currentTask.value!.id)
  ElMessage.success(`已保存 ${saved} 张卡片`)
}

async function loadDecks() {
  const res = await deckApi.list()
  decks.value = res.data?.items || (res.data as any)?.items || []
}

onMounted(loadDecks)
onUnmounted(stopPolling)
</script>

<style scoped>
.gen-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 10px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.gen-card:hover {
  box-shadow: 0 2px 12px rgba(180, 110, 140, 0.12);
}
.gen-body {
  padding: 14px 16px;
}
.gen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.gen-idx {
  font-size: 12px;
  color: #b0a090;
  font-weight: 500;
}

/* 直观问题/答案展示 */
.gen-qa {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.gen-q {
  font-size: 15px;
  font-weight: 500;
  color: #3d2e2a;
  line-height: 1.55;
}
.gen-a {
  font-size: 14px;
  color: #4a3d38;
  background: #f7f4f0;
  padding: 10px 14px;
  border-radius: 6px;
  line-height: 1.65;
  border-left: 3px solid #7ca982;
}
.gen-expl {
  margin-top: 6px;
  font-size: 13px;
  color: #7a6f68;
  line-height: 1.55;
}
.gen-phonetic {
  color: #a389c4;
  font-style: italic;
  margin-left: 8px;
  font-size: 13px;
}

/* choice 选项 */
.gen-options {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}
.gen-option {
  padding: 6px 12px;
  border-radius: 5px;
  font-size: 13px;
  background: #faf8f5;
  border: 1px solid #f0e8df;
  transition: all 0.2s;
}
.gen-option-correct {
  background: #f0f9eb;
  border-color: #c2e7b0;
  color: #3f8a3f;
  font-weight: 500;
}
.gen-option-wrong {
  color: #8a7a70;
}
.gen-option-letter {
  font-weight: 600;
  margin-right: 4px;
}

.gen-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
.gen-approved {
  background: #f0f9eb;
  color: #67c23a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.gen-rejected {
  background: #fef0f0;
  color: #f56c6c;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 已选文件信息条 */
.file-info {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  background: #f7f4f0;
  border-radius: 8px;
  font-size: 13px;
  margin-top: 12px;
}

.hint-warn {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
  padding: 8px 12px;
  background: #fdf4f0;
  border: 1px dashed #f0c8a8;
  border-radius: 8px;
  font-size: 12px;
  color: #c07040;
}

.loading-hint {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  background: linear-gradient(135deg, #f5f0ff 0%, #e8f4ff 100%);
  border: 1px solid rgba(147, 129, 220, 0.3);
  border-radius: 10px;
  font-size: 13px;
  color: #6b5b95;
  animation: pulse-hint 2s ease-in-out infinite;
}
@keyframes pulse-hint {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

:deep(.el-upload.is-disabled .el-upload-dragger) {
  background: #fafafa;
  border-color: #e4e7ed;
}
</style>
