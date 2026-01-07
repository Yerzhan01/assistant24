import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
    Bot,
    MessageSquare,
    Smartphone,
    Calendar,
    Wallet,
    CheckCircle2,
    ArrowRight,
    ArrowLeft,
    Sparkles,
    ExternalLink,
    X
} from 'lucide-react'

interface OnboardingStep {
    id: string
    title: string
    description: string
    icon: typeof Bot
    color: string
    content: React.ReactNode
}

export default function Onboarding() {
    const navigate = useNavigate()
    const { tenant } = useAuth()
    const [currentStep, setCurrentStep] = useState(0)
    const [completedSteps, setCompletedSteps] = useState<string[]>([])
    const [telegramToken, setTelegramToken] = useState('')
    const [showOnboarding, setShowOnboarding] = useState(true)

    // Check if onboarding was completed
    useEffect(() => {
        const completed = localStorage.getItem('onboarding_completed')
        if (completed === 'true') {
            setShowOnboarding(false)
        }
    }, [])

    const completeStep = (stepId: string) => {
        if (!completedSteps.includes(stepId)) {
            setCompletedSteps([...completedSteps, stepId])
        }
    }

    const finishOnboarding = () => {
        localStorage.setItem('onboarding_completed', 'true')
        setShowOnboarding(false)
        navigate('/dashboard')
    }

    const skipOnboarding = () => {
        localStorage.setItem('onboarding_completed', 'true')
        setShowOnboarding(false)
    }

    const steps: OnboardingStep[] = [
        {
            id: 'welcome',
            title: 'Добро пожаловать! 👋',
            description: 'Давайте настроим вашего AI-секретаря за 2 минуты',
            icon: Sparkles,
            color: 'from-purple-500 to-pink-500',
            content: (
                <div className="space-y-6">
                    <div className="text-center">
                        <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-purple-600 rounded-2xl 
                                        flex items-center justify-center mx-auto mb-6">
                            <Bot className="w-10 h-10 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">
                            Привет, {tenant?.business_name || 'друг'}!
                        </h2>
                        <p className="text-gray-400">
                            Ваш AI-секретарь готов к работе. Выберите, как хотите начать:
                        </p>
                    </div>

                    <div className="grid gap-4">
                        {[
                            { icon: '🚀', label: 'Быстрый старт', desc: 'Пропустить настройку и начать', action: finishOnboarding },
                            { icon: '📱', label: 'Подключить Telegram', desc: 'Управляйте через бота', action: () => setCurrentStep(1) },
                            { icon: '💬', label: 'Подключить WhatsApp', desc: 'Общайтесь с клиентами', action: () => setCurrentStep(2) },
                            { icon: '📖', label: 'Тур по функциям', desc: 'Узнайте возможности', action: () => setCurrentStep(3) },
                        ].map((item, i) => (
                            <button
                                key={i}
                                onClick={item.action}
                                className="flex items-center gap-4 p-4 bg-gray-800 hover:bg-gray-700 
                                           border border-gray-700 rounded-xl transition text-left group"
                            >
                                <span className="text-2xl">{item.icon}</span>
                                <div className="flex-1">
                                    <p className="text-white font-medium">{item.label}</p>
                                    <p className="text-gray-400 text-sm">{item.desc}</p>
                                </div>
                                <ArrowRight className="w-5 h-5 text-gray-500 group-hover:text-white transition" />
                            </button>
                        ))}
                    </div>
                </div>
            )
        },
        {
            id: 'telegram',
            title: 'Подключение Telegram',
            description: 'Создайте бота и получайте уведомления',
            icon: MessageSquare,
            color: 'from-blue-500 to-cyan-500',
            content: (
                <div className="space-y-6">
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
                        <h3 className="text-blue-400 font-medium mb-2">📱 3 простых шага:</h3>
                        <ol className="space-y-3 text-gray-300">
                            <li className="flex gap-3">
                                <span className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0">1</span>
                                <div>
                                    Откройте <a href="https://t.me/BotFather" target="_blank" className="text-blue-400 hover:underline">@BotFather</a> в Telegram
                                </div>
                            </li>
                            <li className="flex gap-3">
                                <span className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0">2</span>
                                <div>Отправьте команду <code className="bg-gray-700 px-2 py-0.5 rounded">/newbot</code> и следуйте инструкциям</div>
                            </li>
                            <li className="flex gap-3">
                                <span className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0">3</span>
                                <div>Скопируйте токен и вставьте ниже</div>
                            </li>
                        </ol>
                    </div>

                    <div>
                        <label className="block text-gray-400 text-sm mb-2">Telegram Bot Token</label>
                        <input
                            type="text"
                            value={telegramToken}
                            onChange={e => setTelegramToken(e.target.value)}
                            placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl
                                       text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <button
                        onClick={() => {
                            // TODO: Save token via API
                            completeStep('telegram')
                            setCurrentStep(2)
                        }}
                        disabled={!telegramToken}
                        className="w-full py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-700 
                                   disabled:text-gray-500 text-white font-medium rounded-xl transition"
                    >
                        Подключить Telegram
                    </button>

                    <button
                        onClick={() => setCurrentStep(2)}
                        className="w-full py-2 text-gray-400 hover:text-white transition"
                    >
                        Пропустить этот шаг
                    </button>
                </div>
            )
        },
        {
            id: 'whatsapp',
            title: 'Подключение WhatsApp',
            description: 'Общайтесь с клиентами через WhatsApp',
            icon: Smartphone,
            color: 'from-green-500 to-emerald-500',
            content: (
                <div className="space-y-6">
                    <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
                        <h3 className="text-green-400 font-medium mb-2">💬 Как подключить:</h3>
                        <p className="text-gray-300 mb-4">
                            Для WhatsApp нужен аккаунт Green API. Вы можете получить тестовый доступ бесплатно.
                        </p>
                        <a
                            href="https://green-api.com"
                            target="_blank"
                            className="inline-flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 
                                       text-white rounded-lg transition"
                        >
                            Получить Green API
                            <ExternalLink className="w-4 h-4" />
                        </a>
                    </div>

                    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                        <p className="text-gray-400 text-sm mb-2">Или попросите админа выдать вам доступ:</p>
                        <p className="text-white">Перейдите в Настройки → WhatsApp после онбординга</p>
                    </div>

                    <button
                        onClick={() => {
                            completeStep('whatsapp')
                            setCurrentStep(3)
                        }}
                        className="w-full py-3 bg-green-500 hover:bg-green-600 text-white font-medium rounded-xl transition"
                    >
                        Продолжить
                    </button>
                </div>
            )
        },
        {
            id: 'features',
            title: 'Возможности платформы',
            description: 'Что умеет ваш AI-секретарь',
            icon: Sparkles,
            color: 'from-orange-500 to-amber-500',
            content: (
                <div className="space-y-4">
                    {[
                        { icon: MessageSquare, title: 'AI Чат', desc: 'Общайтесь на естественном языке — бот понимает контекст', color: 'bg-blue-500' },
                        { icon: Calendar, title: 'Календарь', desc: 'Планируйте встречи, бот напомнит и согласует время', color: 'bg-purple-500' },
                        { icon: Wallet, title: 'Финансы', desc: 'Учёт доходов и расходов, аналитика по категориям', color: 'bg-green-500' },
                        { icon: CheckCircle2, title: 'Задачи', desc: 'Создавайте задачи голосом или текстом', color: 'bg-orange-500' },
                    ].map((feature, i) => (
                        <div key={i} className="flex items-start gap-4 p-4 bg-gray-800 rounded-xl border border-gray-700">
                            <div className={`p-2 ${feature.color} rounded-lg`}>
                                <feature.icon className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h4 className="text-white font-medium">{feature.title}</h4>
                                <p className="text-gray-400 text-sm">{feature.desc}</p>
                            </div>
                        </div>
                    ))}

                    <button
                        onClick={() => {
                            completeStep('features')
                            setCurrentStep(4)
                        }}
                        className="w-full py-3 bg-primary-500 hover:bg-primary-600 text-white font-medium rounded-xl transition mt-4"
                    >
                        Понятно, продолжить
                    </button>
                </div>
            )
        },
        {
            id: 'complete',
            title: 'Готово! 🎉',
            description: 'Вы настроили своего AI-секретаря',
            icon: CheckCircle2,
            color: 'from-green-500 to-emerald-500',
            content: (
                <div className="text-center space-y-6">
                    <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full 
                                    flex items-center justify-center mx-auto">
                        <CheckCircle2 className="w-10 h-10 text-white" />
                    </div>

                    <div>
                        <h2 className="text-2xl font-bold text-white mb-2">Всё готово!</h2>
                        <p className="text-gray-400">
                            Теперь вы можете использовать AI-секретаря. Попробуйте написать в чат:
                        </p>
                    </div>

                    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                        <p className="text-gray-400 text-sm mb-2">Примеры команд:</p>
                        <div className="space-y-2 text-left">
                            {[
                                '📅 "Запланируй встречу на завтра в 14:00"',
                                '💰 "Добавь расход 5000 на такси"',
                                '✅ "Напомни позвонить Асету завтра"',
                                '💬 "Что у меня на сегодня?"',
                            ].map((cmd, i) => (
                                <p key={i} className="text-white text-sm">{cmd}</p>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={finishOnboarding}
                        className="w-full py-4 bg-gradient-to-r from-primary-500 to-purple-600 
                                   hover:from-primary-600 hover:to-purple-700 text-white font-semibold 
                                   rounded-xl transition shadow-lg shadow-primary-500/25"
                    >
                        Начать работу
                    </button>
                </div>
            )
        }
    ]

    if (!showOnboarding) {
        return null
    }

    const currentStepData = steps[currentStep]

    return (
        <div className="fixed inset-0 bg-gray-950/95 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 w-full max-w-lg max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="p-6 border-b border-gray-800">
                    <div className="flex items-center justify-between mb-4">
                        {/* Progress */}
                        <div className="flex gap-1.5">
                            {steps.map((_, i) => (
                                <div
                                    key={i}
                                    className={`h-1.5 w-8 rounded-full transition ${i < currentStep ? 'bg-primary-500' :
                                        i === currentStep ? 'bg-primary-400' : 'bg-gray-700'
                                        }`}
                                />
                            ))}
                        </div>
                        <button
                            onClick={skipOnboarding}
                            className="p-2 hover:bg-gray-800 rounded-lg transition"
                        >
                            <X className="w-5 h-5 text-gray-400" />
                        </button>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className={`p-2 bg-gradient-to-br ${currentStepData.color} rounded-xl`}>
                            <currentStepData.icon className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-white">{currentStepData.title}</h2>
                            <p className="text-gray-400 text-sm">{currentStepData.description}</p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6">
                    {currentStepData.content}
                </div>

                {/* Navigation */}
                {currentStep > 0 && currentStep < steps.length - 1 && (
                    <div className="px-6 pb-6">
                        <button
                            onClick={() => setCurrentStep(prev => prev - 1)}
                            className="flex items-center gap-2 text-gray-400 hover:text-white transition"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Назад
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
