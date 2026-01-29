"use client"

import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CreditCard, ChevronRight } from 'lucide-react'
import type { CardData } from '@/lib/api-client'

export interface CardItemProps {
  card: CardData
  onClick: () => void
  disabled?: boolean
}

export function CardItem({ card, onClick, disabled = false }: CardItemProps) {
  const getCardTypeColor = (cardType?: string) => {
    switch (cardType?.toUpperCase()) {
      case 'VISA':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
      case 'MASTERCARD':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'  
      case 'AMEX':
      case 'AMERICAN EXPRESS':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
      case 'DISCOVER':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
    }
  }

  const transactionCount = card.transactions?.length || 0

  return (
    <Card className="card-item cursor-pointer hover:shadow-md transition-all duration-200">
      <CardContent className="p-4">
        <Button
          variant="ghost"
          className="w-full h-auto p-0 flex items-center justify-between"
          onClick={onClick}
          disabled={disabled}
        >
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-primary" />
            </div>
            
            <div className="flex-1 text-left">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-foreground">
                  {card.card_number ? `•••• ${card.card_number.slice(-4)}` : 'Card'}
                </span>
                {card.card_type && (
                  <Badge 
                    variant="outline" 
                    className={getCardTypeColor(card.card_type)}
                  >
                    {card.card_type}
                  </Badge>
                )}
                {card.card_status && (
                  <Badge 
                    variant={card.card_status === 'ACTIVE' ? 'success' : 'secondary'}
                    className="text-xs"
                  >
                    {card.card_status}
                  </Badge>
                )}
              </div>
              
              <p className="text-sm text-muted-foreground">
                {transactionCount} transaction{transactionCount !== 1 ? 's' : ''} available
              </p>
            </div>
          </div>
          
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        </Button>
      </CardContent>
    </Card>
  )
}