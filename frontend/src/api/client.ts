import axios from 'axios';

// Create axios instance with default config
export const api = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add interceptor to inject token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Add interceptor to handle 401s (logout)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Optional: trigger global logout or redirect
            // window.location.href = '/login'; 
        }
        return Promise.reject(error);
    }
);

// Define API modules
export const FinanceApi = {
    getTransactions: (params?: any) => api.get('/finance/transactions', { params }),
    getSummary: () => api.get('/finance/summary'),
    getReports: (period: string = 'month') => api.get(`/finance/reports?period=${period}`),
};

export const CalendarApi = {
    getEvents: (start: string, end: string) => api.get('/calendar/events', { params: { start, end } }),
    createEvent: (data: any) => api.post('/calendar/events', data),
    updateEvent: (id: string, data: any) => api.patch(`/calendar/events/${id}`, data),
    deleteEvent: (id: string) => api.delete(`/calendar/events/${id}`),
};

export const ChatApi = {
    sendMessage: (message: string) => api.post('/chat', { message }),
    getHistory: () => api.get('/chat/history'),
};

export const TasksApi = {
    getAll: (status?: string) => api.get('/tasks', { params: { status } }),
    create: (data: any) => api.post('/tasks', data),
    update: (id: string, data: any) => api.patch(`/tasks/${id}`, data),
    delete: (id: string) => api.delete(`/tasks/${id}`),
};

export const ContactsApi = {
    getAll: (search?: string) => api.get('/contacts', { params: { search } }),
    create: (data: any) => api.post('/contacts', data),
    update: (id: string, data: any) => api.patch(`/contacts/${id}`, data),
    delete: (id: string) => api.delete(`/contacts/${id}`),
};

export const IdeasApi = {
    getAll: () => api.get('/ideas'),
    create: (data: any) => api.post('/ideas', data),
    update: (id: string, data: any) => api.patch(`/ideas/${id}`, data),
    delete: (id: string) => api.delete(`/ideas/${id}`),
};

export const BirthdaysApi = {
    getAll: () => api.get('/birthdays'),
    create: (data: any) => api.post('/birthdays', data),
    update: (id: string, data: any) => api.patch(`/birthdays/${id}`, data),
    delete: (id: string) => api.delete(`/birthdays/${id}`),
};

export const ContractsApi = {
    getAll: () => api.get('/contracts'),
    create: (data: any) => api.post('/contracts', data),
    update: (id: string, data: any) => api.patch(`/contracts/${id}`, data),
    delete: (id: string) => api.delete(`/contracts/${id}`),
};

export const InvoicesApi = {
    getAll: () => api.get('/invoices'),
    create: (data: any) => api.post('/invoices', data),
    update: (id: string, data: any) => api.patch(`/invoices/${id}`, data),
    delete: (id: string) => api.delete(`/invoices/${id}`),
    recordPayment: (id: string, data: { amount: number; note?: string }) => api.post(`/invoices/${id}/payments`, data),
    getPayments: (id: string) => api.get(`/invoices/${id}/payments`),
};

export const SettingsApi = {
    connectTelegram: (data: { bot_token: string }) => api.post('/settings/telegram', data),
    disconnectTelegram: () => api.delete('/settings/telegram'),
    connectWhatsApp: (data: { instance_id: string, token: string, phone?: string }) => api.post('/settings/whatsapp', data),
    disconnectWhatsApp: () => api.delete('/settings/whatsapp'),
    updateAI: (data: { enabled: boolean, custom_api_key?: string | null }) => api.patch('/settings/ai', data),
    updateLanguage: (data: { language: string }) => api.patch('/settings/language', data),
};

export const GroupsApi = {
    getCandidates: () => api.get('/whatsapp/groups/candidates').then(res => res.data),
    batchImport: (groups: { whatsapp_chat_id: string; name: string }[]) => api.post('/whatsapp/groups/batch-import', { groups }).then(res => res.data),
};
