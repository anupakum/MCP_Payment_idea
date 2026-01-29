// File: `web/components/ChatWindow.tsx`
'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { CardItem } from './CardItem'
import { TransactionTable } from './TransactionTable'
import { CaseCard, type CaseData } from './CaseCard'
import { apiClient, type CustomerData, type TransactionData, type DisputeCaseData } from '@/lib/api-client'
import { formatCurrency, getStatusText, getStatusColorClasses } from '@/lib/utils'
import { Send, User, Bot, CreditCard, Receipt, AlertCircle, CheckCircle, XCircle, Clock, Upload, X, FileText } from 'lucide-react'
import { useLog } from '@/lib/log-context'
import { maskCustomerId, maskCardNumber, maskTransactionId, maskAmount, maskEmail, maskName, formatTraceData } from '@/lib/mask-utils'

export interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  data?: any
}

export interface ChatWindowProps {
  className?: string
}

export function ChatWindow({ className }: ChatWindowProps) {
  const {
    updateAgentStep,
    updateToolStep,
    resetAgentFlow,
    addLiveLog,
    addDetailedLog,
    setIsProcessing,
    clearLiveLogs,
    clearDetailedLogs
  } = useLog()

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! I\'m here to help you with your dispute resolution.\n\nYou can:\n• Provide your Customer ID to start a new dispute\n• Type "case status" followed by your Case ID to check an existing case\n• Type "my cases" followed by your Customer ID to see all your cases',
      timestamp: new Date(),
    }
  ])

  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState<'customer' | 'card' | 'transaction' | 'reason' | 'upload' | 'complete'>('customer')
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('')
  const [selectedCardId, setSelectedCardId] = useState<string>('')
  const [selectedTransactionId, setSelectedTransactionId] = useState<string>('')
  const [selectedReasonCode, setSelectedReasonCode] = useState<string>('')
  const [pendingCaseId, setPendingCaseId] = useState<string>('')
  const [pendingCaseStatus, setPendingCaseStatus] = useState<string>('')
  const [customerCards, setCustomerCards] = useState<CustomerData['cards']>([])
  const [cardTransactions, setCardTransactions] = useState<TransactionData[]>([])
  const [displayedCases, setDisplayedCases] = useState<CaseData[]>([])
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, newMessage])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return

    const userMessage = inputValue.trim()
    setInputValue('')

    addMessage({
      type: 'user',
      content: userMessage,
    })

    setIsLoading(true)

    try {
      await handleUserInput(userMessage)
    } catch (error) {
      addMessage({
        type: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Something went wrong'}`,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleUserInput = async (input: string) => {
    if (input.toLowerCase().startsWith('case status')) {
      const caseId = input.substring('case status'.length).trim()
      if (caseId) {
        await handleCaseStatusQuery(caseId)
      } else {
        addMessage({
          type: 'assistant',
          content: 'Please provide a Case ID. Example: "case status abc123"',
        })
      }
      return
    }

    if (input.toLowerCase().startsWith('my cases')) {
      const customerId = input.substring('my cases'.length).trim()
      if (customerId) {
        await handleCustomerCasesQuery(customerId)
      } else {
        addMessage({
          type: 'assistant',
          content: 'Please provide your Customer ID. Example: "my cases CUST001"',
        })
      }
      return
    }

    switch (currentStep) {
      case 'customer':
        await handleCustomerVerification(input)
        break
      case 'card':
        break
      case 'transaction':
        break
      case 'reason':
        break
      default:
        addMessage({
          type: 'assistant',
          content: 'Your dispute has been processed. You can start a new dispute by providing a new Customer ID, or check case status.',
        })
        resetToStart()
    }
  }

  const handleCaseStatusQuery = async (caseId: string) => {
    return handleManagerAgentRequest(
      `Check the status of case ${caseId}`,
      { caseId },
      'case'
    )
  }

  const handleCustomerCasesQuery = async (customerId: string) => {
    return handleManagerAgentRequest(
      `Show all dispute cases for customer ${customerId}`,
      { customerId },
      'case'
    )
  }

  const handleManagerAgentRequest = async (
    request: string,
    context: {
      customerId?: string
      cardNumber?: string
      transactionId?: string
      caseId?: string
      reasonCode?: string
    },
    expectedStep?: 'customer' | 'card' | 'transaction' | 'case'
  ) => {
    const startTime = Date.now()

    setIsLoading(true)
    setIsProcessing(true)

    let delegatedAgent = 'Auto-detected'
    let delegatedAgentName = ''

    if (expectedStep === 'customer' || expectedStep === 'card' || expectedStep === 'transaction') {
      delegatedAgent = 'Verification Agent'
      delegatedAgentName = 'Verification Agent'
    } else if (expectedStep === 'case') {
      delegatedAgent = 'Case Query Agent'
      delegatedAgentName = 'Case Query Agent'
    }

    updateAgentStep('Manager Agent', 'active')
    updateToolStep('Manager Agent', 'request_analysis', 'active')

    addLiveLog({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: `🎯 Manager Agent activated - Analyzing request`,
      agent: 'Manager Agent'
    })

    addDetailedLog({
      timestamp: new Date().toISOString(),
      agent: 'Manager Agent',
      action: 'Request Analysis',
      details: formatTraceData({
        'Input': {
          'Request': request,
          'Context': context,
          'Expected Step': expectedStep || 'auto-detect'
        },
        'Process': 'Hierarchical delegation to specialized agents',
        'API Call': {
          'Endpoint': '/process',
          'Method': 'POST',
          'Status': 'Executing...'
        }
      }),
      duration: '0ms'
    })

    updateToolStep('Manager Agent', 'request_analysis', 'completed')
    updateToolStep('Manager Agent', 'intent_detection', 'active')

    try {
      const response = await apiClient.processRequest(request, context)
      const duration = Date.now() - startTime

      if (response.success && response.data) {
        updateToolStep('Manager Agent', 'intent_detection', 'completed')
        updateToolStep('Manager Agent', 'agent_routing', 'completed')
        updateAgentStep('Manager Agent', 'completed')

        if (delegatedAgentName) {
          updateAgentStep(delegatedAgentName, 'active')
        }

        addLiveLog({
          timestamp: new Date().toISOString(),
          level: 'success',
          message: `✅ Manager Agent completed - Delegated to ${delegatedAgent} in ${duration}ms`,
          agent: 'Manager Agent'
        })

        addDetailedLog({
          timestamp: new Date().toISOString(),
          agent: 'Manager Agent',
          action: 'Delegation Complete',
          details: formatTraceData({
            'ResponseSummary': {
              'Success': true,
              'DurationMs': duration,
              'DelegatedAgent': delegatedAgentName || delegatedAgent
            },
            'ResponseDataKeys': Object.keys(response.data || {})
          }),
          duration: `${duration}ms`
        })

        const result = response.data.result || response.data

        if (expectedStep === 'customer' && result) {
          const cards = result.cards || result.data?.cards || []
          updateToolStep('Verification Agent', 'customer_lookup', 'completed')
          updateAgentStep('Verification Agent', 'completed')

          addLiveLog({
            timestamp: new Date().toISOString(),
            level: 'success',
            message: `✅ Verification Agent completed - Found ${cards.length} card(s) for customer`,
            agent: 'Verification Agent'
          })

          setSelectedCustomerId(context.customerId || '')
          setCustomerCards(cards)
          setCurrentStep('card')

          addMessage({
            type: 'assistant',
            content: `Found ${cards.length} card(s) for customer ${maskCustomerId(context.customerId || '')}. Please select a card.`,
            data: { cards }
          })
          return
        }

        if (expectedStep === 'card' && result) {
          const transactions = result.transactions || result.data?.transactions || []
          updateToolStep('Verification Agent', 'card_lookup', 'completed')
          updateAgentStep('Verification Agent', 'completed')

          addLiveLog({
            timestamp: new Date().toISOString(),
            level: 'success',
            message: `✅ Verification Agent completed - Retrieved ${transactions.length} transaction(s) for card`,
            agent: 'Verification Agent'
          })

          setSelectedCardId(context.cardNumber || '')
          setCardTransactions(transactions)
          setCurrentStep('transaction')

          addMessage({
            type: 'assistant',
            content: `Found ${transactions.length} transaction(s). Please select one to dispute.`,
            data: { transactions }
          })
          return
        }

        if (expectedStep === 'transaction' && result) {
          const disputeCase = result.dispute_case || result.case || result
          const transaction = result.transaction || {}

          const caseId = disputeCase?.case_id || ''
          const caseStatus = (disputeCase?.dispute_status || disputeCase?.status || '') as string

          setPendingCaseId(caseId)
          setPendingCaseStatus(caseStatus)
          setDisplayedCases(disputeCase ? [disputeCase] : [])
          updateToolStep('Verification Agent', 'transaction_lookup', 'completed')
          updateAgentStep('Verification Agent', 'completed')
          updateToolStep('Decision Agent', 'business_rules_engine', 'active')
          updateToolStep('Decision Agent', 'business_rules_engine', 'completed')
          updateToolStep('Decision Agent', 'dispute_case_creation', 'completed')
          updateAgentStep('Decision Agent', 'completed')

          addLiveLog({
            timestamp: new Date().toISOString(),
            level: 'success',
            message: `✅ Decision Agent completed - Created case ${caseId}`,
            agent: 'Decision Agent'
          })

          addMessage({
            type: 'assistant',
            content: `Dispute filed. Case ID: ${caseId} — Status: ${caseStatus || 'UNKNOWN'}`,
            data: { case: disputeCase }
          })
          return
        }

        if (expectedStep === 'case' && result) {
          updateAgentStep('Case Query Agent', 'completed')
          updateToolStep('Case Query Agent', 'customer_cases_lookup', 'completed')

          if (result.cases && Array.isArray(result.cases)) {
            setDisplayedCases(result.cases)
            addMessage({
              type: 'assistant',
              content: `Found ${result.cases.length} case(s) for the customer.`,
              data: { cases: result.cases }
            })
          } else if (result.case) {
            setDisplayedCases([result.case])
            addMessage({
              type: 'assistant',
              content: `Case retrieved: ${result.case.case_id}`,
              data: { case: result.case }
            })
          } else {
            addMessage({
              type: 'assistant',
              content: `No case data returned.`,
            })
          }
          return
        }

        if (delegatedAgentName) {
          updateAgentStep(delegatedAgentName, 'completed')
          addLiveLog({
            timestamp: new Date().toISOString(),
            level: 'info',
            message: `Delegated agent ${delegatedAgentName} completed.`,
            agent: delegatedAgentName
          })
        }

        addMessage({
          type: 'assistant',
          content: `Request processed successfully by Manager Agent.\n\n${JSON.stringify(response.data, null, 2)}`,
          data: response.data
        })
      } else {
        updateAgentStep('Manager Agent', 'error')
        if (delegatedAgentName) {
          updateAgentStep(delegatedAgentName, 'error')
        }

        addLiveLog({
          timestamp: new Date().toISOString(),
          level: 'error',
          message: `❌ Manager Agent failed - ${response.error || 'Unknown error'}`,
          agent: 'Manager Agent'
        })

        addMessage({
          type: 'system',
          content: `Manager Agent error: ${response.error || response.message || 'Request failed'}`,
        })
      }
    } catch (error) {
      const duration = Date.now() - startTime
      updateAgentStep('Manager Agent', 'error')
      if (delegatedAgentName) {
        updateAgentStep(delegatedAgentName, 'error')
      }

      addLiveLog({
        timestamp: new Date().toISOString(),
        level: 'error',
        message: `❌ Manager Agent exception - ${error instanceof Error ? error.message : 'Unknown error'}`,
        agent: 'Manager Agent'
      })

      addDetailedLog({
        timestamp: new Date().toISOString(),
        agent: 'Manager Agent',
        action: 'Error',
        details: formatTraceData({
          'Error': {
            'Message': error instanceof Error ? error.message : 'Unknown error',
            'DurationMs': duration,
            'DelegatedAgent': delegatedAgentName || 'Not yet determined'
          }
        }),
        duration: `${duration}ms`
      })

      addMessage({
        type: 'system',
        content: `Failed to process request: ${error instanceof Error ? error.message : 'Unknown error'}`,
      })
    } finally {
      setIsLoading(false)
      setIsProcessing(false)
    }
  }

  const handleCustomerVerification = async (customerId: string) => {
    return handleManagerAgentRequest(
      `Verify customer ${customerId} and show their cards`,
      { customerId },
      'customer'
    )
  }

  const handleCardSelection = async (cardNumber: string) => {
    if (!selectedCustomerId) return

    return handleManagerAgentRequest(
      `Verify card ${cardNumber} for customer ${selectedCustomerId} and show transactions`,
      {
        customerId: selectedCustomerId,
        cardNumber
      },
      'card'
    )
  }

  const REASON_CODES_BY_CARD_TYPE: Record<string, { code: string; label: string }[]> = {
    visa: [
      { code: '11.3', label: 'Unauthorized Charge - Unknown' },
      { code: '11.2', label: 'Unauthorized Charge - Transaction Declined' },
      { code: '10.1', label: 'Unauthorized Charge Fraud' },
    ],
    mastercard: [
      { code: '4808', label: 'Unauthorized Charge' },
      { code: '4863', label: 'Unauthorized Fraud Charge' },
      { code: '4860', label: 'Credit Not Processed' },
    ],
    amex: [
      { code: 'AMX_UNAUTH', label: 'Unauthorized transaction' },
      { code: 'AMX_GOODS', label: 'Goods not as described' },
    ],
    discover: [
      { code: 'AT', label: 'Unauthorized Charge' },
      { code: 'UA01', label: 'Unauthorize Fraud Charge' },
      { code: 'DP', label: 'Duplicate Transaction' },
    ],
    unknown: [
      { code: 'RC_OTHER', label: 'Other / Not listed' }
    ]
  }

  const handleTransactionSelection = async (transactionId: string) => {
    if (!selectedCustomerId || !selectedCardId) return

    setSelectedTransactionId(transactionId)

    const card = customerCards.find(c => c.card_number === selectedCardId)
    const rawType = (card && (card.card_type || card.type || card.brand)) || 'unknown'
    const cardType = String(rawType).toLowerCase()

    const reasonCodes = REASON_CODES_BY_CARD_TYPE[cardType] || REASON_CODES_BY_CARD_TYPE['unknown']

    setCurrentStep('reason')

    addMessage({
      type: 'assistant',
      content: `Please select a reason code for the dispute (based on card type: ${cardType.toUpperCase()}).`,
      data: {
        reasonCodes,
        cardType,
        transactionId
      }
    })
  }

  const handleReasonSelection = async (reasonCode: string) => {
    if (!selectedCustomerId || !selectedCardId || !selectedTransactionId) {
      addMessage({
        type: 'system',
        content: 'Missing context to file dispute. Please start again.',
      })
      return
    }

    setSelectedReasonCode(reasonCode)
    setIsLoading(true)

    try {
      await handleManagerAgentRequest(
        `File dispute for transaction ${selectedTransactionId} with reason ${reasonCode}`,
        {
          customerId: selectedCustomerId,
          cardNumber: selectedCardId,
          transactionId: selectedTransactionId,
          reasonCode
        },
        'transaction'
      )

      // Use updated pendingCaseStatus (may have been set by manager agent)
      const isRejected = String(pendingCaseStatus || '').toUpperCase().includes('REJECTED')

      if (isRejected) {
        setCurrentStep('complete')
        addMessage({
          type: 'assistant',
          content: 'Your dispute has been completed. Document upload is not available for rejected cases.',
        })
      } else {
        setCurrentStep('upload')
        addMessage({
          type: 'assistant',
          content: 'Dispute filed successfully! Would you like to upload any supporting documents? (Optional - you can skip this step)',
        })
      }
    } catch (error) {
      addMessage({
        type: 'system',
        content: `Failed to file dispute with reason ${reasonCode}: ${error instanceof Error ? error.message : 'Unknown error'}`,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files) {
      const newFiles = Array.from(files)
      setSelectedFiles(prev => [...prev, ...newFiles])
    }
  }

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUploadDocuments = async () => {
    if (!pendingCaseId) {
      addMessage({
        type: 'system',
        content: 'Error: No case ID found for document upload',
      })
      return
    }

    if (selectedFiles.length === 0) {
      addMessage({
        type: 'system',
        content: 'Please select at least one document to upload',
      })
      return
    }

    setIsUploading(true)

    try {
      addMessage({
        type: 'assistant',
        content: `Uploading ${selectedFiles.length} document(s)...`,
      })

      const response = await apiClient.uploadCaseDocuments(pendingCaseId, selectedFiles)

      console.log('Upload response:', response)
      console.log('Response success:', response.success)
      console.log('Response data:', response.data)

      if (response.success && response.data) {
        const updatedCase = displayedCases.length > 0
          ? {
              ...displayedCases[0],
              documents: response.data.uploaded_documents || []
            }
          : null

        if (updatedCase) {
          setDisplayedCases([updatedCase])

          addMessage({
            type: 'assistant',
            content: `✅ Successfully uploaded ${response.data.total_documents} document(s) to case ${pendingCaseId}`,
            data: { case: updatedCase }
          })
        } else {
          addMessage({
            type: 'assistant',
            content: `✅ Successfully uploaded ${response.data.total_documents} document(s) to case ${pendingCaseId}`,
          })
        }

        setSelectedFiles([])
        setCurrentStep('complete')
      } else {
        addMessage({
          type: 'system',
          content: `Failed to upload documents: ${response.error || response.message || 'Unknown error'}`,
        })
      }
    } catch (error) {
      addMessage({
        type: 'system',
        content: `Error uploading documents: ${error instanceof Error ? error.message : 'Unknown error'}`,
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleSkipUpload = () => {
    setCurrentStep('complete')
    addMessage({
      type: 'assistant',
      content: 'No documents uploaded. Your dispute case has been filed successfully!',
    })
  }

  const resetToStart = () => {
    setCurrentStep('customer')
    setSelectedCustomerId('')
    setSelectedCardId('')
    setSelectedTransactionId('')
    setSelectedReasonCode('')
    setPendingCaseId('')
    setPendingCaseStatus('')
    setSelectedFiles([])
    setCustomerCards([])
    setCardTransactions([])
    setDisplayedCases([])
    resetAgentFlow()
    setIsProcessing(false)

    clearLiveLogs()
    clearDetailedLogs()

    setMessages([
      {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'Hello! I\'m here to help you with your dispute resolution. Please provide your Customer ID to get started.',
        timestamp: new Date(),
      }
    ])

    addLiveLog({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: 'Ready for new dispute submission',
    })

    addDetailedLog({
      timestamp: new Date().toISOString(),
      agent: 'System',
      action: 'Reset',
      details: 'Chat and logs cleared. Ready for new dispute.',
      duration: '0ms'
    })
  }

  const getStatusIcon = (status?: string) => {
    const upperStatus = status?.toUpperCase()
    switch (upperStatus) {
      case 'RESOLVED_CUSTOMER':
      case 'APPROVED':
      case 'CLOSED':
        return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'REJECTED_TIME_BARRED':
      case 'REJECTED':
        return <XCircle className="w-4 h-4 text-red-600" />
      case 'FORWARDED_TO_ACQUIRER':
      case 'IN_PROGRESS':
      case 'PENDING':
        return <Clock className="w-4 h-4 text-yellow-600" />
      case 'OPEN':
        return <AlertCircle className="w-4 h-4 text-blue-600" />
      default:
        return <AlertCircle className="w-4 h-4 text-gray-600" />
    }
  }

  const renderMessageContent = (message: ChatMessage) => {
    if (message.type === 'assistant' && message.data && currentStep === 'card') {
      return (
        <div className="space-y-3">
          <p>{message.content}</p>
          <div className="grid gap-2">
            {customerCards.map((card) => (
              <CardItem
                key={card.card_number}
                card={card}
                onClick={() => {
                  // set selected card id locally so card type detection works
                  setSelectedCardId(card.card_number)
                  handleCardSelection(card.card_number)
                }}
                disabled={isLoading}
              />
            ))}
          </div>
        </div>
      )
    }

    if (message.type === 'assistant' && message.data && currentStep === 'transaction') {
      return (
        <div className="space-y-3">
          <p>{message.content}</p>
          <TransactionTable
            transactions={cardTransactions}
            onTransactionSelect={handleTransactionSelection}
            disabled={isLoading}
          />
        </div>
      )
    }

    if (message.type === 'assistant' && message.data && currentStep === 'reason') {
      const reasonCodes = message.data.reasonCodes || []
      return (
        <div className="space-y-3">
          <p>{message.content}</p>
          <div className="grid gap-2 mt-2">
            {reasonCodes.map((r: { code: string; label: string }) => (
              <Button
                key={r.code}
                onClick={() => handleReasonSelection(r.code)}
                disabled={isLoading}
                className="justify-start"
              >
                <div className="flex items-center gap-3 w-full">
                  <span className="font-medium">{r.label}</span>
                  <span className="text-xs text-muted-foreground ml-auto">{r.code}</span>
                </div>
              </Button>
            ))}
          </div>
        </div>
      )
    }

    if (message.type === 'assistant' && message.data) {
      const cases = message.data.cases || message.data.result?.cases || message.data.data?.cases
      const singleCase = message.data.case || message.data.result?.case || message.data.data?.case
      const isCaseArray = Array.isArray(message.data) && message.data.length > 0 && message.data[0]?.case_id

      if (cases || singleCase || isCaseArray) {
        const casesToShow = cases || (isCaseArray ? message.data : (singleCase ? [singleCase] : []))

        if (casesToShow.length > 0 && casesToShow[0]?.case_id) {
          return (
            <div className="space-y-3">
              <p>{message.content}</p>
              <div className="grid gap-3 mt-4">
                {casesToShow.map((caseData: CaseData) => (
                  <CaseCard
                    key={caseData.case_id}
                    caseData={caseData}
                  />
                ))}
              </div>
            </div>
          )
        }
      }
    }

    if (message.type === 'system' && message.content.includes('Case ID:')) {
      const lines = message.content.split('\n')
      return (
        <div className="bg-muted p-4 rounded-lg space-y-2">
          {lines.map((line, index) => {
            if (line.startsWith('Case ID:')) {
              return <p key={index} className="font-mono text-sm font-semibold">{line}</p>
            }
            if (line.startsWith('Status:')) {
              return <p key={index} className="font-medium">{line}</p>
            }
            return <p key={index} className="text-sm">{line}</p>
          })}
        </div>
      )
    }

    return <p className="whitespace-pre-wrap">{message.content}</p>
  }

  const getMessageIcon = (type: ChatMessage['type']) => {
    switch (type) {
      case 'user':
        return <User className="w-4 h-4" />
      case 'assistant':
        return <Bot className="w-4 h-4" />
      case 'system':
        return <AlertCircle className="w-4 h-4" />
      default:
        return null
    }
  }

  const getPlaceholderText = () => {
    switch (currentStep) {
      case 'customer':
        return 'Enter your Customer ID...'
      case 'card':
        return 'Click on a card above to select it...'
      case 'transaction':
        return 'Click on a transaction above to dispute it...'
      case 'reason':
        return 'Select a reason code from the options above...'
      default:
        return 'Enter a new Customer ID to start again...'
    }
  }

  return (
    <Card className={`chat-window ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Receipt className="w-5 h-5" />
            Dispute Resolution Chat
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col p-0" style={{ height: 'calc(600px - 73px)' }}>
        <div ref={messagesContainerRef} className="chat-messages flex-1 overflow-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex items-start gap-3 ${message.type === 'user' ? 'flex-row-reverse' : ''}`}
            >
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                message.type === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : message.type === 'system'
                  ? 'bg-muted text-muted-foreground'
                  : 'bg-secondary text-secondary-foreground'
              }`}>
                {getMessageIcon(message.type)}
              </div>

              <div className={`flex-1 max-w-[80%] ${message.type === 'user' ? 'message-user' : 'message-assistant'}`}>
                {renderMessageContent(message)}
                <div className="text-xs text-muted-foreground mt-2 opacity-70" suppressHydrationWarning>
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary text-secondary-foreground flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div className="flex-1 max-w-[80%] message-assistant">
                <div className="flex items-center gap-2">
                  <div className="loading-pulse w-2 h-2 rounded-full bg-muted-foreground"></div>
                  <div className="loading-pulse w-2 h-2 rounded-full bg-muted-foreground animation-delay-150"></div>
                  <div className="loading-pulse w-2 h-2 rounded-full bg-muted-foreground animation-delay-300"></div>
                  <span className="text-sm text-muted-foreground ml-2">Processing...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="border-t p-4 flex-shrink-0 bg-background">
          {currentStep === 'upload' && (
            <div className="mb-4 p-4 border rounded-lg bg-muted/50">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Upload className="w-4 h-4" />
                Upload Supporting Documents (Optional)
              </h3>

              <div className="mb-3">
                <label htmlFor="document-upload" className="cursor-pointer">
                  <div className="border-2 border-dashed rounded-lg p-4 text-center hover:bg-muted/70 transition-colors">
                    <FileText className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      Click to select files or drag and drop
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Multiple files allowed (PDF, JPG, PNG, etc.)
                    </p>
                  </div>
                  <input
                    id="document-upload"
                    type="file"
                    multiple
                    onChange={handleFileSelect}
                    className="hidden"
                    accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.txt"
                  />
                </label>
              </div>

              {selectedFiles.length > 0 && (
                <div className="mb-3 space-y-2">
                  <p className="text-sm font-medium">Selected files ({selectedFiles.length}):</p>
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-background rounded border">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <FileText className="w-5 h-5 text-muted-foreground" />
                        <div className="min-w-0">
                          <p className="text-sm truncate">{file.name}</p>
                          <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveFile(index)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  onClick={handleUploadDocuments}
                  disabled={selectedFiles.length === 0 || isUploading}
                  className="flex-1"
                >
                  {isUploading ? (
                    <span>Uploading...</span>
                  ) : (
                    <span>Upload Documents</span>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleSkipUpload}
                  disabled={isUploading}
                  className="flex-1"
                >
                  Skip
                </Button>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={getPlaceholderText()}
              disabled={isLoading || currentStep === 'card' || currentStep === 'transaction' || currentStep === 'reason' || currentStep === 'upload'}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={!inputValue.trim() || isLoading || currentStep === 'card' || currentStep === 'transaction' || currentStep === 'reason' || currentStep === 'upload'}
              size="icon"
            >
              <Send className="w-4 h-4" />
            </Button>
          </form>

          {currentStep !== 'customer' && currentStep !== 'upload' && (
            <Button
              variant="outline"
              size="sm"
              className="mt-2 w-full"
              onClick={resetToStart}
              disabled={isLoading}
            >
              Start New Dispute
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
