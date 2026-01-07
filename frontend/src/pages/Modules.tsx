import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { Loader2 } from 'lucide-react'

interface Module {
    module_id: string
    name: string
    description: string
    icon: string
    is_enabled: boolean
}

export default function Modules() {
    const { t, token } = useAuth()
    const [modules, setModules] = useState<Module[]>([])
    const [loading, setLoading] = useState(true)
    const [toggling, setToggling] = useState<string | null>(null)

    useEffect(() => {
        fetchModules()
    }, [])

    const fetchModules = async () => {
        try {
            const res = await fetch('/api/v1/modules', {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                setModules(data)
            }
        } catch (error) {
            console.error('Failed to fetch modules:', error)
        } finally {
            setLoading(false)
        }
    }

    const toggleModule = async (moduleId: string, enabled: boolean) => {
        setToggling(moduleId)
        try {
            const res = await fetch(`/api/v1/modules/${moduleId}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ is_enabled: enabled })
            })

            if (res.ok) {
                const updated = await res.json()
                setModules(modules.map(m =>
                    m.module_id === moduleId ? { ...m, is_enabled: updated.is_enabled } : m
                ))
            }
        } catch (error) {
            console.error('Failed to toggle module:', error)
        } finally {
            setToggling(null)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
        )
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white">{t('modules.title')}</h1>
                <p className="text-gray-400 mt-2">{t('modules.description')}</p>
            </div>

            {/* Modules Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {modules.map((module) => (
                    <div
                        key={module.module_id}
                        className={`bg-gray-800 rounded-2xl p-6 border transition-all ${module.is_enabled
                            ? 'border-primary-500/50 ring-1 ring-primary-500/20'
                            : 'border-gray-700'
                            }`}
                    >
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <span className="text-3xl">{module.icon}</span>
                                <div>
                                    <h3 className="text-lg font-semibold text-white">{module.name}</h3>
                                    <p className="text-sm text-gray-400">{module.description}</p>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-700">
                            <span className={`text-sm font-medium ${module.is_enabled ? 'text-green-400' : 'text-gray-500'
                                }`}>
                                {module.is_enabled ? t('modules.enabled') : t('modules.disabled')}
                            </span>

                            <button
                                onClick={() => toggleModule(module.module_id, !module.is_enabled)}
                                disabled={toggling === module.module_id}
                                className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 ${module.is_enabled ? 'bg-primary-500' : 'bg-gray-600'
                                    } ${toggling === module.module_id ? 'opacity-50' : ''}`}
                            >
                                <span
                                    className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${module.is_enabled ? 'translate-x-5' : 'translate-x-0'
                                        }`}
                                />
                                {toggling === module.module_id && (
                                    <Loader2 className="absolute inset-0 m-auto w-4 h-4 text-white animate-spin" />
                                )}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
