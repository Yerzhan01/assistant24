import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { BirthdaysApi } from '../api/client'
import {
    Cake,
    Plus,
    X,
    Calendar,
    Gift,
    Loader2,
    Trash2,
    Edit,
    Bell,
    User,
    Phone
} from 'lucide-react'

interface Birthday {
    id: string
    name: string
    date: string
    phone?: string
    notes?: string
    reminder_days: number
    created_at: string
}

export default function Birthdays() {
    const { token } = useAuth()
    const [birthdays, setBirthdays] = useState<Birthday[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [selectedBirthday, setSelectedBirthday] = useState<Birthday | null>(null)
    const [filter, setFilter] = useState<'all' | 'upcoming' | 'today'>('all')

    const [formData, setFormData] = useState({
        name: '',
        date: '',
        phone: '',
        notes: '',
        reminder_days: 3
    })

    useEffect(() => {
        fetchBirthdays()
    }, [])

    const fetchBirthdays = async () => {
        setLoading(true)
        try {
            const res = await BirthdaysApi.getAll()
            setBirthdays(res.data.birthdays || [])
        } catch (err) {
            console.error('Failed to fetch birthdays:', err)
        } finally {
            setLoading(false)
        }
    }

    const saveBirthday = async () => {
        try {
            let res;
            if (selectedBirthday) {
                res = await BirthdaysApi.update(selectedBirthday.id, formData)
            } else {
                res = await BirthdaysApi.create(formData)
            }

            if (res.status === 200 || res.status === 201) {
                setShowModal(false)
                resetForm()
                fetchBirthdays()
            }
        } catch (err) {
            console.error('Failed to save birthday:', err)
        }
    }

    const deleteBirthday = async (id: string) => {
        try {
            await BirthdaysApi.delete(id)
            fetchBirthdays()
        } catch (err) {
            console.error('Failed to delete birthday:', err)
        }
    }

    const openEditModal = (birthday: Birthday) => {
        setSelectedBirthday(birthday)
        setFormData({
            name: birthday.name,
            date: birthday.date,
            phone: birthday.phone || '',
            notes: birthday.notes || '',
            reminder_days: birthday.reminder_days
        })
        setShowModal(true)
    }

    const openNewModal = () => {
        setSelectedBirthday(null)
        resetForm()
        setShowModal(true)
    }

    const resetForm = () => {
        setFormData({
            name: '',
            date: '',
            phone: '',
            notes: '',
            reminder_days: 3
        })
    }

    const getDaysUntil = (dateStr: string): number => {
        const today = new Date()
        const thisYear = today.getFullYear()
        const bdayDate = new Date(dateStr)
        bdayDate.setFullYear(thisYear)

        if (bdayDate < today) {
            bdayDate.setFullYear(thisYear + 1)
        }

        const diffTime = bdayDate.getTime() - today.getTime()
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    }

    const getAge = (dateStr: string): number => {
        const today = new Date()
        const bday = new Date(dateStr)
        let age = today.getFullYear() - bday.getFullYear()
        const m = today.getMonth() - bday.getMonth()
        if (m < 0 || (m === 0 && today.getDate() < bday.getDate())) {
            age--
        }
        return age + 1 // Next birthday age
    }

    const formatDate = (dateStr: string): string => {
        const date = new Date(dateStr)
        return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
    }

    const filteredBirthdays = birthdays
        .map(b => ({ ...b, daysUntil: getDaysUntil(b.date) }))
        .filter(b => {
            if (filter === 'today') return b.daysUntil === 0
            if (filter === 'upcoming') return b.daysUntil <= 30 && b.daysUntil > 0
            return true
        })
        .sort((a, b) => a.daysUntil - b.daysUntil)

    const todayCount = birthdays.filter(b => getDaysUntil(b.date) === 0).length
    const upcomingCount = birthdays.filter(b => {
        const days = getDaysUntil(b.date)
        return days <= 30 && days > 0
    }).length

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">🎂 Дни рождения</h1>
                    <p className="text-gray-400 mt-1">Напоминания о праздниках</p>
                </div>

                <button
                    onClick={openNewModal}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                               text-white font-medium rounded-xl transition"
                >
                    <Plus className="w-5 h-5" />
                    Добавить
                </button>
            </div>

            {/* Filters */}
            <div className="flex gap-2">
                <button
                    onClick={() => setFilter('all')}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${filter === 'all'
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                >
                    📅 Все ({birthdays.length})
                </button>
                <button
                    onClick={() => setFilter('today')}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${filter === 'today'
                        ? 'bg-pink-500 text-white'
                        : 'bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                >
                    🎉 Сегодня ({todayCount})
                </button>
                <button
                    onClick={() => setFilter('upcoming')}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${filter === 'upcoming'
                        ? 'bg-yellow-500 text-white'
                        : 'bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                >
                    ⏰ Скоро ({upcomingCount})
                </button>
            </div>

            {/* Birthdays List */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
            ) : filteredBirthdays.length === 0 ? (
                <div className="text-center py-12 text-gray-400 bg-gray-800 rounded-2xl border border-gray-700">
                    <Cake className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                    <p className="text-lg">Нет дней рождения</p>
                    <p className="text-sm mt-1">Добавьте первый</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredBirthdays.map(birthday => {
                        const daysUntil = birthday.daysUntil
                        const isToday = daysUntil === 0
                        const isSoon = daysUntil <= 7 && daysUntil > 0

                        return (
                            <div
                                key={birthday.id}
                                className={`bg-gray-800 rounded-2xl p-5 border transition group ${isToday
                                    ? 'border-pink-500 ring-2 ring-pink-500/20'
                                    : isSoon
                                        ? 'border-yellow-500/50'
                                        : 'border-gray-700 hover:border-gray-600'
                                    }`}
                            >
                                {/* Header */}
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${isToday ? 'bg-pink-500' : 'bg-gray-700'
                                            }`}>
                                            {isToday ? '🎉' : '🎂'}
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-semibold text-white">
                                                {birthday.name}
                                            </h3>
                                            <p className="text-sm text-gray-400">
                                                {formatDate(birthday.date)} • {getAge(birthday.date)} лет
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Days Until */}
                                <div className={`px-3 py-2 rounded-lg text-center mb-3 ${isToday
                                    ? 'bg-pink-500/20 text-pink-400'
                                    : isSoon
                                        ? 'bg-yellow-500/20 text-yellow-400'
                                        : 'bg-gray-700 text-gray-400'
                                    }`}>
                                    {isToday ? (
                                        <span className="font-medium">🎉 Сегодня!</span>
                                    ) : (
                                        <span>Через {daysUntil} дн.</span>
                                    )}
                                </div>

                                {/* Contact */}
                                {birthday.phone && (
                                    <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                                        <Phone className="w-4 h-4" />
                                        {birthday.phone}
                                    </div>
                                )}

                                {/* Notes */}
                                {birthday.notes && (
                                    <p className="text-sm text-gray-500 mb-3 line-clamp-2">
                                        {birthday.notes}
                                    </p>
                                )}

                                {/* Footer */}
                                <div className="flex items-center justify-between pt-3 border-t border-gray-700">
                                    <div className="flex items-center gap-1 text-xs text-gray-500">
                                        <Bell className="w-3 h-3" />
                                        За {birthday.reminder_days} дн.
                                    </div>

                                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                                        <button
                                            onClick={() => openEditModal(birthday)}
                                            className="p-1.5 hover:bg-gray-700 rounded-lg transition"
                                        >
                                            <Edit className="w-4 h-4 text-gray-400" />
                                        </button>
                                        <button
                                            onClick={() => deleteBirthday(birthday.id)}
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
                                {selectedBirthday ? 'Редактировать' : 'Добавить день рождения'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-gray-700 rounded-lg transition"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <User className="w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="Имя"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none focus:ring-2
                                               focus:ring-primary-500"
                                />
                            </div>

                            <div className="flex items-center gap-3">
                                <Calendar className="w-5 h-5 text-gray-400" />
                                <input
                                    type="date"
                                    value={formData.date}
                                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white focus:outline-none"
                                />
                            </div>

                            <div className="flex items-center gap-3">
                                <Phone className="w-5 h-5 text-gray-400" />
                                <input
                                    type="tel"
                                    value={formData.phone}
                                    onChange={e => setFormData({ ...formData, phone: e.target.value })}
                                    placeholder="Телефон (необязательно)"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            <textarea
                                value={formData.notes}
                                onChange={e => setFormData({ ...formData, notes: e.target.value })}
                                placeholder="Заметки (подарки, предпочтения...)"
                                rows={2}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none resize-none"
                            />

                            {/* Reminder */}
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">
                                    Напомнить за
                                </label>
                                <div className="flex gap-2">
                                    {[1, 3, 7, 14].map(days => (
                                        <button
                                            key={days}
                                            onClick={() => setFormData({ ...formData, reminder_days: days })}
                                            className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${formData.reminder_days === days
                                                ? 'bg-primary-500 text-white'
                                                : 'bg-gray-700 text-gray-400'
                                                }`}
                                        >
                                            {days} дн.
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
                                onClick={saveBirthday}
                                disabled={!formData.name || !formData.date}
                                className="flex-1 py-2 bg-primary-500 hover:bg-primary-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50"
                            >
                                {selectedBirthday ? 'Сохранить' : 'Добавить'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
