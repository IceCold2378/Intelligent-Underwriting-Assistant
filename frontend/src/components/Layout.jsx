import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

export default function Layout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const initials = user?.full_name
        ?.split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2) || '??';

    return (
        <div className="app-layout">
            {/* ── Sidebar ── */}
            <aside className="sidebar">
                <div className="sidebar-brand">
                    <div className="sidebar-brand-icon">🛡️</div>
                    <div>
                        <h1>Underwriting<br />Assistant</h1>
                        <span>v2.0 Pro</span>
                    </div>
                </div>

                <nav className="sidebar-nav">
                    <NavLink
                        to="/"
                        end
                        className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                    >
                        📊 Dashboard
                    </NavLink>
                    <NavLink
                        to="/analyze"
                        className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                    >
                        🔍 Analyze
                    </NavLink>
                    <NavLink
                        to="/history"
                        className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                    >
                        📋 History
                    </NavLink>
                    <NavLink
                        to="/integrations"
                        className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                    >
                        🔌 Integrations
                    </NavLink>
                    {user?.role === 'admin' && (
                        <NavLink
                            to="/admin"
                            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                        >
                            ⚙️ Admin Panel
                        </NavLink>
                    )}
                </nav>

                <div className="sidebar-footer">
                    <div className="user-badge">
                        <div className="user-avatar">{initials}</div>
                        <div className="user-info">
                            <div className="user-name">{user?.full_name}</div>
                            <div className="user-role">{user?.role}</div>
                        </div>
                    </div>
                    <button className="nav-item" onClick={handleLogout} style={{ marginTop: '8px' }}>
                        🚪 Sign Out
                    </button>
                </div>
            </aside>

            {/* ── Main Content ── */}
            <main className="main-content">
                <Outlet />
            </main>
        </div>
    );
}
