import { useState, useEffect } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
    LayoutDashboard,
    Puzzle,
    Settings,
    LogOut,
    Bot,
    Globe,
    Calendar,
    MessageSquare,
    Wallet,
    CheckSquare,
    Users,
    Receipt,
    BarChart3,
    UsersRound,
    Menu,
    X
} from 'lucide-react'

export default function Layout() {
    const { t, language, setLanguage, logout, tenant } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

    // Close mobile menu on route change
    useEffect(() => {
        setMobileMenuOpen(false)
    }, [location.pathname])

    // Close menu on window resize to desktop
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth >= 768) {
                setMobileMenuOpen(false)
            }
        }
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    const navItems = [
        { to: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard'), emoji: '🏠' },
        { to: '/dashboard/chat', icon: MessageSquare, label: t('nav.chat'), emoji: '💬' },
        { to: '/dashboard/calendar', icon: Calendar, label: t('nav.calendar'), emoji: '📅' },
        { to: '/dashboard/tasks', icon: CheckSquare, label: t('nav.tasks'), emoji: '✅' },
        { to: '/dashboard/contacts', icon: Users, label: t('nav.contacts'), emoji: '📒' },
        { to: '/dashboard/finance', icon: Wallet, label: t('nav.finance'), emoji: '💰' },
        { to: '/dashboard/invoices', icon: Receipt, label: t('nav.invoices'), emoji: '💸' },
        { to: '/dashboard/ideas', icon: Puzzle, label: t('nav.ideas'), emoji: '💡' },
        { to: '/dashboard/birthdays', icon: Calendar, label: t('nav.birthdays'), emoji: '🎂' },
        { to: '/dashboard/contracts', icon: Receipt, label: t('nav.contracts'), emoji: '📄' },
        { to: '/dashboard/reports', icon: BarChart3, label: t('nav.reports'), emoji: '📊' },
        { to: '/dashboard/groups', icon: UsersRound, label: t('nav.groups'), emoji: '🏢' },
        { to: '/dashboard/modules', icon: Puzzle, label: t('nav.modules'), emoji: '🧩' },
        { to: '/dashboard/settings', icon: Settings, label: t('nav.settings'), emoji: '⚙️' },
        // Only show Admin link if user is admin
        ...(tenant?.is_admin ? [{ to: '/dashboard/admin', icon: Settings, label: t('nav.admin'), emoji: '🛡️' }] : []),
    ]

    return (
        <div className="flex min-h-screen bg-gray-900">
            {/* Mobile Header */}
            <div className="md:hidden fixed top-0 left-0 right-0 h-14 bg-gray-800 border-b border-gray-700 
                            flex items-center justify-between px-4 z-40">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                        <Bot className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-white font-semibold text-sm">{t('app.name')}</span>
                </div>
                <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="p-2 text-gray-400 hover:text-white transition"
                >
                    {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>
            </div>

            {/* Mobile Menu Overlay */}
            {mobileMenuOpen && (
                <div
                    className="md:hidden fixed inset-0 bg-black/50 z-30"
                    onClick={() => setMobileMenuOpen(false)}
                />
            )}

            {/* Sidebar - Desktop always visible, Mobile as slide-out */}
            <aside className={`
                fixed md:static inset-y-0 left-0 z-40
                w-52 bg-gray-800 border-r border-gray-700 
                flex flex-col transition-transform duration-300
                ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
                md:pt-0 pt-14
            `}>
                {/* Header - Desktop only */}
                <div className="hidden md:block p-4">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4 text-white" />
                        </div>
                        <div className="overflow-hidden">
                            <h1 className="text-sm font-bold text-white truncate">{t('app.name')}</h1>
                            <p className="text-xs text-gray-500 truncate">{tenant?.business_name}</p>
                        </div>
                    </div>
                </div>

                {/* Navigation - Scrollable */}
                <nav className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
                    {navItems.map(({ to, label, emoji }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={to === '/'}
                            className={({ isActive }) => `
                                flex items-center gap-2 px-3 py-2.5 rounded-lg transition-all text-sm
                                ${isActive
                                    ? 'bg-primary-500 text-white'
                                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                                }
                            `}
                        >
                            <span className="text-base flex-shrink-0">{emoji}</span>
                            <span className="font-medium truncate">{label}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* Footer */}
                <div className="p-3 border-t border-gray-700">
                    {/* Language Switcher */}
                    <div className="flex items-center gap-1 mb-2">
                        <Globe className="w-3 h-3 text-gray-500" />
                        <button
                            onClick={() => setLanguage('ru')}
                            className={`text-xs px-2 py-0.5 rounded ${language === 'ru' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white'
                                }`}
                        >
                            Рус
                        </button>
                        <button
                            onClick={() => setLanguage('kz')}
                            className={`text-xs px-2 py-0.5 rounded ${language === 'kz' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white'
                                }`}
                        >
                            Қаз
                        </button>
                    </div>

                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 w-full px-2 py-2 text-gray-400 
                                   hover:text-red-400 hover:bg-gray-700 rounded-lg transition"
                    >
                        <LogOut className="w-4 h-4" />
                        <span className="text-sm">{t('nav.logout')}</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 p-4 md:p-6 overflow-auto pt-16 md:pt-6">
                <Outlet />
            </main>
        </div>
    )
}
