import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../stores/user'

// 路由定义
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'decks',
        name: 'DeckList',
        component: () => import('../views/decks/DeckList.vue'),
        meta: { title: '知识库' },
      },
      {
        path: 'decks/:id',
        name: 'DeckDetail',
        component: () => import('../views/decks/DeckDetail.vue'),
        meta: { title: '知识库详情' },
      },
      {
        path: 'cards/new',
        name: 'CardNew',
        component: () => import('../views/cards/CardForm.vue'),
        meta: { title: '新建卡片' },
      },
      {
        path: 'cards/:id/edit',
        name: 'CardEdit',
        component: () => import('../views/cards/CardForm.vue'),
        meta: { title: '编辑卡片' },
      },
      {
        path: 'review',
        name: 'Review',
        component: () => import('../views/Review.vue'),
        meta: { title: '智能复习' },
      },
      {
        path: 'ai-studio',
        name: 'AIStudio',
        component: () => import('../views/AIStudio.vue'),
        meta: { title: 'AI 工作台' },
      },
      {
        path: 'practice',
        name: 'PracticeHome',
        component: () => import('../views/practice/PracticeHome.vue'),
        meta: { title: '专项训练' },
      },
      {
        path: 'practice/interview',
        name: 'InterviewMode',
        component: () => import('../views/practice/InterviewMode.vue'),
        meta: { title: '面试专项' },
      },
      {
        path: 'practice/exam',
        name: 'ExamMode',
        component: () => import('../views/practice/ExamMode.vue'),
        meta: { title: '模拟考试' },
      },
      {
        path: 'practice/vocab',
        name: 'VocabMode',
        component: () => import('../views/practice/VocabMode.vue'),
        meta: { title: '英语专项' },
      },
      {
        path: 'feynman',
        name: 'FeynmanMode',
        component: () => import('../views/FeynmanMode.vue'),
        meta: { title: '费曼学习法' },
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('../views/Analytics.vue'),
        meta: { title: '学习分析' },
      },
      {
        path: 'planner',
        name: 'Planner',
        component: () => import('../views/Planner.vue'),
        meta: { title: '学习计划' },
      },
      {
        path: 'tags',
        name: 'Tags',
        component: () => import('../views/Tags.vue'),
        meta: { title: '标签管理' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/Settings.vue'),
        meta: { title: '设置' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from) => {
  const userStore = useUserStore()
  const requiresAuth = to.meta.requiresAuth !== false
  if (requiresAuth && !userStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if ((to.path === '/login' || to.path === '/register') && userStore.isLoggedIn) {
    return '/dashboard'
  }
})

export default router
