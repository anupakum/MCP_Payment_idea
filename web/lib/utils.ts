import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format currency amount for display
 */
export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount)
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    }).format(date)
  } catch {
    return dateString
  }
}

/**
 * Get status color classes
 */
export function getStatusColorClasses(status: string): string {
  const upperStatus = status.toUpperCase()
  switch (upperStatus) {
    case 'RESOLVED_CUSTOMER':
    case 'APPROVED':
    case 'CLOSED':
      return 'status-resolved'
    case 'REJECTED_TIME_BARRED':
    case 'REJECTED':
      return 'status-rejected'
    case 'FORWARDED_TO_ACQUIRER':
    case 'IN_PROGRESS':
    case 'PENDING':
      return 'status-forwarded'
    case 'OPEN':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
  }
}

/**
 * Get human-readable status text
 */
export function getStatusText(status: string): string {
  const upperStatus = status.toUpperCase()
  switch (upperStatus) {
    case 'RESOLVED_CUSTOMER':
    case 'APPROVED':
      return 'Resolved in Customer Favor'
    case 'REJECTED_TIME_BARRED':
      return 'Rejected - Time Barred'
    case 'REJECTED':
      return 'Rejected'
    case 'FORWARDED_TO_ACQUIRER':
      return 'Forwarded to Acquirer'
    case 'IN_PROGRESS':
      return 'In Progress'
    case 'PENDING':
      return 'Pending'
    case 'OPEN':
      return 'Open'
    case 'CLOSED':
      return 'Closed'
    default:
      return status
  }
}

/**
 * Truncate long strings with ellipsis
 */
export function truncateString(str: string, length: number): string {
  if (str.length <= length) return str
  return str.substring(0, length) + '...'
}

/**
 * Sleep utility for delays
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}