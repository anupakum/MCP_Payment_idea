"use client"

import React from 'react'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatDate, truncateString } from '@/lib/utils'
import { Receipt, ExternalLink } from 'lucide-react'
import type { TransactionData } from '@/lib/api-client'

export interface TransactionTableProps {
  transactions: TransactionData[]
  onTransactionSelect: (transactionId: string) => void
  disabled?: boolean
}

export function TransactionTable({ 
  transactions, 
  onTransactionSelect, 
  disabled = false 
}: TransactionTableProps) {
  if (!transactions || transactions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Receipt className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No transactions found</p>
      </div>
    )
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Merchant</TableHead>
            <TableHead>Description</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        
        <TableBody>
          {transactions.map((transaction) => {
            const amount = transaction.amount || 0
            const currency = transaction.currency || 'USD'
            const dateStr = transaction.transaction_date || 'Unknown Date'
            const merchant = transaction.merchant || 'Unknown Merchant'
            const description = transaction.description || 'No description'
            const status = transaction.status || 'COMPLETED'
            
            return (
              <TableRow 
                key={transaction.transaction_id} 
                className="transaction-row hover:bg-muted/50 cursor-pointer"
                onClick={() => !disabled && onTransactionSelect(transaction.transaction_id)}
              >
                <TableCell>
                  <div className="font-medium text-sm">
                    {formatDate(dateStr)}
                  </div>
                </TableCell>
                
                <TableCell>
                  <div className="font-semibold">
                    {formatCurrency(amount, currency)}
                  </div>
                </TableCell>
                
                <TableCell>
                  <div className="font-medium">
                    {truncateString(merchant, 20)}
                  </div>
                </TableCell>
                
                <TableCell>
                  <div className="text-sm text-muted-foreground">
                    {truncateString(description, 30)}
                  </div>
                </TableCell>
                
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={disabled}
                    onClick={(e) => {
                      e.stopPropagation()
                      onTransactionSelect(transaction.transaction_id)
                    }}
                    className="text-xs"
                  >
                    <ExternalLink className="w-3 h-3 mr-1" />
                    Dispute
                  </Button>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      
      {transactions.length > 0 && (
        <div className="bg-muted/30 px-4 py-2 text-xs text-muted-foreground border-t">
          Showing {transactions.length} transaction{transactions.length !== 1 ? 's' : ''}. 
          Click on any transaction to start a dispute.
        </div>
      )}
    </div>
  )
}