import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { ContactsApi } from '../api/client'
import {
    User,
    Phone,
    Mail,
    Building,
    Plus,
    Search,
    X,
    Calendar,
    MessageCircle,
    Loader2,
    Edit,
    Trash2,
    Star,
    StarOff
} from 'lucide-react'

interface Contact {
    id: string
    name: string
    phone?: string
    email?: string
    company?: string
    position?: string
    notes?: string
    is_favorite: boolean
    created_at: string
}

export default function Contacts() {
    const { } = useAuth()
    const [contacts, setContacts] = useState<Contact[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [selectedContact, setSelectedContact] = useState<Contact | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filter, setFilter] = useState<'all' | 'favorites'>('all')

    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        email: '',
        company: '',
        position: '',
        notes: ''
    })

    useEffect(() => {
        fetchContacts()
    }, [])

    const fetchContacts = async () => {
        setLoading(true)
        try {
            const res = await ContactsApi.getAll()
            console.log('📦 Contacts API Response:', res.data)
            const contactsData = Array.isArray(res.data) ? res.data : (res.data.contacts || [])
            setContacts(contactsData)
        } catch (err) {
            console.error('Failed to fetch contacts:', err)
        } finally {
            setLoading(false)
        }
    }

    const saveContact = async () => {
        try {
            let res;
            if (selectedContact) {
                res = await ContactsApi.update(selectedContact.id, formData)
            } else {
                res = await ContactsApi.create(formData)
            }

            if (res.status === 200 || res.status === 201) {
                setShowModal(false)
                resetForm()
                fetchContacts()
            }
        } catch (err) {
            console.error('Failed to save contact:', err)
        }
    }

    const deleteContact = async (id: string) => {
        try {
            await ContactsApi.delete(id)
            fetchContacts()
        } catch (err) {
            console.error('Failed to delete contact:', err)
        }
    }

    const toggleFavorite = async (contact: Contact) => {
        try {
            await ContactsApi.update(contact.id, { is_favorite: !contact.is_favorite })
            fetchContacts()
        } catch (err) {
            console.error('Failed to toggle favorite:', err)
        }
    }

    const openEditModal = (contact: Contact) => {
        setSelectedContact(contact)
        setFormData({
            name: contact.name,
            phone: contact.phone || '',
            email: contact.email || '',
            company: contact.company || '',
            position: contact.position || '',
            notes: contact.notes || ''
        })
        setShowModal(true)
    }

    const openNewModal = () => {
        setSelectedContact(null)
        resetForm()
        setShowModal(true)
    }

    const resetForm = () => {
        setFormData({
            name: '',
            phone: '',
            email: '',
            company: '',
            position: '',
            notes: ''
        })
    }

    const filteredContacts = contacts.filter(contact => {
        if (filter === 'favorites' && !contact.is_favorite) return false
        if (searchTerm) {
            const term = searchTerm.toLowerCase()
            return contact.name.toLowerCase().includes(term) ||
                contact.company?.toLowerCase().includes(term) ||
                contact.phone?.includes(term)
        }
        return true
    })

    const getInitials = (name: string) => {
        return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    }

    const getAvatarColor = (name: string) => {
        const colors = [
            'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-red-500',
            'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-cyan-500'
        ]
        const index = name.charCodeAt(0) % colors.length
        return colors[index]
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">📒 Контакты</h1>
                    <p className="text-gray-400 mt-1">{contacts.length} контактов</p>
                </div>

                <button
                    onClick={openNewModal}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                               text-white font-medium rounded-xl transition"
                >
                    <Plus className="w-5 h-5" />
                    Новый контакт
                </button>
            </div>

            {/* Search & Filters */}
            <div className="flex items-center gap-4">
                <div className="flex-1 relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        placeholder="Поиск по имени, компании или телефону..."
                        className="w-full pl-11 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-xl
                                   text-white placeholder-gray-400 focus:outline-none focus:ring-2
                                   focus:ring-primary-500"
                    />
                </div>

                <div className="flex bg-gray-800 rounded-xl p-1">
                    {(['all', 'favorites'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${filter === f
                                ? 'bg-primary-500 text-white'
                                : 'text-gray-400 hover:text-white'
                                }`}
                        >
                            {f === 'all' ? 'Все' : <><Star className="w-4 h-4" /> Избранные</>}
                        </button>
                    ))}
                </div>
            </div>

            {/* Contacts Grid */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
            ) : filteredContacts.length === 0 ? (
                <div className="bg-gray-800 rounded-2xl border border-gray-700 p-12 text-center">
                    <User className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-lg text-gray-400">Нет контактов</p>
                    <p className="text-sm text-gray-500 mt-1">Добавьте первый контакт</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredContacts.map(contact => (
                        <div
                            key={contact.id}
                            className="bg-gray-800 rounded-2xl border border-gray-700 p-5 
                                       hover:border-gray-600 transition"
                        >
                            <div className="flex items-start gap-4">
                                {/* Avatar */}
                                <div className={`w-12 h-12 rounded-xl ${getAvatarColor(contact.name)} 
                                               flex items-center justify-center text-white font-semibold`}>
                                    {getInitials(contact.name)}
                                </div>

                                {/* Info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-white font-medium truncate">{contact.name}</h3>
                                        {contact.is_favorite && (
                                            <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                                        )}
                                    </div>
                                    {contact.company && (
                                        <p className="text-sm text-gray-400 truncate">
                                            {contact.position ? `${contact.position}, ` : ''}{contact.company}
                                        </p>
                                    )}
                                </div>

                                {/* Actions */}
                                <div className="flex items-center gap-1">
                                    <button
                                        onClick={() => toggleFavorite(contact)}
                                        className="p-2 hover:bg-gray-700 rounded-lg transition"
                                    >
                                        {contact.is_favorite
                                            ? <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                                            : <StarOff className="w-4 h-4 text-gray-500" />
                                        }
                                    </button>
                                </div>
                            </div>

                            {/* Contact Details */}
                            <div className="mt-4 space-y-2">
                                {contact.phone && (
                                    <a
                                        href={`tel:${contact.phone}`}
                                        className="flex items-center gap-2 text-sm text-gray-400 
                                                   hover:text-white transition"
                                    >
                                        <Phone className="w-4 h-4" />
                                        {contact.phone}
                                    </a>
                                )}
                                {contact.email && (
                                    <a
                                        href={`mailto:${contact.email}`}
                                        className="flex items-center gap-2 text-sm text-gray-400 
                                                   hover:text-white transition"
                                    >
                                        <Mail className="w-4 h-4" />
                                        {contact.email}
                                    </a>
                                )}
                            </div>

                            {/* Action Buttons */}
                            <div className="flex gap-2 mt-4 pt-4 border-t border-gray-700">
                                <button className="flex-1 flex items-center justify-center gap-2 py-2 
                                                   bg-gray-700 hover:bg-gray-600 text-gray-300 
                                                   text-sm rounded-lg transition">
                                    <Calendar className="w-4 h-4" />
                                    Встреча
                                </button>
                                <button className="flex-1 flex items-center justify-center gap-2 py-2 
                                                   bg-gray-700 hover:bg-gray-600 text-gray-300 
                                                   text-sm rounded-lg transition">
                                    <MessageCircle className="w-4 h-4" />
                                    Сообщение
                                </button>
                                <button
                                    onClick={() => openEditModal(contact)}
                                    className="p-2 hover:bg-gray-600 rounded-lg transition"
                                >
                                    <Edit className="w-4 h-4 text-gray-400" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-md border border-gray-700">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">
                                {selectedContact ? 'Редактировать' : 'Новый контакт'}
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
                                    placeholder="Имя *"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            <div className="flex items-center gap-3">
                                <Phone className="w-5 h-5 text-gray-400" />
                                <input
                                    type="tel"
                                    value={formData.phone}
                                    onChange={e => setFormData({ ...formData, phone: e.target.value })}
                                    placeholder="+7 (___) ___-__-__"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            <div className="flex items-center gap-3">
                                <Mail className="w-5 h-5 text-gray-400" />
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                                    placeholder="Email"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            <div className="flex items-center gap-3">
                                <Building className="w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    value={formData.company}
                                    onChange={e => setFormData({ ...formData, company: e.target.value })}
                                    placeholder="Компания"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            <input
                                type="text"
                                value={formData.position}
                                onChange={e => setFormData({ ...formData, position: e.target.value })}
                                placeholder="Должность"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none"
                            />

                            <textarea
                                value={formData.notes}
                                onChange={e => setFormData({ ...formData, notes: e.target.value })}
                                placeholder="Заметки..."
                                rows={2}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none resize-none"
                            />
                        </div>

                        <div className="flex gap-3 mt-6">
                            {selectedContact && (
                                <button
                                    onClick={() => {
                                        deleteContact(selectedContact.id)
                                        setShowModal(false)
                                    }}
                                    className="px-4 py-2 text-red-400 hover:bg-red-500/20 rounded-lg transition"
                                >
                                    <Trash2 className="w-5 h-5" />
                                </button>
                            )}
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 py-2 text-gray-400 hover:bg-gray-700 rounded-xl transition"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={saveContact}
                                disabled={!formData.name}
                                className="flex-1 py-2 bg-primary-500 hover:bg-primary-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50"
                            >
                                {selectedContact ? 'Сохранить' : 'Создать'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
