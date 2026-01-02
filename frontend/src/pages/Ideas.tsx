import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { IdeasApi } from '../api/client'
import {
    Lightbulb,
    Plus,
    X,
    Star,
    Tag,
    Loader2,
    Trash2,
    Edit,
    Sparkles,
    TrendingUp,
    Zap
} from 'lucide-react'

interface Idea {
    id: string
    title: string
    description?: string
    category: string
    priority: 'low' | 'medium' | 'high'
    status: 'new' | 'in_progress' | 'implemented' | 'archived'
    created_at: string
}

const categories = [
    { id: 'business', label: 'Бизнес', icon: TrendingUp, color: 'bg-green-500' },
    { id: 'product', label: 'Продукт', icon: Sparkles, color: 'bg-purple-500' },
    { id: 'marketing', label: 'Маркетинг', icon: Zap, color: 'bg-yellow-500' },
    { id: 'other', label: 'Другое', icon: Lightbulb, color: 'bg-blue-500' }
]

export default function Ideas() {
    const { token } = useAuth()
    const [ideas, setIdeas] = useState<Idea[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null)
    const [filter, setFilter] = useState<string>('all')

    const [formData, setFormData] = useState({
        title: '',
        description: '',
        category: 'business',
        priority: 'medium' as Idea['priority']
    })

    useEffect(() => {
        fetchIdeas()
    }, [])

    const fetchIdeas = async () => {
        setLoading(true)
        try {
            const res = await IdeasApi.getAll()
            setIdeas(res.data.ideas || [])
        } catch (err) {
            console.error('Failed to fetch ideas:', err)
        } finally {
            setLoading(false)
        }
    }

    const saveIdea = async () => {
        try {
            let res;
            if (selectedIdea) {
                res = await IdeasApi.update(selectedIdea.id, formData)
            } else {
                res = await IdeasApi.create(formData)
            }

            if (res.status === 200 || res.status === 201) {
                setShowModal(false)
                resetForm()
                fetchIdeas()
            }
        } catch (err) {
            console.error('Failed to save idea:', err)
        }
    }

    const deleteIdea = async (id: string) => {
        try {
            await IdeasApi.delete(id)
            fetchIdeas()
        } catch (err) {
            console.error('Failed to delete idea:', err)
        }
    }

    const openEditModal = (idea: Idea) => {
        setSelectedIdea(idea)
        setFormData({
            title: idea.title,
            description: idea.description || '',
            category: idea.category,
            priority: idea.priority
        })
        setShowModal(true)
    }

    const openNewModal = () => {
        setSelectedIdea(null)
        resetForm()
        setShowModal(true)
    }

    const resetForm = () => {
        setFormData({
            title: '',
            description: '',
            category: 'business',
            priority: 'medium'
        })
    }

    const filteredIdeas = ideas.filter(idea => {
        if (filter === 'all') return true
        return idea.category === filter
    })

    const getCategoryInfo = (categoryId: string) => {
        return categories.find(c => c.id === categoryId) || categories[3]
    }

    const priorityStars = {
        low: 1,
        medium: 2,
        high: 3
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">💡 Идеи</h1>
                    <p className="text-gray-400 mt-1">Банк идей с приоритетами</p>
                </div>

                <button
                    onClick={openNewModal}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                               text-white font-medium rounded-xl transition"
                >
                    <Plus className="w-5 h-5" />
                    Новая идея
                </button>
            </div>

            {/* Category Filters */}
            <div className="flex gap-2 flex-wrap">
                <button
                    onClick={() => setFilter('all')}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition ${filter === 'all'
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                >
                    Все ({ideas.length})
                </button>
                {categories.map(cat => {
                    const count = ideas.filter(i => i.category === cat.id).length
                    const CatIcon = cat.icon
                    return (
                        <button
                            key={cat.id}
                            onClick={() => setFilter(cat.id)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${filter === cat.id
                                ? `${cat.color} text-white`
                                : 'bg-gray-800 text-gray-400 hover:text-white'
                                }`}
                        >
                            <CatIcon className="w-4 h-4" />
                            {cat.label} ({count})
                        </button>
                    )
                })}
            </div>

            {/* Ideas Grid */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
            ) : filteredIdeas.length === 0 ? (
                <div className="text-center py-12 text-gray-400 bg-gray-800 rounded-2xl border border-gray-700">
                    <Lightbulb className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                    <p className="text-lg">Нет идей</p>
                    <p className="text-sm mt-1">Добавьте первую идею</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredIdeas.map(idea => {
                        const catInfo = getCategoryInfo(idea.category)
                        const CatIcon = catInfo.icon

                        return (
                            <div
                                key={idea.id}
                                className="bg-gray-800 rounded-2xl p-5 border border-gray-700 hover:border-gray-600 transition group"
                            >
                                {/* Category Badge */}
                                <div className="flex items-center justify-between mb-3">
                                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${catInfo.color} bg-opacity-20 text-white`}>
                                        <CatIcon className="w-3 h-3" />
                                        {catInfo.label}
                                    </div>

                                    {/* Priority Stars */}
                                    <div className="flex gap-0.5">
                                        {[...Array(3)].map((_, i) => (
                                            <Star
                                                key={i}
                                                className={`w-4 h-4 ${i < priorityStars[idea.priority]
                                                    ? 'text-yellow-400 fill-yellow-400'
                                                    : 'text-gray-600'
                                                    }`}
                                            />
                                        ))}
                                    </div>
                                </div>

                                {/* Title */}
                                <h3 className="text-lg font-semibold text-white mb-2">
                                    {idea.title}
                                </h3>

                                {/* Description */}
                                {idea.description && (
                                    <p className="text-gray-400 text-sm line-clamp-2 mb-4">
                                        {idea.description}
                                    </p>
                                )}

                                {/* Footer */}
                                <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-700">
                                    <span className="text-xs text-gray-500">
                                        {new Date(idea.created_at).toLocaleDateString('ru-RU')}
                                    </span>

                                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                                        <button
                                            onClick={() => openEditModal(idea)}
                                            className="p-1.5 hover:bg-gray-700 rounded-lg transition"
                                        >
                                            <Edit className="w-4 h-4 text-gray-400" />
                                        </button>
                                        <button
                                            onClick={() => deleteIdea(idea.id)}
                                            className="p-1.5 hover:bg-red-500/20 rounded-lg transition"
                                        >
                                            <Trash2 className="w-4 h-4 text-red-400" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-md border border-gray-700">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">
                                {selectedIdea ? 'Редактировать идею' : 'Новая идея'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-gray-700 rounded-lg transition"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <input
                                type="text"
                                value={formData.title}
                                onChange={e => setFormData({ ...formData, title: e.target.value })}
                                placeholder="Название идеи"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none focus:ring-2
                                           focus:ring-primary-500"
                            />

                            <textarea
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Описание идеи..."
                                rows={4}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none resize-none"
                            />

                            {/* Category */}
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Категория</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {categories.map(cat => {
                                        const CatIcon = cat.icon
                                        return (
                                            <button
                                                key={cat.id}
                                                onClick={() => setFormData({ ...formData, category: cat.id })}
                                                className={`py-2 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2 ${formData.category === cat.id
                                                    ? `${cat.color} text-white`
                                                    : 'bg-gray-700 text-gray-400'
                                                    }`}
                                            >
                                                <CatIcon className="w-4 h-4" />
                                                {cat.label}
                                            </button>
                                        )
                                    })}
                                </div>
                            </div>

                            {/* Priority */}
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Приоритет</label>
                                <div className="flex gap-2">
                                    {(['low', 'medium', 'high'] as const).map(p => (
                                        <button
                                            key={p}
                                            onClick={() => setFormData({ ...formData, priority: p })}
                                            className={`flex-1 py-2 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2 ${formData.priority === p
                                                ? 'bg-yellow-500 text-white'
                                                : 'bg-gray-700 text-gray-400'
                                                }`}
                                        >
                                            {[...Array(priorityStars[p])].map((_, i) => (
                                                <Star key={i} className="w-4 h-4 fill-current" />
                                            ))}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 py-2 text-gray-400 hover:bg-gray-700 rounded-xl transition"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={saveIdea}
                                disabled={!formData.title}
                                className="flex-1 py-2 bg-primary-500 hover:bg-primary-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50"
                            >
                                {selectedIdea ? 'Сохранить' : 'Создать'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
