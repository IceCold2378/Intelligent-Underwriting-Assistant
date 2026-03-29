import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

export default function RegisterPage() {
    const { register } = useAuth();
    const navigate = useNavigate();
    const [form, setForm] = useState({
        full_name: '',
        email: '',
        password: '',
        organization: '',
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const update = (field) => (e) =>
        setForm((f) => ({ ...f, [field]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (form.password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        setLoading(true);
        try {
            await register(form.email, form.password, form.full_name, form.organization || null);
            navigate('/');
        } catch (err) {
            setError(err.message || 'Registration failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-logo">🛡️</div>
                <h2>Create Account</h2>
                <p className="subtitle">Start analyzing loan applications with AI</p>

                {error && <div className="alert error">⚠️ {error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-name">Full Name</label>
                        <input
                            id="reg-name"
                            className="form-input"
                            type="text"
                            placeholder="Jane Smith"
                            value={form.full_name}
                            onChange={update('full_name')}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-email">Work Email</label>
                        <input
                            id="reg-email"
                            className="form-input"
                            type="email"
                            placeholder="jane@company.com"
                            value={form.email}
                            onChange={update('email')}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-org">Organization</label>
                        <input
                            id="reg-org"
                            className="form-input"
                            type="text"
                            placeholder="Acme Financial (optional)"
                            value={form.organization}
                            onChange={update('organization')}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-password">Password</label>
                        <input
                            id="reg-password"
                            className="form-input"
                            type="password"
                            placeholder="Min. 8 characters"
                            value={form.password}
                            onChange={update('password')}
                            required
                            minLength={8}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={loading}>
                        {loading ? 'Creating account...' : 'Create Account'}
                    </button>
                </form>

                <div className="auth-footer">
                    Already have an account? <Link to="/login">Sign in</Link>
                </div>
            </div>
        </div>
    );
}
