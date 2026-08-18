'use client'

import { useState, useEffect } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'

interface DocumentViewerProps {
  documentId: string
  accessToken: string
}

export function DocumentViewer({ documentId, accessToken }: DocumentViewerProps) {
  const [url, setUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    const fetchUrl = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/documents/${documentId}/download-url`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          }
        })
        if (!res.ok) {
          throw new Error('Failed to fetch document preview URL')
        }
        const data = await res.json()
        setUrl(data.url)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setIsLoading(false)
      }
    }

    fetchUrl()
  }, [documentId, accessToken, API_URL])

  if (isLoading) {
    return (
      <div className="absolute inset-0 flex items-center justify-center p-8 bg-zinc-50/50 dark:bg-zinc-950/50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
          <p className="text-sm font-medium text-zinc-500">Loading document...</p>
        </div>
      </div>
    )
  }

  if (error || !url) {
    return (
      <div className="absolute inset-0 flex items-center justify-center p-8 bg-zinc-50/50 dark:bg-zinc-950/50">
        <div className="flex flex-col items-center text-center gap-3 max-w-sm">
          <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-500" />
          </div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Failed to load preview</p>
          <p className="text-xs text-zinc-500">{error || 'Unknown error occurred'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="absolute inset-0 bg-zinc-100 dark:bg-zinc-900">
      <object 
        data={url} 
        type="application/pdf" 
        className="w-full h-full"
      >
        {/* Fallback if PDF plugin isn't supported */}
        <div className="absolute inset-0 flex items-center justify-center p-8 bg-zinc-50 dark:bg-zinc-950">
          <div className="flex flex-col items-center text-center gap-3 max-w-sm">
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">PDF Viewer not supported</p>
            <p className="text-xs text-zinc-500">
              Your browser doesn't support embedded PDFs. 
              <a href={url} target="_blank" rel="noopener noreferrer" className="ml-1 text-indigo-500 hover:underline">
                Click here to download it.
              </a>
            </p>
          </div>
        </div>
      </object>
    </div>
  )
}
