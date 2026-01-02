import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { ChatApi } from '../api/client'
import {
    Send,
    Bot,
    User,
    Loader2,
    Sparkles,
    Calendar,
    DollarSign,
    CheckSquare,
    Mic,
    MicOff
} from 'lucide-react'

interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    intent?: string
}

const quickActions = [
    { icon: Calendar, label: 'Встреча завтра в 10:00', color: 'bg-blue-500' },
    { icon: DollarSign, label: 'Записать доход 50000', color: 'bg-green-500' },
    { icon: CheckSquare, label: 'Что у меня сегодня?', color: 'bg-purple-500' },
]

export default function Chat() {
    const { token } = useAuth()
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [isRecording, setIsRecording] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Focus input on mount
    useEffect(() => {
        inputRef.current?.focus()
    }, [])

    // Load history
    useEffect(() => {
        loadHistory()
    }, [])

    const loadHistory = async () => {
        try {
            setLoading(true)
            const res = await ChatApi.getHistory()
            const historyMessages = res.data.map((msg: any) => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: new Date(msg.timestamp),
                intent: msg.intent
            }))

            if (historyMessages.length > 0) {
                setMessages(historyMessages)
            } else {
                // Initial greeting if no history
                setMessages([{
                    id: '0',
                    role: 'assistant',
                    content: `👋 Привет! Я ваш Цифровой Секретарь.

Я могу помочь с:
• 📅 Планированием встреч
• 💰 Записью финансов
• ✅ Управлением задачами
• 📒 Работой с контактами

Просто напишите, что нужно сделать!`,
                    timestamp: new Date()
                }])
            }
        } catch (err) {
            console.error('Failed to load history:', err)
        } finally {
            setLoading(false)
        }
    }

    const sendMessage = async (text?: string) => {
        const messageText = text || input.trim()
        if (!messageText || loading) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: messageText,
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setLoading(true)

        // Temporary ID for assistant message being streamed
        const assistantId = (Date.now() + 1).toString()
        // Placeholder message
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '...',
            timestamp: new Date(),
            intent: 'thinking'
        }])

        try {
            const response = await fetch(`${(import.meta as any).env.VITE_API_URL || '/api/v1'}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ message: messageText })
            })

            const reader = response.body?.getReader()
            const decoder = new TextDecoder()

            if (!reader) throw new Error('No reader')

            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n\n')
                buffer = lines.pop() || ''

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6))

                        if (data.type === 'status') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantId
                                    ? { ...msg, content: `🤖 ${data.content}`, intent: 'thinking' }
                                    : msg
                            ))
                        } else if (data.type === 'result') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantId
                                    ? { ...msg, content: data.content, intent: data.intent }
                                    : msg
                            ))
                        } else if (data.type === 'error') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantId
                                    ? { ...msg, content: `❌ Ошибка: ${data.content}` }
                                    : msg
                            ))
                        }
                    }
                }
            }

        } catch (err) {
            console.error('Stream error:', err)
            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? { ...msg, content: '❌ Произошла ошибка связи.' }
                    : msg
            ))
        } finally {
            setLoading(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    const toggleRecording = () => {
        // TODO: Implement voice recording
        setIsRecording(!isRecording)
    }

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    }

    const getIntentBadge = (intent?: string) => {
        if (!intent) return null
        const badges: Record<string, { icon: typeof Calendar, color: string, label: string }> = {
            'create_meeting': { icon: Calendar, color: 'bg-blue-500', label: 'Встреча' },
            'schedule_meeting': { icon: Calendar, color: 'bg-blue-500', label: 'Встреча' },
            'meeting': { icon: Calendar, color: 'bg-blue-500', label: 'Встреча' },
            'add_income': { icon: DollarSign, color: 'bg-green-500', label: 'Доход' },
            'add_expense': { icon: DollarSign, color: 'bg-red-500', label: 'Расход' },
            'finance': { icon: DollarSign, color: 'bg-green-500', label: 'Финансы' },
            'create_task': { icon: CheckSquare, color: 'bg-purple-500', label: 'Задача' },
            'task': { icon: CheckSquare, color: 'bg-purple-500', label: 'Задача' },
        }
        const badge = badges[intent]
        if (!badge) return null
        return (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 ${badge.color} 
                             text-white text-xs rounded-full mt-2`}>
                <badge.icon className="w-3 h-3" />
                {badge.label}
            </span>
        )
    }

    return (
        <div className="flex flex-col h-[calc(100vh-80px)] md:h-[calc(100vh-120px)]">
            {/* Header */}
            <div className="flex items-center gap-3 mb-3 md:mb-6">
                <div className="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-br from-primary-500 to-purple-600 
                                rounded-lg md:rounded-xl flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 md:w-6 md:h-6 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                    <h1 className="text-lg md:text-2xl font-bold text-white">💬 AI Ассистент</h1>
                    <p className="text-gray-400 text-xs md:text-sm truncate">Напишите или продиктуйте задачу</p>
                </div>
                <div className="hidden md:flex items-center gap-2 text-sm">
                    <Sparkles className="w-4 h-4 text-yellow-400" />
                    <span className="text-gray-400">AI-powered</span>
                </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 bg-gray-800 rounded-xl md:rounded-2xl border border-gray-700 overflow-hidden flex flex-col">
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-3 md:p-6 space-y-3 md:space-y-4">
                    {messages.map(message => (
                        <div
                            key={message.id}
                            className={`flex gap-2 md:gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                        >
                            {/* Avatar */}
                            <div className={`w-7 h-7 md:w-8 md:h-8 rounded-full flex items-center justify-center flex-shrink-0 ${message.role === 'user'
                                ? 'bg-primary-500'
                                : 'bg-gradient-to-br from-primary-500 to-purple-600'
                                }`}>
                                {message.role === 'user'
                                    ? <User className="w-3 h-3 md:w-4 md:h-4 text-white" />
                                    : <Bot className="w-3 h-3 md:w-4 md:h-4 text-white" />
                                }
                            </div>

                            {/* Message Bubble */}
                            <div className={`max-w-[80%] md:max-w-[70%] ${message.role === 'user' ? 'text-right' : ''
                                }`}>
                                <div className={`px-3 py-2 md:px-4 md:py-3 rounded-xl md:rounded-2xl text-sm md:text-base ${message.role === 'user'
                                    ? 'bg-primary-500 text-white rounded-tr-sm'
                                    : 'bg-gray-700 text-gray-100 rounded-tl-sm'
                                    }`}>
                                    <div className="whitespace-pre-wrap">{message.content}</div>
                                </div>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs text-gray-500">
                                        {formatTime(message.timestamp)}
                                    </span>
                                    {getIntentBadge(message.intent)}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Typing indicator */}
                    {loading && (
                        <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 
                                           flex items-center justify-center">
                                <Bot className="w-4 h-4 text-white" />
                            </div>
                            <div className="px-4 py-3 bg-gray-700 rounded-2xl rounded-tl-sm">
                                <div className="flex gap-1">
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                        style={{ animationDelay: '0ms' }} />
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                        style={{ animationDelay: '150ms' }} />
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                        style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Quick Actions */}
                {messages.length <= 1 && (
                    <div className="px-3 md:px-6 pb-3 md:pb-4">
                        <p className="text-xs md:text-sm text-gray-500 mb-2">Быстрые действия:</p>
                        <div className="flex flex-wrap gap-1.5 md:gap-2">
                            {quickActions.map((action, i) => (
                                <button
                                    key={i}
                                    onClick={() => sendMessage(action.label)}
                                    className="flex items-center gap-1.5 md:gap-2 px-2.5 md:px-4 py-1.5 md:py-2 bg-gray-700 hover:bg-gray-600 
                                               text-white text-xs md:text-sm rounded-lg md:rounded-xl transition"
                                >
                                    <action.icon className="w-3 h-3 md:w-4 md:h-4" />
                                    <span className="hidden sm:inline">{action.label}</span>
                                    <span className="sm:hidden">{action.label.split(' ')[0]}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Input */}
                <div className="p-2 md:p-4 border-t border-gray-700">
                    <div className="flex items-center gap-2 md:gap-3">
                        <button
                            onClick={toggleRecording}
                            className={`p-2 md:p-3 rounded-lg md:rounded-xl transition flex-shrink-0 ${isRecording
                                ? 'bg-red-500 text-white animate-pulse'
                                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                                }`}
                        >
                            {isRecording ? <MicOff className="w-4 h-4 md:w-5 md:h-5" /> : <Mic className="w-4 h-4 md:w-5 md:h-5" />}
                        </button>

                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Сообщение..."
                            disabled={loading}
                            className="flex-1 px-3 py-2 md:px-4 md:py-3 bg-gray-700 border border-gray-600 rounded-lg md:rounded-xl
                                       text-white text-sm md:text-base placeholder-gray-400 focus:outline-none focus:ring-2
                                       focus:ring-primary-500 disabled:opacity-50"
                        />

                        <button
                            onClick={() => sendMessage()}
                            disabled={loading || !input.trim()}
                            className="p-2 md:p-3 bg-primary-500 hover:bg-primary-600 text-white rounded-lg md:rounded-xl
                                       transition disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                        >
                            {loading
                                ? <Loader2 className="w-4 h-4 md:w-5 md:h-5 animate-spin" />
                                : <Send className="w-4 h-4 md:w-5 md:h-5" />
                            }
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
