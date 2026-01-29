'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useState } from 'react'
import { FileText, ChevronRight, ChevronDown } from 'lucide-react'
import { useLog } from '@/lib/log-context'

export function DetailedLogs() {
  const { detailedLogs } = useLog()
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const logs = detailedLogs.map(log => ({
    ...log,
    expanded: expandedIds.has(log.id)
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="w-4 h-4" />
          Detailed Logs
        </CardTitle>
        <CardDescription>
          Complete execution trace and agent decisions
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {logs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No detailed logs available
            </div>
          ) : (
            logs.map((log) => (
              <div 
                key={log.id} 
                className="border border-border rounded-lg overflow-hidden hover:border-primary/50 transition-colors"
              >
                <div 
                  className="p-3 cursor-pointer bg-muted/30 hover:bg-muted/50"
                  onClick={() => toggleExpand(log.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 flex-1 min-w-0">
                      <div className="mt-0.5">
                        {log.expanded ? (
                          <ChevronDown className="w-4 h-4 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-muted-foreground" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-xs">
                            {log.agent}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(log.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm font-medium truncate">
                          {log.action}
                        </p>
                      </div>
                    </div>
                    {log.duration && (
                      <Badge variant="secondary" className="text-xs flex-shrink-0">
                        {log.duration}
                      </Badge>
                    )}
                  </div>
                </div>
                
                {log.expanded && (
                  <div className="p-3 bg-background border-t border-border">
                    <p className="text-xs text-muted-foreground font-mono whitespace-pre-wrap">
                      {log.details}
                    </p>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
        
        {logs.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs text-muted-foreground text-center">
              Click on any log entry to expand details
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
