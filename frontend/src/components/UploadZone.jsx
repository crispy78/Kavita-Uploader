import { useState, useCallback, useEffect } from 'react'
import { uploadFile } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

export default function UploadZone({ config, onUploadComplete }) {
  const { isAuthenticated, requireAuth, authEnabled, user, loading: authLoading } = useAuth()
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadStage, setUploadStage] = useState('idle') // idle, uploading, quarantined, error
  const [error, setError] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  
  // Check if authentication is required for uploads
  // Only block if auth is enabled, required, and user is actually not authenticated
  // Wait for auth to finish loading before checking
  const needsAuth = !authLoading && authEnabled && requireAuth && !isAuthenticated
  
  // Debug logging (can be removed after fixing)
  useEffect(() => {
    if (authEnabled) {
      console.debug('UploadZone auth state:', { authEnabled, requireAuth, isAuthenticated, authLoading, user })
    }
  }, [authEnabled, requireAuth, isAuthenticated, authLoading, user])

  const maxSizeMB = config?.upload?.max_file_size_mb || 25
  const allowedExtensions = config?.upload?.allowed_extensions || []

  const validateFile = (file) => {
    // Check file size
    const maxSizeBytes = maxSizeMB * 1024 * 1024
    if (file.size > maxSizeBytes) {
      return `File size exceeds ${maxSizeMB} MB limit`
    }

    if (file.size === 0) {
      return 'File is empty'
    }

    // Check file extension
    const extension = file.name.split('.').pop().toLowerCase()
    if (!allowedExtensions.includes(extension)) {
      return `Only ${allowedExtensions.join(', ')} files are allowed`
    }

    return null
  }

  const handleFile = async (file) => {
    setError(null)
    setSelectedFile(file)
    
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      setUploadStage('error')
      return
    }

    setIsUploading(true)
    setUploadStage('uploading')
    setUploadProgress(0)

    try {
      const result = await uploadFile(file, (progress) => {
        setUploadProgress(progress)
      })

      if (result.success) {
        setUploadStage('quarantined')
        if (onUploadComplete) {
          onUploadComplete({
            uuid: result.upload.uuid,
            filename: result.upload.filename,
            file_size: result.upload.file_size,
            file_size_formatted: result.upload.file_size_formatted,
            status: result.upload.status,
            uploaded_at: result.upload.uploaded_at,
          })
        }
        
        // Reset after 3 seconds
        setTimeout(() => {
          resetUpload()
        }, 3000)
      }
    } catch (err) {
      console.error('Upload error:', err)
      
      // Handle different error types
      if (err.response?.status === 401) {
        const errorMessage = err.response?.data?.detail?.message || err.response?.data?.message || 'Authentication required. Please log in to upload files.'
        setError(errorMessage)
        setUploadStage('error')
      } else if (err.response?.status === 422) {
        // Validation error
        const errorMessage = err.response?.data?.message || err.response?.data?.detail?.message || 'File upload validation failed. Please check your file.'
        setError(errorMessage)
        setUploadStage('error')
      } else if (err.response?.status === 413 || err.response?.status === 507) {
        // File too large or insufficient storage
        const errorMessage = err.response?.data?.detail?.message || err.response?.data?.message || 'File is too large or storage is insufficient.'
        setError(errorMessage)
        setUploadStage('error')
      } else {
        const errorMessage = err.response?.data?.detail?.message || err.response?.data?.message || err.response?.data?.detail || err.message || 'Upload failed. Please try again.'
        setError(errorMessage)
        setUploadStage('error')
      }
    } finally {
      setIsUploading(false)
    }
  }

  const resetUpload = () => {
    setUploadStage('idle')
    setUploadProgress(0)
    setSelectedFile(null)
    setError(null)
  }

  const handleDragEnter = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      handleFile(files[0])
    }
  }, [])

  const handleFileSelect = (e) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFile(files[0])
    }
  }

  const getStageIcon = () => {
    switch (uploadStage) {
      case 'uploading':
        return (
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
        )
      case 'quarantined':
        return (
          <svg className="w-16 h-16 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      case 'error':
        return (
          <svg className="w-16 h-16 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      default:
        return (
          <svg className="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        )
    }
  }

  const getStageMessage = () => {
    if (needsAuth) {
      return 'Please log in to upload files'
    }
    
    switch (uploadStage) {
      case 'uploading':
        return `Uploading... ${uploadProgress}%`
      case 'quarantined':
        return 'File quarantined successfully!'
      case 'error':
        return error || 'Upload failed'
      default:
        return 'Drag and drop your e-book here'
    }
  }
  
  const handleClick = () => {
    if (needsAuth) {
      setError('Please log in to upload files. Click the Login button in the header.')
      return
    }
    if (!isUploading) {
      document.getElementById('file-input').click()
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg p-8">
      <div
        className={`
          relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300
          ${isDragging ? 'border-blue-500 bg-blue-50 scale-105' : 'border-gray-300 bg-gray-50'}
          ${uploadStage === 'quarantined' ? 'border-green-500 bg-green-50' : ''}
          ${uploadStage === 'error' ? 'border-red-500 bg-red-50' : ''}
          ${needsAuth ? 'border-gray-300 bg-gray-100 cursor-not-allowed opacity-60' : ''}
          ${isUploading ? 'cursor-not-allowed' : needsAuth ? '' : 'cursor-pointer hover:border-blue-400 hover:bg-blue-50'}
        `}
        onDragEnter={needsAuth ? undefined : handleDragEnter}
        onDragOver={needsAuth ? undefined : handleDragOver}
        onDragLeave={needsAuth ? undefined : handleDragLeave}
        onDrop={needsAuth ? undefined : handleDrop}
        onClick={handleClick}
      >
        <input
          id="file-input"
          type="file"
          className="hidden"
          onChange={handleFileSelect}
          accept={allowedExtensions.map(ext => `.${ext}`).join(',')}
          disabled={isUploading}
        />

        <div className="flex flex-col items-center space-y-4">
          {getStageIcon()}

          <div>
            <p className="text-xl font-semibold text-gray-700 mb-2">
              {getStageMessage()}
            </p>
            
            {uploadStage === 'idle' && (
              <>
                <p className="text-gray-500 mb-4">
                  or click to browse files
                </p>
                <div className="text-sm text-gray-400">
                  <p>Supported formats: {allowedExtensions.join(', ').toUpperCase()}</p>
                  <p className="mt-1">Maximum file size: {maxSizeMB} MB</p>
                </div>
              </>
            )}

            {selectedFile && uploadStage === 'uploading' && (
              <div className="mt-4">
                <p className="text-sm text-gray-600 mb-2">{selectedFile.name}</p>
                <div className="w-64 mx-auto bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
              </div>
            )}

            {selectedFile && uploadStage === 'quarantined' && (
              <p className="text-sm text-green-600 mt-2">
                {selectedFile.name} has been quarantined
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}



