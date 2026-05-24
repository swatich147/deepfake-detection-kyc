import axios from 'axios'
import { useAuthStore } from '../store/authSlice'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        const refreshToken = useAuthStore.getState().refreshToken
        if (!refreshToken) {
          throw new Error('No refresh token')
        }
        
        const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
          refresh: refreshToken,
        })
        
        const { access } = response.data
        useAuthStore.getState().setAccessToken(access)
        
        originalRequest.headers.Authorization = `Bearer ${access}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login/', { email, password })
    return response.data
  },
  
  register: async (data: {
    email: string
    password: string
    password_confirm: string
    first_name?: string
    last_name?: string
    organization_name?: string
  }) => {
    const response = await apiClient.post('/auth/register/', data)
    return response.data
  },
  
  logout: async () => {
    const refreshToken = useAuthStore.getState().refreshToken
    if (refreshToken) {
      await apiClient.post('/auth/logout/', { refresh: refreshToken })
    }
  },
  
  me: async () => {
    const response = await apiClient.get('/auth/me/')
    return response.data
  },
}

// Sessions API
export const sessionsApi = {
  create: async (data: {
    external_reference?: string
    applicant_name?: string
    challenge_type?: string
  }) => {
    const response = await apiClient.post('/sessions/', data)
    return response.data
  },
  
  get: async (id: string) => {
    const response = await apiClient.get(`/sessions/${id}/`)
    return response.data
  },
  
  list: async (params?: {
    status?: string
    page?: number
    page_size?: number
  }) => {
    const response = await apiClient.get('/sessions/', { params })
    return response.data
  },
  
  completeRecording: async (id: string) => {
    const response = await apiClient.post(`/sessions/${id}/complete_recording/`)
    return response.data
  },

  exportJson: async (id: string) => {
    const response = await apiClient.get(`/sessions/${id}/export/`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `session-${id}.json`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

// Analysis API
export const analysisApi = {
  getFrames: async (sessionId: string, params?: {
    from_frame?: number
    to_frame?: number
    anomalies_only?: boolean
  }) => {
    const response = await apiClient.get(`/analysis/${sessionId}/frames/`, { params })
    return response.data
  },
  
  getStats: async (params?: {
    from_date?: string
    to_date?: string
  }) => {
    const response = await apiClient.get('/analysis/stats/', { params })
    return response.data
  },
}
