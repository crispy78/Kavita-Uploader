import React from 'react'

export default function WorkflowSteps({ colors }) {
  // Default colors (configurable via props)
  const defaultColors = {
    upload: 'orange',
    scan: 'yellow',
    metadata: 'yellow',
    publish: 'green'
  }
  
  const stepColors = colors || defaultColors

  const steps = [
    {
      number: 1,
      title: 'File Upload',
      description: 'Upload your e-book files',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
      color: stepColors.upload
    },
    {
      number: 2,
      title: 'Virus Scan',
      description: 'Scanning for viruses and malware',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
      color: stepColors.scan
    },
    {
      number: 3,
      title: 'Edit Metadata',
      description: 'Review and edit book information',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
      ),
      color: stepColors.metadata
    },
    {
      number: 4,
      title: 'Publish to Library',
      description: 'Move to Kavita library',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
        </svg>
      ),
      color: stepColors.publish
    }
  ]

  const getColorClasses = (color) => {
    const colors = {
      orange: 'bg-orange-100 text-orange-600 border-orange-300',
      yellow: 'bg-yellow-100 text-yellow-600 border-yellow-300',
      green: 'bg-green-100 text-green-600 border-green-300',
      blue: 'bg-blue-100 text-blue-600 border-blue-300',
      purple: 'bg-purple-100 text-purple-600 border-purple-300',
      emerald: 'bg-emerald-100 text-emerald-600 border-emerald-300'
    }
    return colors[color] || colors.blue
  }

  const getConnectorColor = (color) => {
    const colors = {
      orange: 'bg-orange-300',
      yellow: 'bg-yellow-300',
      green: 'bg-green-300',
      blue: 'bg-blue-300',
      purple: 'bg-purple-300',
      emerald: 'bg-emerald-300'
    }
    return colors[color] || colors.blue
  }

  const getBadgeGradient = (color) => {
    const gradients = {
      orange: 'bg-gradient-to-br from-orange-500 to-orange-600',
      yellow: 'bg-gradient-to-br from-yellow-500 to-yellow-600',
      green: 'bg-gradient-to-br from-green-500 to-green-600',
      blue: 'bg-gradient-to-br from-blue-500 to-blue-600',
      purple: 'bg-gradient-to-br from-purple-500 to-purple-600',
      emerald: 'bg-gradient-to-br from-emerald-500 to-emerald-600'
    }
    return gradients[color] || gradients.blue
  }

  return (
    <div className="mb-12">
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
        
        <div className="relative">
          {/* Steps Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative">
            {steps.map((step, index) => (
              <div key={step.number} className="relative">
                {/* Connector Line (not for last step) */}
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-12 left-1/2 w-full h-0.5 flex items-center">
                    <div className={`flex-1 h-0.5 ${getConnectorColor(step.color)} opacity-40`}></div>
                    <svg className={`w-5 h-5 ${getConnectorColor(step.color).replace('bg-','text-')}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l5 5a1 1 0 010 1.414l-5 5a1 1 0 11-1.414-1.414L13.586 10 10.293 6.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}

                {/* Step Card */}
                <div className="relative flex flex-col items-center text-center">
                  {/* Circle Icon */}
                  <div className={`
                    w-24 h-24 rounded-full 
                    flex items-center justify-center 
                    border-4 shadow-lg
                    transform transition-transform hover:scale-110
                    ${getColorClasses(step.color)}
                  `}>
                    {step.icon}
                  </div>

                  {/* Number badge removed per request */}

                  {/* Step Title */}
                  <h3 className="mt-4 font-bold text-gray-800 text-lg">
                    {step.title}
                  </h3>

                  {/* Step Description */}
                  <p className="mt-2 text-sm text-gray-600 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Info Note */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-500">
            All uploads go through these secure steps before reaching your Kavita library
          </p>
        </div>
      </div>
    </div>
  )
}

