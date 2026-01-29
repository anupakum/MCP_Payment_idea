"use client"

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileText, Calendar, DollarSign, AlertCircle, Download } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

export interface CaseData {
  case_id: string
  dispute_status?: string
  status?: string
  transaction_id?: string
  customer_id?: string
  transaction_amount?: number
  amount_disputed?: number
  decision_reason?: string
  description?: string
  credit_type?: string
  credit_amount?: number
  created_at?: string
  created_date?: string
  updated_at?: string
  documents?: Array<{
    filename: string
    url: string
    key: string
    download_url?: string
  }>
}

export interface CaseCardProps {
  caseData: CaseData
  index?: number
  onClick?: () => void
  showCustomerId?: boolean
}

export function CaseCard({ caseData, index, onClick, showCustomerId = true }: CaseCardProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const handleDownloadDocuments = async (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click when clicking button
    
    setIsDownloading(true)
    setDownloadError(null)
    
    try {
      // Debug logging
      console.log('CaseCard caseData:', caseData)
      console.log('CaseCard documents:', caseData.documents)
      
      // Check if documents already have download URLs (from upload response)
      const existingDocs = caseData.documents || []
      const hasDownloadUrls = existingDocs.length > 0 && existingDocs.some(doc => doc.download_url)
      
      console.log('Existing docs:', existingDocs)
      console.log('Has download URLs?', hasDownloadUrls)
      
      let documents = existingDocs
      
      // If no download URLs, fetch from API
      if (!hasDownloadUrls) {
        console.log('Fetching from API...')
        const response = await apiClient.getCaseDocuments(caseData.case_id)
        
        console.log('API Response:', response)
        
        if (response.success && response.data) {
          documents = response.data.documents || []
          console.log('Documents from API:', documents)
        } else {
          console.error('API Error:', response.error)
          setDownloadError(response.error || response.message || 'Failed to get document URLs')
          return
        }
      }
      
      if (documents.length === 0) {
        setDownloadError('No documents found for this case')
        return
      }
      
      console.log('Downloading documents:', documents)
      
      // Download each document
      for (const doc of documents) {
        if (doc.download_url) {
          console.log('Opening URL:', doc.download_url)
          // Open in new tab to trigger download
          window.open(doc.download_url, '_blank')
        } else {
          console.warn('Document missing download_url:', doc)
        }
      }
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : 'Download failed')
    } finally {
      setIsDownloading(false)
    }
  }

  const getStatusColor = (status?: string) => {
    const statusUpper = status?.toUpperCase() || ''
    
    if (statusUpper.includes('RESOLVED') || statusUpper.includes('APPROVED')) {
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
    } else if (statusUpper.includes('REJECTED') || statusUpper.includes('DECLINED')) {
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
    } else if (statusUpper.includes('FORWARDED') || statusUpper.includes('PENDING')) {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
    } else if (statusUpper.includes('REVIEW') || statusUpper.includes('INVESTIGATING')) {
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
    } else {
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
    }
  }

  const getCreditTypeColor = (creditType?: string) => {
    if (creditType === 'PERMANENT') {
      return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-300'
    } else if (creditType === 'TEMPORARY') {
      return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300'
    } else {
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
    }
  }

  const status = caseData.dispute_status || caseData.status || 'UNKNOWN'
  const amount = Number(caseData.transaction_amount || caseData.amount_disputed || 0)
  const createdAt = new Date(caseData.created_at || caseData.created_date || Date.now())
  
  return (
    <Card 
      className={`w-full transition-all duration-200 ${onClick ? 'cursor-pointer hover:shadow-md' : ''}`}
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <FileText className="w-4 h-4 text-primary" />
            </div>
            <div>
              {index !== undefined && (
                <CardTitle className="text-sm font-semibold text-muted-foreground">
                  Case {index}
                </CardTitle>
              )}
              <p className="text-xs font-mono text-muted-foreground mt-0.5">
                {caseData.case_id}
              </p>
            </div>
          </div>
          
          <Badge 
            variant="outline" 
            className={getStatusColor(status)}
          >
            {status.replace(/_/g, ' ')}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-3">
        {/* Transaction Info */}
        {caseData.transaction_id && (
          <div className="flex items-center gap-2 text-sm">
            <AlertCircle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <span className="text-muted-foreground">Transaction:</span>
            <span className="font-medium font-mono">
              {caseData.transaction_id}
            </span>
          </div>
        )}

        {/* Customer ID */}
        {showCustomerId && caseData.customer_id && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Customer:</span>
            <span className="font-medium font-mono">
              {caseData.customer_id}
            </span>
          </div>
        )}

        {/* Amount */}
        <div className="flex items-center gap-2 text-sm">
          <DollarSign className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          <span className="text-muted-foreground">Amount:</span>
          <span className="font-semibold">
            USD ${amount.toFixed(2)}
          </span>
        </div>

        {/* Credit Type & Amount */}
        {caseData.credit_type && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Credit:</span>
            <Badge 
              variant="outline" 
              className={getCreditTypeColor(caseData.credit_type)}
            >
              {caseData.credit_type}
            </Badge>
            {caseData.credit_amount !== undefined && (
              <span className="font-medium">
                ${Number(caseData.credit_amount).toFixed(2)}
              </span>
            )}
          </div>
        )}

        {/* Reason */}
        {(caseData.decision_reason || caseData.description) && (
          <div className="text-sm">
            <span className="text-muted-foreground">Reason: </span>
            <span className="text-foreground">
              {caseData.decision_reason || caseData.description}
            </span>
          </div>
        )}

        {/* Created Date */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t">
          <Calendar className="w-3 h-3" />
          <span>Created: {createdAt.toLocaleString()}</span>
        </div>

        {/* Download Documents Button */}
        {caseData.documents && caseData.documents.length > 0 && (
          <div className="pt-2">
            <Button
              onClick={handleDownloadDocuments}
              disabled={isDownloading}
              variant="outline"
              size="sm"
              className="w-full"
            >
              <Download className="w-4 h-4 mr-2" />
              {isDownloading 
                ? 'Downloading...' 
                : `Download Documents (${caseData.documents.length})`
              }
            </Button>
            {downloadError && (
              <p className="text-xs text-red-500 mt-1">{downloadError}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
