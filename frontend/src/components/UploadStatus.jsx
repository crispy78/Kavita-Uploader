import { useState, useEffect } from 'react'
import { getUploadStatus, moveToUnsorted } from '../services/api'
import MetadataModal from './MetadataModal'

export default function UploadStatus({ uploadInfo }) {
  const [expanded, setExpanded] = useState(true)  // Expanded by default
  const [details, setDetails] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showMetadataModal, setShowMetadataModal] = useState(false)

  // Load details on mount since expanded by default
  useEffect(() => {
    loadDetails()
  }, [])

  // Poll status until it reaches a terminal state so the Edit/Publish button becomes available
  useEffect(() => {
    let intervalId
    const terminalStatuses = new Set(['safe', 'clean', 'metadata_verified', 'moved', 'duplicate_discarded'])
    if (!details || !terminalStatuses.has(details.status)) {
      intervalId = setInterval(async () => {
        try {
          const result = await getUploadStatus(uploadInfo.uuid)
          if (result?.upload) {
            setDetails(result.upload)
            if (terminalStatuses.has(result.upload.status)) {
              clearInterval(intervalId)
            }
          }
        } catch {}
      }, 5000)
    }
    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [details, uploadInfo?.uuid])

  const loadDetails = async () => {
    if (details || loading) return
    
    setLoading(true)
    try {
      const result = await getUploadStatus(uploadInfo.uuid)
      setDetails(result.upload)
    } catch (error) {
      console.error('Failed to load details:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = () => {
    if (!expanded) {
      loadDetails()
    }
    setExpanded(!expanded)
  }

  const handleMetadataSave = async (metadata) => {
    // Update details and then attempt publish (move)
    setDetails(prev => ({
      ...prev,
      status: 'metadata_verified',
      metadata_json: JSON.stringify(metadata)
    }))

    try {
      const moveResult = await moveToUnsorted(uploadInfo.uuid)
      if (moveResult?.success) {
        setDetails(prev => ({
          ...prev,
          status: 'moved',
          final_path: moveResult.destination || prev?.final_path
        }))
      }
    } catch {}
  }

  const getStatusColor = (status) => {
    if (!status) return 'text-gray-600 bg-gray-50 border-gray-200'
    
    switch (status) {
      case 'quarantined':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'safe':
      case 'clean':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'infected':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'moved':
        return 'text-emerald-600 bg-emerald-50 border-emerald-200'
      case 'metadata_verified':
        return 'text-purple-600 bg-purple-50 border-purple-200'
      case 'duplicate_discarded':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getScanningIndicator = () => (
    <div className="flex items-center space-x-3 text-blue-600">
      <div className="relative h-5 w-5">
        <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-300 border-t-blue-600"></div>
      </div>
      <span className="text-sm">Scanning for viruses and malware…</span>
    </div>
  )

  const getFinalFilename = (finalPath) => {
    if (!finalPath) return null
    try {
      const parts = String(finalPath).split(/[/\\]/)
      return parts[parts.length - 1] || null
    } catch {
      return null
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    try {
      const date = new Date(dateString)
      return date.toLocaleString()
    } catch {
      return 'N/A'
    }
  }

  // Null safety check
  if (!uploadInfo) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
      <div
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={handleToggle}
      >
        <div className="flex items-center space-x-4 flex-1">
          <div className="flex-shrink-0">
            <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {uploadInfo.filename || 'Unknown'}
            </p>
            <p className="text-xs text-gray-500">
              {uploadInfo.file_size_formatted || 'Unknown size'} • {formatDate(uploadInfo.uploaded_at)}
            </p>
          </div>

          <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(uploadInfo.status)}`}>
            {uploadInfo.status || 'unknown'}
          </div>
        </div>

        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {expanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          {loading ? (
            <div className="text-center py-4">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : details ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-600">UUID:</span>
                  <p className="text-gray-900 font-mono text-xs mt-1 break-all">{details.uuid}</p>
                </div>
                <div>
                  <span className="font-medium text-gray-600">MIME Type:</span>
                  <p className="text-gray-900 mt-1">{details.mime_type || 'Unknown'}</p>
                </div>
                <div>
                  <span className="font-medium text-gray-600">File Size:</span>
                  <p className="text-gray-900 mt-1">{details.file_size} bytes</p>
                </div>
                <div>
                  <span className="font-medium text-gray-600">Status:</span>
                  <p className="text-gray-900 mt-1 capitalize">{details.status}</p>
                </div>
              </div>

              {/* Metadata Action Button */}
              {(
                 details.status === 'safe' ||
                 details.status === 'clean' ||
                 details.scan_result === 'safe' ||
                 details.scan_result === 'clean' ||
                 details.status === 'metadata_verified'
               ) && details.status !== 'moved' && (
                <div className="pt-3 border-t border-gray-200">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setShowMetadataModal(true)
                    }}
                    className="w-full px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 flex items-center justify-center space-x-2 shadow-sm"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    <span>Edit Metadata & Publish</span>
                  </button>
                </div>
              )}

              {/* Show metadata status if verified */}
              {(details.status === 'metadata_verified' || details.status === 'moved') && (
                <div className="pt-3 border-t border-gray-200">
                  <div className="flex items-center space-x-2 text-green-600">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">Metadata verified - Ready for Step 4</span>
                  </div>
                </div>
              )}

              {/* Show scanning indicator */}
              {(details.status === 'scanning' || details.scan_result === 'pending') && (
                <div className="pt-3 border-t border-gray-200">
                  {getScanningIndicator()}
                </div>
              )}

              {/* Show moved status (no directory path, only filename) */}
              {details.status === 'moved' && (
                <div className="pt-3 border-t border-gray-200">
                  <div className="flex items-center space-x-2 text-emerald-600 mb-1">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">File moved to library</span>
                  </div>
                  {getFinalFilename(details.final_path) ? (
                    <p className="text-xs text-gray-700">Saved as: <span className="font-mono">{getFinalFilename(details.final_path)}</span></p>
                  ) : (
                    <p className="text-xs text-gray-500">Destination hidden for security</p>
                  )}

                  {/* Brief metadata to help find it in Kavita */}
                  {details.metadata_json && (
                    (() => {
                      let meta
                      try { meta = JSON.parse(details.metadata_json || '{}') } catch { meta = null }
                      if (!meta) return null
                      const title = meta.title || null
                      const author = meta.author || null
                      if (!title && !author) return null
                      return (
                        <p className="text-xs text-gray-600 mt-1">
                          {title && <><span className="font-medium">Title:</span> {title}</>}
                          {title && author ? ' • ' : ''}
                          {author && <><span className="font-medium">Author:</span> {author}</>}
                        </p>
                      )
                    })()
                  )}
                </div>
              )}

              <div className="pt-3 border-t border-gray-200 mt-3">
                <p className="text-xs text-gray-500">
                  <strong>Progress:</strong> ✅ Upload → ✅ Scan → 
                  {details.status === 'metadata_verified' || details.status === 'moved' ? ' ✅ Metadata' : ' Metadata'} → 
                  {details.status === 'moved' ? ' ✅ Move' : ' Move'}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Failed to load details</p>
          )}
        </div>
      )}

      {/* Metadata Modal */}
      {showMetadataModal && details && (
        <MetadataModal
          uploadUuid={details.uuid}
          filename={details.original_filename}
          onClose={() => setShowMetadataModal(false)}
          onSave={handleMetadataSave}
        />
      )}
    </div>
  )
}
