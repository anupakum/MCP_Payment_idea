/**
 * MCPQueryDemo Component
 * Demonstrates Next.js → CrewAI → MCP → DynamoDB integration
 */

'use client'

import { useState } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { apiClient, DynamoQueryRequest } from '@/lib/api-client'

export default function MCPQueryDemo() {
  const [customerId, setCustomerId] = useState('C123')
  const [transactionId, setTransactionId] = useState('TXN001')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleQueryCustomerTransactions = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      // Call the MCP query endpoint
      const response = await apiClient.queryCustomerTransactions(customerId, 50)
      
      if (response.success) {
        setResult({
          type: 'Customer Transactions',
          data: response.data
        })
      } else {
        setError(response.error || 'Query failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleQueryTransactionById = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await apiClient.queryTransactionById(transactionId)
      
      if (response.success) {
        setResult({
          type: 'Transaction Details',
          data: response.data
        })
      } else {
        setError(response.error || 'Query failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleQueryCustomerCases = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await apiClient.queryCasesByCustomer(customerId, 20)
      
      if (response.success) {
        setResult({
          type: 'Customer Dispute Cases',
          data: response.data
        })
      } else {
        setError(response.error || 'Query failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleCustomQuery = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      // Example: Advanced custom query with filter
      const queryRequest: DynamoQueryRequest = {
        table_name: 'ptr_dispute_resol_customer_cards_and_transactions',
        operation: 'query',
        key_condition: { customer_id: customerId },
        limit: 100
      }

      const response = await apiClient.executeMCPQuery(queryRequest)
      
      if (response.success) {
        // Filter high-value transactions client-side
        const items = response.data?.items || []
        const highValueTxns = items.filter(item => 
          item.transaction_id && (item.amount || 0) > 500
        )

        setResult({
          type: 'High-Value Transactions (>$500)',
          data: {
            ...response.data,
            items: highValueTxns,
            count: highValueTxns.length,
            original_count: items.length
          }
        })
      } else {
        setError(response.error || 'Query failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyAndCreateDispute = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      // This calls CrewAI agents which use MCP tools internally
      const response = await apiClient.verifyTransaction(
        customerId,
        '4532015112830366',
        transactionId
      )
      
      if (response.success) {
        setResult({
          type: 'Dispute Case Created (via CrewAI)',
          data: response.data
        })
      } else {
        setError(response.error || 'Verification failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>MCP Query Demo</CardTitle>
          <CardDescription>
            Demonstrates Next.js → FastAPI → CrewAI → MCP Tool → DynamoDB integration
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Input Fields */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Customer ID</label>
              <Input
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="C123"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Transaction ID</label>
              <Input
                value={transactionId}
                onChange={(e) => setTransactionId(e.target.value)}
                placeholder="TXN001"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Direct MCP Queries (Next.js → MCP → DynamoDB)
            </h3>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={handleQueryCustomerTransactions}
                disabled={loading}
                variant="outline"
              >
                Query Customer Transactions
              </Button>
              <Button
                onClick={handleQueryTransactionById}
                disabled={loading}
                variant="outline"
              >
                Query Transaction by ID
              </Button>
              <Button
                onClick={handleQueryCustomerCases}
                disabled={loading}
                variant="outline"
              >
                Query Customer Cases
              </Button>
              <Button
                onClick={handleCustomQuery}
                disabled={loading}
                variant="outline"
              >
                Custom Query (High Value Txns)
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              CrewAI Agent Actions (Next.js → CrewAI → MCP → DynamoDB)
            </h3>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={handleVerifyAndCreateDispute}
                disabled={loading}
                variant="default"
              >
                Verify Transaction & Create Dispute
              </Button>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
              <span className="ml-3 text-sm text-gray-600 dark:text-gray-400">
                Executing query...
              </span>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <Card className="border-red-200 bg-red-50 dark:bg-red-900/10">
              <CardContent className="pt-6">
                <div className="flex items-start">
                  <Badge variant="destructive" className="mr-2">Error</Badge>
                  <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Result Display */}
          {result && (
            <Card className="border-green-200 bg-green-50 dark:bg-green-900/10">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-100 dark:bg-green-900">
                    Success
                  </Badge>
                  {result.type}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Summary Stats */}
                  {result.data?.count !== undefined && (
                    <div className="flex gap-4 text-sm">
                      <div>
                        <span className="font-semibold">Items Found:</span>{' '}
                        <Badge variant="secondary">{result.data.count}</Badge>
                      </div>
                      {result.data?.scanned_count && (
                        <div>
                          <span className="font-semibold">Scanned:</span>{' '}
                          <Badge variant="secondary">{result.data.scanned_count}</Badge>
                        </div>
                      )}
                      {result.data?.original_count && (
                        <div>
                          <span className="font-semibold">Total Before Filter:</span>{' '}
                          <Badge variant="secondary">{result.data.original_count}</Badge>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Raw JSON Result */}
                  <div className="relative">
                    <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto text-xs">
                      {JSON.stringify(result.data, null, 2)}
                    </pre>
                  </div>

                  {/* Transaction List */}
                  {result.data?.items && result.data.items.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-semibold text-sm">Items:</h4>
                      <div className="space-y-2">
                        {result.data.items.slice(0, 5).map((item: any, idx: number) => (
                          <div
                            key={idx}
                            className="bg-white dark:bg-gray-800 p-3 rounded border text-sm"
                          >
                            <div className="grid grid-cols-2 gap-2">
                              {item.transaction_id && (
                                <div>
                                  <span className="font-medium">Transaction:</span>{' '}
                                  {item.transaction_id}
                                </div>
                              )}
                              {item.amount && (
                                <div>
                                  <span className="font-medium">Amount:</span> $
                                  {item.amount.toFixed(2)}
                                </div>
                              )}
                              {item.merchant && (
                                <div>
                                  <span className="font-medium">Merchant:</span>{' '}
                                  {item.merchant}
                                </div>
                              )}
                              {item.transaction_date && (
                                <div>
                                  <span className="font-medium">Date:</span>{' '}
                                  {new Date(item.transaction_date).toLocaleDateString()}
                                </div>
                              )}
                              {item.case_id && (
                                <div>
                                  <span className="font-medium">Case ID:</span>{' '}
                                  {item.case_id}
                                </div>
                              )}
                              {item.status && (
                                <div>
                                  <Badge variant="outline">{item.status}</Badge>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                        {result.data.items.length > 5 && (
                          <p className="text-sm text-gray-500 italic">
                            ... and {result.data.items.length - 5} more items
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Dispute Case Display */}
                  {result.data?.dispute_case && (
                    <div className="space-y-2">
                      <h4 className="font-semibold text-sm">Dispute Case:</h4>
                      <div className="bg-white dark:bg-gray-800 p-3 rounded border">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <span className="font-medium">Case ID:</span>{' '}
                            {result.data.dispute_case.case_id}
                          </div>
                          <div>
                            <span className="font-medium">Status:</span>{' '}
                            <Badge>{result.data.dispute_case.status}</Badge>
                          </div>
                          <div>
                            <span className="font-medium">Amount:</span> $
                            {result.data.dispute_case.amount_disputed}
                          </div>
                          <div>
                            <span className="font-medium">Priority:</span>{' '}
                            {result.data.dispute_case.priority}
                          </div>
                          <div className="col-span-2">
                            <span className="font-medium">Reason:</span>{' '}
                            {result.data.dispute_case.decision_reason}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>

      {/* Integration Architecture Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Integration Architecture</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Badge>1</Badge>
              <span className="font-medium">Next.js Frontend</span>
              <span className="text-gray-500">→</span>
              <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">apiClient.queryCustomerTransactions()</code>
            </div>
            <div className="flex items-center gap-2">
              <Badge>2</Badge>
              <span className="font-medium">FastAPI MCP Server</span>
              <span className="text-gray-500">→</span>
              <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">POST /mcp/query</code>
            </div>
            <div className="flex items-center gap-2">
              <Badge>3</Badge>
              <span className="font-medium">MCP Tool</span>
              <span className="text-gray-500">→</span>
              <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">DynamoQueryCreatorTool._run()</code>
            </div>
            <div className="flex items-center gap-2">
              <Badge>4</Badge>
              <span className="font-medium">DynamoDB</span>
              <span className="text-gray-500">→</span>
              <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">Query/Scan/GetItem</code>
            </div>
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                <strong>Note:</strong> CrewAI agents can also use the MCP DynamoDB Query Creator tool
                internally to make intelligent decisions about what data to retrieve.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
