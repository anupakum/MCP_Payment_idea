'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useEffect, useRef } from 'react'
import { Terminal } from 'lucide-react'
import { useLog, type LogEntry } from '@/lib/log-context'

export function LiveLogs() {
  const { liveLogs: logs } = useLog()
  const logsEndRef = useRef<HTMLDivElement>(null)
  const logsContainerRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [logs])

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return 'text-green-600 dark:text-green-400'
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'error':
        return 'text-red-600 dark:text-red-400'
      default:
        return 'text-blue-600 dark:text-blue-400'
    }
  }

  const getLevelBadge = (level: LogEntry['level']) => {
    const variants = {
      info: 'default',
      success: 'success',
      warning: 'secondary',
      error: 'destructive'
    }
    return variants[level] as any
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              Live Logs
            </CardTitle>
            <CardDescription>
              Real-time CrewAI processing events
            </CardDescription>
          </div>
          {logs.length > 0 && (
            <Badge variant="outline" className="text-xs">
              {logs.length} events
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div ref={logsContainerRef} className="space-y-2 max-h-64 overflow-y-auto font-mono text-xs bg-muted/30 rounded-lg p-3">
          {logs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No logs yet...
            </p>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="flex flex-col gap-1 pb-2 border-b border-border/50 last:border-0 last:pb-0">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground text-[10px]">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <Badge variant={getLevelBadge(log.level)} className="text-[10px] px-1.5 py-0">
                    {log.level.toUpperCase()}
                  </Badge>
                  {log.agent && (
                    <span className="text-muted-foreground text-[10px]">
                      [{log.agent}]
                    </span>
                  )}
                </div>
                <p className={`${getLevelColor(log.level)} text-[11px] leading-relaxed`}>
                  {log.message}
                </p>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </CardContent>
    </Card>
  )
}
