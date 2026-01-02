import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { TasksApi } from '../api/client'
import {
    CheckCircle,
    Circle,
    Clock,
    Plus,
    X,
    Calendar,
    Flag,
    Loader2,
    Trash2,
    Edit
} from 'lucide-react'

interface Task {
    id: string
    title: string
    description?: string
    status: 'new' | 'todo' | 'in_progress' | 'done'
    priority: 'low' | 'medium' | 'high'
    deadline?: string
    assigned_to?: string
    created_at: string
}

export default function Tasks() {
    const { } = useAuth()
    const [tasks, setTasks] = useState<Task[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [selectedTask, setSelectedTask] = useState<Task | null>(null)
    const [filter, setFilter] = useState<'all' | 'todo' | 'in_progress' | 'done'>('all')

    const [formData, setFormData] = useState({
        title: '',
        description: '',
        status: 'new' as Task['status'],
        priority: 'medium' as Task['priority'],
        deadline: '',
        assigned_to: ''
    })

    const priorityColors = {
        low: 'bg-blue-500',
        medium: 'bg-yellow-500',
        high: 'bg-red-500'
    }

    const statusIcons = {
        new: Circle,
        todo: Circle,
        in_progress: Clock,
        done: CheckCircle
    }

    useEffect(() => {
        fetchTasks()
    }, [])

    const fetchTasks = async () => {
        setLoading(true)
        try {
            const res = await TasksApi.getAll()
            console.log('📦 Tasks API Response:', res.data)

            // Handle both Array or Object wrapper
            const tasksData = Array.isArray(res.data) ? res.data : (res.data.tasks || [])

            // Map due_date to deadline to match component logic
            const mappedTasks = tasksData.map((t: any) => ({
                ...t,
                deadline: t.due_date || t.deadline, // Handle both
                assigned_to: t.assignee_id // Map assignee_id to assigned_to if needed
            }))
            console.log('✅ Mapped Tasks:', mappedTasks)
            setTasks(mappedTasks)
        } catch (err) {
            console.error('Failed to fetch tasks:', err)
        } finally {
            setLoading(false)
        }
    }

    const saveTask = async () => {
        try {
            let res;
            if (selectedTask) {
                res = await TasksApi.update(selectedTask.id, formData)
            } else {
                res = await TasksApi.create(formData)
            }

            if (res.status === 200 || res.status === 201) {
                setShowModal(false)
                resetForm()
                fetchTasks()
            }
        } catch (err) {
            console.error('Failed to save task:', err)
        }
    }

    const deleteTask = async (id: string) => {
        try {
            await TasksApi.delete(id)
            fetchTasks()
        } catch (err) {
            console.error('Failed to delete task:', err)
        }
    }

    const toggleStatus = async (task: Task) => {
        const newStatus = task.status === 'done'
            ? 'in_progress'
            : task.status === 'in_progress'
                ? 'done'
                : 'in_progress' // new/todo -> in_progress

        try {
            await TasksApi.update(task.id, { status: newStatus })
            fetchTasks()
        } catch (err) {
            console.error('Failed to update status:', err)
        }
    }

    const openEditModal = (task: Task) => {
        setSelectedTask(task)
        setFormData({
            title: task.title,
            description: task.description || '',
            status: task.status,
            priority: task.priority,
            deadline: task.deadline || '',
            assigned_to: task.assigned_to || ''
        })
        setShowModal(true)
    }

    const openNewModal = () => {
        setSelectedTask(null)
        resetForm()
        setShowModal(true)
    }

    const resetForm = () => {
        setFormData({
            title: '',
            description: '',
            status: 'new',
            priority: 'medium',
            deadline: '',
            assigned_to: ''
        })
    }

    const filteredTasks = tasks.filter(task => {
        if (filter === 'all') return true
        if (filter === 'todo') return task.status === 'todo' || task.status === 'new'
        return task.status === filter
    })

    const isOverdue = (deadline?: string) => {
        if (!deadline) return false
        return new Date(deadline) < new Date()
    }

    const formatDeadline = (deadline?: string) => {
        if (!deadline) return null
        const date = new Date(deadline)
        const today = new Date()
        const tomorrow = new Date(today)
        tomorrow.setDate(tomorrow.getDate() + 1)

        if (date.toDateString() === today.toDateString()) return 'Сегодня'
        if (date.toDateString() === tomorrow.toDateString()) return 'Завтра'
        return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
    }

    const taskCounts = {
        all: tasks.length,
        todo: tasks.filter(t => t.status === 'todo' || t.status === 'new').length,
        in_progress: tasks.filter(t => t.status === 'in_progress').length,
        done: tasks.filter(t => t.status === 'done').length
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">✅ Задачи</h1>
                    <p className="text-gray-400 mt-1">Управление задачами и дедлайнами</p>
                </div>

                <button
                    onClick={openNewModal}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 
                               text-white font-medium rounded-xl transition"
                >
                    <Plus className="w-5 h-5" />
                    Новая задача
                </button>
            </div>

            {/* Filters */}
            <div className="flex gap-2">
                {(['all', 'todo', 'in_progress', 'done'] as const).map(f => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2 ${filter === f
                            ? 'bg-primary-500 text-white'
                            : 'bg-gray-800 text-gray-400 hover:text-white'
                            }`}
                    >
                        {f === 'all' && 'Все'}
                        {f === 'todo' && '📋 К выполнению'}
                        {f === 'in_progress' && '🔄 В работе'}
                        {f === 'done' && '✅ Выполнено'}
                        <span className="bg-gray-700 px-2 py-0.5 rounded-full text-xs">
                            {taskCounts[f]}
                        </span>
                    </button>
                ))}
            </div>

            {/* Tasks List */}
            <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                    </div>
                ) : filteredTasks.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                        <p className="text-lg">Нет задач</p>
                        <p className="text-sm mt-1">Создайте первую задачу</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-700">
                        {filteredTasks.map(task => {
                            const StatusIcon = statusIcons[task.status] || Circle // Fallback
                            const overdue = task.status !== 'done' && isOverdue(task.deadline)

                            return (
                                <div
                                    key={task.id}
                                    className={`flex items-center gap-4 p-4 hover:bg-gray-700/50 transition ${task.status === 'done' ? 'opacity-60' : ''
                                        }`}
                                >
                                    {/* Status Toggle */}
                                    <button
                                        onClick={() => toggleStatus(task)}
                                        className={`w-6 h-6 rounded-full flex items-center justify-center transition ${task.status === 'done'
                                            ? 'bg-green-500 text-white'
                                            : task.status === 'in_progress'
                                                ? 'bg-yellow-500/20 text-yellow-400 border-2 border-yellow-500'
                                                : 'border-2 border-gray-500 text-gray-500'
                                            }`}
                                    >
                                        <StatusIcon className="w-4 h-4" />
                                    </button>

                                    {/* Priority */}
                                    <div className={`w-1.5 h-8 rounded-full ${priorityColors[task.priority]}`} />

                                    {/* Content */}
                                    <div className="flex-1">
                                        <p className={`font-medium ${task.status === 'done' ? 'text-gray-400 line-through' : 'text-white'
                                            }`}>
                                            {task.title}
                                        </p>
                                        {task.description && (
                                            <p className="text-sm text-gray-500 truncate">{task.description}</p>
                                        )}
                                    </div>

                                    {/* Deadline */}
                                    {task.deadline && (
                                        <div className={`flex items-center gap-1 text-sm ${overdue ? 'text-red-400' : 'text-gray-400'
                                            }`}>
                                            <Calendar className="w-4 h-4" />
                                            {formatDeadline(task.deadline)}
                                        </div>
                                    )}

                                    {/* Actions */}
                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={() => openEditModal(task)}
                                            className="p-2 hover:bg-gray-600 rounded-lg transition"
                                        >
                                            <Edit className="w-4 h-4 text-gray-400" />
                                        </button>
                                        <button
                                            onClick={() => deleteTask(task.id)}
                                            className="p-2 hover:bg-red-500/20 rounded-lg transition"
                                        >
                                            <Trash2 className="w-4 h-4 text-red-400" />
                                        </button>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-md border border-gray-700">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-white">
                                {selectedTask ? 'Редактировать' : 'Новая задача'}
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
                                placeholder="Название задачи"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none focus:ring-2
                                           focus:ring-primary-500"
                            />

                            <textarea
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Описание..."
                                rows={3}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                           text-white placeholder-gray-400 focus:outline-none resize-none"
                            />

                            {/* Priority */}
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Приоритет</label>
                                <div className="flex gap-2">
                                    {(['low', 'medium', 'high'] as const).map(p => (
                                        <button
                                            key={p}
                                            onClick={() => setFormData({ ...formData, priority: p })}
                                            className={`flex-1 py-2 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2 ${formData.priority === p
                                                ? `${priorityColors[p]} text-white`
                                                : 'bg-gray-700 text-gray-400'
                                                }`}
                                        >
                                            <Flag className="w-4 h-4" />
                                            {p === 'low' ? 'Низкий' : p === 'medium' ? 'Средний' : 'Высокий'}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Deadline */}
                            <div className="flex items-center gap-3">
                                <Calendar className="w-5 h-5 text-gray-400" />
                                <input
                                    type="date"
                                    value={formData.deadline}
                                    onChange={e => setFormData({ ...formData, deadline: e.target.value })}
                                    className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl
                                               text-white focus:outline-none"
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
                                onClick={saveTask}
                                disabled={!formData.title}
                                className="flex-1 py-2 bg-primary-500 hover:bg-primary-600 text-white
                                           font-medium rounded-xl transition disabled:opacity-50"
                            >
                                {selectedTask ? 'Сохранить' : 'Создать'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
