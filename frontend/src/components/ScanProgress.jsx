import { useState, useEffect } from 'react'
import { scanUpload, getScanStatus } from '../services/api'

export default function ScanProgress({ uploadUuid, onScanComplete }) {
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState('idle') // idle, scanning, completed, error

  useEffect(() => {
    // Auto-start scan after a short delay
    const timer = setTimeout(() => {
      startScan()
    }, 1000)

    return () => clearTimeout(timer)
  }, [uploadUuid])

  const startScan = async () => {
    setScanning(true)
    setProgress('scanning')
    setError(null)

    try {
      const result = await scanUpload(uploadUuid)

      if (result.success) {
        const scanData = result.result

        if (scanData.status === 'pending') {
          // Poll for results
          pollScanStatus()
        } else {
          setScanResult(scanData)
          setProgress('completed')
          setScanning(false)

          if (onScanComplete) {
            onScanComplete(scanData)
          }
        }
      } else {
        setError(result.message || 'Scan failed')
        setProgress('error')
        setScanning(false)
      }
    } catch (err) {
      setError(err.response?.data?.detail?.message || 'Failed to start scan')
      setProgress('error')
      setScanning(false)
    }
  }

  const pollScanStatus = async () => {
    const maxAttempts = 60 // 5 minutes max
    let attempts = 0

    const poll = async () => {
      attempts++

      try {
        const status = await getScanStatus(uploadUuid)

        if (status.scan_status && status.scan_status !== 'pending') {
          setScanResult({
            scan_result: status.scan_status,
            scan_details: status.scan_details,
            scanned_at: status.scanned_at
          })
          setProgress('completed')
          setScanning(false)

          if (onScanComplete) {
            onScanComplete(status)
          }
        } else if (attempts < maxAttempts) {
          setTimeout(poll, 5000) // Poll every 5 seconds
        } else {
          setError('Scan timeout - please check back later')
          setProgress('error')
          setScanning(false)
        }
      } catch (err) {
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000)
        } else {
          setError('Failed to get scan status')
          setProgress('error')
          setScanning(false)
        }
      }
    }

    poll()
  }

  const getScanStatusIcon = () => {
    if (progress === 'scanning') {
      return (
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      )
    } else if (progress === 'completed') {
      const result = scanResult?.scan_result || scanResult?.status
      if (result === 'safe' || result === 'clean') {
        return (
          <svg className="w-12 h-12 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        )
      } else if (result === 'malicious' || result === 'infected') {
        return (
          <svg className="w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        )
      } else {
        return (
          <svg className="w-12 h-12 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      }
    } else if (progress === 'error') {
      return (
        <svg className="w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    }

    return null
  }

  const getScanStatusMessage = () => {
    if (progress === 'scanning') {
      return 'Scanning for viruses and malware...'
    } else if (progress === 'completed') {
      const result = scanResult?.scan_result || scanResult?.status
      if (result === 'safe' || result === 'clean') {
        return 'File is safe!'
      } else if (result === 'malicious' || result === 'infected') {
        return 'File is infected!'
      } else if (result === 'suspicious') {
        return 'File appears suspicious'
      } else {
        return 'Scan completed'
      }
    } else if (progress === 'error') {
      return error || 'Scan failed'
    }

    return ''
  }

  const getVirusTotalLink = () => {
    if (scanResult?.scan_details?.virustotal_link) {
      return scanResult.scan_details.virustotal_link
    }
    return null
  }

  return (
    <div className="mt-4 p-4 border rounded-lg">
      <div className="flex items-center space-x-4">
        {getScanStatusIcon()}

        <div className="flex-1">
          <h3 className="text-lg font-semibold">
            {getScanStatusMessage()}
          </h3>

          {scanResult?.scan_details && (
            <div className="mt-2 text-sm text-gray-600">
              <p>
                {scanResult.scan_details.malicious_count || 0} / {scanResult.scan_details.total_engines || 0} engines
                detected threats
              </p>
              {scanResult.scan_details.scan_date && (
                <p className="text-xs text-gray-500 mt-1">
                  Scanned: {new Date(scanResult.scan_details.scan_date).toLocaleString()}
                </p>
              )}
            </div>
          )}

          {progress === 'error' && (
            <button
              onClick={startScan}
              className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
            >
              Retry Scan
            </button>
          )}

          {getVirusTotalLink() && (
            <a
              href={getVirusTotalLink()}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-800 underline"
            >
              View full report on VirusTotal →
            </a>
          )}
        </div>
      </div>
    </div>
  )
}



