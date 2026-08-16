'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import { createClient } from '@/utils/supabase/client'

type Document = {
  id: string
  title: string
  original_filename: string
  file_type: string
  file_size_bytes: number
  status: string
  created_at: string
}

export function DocumentDashboard() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const supabase = createClient()

  const fetchDocuments = useCallback(async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const res = await fetch(`${API_URL}/api/v1/documents/`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      if (!res.ok) throw new Error('Failed to fetch documents')
      const data = await res.json()
      setDocuments(data.documents)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsLoading(false)
    }
  }, [API_URL, supabase.auth])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDocuments()
  }, [fetchDocuments])


  // Auto-poll while any document is still processing
  useEffect(() => {
    const hasPending = documents.some(d => d.status === 'processing' || d.status === 'queued')
    if (!hasPending) return
    const interval = setInterval(fetchDocuments, 4000)
    return () => clearInterval(interval)
  }, [documents, fetchDocuments])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setError(null)
    
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('Not authenticated')

      // 1. Get signed URL
      const signedUrlRes = await fetch(`${API_URL}/api/v1/documents/signed-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          filename: file.name,
          file_type: file.type,
          file_size_bytes: file.size
        })
      })

      if (!signedUrlRes.ok) {
        const errData = await signedUrlRes.json()
        throw new Error(errData.detail || 'Failed to get upload URL')
      }

      const { document_id, signed_url, file_path } = await signedUrlRes.json()

      // 2. Upload directly to Supabase Storage
      const uploadRes = await fetch(signed_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type
        }
      })

      if (!uploadRes.ok) {
        throw new Error('Failed to upload file to storage')
      }

      // 3. Register document
      const registerRes = await fetch(`${API_URL}/api/v1/documents/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          document_id,
          file_path,
          original_filename: file.name,
          file_type: file.type,
          file_size_bytes: file.size
        })
      })

      if (!registerRes.ok) {
        const errData = await registerRes.json()
        throw new Error(errData.detail || 'Failed to register document')
      }

      await fetchDocuments()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }
  
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return
    
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('Not authenticated')

      const res = await fetch(`${API_URL}/api/v1/documents/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      
      if (!res.ok) throw new Error('Failed to delete document')
      
      await fetchDocuments()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const formatBytes = (bytes: number, decimals = 2) => {
      if (!+bytes) return '0 Bytes'
      const k = 1024
      const dm = decimals < 0 ? 0 : decimals
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
  }

  return (
    <div className="space-y-6 mt-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">Your Documents</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">Upload and manage your documents for processing.</p>
        </div>
        
        <div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleUpload}
            className="hidden"
            accept=".pdf,.docx,.png,.jpg,.jpeg"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950 disabled:pointer-events-none disabled:opacity-50 bg-zinc-900 text-zinc-50 hover:bg-zinc-900/90 h-10 px-4 py-2 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-50/90"
          >
            {isUploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-red-50 text-red-900 border border-red-200 dark:bg-red-950/50 dark:text-red-200 dark:border-red-900/50 text-sm">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center p-8 text-sm text-zinc-500">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 border border-dashed rounded-lg border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
          <p className="text-sm text-zinc-500 dark:text-zinc-400 text-center">No documents yet.<br/>Upload one to get started.</p>
        </div>
      ) : (
        <div className="rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-zinc-500 uppercase bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
              <tr>
                <th className="px-6 py-3 font-medium">Name</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Size</th>
                <th className="px-6 py-3 font-medium">Date</th>
                <th className="px-6 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map(doc => (
                <tr key={doc.id} className="border-b border-zinc-200 dark:border-zinc-800 last:border-0 hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors">
                  <td className="px-6 py-4 font-medium text-zinc-900 dark:text-zinc-100">
                    {doc.original_filename}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border capitalize ${
                      doc.status === 'ready' 
                        ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-900'
                        : doc.status === 'failed'
                        ? 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-900'
                        : doc.status === 'processing' || doc.status === 'queued'
                        ? 'bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-950 dark:text-yellow-300 dark:border-yellow-900'
                        : 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300 border-zinc-200 dark:border-zinc-700'
                    }`}>
                      {doc.status === 'processing' || doc.status === 'queued' ? '⟳ ' : ''}{doc.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-zinc-500">
                    {formatBytes(doc.file_size_bytes)}
                  </td>
                  <td className="px-6 py-4 text-zinc-500 whitespace-nowrap">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right flex items-center justify-end gap-3">
                    {doc.status === 'ready' && (
                      <Link 
                        href={`/dashboard/documents/${doc.id}`}
                        className="text-zinc-900 hover:text-zinc-600 dark:text-zinc-100 dark:hover:text-zinc-400 font-medium text-xs border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1 bg-white dark:bg-zinc-900"
                      >
                        Ask AI
                      </Link>
                    )}
                    <button 
                      onClick={() => handleDelete(doc.id)}
                      className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
