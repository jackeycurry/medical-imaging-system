import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8084',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default {
  login: (data) => api.post('/api/auth/login', data),
  register: (data) => api.post('/api/auth/register', data),

  getPatients: (name) => api.get('/api/patients', { params: { name } }),
  createPatient: (data) => api.post('/api/patients', data),
  updatePatient: (id, data) => api.put(`/api/patients/${id}`, data),
  deletePatient: (id) => api.delete(`/api/patients/${id}`),

  getRecords: (patientName) => api.get('/api/records', { params: { patientName } }),
  createRecord: (data) => api.post('/api/records', data),
  deleteRecord: (id) => api.delete(`/api/records/${id}`),

  getImages: (params) => api.get('/api/images', { params }),
  getImage: (id) => api.get(`/api/images/${id}`),
  getImageData: (id) => api.get(`/api/images/${id}/image`),
  deleteImage: (id) => api.delete(`/api/images/${id}`),
  externalUpload: (data) => api.post('/api/external/upload', null, { params: data }),

  // Chest X-ray analysis via Qwen-VL
  analyzeChestXray: (formData) => {
    return api.post('/api/chest-xray/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  saveChestXrayResult: (data) => api.post('/api/chest-xray/save', data),

  // CT demo report via Qwen-VL
  analyzeCtDemo: (formData) => {
    return api.post('/api/ct/demo-report', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000
    })
  },

  // CT lesion detection via ResNet50 (legacy)
  analyzeCt: (imageBase64, patientName, patientId) =>
    api.post('/api/ct/analyze', null, { params: { image_base64: imageBase64, patient_name: patientName, patient_id: patientId } }),

  // Brain CT/MRI analysis via Qwen-VL
  analyzeBrain: (formData) => {
    return api.post('/api/brain/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000
    })
  },

  // Retina fundus analysis via Qwen-VL
  analyzeRetina: (formData) => {
    return api.post('/api/retina/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000
    })
  },

  // Abdomen analysis via Qwen-VL
  analyzeAbdomen: (formData) => {
    return api.post('/api/abdomen/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000
    })
  },

  // Spine analysis via Qwen-VL
  analyzeSpine: (formData) => {
    return api.post('/api/spine/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000
    })
  },

  // Breast analysis via Qwen-VL
  analyzeBreast: (formData) => {
    return api.post('/api/breast/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000
    })
  },

  // Cardiovascular analysis via Qwen-VL
  analyzeCardiovascular: (formData) => {
    return api.post('/api/cardiovascular/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000
    })
  },

  // PDF report download
  downloadPdf: (reportId) => {
    return api.get(`/api/report/${reportId}/pdf`, {
      responseType: 'blob',
      timeout: 30000
    })
  },
}