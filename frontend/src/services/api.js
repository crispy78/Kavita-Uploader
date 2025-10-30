import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
    'X-UI-Request': '1',
  },
})

export const getConfig = async () => {
  const response = await api.get('/config')
  return response.data
}

export const uploadFile = async (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
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

export default api

