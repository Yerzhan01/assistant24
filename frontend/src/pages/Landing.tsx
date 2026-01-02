import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
    Bot,
    Sparkles,
    Calendar,
    MessageSquare,
    Wallet,
    CheckSquare,
    Users,
    Star,
    ArrowRight,
    Play,
    Smartphone,
    Globe,
    FileText,
    BellRing,
    Lightbulb,
    Receipt
} from 'lucide-react'

const features = [
    {
        icon: Bot,
        title: 'AI Ассистент на Gemini',
        description: 'Пишите боту в WhatsApp/Telegram на естественном языке — он поймёт и выполнит',
        color: 'from-blue-500 to-cyan-500'
    },
    {
        icon: Wallet,
        title: 'Учёт финансов',
        description: 'Доходы, расходы, категории. Скажите «записал 50000 от Асана» — готово',
        color: 'from-green-500 to-emerald-500'
    },
    {
        icon: Calendar,
        title: 'Календарь встреч',
        description: 'iCal экспорт, напоминания, цветовая маркировка. Синхронизация с Google Calendar',
        color: 'from-purple-500 to-pink-500'
    },
    {
        icon: CheckSquare,
        title: 'Задачи из групп',
        description: 'AI извлекает задачи из WhatsApp-групп и отслеживает их выполнение',
        color: 'from-orange-500 to-amber-500'
    },
    {
        icon: Users,
        title: 'CRM с контактами',
        description: 'База клиентов с тегами, историей, заметками. Поиск по имени или телефону',
        color: 'from-red-500 to-rose-500'
    },
    {
        icon: Receipt,
        title: 'Сбор долгов',
        description: 'Автоматические напоминания должникам. AI готовит сообщения',
        color: 'from-indigo-500 to-violet-500'
    },
    {
        icon: FileText,
        title: 'Договоры',
        description: 'Храните контракты, сроки, суммы. Напоминания о продлении',
        color: 'from-teal-500 to-cyan-500'
    },
    {
        icon: Lightbulb,
        title: 'Копилка идей',
        description: 'Записывайте идеи голосом или текстом — бот сохранит и структурирует',
        color: 'from-yellow-500 to-orange-500'
    },
    {
        icon: BellRing,
        title: 'Дни рождения',
        description: 'Бот сам напомнит о днях рождения клиентов и партнёров',
        color: 'from-pink-500 to-rose-500'
    }
]

const testimonials = [
    {
        name: 'Айгерим К.',
        role: 'Директор ТОО',
        text: 'Сэкономила 2 часа в день на рутинных задачах. Бот сам напоминает о встречах и ведёт учёт.',
        avatar: '👩‍💼'
    },
    {
        name: 'Нурлан М.',
        role: 'ИП, услуги',
        text: 'Наконец-то все финансы под контролем. Вижу доходы и расходы в реальном времени.',
        avatar: '👨‍💻'
    },
    {
        name: 'Дана Т.',
        role: 'Бухгалтер',
        text: 'Интеграция с WhatsApp — это супер! Клиенты пишут, а бот сразу фиксирует информацию.',
        avatar: '👩‍🔧'
    }
]

