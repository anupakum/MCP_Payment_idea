'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { apiClient } from './api-client'

// Types for our log system
export interface ToolStep {
  name: string
  status: 'pending' | 'active' | 'completed' | 'error'
  description: string
  timestamp?: string
}

export interface AgentStep {
  name: string
  status: 'pending' | 'active' | 'completed' | 'error'
  description?: string
  timestamp?: string
  tools?: ToolStep[]
}

export interface LogEntry {
  id: string
  timestamp: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  agent?: string
}

export interface DetailedLogEntry {
  id: string
  timestamp: string
  agent: string
  action: string
  details: string
  duration?: string
  expanded?: boolean
}

interface LogContextType {
  // Agent Flow
  agentSteps: AgentStep[]
  updateAgentStep: (stepName: string, status: AgentStep['status']) => void
  updateToolStep: (agentName: string, toolName: string, status: ToolStep['status']) => void
  resetAgentFlow: () => void
  
  // Live Logs
  liveLogs: LogEntry[]
  addLiveLog: (log: Omit<LogEntry, 'id'>) => void
  clearLiveLogs: () => void
  
  // Detailed Logs
  detailedLogs: DetailedLogEntry[]
  addDetailedLog: (log: Omit<DetailedLogEntry, 'id' | 'expanded'>) => void
  clearDetailedLogs: () => void
  
  // Processing state
  isProcessing: boolean
  setIsProcessing: (processing: boolean) => void
}

const LogContext = createContext<LogContextType | undefined>(undefined)

const INITIAL_AGENT_STEPS: AgentStep[] = [
  { 
    name: 'Manager Agent', 
    status: 'pending',
    description: 'Intelligent orchestrator - analyzes request and routes to specialized agents',
    tools: [
      { name: 'request_analysis', status: 'pending', description: 'Parse and classify user request' },
      { name: 'intent_detection', status: 'pending', description: 'Detect customer/card/transaction/case intent' },
      { name: 'agent_routing', status: 'pending', description: 'Route to appropriate specialized agent' }
    ]
  },
  { 
    name: 'Verification Agent', 
    status: 'pending',
    description: 'Verifies customer identity and validates transaction data (delegated by Manager)',
    tools: [
      { name: 'customer_lookup', status: 'pending', description: 'Look up customer by ID' },
      { name: 'card_lookup', status: 'pending', description: 'Verify card ownership' },
      { name: 'transaction_lookup', status: 'pending', description: 'Retrieve transaction details' },
      { name: 'dynamo_query_creator', status: 'pending', description: 'Custom DynamoDB queries' }
    ]
  },
  { 
    name: 'Decision Agent', 
    status: 'pending',
    description: 'Applies business rules and creates dispute cases (delegated by Manager)',
    tools: [
      { name: 'dispute_case_creation', status: 'pending', description: 'Create and persist cases' },
      { name: 'business_rules_engine', status: 'pending', description: 'Apply time-barred and amount rules' },
      { name: 'dynamo_query_creator', status: 'pending', description: 'Query historical disputes' }
    ]
  },
  { 
    name: 'Case Query Agent', 
    status: 'pending',
    description: 'Retrieves and analyzes dispute case information (delegated by Manager)',
    tools: [
      { name: 'case_lookup', status: 'pending', description: 'Look up case by case ID' },
      { name: 'customer_cases_lookup', status: 'pending', description: 'Retrieve all cases for customer' },
      { name: 'dynamo_query_tool', status: 'pending', description: 'Custom case queries' }
    ]
  }
]

const MAX_LIVE_LOGS = 50
const MAX_DETAILED_LOGS = 20

