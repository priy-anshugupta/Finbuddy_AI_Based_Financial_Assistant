'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Wallet, TrendingUp, Plus, X, Loader2 } from 'lucide-react'

interface CashSuggestion {
    label: string
    subcategory: string
    typical_amount: number
    amount_range: { low: number; high: number }
    probability: number
}

interface CashCheckData {
    estimated_untracked_cash: number
    total_withdrawn: number
    tracked_cash_spend: number
    days_since_withdrawal: number | null
    suggestions: CashSuggestion[]
}

interface UntrackedCashWidgetProps {
    onTransactionAdded?: () => void
}

export function UntrackedCashWidget({ onTransactionAdded }: UntrackedCashWidgetProps = {}) {
    const [cashData, setCashData] = useState<CashCheckData | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isExpanded, setIsExpanded] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)

    useEffect(() => {
        fetchCashCheck()
    }, [])

    const fetchCashCheck = async () => {
        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/cash-check/summary`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            })

            if (response.ok) {
                const data = await response.json()
                setCashData(data)
            }
        } catch (error) {
            console.error('Error fetching cash check:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const handleQuickAdd = async (suggestion: CashSuggestion) => {
        setIsSubmitting(true)
        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/cash-check/quick-add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    amount: suggestion.typical_amount,
                    subcategory: suggestion.subcategory,
                    description: `Cash - ${suggestion.label}`,
                }),
            })

            if (response.ok) {
                // Refresh cash check data
                await fetchCashCheck()
                setIsExpanded(false)
                // Notify parent component
                if (onTransactionAdded) {
                    onTransactionAdded()
                }
            } else {
                alert('Failed to add expense')
            }
        } catch (error) {
            console.error('Error adding expense:', error)
            alert('Failed to add expense')
        } finally {
            setIsSubmitting(false)
        }
    }

    if (isLoading) {
        return (
            <div className="glass-card p-6 animate-pulse">
                <div className="h-4 bg-slate-700 rounded w-32 mb-4" />
                <div className="h-8 bg-slate-700 rounded w-24" />
            </div>
        )
    }

    if (!cashData || cashData.estimated_untracked_cash < 100) {
        return null // Don't show if no untracked cash
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 bg-gradient-to-br from-amber-900/20 to-orange-900/20 border-l-4 border-l-amber-500"
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                        <Wallet className="w-5 h-5 text-amber-400" />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-white">Untracked Cash</h3>
                        <p className="text-xs text-slate-400">
                            {cashData.days_since_withdrawal !== null 
                                ? `${cashData.days_since_withdrawal} days since withdrawal`
                                : 'Recent withdrawals'
                            }
                        </p>
                    </div>
                </div>
                {!isExpanded && (
                    <button
                        onClick={() => setIsExpanded(true)}
                        className="text-amber-400 hover:text-amber-300 text-sm font-medium"
                    >
                        Quick Add
                    </button>
                )}
            </div>

            {/* Amount Display */}
            <div className="mb-4">
                <p className="text-3xl font-bold text-white">
                    ₹{cashData.estimated_untracked_cash.toLocaleString('en-IN')}
                </p>
                <p className="text-sm text-slate-400 mt-1">
                    Tracked: ₹{cashData.tracked_cash_spend.toLocaleString('en-IN')} of ₹
                    {cashData.total_withdrawn.toLocaleString('en-IN')}
                </p>
            </div>

            {/* Suggestions (Expanded) */}
            {isExpanded && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-slate-700 pt-4 space-y-2"
                >
                    <div className="flex items-center justify-between mb-3">
                        <p className="text-xs text-slate-400 font-medium">Common expenses:</p>
                        <button
                            onClick={() => setIsExpanded(false)}
                            className="text-slate-500 hover:text-white"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    {cashData.suggestions.map((suggestion, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleQuickAdd(suggestion)}
                            disabled={isSubmitting}
                            className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 hover:border-amber-500/50 transition-all group disabled:opacity-50"
                        >
                            <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
                                    <Plus className="w-4 h-4 text-amber-400" />
                                </div>
                                <div className="text-left">
                                    <p className="text-sm font-medium text-white">{suggestion.label}</p>
                                    <p className="text-xs text-slate-500">
                                        ₹{suggestion.amount_range.low}-₹{suggestion.amount_range.high} typical
                                    </p>
                                </div>
                            </div>
                            <span className="text-lg font-bold text-amber-400">
                                ₹{suggestion.typical_amount}
                            </span>
                        </button>
                    ))}

                    <button
                        onClick={() => setIsExpanded(false)}
                        className="w-full mt-2 py-2 text-xs text-slate-400 hover:text-white transition-colors"
                    >
                        I still have this cash in my wallet
                    </button>
                </motion.div>
            )}

            {/* Progress Bar */}
            {!isExpanded && (
                <div className="mt-4">
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{
                                width: `${Math.min(100, (cashData.tracked_cash_spend / cashData.total_withdrawn) * 100)}%`,
                            }}
                            className="h-full bg-gradient-to-r from-amber-500 to-orange-500"
                        />
                    </div>
                </div>
            )}
        </motion.div>
    )
}
