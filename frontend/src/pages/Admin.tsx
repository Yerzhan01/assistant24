import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import {
    Users,
    BarChart3,
    Settings,
    Activity,
    UserCheck,
    UserX,
    TrendingUp,
    Calendar,
    MessageSquare,
    DollarSign,
    Search,
    MoreVertical,
    ChevronLeft,
    ChevronRight,
    Loader2,
    RefreshCw,
    Smartphone,
    Plus,
    Copy,
    Check,
    Trash2,
    PieChart,
    Lock
} from 'lucide-react'

interface AdminUser {
    id: string
    email: string
    business_name: string
    created_at: string
    is_active: boolean
    telegram_connected: boolean
    whatsapp_connected: boolean
    last_activity?: string
    stats: {
        meetings: number
        tasks: number
        transactions: number
        messages: number
    }
}

interface AdminStats {
    total_users: number
    active_users: number
    new_users_today: number
    new_users_week: number
    total_meetings: number
    total_tasks: number
    total_transactions: number
    total_messages: number
}

interface WhatsAppInstance {
    id: string
    instance_id: string
    token: string
    created_at: string
    assigned_to?: string
    status: 'available' | 'assigned' | 'expired'
}

interface AdminTrace {
    id: string
    trace_id: string
    source: string
    user_message: string
    success: boolean
    error_message?: string
    total_duration_ms: number
    created_at: string
    steps: any[]
}

interface AdminUsage {
    total_cost_kzt: number
    total_tokens: number
    currency_rate: number
    breakdown: Array<{
        model: string
        requests: number
        prompt_tokens: number
        response_tokens: number
        total_tokens: number
        cost_usd: number
        cost_kzt: number
    }>
}

