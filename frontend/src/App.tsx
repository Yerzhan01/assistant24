import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Modules from './pages/Modules'
import Settings from './pages/Settings'
import Calendar from './pages/Calendar'
import Chat from './pages/Chat'
import Finance from './pages/Finance'
import Tasks from './pages/Tasks'
import Contacts from './pages/Contacts'
import Invoices from './pages/Invoices'
import Reports from './pages/Reports'
import Groups from './pages/Groups'
import Landing from './pages/Landing'
import Admin from './pages/Admin'
import Ideas from './pages/Ideas'
import Birthdays from './pages/Birthdays'
import Contracts from './pages/Contracts'

function PrivateRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated } = useAuth()
    return isAuthenticated ? <>{children}</> : <Navigate to="/" />
}

function PublicRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated } = useAuth()
    return !isAuthenticated ? <>{children}</> : <Navigate to="/dashboard" />
}

function AppRoutes() {
    return (
        <Routes>
            {/* Public landing page at root */}
            <Route path="/" element={
                <PublicRoute><Landing /></PublicRoute>
            } />
            <Route path="/login" element={
                <PublicRoute><Login /></PublicRoute>
            } />
            <Route path="/register" element={
                <PublicRoute><Register /></PublicRoute>
            } />
            {/* Private routes under /dashboard layout */}
            <Route path="/dashboard" element={
                <PrivateRoute><Layout /></PrivateRoute>
            }>
                <Route index element={<Dashboard />} />
                <Route path="calendar" element={<Calendar />} />
                <Route path="chat" element={<Chat />} />
                <Route path="finance" element={<Finance />} />
                <Route path="tasks" element={<Tasks />} />
                <Route path="contacts" element={<Contacts />} />
                <Route path="invoices" element={<Invoices />} />
                <Route path="reports" element={<Reports />} />
                <Route path="groups" element={<Groups />} />
                <Route path="modules" element={<Modules />} />
                <Route path="settings" element={<Settings />} />
                <Route path="admin" element={<Admin />} />
                <Route path="ideas" element={<Ideas />} />
                <Route path="birthdays" element={<Birthdays />} />
                <Route path="contracts" element={<Contracts />} />
            </Route>
            <Route path="*" element={<Navigate to="/" />} />
        </Routes>
    )
}

export default function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <AppRoutes />
            </AuthProvider>
        </BrowserRouter>
    )
}

