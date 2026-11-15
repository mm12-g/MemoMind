<template>
  <div class="app-shell">
    <!-- 侧边栏（悬浮玻璃卡片） -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <i class="fa-regular fa-lightbulb"></i>
        </div>
        <div class="brand-name">MemoMind</div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :router="true"
        background-color="transparent"
        text-color="inherit"
        active-text-color="#555"
      >
        <el-menu-item index="/dashboard">
          <i class="fa-solid fa-gauge-high" style="margin-right: 10px; font-size: 16px"></i>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/decks">
          <i class="fa-solid fa-book-open" style="margin-right: 10px; font-size: 16px"></i>
          <span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/review">
          <i class="fa-solid fa-brain" style="margin-right: 10px; font-size: 16px"></i>
          <span>智能复习</span>
          <span v-if="dueCount > 0" class="menu-badge">{{ dueCount > 99 ? '99+' : dueCount }}</span>
        </el-menu-item>
        <el-menu-item index="/ai-studio">
          <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 10px; font-size: 16px"></i>
          <span>AI 工作台</span>
        </el-menu-item>
        <el-menu-item index="/practice">
          <i class="fa-solid fa-dumbbell" style="margin-right: 10px; font-size: 16px"></i>
          <span>专项训练</span>
        </el-menu-item>
        <el-menu-item index="/feynman">
          <i class="fa-solid fa-lightbulb" style="margin-right: 10px; font-size: 16px"></i>
          <span>费曼学习</span>
        </el-menu-item>
        <el-menu-item index="/analytics">
          <i class="fa-solid fa-chart-line" style="margin-right: 10px; font-size: 16px"></i>
          <span>学习分析</span>
        </el-menu-item>
        <el-menu-item index="/planner">
          <i class="fa-solid fa-calendar-days" style="margin-right: 10px; font-size: 16px"></i>
          <span>学习计划</span>
        </el-menu-item>
        <el-menu-item index="/tags">
          <i class="fa-solid fa-tags" style="margin-right: 10px; font-size: 16px"></i>
          <span>标签管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <i class="fa-solid fa-gear" style="margin-right: 10px; font-size: 16px"></i>
          <span>设置</span>
        </el-menu-item>
      </el-menu>

      <!-- 用户卡片 -->
      <div class="user-card" @click="showUserMenu = !showUserMenu">
        <el-avatar :size="36" style="background: linear-gradient(135deg, var(--cream-rose), var(--peach-pink)); color: #555; font-weight: 500">
          {{ userStore.user?.username?.[0]?.toUpperCase() || 'U' }}
        </el-avatar>
        <div style="flex: 1; min-width: 0">
          <div style="font-size: 13px; color: var(--color-text); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">
            {{ userStore.user?.username || '未登录' }}
          </div>
          <div style="font-size: 11px; color: var(--color-muted)">温柔记忆中…</div>
        </div>
        <el-dropdown trigger="click" @command="handleCommand">
          <i class="fa-solid fa-ellipsis-vertical" style="color: var(--color-muted)"></i>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <i class="fa-solid fa-user" style="margin-right: 8px"></i>个人资料
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <i class="fa-solid fa-right-from-bracket" style="margin-right: 8px"></i>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <!-- 主内容 -->
    <div class="content">
      <div class="topbar">
        <div class="page-title">
          <i class="fa-regular fa-circle" style="font-size: 8px; color: var(--cream-rose); margin-right: 10px"></i>
          {{ pageTitle }}
        </div>
        <div>
          <i class="fa-regular fa-clock" style="color: var(--color-muted); margin-right: 6px"></i>
          <span style="font-size: 13px; color: var(--color-muted)">{{ currentDate }}</span>
        </div>
      </div>

      <main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import { reviewApi } from '../api/reviews'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showUserMenu = ref(false)
const dueCount = ref(0)

async function fetchDueCount() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await reviewApi.due({ limit: 200 })
    dueCount.value = res.data?.length || 0
  } catch {
    dueCount.value = 0
  }
}

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => (route.meta.title as string) || 'MemoMind')

const currentDate = ref('')
let timer: number | null = null

function updateDate() {
  const d = new Date()
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  currentDate.value = `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 · ${weekdays[d.getDay()]}`
}

onMounted(() => {
  updateDate()
  timer = window.setInterval(updateDate, 60000)
  fetchDueCount()
  // 每 30 秒刷新一次徽章
  window.setInterval(fetchDueCount, 30000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})

// 路由变化（如复习完）刷新徽章
watch(() => route.path, () => fetchDueCount())

async function handleCommand(command: string) {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
      })
      userStore.logout()
      router.push('/login')
    } catch {
      /* 用户取消 */
    }
  } else if (command === 'profile') {
    router.push('/settings')
  }
}
</script>