export default function Admin() {
    const { token } = useAuth()
    const [users, setUsers] = useState<AdminUser[]>([])
    const [stats, setStats] = useState<AdminStats | null>(null)
    const [instances, setInstances] = useState<WhatsAppInstance[]>([])
    const [traces, setTraces] = useState<AdminTrace[]>([])
    const [usage, setUsage] = useState<AdminUsage | null>(null)

    const [loading, setLoading] = useState(true)
    const [accessDenied, setAccessDenied] = useState(false)

    const [generatingInstance, setGeneratingInstance] = useState(false)
    const [copiedId, setCopiedId] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [currentPage, setCurrentPage] = useState(1)
    const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'whatsapp' | 'traces' | 'analytics'>('overview')
    const usersPerPage = 10

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        setLoading(true)
        setAccessDenied(false)
        try {
            // Fetch admin stats - Check auth first
            const statsRes = await fetch('/api/v1/admin/stats', {
                headers: { Authorization: `Bearer ${token}` }
            })

            if (statsRes.status === 403) {
                setAccessDenied(true)
                setLoading(false)
                return
            }

            if (statsRes.ok) {
                setStats(await statsRes.json())
            }

            // Fetch users list
            const usersRes = await fetch('/api/v1/admin/users', {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (usersRes.ok) {
                const data = await usersRes.json()
                setUsers(data.users || data || [])
            }

            // Fetch WhatsApp instances
            const instancesRes = await fetch('/api/v1/admin/whatsapp/instances', {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (instancesRes.ok) {
                const data = await instancesRes.json()
                setInstances(data.instances || data || [])
            }

            // Fetch Traces
            const tracesRes = await fetch('/api/v1/admin/traces/search?limit=20', {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (tracesRes.ok) {
                const data = await tracesRes.json()
                setTraces(data.traces || [])
            }

            // Fetch Usage Analytics
            const usageRes = await fetch('/api/v1/admin/usage', {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (usageRes.ok) {
                setUsage(await usageRes.json())
            }

        } catch (err) {
            console.error('Failed to fetch admin data:', err)
        } finally {
            setLoading(false)
        }
    }

    const generateInstance = async () => {
        setGeneratingInstance(true)
        try {
            const res = await fetch('/api/v1/admin/whatsapp/generate', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })
            if (res.ok) {
                const newInstance = await res.json()
                setInstances(prev => [newInstance, ...prev])
            } else {
                console.error('Failed to generate instance')
            }
        } catch (err) {
            console.error('Error generating instance:', err)
        } finally {
            setGeneratingInstance(false)
        }
    }

    const copyToClipboard = async (text: string, id: string) => {
        await navigator.clipboard.writeText(text)
        setCopiedId(id)
        setTimeout(() => setCopiedId(null), 2000)
    }

    const deleteInstance = async (instanceId: string) => {
        try {
            await fetch(`/api/v1/admin/whatsapp/instances/${instanceId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            })
            setInstances(prev => prev.filter(i => i.id !== instanceId))
        } catch (err) {
            console.error('Failed to delete instance:', err)
        }
    }

    const filteredUsers = users.filter(user =>
        user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.business_name.toLowerCase().includes(searchTerm.toLowerCase())
    )

    const paginatedUsers = filteredUsers.slice(
        (currentPage - 1) * usersPerPage,
        currentPage * usersPerPage
    )

    const totalPages = Math.ceil(filteredUsers.length / usersPerPage)

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const StatCard = ({ icon: Icon, label, value, change, color }: {
        icon: typeof Users; label: string; value: string | number; change?: string; color: string
    }) => (
        <div className="bg-gray-800 rounded-xl p-4 md:p-5 border border-gray-700">
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-gray-400 text-sm">{label}</p>
                    <p className="text-2xl md:text-3xl font-bold text-white mt-1">{value}</p>
                    {change && <p className="text-green-400 text-sm mt-1">{change}</p>}
                </div>
                <div className={`p-3 rounded-xl ${color}`}>
                    <Icon className="w-6 h-6 text-white" />
                </div>
            </div>
        </div>
    )

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
        )
    }

    if (accessDenied) {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
                <div className="bg-red-500/10 p-4 rounded-full mb-4">
                    <Lock className="w-12 h-12 text-red-500" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-2">Доступ запрещен</h1>
                <p className="text-gray-400 max-w-md">
                    У вас нет прав администратора для просмотра этой страницы.
                    Только пользователи с подтвержденным доступом могут управлять системой.
                </p>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl md:text-3xl font-bold text-white">🛡️ Админ-панель</h1>
                    <p className="text-gray-400">Управление системой, пользователями и мониторинг AI</p>
                </div>
                <button
                    onClick={fetchData}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 
                               text-white rounded-xl transition"
                >
                    <RefreshCw className="w-4 h-4" />
                    Обновить
                </button>
            </div>

            {/* Tabs */}
            <div className="flex flex-wrap bg-gray-800 rounded-xl p-1 w-fit gap-1">
                {[
                    { id: 'overview', label: 'Обзор', icon: BarChart3 },
                    { id: 'analytics', label: 'Аналитика & Затраты', icon: PieChart },
                    { id: 'users', label: 'Пользователи', icon: Users },
                    { id: 'whatsapp', label: 'WhatsApp', icon: Smartphone },
                    { id: 'traces', label: 'AI Логи', icon: Activity }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as typeof activeTab)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${activeTab === tab.id
                            ? 'bg-primary-500 text-white'
                            : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {activeTab === 'overview' && stats && (
                <>
                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <StatCard icon={Users} label="Всего пользователей" value={stats.total_users} color="bg-blue-500" />
                        <StatCard icon={UserCheck} label="Активных" value={stats.active_users} change="+5 сегодня" color="bg-green-500" />
                        <StatCard icon={TrendingUp} label="Новых за неделю" value={stats.new_users_week} color="bg-purple-500" />
                        <StatCard icon={Activity} label="Сегодня" value={stats.new_users_today} color="bg-orange-500" />
                    </div>

                    {/* Activity Stats */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <StatCard icon={Calendar} label="Всего встреч" value={stats.total_meetings} color="bg-indigo-500" />
                        <StatCard icon={Settings} label="Всего задач" value={stats.total_tasks} color="bg-cyan-500" />
                        <StatCard icon={DollarSign} label="Транзакций" value={stats.total_transactions} color="bg-emerald-500" />
                        <StatCard icon={MessageSquare} label="Сообщений" value={stats.total_messages} color="bg-pink-500" />
                    </div>
                </>
            )}

            {activeTab === 'analytics' && usage && (
                <div className="space-y-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                            <p className="text-gray-400 text-sm">Общие расходы</p>
                            <p className="text-3xl font-bold text-white mt-1">₸ {usage.total_cost_kzt.toLocaleString()}</p>
                            <p className="text-gray-500 text-xs mt-2">Курс: 1$ = {usage.currency_rate} ₸</p>
                        </div>
                        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                            <p className="text-gray-400 text-sm">Всего токенов</p>
                            <p className="text-3xl font-bold text-white mt-1">{(usage.total_tokens / 1000).toFixed(1)}k</p>
                            <p className="text-green-400 text-xs mt-2">Gemini Models</p>
                        </div>
                        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                            <p className="text-gray-400 text-sm">Всего запросов</p>
                            <p className="text-3xl font-bold text-white mt-1">
                                {usage.breakdown.reduce((sum, item) => sum + item.requests, 0)}
                            </p>
                            <p className="text-blue-400 text-xs mt-2">API Calls</p>
                        </div>
                    </div>

                    {/* Usage Table */}
                    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                        <div className="p-4 border-b border-gray-700">
                            <h3 className="text-lg font-semibold text-white">Детализация по моделям</h3>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-900">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Модель</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Запросы</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Входные токены</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Выходные токены</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Стоимость ($)</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Стоимость (₸)</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-700">
                                    {usage.breakdown.map((item, idx) => (
                                        <tr key={idx} className="hover:bg-gray-700/50 transition">
                                            <td className="px-4 py-4">
                                                <span className="font-mono text-sm text-primary-400">{item.model}</span>
                                            </td>
                                            <td className="px-4 py-4 text-white">{item.requests}</td>
                                            <td className="px-4 py-4 text-gray-400">{item.prompt_tokens.toLocaleString()}</td>
                                            <td className="px-4 py-4 text-gray-400">{item.response_tokens.toLocaleString()}</td>
                                            <td className="px-4 py-4 text-gray-400">${item.cost_usd.toFixed(4)}</td>
                                            <td className="px-4 py-4 font-bold text-white">₸ {item.cost_kzt.toFixed(2)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'users' && (
                <>
                    {/* Search */}
                    <div className="relative max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            placeholder="Поиск пользователей..."
                            className="w-full pl-11 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-xl
                                       text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                    </div>

                    {/* Users Table */}
                    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-900">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Пользователь</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Статус</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Интеграции</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Активность</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Регистрация</th>
                                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-400"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-700">
                                    {paginatedUsers.map(user => (
                                        <tr key={user.id} className="hover:bg-gray-700/50 transition">
                                            <td className="px-4 py-4">
                                                <div>
                                                    <p className="text-white font-medium">{user.business_name}</p>
                                                    <p className="text-gray-400 text-sm">{user.email}</p>
                                                </div>
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${user.is_active
                                                    ? 'bg-green-500/20 text-green-400'
                                                    : 'bg-red-500/20 text-red-400'
                                                    }`}>
                                                    {user.is_active ? <UserCheck className="w-3 h-3" /> : <UserX className="w-3 h-3" />}
                                                    {user.is_active ? 'Активен' : 'Неактивен'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4">
                                                <div className="flex gap-2">
                                                    {user.telegram_connected && (
                                                        <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">TG</span>
                                                    )}
                                                    {user.whatsapp_connected && (
                                                        <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">WA</span>
                                                    )}
                                                    {!user.telegram_connected && !user.whatsapp_connected && (
                                                        <span className="text-gray-500 text-xs">—</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-4 py-4 text-gray-400 text-sm">
                                                {user.stats.meetings} встреч, {user.stats.tasks} задач
                                            </td>
                                            <td className="px-4 py-4 text-gray-400 text-sm">
                                                {formatDate(user.created_at)}
                                            </td>
                                            <td className="px-4 py-4 text-right">
                                                <button className="p-2 hover:bg-gray-700 rounded-lg transition">
                                                    <MoreVertical className="w-4 h-4 text-gray-400" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700">
                                <p className="text-sm text-gray-400">
                                    Показано {(currentPage - 1) * usersPerPage + 1} - {Math.min(currentPage * usersPerPage, filteredUsers.length)} из {filteredUsers.length}
                                </p>
                                <div className="flex gap-1">
                                    <button
                                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                        disabled={currentPage === 1}
                                        className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition disabled:opacity-50"
                                    >
                                        <ChevronLeft className="w-4 h-4 text-white" />
                                    </button>
                                    <button
                                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                        disabled={currentPage === totalPages}
                                        className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition disabled:opacity-50"
                                    >
                                        <ChevronRight className="w-4 h-4 text-white" />
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </>
            )}

            {activeTab === 'whatsapp' && (
                <>
                    {/* Header */}
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-lg font-semibold text-white">WhatsApp Инстансы</h3>
                            <p className="text-gray-400 text-sm">Генерация и управление учётными данными</p>
                        </div>
                        <button
                            onClick={generateInstance}
                            disabled={generatingInstance}
                            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 
                                       text-white rounded-xl transition disabled:opacity-50"
                        >
                            {generatingInstance ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Plus className="w-4 h-4" />
                            )}
                            Создать инстанс
                        </button>
                    </div>

                    {/* Instances List */}
                    <div className="space-y-4">
                        {instances.length === 0 ? (
                            <div className="bg-gray-800 rounded-xl border border-gray-700 p-8 text-center">
                                <Smartphone className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                                <p className="text-gray-400">Нет созданных инстансов</p>
                                <p className="text-gray-500 text-sm mt-1">Нажмите "Создать инстанс" чтобы сгенерировать новые учётные данные</p>
                            </div>
                        ) : (
                            instances.map(instance => (
                                <div key={instance.id} className="bg-gray-800 rounded-xl border border-gray-700 p-4 md:p-5">
                                    <div className="flex items-start justify-between mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${instance.status === 'available'
                                                ? 'bg-green-500/20'
                                                : instance.status === 'assigned'
                                                    ? 'bg-blue-500/20'
                                                    : 'bg-red-500/20'}`}>
                                                <Smartphone className={`w-5 h-5 ${instance.status === 'available'
                                                    ? 'text-green-400'
                                                    : instance.status === 'assigned'
                                                        ? 'text-blue-400'
                                                        : 'text-red-400'}`} />
                                            </div>
                                            <div>
                                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${instance.status === 'available'
                                                    ? 'bg-green-500/20 text-green-400'
                                                    : instance.status === 'assigned'
                                                        ? 'bg-blue-500/20 text-blue-400'
                                                        : 'bg-red-500/20 text-red-400'}`}>
                                                    {instance.status === 'available' ? 'Доступен' : instance.status === 'assigned' ? 'Назначен' : 'Истёк'}
                                                </span>
                                                {instance.assigned_to && (
                                                    <p className="text-gray-400 text-sm mt-1">Назначен: {instance.assigned_to}</p>
                                                )}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => deleteInstance(instance.id)}
                                            className="p-2 hover:bg-red-500/20 rounded-lg transition text-gray-400 hover:text-red-400"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>

                                    <div className="grid md:grid-cols-2 gap-3">
                                        {/* Instance ID */}
                                        <div className="bg-gray-900 rounded-lg p-3">
                                            <p className="text-gray-400 text-xs mb-1">Instance ID</p>
                                            <div className="flex items-center gap-2">
                                                <code className="text-white text-sm flex-1 truncate">{instance.instance_id}</code>
                                                <button
                                                    onClick={() => copyToClipboard(instance.instance_id, `id-${instance.id}`)}
                                                    className="p-1.5 hover:bg-gray-700 rounded transition"
                                                >
                                                    {copiedId === `id-${instance.id}` ? (
                                                        <Check className="w-4 h-4 text-green-400" />
                                                    ) : (
                                                        <Copy className="w-4 h-4 text-gray-400" />
                                                    )}
                                                </button>
                                            </div>
                                        </div>

                                        {/* Token */}
                                        <div className="bg-gray-900 rounded-lg p-3">
                                            <p className="text-gray-400 text-xs mb-1">API Token</p>
                                            <div className="flex items-center gap-2">
                                                <code className="text-white text-sm flex-1 truncate">{instance.token}</code>
                                                <button
                                                    onClick={() => copyToClipboard(instance.token, `token-${instance.id}`)}
                                                    className="p-1.5 hover:bg-gray-700 rounded transition"
                                                >
                                                    {copiedId === `token-${instance.id}` ? (
                                                        <Check className="w-4 h-4 text-green-400" />
                                                    ) : (
                                                        <Copy className="w-4 h-4 text-gray-400" />
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-700">
                                        <span className="text-gray-500 text-xs">
                                            Создан: {formatDate(instance.created_at)}
                                        </span>
                                        <button
                                            onClick={() => copyToClipboard(`Instance ID: ${instance.instance_id}\nAPI Token: ${instance.token}`, `all-${instance.id}`)}
                                            className="text-sm text-primary-400 hover:text-primary-300 transition"
                                        >
                                            {copiedId === `all-${instance.id}` ? 'Скопировано!' : 'Копировать всё'}
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </>
            )}

            {activeTab === 'traces' && (
                <div className="space-y-4">
                    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                        <div className="p-4 border-b border-gray-700">
                            <h3 className="text-lg font-semibold text-white">Журнал работы AI</h3>
                            <p className="text-gray-400 text-sm">История запросов, ошибок и действий агентов</p>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-900">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">ID / Время</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Источник</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Запрос</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Статус</th>
                                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Длительность</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-700">
                                    {traces.map(trace => (
                                        <tr key={trace.id} className="hover:bg-gray-700/50 transition">
                                            <td className="px-4 py-4">
                                                <div className="font-mono text-xs text-primary-400 mb-1">{trace.trace_id}</div>
                                                <div className="text-gray-400 text-xs">{formatDate(trace.created_at)}</div>
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className="px-2 py-1 bg-gray-700 rounded text-xs text-white capitalize">
                                                    {trace.source}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4">
                                                <p className="text-white text-sm line-clamp-2" title={trace.user_message}>
                                                    {trace.user_message}
                                                </p>
                                                {trace.error_message && (
                                                    <p className="text-red-400 text-xs mt-1">{trace.error_message}</p>
                                                )}
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className={`px-2 py-1 rounded text-xs ${trace.success ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                    {trace.success ? 'Успех' : 'Ошибка'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4 text-gray-400 text-sm">
                                                {trace.total_duration_ms} ms
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {traces.length === 0 && (
                                <div className="p-8 text-center text-gray-500">
                                    Нет записей в журнале
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
