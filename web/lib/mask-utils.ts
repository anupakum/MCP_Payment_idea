/**
 * Utility functions for masking sensitive data in logs
 */

export function maskCustomerId(customerId: string): string {
  if (!customerId || customerId.length < 4) return '****'
  return `${customerId.substring(0, 4)}${'*'.repeat(customerId.length - 4)}`
}

export function maskCardNumber(cardNumber: string): string {
  if (!cardNumber || cardNumber.length < 4) return '****-****-****-****'
  const last4 = cardNumber.slice(-4)
  return `****-****-****-${last4}`
}

export function maskTransactionId(transactionId: string): string {
  if (!transactionId || transactionId.length < 8) return '********'
  return `${transactionId.substring(0, 8)}...`
}

export function maskAmount(amount: number, currency: string = 'USD'): string {
  return `${currency} ${'*'.repeat(amount.toString().length)}.XX`
}

export function maskEmail(email?: string): string {
  if (!email) return 'user@*****.com'
  const [localPart, domain] = email.split('@')
  if (!domain) return '***@***'
  const maskedLocal = localPart.length > 2 
    ? `${localPart.substring(0, 2)}${'*'.repeat(localPart.length - 2)}`
    : '**'
  return `${maskedLocal}@${domain}`
}

export function maskName(name?: string): string {
  if (!name) return '*** ***'
  const parts = name.split(' ')
  return parts.map(part => 
    part.length > 1 ? `${part[0]}${'*'.repeat(part.length - 1)}` : '*'
  ).join(' ')
}

/**
 * Format trace data as a readable string with proper indentation
 */
export function formatTraceData(data: Record<string, any>, indent: number = 0): string {
  const spaces = '  '.repeat(indent)
  const entries: string[] = []
  
  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined) {
      entries.push(`${spaces}${key}: null`)
    } else if (typeof value === 'object' && !Array.isArray(value)) {
      entries.push(`${spaces}${key}:`)
      entries.push(formatTraceData(value, indent + 1))
    } else if (Array.isArray(value)) {
      entries.push(`${spaces}${key}: [${value.length} items]`)
      if (value.length > 0 && typeof value[0] === 'object') {
        value.slice(0, 3).forEach((item, i) => {
          entries.push(`${spaces}  [${i}]:`)
          entries.push(formatTraceData(item, indent + 2))
        })
        if (value.length > 3) {
          entries.push(`${spaces}  ... ${value.length - 3} more items`)
        }
      }
    } else {
      entries.push(`${spaces}${key}: ${value}`)
    }
  }
  
  return entries.join('\n')
}