export default function Landing() {
    const navigate = useNavigate()
    const { isAuthenticated } = useAuth()
    const [scrolled, setScrolled] = useState(false)

    useEffect(() => {
        if (isAuthenticated) {
            navigate('/dashboard')
        }
    }, [isAuthenticated, navigate])

    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 50)
        }
        window.addEventListener('scroll', handleScroll)
        return () => window.removeEventListener('scroll', handleScroll)
    }, [])

    return (
        <div className="min-h-screen bg-gray-950 text-white overflow-x-hidden selection:bg-primary-500/30">
            {/* Animated Background */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 left-0 w-full h-full bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10" />
                <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary-500/20 rounded-full blur-[100px] animate-pulse" />
                <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-purple-500/20 rounded-full blur-[100px] animate-pulse delay-1000" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-r from-primary-500/10 to-purple-500/10 rounded-full blur-[100px]" />
            </div>

            {/* Header */}
            <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-gray-950/80 backdrop-blur-xl border-b border-gray-800/50' : 'bg-transparent'
                }`}>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-20">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 via-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20">
                                <Bot className="w-6 h-6 text-white" />
                            </div>
                            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                                Assistant24
                            </span>
                        </div>

                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => navigate('/login')}
                                className="px-4 py-2 text-gray-300 hover:text-white transition font-medium hidden sm:block"
                            >
                                Войти
                            </button>
                            <button
                                onClick={() => navigate('/register')}
                                className="px-6 py-2.5 bg-white text-gray-900 hover:bg-gray-100 
                                           font-semibold rounded-xl transition shadow-lg shadow-white/10"
                            >
                                Начать
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <section className="relative pt-32 md:pt-48 pb-20 px-4 overflow-hidden">
                <div className="max-w-7xl mx-auto text-center relative z-10">
                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 
                                    rounded-full text-sm text-gray-300 mb-8 backdrop-blur-md shadow-xl animate-fade-in-up">
                        <span className="flex h-2 w-2 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                        </span>
                        <span>AI-помощник работает 24/7</span>
                    </div>

                    {/* Main Heading */}
                    <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold leading-tight mb-8 tracking-tight">
                        <span className="block text-white">Твой бизнес.</span>
                        <span className="bg-gradient-to-r from-primary-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                            На автопилоте.
                        </span>
                    </h1>

                    <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-12 leading-relaxed">
                        AI-ассистент, который работает в Telegram и WhatsApp 24 часа в сутки.
                        Записывает клиентов, ведёт финансы, напоминает о встречах.
                    </p>

                    {/* CTA Buttons */}
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-20">
                        <button
                            onClick={() => navigate('/register')}
                            className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-4 
                                       bg-gradient-to-r from-primary-600 to-purple-600 hover:scale-105 active:scale-95
                                       text-white font-semibold text-lg rounded-2xl transition-all duration-300
                                       shadow-[0_0_40px_-10px_rgba(168,85,247,0.5)] border border-white/10"
                        >
                            Попробовать бесплатно
                            <ArrowRight className="w-5 h-5" />
                        </button>
                        <button
                            className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-4 
                                       bg-white/5 hover:bg-white/10 backdrop-blur-sm text-white font-semibold text-lg rounded-2xl 
                                       transition border border-white/10"
                        >
                            <Play className="w-5 h-5 fill-current" />
                            Как это работает?
                        </button>
                    </div>

                    {/* Hero Visual Dashboard */}
                    <div className="relative mx-auto max-w-6xl">
                        {/* Glow effect behind */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-primary-500/20 blur-[120px]" />

                        <div className="relative bg-gray-900/80 backdrop-blur-xl rounded-3xl border border-white/10 shadow-2xl overflow-hidden ring-1 ring-white/10">
                            {/* Window Config */}
                            <div className="h-10 border-b border-white/10 bg-white/5 flex items-center px-4 gap-2">
                                <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
                                <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                                <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
                                <div className="ml-auto text-xs text-gray-500 font-mono">dashboard.app</div>
                            </div>

                            {/* Dashboard Content */}
                            <div className="p-4 md:p-8 grid md:grid-cols-3 gap-6 text-left">
                                {/* Left Sidebar - Chat */}
                                <div className="md:col-span-1 space-y-4">
                                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                                        <div className="flex items-center gap-3 mb-4">
                                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
                                                <Smartphone className="w-5 h-5 text-white" />
                                            </div>
                                            <div>
                                                <div className="text-sm font-medium text-white">WhatsApp</div>
                                                <div className="text-xs text-green-400">Подключен</div>
                                            </div>
                                        </div>
                                        <div className="space-y-3">
                                            <div className="bg-gray-800/50 rounded-xl rounded-tl-sm p-3 text-xs text-gray-300">
                                                Здравствуйте! Можно записаться на 15:00?
                                            </div>
                                            <div className="bg-green-500/20 text-green-200 rounded-xl rounded-tr-sm p-3 text-xs ml-auto max-w-[90%] border border-green-500/20">
                                                Добрый день! Да, время свободно. Записал вас.
                                            </div>
                                        </div>
                                    </div>

                                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm text-gray-400">Сегодня</span>
                                            <span className="text-xs text-green-400">+12%</span>
                                        </div>
                                        <div className="text-2xl font-bold text-white">45 000 ₸</div>
                                        <div className="w-full bg-gray-700 h-1.5 rounded-full mt-3 overflow-hidden">
                                            <div className="bg-green-500 h-full w-[70%]" />
                                        </div>
                                    </div>
                                </div>

                                {/* Main Area - Analytics & Tasks */}
                                <div className="md:col-span-2 grid grid-cols-2 gap-4">
                                    <div className="col-span-2 bg-gradient-to-br from-primary-500/10 to-purple-500/10 rounded-2xl p-6 border border-white/10">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <h3 className="text-lg font-medium text-white mb-1">AI Анализ</h3>
                                                <p className="text-sm text-gray-400">Еженедельный отчёт готов</p>
                                            </div>
                                            <Sparkles className="w-6 h-6 text-primary-400" />
                                        </div>
                                        <div className="mt-6 flex gap-2">
                                            {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day, i) => (
                                                <div key={i} className="flex-1 flex flex-col items-center gap-2">
                                                    <div className="w-full bg-white/5 rounded-full h-24 relative overflow-hidden">
                                                        <div
                                                            className="absolute bottom-0 w-full bg-primary-500/50 rounded-full"
                                                            style={{ height: `${[40, 60, 30, 80, 50, 90, 70][i]}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-xs text-gray-500">{day}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                                        <div className="w-10 h-10 rounded-xl bg-orange-500/20 flex items-center justify-center mb-4">
                                            <Calendar className="w-5 h-5 text-orange-400" />
                                        </div>
                                        <div className="text-2xl font-bold text-white mb-1">12</div>
                                        <div className="text-xs text-gray-400">Встреч на неделе</div>
                                    </div>

                                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                                        <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center mb-4">
                                            <Users className="w-5 h-5 text-blue-400" />
                                        </div>
                                        <div className="text-2xl font-bold text-white mb-1">1,240</div>
                                        <div className="text-xs text-gray-400">База клиентов</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section >

            {/* Integrations Strip */}
            < div className="border-y border-white/5 bg-white/[0.02] py-10" >
                <div className="max-w-7xl mx-auto px-4 text-center">
                    <p className="text-sm text-gray-500 mb-6 uppercase tracking-widest font-medium">Интеграции и технологии</p>
                    <div className="flex flex-wrap justify-center gap-8 md:gap-16 items-center opacity-70 grayscale hover:grayscale-0 transition-all duration-500">
                        <div className="flex items-center gap-2 text-xl font-semibold text-white"><Bot className="w-6 h-6" /> Google Gemini</div>
                        <div className="flex items-center gap-2 text-xl font-semibold text-white"><Smartphone className="w-6 h-6" /> WhatsApp</div>
                        <div className="flex items-center gap-2 text-xl font-semibold text-white"><MessageSquare className="w-6 h-6" /> Telegram</div>
                        <div className="flex items-center gap-2 text-xl font-semibold text-white"><Globe className="w-6 h-6" /> Google Calendar</div>
                    </div>
                </div>
            </div >

            {/* Features Grid */}
            < section className="py-24 px-4 relative" >
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-bold mb-6">Всё в одном месте</h2>
                        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
                            Мы объединили лучшие инструменты для управления малым бизнесом в единый интерфейс
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {features.map((feature, i) => (
                            <div
                                key={i}
                                className="group p-8 bg-white/5 hover:bg-white/10 border border-white/5 
                                           hover:border-primary-500/30 rounded-3xl transition-all duration-300 
                                           hover:-translate-y-1 relative overflow-hidden"
                            >
                                <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-5 transition-opacity duration-500`} />
                                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} 
                                                flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                                    <feature.icon className="w-7 h-7 text-white" />
                                </div>
                                <h3 className="text-2xl font-semibold text-white mb-3">{feature.title}</h3>
                                <p className="text-gray-400 leading-relaxed">{feature.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section >

            {/* Pricing Section - NEW */}
            < section className="py-24 px-4 bg-gray-900/50 border-y border-white/5" >
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-bold mb-6">Простые тарифы</h2>
                        <p className="text-gray-400 text-lg">Начните бесплатно, платите по мере роста</p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                        {/* Starter */}
                        <div className="bg-gray-900 rounded-3xl p-8 border border-gray-800 hover:border-gray-700 transition">
                            <h3 className="text-xl font-semibold text-white mb-2">Старт</h3>
                            <div className="text-4xl font-bold text-white mb-6">0 ₸<span className="text-lg text-gray-500 font-normal">/мес</span></div>
                            <ul className="space-y-4 mb-8">
                                <li className="flex gap-3 text-gray-300"><CheckSquare className="w-5 h-5 text-gray-500" /> Основные функции</li>
                                <li className="flex gap-3 text-gray-300"><CheckSquare className="w-5 h-5 text-gray-500" /> 1 пользователь</li>
                                <li className="flex gap-3 text-gray-300"><CheckSquare className="w-5 h-5 text-gray-500" /> Telegram бот</li>
                            </ul>
                            <button onClick={() => navigate('/register')} className="w-full py-3 rounded-xl bg-gray-800 text-white font-medium hover:bg-gray-700 transition">Выбрать</button>
                        </div>

                        {/* Pro - Featured */}
                        <div className="bg-gray-900 rounded-3xl p-8 border border-primary-500 relative transform md:-translate-y-4 shadow-2xl shadow-primary-500/20">
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-primary-500 text-white px-4 py-1 rounded-full text-sm font-medium shadow-lg">
                                Популярный
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Бизнес</h3>
                            <div className="text-4xl font-bold text-white mb-6">7,990 ₸<span className="text-lg text-gray-500 font-normal">/мес</span></div>
                            <ul className="space-y-4 mb-8">
                                <li className="flex gap-3 text-white"><CheckSquare className="w-5 h-5 text-primary-400" /> Всё из Старт</li>
                                <li className="flex gap-3 text-white"><CheckSquare className="w-5 h-5 text-primary-400" /> WhatsApp интеграция</li>
                                <li className="flex gap-3 text-white"><CheckSquare className="w-5 h-5 text-primary-400" /> AI Аналитика</li>
                                <li className="flex gap-3 text-white"><CheckSquare className="w-5 h-5 text-primary-400" /> До 5 сотрудников</li>
                            </ul>
                            <button onClick={() => navigate('/register')} className="w-full py-3 rounded-xl bg-gradient-to-r from-primary-500 to-purple-600 text-white font-bold hover:shadow-lg transition">Попробовать 14 дней</button>
                        </div>

                        {/* Enterprise */}
                        <div className="bg-gray-900 rounded-3xl p-8 border border-gray-800 hover:border-gray-700 transition">
                            <h3 className="text-xl font-semibold text-white mb-2">Pro</h3>
                            <div className="text-4xl font-bold text-white mb-6">24,990 ₸<span className="text-lg text-gray-500 font-normal">/мес</span></div>
                            <ul className="space-y-4 mb-8">
                                <li className="flex gap-3 text-gray-300"><CheckSquare className="w-5 h-5 text-gray-500" /> Всё из Бизнес</li>
                                <li className="flex gap-3 text-gray-300"><CheckSquare className="w-5 h-5 text-gray-500" /> Приоритетная поддержка</li>
                                <li className="flex gap-3 text-gray-300"><CheckSquare className="w-5 h-5 text-gray-500" /> API доступ</li>
                                <li className="flex gap-3 text-gray-300"><CheckSquare className="w-5 h-5 text-gray-500" /> Кастомные доработки</li>
                            </ul>
                            <button className="w-full py-3 rounded-xl bg-gray-800 text-white font-medium hover:bg-gray-700 transition">Связаться с нами</button>
                        </div>
                    </div>
                </div>
            </section >

            {/* Testimonials */}
            < section className="py-24 px-4 overflow-hidden" >
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-bold mb-6">Нам доверяют</h2>
                        <div className="grid md:grid-cols-3 gap-6 relative">
                            {/* Decorative blur */}
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-primary-500/5 blur-3xl rounded-full" />

                            {testimonials.map((t, i) => (
                                <div key={i} className="relative bg-white/5 backdrop-blur-md border border-white/5 rounded-3xl p-8 hover:-translate-y-1 transition-transform">
                                    <div className="flex text-yellow-500 mb-4 gap-1">
                                        {[...Array(5)].map((_, j) => <Star key={j} className="w-4 h-4 fill-current" />)}
                                    </div>
                                    <p className="text-lg text-gray-200 mb-6 italic">"{t.text}"</p>
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center text-xl">
                                            {t.avatar}
                                        </div>
                                        <div>
                                            <div className="font-bold text-white">{t.name}</div>
                                            <div className="text-sm text-gray-400">{t.role}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section >

            {/* CTA Section - Footer */}
            < div className="px-4 pb-12" >
                <div className="max-w-7xl mx-auto bg-gradient-to-r from-primary-900 to-purple-900 rounded-[3rem] p-12 md:p-24 text-center relative overflow-hidden border border-white/10">
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20" />
                    <div className="absolute -top-24 -right-24 w-64 h-64 bg-primary-500 rounded-full blur-[100px]" />
                    <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-purple-500 rounded-full blur-[100px]" />

                    <div className="relative z-10">
                        <h2 className="text-4xl md:text-6xl font-bold text-white mb-6 tracking-tight">
                            Готовы к цифровой трансформации?
                        </h2>
                        <p className="text-xl text-gray-300 mb-10 max-w-2xl mx-auto">
                            Присоединяйтесь к 500+ предпринимателям, которые уже экономят время с нами
                        </p>
                        <button
                            onClick={() => navigate('/register')}
                            className="inline-flex items-center gap-2 px-10 py-5 bg-white text-gray-900 
                                       font-bold text-xl rounded-2xl hover:bg-gray-100 transition 
                                       shadow-2xl shadow-white/10 hover:shadow-white/20 transform hover:-translate-y-1"
                        >
                            Создать аккаунт
                            <ArrowRight className="w-6 h-6" />
                        </button>
                    </div>
                </div>
            </div >

            {/* Footer */}
            < footer className="border-t border-white/5 py-12 px-4 bg-black/20" >
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-purple-600 rounded-lg flex items-center justify-center">
                                <Bot className="w-4 h-4 text-white" />
                            </div>
                            <span className="text-gray-400 font-medium">Assistant24 © 2026</span>
                        </div>
                        <div className="flex items-center gap-8 text-sm font-medium text-gray-500">
                            <a href="#" className="hover:text-white transition">Privacy</a>
                            <a href="#" className="hover:text-white transition">Terms</a>
                            <a href="#" className="hover:text-white transition">Contact</a>
                            <div className="flex gap-4 ml-4">
                                <a href="#" className="hover:text-white transition"><Globe className="w-5 h-5" /></a>
                            </div>
                        </div>
                    </div>
                </div>
            </footer >
        </div >
    )
}
