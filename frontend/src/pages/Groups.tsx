import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import {
    Users,
    Plus,
    Search,
    MessageCircle,
    X,
    Loader2,
    Bell,
    BellOff,
    Link
} from 'lucide-react'

interface WhatsAppGroup {
    id: string
    name: string
    description?: string
    participant_count: number
    owner_phone: string
    invite_link?: string
    notifications_enabled: boolean
    last_message?: string
    last_message_time?: string
    created_at: string
}

interface GroupParticipant {
    phone: string
    name?: string
    is_admin: boolean
}

export default function Groups() {
    const { token } = useAuth()
    const [groups, setGroups] = useState<WhatsAppGroup[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [showParticipantsModal, setShowParticipantsModal] = useState(false)
    const [selectedGroup, setSelectedGroup] = useState<WhatsAppGroup | null>(null)
    const [participants, setParticipants] = useState<GroupParticipant[]>([])
    const [searchTerm, setSearchTerm] = useState('')

    const [formData, setFormData] = useState({
        name: '',
        description: '',
        participants: ''
    })

    useEffect(() => {
        fetchGroups()
    }, [])

    const fetchGroups = async () => {
        setLoading(true)
        try {
            const res = await fetch('/api/v1/whatsapp/groups', {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                setGroups(data.groups || [])
            }
        } catch (err) {
            console.error('Failed to fetch groups:', err)
            // Demo data
            setGroups([
                {
                    id: '1',
                    name: 'Команда продаж',
                    description: 'Рабочий чат отдела продаж',
                    participant_count: 12,
                    owner_phone: '+77001234567',
                    notifications_enabled: true,
                    last_message: 'Отчёт за неделю готов',
                    last_message_time: '2 часа назад',
                    created_at: '2024-01-15'
                },
                {
                    id: '2',
                    name: 'Клиенты VIP',
                    description: 'Группа для VIP клиентов',
                    participant_count: 25,
                    owner_phone: '+77001234567',
                    notifications_enabled: false,
                    last_message: 'Спасибо за скидку!',
                    last_message_time: 'вчера',
                    created_at: '2024-02-10'
                },
                {
                    id: '3',
                    name: 'Партнёры',
                    description: 'Чат с бизнес-партнёрами',
                    participant_count: 8,
                    owner_phone: '+77001234567',
                    notifications_enabled: true,
                    last_message: 'Договор подписан',
                    last_message_time: '3 дня назад',
                    created_at: '2024-03-01'
                }
            ])
        } finally {
            setLoading(false)
        }
    }

    const createGroup = async () => {
        try {
            const phones = formData.participants.split(',').map(p => p.trim()).filter(Boolean)

            const res = await fetch('/api/v1/whatsapp/groups', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: formData.name,
                    description: formData.description,
                    participants: phones
                })
            })

            if (res.ok) {
                setShowModal(false)
                resetForm()
                fetchGroups()
            }
        } catch (err) {
            console.error('Failed to create group:', err)
        }
    }

    const toggleNotifications = async (group: WhatsAppGroup) => {
        try {
            await fetch(`/api/v1/whatsapp/groups/${group.id}/notifications`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enabled: !group.notifications_enabled })
            })
            fetchGroups()
        } catch (err) {
            console.error('Failed to toggle notifications:', err)
        }
    }

    const openParticipants = async (group: WhatsAppGroup) => {
        setSelectedGroup(group)
        setShowParticipantsModal(true)

        try {
            const res = await fetch(`/api/v1/whatsapp/groups/${group.id}/participants`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                setParticipants(data.participants || [])
            }
        } catch (err) {
            // Demo data
            setParticipants([
                { phone: '+77001234567', name: 'Асхат', is_admin: true },
                { phone: '+77007654321', name: 'Марат', is_admin: false },
                { phone: '+77009876543', name: 'Айгерим', is_admin: false },
            ])
        }
    }

    const sendMessage = async (_groupId: string) => {
        // Open chat with group
        window.open(`https://wa.me/?text=`, '_blank')
    }

    const getInviteLink = async (group: WhatsAppGroup) => {
        try {
            const res = await fetch(`/api/v1/whatsapp/groups/${group.id}/invite`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                navigator.clipboard.writeText(data.invite_link)
                alert('Ссылка скопирована!')
            }
        } catch (err) {
            console.error('Failed to get invite link:', err)
        }
    }

    const resetForm = () => {
        setFormData({ name: '', description: '', participants: '' })
    }

    const filteredGroups = groups.filter(group =>
        group.name.toLowerCase().includes(searchTerm.toLowerCase())
    )

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">🏢 Группы WhatsApp</h1>
                    <p className="text-gray-400 mt-1">{groups.length} групп</p>
                </div>

                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 
                               text-white font-medium rounded-xl transition"
                >
                    <Plus className="w-5 h-5" />
                    Новая группа
                </button>
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                    type="text"
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    placeholder="Поиск групп..."
                    className="w-full pl-11 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-xl
                               text-white placeholder-gray-400 focus:outline-none focus:ring-2
                               focus:ring-green-500"
                />
            </div>

            {/* Groups List */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-green-500 animate-spin" />
                </div>
            ) : filteredGroups.length === 0 ? (
                <div className="bg-gray-800 rounded-2xl border border-gray-700 p-12 text-center">
                    <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-lg text-gray-400">Нет групп</p>
                    <p className="text-sm text-gray-500 mt-1">Создайте первую группу WhatsApp</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredGroups.map(group => (
                        <div
                            key={group.id}
                            className="bg-gray-800 rounded-2xl border border-gray-700 p-5 
                                       hover:border-green-500/50 transition"
                        >
                            {/* Header */}
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-12 h-12 bg-green-500/20 rounded-xl 
                                                   flex items-center justify-center">
                                        <Users className="w-6 h-6 text-green-400" />
                                    </div>
                                    <div>
                                        <h3 className="text-white font-medium">{group.name}</h3>
                                        <p className="text-sm text-gray-400">
                                            {group.participant_count} участников
                                        </p>
                                    </div>
                                </div>

                                <button
                                    onClick={() => toggleNotifications(group)}
                                    className="p-2 hover:bg-gray-700 rounded-lg transition"
                                    title={group.notifications_enabled ? 'Отключить уведомления' : 'Включить уведомления'}
                                >
                                    {group.notifications_enabled
                                        ? <Bell className="w-4 h-4 text-green-400" />
                                        : <BellOff className="w-4 h-4 text-gray-500" />
                                    }
                                </button>
                            </div>

                            {/* Description */}
                            {group.description && (
                                <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                                    {group.description}
                                </p>
                            )}

                            {/* Last Message */}
                            {group.last_message && (
                                <div className="bg-gray-700/50 rounded-lg p-3 mb-4">
                                    <p className="text-sm text-gray-300 truncate">{group.last_message}</p>
                                    <p className="text-xs text-gray-500 mt-1">{group.last_message_time}</p>
                                </div>
                            )}

                            {/* Actions */}
                            <div className="flex gap-2">
                                <button
                                    onClick={() => sendMessage(group.id)}
                                    className="flex-1 flex items-center justify-center gap-2 py-2 
                                               bg-green-500/20 hover:bg-green-500/30 text-green-400 
                                               text-sm rounded-lg transition"
                                >
                                    <MessageCircle className="w-4 h-4" />
                                    Написать
                                </button>
                                <button
                                    onClick={() => openParticipants(group)}
                                    className="flex-1 flex items-center justify-center gap-2 py-2 
                                               bg-gray-700 hover:bg-gray-600 text-gray-300 
                                               text-sm rounded-lg transition"
                                >
                                    <Users className="w-4 h-4" />
                                    Участники
                                </button>
                                <button
                                    onClick={() => getInviteLink(group)}
                                    className="p-2 hover:bg-gray-600 rounded-lg transition"
                                    title="Скопировать ссылку"
                                >
                                    <Link className="w-4 h-4 text-gray-400" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Create Group Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-md border border-gray-700">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">Новая группа</h2>
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
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                                placeholder="Название группы *"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none"
                            />

                            <textarea
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Описание (опционально)"
                                rows={2}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none resize-none"
                            />

                            <div>
                                <label className="text-sm text-gray-400 block mb-2">
                                    Участники (через запятую)
                                </label>
                                <textarea
                                    value={formData.participants}
                                    onChange={e => setFormData({ ...formData, participants: e.target.value })}
                                    placeholder="+77001234567, +77007654321"
                                    rows={3}
                                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none resize-none"
                                />
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
                                onClick={createGroup}
                                disabled={!formData.name}
                                className="flex-1 py-2 bg-green-500 hover:bg-green-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50"
                            >
                                Создать
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Participants Modal */}
            {showParticipantsModal && selectedGroup && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-md border border-gray-700">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-semibold text-white">{selectedGroup.name}</h2>
                                <p className="text-sm text-gray-400">{participants.length} участников</p>
                            </div>
                            <button
                                onClick={() => setShowParticipantsModal(false)}
                                className="p-2 hover:bg-gray-700 rounded-lg transition"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-2 max-h-80 overflow-y-auto">
                            {participants.map((p, i) => (
                                <div
                                    key={i}
                                    className="flex items-center justify-between p-3 bg-gray-700 rounded-xl"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-gray-600 rounded-full 
                                                       flex items-center justify-center text-white font-medium">
                                            {(p.name || p.phone)[0]}
                                        </div>
                                        <div>
                                            <p className="text-white">{p.name || p.phone}</p>
                                            {p.name && <p className="text-sm text-gray-400">{p.phone}</p>}
                                        </div>
                                    </div>
                                    {p.is_admin && (
                                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 
                                                        text-xs rounded-full">
                                            Админ
                                        </span>
                                    )}
                                </div>
                            ))}
                        </div>

                        <button
                            onClick={() => setShowParticipantsModal(false)}
                            className="w-full mt-4 py-2 bg-gray-700 hover:bg-gray-600 text-white 
                                       rounded-xl transition"
                        >
                            Закрыть
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
