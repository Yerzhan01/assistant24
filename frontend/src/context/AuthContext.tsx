import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { translations, Language } from '../i18n/translations'

interface AuthContextType {
    token: string | null
    tenant: TenantInfo | null
    language: Language
    isAuthenticated: boolean
    login: (token: string) => void
    logout: () => void
    setLanguage: (lang: Language) => void
    t: (key: string) => string
}

interface TenantInfo {
    id: string
    email: string
    business_name: string
    language: string
    plan: string
    telegram_connected: boolean
    whatsapp_connected: boolean
    ai_enabled: boolean
    is_admin: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(() =>
        localStorage.getItem('token')
    )
    const [tenant, setTenant] = useState<TenantInfo | null>(null)
    const [language, setLanguageState] = useState<Language>(() =>
        (localStorage.getItem('language') as Language) || 'ru'
    )

    useEffect(() => {
        if (token) {
            fetchTenant()
        }
    }, [token])

    const fetchTenant = async () => {
        try {
            const res = await fetch('/api/v1/auth/me', {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                setTenant(data)
                if (data.language) {
                    setLanguageState(data.language as Language)
                }
            } else {
                logout()
            }
        } catch (error) {
            console.error('Failed to fetch tenant:', error)
        }
    }

    const login = (newToken: string) => {
        localStorage.setItem('token', newToken)
        setToken(newToken)
    }

    const logout = () => {
        localStorage.removeItem('token')
        setToken(null)
        setTenant(null)
    }

    const setLanguage = (lang: Language) => {
        localStorage.setItem('language', lang)
        setLanguageState(lang)
    }

    // Translation function
    const t = (key: string): string => {
        const keys = key.split('.')
        let value: any = translations[language]

        for (const k of keys) {
            value = value?.[k]
        }

        return value || key
    }

    return (
        <AuthContext.Provider value={{
            token,
            tenant,
            language,
            isAuthenticated: !!token,
            login,
            logout,
            setLanguage,
            t
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context
}
