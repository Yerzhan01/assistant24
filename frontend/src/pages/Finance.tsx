import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { FinanceApi } from '../api/client'
import {
    TrendingUp,
    TrendingDown,
    Plus,
    Download,
    Calendar,
    Search,
    X,
    Loader2,
    ArrowUpRight,
    ArrowDownRight
} from 'lucide-react'

interface Transaction {
    id: string
    type: 'income' | 'expense'
    amount: number
    category: string
    description: string
    date: string
    contact_name?: string
}

interface FinanceSummary {
    total_income: number
    total_expense: number
    balance: number
    this_month_income: number
    this_month_expense: number
}

export default function Finance() {
    const { token } = useAuth()
    const [transactions, setTransactions] = useState<Transaction[]>([])
    const [summary, setSummary] = useState<FinanceSummary | null>(null)
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [filter, setFilter] = useState<'all' | 'income' | 'expense'>('all')
    const [searchTerm, setSearchTerm] = useState('')

    // Form state
    const [formData, setFormData] = useState({
        type: 'income' as 'income' | 'expense',
        amount: '',
        category: '',
        description: '',
        date: new Date().toISOString().split('T')[0],
        contact_name: ''
    })

    const categories = {
        income: ['Продажи', 'Услуги', 'Инвестиции', 'Возврат', 'Другое'],
        expense: ['Зарплата', 'Аренда', 'Налоги', 'Реклама', 'Транспорт', 'Связь', 'Другое']
    }

    // Fetch data
    useEffect(() => {
        fetchTransactions()
        fetchSummary()
    }, [])

    const fetchTransactions = async () => {
        try {
            const res = await FinanceApi.getTransactions({ limit: 10 })
            setTransactions(res.data.transactions || res.data || [])
        } catch (err) {
            console.error('Failed to fetch transactions:', err)
        } finally {
            setLoading(false)
        }
    }

    const fetchSummary = async () => {
        try {
            const res = await FinanceApi.getSummary()
            setSummary(res.data)
        } catch (err) {
            console.error('Failed to fetch summary:', err)
        }
    }

    const saveTransaction = async () => {
        try {
            const res = await fetch('/api/v1/finance/transactions', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...formData,
                    amount: parseFloat(formData.amount)
                })
            })

            if (res.ok) {
                setShowModal(false)
                resetForm()
                fetchTransactions()
                fetchSummary()
            }
        } catch (err) {
            console.error('Failed to save transaction:', err)
        }
    }

    const resetForm = () => {
        setFormData({
            type: 'income',
            amount: '',
            category: '',
            description: '',
            date: new Date().toISOString().split('T')[0],
            contact_name: ''
        })
    }

    const filteredTransactions = transactions.filter(tx => {
        if (filter !== 'all' && tx.type !== filter) return false
        if (searchTerm && !tx.description.toLowerCase().includes(searchTerm.toLowerCase())) return false
        return true
    })

    const formatAmount = (amount: number) => {
        return new Intl.NumberFormat('ru-RU').format(amount) + ' ₸'
    }

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short'
        })
    }

    return (
        <div className="space-y-4 md:space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl md:text-2xl lg:text-3xl font-bold text-white">💰 Финансы</h1>
                        <p className="text-gray-400 text-sm md:text-base">Учёт доходов и расходов</p>
                    </div>
                    {/* Mobile Add Button */}
                    <button
                        onClick={() => setShowModal(true)}
                        className="md:hidden p-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg"
                    >
                        <Plus className="w-5 h-5" />
                    </button>
                </div>

                <div className="hidden md:flex items-center gap-3">
                    <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 
                                       text-white rounded-xl transition">
                        <Download className="w-4 h-4" />
                        Экспорт
                    </button>
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                                   text-white font-medium rounded-xl transition"
                    >
                        <Plus className="w-5 h-5" />
                        Добавить
                    </button>
                </div>
            </div>

            {/* Summary Cards */}
            {summary && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
                    <div className="bg-gray-800 rounded-xl md:rounded-2xl p-3 md:p-5 border border-gray-700">
                        <div className="flex items-center justify-between">
                            <div className="min-w-0 flex-1">
                                <p className="text-gray-400 text-xs md:text-sm truncate">Баланс</p>
                                <p className={`text-lg md:text-2xl font-bold mt-0.5 truncate ${summary.balance >= 0 ? 'text-green-400' : 'text-red-400'
                                    }`}>
                                    {formatAmount(summary.balance)}
                                </p>
                            </div>
                            <div className={`p-2 md:p-3 rounded-lg md:rounded-xl flex-shrink-0 ${summary.balance >= 0 ? 'bg-green-500' : 'bg-red-500'
                                }`}>
                                {summary.balance >= 0
                                    ? <TrendingUp className="w-4 h-4 md:w-5 md:h-5 text-white" />
                                    : <TrendingDown className="w-4 h-4 md:w-5 md:h-5 text-white" />
                                }
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-800 rounded-xl md:rounded-2xl p-3 md:p-5 border border-gray-700">
                        <div className="flex items-center justify-between">
                            <div className="min-w-0 flex-1">
                                <p className="text-gray-400 text-xs md:text-sm truncate">Доходы</p>
                                <p className="text-lg md:text-2xl font-bold text-green-400 mt-0.5 truncate">
                                    {formatAmount(summary.total_income)}
                                </p>
                            </div>
                            <div className="p-2 md:p-3 rounded-lg md:rounded-xl bg-green-500/20 flex-shrink-0">
                                <ArrowUpRight className="w-4 h-4 md:w-5 md:h-5 text-green-400" />
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-800 rounded-xl md:rounded-2xl p-3 md:p-5 border border-gray-700">
                        <div className="flex items-center justify-between">
                            <div className="min-w-0 flex-1">
                                <p className="text-gray-400 text-xs md:text-sm truncate">Расходы</p>
                                <p className="text-lg md:text-2xl font-bold text-red-400 mt-0.5 truncate">
                                    {formatAmount(summary.total_expense)}
                                </p>
                            </div>
                            <div className="p-2 md:p-3 rounded-lg md:rounded-xl bg-red-500/20 flex-shrink-0">
                                <ArrowDownRight className="w-4 h-4 md:w-5 md:h-5 text-red-400" />
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-800 rounded-xl md:rounded-2xl p-3 md:p-5 border border-gray-700">
                        <div className="flex items-center justify-between">
                            <div className="min-w-0 flex-1">
                                <p className="text-gray-400 text-xs md:text-sm truncate">Этот месяц</p>
                                <p className="text-sm md:text-lg font-bold text-white mt-0.5">
                                    <span className="text-green-400">+{formatAmount(summary.this_month_income)}</span>
                                </p>
                                <p className="text-xs md:text-sm text-red-400">
                                    -{formatAmount(summary.this_month_expense)}
                                </p>
                            </div>
                            <div className="p-2 md:p-3 rounded-lg md:rounded-xl bg-primary-500/20 flex-shrink-0">
                                <Calendar className="w-4 h-4 md:w-5 md:h-5 text-primary-400" />
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Filters & Search */}
            <div className="flex flex-col md:flex-row gap-3">
                <div className="flex bg-gray-800 rounded-lg md:rounded-xl p-0.5 md:p-1 overflow-x-auto">
                    {(['all', 'income', 'expense'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-2 md:px-4 py-1.5 md:py-2 rounded-md md:rounded-lg text-xs md:text-sm font-medium transition whitespace-nowrap ${filter === f
                                ? 'bg-primary-500 text-white'
                                : 'text-gray-400 hover:text-white'
                                }`}
                        >
                            {f === 'all' ? 'Все' : f === 'income' ? '💰 Доходы' : '💳 Расходы'}
                        </button>
                    ))}
                </div>

                <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        placeholder="Поиск..."
                        className="w-full pl-9 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg md:rounded-xl
                                   text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-2
                                   focus:ring-primary-500"
                    />
                </div>
            </div>

            {/* Transactions List */}
            <div className="bg-gray-800 rounded-xl md:rounded-2xl border border-gray-700 overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                    </div>
                ) : filteredTransactions.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <p className="text-base md:text-lg">Нет транзакций</p>
                        <p className="text-xs md:text-sm mt-1">Добавьте первую запись</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-700">
                        {filteredTransactions.map(tx => (
                            <div key={tx.id} className="flex items-center gap-3 p-3 md:p-4 hover:bg-gray-700/50 transition">
                                <div className={`w-8 h-8 md:w-10 md:h-10 rounded-lg md:rounded-xl flex items-center justify-center flex-shrink-0 ${tx.type === 'income' ? 'bg-green-500/20' : 'bg-red-500/20'
                                    }`}>
                                    {tx.type === 'income'
                                        ? <ArrowUpRight className="w-4 h-4 md:w-5 md:h-5 text-green-400" />
                                        : <ArrowDownRight className="w-4 h-4 md:w-5 md:h-5 text-red-400" />
                                    }
                                </div>

                                <div className="flex-1 min-w-0">
                                    <p className="text-white text-sm md:text-base font-medium truncate">{tx.description || tx.category}</p>
                                    <p className="text-xs md:text-sm text-gray-400 truncate">
                                        {tx.category} {tx.contact_name && `• ${tx.contact_name}`}
                                    </p>
                                </div>

                                <div className="text-right flex-shrink-0">
                                    <p className={`text-sm md:text-base font-semibold ${tx.type === 'income' ? 'text-green-400' : 'text-red-400'
                                        }`}>
                                        {tx.type === 'income' ? '+' : '-'}{formatAmount(tx.amount)}
                                    </p>
                                    <p className="text-xs text-gray-500">{formatDate(tx.date)}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Add Transaction Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-end md:items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-t-2xl md:rounded-2xl p-5 md:p-6 w-full md:max-w-md border-t md:border border-gray-700
                                    max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">Новая запись</h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-gray-700 rounded-lg transition"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* Type Selector */}
                            <div className="flex bg-gray-700 rounded-xl p-1">
                                {(['income', 'expense'] as const).map(type => (
                                    <button
                                        key={type}
                                        onClick={() => setFormData({ ...formData, type, category: '' })}
                                        className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${formData.type === type
                                            ? type === 'income'
                                                ? 'bg-green-500 text-white'
                                                : 'bg-red-500 text-white'
                                            : 'text-gray-400'
                                            }`}
                                    >
                                        {type === 'income' ? '💰 Доход' : '💳 Расход'}
                                    </button>
                                ))}
                            </div>

                            {/* Amount */}
                            <div>
                                <label className="text-sm text-gray-400 block mb-1">Сумма (₸)</label>
                                <input
                                    type="number"
                                    value={formData.amount}
                                    onChange={e => setFormData({ ...formData, amount: e.target.value })}
                                    placeholder="0"
                                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white text-lg font-semibold focus:outline-none 
                                               focus:ring-2 focus:ring-primary-500"
                                />
                            </div>

                            {/* Category */}
                            <div>
                                <label className="text-sm text-gray-400 block mb-1">Категория</label>
                                <div className="flex flex-wrap gap-2">
                                    {categories[formData.type].map(cat => (
                                        <button
                                            key={cat}
                                            onClick={() => setFormData({ ...formData, category: cat })}
                                            className={`px-3 py-1.5 rounded-lg text-sm transition ${formData.category === cat
                                                ? 'bg-primary-500 text-white'
                                                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                                }`}
                                        >
                                            {cat}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Description */}
                            <input
                                type="text"
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Описание"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none"
                            />

                            {/* Date */}
                            <input
                                type="date"
                                value={formData.date}
                                onChange={e => setFormData({ ...formData, date: e.target.value })}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white focus:outline-none"
                            />
                        </div>

                        {/* Actions */}
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 py-2 text-gray-400 hover:bg-gray-700 rounded-xl transition"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={saveTransaction}
                                disabled={!formData.amount || !formData.category}
                                className="flex-1 py-2 bg-primary-500 hover:bg-primary-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50"
                            >
                                Сохранить
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
