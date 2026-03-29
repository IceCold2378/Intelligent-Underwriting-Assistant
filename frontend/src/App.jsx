import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext.jsx';
import Layout from './components/Layout.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import AnalyzePage from './pages/AnalyzePage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import AnalysisDetailPage from './pages/AnalysisDetailPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import IntegrationsPage from './pages/IntegrationsPage.jsx';

function ProtectedRoute({ children, requireAdmin = false }) {
    const { user, loading } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    if (!user) return <Navigate to="/login" replace />;
    if (requireAdmin && user.role !== 'admin') return <Navigate to="/" replace />;
    return children;
}

export default function App() {
    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
                path="/"
                element={
                    <ProtectedRoute>
                        <Layout />
                    </ProtectedRoute>
                }
            >
                <Route index element={<DashboardPage />} />
                <Route path="analyze" element={<AnalyzePage />} />
                <Route path="history" element={<HistoryPage />} />
                <Route path="analysis/:id" element={<AnalysisDetailPage />} />
                <Route path="integrations" element={<IntegrationsPage />} />
                <Route 
                    path="admin" 
                    element={
                        <ProtectedRoute requireAdmin={true}>
                            <AdminPage />
                        </ProtectedRoute>
                    } 
                />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}
