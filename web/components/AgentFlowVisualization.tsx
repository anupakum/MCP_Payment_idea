    'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, Clock, AlertCircle, Activity, Database, Brain, FileCheck, Sparkles, LayoutList, CircleDot, LayoutGrid, ArrowRight, Columns, ChevronDown, ChevronRight, Wrench, Search } from 'lucide-react'
import { useLog, type AgentStep } from '@/lib/log-context'
import { useState, useEffect } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

type ViewMode = 'timeline' | 'circle' | 'grid' | 'horizontal' | 'kanban'

export function AgentFlowVisualization() {
  const { agentSteps: steps } = useLog()
  const [startTime, setStartTime] = useState<Date | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('timeline')
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set())

  // Track processing start time
  useEffect(() => {
    const hasActive = steps.some(s => s.status === 'active' || s.status === 'completed')
    if (hasActive && !startTime) {
      setStartTime(new Date())
    } else if (!hasActive) {
      setStartTime(null)
    }
  }, [steps, startTime])

  const toggleAgentExpansion = (agentName: string) => {
    setExpandedAgents(prev => {
      const newSet = new Set(prev)
      if (newSet.has(agentName)) {
        newSet.delete(agentName)
      } else {
        newSet.add(agentName)
      }
      return newSet
    })
  }

  const getAgentIcon = (stepName: string) => {
    if (stepName.includes('Manager')) return Brain  // Manager Agent uses Brain icon for orchestration
    if (stepName.includes('Verification')) return Activity
    if (stepName.includes('Data Retrieval')) return Database
    if (stepName.includes('Analysis')) return Search
    if (stepName.includes('Decision')) return FileCheck
    if (stepName.includes('Case Query')) return Search
    return Sparkles
  }

  const getStatusIcon = (status: AgentStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'active':
        return <Clock className="w-5 h-5 text-blue-500 animate-pulse" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30" />
    }
  }

  const getStatusColor = (status: AgentStep['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/10 border-green-500/20'
      case 'active':
        return 'bg-blue-500/10 border-blue-500/30 shadow-lg shadow-blue-500/20'
      case 'error':
        return 'bg-red-500/10 border-red-500/20'
      default:
        return 'bg-muted/30 border-muted-foreground/10'
    }
  }

  const calculateProgress = () => {
    const completed = steps.filter(s => s.status === 'completed').length
    return Math.round((completed / steps.length) * 100)
  }

  const getElapsedTime = (timestamp?: string) => {
    if (!timestamp) return null
    const elapsed = Date.now() - new Date(timestamp).getTime()
    const seconds = Math.floor(elapsed / 1000)
    if (seconds < 60) return `${seconds}s`
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  }

  const progress = calculateProgress()

  // Render different views based on selection
  const renderView = () => {
    switch (viewMode) {
      case 'timeline':
        return renderTimelineView()
      case 'circle':
        return renderCircleView()
      case 'grid':
        return renderGridView()
      case 'horizontal':
        return renderHorizontalView()
      case 'kanban':
        return renderKanbanView()
      default:
        return renderTimelineView()
    }
  }

  // Timeline View (Original Enhanced)
  const renderTimelineView = () => (
    <div className="relative">
      {/* Vertical Timeline Line */}
      <div className="absolute left-[22px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-muted-foreground/20 via-muted-foreground/10 to-transparent" />
      
      <div className="space-y-2">
        {steps.map((step, index) => {
          const Icon = getAgentIcon(step.name)
          const isLast = index === steps.length - 1
          const isExpanded = expandedAgents.has(step.name)
          const hasTools = step.tools && step.tools.length > 0
          
          return (
            <div key={index} className="relative">
              {/* Agent Card */}
              <div 
                className={`
                  relative flex items-start gap-3 p-3 rounded-lg border transition-all duration-300 cursor-pointer
                  ${getStatusColor(step.status)}
                  ${step.status === 'active' ? 'scale-[1.02]' : ''}
                  ${hasTools ? 'hover:shadow-md' : ''}
                `}
                onClick={() => hasTools && toggleAgentExpansion(step.name)}
              >
                <div className="relative flex-shrink-0">
                  <div className={`
                    absolute inset-0 rounded-full
                    ${step.status === 'active' ? 'animate-ping bg-blue-500/30' : ''}
                  `} />
                  <div className="relative p-2 rounded-full bg-background border shadow-sm">
                    {getStatusIcon(step.status)}
                  </div>
                </div>
                
                <div className="flex-1 min-w-0 pt-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Icon className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                        <p className={`text-sm font-medium truncate ${
                          step.status === 'active' ? 'text-primary font-semibold' : 
                          step.status === 'completed' ? 'text-foreground' : 
                          'text-muted-foreground'
                        }`}>
                          {step.name}
                        </p>
                      </div>
                      
                      {step.description && (
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                          {step.description}
                        </p>
                      )}
                      
                      <div className="flex items-center gap-2 mt-1">
                        {step.timestamp && (
                          <>
                            <p className="text-xs text-muted-foreground">
                              {new Date(step.timestamp).toLocaleTimeString()}
                            </p>
                            {step.status === 'completed' && (
                              <Badge variant="outline" className="text-[10px] h-4 px-1.5">
                                {getElapsedTime(step.timestamp)}
                              </Badge>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Badge 
                        variant={
                          step.status === 'completed' ? 'success' :
                          step.status === 'active' ? 'default' :
                          step.status === 'error' ? 'destructive' :
                          'outline'
                        }
                        className="text-[10px] h-5 px-2 flex-shrink-0"
                      >
                        {step.status === 'active' && '⚡ '}
                        {step.status.charAt(0).toUpperCase() + step.status.slice(1)}
                      </Badge>
                      {hasTools && (
                        isExpanded 
                          ? <ChevronDown className="w-4 h-4 text-muted-foreground" />
                          : <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Tools Section (Expandable) */}
              {hasTools && isExpanded && (
                <div className="ml-11 mt-1 space-y-1 border-l-2 border-muted-foreground/20 pl-4">
                  {step.tools!.map((tool, toolIndex) => (
                    <div 
                      key={toolIndex}
                      className={`
                        flex items-center gap-2 p-2 rounded-md text-xs transition-all
                        ${tool.status === 'active' ? 'bg-blue-500/10 border border-blue-500/20' : ''}
                        ${tool.status === 'completed' ? 'bg-green-500/5' : ''}
                        ${tool.status === 'error' ? 'bg-red-500/10 border border-red-500/20' : ''}
                        ${tool.status === 'pending' ? 'opacity-50' : ''}
                      `}
                    >
                      <div className="flex-shrink-0">
                        {tool.status === 'completed' && <CheckCircle2 className="w-3 h-3 text-green-500" />}
                        {tool.status === 'active' && <Clock className="w-3 h-3 text-blue-500 animate-pulse" />}
                        {tool.status === 'error' && <AlertCircle className="w-3 h-3 text-red-500" />}
                        {tool.status === 'pending' && <Wrench className="w-3 h-3 text-muted-foreground" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-foreground truncate">{tool.name}</p>
                        <p className="text-muted-foreground text-[10px] truncate">{tool.description}</p>
                      </div>
                      {tool.timestamp && (
                        <p className="text-[10px] text-muted-foreground flex-shrink-0">
                          {getElapsedTime(tool.timestamp)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {!isLast && (
                <div className="absolute left-[26px] bottom-[-8px] w-2 h-2 rounded-full bg-muted-foreground/20 z-10" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )

  // Circle/Radial View
  const renderCircleView = () => {
    const radius = 70
    const centerX = 100
    const centerY = 100
    const angleStep = (2 * Math.PI) / steps.length
    
    return (
      <div className="relative w-full aspect-square max-w-[280px] mx-auto">
        <svg viewBox="0 0 200 200" className="w-full h-full">
          {/* Background Circle */}
          <circle
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            className="text-muted-foreground/20"
          />
          
          {/* Progress Arc */}
          {progress > 0 && (
            <circle
              cx={centerX}
              cy={centerY}
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray={`${(progress / 100) * (2 * Math.PI * radius)} ${2 * Math.PI * radius}`}
              strokeLinecap="round"
              className={progress === 100 ? 'text-green-500' : 'text-blue-500'}
              transform={`rotate(-90 ${centerX} ${centerY})`}
            />
          )}
          
          {/* Agent Nodes */}
          {steps.map((step, index) => {
            const angle = angleStep * index - Math.PI / 2
            const x = centerX + radius * Math.cos(angle)
            const y = centerY + radius * Math.sin(angle)
            
            return (
              <g key={index}>
                {/* Connection Line to Center */}
                <line
                  x1={x}
                  y1={y}
                  x2={centerX}
                  y2={centerY}
                  stroke="currentColor"
                  strokeWidth="0.5"
                  className="text-muted-foreground/10"
                />
                
                {/* Node Circle */}
                <circle
                  cx={x}
                  cy={y}
                  r="12"
                  fill="currentColor"
                  className={`
                    ${step.status === 'completed' ? 'text-green-500' :
                      step.status === 'active' ? 'text-blue-500' :
                      step.status === 'error' ? 'text-red-500' :
                      'text-muted-foreground/30'}
                  `}
                />
                <circle
                  cx={x}
                  cy={y}
                  r="8"
                  fill="currentColor"
                  className="text-background"
                />
                
                {/* Pulse Effect for Active */}
                {step.status === 'active' && (
                  <circle
                    cx={x}
                    cy={y}
                    r="12"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="text-blue-500 animate-ping"
                  />
                )}
              </g>
            )
          })}
          
          {/* Center Progress */}
          <text
            x={centerX}
            y={centerY}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-2xl font-bold fill-current"
          >
            {progress}%
          </text>
        </svg>
        
        {/* Labels */}
        <div className="mt-3 space-y-1">
          {steps.map((step, index) => (
            <div key={index} className="flex items-center gap-2 text-xs">
              <div className={`w-2 h-2 rounded-full ${
                step.status === 'completed' ? 'bg-green-500' :
                step.status === 'active' ? 'bg-blue-500 animate-pulse' :
                step.status === 'error' ? 'bg-red-500' :
                'bg-muted-foreground/30'
              }`} />
              <span className={step.status === 'active' ? 'text-primary font-medium' : 'text-muted-foreground'}>
                {step.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Grid View
  const renderGridView = () => (
    <div className="grid grid-cols-2 gap-2">
      {steps.map((step, index) => {
        const Icon = getAgentIcon(step.name)
        return (
          <div
            key={index}
            className={`
              p-3 rounded-lg border transition-all duration-300
              ${getStatusColor(step.status)}
              ${step.status === 'active' ? 'scale-[1.02]' : ''}
            `}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="relative">
                {step.status === 'active' && (
                  <div className="absolute inset-0 rounded-full animate-ping bg-blue-500/30" />
                )}
                <div className="relative">
                  {getStatusIcon(step.status)}
                </div>
              </div>
              <Icon className="w-4 h-4 text-muted-foreground" />
            </div>
            
            <p className={`text-xs font-medium mb-1 ${
              step.status === 'active' ? 'text-primary' : 'text-foreground'
            }`}>
              {step.name}
            </p>
            
            <Badge
              variant={
                step.status === 'completed' ? 'success' :
                step.status === 'active' ? 'default' :
                step.status === 'error' ? 'destructive' :
                'outline'
              }
              className="text-[10px] h-4 px-1.5"
            >
              {step.status.charAt(0).toUpperCase() + step.status.slice(1)}
            </Badge>
          </div>
        )
      })}
    </div>
  )

  // Horizontal Stepper View
  const renderHorizontalView = () => (
    <div className="space-y-3">
      {/* Steps */}
      <div className="flex items-center justify-between gap-1">
        {steps.map((step, index) => {
          const Icon = getAgentIcon(step.name)
          return (
            <div key={index} className="flex items-center flex-1">
              <div className="flex flex-col items-center gap-1 flex-1">
                <div className="relative">
                  {step.status === 'active' && (
                    <div className="absolute inset-0 rounded-full animate-ping bg-blue-500/30" />
                  )}
                  <div className={`
                    relative w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all
                    ${step.status === 'completed' ? 'bg-green-500 border-green-500' :
                      step.status === 'active' ? 'bg-blue-500 border-blue-500' :
                      step.status === 'error' ? 'bg-red-500 border-red-500' :
                      'bg-muted border-muted-foreground/30'}
                  `}>
                    <Icon className={`w-4 h-4 ${
                      step.status === 'pending' ? 'text-muted-foreground' : 'text-white'
                    }`} />
                  </div>
                </div>
                
                <p className={`text-[10px] text-center font-medium max-w-[60px] ${
                  step.status === 'active' ? 'text-primary' : 'text-muted-foreground'
                }`}>
                  {step.name.split(' ')[0]}
                </p>
              </div>
              
              {index < steps.length - 1 && (
                <div className="flex-1 h-0.5 bg-muted-foreground/20 mx-1" />
              )}
            </div>
          )
        })}
      </div>
      
      {/* Active Step Details */}
      {steps.find(s => s.status === 'active') && (
        <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <p className="text-xs font-medium text-primary">
            {steps.find(s => s.status === 'active')?.name}
          </p>
          <p className="text-[10px] text-muted-foreground mt-1">
            Processing...
          </p>
        </div>
      )}
    </div>
  )

  // Kanban Board View
  const renderKanbanView = () => {
    const pendingSteps = steps.filter(s => s.status === 'pending')
    const activeSteps = steps.filter(s => s.status === 'active')
    const completedSteps = steps.filter(s => s.status === 'completed')
    const errorSteps = steps.filter(s => s.status === 'error')
    
    const renderColumn = (title: string, items: AgentStep[], color: string) => (
      <div className="flex-1 min-w-0">
        <div className={`text-[10px] font-semibold mb-2 px-2 py-1 rounded-md ${color}`}>
          {title} ({items.length})
        </div>
        <div className="space-y-1">
          {items.map((step, index) => {
            const Icon = getAgentIcon(step.name)
            return (
              <div
                key={index}
                className="p-2 bg-background border rounded-lg shadow-sm"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <Icon className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                  <p className="text-[10px] font-medium truncate">
                    {step.name}
                  </p>
                </div>
                {step.timestamp && (
                  <p className="text-[9px] text-muted-foreground">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
    
    return (
      <div className="flex gap-2">
        {pendingSteps.length > 0 && renderColumn('Todo', pendingSteps, 'bg-muted/50 text-muted-foreground')}
        {activeSteps.length > 0 && renderColumn('Active', activeSteps, 'bg-blue-500/20 text-blue-700 dark:text-blue-400')}
        {completedSteps.length > 0 && renderColumn('Done', completedSteps, 'bg-green-500/20 text-green-700 dark:text-green-400')}
        {errorSteps.length > 0 && renderColumn('Error', errorSteps, 'bg-red-500/20 text-red-700 dark:text-red-400')}
      </div>
    )
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2 pt-3 px-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-semibold">Agent Pipeline</CardTitle>
            <CardDescription className="text-[10px] mt-0.5">
              Multi-agent workflow
            </CardDescription>
          </div>
          
          <div className="flex items-center gap-2">
            {progress > 0 && (
              <Badge variant={progress === 100 ? "success" : "default"} className="text-[10px] h-5 px-1.5 font-semibold">
                {progress}%
              </Badge>
            )}
            
            {/* View Mode Selector */}
            <Select value={viewMode} onValueChange={(value: string) => setViewMode(value as ViewMode)}>
              <SelectTrigger className="w-[32px] h-7 p-0 border-dashed">
                <SelectValue>
                  {viewMode === 'timeline' && <LayoutList className="w-3.5 h-3.5 mx-auto" />}
                  {viewMode === 'circle' && <CircleDot className="w-3.5 h-3.5 mx-auto" />}
                  {viewMode === 'grid' && <LayoutGrid className="w-3.5 h-3.5 mx-auto" />}
                  {viewMode === 'horizontal' && <ArrowRight className="w-3.5 h-3.5 mx-auto" />}
                  {viewMode === 'kanban' && <Columns className="w-3.5 h-3.5 mx-auto" />}
                </SelectValue>
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="timeline">
                  <div className="flex items-center gap-2">
                    <LayoutList className="w-4 h-4" />
                    <span>Timeline</span>
                  </div>
                </SelectItem>
                <SelectItem value="circle">
                  <div className="flex items-center gap-2">
                    <CircleDot className="w-4 h-4" />
                    <span>Circle</span>
                  </div>
                </SelectItem>
                <SelectItem value="grid">
                  <div className="flex items-center gap-2">
                    <LayoutGrid className="w-4 h-4" />
                    <span>Grid</span>
                  </div>
                </SelectItem>
                <SelectItem value="horizontal">
                  <div className="flex items-center gap-2">
                    <ArrowRight className="w-4 h-4" />
                    <span>Stepper</span>
                  </div>
                </SelectItem>
                <SelectItem value="kanban">
                  <div className="flex items-center gap-2">
                    <Columns className="w-4 h-4" />
                    <span>Kanban</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        
        {/* Progress Bar */}
        {progress > 0 && viewMode !== 'circle' && (
          <div className="mt-2 h-1 bg-muted rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ease-out ${
                progress === 100 ? 'bg-green-500' : 'bg-blue-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </CardHeader>
      
      <CardContent className="pt-2">
        {renderView()}
        
        {/* Empty State */}
        {steps.every(s => s.status === 'pending') && viewMode !== 'kanban' && (
          <div className="mt-4 p-4 bg-gradient-to-br from-muted/50 to-muted/30 rounded-lg border border-dashed">
            <div className="flex items-center justify-center gap-2">
              <Sparkles className="w-4 h-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground font-medium">
                Ready to process disputes
              </p>
            </div>
          </div>
        )}
        
        {/* Completion Message */}
        {steps.every(s => s.status === 'completed') && viewMode !== 'kanban' && (
          <div className="mt-4 p-4 bg-gradient-to-br from-green-500/10 to-green-500/5 rounded-lg border border-green-500/20">
            <div className="flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <p className="text-xs text-green-700 dark:text-green-400 font-medium">
                Pipeline completed successfully
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
