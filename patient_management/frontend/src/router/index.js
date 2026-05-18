import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/patients'
  },
  {
    path: '/patients',
    name: 'PatientList',
    component: () => import('../views/PatientList.vue')
  },
  {
    path: '/patients/:id',
    name: 'PatientDetail',
    component: () => import('../views/PatientDetail.vue')
  },
  {
    path: '/examinations',
    name: 'ExamList',
    component: () => import('../views/ExamList.vue')
  },
  {
    path: '/examinations/new',
    name: 'NewExam',
    component: () => import('../views/NewExam.vue')
  },
  {
    path: '/examinations/:id',
    name: 'ExamDetail',
    component: () => import('../views/ExamDetail.vue')
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: () => import('../views/Statistics.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
