import { useState, useEffect } from 'react'
import { getMetadata, updateMetadata, getPreview } from '../services/api'

export default function MetadataModal({ uploadUuid, filename, onClose, onSave }) {
  const [metadata, setMetadata] = useState({
    title: '',
    author: '',
    language: '',
    series: '',
    volume: '',
    publisher: '',
    year: ''
  })
  const [validation, setValidation] = useState({ is_valid: true, missing_fields: [] })
  const [previews, setPreviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadMetadata()
    loadPreview()
  }, [uploadUuid])

  const loadMetadata = async () => {
    try {
      const result = await getMetadata(uploadUuid)
      if (result.success) {
        setMetadata(result.metadata)
        setValidation(result.validation)
      } else {
        setError('Failed to load metadata')
      }
    } catch (err) {
      console.error('Failed to load metadata:', err)
      setError(err.response?.data?.detail || 'Failed to load metadata')
    } finally {
      setLoading(false)
    }
  }

  const loadPreview = async () => {
    try {
      const result = await getPreview(uploadUuid)
      if (result.success && result.previews && result.previews.length > 0) {
        setPreviews(result.previews)
      }
    } catch (err) {
      console.error('Failed to load preview:', err)
      // Preview is optional, don't show error
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleChange = (field, value) => {
    setMetadata(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)

    try {
      // Client-side guard using required_fields (fallback to sensible defaults)
      const required = (validation?.required_fields && validation.required_fields.length > 0)
        ? validation.required_fields
        : ['title', 'author']
      const missingClient = required.filter((f) => {
        const v = String(metadata?.[f] ?? '').trim()
        return v.length === 0
      })
      if (missingClient.length > 0) {
        setValidation(prev => ({
          ...(prev || {}),
          is_valid: false,
          missing_fields: missingClient
        }))
        setError(`Missing required field${missingClient.length > 1 ? 's' : ''}: ${missingClient.join(', ')}`)
        setSaving(false)
        return
      }

      const result = await updateMetadata(uploadUuid, metadata)
      if (result.success) {
        onSave(result.metadata)
        onClose()
      } else {
        // Capture validation for UI; avoid generic error when it's just validation
        setError(null)
        setValidation(result.validation)
      }
    } catch (err) {
      console.error('Failed to save metadata:', err)
      setError(err.response?.data?.detail?.error || 'Failed to save metadata')
    } finally {
      setSaving(false)
    }
  }

  const getValidationMessage = () => {
    const missing = validation?.missing_fields || []
    if (validation && validation.is_valid === false && missing.length > 0) {
      return `Missing required field${missing.length > 1 ? 's' : ''}: ${missing.join(', ')}`
    }
    return null
  }

  const isFieldRequired = (field) => {
    return validation?.required_fields?.includes(field) || false
  }

  const isFieldMissing = (field) => {
    return validation?.missing_fields?.includes(field) || false
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="text-gray-700">Loading metadata...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col my-8">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Metadata Editor</h2>
              <p className="text-sm text-gray-600 mt-1">{filename}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Preview Section */}
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Preview</h3>
              <div className="space-y-4">
                {previewLoading ? (
                  <div className="bg-gray-100 rounded-lg p-8 flex items-center justify-center">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                      <p className="mt-3 text-sm text-gray-600">Loading preview...</p>
                    </div>
                  </div>
                ) : previews && previews.length > 0 ? (
                  previews.map((preview, index) => (
                    <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <p className="text-xs text-gray-500 mb-2">Page {index + 1}</p>
                      <img
                        src={`data:image/png;base64,${preview}`}
                        alt={`Preview page ${index + 1}`}
                        className="w-full h-auto rounded shadow-sm"
                      />
                    </div>
                  ))
                ) : (
                  <div className="bg-gray-50 rounded-lg p-8 text-center border border-gray-200">
                    <svg className="w-16 h-16 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-gray-500 text-sm">Preview not available</p>
                  </div>
                )}
              </div>
            </div>

            {/* Metadata Fields */}
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Metadata Fields</h3>
              
          {(!validation?.is_valid && getValidationMessage()) ? (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{getValidationMessage()}</p>
            </div>
          ) : (
            error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )
          )}

              {validation && !validation.is_valid && validation.missing_fields && validation.missing_fields.length > 0 && (
                <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    Please complete the required field{validation.missing_fields.length > 1 ? 's' : ''}: {validation.missing_fields.join(', ')}
                  </p>
                </div>
              )}

              <div className="space-y-4">
                {/* Title */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Title {isFieldRequired('title') && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    value={metadata?.title || ''}
                    onChange={(e) => handleChange('title', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      isFieldMissing('title') ? 'border-red-300 bg-red-50' : 'border-gray-300'
                    }`}
                    placeholder="Enter title"
                  />
                  {isFieldMissing('title') && (
                    <p className="mt-1 text-xs text-red-600">Title is required</p>
                  )}
                </div>

                {/* Author */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Author {isFieldRequired('author') && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    value={metadata?.author || ''}
                    onChange={(e) => handleChange('author', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      isFieldMissing('author') ? 'border-red-300 bg-red-50' : 'border-gray-300'
                    }`}
                    placeholder="Enter author name"
                  />
                  {isFieldMissing('author') && (
                    <p className="mt-1 text-xs text-red-600">Author is required</p>
                  )}
                </div>

                {/* Series */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Series {isFieldRequired('series') && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    value={metadata?.series || ''}
                    onChange={(e) => handleChange('series', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter series name (optional)"
                  />
                  {isFieldMissing('series') && (
                    <p className="mt-1 text-xs text-red-600">Series is required</p>
                  )}
                </div>

                {/* Volume */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Volume {isFieldRequired('volume') && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    value={metadata?.volume || ''}
                    onChange={(e) => handleChange('volume', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter volume number (optional)"
                  />
                  {isFieldMissing('volume') && (
                    <p className="mt-1 text-xs text-red-600">Volume is required</p>
                  )}
                </div>

                {/* Publisher */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Publisher {isFieldRequired('publisher') && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    value={metadata?.publisher || ''}
                    onChange={(e) => handleChange('publisher', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter publisher (optional)"
                  />
                  {isFieldMissing('publisher') && (
                    <p className="mt-1 text-xs text-red-600">Publisher is required</p>
                  )}
                </div>

                {/* Year */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Year {isFieldRequired('year') && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    value={metadata?.year || ''}
                    onChange={(e) => handleChange('year', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter publication year (optional)"
                  />
                  {isFieldMissing('year') && (
                    <p className="mt-1 text-xs text-red-600">Year is required</p>
                  )}
                </div>

                {/* Language */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Language {isFieldRequired('language') && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    value={metadata?.language || ''}
                    onChange={(e) => handleChange('language', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter language (optional)"
                  />
                  {isFieldMissing('language') && (
                    <p className="mt-1 text-xs text-red-600">Language is required</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            <span className="text-red-500">*</span> Required fields
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Save & Continue</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

