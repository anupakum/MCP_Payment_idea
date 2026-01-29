/**
 * API client for communicating with Fast MCP (FastAPI) backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface APIResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export interface CustomerData {
  customer_id: string
  cardholder_name?: string
  cards: CardData[]
  message?: string
}

export interface CardData {
  card_number: string
  card_type?: string
  card_status?: string
  cardholder_name?: string
  expiry_date?: string
  transactions?: TransactionData[]
}

export interface TransactionData {
  transaction_id: string
  transaction_date: string
  amount?: number
  currency?: string
  merchant?: string
  description?: string
  status?: string
}

export interface DisputeCaseData {
  case_id: string
  customer_id: string
  transaction_id: string
  case_type?: string
  status?: string
  created_date?: string
  created_at?: string
  updated_at?: string
  description?: string
  amount_disputed?: number
  transaction_amount?: number
  priority?: string
  dispute_status?: string
  decision_reason?: string
  auto_decided?: boolean
  requires_manual_review?: boolean
  card_id?: string
  transaction_date?: string
  merchant?: string
}

export interface VerificationResult {
  success: boolean
  transaction?: TransactionData
  dispute_case?: DisputeCaseData
  message?: string
}

export interface DynamoQueryRequest {
  table_name: string
  operation: 'query' | 'get_item' | 'scan' | 'put_item' | 'update_item'
  key_condition?: Record<string, any>
  filter_expression?: Record<string, any>
  index_name?: string
  attributes_to_get?: string[]
  limit?: number
  item_data?: Record<string, any>
  update_expression?: Record<string, any>
}

export interface DynamoQueryResult {
  success: boolean
  items?: any[]
  item?: any
  count?: number
  scanned_count?: number
  message?: string
  error?: string
}

class APIClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`

    const defaultHeaders = {
      'Content-Type': 'application/json',
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...defaultHeaders,
          ...options.headers,
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data as APIResponse<T>
    } catch (error) {
      console.error('API request failed:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        message: 'Failed to communicate with server'
      }
    }
  }

  /**
   * NEW: Process any request through Manager Agent (Unified Endpoint)
   * This uses the hierarchical process with intelligent routing
   */
  async processRequest(
    request: string,
    context?: {
      customerId?: string
      cardNumber?: string
      transactionId?: string
      caseId?: string
    }
  ): Promise<APIResponse<any>> {
    return this.request<any>('/process', {
      method: 'POST',
      body: JSON.stringify({
        request,
        customer_id: context?.customerId,
        card_number: context?.cardNumber,
        transaction_id: context?.transactionId,
        case_id: context?.caseId
      }),
    })
  }

  /**
   * Verify customer and get associated cards
   * LEGACY: Use processRequest() for new integrations
   */
  async verifyCustomer(customerId: string): Promise<APIResponse<CustomerData>> {
    return this.request<CustomerData>('/verify/customer', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId }),
    })
  }

  /**
   * Verify card and get associated transactions
   * LEGACY: Use processRequest() for new integrations
   */
  async verifyCard(
    customerId: string,
    cardNumber: string
  ): Promise<APIResponse<{ transactions: TransactionData[] }>> {
    return this.request<{ transactions: TransactionData[] }>('/verify/card', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: customerId,
        card_number: cardNumber
      }),
    })
  }

  /**
   * Verify transaction and create dispute case
   * LEGACY: Use processRequest() for new integrations
   */
  async verifyTransaction(
    customerId: string,
    cardNumber: string,
    transactionId: string
  ): Promise<APIResponse<VerificationResult>> {
    return this.request<VerificationResult>('/verify/txn', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: customerId,
        card_number: cardNumber,
        transaction_id: transactionId
      }),
    })
  }

  /**
   * Get case status by case ID
   * LEGACY: Use processRequest() for new integrations
   */
  async getCaseStatus(caseId: string): Promise<APIResponse<{ case: DisputeCaseData }>> {
    return this.request<{ case: DisputeCaseData }>('/case/status', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId }),
    })
  }

  /**
   * Get all cases for a customer
   * LEGACY: Use processRequest() for new integrations
   */
  async getCustomerCases(customerId: string): Promise<APIResponse<{ cases: DisputeCaseData[]; count: number }>> {
    return this.request<{ cases: DisputeCaseData[]; count: number }>('/case/customer', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId }),
    })
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<APIResponse<{ status: string; database: any }>> {
    return this.request<{ status: string; database: any }>('/health', {
      method: 'GET',
    })
  }

  /**
   * Get service information
   */
  async getServiceInfo(): Promise<APIResponse<any>> {
    return this.request<any>('/', {
      method: 'GET',
    })
  }

  /**
   * Execute a dynamic DynamoDB query via MCP tool
   * This allows Next.js to request CrewAI agents to execute custom queries
   */
  async executeMCPQuery(queryRequest: DynamoQueryRequest): Promise<APIResponse<DynamoQueryResult>> {
    return this.request<DynamoQueryResult>('/mcp/query', {
      method: 'POST',
      body: JSON.stringify(queryRequest),
    })
  }

  /**
   * Helper: Query customer transactions using MCP
   */
  async queryCustomerTransactions(customerId: string, limit: number = 50): Promise<APIResponse<DynamoQueryResult>> {
    return this.executeMCPQuery({
      table_name: 'ptr_dispute_resol_customer_cards_and_transactions',
      operation: 'query',
      key_condition: { customer_id: customerId },
      limit: limit
    })
  }

  /**
   * Helper: Query transaction by ID using MCP
   */
  async queryTransactionById(transactionId: string): Promise<APIResponse<DynamoQueryResult>> {
    return this.executeMCPQuery({
      table_name: 'ptr_dispute_resol_customer_cards_and_transactions',
      operation: 'query',
      key_condition: { transaction_id: transactionId },
      index_name: 'TransactionIndex'
    })
  }

  /**
   * Helper: Query cases by customer using MCP
   */
  async queryCasesByCustomer(customerId: string, limit: number = 50): Promise<APIResponse<DynamoQueryResult>> {
    return this.executeMCPQuery({
      table_name: 'ptr_dispute_resol_case_db',
      operation: 'query',
      key_condition: { customer_id: customerId },
      index_name: 'CustomerIndex',
      limit: limit
    })
  }

  /**
   * Get live logs from backend
   */
  async getLiveLogs(limit: number = 50): Promise<APIResponse<{ logs: any[], count: number }>> {
    return this.request<{ logs: any[], count: number }>(`/logs/live?limit=${limit}`, {
      method: 'GET',
    })
  }

  /**
   * Get detailed logs from backend
   */
  async getDetailedLogs(limit: number = 20): Promise<APIResponse<{ logs: any[], count: number }>> {
    return this.request<{ logs: any[], count: number }>(`/logs/detailed?limit=${limit}`, {
      method: 'GET',
    })
  }

  /**
   * Get logging statistics
   */
  async getLogStats(): Promise<APIResponse<{ stats: any }>> {
    return this.request<{ stats: any }>('/logs/stats', {
      method: 'GET',
    })
  }

  /**
   * Clear all logs
   */
  async clearLogs(): Promise<APIResponse<{ message: string }>> {
    return this.request<{ message: string }>('/logs/clear', {
      method: 'DELETE',
    })
  }

  /**
   * Upload documents for a case
   */
  async uploadCaseDocuments(
    caseId: string,
    files: File[]
  ): Promise<APIResponse<{
    case_id: string
    uploaded_documents: Array<{
      filename: string
      url: string
      key: string
      bucket: string
    }>
    total_documents: number
    message: string
  }>> {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const url = `${this.baseURL}/case/${caseId}/upload-documents`

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - browser will set it with boundary for multipart/form-data
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
      }

      const data = await response.json()

      // Backend returns the data directly with success field
      return {
        success: data.success || false,
        data: data,
        message: data.message
      } as APIResponse<any>
    } catch (error) {
      console.error('Document upload failed:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        message: 'Failed to upload documents'
      }
    }
  }

  /**
   * Get documents for a case with download URLs
   */
  async getCaseDocuments(
    caseId: string
  ): Promise<APIResponse<{
    case_id: string
    documents: Array<{
      filename: string
      url: string
      key: string
      bucket: string
      download_url?: string
    }>
    count: number
  }>> {
    const response = await this.request<any>(`/case/${caseId}/documents`, {
      method: 'GET',
    }) as any

    // Backend returns data at root level, wrap it properly
    if (response.success) {
      return {
        success: true,
        data: {
          case_id: response.case_id,
          documents: response.documents || [],
          count: response.count || 0
        }
      }
    }

    return response
  }
}

// Export singleton instance
export const apiClient = new APIClient()

// Export class for custom instances
export { APIClient }

// Helper function for error handling
export function getErrorMessage(response: APIResponse): string {
  return response.error || response.message || 'An unexpected error occurred'
}