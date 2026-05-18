import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
})

// Patients
export const patientApi = {
  list: (params) => api.get('/patients', { params }),
  get: (id) => api.get(`/patients/${id}`),
  create: (data) => api.post('/patients', data),
  update: (id, data) => api.put(`/patients/${id}`, data),
  delete: (id) => api.delete(`/patients/${id}`)
}

// Examinations
export const examApi = {
  list: (params) => api.get('/examinations', { params }),
  get: (id) => api.get(`/examinations/${id}`),
  create: (data) => api.post('/examinations', data),
  update: (id, data) => api.put(`/examinations/${id}`, data),
  delete: (id) => api.delete(`/examinations/${id}`),
  upload: (id, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/examinations/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  analyze: (id) => api.post(`/examinations/${id}/analyze`),
  confirm: (id) => api.post(`/examinations/${id}/confirm`),
  discard: (id) => api.post(`/examinations/${id}/discard`)
}

// Statistics
export const statsApi = {
  get: () => api.get('/statistics')
}

export default api
