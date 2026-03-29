import { useState, useEffect } from 'react';
import { admin } from '../api.js';

export default function AdminPage() {
    const [metrics, setMetrics] = useState(null);
    const [users, setUsers] = useState([]);
    const [apiKeys, setApiKeys] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Form states
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    
    // Key Generate States
    const [keyName, setKeyName] = useState('');
    const [generatedKey, setGeneratedKey] = useState(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [mRes, uRes, kRes] = await Promise.all([
                admin.getMetrics(),
                admin.getUsers(),
                admin.getApiKeys()
            ]);
            setMetrics(mRes);
            setUsers(uRes);
            setApiKeys(kRes.keys || []);
            setError(null);
        } catch (err) {
            setError(err.message || 'Failed to load admin data');
        } finally {
            setLoading(false);
        }
    };

    const handleRoleChange = async (userId, newRole) => {
        try {
            await admin.updateUser(userId, { role: newRole });
            fetchData();
        } catch (err) {
            alert(err.message);
        }
    };

    const handleUploadGuidelines = async (e) => {
        e.preventDefault();
        if (!file) return;
        setUploading(true);
        try {
            await admin.uploadGuidelines(file);
            alert("Guidelines updated and Vector DB rebuilt!");
            setFile(null);
        } catch (err) {
            alert(err.message);
        } finally {
            setUploading(false);
        }
    };

    const handleGenerateKey = async (e) => {
        e.preventDefault();
        if (!keyName) return;
        try {
            const res = await admin.createApiKey({ name: keyName, scopes: ["read", "write"] });
            setGeneratedKey(res.api_key); // Only shown once!
            setKeyName('');
            fetchData();
        } catch (err) {
            alert(err.message);
        }
    };

    const handleRevokeKey = async (keyId) => {
        if (!window.confirm("Are you sure you want to revoke this key?")) return;
        try {
            await admin.revokeApiKey(keyId);
            fetchData();
        } catch (err) {
            alert(err.message);
        }
    };

    if (loading) return <div className="loading-screen">Loading Admin Panel...</div>;

    return (
        <div className="admin-page fade-in">
            <header className="page-header">
                <h2>Admin Control Center</h2>
                <p>Manage users, system configurations, and enterprise access keys.</p>
            </header>

            {error && <div className="error-banner">{error}</div>}

            <section className="metrics-grid">
                <div className="metric-card">
                    <div className="metric-icon blue">👥</div>
                    <div className="metric-value">{metrics?.total_users || 0}</div>
                    <div className="metric-label">Total Users</div>
                </div>
                <div className="metric-card">
                    <div className="metric-icon green">🔌</div>
                    <div className="metric-value">{metrics?.active_integrations || 0}</div>
                    <div className="metric-label">Active Integrations</div>
                </div>
                <div className="metric-card">
                    <div className="metric-icon purple">💾</div>
                    <div className="metric-value">{metrics?.vector_db_size_mb || 0} MB</div>
                    <div className="metric-label">Vector DB Size</div>
                </div>
            </section>

            <div className="grid-2col">
                {/* Guidelines Upload */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Update Underwriting Guidelines</h3>
                    </div>
                    <form onSubmit={handleUploadGuidelines}>
                        <div className="form-group">
                            <label className="form-label">Upload New Ruleset (.txt or .md)</label>
                            <input 
                                type="file" 
                                accept=".txt,.md"
                                className="form-input"
                                onChange={(e) => setFile(e.target.files[0])}
                            />
                        </div>
                        <button type="submit" className="btn btn-primary" disabled={!file || uploading}>
                            {uploading ? 'Rebuilding DB...' : 'Upload & Rebuild Vector DB'}
                        </button>
                    </form>
                </div>

                {/* API Key Generation */}
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Service API Keys</h3>
                    </div>
                    {generatedKey ? (
                        <div className="success-banner" style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                            <h4 style={{ color: '#10b981', marginBottom: '8px' }}>Key Created Successfully!</h4>
                            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '8px' }}>Please copy this key now. You will not be able to see it again.</p>
                            <code style={{ background: '#0a0e1a', padding: '8px', display: 'block', borderRadius: '4px', color: '#6366f1', wordBreak: 'break-all' }}>
                                {generatedKey}
                            </code>
                            <button className="btn btn-secondary" style={{ marginTop: '12px' }} onClick={() => setGeneratedKey(null)}>Close</button>
                        </div>
                    ) : (
                        <form onSubmit={handleGenerateKey}>
                            <div className="form-group">
                                <label className="form-label">Key Name (e.g., Salesforce Integration)</label>
                                <input 
                                    type="text" 
                                    className="form-input"
                                    value={keyName}
                                    placeholder="Enter identifier..."
                                    onChange={(e) => setKeyName(e.target.value)}
                                />
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={!keyName}>
                                Generate New Key
                            </button>
                        </form>
                    )}
                </div>
            </div>

            {/* API Keys Table */}
            <div className="card" style={{ marginTop: '24px' }}>
                <div className="card-header"><h3 className="card-title">Active API Keys</h3></div>
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Scopes</th>
                                <th>Created</th>
                                <th>Expires</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {apiKeys.map(k => (
                                <tr key={k.id}>
                                    <td><strong>{k.name}</strong></td>
                                    <td>
                                        {k.scopes.map(s => <span key={s} className="badge low" style={{ marginRight: '4px' }}>{s}</span>)}
                                    </td>
                                    <td>{new Date(k.created_at).toLocaleDateString()}</td>
                                    <td>{k.expires_at ? new Date(k.expires_at).toLocaleDateString() : 'Never'}</td>
                                    <td>
                                        <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleRevokeKey(k.id)}>
                                            Revoke
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {apiKeys.length === 0 && (
                                <tr><td colSpan="5" style={{ textAlign: 'center', opacity: 0.5 }}>No active API keys found.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Users Table */}
            <div className="card" style={{ marginTop: '24px' }}>
                <div className="card-header"><h3 className="card-title">User Role Management</h3></div>
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>User ID</th>
                                <th>Email</th>
                                <th>Name</th>
                                <th>Role</th>
                                <th>Joined</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map(u => (
                                <tr key={u.id}>
                                    <td>#{u.id}</td>
                                    <td>{u.email}</td>
                                    <td>{u.full_name}</td>
                                    <td>
                                        <select 
                                            value={u.role} 
                                            onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                            style={{ padding: '4px', background: 'var(--bg-elevated)', color: 'white', border: '1px solid var(--border-default)', borderRadius: '4px' }}
                                        >
                                            <option value="analyst">Analyst</option>
                                            <option value="reviewer">Reviewer</option>
                                            <option value="compliance_officer">Compliance Officer</option>
                                            <option value="admin">Admin</option>
                                        </select>
                                    </td>
                                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            
        </div>
    );
}
