import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { ContractsApi } from '../api/client'
import {
    FileText,
    Plus,
    X,
    Calendar,
    DollarSign,
    Building2,
    Loader2,
    Trash2,
    Edit,
    CheckCircle,
    AlertTriangle,
    Search
} from 'lucide-react'

interface Contract {
    id: string
    title: string
    counterparty: string
    amount: number
    currency: string
    start_date: string
    end_date?: string
    status: 'draft' | 'active' | 'completed' | 'cancelled'
    description?: string
    created_at: string
}

export default function Contracts() {
    const { } = useAuth()
    const [contracts, setContracts] = useState<Contract[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [selectedContract, setSelectedContract] = useState<Contract | null>(null)
    const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'draft'>('all')
    const [searchQuery, setSearchQuery] = useState('')

    const [formData, setFormData] = useState({
        title: '',
        counterparty: '',
        amount: 0,
        currency: 'KZT',
        start_date: '',
        end_date: '',
        status: 'active' as Contract['status'],
        description: ''
    })

    const statusConfig = {
        draft: { label: 'Черновик', color: 'bg-gray-500', icon: FileText },
        active: { label: 'Активный', color: 'bg-green-500', icon: CheckCircle },
        completed: { label: 'Завершён', color: 'bg-blue-500', icon: CheckCircle },
        cancelled: { label: 'Отменён', color: 'bg-red-500', icon: AlertTriangle }
    }

    useEffect(() => {
        fetchContracts()
    }, [])

    const fetchContracts = async () => {
        setLoading(true)
        try {
            const res = await ContractsApi.getAll()
            console.log('📦 Contracts API Response:', res.data)
            const contractsData = Array.isArray(res.data) ? res.data : (res.data.contracts || [])
            setContracts(contractsData)
        } catch (err) {
            console.error('Failed to fetch contracts:', err)
        } finally {
            setLoading(false)
        }
    }

    const saveContract = async () => {
        try {
            let res;
            if (selectedContract) {
                res = await ContractsApi.update(selectedContract.id, formData)
            } else {
                res = await ContractsApi.create(formData)
            }

            if (res.status === 200 || res.status === 201) {
                setShowModal(false)
                resetForm()
                fetchContracts()
            }
        } catch (err) {
            console.error('Failed to save contract:', err)
        }
    }

    const deleteContract = async (id: string) => {
        try {
            await ContractsApi.delete(id)
            fetchContracts()
        } catch (err) {
            console.error('Failed to delete contract:', err)
        }
    }

    const openEditModal = (contract: Contract) => {
        setSelectedContract(contract)
        setFormData({
            title: contract.title,
            counterparty: contract.counterparty,
            amount: contract.amount,
            currency: contract.currency,
            start_date: contract.start_date,
            end_date: contract.end_date || '',
            status: contract.status,
            description: contract.description || ''
        })
        setShowModal(true)
    }

    const openNewModal = () => {
        setSelectedContract(null)
        resetForm()
        setShowModal(true)
    }

    const resetForm = () => {
        setFormData({
            title: '',
            counterparty: '',
            amount: 0,
            currency: 'KZT',
            start_date: new Date().toISOString().split('T')[0],
            end_date: '',
            status: 'active',
            description: ''
        })
    }

    const formatAmount = (amount: number, currency: string) => {
        if (currency === 'KZT') {
            return new Intl.NumberFormat('ru-RU').format(amount) + ' ₸'
        }
        return new Intl.NumberFormat('ru-RU', { style: 'currency', currency }).format(amount)
    }

    const filteredContracts = contracts
        .filter(c => {
            if (filter !== 'all' && c.status !== filter) return false
            if (searchQuery) {
                const query = searchQuery.toLowerCase()
                return c.title.toLowerCase().includes(query) ||
                    c.counterparty.toLowerCase().includes(query)
            }
            return true
        })
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    const totalActive = contracts
        .filter(c => c.status === 'active')
        .reduce((sum, c) => sum + c.amount, 0)

    const counts = {
        all: contracts.length,
        active: contracts.filter(c => c.status === 'active').length,
        completed: contracts.filter(c => c.status === 'completed').length,
        draft: contracts.filter(c => c.status === 'draft').length
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">📄 Договоры</h1>
                    <p className="text-gray-400 mt-1">Учёт договоров и ЭСФ</p>
                </div>

                <button
                    onClick={openNewModal}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                               text-white font-medium rounded-xl transition"
                >
                    <Plus className="w-5 h-5" />
                    Новый договор
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-green-500/20 rounded-xl flex items-center justify-center">
                            <CheckCircle className="w-5 h-5 text-green-400" />
                        </div>
                        <span className="text-gray-400">Активных договоров</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{counts.active}</p>
                </div>

                <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-primary-500/20 rounded-xl flex items-center justify-center">
                            <DollarSign className="w-5 h-5 text-primary-400" />
                        </div>
                        <span className="text-gray-400">Сумма активных</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{formatAmount(totalActive, 'KZT')}</p>
                </div>

                <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-blue-500/20 rounded-xl flex items-center justify-center">
                            <FileText className="w-5 h-5 text-blue-400" />
                        </div>
                        <span className="text-gray-400">Всего договоров</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{counts.all}</p>
                </div>
            </div>

            {/* Filters & Search */}
            <div className="flex flex-wrap gap-4 items-center">
                <div className="flex gap-2">
                    {(['all', 'active', 'completed', 'draft'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition ${filter === f
                                ? 'bg-primary-500 text-white'
                                : 'bg-gray-800 text-gray-400 hover:text-white'
                                }`}
                        >
                            {f === 'all' && `Все (${counts.all})`}
                            {f === 'active' && `Активные (${counts.active})`}
                            {f === 'completed' && `Завершённые (${counts.completed})`}
                            {f === 'draft' && `Черновики (${counts.draft})`}
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
                            placeholder="Поиск по названию или контрагенту..."
                            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-xl
                                       text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                    </div>
                </div>
            </div>

            {/* Contracts List */}
            <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                    </div>
                ) : filteredContracts.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <FileText className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                        <p className="text-lg">Нет договоров</p>
                        <p className="text-sm mt-1">Создайте первый договор</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-700">
                        {filteredContracts.map(contract => {
                            const status = statusConfig[contract.status]
                            const StatusIcon = status.icon

                            return (
                                <div
                                    key={contract.id}
                                    className="flex items-center gap-4 p-4 hover:bg-gray-700/50 transition group"
                                >
                                    {/* Status */}
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${status.color} bg-opacity-20`}>
                                        <StatusIcon className={`w-5 h-5 text-white`} />
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <h3 className="font-medium text-white truncate">
                                                {contract.title}
                                            </h3>
                                            <span className={`px-2 py-0.5 rounded text-xs ${status.color} text-white`}>
                                                {status.label}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-400">
                                            <span className="flex items-center gap-1">
                                                <Building2 className="w-4 h-4" />
                                                {contract.counterparty}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Calendar className="w-4 h-4" />
                                                {new Date(contract.start_date).toLocaleDateString('ru-RU')}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Amount */}
                                    <div className="text-right">
                                        <p className="font-semibold text-white">
                                            {formatAmount(contract.amount, contract.currency)}
                                        </p>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                                        <button
                                            onClick={() => openEditModal(contract)}
                                            className="p-2 hover:bg-gray-600 rounded-lg transition"
                                        >
                                            <Edit className="w-4 h-4 text-gray-400" />
                                        </button>
                                        <button
                                            onClick={() => deleteContract(contract.id)}
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
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-lg border border-gray-700 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">
                                {selectedContract ? 'Редактировать договор' : 'Новый договор'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-gray-700 rounded-lg transition"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <input
                                type="text"
                                value={formData.title}
                                onChange={e => setFormData({ ...formData, title: e.target.value })}
                                placeholder="Название договора"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none focus:ring-2
                                           focus:ring-primary-500"
                            />

                            <div className="flex items-center gap-3">
                                <Building2 className="w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    value={formData.counterparty}
                                    onChange={e => setFormData({ ...formData, counterparty: e.target.value })}
                                    placeholder="Контрагент (ТОО, ИП...)"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            {/* Amount */}
                            <div className="flex gap-3">
                                <div className="flex-1">
                                    <label className="text-sm text-gray-400 block mb-2">Сумма</label>
                                    <div className="flex items-center gap-2">
                                        <DollarSign className="w-5 h-5 text-gray-400" />
                                        <input
                                            type="number"
                                            value={formData.amount}
                                            onChange={e => setFormData({ ...formData, amount: Number(e.target.value) })}
                                            className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                       text-white focus:outline-none"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="text-sm text-gray-400 block mb-2">Валюта</label>
                                    <select
                                        value={formData.currency}
                                        onChange={e => setFormData({ ...formData, currency: e.target.value })}
                                        className="px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                   text-white focus:outline-none"
                                    >
                                        <option value="KZT">₸ KZT</option>
                                        <option value="USD">$ USD</option>
                                        <option value="RUB">₽ RUB</option>
                                    </select>
                                </div>
                            </div>

                            {/* Dates */}
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm text-gray-400 block mb-2">Дата начала</label>
                                    <input
                                        type="date"
                                        value={formData.start_date}
                                        onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                                        className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                   text-white focus:outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm text-gray-400 block mb-2">Дата окончания</label>
                                    <input
                                        type="date"
                                        value={formData.end_date}
                                        onChange={e => setFormData({ ...formData, end_date: e.target.value })}
                                        className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                   text-white focus:outline-none"
                                    />
                                </div>
                            </div>

                            {/* Status */}
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Статус</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {Object.entries(statusConfig).map(([key, config]) => (
                                        <button
                                            key={key}
                                            onClick={() => setFormData({ ...formData, status: key as Contract['status'] })}
                                            className={`py-2 rounded-lg text-sm font-medium transition ${formData.status === key
                                                ? `${config.color} text-white`
                                                : 'bg-gray-700 text-gray-400'
                                                }`}
                                        >
                                            {config.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <textarea
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Описание..."
                                rows={3}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none resize-none"
                            />
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 py-2 text-gray-400 hover:bg-gray-700 rounded-xl transition"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={saveContract}
                                disabled={!formData.title || !formData.counterparty}
                                className="flex-1 py-2 bg-primary-500 hover:bg-primary-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50"
                            >
                                {selectedContract ? 'Сохранить' : 'Создать'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