export function LogProvider({ children }: { children: React.ReactNode }) {
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>(INITIAL_AGENT_STEPS)
  const [liveLogs, setLiveLogs] = useState<LogEntry[]>([])
  const [detailedLogs, setDetailedLogs] = useState<DetailedLogEntry[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

  const updateAgentStep = useCallback((stepName: string, status: AgentStep['status']) => {
    setAgentSteps(prev => prev.map(step => 
      step.name === stepName 
        ? { ...step, status, timestamp: new Date().toISOString() }
        : step
    ))
  }, [])

  const updateToolStep = useCallback((agentName: string, toolName: string, status: ToolStep['status']) => {
    setAgentSteps(prev => prev.map(step => {
      if (step.name === agentName && step.tools) {
        return {
          ...step,
          tools: step.tools.map(tool =>
            tool.name === toolName
              ? { ...tool, status, timestamp: new Date().toISOString() }
              : tool
          )
        }
      }
      return step
    }))
  }, [])

  const resetAgentFlow = useCallback(() => {
    setAgentSteps(INITIAL_AGENT_STEPS)
  }, [])

  const addLiveLog = useCallback((log: Omit<LogEntry, 'id'>) => {
    const newLog: LogEntry = {
      ...log,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }
    setLiveLogs(prev => {
      const updated = [...prev, newLog]
      // Keep only the last MAX_LIVE_LOGS entries
      return updated.slice(-MAX_LIVE_LOGS)
    })
  }, [])

  const clearLiveLogs = useCallback(() => {
    setLiveLogs([])
  }, [])

  const addDetailedLog = useCallback((log: Omit<DetailedLogEntry, 'id' | 'expanded'>) => {
    const newLog: DetailedLogEntry = {
      ...log,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      expanded: false
    }
    setDetailedLogs(prev => {
      const updated = [...prev, newLog]
      // Keep only the last MAX_DETAILED_LOGS entries
      return updated.slice(-MAX_DETAILED_LOGS)
    })
  }, [])

  const clearDetailedLogs = useCallback(() => {
    setDetailedLogs([])
  }, [])

  // Initialize with a welcome message
  useEffect(() => {
    addLiveLog({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: 'System ready. Waiting for dispute submission...'
    })
    
    addDetailedLog({
      timestamp: new Date().toISOString(),
      agent: 'System',
      action: 'Initialized',
      details: 'CrewAI dispute resolution system ready',
      duration: '0ms'
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Poll backend logs every 2 seconds when processing
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null

    const fetchLogs = async () => {
      try {
        // Fetch live logs
        const liveResponse = await apiClient.getLiveLogs(50)
        if (liveResponse.success && liveResponse.data?.logs) {
          // Replace logs with backend logs (backend is source of truth)
          setLiveLogs(liveResponse.data.logs.map(log => ({
            id: log.id,
            timestamp: log.timestamp,
            level: log.level as 'info' | 'success' | 'warning' | 'error',
            message: log.message,
            agent: log.agent
          })))
        }

        // Fetch detailed logs
        const detailedResponse = await apiClient.getDetailedLogs(20)
        if (detailedResponse.success && detailedResponse.data?.logs) {
          setDetailedLogs(detailedResponse.data.logs.map(log => ({
            id: log.id,
            timestamp: log.timestamp,
            agent: log.agent,
            action: log.action,
            details: log.details,
            duration: log.duration,
            expanded: false
          })))
        }
      } catch (error) {
        console.error('Error fetching logs from backend:', error)
      }
    }

    // Start polling when processing
    if (isProcessing) {
      fetchLogs() // Fetch immediately
      intervalId = setInterval(fetchLogs, 2000) // Then every 2 seconds
    }

    // Cleanup
    return () => {
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [isProcessing])

  const value: LogContextType = {
    agentSteps,
    updateAgentStep,
    updateToolStep,
    resetAgentFlow,
    liveLogs,
    addLiveLog,
    clearLiveLogs,
    detailedLogs,
    addDetailedLog,
    clearDetailedLogs,
    isProcessing,
    setIsProcessing
  }

  return <LogContext.Provider value={value}>{children}</LogContext.Provider>
}

export function useLog() {
  const context = useContext(LogContext)
  if (context === undefined) {
    throw new Error('useLog must be used within a LogProvider')
  }
  return context
}
