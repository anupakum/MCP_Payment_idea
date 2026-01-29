"""
Centralized logging system for CrewAI + MCP integration.

This module provides a thread-safe logging system that captures:
- CrewAI agent activities
- MCP server calls
- DynamoDB queries
- System events

Logs are stored in memory and exposed via FastAPI endpoints for frontend consumption.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque
from threading import Lock
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Log levels matching frontend expectations."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class LogEntry:
    """Individual log entry."""
    
    def __init__(
        self,
        level: LogLevel,
        message: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[str] = None,
        duration: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = f"{datetime.now().timestamp()}-{id(self)}"
        self.timestamp = datetime.now().isoformat()
        self.level = level
        self.message = message
        self.agent = agent
        self.action = action
        self.details = details
        self.duration = duration
        self.metadata = metadata or {}
    
    def to_live_log(self) -> Dict[str, Any]:
        """Convert to live log format for frontend."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "message": self.message,
            "agent": self.agent
        }
    
    def to_detailed_log(self) -> Dict[str, Any]:
        """Convert to detailed log format for frontend."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "agent": self.agent or "System",
            "action": self.action or "Activity",
            "details": self.details or self.message,
            "duration": self.duration,
            "expanded": False
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "message": self.message,
            "agent": self.agent,
            "action": self.action,
            "details": self.details,
            "duration": self.duration,
            "metadata": self.metadata
        }


class LogManager:
    """
    Thread-safe log manager for storing and retrieving logs.
    
    Singleton pattern - use LogManager.get_instance() to access.
    """
    
    _instance: Optional['LogManager'] = None
    _lock = Lock()
    
    def __init__(self, max_logs: int = 200):
        """Initialize log manager."""
        self.max_logs = max_logs
        self.logs: deque[LogEntry] = deque(maxlen=max_logs)
        self.logs_lock = Lock()
        logger.info(f"LogManager initialized (max logs: {max_logs})")
    
    @classmethod
    def get_instance(cls) -> 'LogManager':
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)."""
        with cls._lock:
            cls._instance = None
    
    def add_log(
        self,
        level: LogLevel,
        message: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[str] = None,
        duration: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogEntry:
        """Add a log entry."""
        log_entry = LogEntry(
            level=level,
            message=message,
            agent=agent,
            action=action,
            details=details,
            duration=duration,
            metadata=metadata
        )
        
        with self.logs_lock:
            self.logs.append(log_entry)
        
        # Also log to standard logger
        log_method = getattr(logger, level.value if level != LogLevel.SUCCESS else "info")
        log_method(f"[{agent or 'System'}] {message}")
        
        return log_entry
    
    def get_logs(
        self,
        limit: Optional[int] = None,
        level: Optional[LogLevel] = None,
        agent: Optional[str] = None
    ) -> List[LogEntry]:
        """Get logs with optional filtering."""
        with self.logs_lock:
            filtered_logs = list(self.logs)
        
        # Apply filters
        if level:
            filtered_logs = [log for log in filtered_logs if log.level == level]
        
        if agent:
            filtered_logs = [log for log in filtered_logs if log.agent == agent]
        
        # Apply limit
        if limit:
            filtered_logs = filtered_logs[-limit:]
        
        return filtered_logs
    
    def get_live_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get logs formatted for live logs display."""
        logs = self.get_logs(limit=limit)
        return [log.to_live_log() for log in logs]
    
    def get_detailed_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get logs formatted for detailed logs display."""
        logs = self.get_logs(limit=limit)
        return [log.to_detailed_log() for log in logs]
    
    def clear_logs(self):
        """Clear all logs."""
        with self.logs_lock:
            self.logs.clear()
        logger.info("All logs cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        with self.logs_lock:
            total = len(self.logs)
            by_level = {}
            by_agent = {}
            
            for log in self.logs:
                # Count by level
                level_key = log.level.value
                by_level[level_key] = by_level.get(level_key, 0) + 1
                
                # Count by agent
                agent_key = log.agent or "System"
                by_agent[agent_key] = by_agent.get(agent_key, 0) + 1
        
        return {
            "total_logs": total,
            "max_logs": self.max_logs,
            "by_level": by_level,
            "by_agent": by_agent
        }


# Convenience functions for quick logging
def log_info(message: str, agent: Optional[str] = None, **kwargs):
    """Log info message."""
    LogManager.get_instance().add_log(LogLevel.INFO, message, agent=agent, **kwargs)


def log_success(message: str, agent: Optional[str] = None, **kwargs):
    """Log success message."""
    LogManager.get_instance().add_log(LogLevel.SUCCESS, message, agent=agent, **kwargs)


def log_warning(message: str, agent: Optional[str] = None, **kwargs):
    """Log warning message."""
    LogManager.get_instance().add_log(LogLevel.WARNING, message, agent=agent, **kwargs)


def log_error(message: str, agent: Optional[str] = None, **kwargs):
    """Log error message."""
    LogManager.get_instance().add_log(LogLevel.ERROR, message, agent=agent, **kwargs)


def log_mcp_call(operation: str, table: str, result_count: Optional[int] = None, duration: Optional[str] = None):
    """Log MCP/DynamoDB call."""
    message = f"MCP Query: {operation} on {table}"
    if result_count is not None:
        message += f" ({result_count} items)"
    
    LogManager.get_instance().add_log(
        LogLevel.INFO,
        message,
        agent="MCP Server",
        action=f"DynamoDB {operation}",
        details=f"Table: {table}, Results: {result_count or 0}",
        duration=duration,
        metadata={"operation": operation, "table": table, "result_count": result_count}
    )


def log_agent_activity(agent_name: str, action: str, details: Optional[str] = None):
    """Log agent activity."""
    LogManager.get_instance().add_log(
        LogLevel.INFO,
        f"{agent_name}: {action}",
        agent=agent_name,
        action=action,
        details=details
    )
