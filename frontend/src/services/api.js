import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
    'X-UI-Request': '1',
  },
  withCredentials: true, // Always include credentials (cookies) for all requests
})

export const getConfig = async () => {
  const response = await api.get('/config')
  return response.data
}

export const uploadFile = async (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)

  // For FormData uploads, we need axios to set Content-Type automatically with boundary
  // Create a temporary axios instance without the default Content-Type header
  const uploadApi = axios.create({
    baseURL: API_BASE,
    withCredentials: true,
  })

  const response = await uploadApi.post('/upload', formData, {
    headers: {
      'X-UI-Request': '1',
      // Don't set Content-Type - axios will automatically set multipart/form-data with boundary
    },
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      )
      if (onProgress) {
        onProgress(percentCompleted)
      }
    },
  })

  return response.data
}

export const getUploadStatus = async (uuid) => {
  const response = await api.get(`/upload/${uuid}`)
  return response.data
}

// Step 2: Scanning endpoints
export const scanUpload = async (uuid) => {
  const response = await api.post(`/upload/${uuid}/scan`)
  return response.data
}

export const getScanStatus = async (uuid) => {
  const response = await api.get(`/upload/${uuid}/scan/status`)
  return response.data
}

export const checkDuplicate = async (uuid) => {
  const response = await api.post(`/upload/${uuid}/check-duplicate`)
  return response.data
}

export const getPreview = async (uuid) => {
  const response = await api.get(`/upload/${uuid}/preview`)
  return response.data
}

// Step 3: Metadata endpoints (stub)
export const getMetadata = async (uuid) => {
  const response = await api.get(`/upload/${uuid}/metadata`)
  return response.data
}

export const updateMetadata = async (uuid, metadata) => {
  const response = await api.put(`/upload/${uuid}/metadata`, metadata)
  return response.data
}

// Step 4: Move endpoints (IMPLEMENTED)
export const moveToUnsorted = async (uuid) => {
  const response = await api.post(`/upload/${uuid}/move`)
  return response.data
}

export const getMoveStatus = async (uuid) => {
  const response = await api.get(`/upload/${uuid}/move/status`)
  return response.data
}

// Authentication endpoints
export const login = async (username, password) => {
  const response = await api.post('/auth/login', {
    username,
    password
  })
  return response.data
}

export const logout = async () => {
  const response = await api.post('/auth/logout', {})
  return response.data
}

export const getCurrentUser = async () => {
  try {
    const response = await api.get('/auth/me')
    return response.data
  } catch (error) {
    // Return null if not authenticated (401)
    if (error.response?.status === 401) {
      return { authenticated: false }
    }
    throw error
  }
}

export default api

