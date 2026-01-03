import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { CalendarApi } from '../api/client'
import {
    ChevronLeft,
    ChevronRight,
    Plus,
    X,
    Clock,
    MapPin,
    User,
    Loader2
} from 'lucide-react'

interface Meeting {
    id: string
    title: string
    start_time: string
    end_time: string
    location?: string
    attendee_name?: string
    color?: string
    description?: string
    is_all_day?: boolean
}

interface CalendarDay {
    date: Date
    isCurrentMonth: boolean
    isToday: boolean
    events: Meeting[]
}

type ViewMode = 'month' | 'week' | 'day'

export default function Calendar() {
    useAuth()
    const [currentDate, setCurrentDate] = useState(new Date())
    const [viewMode, setViewMode] = useState<ViewMode>('month')
    const [events, setEvents] = useState<Meeting[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [, setSelectedDate] = useState<Date | null>(null)
    const [selectedEvent, setSelectedEvent] = useState<Meeting | null>(null)

    // Form state
    const [formData, setFormData] = useState({
        title: '',
        date: '',
        start_time: '09:00',
        end_time: '10:00',
        location: '',
        attendee_name: '',
        description: '',
        color: '#3B82F6'
    })

    const colors = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
        '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'
    ]

    // Fetch events
    const fetchEvents = useCallback(async () => {
        setLoading(true)
        try {
            const start = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1)
            const end = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0)

            const res = await CalendarApi.getEvents(start.toISOString(), end.toISOString())
            setEvents(res.data.events || res.data || [])
        } catch (err) {
            console.error('Failed to fetch events:', err)
        } finally {
            setLoading(false)
        }
    }, [currentDate])

    useEffect(() => {
        fetchEvents()
    }, [fetchEvents])

    // Calendar grid generation
    const generateCalendarDays = (): CalendarDay[] => {
        const year = currentDate.getFullYear()
        const month = currentDate.getMonth()
        const firstDay = new Date(year, month, 1)
        const lastDay = new Date(year, month + 1, 0)
        const today = new Date()

        const days: CalendarDay[] = []

        // Previous month days
        const startDay = firstDay.getDay() || 7
        for (let i = startDay - 1; i > 0; i--) {
            const date = new Date(year, month, 1 - i)
            days.push({
                date,
                isCurrentMonth: false,
                isToday: false,
                events: getEventsForDate(date)
            })
        }

        // Current month days
        for (let i = 1; i <= lastDay.getDate(); i++) {
            const date = new Date(year, month, i)
            days.push({
                date,
                isCurrentMonth: true,
                isToday: date.toDateString() === today.toDateString(),
                events: getEventsForDate(date)
            })
        }

        // Next month days
        const remaining = 42 - days.length
        for (let i = 1; i <= remaining; i++) {
            const date = new Date(year, month + 1, i)
            days.push({
                date,
                isCurrentMonth: false,
                isToday: false,
                events: getEventsForDate(date)
            })
        }

        return days
    }

    const getEventsForDate = (date: Date): Meeting[] => {
        return events.filter(event => {
            const eventDate = new Date(event.start_time)
            return eventDate.toDateString() === date.toDateString()
        })
    }

    const formatTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    // Week view helpers
    const getWeekDays = (): Date[] => {
        const startOfWeek = new Date(currentDate)
        const day = startOfWeek.getDay()
        const diff = startOfWeek.getDate() - day + (day === 0 ? -6 : 1) // Adjust for Monday start
        startOfWeek.setDate(diff)

        return Array.from({ length: 7 }, (_, i) => {
            const date = new Date(startOfWeek)
            date.setDate(startOfWeek.getDate() + i)
            return date
        })
    }

    const getEventsForHour = (date: Date, hour: number): Meeting[] => {
        return events.filter(event => {
            const eventDate = new Date(event.start_time)
            const eventHour = eventDate.getHours()
            return eventDate.toDateString() === date.toDateString() && eventHour === hour
        })
    }

    const getEventTopOffset = (event: Meeting): number => {
        const eventDate = new Date(event.start_time)
        return (eventDate.getMinutes() / 60) * 100
    }

    const getEventHeight = (event: Meeting): number => {
        const start = new Date(event.start_time)
        const end = new Date(event.end_time)
        const durationMinutes = (end.getTime() - start.getTime()) / (1000 * 60)
        return (durationMinutes / 60) * 100
    }

    const openNewEventAtTime = (date: Date, hour: number) => {
        setSelectedEvent(null)
        setSelectedDate(date)
        const dateStr = date.toISOString().split('T')[0]
        const startTime = `${hour.toString().padStart(2, '0')}:00`
        const endTime = `${(hour + 1).toString().padStart(2, '0')}:00`
        setFormData({
            title: '',
            date: dateStr,
            start_time: startTime,
            end_time: endTime,
            location: '',
            attendee_name: '',
            description: '',
            color: '#3B82F6'
        })
        setShowModal(true)
    }

    // Navigation
    const navigate = (direction: number) => {
        if (viewMode === 'month') {
            setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + direction, 1))
        } else if (viewMode === 'week') {
            setCurrentDate(new Date(currentDate.getTime() + direction * 7 * 24 * 60 * 60 * 1000))
        } else {
            setCurrentDate(new Date(currentDate.getTime() + direction * 24 * 60 * 60 * 1000))
        }
    }

    const goToToday = () => setCurrentDate(new Date())

    // Modal handlers
    const openNewEvent = (date?: Date) => {
        setSelectedEvent(null)
        setSelectedDate(date || new Date())
        setFormData({
            title: '',
            date: (date || new Date()).toISOString().split('T')[0],
            start_time: '09:00',
            end_time: '10:00',
            location: '',
            attendee_name: '',
            description: '',
            color: '#3B82F6'
        })
        setShowModal(true)
    }

    const openEditEvent = (event: Meeting) => {
        setSelectedEvent(event)
        const startDate = new Date(event.start_time)
        const endDate = new Date(event.end_time)
        setFormData({
            title: event.title,
            date: startDate.toISOString().split('T')[0],
            start_time: startDate.toTimeString().slice(0, 5),
            end_time: endDate.toTimeString().slice(0, 5),
            location: event.location || '',
            attendee_name: event.attendee_name || '',
            description: event.description || '',
            color: event.color || '#3B82F6'
        })
        setShowModal(true)
    }

    const saveEvent = async () => {
        const body = {
            title: formData.title,
            start_time: `${formData.date}T${formData.start_time}:00`,
            end_time: `${formData.date}T${formData.end_time}:00`,
            location: formData.location || null,
            attendee_name: formData.attendee_name || null,
            description: formData.description || null,
            color: formData.color
        }

        try {
            if (selectedEvent) {
                await CalendarApi.updateEvent(selectedEvent.id, body)
            } else {
                await CalendarApi.createEvent(body)
            }
            setShowModal(false)
            fetchEvents()
        } catch (err) {
            console.error('Failed to save event:', err)
        }
    }

    const deleteEvent = async () => {
        if (!selectedEvent) return

        try {
            await CalendarApi.deleteEvent(selectedEvent.id)
            setShowModal(false)
            fetchEvents()
        } catch (err) {
            console.error('Failed to delete event:', err)
        }
    }

    const monthNames = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

    const calendarDays = generateCalendarDays()

    return (
        <div className="space-y-3 md:space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center justify-between md:block">
                    <div>
                        <h1 className="text-xl md:text-2xl lg:text-3xl font-bold text-white">📅 Календарь</h1>
                        <p className="text-gray-400 text-sm md:text-base">
                            {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
                        </p>
                    </div>
                    {/* Mobile Add Button */}
                    <button
                        onClick={() => openNewEvent()}
                        className="md:hidden p-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg"
                    >
                        <Plus className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex flex-wrap items-center gap-2 md:gap-4">
                    {/* View Mode Switcher */}
                    <div className="flex bg-gray-800 rounded-lg md:rounded-xl p-0.5 md:p-1">
                        {(['month', 'week', 'day'] as ViewMode[]).map(mode => (
                            <button
                                key={mode}
                                onClick={() => setViewMode(mode)}
                                className={`px-2 md:px-4 py-1.5 md:py-2 rounded-md md:rounded-lg text-xs md:text-sm font-medium transition ${viewMode === mode
                                    ? 'bg-primary-500 text-white'
                                    : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                {mode === 'month' ? 'М' : mode === 'week' ? 'Н' : 'Д'}
                                <span className="hidden md:inline">{mode === 'month' ? 'есяц' : mode === 'week' ? 'еделя' : 'ень'}</span>
                            </button>
                        ))}
                    </div>

                    {/* Navigation */}
                    <div className="flex items-center gap-1 md:gap-2">
                        <button
                            onClick={() => navigate(-1)}
                            className="p-1.5 md:p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
                        >
                            <ChevronLeft className="w-4 h-4 md:w-5 md:h-5 text-white" />
                        </button>
                        <button
                            onClick={goToToday}
                            className="px-2 md:px-4 py-1.5 md:py-2 bg-gray-800 hover:bg-gray-700 text-white text-xs md:text-sm rounded-lg transition"
                        >
                            Сегодня
                        </button>
                        <button
                            onClick={() => navigate(1)}
                            className="p-1.5 md:p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
                        >
                            <ChevronRight className="w-4 h-4 md:w-5 md:h-5 text-white" />
                        </button>
                    </div>

                    {/* Add Event - Desktop */}
                    <button
                        onClick={() => openNewEvent()}
                        className="hidden md:flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                                   text-white font-medium rounded-xl transition"
                    >
                        <Plus className="w-5 h-5" />
                        Новое событие
                    </button>
                </div>
            </div>

            {/* Calendar Grid */}
            {loading ? (
                <div className="flex items-center justify-center h-96">
                    <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
            ) : viewMode === 'month' ? (
                <div className="bg-gray-800 rounded-xl md:rounded-2xl border border-gray-700 overflow-hidden">
                    {/* Day Headers */}
                    <div className="grid grid-cols-7 bg-gray-900">
                        {dayNames.map(day => (
                            <div key={day} className="py-2 md:py-3 text-center text-xs md:text-sm font-medium text-gray-400">
                                {day}
                            </div>
                        ))}
                    </div>

                    {/* Calendar Days */}
                    <div className="grid grid-cols-7">
                        {calendarDays.map((day, index) => (
                            <div
                                key={index}
                                onClick={() => openNewEvent(day.date)}
                                className={`min-h-16 md:min-h-28 p-1 md:p-2 border-t border-r border-gray-700 cursor-pointer
                                           hover:bg-gray-700/50 transition ${!day.isCurrentMonth ? 'bg-gray-900/50' : ''
                                    } ${index % 7 === 0 ? 'border-l' : ''}`}
                            >
                                <div className={`text-sm font-medium mb-1 ${day.isToday
                                    ? 'w-7 h-7 bg-primary-500 text-white rounded-full flex items-center justify-center'
                                    : day.isCurrentMonth
                                        ? 'text-white'
                                        : 'text-gray-600'
                                    }`}>
                                    {day.date.getDate()}
                                </div>

                                {/* Events */}
                                <div className="space-y-1">
                                    {day.events.slice(0, 3).map(event => (
                                        <div
                                            key={event.id}
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                openEditEvent(event)
                                            }}
                                            style={{ backgroundColor: event.color || '#3B82F6' }}
                                            className="px-2 py-1 rounded text-xs text-white truncate cursor-pointer
                                                       hover:opacity-80 transition"
                                        >
                                            {formatTime(event.start_time)} {event.title}
                                        </div>
                                    ))}
                                    {day.events.length > 3 && (
                                        <div className="text-xs text-gray-400 px-2">
                                            +{day.events.length - 3} ещё
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ) : viewMode === 'week' ? (
                /* Week View */
                <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
                    {/* Week Header */}
                    <div className="grid grid-cols-8 bg-gray-900 border-b border-gray-700">
                        <div className="py-3 px-2 text-center text-sm font-medium text-gray-500">
                            {/* Time column header */}
                        </div>
                        {getWeekDays().map((day, index) => (
                            <div key={index} className="py-3 text-center border-l border-gray-700">
                                <div className="text-xs text-gray-500">{dayNames[index]}</div>
                                <div className={`text-lg font-semibold mt-1 ${day.toDateString() === new Date().toDateString()
                                    ? 'w-8 h-8 bg-primary-500 text-white rounded-full flex items-center justify-center mx-auto'
                                    : 'text-white'
                                    }`}>
                                    {day.getDate()}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Week Grid */}
                    <div className="overflow-y-auto max-h-[600px]">
                        {Array.from({ length: 24 }, (_, hour) => (
                            <div key={hour} className="grid grid-cols-8 border-b border-gray-700/50">
                                {/* Time Label */}
                                <div className="py-3 px-2 text-xs text-gray-500 text-right pr-3 border-r border-gray-700">
                                    {hour.toString().padStart(2, '0')}:00
                                </div>
                                {/* Day columns */}
                                {getWeekDays().map((day, dayIndex) => {
                                    const dayEvents = getEventsForHour(day, hour)
                                    return (
                                        <div
                                            key={dayIndex}
                                            onClick={() => openNewEventAtTime(day, hour)}
                                            className="min-h-12 border-l border-gray-700/50 hover:bg-gray-700/30 
                                                       cursor-pointer relative transition"
                                        >
                                            {dayEvents.map(event => (
                                                <div
                                                    key={event.id}
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        openEditEvent(event)
                                                    }}
                                                    style={{
                                                        backgroundColor: event.color || '#3B82F6',
                                                        top: `${getEventTopOffset(event)}%`,
                                                        height: `${Math.min(getEventHeight(event), 100)}%`
                                                    }}
                                                    className="absolute left-0.5 right-0.5 px-1 py-0.5 rounded text-xs 
                                                               text-white truncate cursor-pointer hover:opacity-80 
                                                               transition z-10"
                                                >
                                                    {event.title}
                                                </div>
                                            ))}
                                        </div>
                                    )
                                })}
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                /* Day View */
                <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
                    {/* Day Header */}
                    <div className="bg-gray-900 border-b border-gray-700 p-4 text-center">
                        <div className="text-sm text-gray-400">
                            {dayNames[currentDate.getDay() === 0 ? 6 : currentDate.getDay() - 1]}
                        </div>
                        <div className={`text-3xl font-bold mt-1 ${currentDate.toDateString() === new Date().toDateString()
                            ? 'text-primary-400'
                            : 'text-white'
                            }`}>
                            {currentDate.getDate()}
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                            {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
                        </div>
                    </div>

                    {/* Day Grid */}
                    <div className="overflow-y-auto max-h-[600px]">
                        {Array.from({ length: 24 }, (_, hour) => {
                            const hourEvents = getEventsForHour(currentDate, hour)
                            return (
                                <div
                                    key={hour}
                                    onClick={() => openNewEventAtTime(currentDate, hour)}
                                    className="flex border-b border-gray-700/50 hover:bg-gray-700/30 
                                               cursor-pointer transition min-h-16"
                                >
                                    {/* Time Label */}
                                    <div className="w-20 py-4 px-3 text-sm text-gray-500 text-right 
                                                    border-r border-gray-700 flex-shrink-0">
                                        {hour.toString().padStart(2, '0')}:00
                                    </div>
                                    {/* Events */}
                                    <div className="flex-1 p-1 relative">
                                        {hourEvents.map(event => (
                                            <div
                                                key={event.id}
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    openEditEvent(event)
                                                }}
                                                style={{ backgroundColor: event.color || '#3B82F6' }}
                                                className="px-3 py-2 rounded-lg text-white cursor-pointer 
                                                           hover:opacity-80 transition mb-1"
                                            >
                                                <div className="font-medium">{event.title}</div>
                                                <div className="text-xs opacity-80 flex items-center gap-2 mt-1">
                                                    <Clock className="w-3 h-3" />
                                                    {formatTime(event.start_time)} - {formatTime(event.end_time)}
                                                    {event.location && (
                                                        <>
                                                            <MapPin className="w-3 h-3 ml-2" />
                                                            {event.location}
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* Event Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-md border border-gray-700">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">
                                {selectedEvent ? 'Редактировать' : 'Новое событие'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-gray-700 rounded-lg transition"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* Title */}
                            <input
                                type="text"
                                value={formData.title}
                                onChange={e => setFormData({ ...formData, title: e.target.value })}
                                placeholder="Название события"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none focus:ring-2
                                           focus:ring-primary-500"
                            />

                            {/* Date & Time */}
                            <div className="grid grid-cols-3 gap-3">
                                <input
                                    type="date"
                                    value={formData.date}
                                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                                    className="px-3 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                                />
                                <div className="flex items-center gap-2">
                                    <Clock className="w-4 h-4 text-gray-400" />
                                    <input
                                        type="time"
                                        value={formData.start_time}
                                        onChange={e => setFormData({ ...formData, start_time: e.target.value })}
                                        className="flex-1 px-2 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                                   text-white focus:outline-none"
                                    />
                                </div>
                                <input
                                    type="time"
                                    value={formData.end_time}
                                    onChange={e => setFormData({ ...formData, end_time: e.target.value })}
                                    className="px-3 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white focus:outline-none"
                                />
                            </div>

                            {/* Location */}
                            <div className="flex items-center gap-3">
                                <MapPin className="w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    value={formData.location}
                                    onChange={e => setFormData({ ...formData, location: e.target.value })}
                                    placeholder="Место"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            {/* Attendee */}
                            <div className="flex items-center gap-3">
                                <User className="w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    value={formData.attendee_name}
                                    onChange={e => setFormData({ ...formData, attendee_name: e.target.value })}
                                    placeholder="Участник"
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white placeholder-gray-400 focus:outline-none"
                                />
                            </div>

                            {/* Color Picker */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-gray-400">Цвет:</span>
                                <div className="flex gap-2">
                                    {colors.map(color => (
                                        <button
                                            key={color}
                                            onClick={() => setFormData({ ...formData, color })}
                                            style={{ backgroundColor: color }}
                                            className={`w-7 h-7 rounded-full transition ${formData.color === color
                                                ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-800'
                                                : ''
                                                }`}
                                        />
                                    ))}
                                </div>
                            </div>

                            {/* Description */}
                            <textarea
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Описание..."
                                rows={3}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none resize-none"
                            />
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-between mt-6">
                            {selectedEvent ? (
                                <button
                                    onClick={deleteEvent}
                                    className="px-4 py-2 text-red-400 hover:bg-red-500/20 rounded-lg transition"
                                >
                                    Удалить
                                </button>
                            ) : (
                                <div />
                            )}
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowModal(false)}
                                    className="px-4 py-2 text-gray-400 hover:bg-gray-700 rounded-lg transition"
                                >
                                    Отмена
                                </button>
                                <button
                                    onClick={saveEvent}
                                    disabled={!formData.title}
                                    className="px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white
                                               font-medium rounded-xl transition disabled:opacity-50"
                                >
                                    {selectedEvent ? 'Сохранить' : 'Создать'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
