import { useState, useEffect } from 'react'
import UploadZone from './components/UploadZone'
import UploadStatus from './components/UploadStatus'
import Header from './components/Header'
import WorkflowSteps from './components/WorkflowSteps'
import { getConfig } from './services/api'

function App() {
  const [config, setConfig] = useState(null)
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const data = await getConfig()
      setConfig(data)
    } catch (error) {
      console.error('Failed to load config:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUploadComplete = (uploadInfo) => {
    setUploadedFiles(prev => [uploadInfo, ...prev])
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <div className="animate-pulse text-gray-600">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Header />
      
      <main className="container mx-auto px-4 py-8 max-w-6xl">
        <WorkflowSteps />

        <UploadZone config={config} onUploadComplete={handleUploadComplete} />

        {uploadedFiles.length > 0 && (
          <div className="mt-12">
            <div className="space-y-4">
              {uploadedFiles.map((file) => (
                <UploadStatus key={file.uuid} uploadInfo={file} />
              ))}
            </div>
          </div>
        )}
      </main>

      <footer className="container mx-auto px-4 py-8 max-w-6xl mt-12">
        <div className="text-center text-sm text-gray-500">
          <p>Kavita Uploader v0.1.0</p>
        </div>
      </footer>
    </div>
  )
}

export default App



