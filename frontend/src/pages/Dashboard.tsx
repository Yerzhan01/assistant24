import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { FinanceApi, ContractsApi, CalendarApi, TasksApi, InvoicesApi } from '../api/client'
import {
    TrendingUp,
    TrendingDown,
    Calendar,
    FileText,
    MessageCircle,
    Send,
    AlertTriangle,
    CheckCircle,
    Clock
} from 'lucide-react'
import Onboarding from '../components/Onboarding'
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from 'recharts'

export default function Dashboard() {
    const { t, tenant } = useAuth()
    const navigate = useNavigate()
    const [financeData, setFinanceData] = useState({ income: 0, expense: 0 })
    const [counts, setCounts] = useState({ meetings: 0, contracts: 0 })
    const [chartData, setChartData] = useState<any[]>([])
    const [deadlines, setDeadlines] = useState<any[]>([])
    const [activity, setActivity] = useState<any[]>([])

    useEffect(() => {
        const fetchData = async () => {
            try {
                // 1. Finance Summary & Chart
                const resFinance = await FinanceApi.getSummary()
                setFinanceData({
                    income: resFinance.data.total_income || 0,
                    expense: resFinance.data.total_expense || 0
                })

                const resReports = await FinanceApi.getReports('month')
                if (resReports.data && resReports.data.monthly) {
                    setChartData(resReports.data.monthly)
                }

                // 2. Contracts
                const resContracts = await ContractsApi.getAll()
                const contracts = resContracts.data.contracts || []
                const activeContracts = contracts.filter((c: any) => c.status === 'active').length

                // 3. Meetings
                const today = new Date().toISOString().split('T')[0]
                const resEvents = await CalendarApi.getEvents(today, today)
                const todayMeetings = (resEvents.data.events || []).length

                setCounts({
                    contracts: activeContracts,
                    meetings: todayMeetings
                })

                // 4. Deadlines (Overdue Tasks & Invoices)
                const resTasks = await TasksApi.getAll()
                const tasks = resTasks.data.tasks || []
                const overdueTasks = tasks.filter((t: any) => new Date(t.deadline) < new Date() && t.status !== 'done')

                const resInvoices = await InvoicesApi.getAll()
                const invoices = resInvoices.data.invoices || []
                const overdueInvoices = invoices.filter((i: any) => i.status === 'overdue')

                setDeadlines([
                    ...overdueTasks.map((t: any) => ({ type: 'task', title: t.title, date: t.deadline })),
                    ...overdueInvoices.map((i: any) => ({ type: 'invoice', title: `Счет: ${i.debtor_name}`, date: i.due_date }))
                ])

                // 5. Activity Feed
                const recentActivity = [
                    ...contracts.slice(0, 3).map((c: any) => ({
                        type: 'contract',
                        title: `Договор с ${c.company_name}`,
                        date: c.created_at,
                        icon: FileText,
                        color: 'text-purple-500 bg-purple-500/10'
                    })),
                    ...tasks.slice(0, 3).map((t: any) => ({
                        type: 'task',
                        title: `Задача: ${t.title}`,
                        date: t.created_at,
                        icon: CheckCircle,
                        color: 'text-green-500 bg-green-500/10'
                    })),
                    ...invoices.slice(0, 3).map((i: any) => ({
                        type: 'invoice',
                        title: `Счет для ${i.debtor_name}`,
                        date: i.created_at,
                        icon: TrendingUp,
                        color: 'text-blue-500 bg-blue-500/10'
                    }))
                ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).slice(0, 5)

                setActivity(recentActivity)

            } catch (err) {
                console.error('Failed to fetch dashboard data:', err)
            }
        }
        fetchData()
    }, [])

    const formatAmount = (amount: number) => {
        return new Intl.NumberFormat('ru-RU').format(amount) + ' ₸'
    }

    const stats = [
        {
            label: t('dashboard.stats.income'),
            value: formatAmount(financeData.income),
            icon: TrendingUp,
            color: 'bg-green-500',
            change: '+0%'
        },
        {
            label: t('dashboard.stats.expenses'),
            value: formatAmount(financeData.expense),
            icon: TrendingDown,
            color: 'bg-red-500',
            change: '0%'
        },
        {
            label: t('dashboard.stats.meetings'),
            value: counts.meetings.toString(),
            icon: Calendar,
            color: 'bg-blue-500',
            change: 'Сегодня'
        },
        {
            label: t('dashboard.stats.contracts'),
            value: counts.contracts.toString(),
            icon: FileText,
            color: 'bg-purple-500',
            change: 'Активных'
        },
    ]

    const quickActions = [
        { icon: '💰', label: 'Доход', action: () => navigate('/dashboard/finance') },
        { icon: '💸', label: 'Долги', action: () => navigate('/dashboard/invoices') },
        { icon: '📅', label: 'Встреча', action: () => navigate('/dashboard/calendar') },
        { icon: '✅', label: 'Задача', action: () => navigate('/dashboard/tasks') },
        { icon: '💬', label: 'Чат', action: () => navigate('/dashboard/chat') },
    ]

    return (
        <>
            <Onboarding />
            <div className="space-y-4 md:space-y-6 pb-10">
                {/* Welcome Header */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h1 className="text-xl md:text-2xl lg:text-3xl font-bold text-white">
                            {t('dashboard.welcome')}, {tenant?.business_name || 'Пользователь'}! 👋
                        </h1>
                        <p className="text-gray-400 mt-1 text-sm md:text-base">
                            {t('app.tagline')}
                        </p>
                    </div>
                </div>

                {/* Deadlines Widget (Conditional) */}
                {deadlines.length > 0 && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-3">
                            <AlertTriangle className="w-5 h-5 text-red-500" />
                            <h3 className="font-semibold text-white">Горящие сроки ({deadlines.length})</h3>
                        </div>
                        <div className="space-y-2">
                            {deadlines.slice(0, 3).map((item, idx) => (
                                <div key={idx} className="flex items-center justify-between text-sm bg-gray-800/50 p-2 rounded-lg">
                                    <span className="text-gray-200">{item.title}</span>
                                    <span className="text-red-400 font-mono text-xs">
                                        {new Date(item.date).toLocaleDateString()}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Stats Grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
                    {stats.map((stat, index) => (
                        <div
                            key={index}
                            className="bg-gray-800 rounded-xl md:rounded-2xl p-3 md:p-4 lg:p-5 border border-gray-700 hover:border-gray-600 transition-colors"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex-1 min-w-0">
                                    <p className="text-gray-400 text-xs md:text-sm truncate">{stat.label}</p>
                                    <p className="text-lg md:text-xl lg:text-2xl font-bold text-white mt-0.5">{stat.value}</p>
                                    <p className="text-gray-500 text-xs mt-0.5 hidden md:block">{stat.change}</p>
                                </div>
                                <div className={`${stat.color} p-2 md:p-3 rounded-lg md:rounded-xl flex-shrink-0`}>
                                    <stat.icon className="w-4 h-4 md:w-5 md:h-5 text-white" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Finance Chart */}
                    <div className="lg:col-span-2 bg-gray-800 rounded-xl p-4 border border-gray-700">
                        <h3 className="text-lg font-semibold text-white mb-4">Динамика финансов</h3>
                        <div className="h-64 md:h-80 w-full">
                            {chartData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={chartData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                        <XAxis dataKey="month" stroke="#9CA3AF" />
                                        <YAxis stroke="#9CA3AF" />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#fff' }}
                                            formatter={(value: any) => new Intl.NumberFormat('ru-RU').format(value)}
                                        />
                                        <Legend />
                                        <Bar dataKey="income" name="Доходы" fill="#10B981" radius={[4, 4, 0, 0]} />
                                        <Bar dataKey="expense" name="Расходы" fill="#EF4444" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="h-full flex items-center justify-center text-gray-400">
                                    Нет данных для отображения
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Activity Feed */}
                    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                        <h3 className="text-lg font-semibold text-white mb-4">Активность</h3>
                        <div className="space-y-4">
                            {activity.length > 0 ? (
                                activity.map((item, idx) => (
                                    <div key={idx} className="flex items-start gap-3">
                                        <div className={`p-2 rounded-lg ${item.color}`}>
                                            <item.icon className="w-4 h-4" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-white truncate">{item.title}</p>
                                            <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                                                <Clock className="w-3 h-3" />
                                                {new Date(item.date).toLocaleDateString()}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p className="text-gray-400 text-sm text-center py-4">Нет недавней активности</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Quick Actions & Status */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                        <h2 className="text-base md:text-lg font-semibold text-white mb-3">{t('dashboard.quickActions')}</h2>
                        <div className="grid grid-cols-5 gap-2">
                            {quickActions.map((item, index) => (
                                <button
                                    key={index}
                                    onClick={item.action}
                                    className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-center"
                                >
                                    <span className="text-xl block">{item.icon}</span>
                                    <span className="text-xs text-gray-300 mt-1 block truncate">{item.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Statuses */}
                    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex flex-col justify-center gap-3">
                        <div className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                                    <Send className="w-4 h-4 text-white" />
                                </div>
                                <span className="text-white font-medium">Telegram</span>
                            </div>
                            <span className={`text-xs px-2 py-1 rounded-full ${tenant?.telegram_connected ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'
                                }`}>
                                {tenant?.telegram_connected ? 'Подключен' : 'Отключен'}
                            </span>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                                    <MessageCircle className="w-4 h-4 text-white" />
                                </div>
                                <span className="text-white font-medium">WhatsApp</span>
                            </div>
                            <span className={`text-xs px-2 py-1 rounded-full ${tenant?.whatsapp_connected ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'
                                }`}>
                                {tenant?.whatsapp_connected ? 'Подключен' : 'Отключен'}
                            </span>
                        </div>
                    </div>
                </div>

            </div>
        </>
    )
}
