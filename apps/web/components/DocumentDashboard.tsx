'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import { createClient } from '@/utils/supabase/client'
import { Upload, FileText, Trash2, ArrowRight, Loader2, AlertCircle } from 'lucide-react'

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
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
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
            className="inline-flex items-center justify-center gap-2 rounded-full text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950 disabled:pointer-events-none disabled:opacity-50 bg-zinc-900 text-zinc-50 hover:bg-zinc-800 h-10 px-6 py-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 shadow-sm"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Upload Document
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 text-red-900 border border-red-200 dark:bg-red-950/50 dark:text-red-200 dark:border-red-900/50 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 text-zinc-500">
          <Loader2 className="w-8 h-8 animate-spin text-zinc-400 mb-4" />
          <p className="text-sm font-medium">Loading your documents...</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 py-20 border-2 border-dashed rounded-2xl border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-950/50 text-center">
          <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center mb-6">
            <FileText className="w-8 h-8 text-zinc-400" />
          </div>
          <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-2">No documents yet</h3>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-sm mb-6">
            Upload your first document to start extracting intelligence and asking questions.
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center justify-center gap-2 rounded-full text-sm font-medium transition-colors bg-white border border-zinc-200 text-zinc-900 hover:bg-zinc-50 h-10 px-6 py-2 dark:bg-zinc-900 dark:border-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-800"
          >
            <Upload className="w-4 h-4" />
            Upload your first document
          </button>
        </div>
      ) : (
        <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left whitespace-nowrap">
              <thead className="text-xs text-zinc-500 uppercase bg-zinc-50 dark:bg-zinc-900/50 border-b border-zinc-200 dark:border-zinc-800">
                <tr>
                  <th className="px-6 py-4 font-semibold tracking-wider">Name</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Status</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Size</th>
                  <th className="px-6 py-4 font-semibold tracking-wider">Date</th>
                  <th className="px-6 py-4 font-semibold tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {documents.map(doc => (
                  <tr key={doc.id} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-900/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center shrink-0">
                          <FileText className="w-4 h-4 text-zinc-500" />
                        </div>
                        <span className="font-medium text-zinc-900 dark:text-zinc-100 truncate max-w-[200px] sm:max-w-xs md:max-w-md">
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide uppercase border ${
                        doc.status === 'ready' 
                          ? 'bg-green-50 text-green-700 border-green-200/60 dark:bg-green-500/10 dark:text-green-400 dark:border-green-500/20'
                          : doc.status === 'failed'
                          ? 'bg-red-50 text-red-700 border-red-200/60 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20'
                          : doc.status === 'processing' || doc.status === 'queued'
                          ? 'bg-yellow-50 text-yellow-700 border-yellow-200/60 dark:bg-yellow-500/10 dark:text-yellow-400 dark:border-yellow-500/20'
                          : 'bg-zinc-100 text-zinc-800 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700'
                      }`}>
                        {(doc.status === 'processing' || doc.status === 'queued') && (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        )}
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-zinc-500 dark:text-zinc-400 font-medium">
                      {formatBytes(doc.file_size_bytes)}
                    </td>
                    <td className="px-6 py-4 text-zinc-500 dark:text-zinc-400">
                      {new Date(doc.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {doc.status === 'ready' ? (
                          <Link 
                            href={`/dashboard/documents/${doc.id}`}
                            className="inline-flex items-center gap-1.5 bg-zinc-900 text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 font-medium text-xs rounded-full px-4 py-2 transition-colors shadow-sm"
                          >
                            Ask AI <ArrowRight className="w-3 h-3" />
                          </Link>
                        ) : (doc.status === 'processing' || doc.status === 'queued') ? (
                          <span className="inline-flex items-center bg-zinc-100 text-zinc-400 dark:bg-zinc-900 dark:text-zinc-600 font-medium text-xs rounded-full px-4 py-2 cursor-not-allowed border border-transparent">
                            Processing...
                          </span>
                        ) : null}
                        
                        <button 
                          onClick={() => handleDelete(doc.id)}
                          className="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-950/30 rounded-full transition-colors ml-2"
                          title="Delete document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
