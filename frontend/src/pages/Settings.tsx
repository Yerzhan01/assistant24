import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { Send, MessageCircle, Globe, Bot, Loader2, CheckCircle, XCircle } from 'lucide-react'

export default function Settings() {
    const { t, token, tenant, language, setLanguage } = useAuth()

    // Telegram
    const [tgToken, setTgToken] = useState('')
    const [tgLoading, setTgLoading] = useState(false)
    const [tgError, setTgError] = useState('')
    const [tgSuccess, setTgSuccess] = useState(false)

    // WhatsApp
    const [waInstanceId, setWaInstanceId] = useState('')
    const [waToken, setWaToken] = useState('')
    const [waPhone, setWaPhone] = useState('')
    const [waLoading, setWaLoading] = useState(false)
    const [waError, setWaError] = useState('')
    const [waSuccess, setWaSuccess] = useState(false)

    // AI
    const [aiEnabled, setAiEnabled] = useState(tenant?.ai_enabled ?? true)
    const [aiKey, setAiKey] = useState('')
    const [aiLoading, setAiLoading] = useState(false)

    const connectTelegram = async () => {
        setTgLoading(true)
        setTgError('')
        setTgSuccess(false)

        try {
            const res = await fetch('/api/v1/settings/telegram', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ bot_token: tgToken })
            })

            if (res.ok) {
                setTgSuccess(true)
                setTgToken('')
            } else {
                const data = await res.json()
                setTgError(data.detail || 'Failed')
            }
        } catch (err) {
            setTgError('Network error')
        } finally {
            setTgLoading(false)
        }
    }

    const connectWhatsApp = async () => {
        setWaLoading(true)
        setWaError('')
        setWaSuccess(false)

        try {
            const res = await fetch('/api/v1/settings/whatsapp', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    instance_id: waInstanceId,
                    token: waToken,
                    phone: waPhone
                })
            })

            if (res.ok) {
                setWaSuccess(true)
            } else {
                const data = await res.json()
                setWaError(data.detail || 'Failed')
            }
        } catch (err) {
            setWaError('Network error')
        } finally {
            setWaLoading(false)
        }
    }

    const updateAI = async () => {
        setAiLoading(true)
        try {
            await fetch('/api/v1/settings/ai', {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    enabled: aiEnabled,
                    custom_api_key: aiKey || null
                })
            })
        } catch (err) {
            console.error('Failed to update AI settings:', err)
        } finally {
            setAiLoading(false)
        }
    }

    const updateLanguage = async (lang: 'ru' | 'kz') => {
        setLanguage(lang)
        await fetch('/api/v1/settings/language', {
            method: 'PATCH',
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ language: lang })
        })
    }

    const disconnectTelegram = async () => {
        if (!confirm(t('common.are_you_sure'))) return

        try {
            await fetch('/api/v1/settings/telegram', {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            })
            window.location.reload() // Reload to update tenant state
        } catch (err) {
            console.error(err)
        }
    }

    const disconnectWhatsApp = async () => {
        if (!confirm(t('common.are_you_sure'))) return

        try {
            await fetch('/api/v1/settings/whatsapp', {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            })
            window.location.reload()
        } catch (err) {
            console.error(err)
        }
    }

    return (
        <div className="space-y-8 max-w-3xl">
            <div>
                <h1 className="text-3xl font-bold text-white">{t('settings.title')}</h1>
            </div>

            {/* Telegram */}
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                <div className="flex items-center gap-3 mb-4">
                    <Send className="w-6 h-6 text-blue-400" />
                    <div>
                        <h2 className="text-lg font-semibold text-white">{t('settings.telegram.title')}</h2>
                        <p className="text-sm text-gray-400">{t('settings.telegram.description')}</p>
                    </div>
                    {tenant?.telegram_connected && (
                        <CheckCircle className="w-5 h-5 text-green-400 ml-auto" />
                    )}
                </div>

                {tenant?.telegram_connected ? (
                    <div className="flex items-center justify-between p-4 bg-green-500/10 rounded-xl border border-green-500/30">
                        <span className="text-green-400">✅ {t('settings.telegram.connected')}</span>
                        <button
                            onClick={disconnectTelegram}
                            className="text-sm text-red-400 hover:text-red-300"
                        >
                            {t('settings.telegram.disconnect')}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-gray-500">{t('settings.telegram.instruction')}</p>

                        {tgError && (
                            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                                {tgError}
                            </div>
                        )}

                        {tgSuccess && (
                            <div className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg text-green-400 text-sm">
                                ✅ {t('settings.telegram.connected')}
                            </div>
                        )}

                        <input
                            type="text"
                            value={tgToken}
                            onChange={e => setTgToken(e.target.value)}
                            placeholder={t('settings.telegram.token')}
                            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                       placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />

                        <button
                            onClick={connectTelegram}
                            disabled={tgLoading || !tgToken}
                            className="px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white font-medium 
                       rounded-xl transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            {tgLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                            {t('settings.telegram.connect')}
                        </button>
                    </div>
                )}
            </div>

            {/* WhatsApp */}
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                <div className="flex items-center gap-3 mb-4">
                    <MessageCircle className="w-6 h-6 text-green-400" />
                    <div>
                        <h2 className="text-lg font-semibold text-white">{t('settings.whatsapp.title')}</h2>
                        <p className="text-sm text-gray-400">{t('settings.whatsapp.description')}</p>
                    </div>
                    {tenant?.whatsapp_connected && (
                        <CheckCircle className="w-5 h-5 text-green-400 ml-auto" />
                    )}
                </div>

                {tenant?.whatsapp_connected ? (
                    <div className="flex items-center justify-between p-4 bg-green-500/10 rounded-xl border border-green-500/30">
                        <span className="text-green-400">✅ {t('settings.whatsapp.connected')}</span>
                        <button
                            onClick={disconnectWhatsApp}
                            className="text-sm text-red-400 hover:text-red-300"
                        >
                            {t('settings.whatsapp.disconnect')}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {waError && (
                            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                                {waError}
                            </div>
                        )}

                        {waSuccess && (
                            <div className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg text-green-400 text-sm">
                                ✅ {t('settings.whatsapp.connected')}
                            </div>
                        )}

                        <input
                            type="text"
                            value={waInstanceId}
                            onChange={e => setWaInstanceId(e.target.value)}
                            placeholder={t('settings.whatsapp.instanceId')}
                            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                       placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />

                        <input
                            type="text"
                            value={waToken}
                            onChange={e => setWaToken(e.target.value)}
                            placeholder={t('settings.whatsapp.token')}
                            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                       placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />

                        <input
                            type="text"
                            value={waPhone}
                            onChange={e => setWaPhone(e.target.value)}
                            placeholder={t('settings.whatsapp.phone')}
                            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                       placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />

                        <button
                            onClick={connectWhatsApp}
                            disabled={waLoading || !waInstanceId || !waToken}
                            className="px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white font-medium 
                       rounded-xl transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            {waLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                            {t('settings.whatsapp.connect')}
                        </button>
                    </div>
                )}
            </div>

            {/* Language */}
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                <div className="flex items-center gap-3 mb-4">
                    <Globe className="w-6 h-6 text-purple-400" />
                    <div>
                        <h2 className="text-lg font-semibold text-white">{t('settings.language.title')}</h2>
                        <p className="text-sm text-gray-400">{t('settings.language.description')}</p>
                    </div>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => updateLanguage('ru')}
                        className={`flex-1 py-3 rounded-xl font-medium transition ${language === 'ru'
                            ? 'bg-primary-500 text-white'
                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                            }`}
                    >
                        🇷🇺 Русский
                    </button>
                    <button
                        onClick={() => updateLanguage('kz')}
                        className={`flex-1 py-3 rounded-xl font-medium transition ${language === 'kz'
                            ? 'bg-primary-500 text-white'
                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                            }`}
                    >
                        🇰🇿 Қазақша
                    </button>
                </div>
            </div>

            {/* AI Settings */}
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
                <div className="flex items-center gap-3 mb-4">
                    <Bot className="w-6 h-6 text-cyan-400" />
                    <div>
                        <h2 className="text-lg font-semibold text-white">{t('settings.ai.title')}</h2>
                        <p className="text-sm text-gray-400">{t('settings.ai.description')}</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <span className="text-gray-300">{t('settings.ai.enabled')}</span>
                        <button
                            onClick={() => {
                                setAiEnabled(!aiEnabled)
                            }}
                            className={`w-14 h-7 rounded-full transition-colors relative ${aiEnabled ? 'bg-primary-500' : 'bg-gray-600'
                                }`}
                        >
                            <span
                                className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${aiEnabled ? 'translate-x-7' : 'translate-x-1'
                                    }`}
                            />
                        </button>
                    </div>

                    <input
                        type="text"
                        value={aiKey}
                        onChange={e => setAiKey(e.target.value)}
                        placeholder={t('settings.ai.customKey')}
                        className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white 
                     placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />

                    <button
                        onClick={updateAI}
                        disabled={aiLoading}
                        className="px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white font-medium 
                     rounded-xl transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        {aiLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                        {t('common.save')}
                    </button>
                </div>
            </div>
        </div>
    )
}
