import { useState, useEffect } from 'react'
import { InvoicesApi } from '../api/client'
import {
    Wallet,
    Plus,
    X,
    Loader2,
    Trash2,
    Edit,
    CheckCircle,
    AlertTriangle,
    Search,
    ArrowUpRight
} from 'lucide-react'

interface Invoice {
    id: string
    debtor_name: string
    amount: number
    currency: string
    description: string
    due_date: string
    status: 'sent' | 'paid' | 'overdue' | 'cancelled'
    created_at: string
    days_overdue: number
}

export default function Invoices() {
    const [invoices, setInvoices] = useState<Invoice[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null)
    const [filter, setFilter] = useState<'all' | 'active' | 'overdue' | 'paid'>('all')
    const [searchQuery, setSearchQuery] = useState('')

    const [formData, setFormData] = useState({
        debtor_name: '',
        amount: 0,
        currency: 'KZT',
        description: '',
        due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        status: 'sent'
    })

    useEffect(() => {
        fetchInvoices()
    }, [])

    const fetchInvoices = async () => {
        setLoading(true)
        try {
            const res = await InvoicesApi.getAll()
            console.log('📦 Invoices API Response:', res.data)
            const invoicesData = Array.isArray(res.data) ? res.data : (res.data.invoices || [])
            setInvoices(invoicesData)
        } catch (err) {
            console.error('Failed to fetch invoices:', err)
        } finally {
            setLoading(false)
        }
    }

    const saveInvoice = async () => {
        try {
            let res;
            if (selectedInvoice) {
                res = await InvoicesApi.update(selectedInvoice.id, formData)
            } else {
                res = await InvoicesApi.create(formData)
            }

            if (res.status === 200 || res.status === 201) {
                setShowModal(false)
                resetForm()
                fetchInvoices()
            }
        } catch (err) {
            console.error('Failed to save invoice:', err)
        }
    }

    const deleteInvoice = async (id: string) => {
        try {
            await InvoicesApi.delete(id)
            fetchInvoices()
        } catch (err) {
            console.error('Failed to delete invoice:', err)
        }
    }

    const openEditModal = (invoice: Invoice) => {
        setSelectedInvoice(invoice)
        setFormData({
            debtor_name: invoice.debtor_name,
            amount: invoice.amount,
            currency: invoice.currency,
            description: invoice.description,
            due_date: new Date(invoice.due_date).toISOString().split('T')[0],
            status: invoice.status
        })
        setShowModal(true)
    }

    const openNewModal = () => {
        setSelectedInvoice(null)
        resetForm()
        setShowModal(true)
    }

    const resetForm = () => {
        setFormData({
            debtor_name: '',
            amount: 0,
            currency: 'KZT',
            description: '',
            due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            status: 'sent'
        })
    }

    const formatAmount = (amount: number, currency: string) => {
        if (currency === 'KZT') {
            return new Intl.NumberFormat('ru-RU').format(amount) + ' ₸'
        }
        return new Intl.NumberFormat('ru-RU', { style: 'currency', currency }).format(amount)
    }

    const filteredInvoices = invoices
        .filter(i => {
            if (filter === 'active') return i.status === 'sent' && i.days_overdue <= 0
            if (filter === 'overdue') return i.status === 'overdue' || (i.status === 'sent' && i.days_overdue > 0)
            if (filter === 'paid') return i.status === 'paid'
            return true
        })
        .filter(i => {
            if (!searchQuery) return true
            return i.debtor_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                i.description.toLowerCase().includes(searchQuery.toLowerCase())
        })

    const totalOwed = invoices
        .filter(i => i.status !== 'paid' && i.status !== 'cancelled')
        .reduce((sum, i) => sum + i.amount, 0)

    const overdueAmount = invoices
        .filter(i => (i.status === 'overdue' || (i.status === 'sent' && i.days_overdue > 0)))
        .reduce((sum, i) => sum + i.amount, 0)

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">💰 Дебиторка</h1>
                    <p className="text-gray-400 mt-1">Учёт долгов и счетов</p>
                </div>
                <button
                    onClick={openNewModal}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                               text-white font-medium rounded-xl transition"
                >
                    <Plus className="w-5 h-5" />
                    Записать долг
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-primary-500/20 rounded-xl flex items-center justify-center">
                            <Wallet className="w-5 h-5 text-primary-400" />
                        </div>
                        <span className="text-gray-400">Общий долг вам</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{formatAmount(totalOwed, 'KZT')}</p>
                </div>

                <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-red-500/20 rounded-xl flex items-center justify-center">
                            <AlertTriangle className="w-5 h-5 text-red-400" />
                        </div>
                        <span className="text-gray-400">Просрочено</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{formatAmount(overdueAmount, 'KZT')}</p>
                </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-4 items-center">
                <div className="flex gap-2">
                    {[
                        { id: 'all', label: 'Все' },
                        { id: 'active', label: 'Активные' },
                        { id: 'overdue', label: 'Просроченные' },
                        { id: 'paid', label: 'Оплаченные' }
                    ].map(f => (
                        <button
                            key={f.id}
                            onClick={() => setFilter(f.id as any)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition ${filter === f.id
                                ? 'bg-primary-500 text-white'
                                : 'bg-gray-800 text-gray-400 hover:text-white'
                                }`}
                        >
                            {f.label}
                        </button>
                    ))}
                </div>

                <div className="flex-1 min-w-[200px]">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            placeholder="Поиск..."
                            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-xl
                                       text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                    </div>
                </div>
            </div>

            {/* List */}
            <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                    </div>
                ) : filteredInvoices.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <Wallet className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                        <p className="text-lg">Нет записей</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-700">
                        {filteredInvoices.map(invoice => {
                            const isOverdue = invoice.status === 'overdue' || (invoice.status === 'sent' && invoice.days_overdue > 0)
                            const isPaid = invoice.status === 'paid'

                            return (
                                <div
                                    key={invoice.id}
                                    className="flex items-center gap-4 p-4 hover:bg-gray-700/50 transition group"
                                >
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isPaid ? 'bg-green-500/20' : isOverdue ? 'bg-red-500/20' : 'bg-blue-500/20'
                                        }`}>
                                        {isPaid ? <CheckCircle className="w-5 h-5 text-green-400" /> :
                                            isOverdue ? <AlertTriangle className="w-5 h-5 text-red-400" /> :
                                                <ArrowUpRight className="w-5 h-5 text-blue-400" />}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <h3 className="font-medium text-white truncate">
                                                {invoice.debtor_name}
                                            </h3>
                                            {isOverdue && (
                                                <span className="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400">
                                                    Просрочено {invoice.days_overdue} дн.
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-400">
                                            <span>{invoice.description}</span>
                                            <span>
                                                До: {new Date(invoice.due_date).toLocaleDateString('ru-RU')}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="text-right">
                                        <p className={`font-semibold ${isPaid ? 'text-green-400' : 'text-white'}`}>
                                            {formatAmount(invoice.amount, invoice.currency)}
                                        </p>
                                    </div>

                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                                        <button
                                            onClick={() => openEditModal(invoice)}
                                            className="p-2 hover:bg-gray-600 rounded-lg transition"
                                        >
                                            <Edit className="w-4 h-4 text-gray-400" />
                                        </button>
                                        <button
                                            onClick={() => deleteInvoice(invoice.id)}
                                            className="p-2 hover:bg-red-500/20 rounded-lg transition"
                                        >
                                            <Trash2 className="w-4 h-4 text-red-400" />
                                        </button>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-lg border border-gray-700">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">
                                {selectedInvoice ? 'Редактировать долг' : 'Новая запись'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-gray-700 rounded-lg transition"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Должник</label>
                                <input
                                    type="text"
                                    value={formData.debtor_name}
                                    onChange={e => setFormData({ ...formData, debtor_name: e.target.value })}
                                    placeholder="Имя или название компании"
                                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                                />
                            </div>

                            <div className="flex gap-3">
                                <div className="flex-1">
                                    <label className="text-sm text-gray-400 block mb-2">Сумма</label>
                                    <input
                                        type="number"
                                        value={formData.amount}
                                        onChange={e => setFormData({ ...formData, amount: Number(e.target.value) })}
                                        className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                   text-white focus:outline-none"
                                    />
                                </div>
                                <div className="w-1/3">
                                    <label className="text-sm text-gray-400 block mb-2">Валюта</label>
                                    <select
                                        value={formData.currency}
                                        onChange={e => setFormData({ ...formData, currency: e.target.value })}
                                        className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                   text-white focus:outline-none"
                                    >
                                        <option value="KZT">KZT</option>
                                        <option value="USD">USD</option>
                                        <option value="RUB">RUB</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Описание</label>
                                <input
                                    type="text"
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="За что?"
                                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Срок возврата</label>
                                <input
                                    type="date"
                                    value={formData.due_date}
                                    onChange={e => setFormData({ ...formData, due_date: e.target.value })}
                                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white focus:outline-none"
                                />
                            </div>

                            {selectedInvoice && (
                                <div>
                                    <label className="text-sm text-gray-400 block mb-2">Статус</label>
                                    <select
                                        value={formData.status}
                                        onChange={e => setFormData({ ...formData, status: e.target.value })}
                                        className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                   text-white focus:outline-none"
                                    >
                                        <option value="sent">Активен</option>
                                        <option value="paid">Оплачен</option>
                                        <option value="cancelled">Отменен</option>
                                    </select>
                                </div>
                            )}

                            <button
                                onClick={saveInvoice}
                                disabled={!formData.debtor_name || !formData.amount}
                                className="w-full py-3 bg-primary-500 hover:bg-primary-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50 mt-4"
                            >
                                {selectedInvoice ? 'Сохранить' : 'Создать запись'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
