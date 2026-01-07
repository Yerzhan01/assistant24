import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import {
    TrendingUp,
    Download,
    PieChart,
    BarChart3,
    Loader2,
    ArrowUpRight,
    ArrowDownRight
} from 'lucide-react'

interface MonthlyData {
    month: string
    income: number
    expense: number
}

interface CategoryData {
    category: string
    amount: number
    percentage: number
    color: string
}

interface ReportSummary {
    total_income: number
    total_expense: number
    profit: number
    profit_margin: number
    top_income_category: string
    top_expense_category: string
}

export default function Reports() {
    const { token } = useAuth()
    const [loading, setLoading] = useState(true)
    const [period, setPeriod] = useState<'month' | 'quarter' | 'year'>('month')
    const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([])
    const [incomeCategories, setIncomeCategories] = useState<CategoryData[]>([])
    const [expenseCategories, setExpenseCategories] = useState<CategoryData[]>([])
    const [summary, setSummary] = useState<ReportSummary | null>(null)

    // Colors for charts
    const categoryColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
        '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'
    ]

    useEffect(() => {
        fetchReportData()
    }, [period])

    const fetchReportData = async () => {
        setLoading(true)
        try {
            const res = await fetch(`/api/v1/finance/reports?period=${period}`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                setMonthlyData(data.monthly || [])
                setIncomeCategories(data.income_categories || [])
                setExpenseCategories(data.expense_categories || [])
                setSummary(data.summary)
            }
        } catch (err) {
            console.error('Failed to fetch reports:', err)
            // Demo data
            setMonthlyData([
                { month: 'Янв', income: 500000, expense: 350000 },
                { month: 'Фев', income: 620000, expense: 400000 },
                { month: 'Мар', income: 580000, expense: 380000 },
                { month: 'Апр', income: 750000, expense: 420000 },
                { month: 'Май', income: 680000, expense: 450000 },
                { month: 'Июн', income: 820000, expense: 500000 },
            ])
            setIncomeCategories([
                { category: 'Продажи', amount: 2500000, percentage: 60, color: categoryColors[0] },
                { category: 'Услуги', amount: 1000000, percentage: 24, color: categoryColors[1] },
                { category: 'Другое', amount: 450000, percentage: 16, color: categoryColors[2] },
            ])
            setExpenseCategories([
                { category: 'Зарплата', amount: 1200000, percentage: 48, color: categoryColors[3] },
                { category: 'Аренда', amount: 600000, percentage: 24, color: categoryColors[4] },
                { category: 'Реклама', amount: 400000, percentage: 16, color: categoryColors[5] },
                { category: 'Другое', amount: 300000, percentage: 12, color: categoryColors[6] },
            ])
            setSummary({
                total_income: 3950000,
                total_expense: 2500000,
                profit: 1450000,
                profit_margin: 36.7,
                top_income_category: 'Продажи',
                top_expense_category: 'Зарплата'
            })
        } finally {
            setLoading(false)
        }
    }

    const formatAmount = (amount: number) => {
        if (amount >= 1000000) {
            return (amount / 1000000).toFixed(1) + 'M ₸'
        }
        return new Intl.NumberFormat('ru-RU').format(amount) + ' ₸'
    }

    const getMaxValue = () => {
        return Math.max(...monthlyData.map(d => Math.max(d.income, d.expense)))
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">📊 Отчёты</h1>
                    <p className="text-gray-400 mt-1">Аналитика доходов и расходов</p>
                </div>

                <div className="flex items-center gap-4">
                    {/* Period Selector */}
                    <div className="flex bg-gray-800 rounded-xl p-1">
                        {(['month', 'quarter', 'year'] as const).map(p => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${period === p
                                    ? 'bg-primary-500 text-white'
                                    : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                {p === 'month' ? 'Месяц' : p === 'quarter' ? 'Квартал' : 'Год'}
                            </button>
                        ))}
                    </div>

                    <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 
                                       text-white rounded-xl transition">
                        <Download className="w-4 h-4" />
                        Экспорт
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
            ) : (
                <>
                    {/* Summary Cards */}
                    {summary && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                                <div className="flex items-center gap-3 mb-2">
                                    <ArrowUpRight className="w-5 h-5 text-green-400" />
                                    <span className="text-gray-400 text-sm">Доходы</span>
                                </div>
                                <p className="text-2xl font-bold text-green-400">
                                    {formatAmount(summary.total_income)}
                                </p>
                                <p className="text-sm text-gray-500 mt-1">
                                    Топ: {summary.top_income_category}
                                </p>
                            </div>

                            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                                <div className="flex items-center gap-3 mb-2">
                                    <ArrowDownRight className="w-5 h-5 text-red-400" />
                                    <span className="text-gray-400 text-sm">Расходы</span>
                                </div>
                                <p className="text-2xl font-bold text-red-400">
                                    {formatAmount(summary.total_expense)}
                                </p>
                                <p className="text-sm text-gray-500 mt-1">
                                    Топ: {summary.top_expense_category}
                                </p>
                            </div>

                            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                                <div className="flex items-center gap-3 mb-2">
                                    <TrendingUp className="w-5 h-5 text-primary-400" />
                                    <span className="text-gray-400 text-sm">Прибыль</span>
                                </div>
                                <p className={`text-2xl font-bold ${summary.profit >= 0 ? 'text-green-400' : 'text-red-400'
                                    }`}>
                                    {formatAmount(summary.profit)}
                                </p>
                            </div>

                            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                                <div className="flex items-center gap-3 mb-2">
                                    <PieChart className="w-5 h-5 text-purple-400" />
                                    <span className="text-gray-400 text-sm">Рентабельность</span>
                                </div>
                                <p className="text-2xl font-bold text-white">
                                    {summary.profit_margin.toFixed(1)}%
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Charts Row */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Bar Chart - Monthly Comparison */}
                        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                            <div className="flex items-center gap-2 mb-6">
                                <BarChart3 className="w-5 h-5 text-primary-400" />
                                <h3 className="text-lg font-semibold text-white">Динамика по месяцам</h3>
                            </div>

                            <div className="space-y-4">
                                {monthlyData.map((data, index) => {
                                    const maxVal = getMaxValue()
                                    const incomeWidth = (data.income / maxVal) * 100
                                    const expenseWidth = (data.expense / maxVal) * 100

                                    return (
                                        <div key={index} className="space-y-2">
                                            <div className="flex items-center justify-between text-sm">
                                                <span className="text-gray-400 w-12">{data.month}</span>
                                                <div className="flex gap-4 text-xs">
                                                    <span className="text-green-400">+{formatAmount(data.income)}</span>
                                                    <span className="text-red-400">-{formatAmount(data.expense)}</span>
                                                </div>
                                            </div>
                                            <div className="space-y-1">
                                                <div
                                                    className="h-3 bg-green-500 rounded-full transition-all duration-500"
                                                    style={{ width: `${incomeWidth}%` }}
                                                />
                                                <div
                                                    className="h-3 bg-red-500 rounded-full transition-all duration-500"
                                                    style={{ width: `${expenseWidth}%` }}
                                                />
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>

                            {/* Legend */}
                            <div className="flex gap-6 mt-6 pt-4 border-t border-gray-700">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 bg-green-500 rounded-full" />
                                    <span className="text-sm text-gray-400">Доходы</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 bg-red-500 rounded-full" />
                                    <span className="text-sm text-gray-400">Расходы</span>
                                </div>
                            </div>
                        </div>

                        {/* Pie Charts - Categories */}
                        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                            <div className="flex items-center gap-2 mb-6">
                                <PieChart className="w-5 h-5 text-primary-400" />
                                <h3 className="text-lg font-semibold text-white">По категориям</h3>
                            </div>

                            <div className="grid grid-cols-2 gap-6">
                                {/* Income Categories */}
                                <div>
                                    <p className="text-sm text-gray-400 mb-3">💰 Доходы</p>
                                    <div className="space-y-3">
                                        {incomeCategories.map((cat, i) => (
                                            <div key={i}>
                                                <div className="flex justify-between text-sm mb-1">
                                                    <span className="text-white">{cat.category}</span>
                                                    <span className="text-gray-400">{cat.percentage}%</span>
                                                </div>
                                                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full transition-all duration-500"
                                                        style={{
                                                            width: `${cat.percentage}%`,
                                                            backgroundColor: cat.color
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Expense Categories */}
                                <div>
                                    <p className="text-sm text-gray-400 mb-3">💳 Расходы</p>
                                    <div className="space-y-3">
                                        {expenseCategories.map((cat, i) => (
                                            <div key={i}>
                                                <div className="flex justify-between text-sm mb-1">
                                                    <span className="text-white">{cat.category}</span>
                                                    <span className="text-gray-400">{cat.percentage}%</span>
                                                </div>
                                                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full transition-all duration-500"
                                                        style={{
                                                            width: `${cat.percentage}%`,
                                                            backgroundColor: cat.color
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Profit Trend */}
                    <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                        <h3 className="text-lg font-semibold text-white mb-4">📈 Прибыль по месяцам</h3>
                        <div className="flex items-end gap-4 h-40">
                            {monthlyData.map((data, index) => {
                                const profit = data.income - data.expense
                                const maxProfit = Math.max(...monthlyData.map(d => d.income - d.expense))
                                const height = (profit / maxProfit) * 100

                                return (
                                    <div key={index} className="flex-1 flex flex-col items-center">
                                        <div
                                            className={`w-full rounded-t-lg transition-all duration-500 ${profit >= 0 ? 'bg-green-500' : 'bg-red-500'
                                                }`}
                                            style={{ height: `${height}%`, minHeight: '8px' }}
                                        />
                                        <span className="text-xs text-gray-400 mt-2">{data.month}</span>
                                        <span className={`text-xs mt-1 ${profit >= 0 ? 'text-green-400' : 'text-red-400'
                                            }`}>
                                            {formatAmount(profit)}
                                        </span>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
