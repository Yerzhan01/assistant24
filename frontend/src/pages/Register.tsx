import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Bot, Loader2 } from 'lucide-react'

export default function Register() {
    const { login, t, language, setLanguage } = useAuth()
    const navigate = useNavigate()
    const [businessName, setBusinessName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const res = await fetch('/api/v1/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    password,
                    business_name: businessName,
                    language
                })
            })

            const data = await res.json()

            if (res.ok) {
                login(data.access_token)
                navigate('/')
            } else {
                setError(data.detail || 'Registration failed')
            }
        } catch (err) {
            setError('Network error')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
            <div className="w-full max-w-md">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-primary-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <Bot className="w-10 h-10 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-white">{t('app.name')}</h1>
                    <p className="text-gray-400 mt-2">{t('app.tagline')}</p>
                </div>

                {/* Language Toggle */}
                <div className="flex justify-center gap-2 mb-6">
                    <button
                        onClick={() => setLanguage('ru')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition ${language === 'ru'
                                ? 'bg-primary-500 text-white'
                                : 'bg-gray-800 text-gray-400 hover:text-white'
                            }`}
                    >
                        Русский
                    </button>
                    <button
                        onClick={() => setLanguage('kz')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition ${language === 'kz'
                                ? 'bg-primary-500 text-white'
                                : 'bg-gray-800 text-gray-400 hover:text-white'
                            }`}
                    >
                        Қазақша
                    </button>
                </div>

                {/* Form */}
                <div className="bg-gray-800 rounded-2xl p-8 shadow-xl border border-gray-700">
                    <h2 className="text-xl font-semibold text-white mb-6">{t('auth.register')}</h2>

                    {error && (
                        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                {t('auth.businessName')}
                            </label>
                            <input
                                type="text"
                                value={businessName}
                                onChange={e => setBusinessName(e.target.value)}
                                required
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                         placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                placeholder="ИП Асхатов"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                {t('auth.email')}
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                required
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                         placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                placeholder="email@example.com"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                {t('auth.password')}
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                                minLength={6}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                         placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                placeholder="••••••••"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 bg-primary-500 hover:bg-primary-600 text-white font-medium 
                       rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            {loading && <Loader2 className="w-5 h-5 animate-spin" />}
                            {t('auth.register')}
                        </button>
                    </form>

                    <p className="mt-6 text-center text-gray-400">
                        {t('auth.hasAccount')}{' '}
                        <Link to="/login" className="text-primary-400 hover:text-primary-300">
                            {t('auth.login')}
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
