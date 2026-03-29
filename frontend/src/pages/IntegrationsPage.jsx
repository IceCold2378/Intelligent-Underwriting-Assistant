import { useState, useEffect } from 'react';
import { integrations } from '../api.js';

export default function IntegrationsPage() {
    const [integrationList, setIntegrationList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState({});

    useEffect(() => {
        fetchIntegrations();
    }, []);

    const fetchIntegrations = async () => {
        try {
            const res = await integrations.getAll();
            setIntegrationList(res.integrations || []);
        } catch (err) {
            console.error("Failed to fetch integrations", err);
        } finally {
            setLoading(false);
        }
    };

    const handleConnect = async (name) => {
        // In a real app we'd prompt for configuration secrets here or use OAuth
        try {
            // Passing empty config just to toggle the connected status for demo purposes
            await integrations.connect(name, {});
            fetchIntegrations();
        } catch (err) {
            alert(err.message);
        }
    };

    const handleDisconnect = async (name) => {
        try {
            await integrations.disconnect(name);
            fetchIntegrations();
        } catch (err) {
            alert(err.message);
        }
    };

    const handleSync = async (name) => {
        setSyncing(prev => ({ ...prev, [name]: true }));
        try {
            await integrations.sync(name);
            alert(`Sync triggered for ${name}`);
        } catch (err) {
            alert(err.message);
        } finally {
            setSyncing(prev => ({ ...prev, [name]: false }));
            fetchIntegrations();
        }
    };

    if (loading) return <div className="loading-screen">Loading Integrations...</div>;

    return (
        <div className="integrations-page fade-in">
            <header className="page-header">
                <h2>Enterprise Integrations</h2>
                <p>Manage connections to external CRMs, data warehouses, and cloud services.</p>
            </header>

            <div className="grid-2col" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '24px' }}>
                {integrationList.map(int => (
                    <div key={int.name} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
                        <div className="card-header" style={{ marginBottom: '12px' }}>
                            <h3 className="card-title" style={{ fontSize: '1.2rem' }}>
                                {int.name.charAt(0).toUpperCase() + int.name.slice(1)} Connector
                            </h3>
                            <span className={`badge ${int.status === 'connected' ? 'approve' : 'deny'}`}>
                                {int.status.toUpperCase()}
                            </span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px', flex: 1 }}>
                            Status check: {int.health} <br/>
                            Configured: {int.is_configured ? 'Yes' : 'No'}
                        </p>
                        
                        <div style={{ display: 'flex', gap: '12px', marginTop: 'auto' }}>
                            {int.status === 'connected' ? (
                                <>
                                    <button 
                                        className="btn btn-secondary" 
                                        onClick={() => handleDisconnect(int.name)}
                                        style={{ flex: 1 }}
                                    >
                                        Disconnect
                                    </button>
                                    <button 
                                        className="btn btn-primary" 
                                        onClick={() => handleSync(int.name)}
                                        style={{ flex: 1 }}
                                        disabled={syncing[int.name]}
                                    >
                                        {syncing[int.name] ? 'Syncing...' : 'Sync Data'}
                                    </button>
                                </>
                            ) : (
                                <button 
                                    className="btn btn-primary btn-block" 
                                    onClick={() => handleConnect(int.name)}
                                >
                                    Connect Integration
                                </button>
                            )}
                        </div>
                    </div>
                ))}
            </div>
            
            {/* Future Webhook Manager UI would go here */}
            <div className="card" style={{ marginTop: '32px' }}>
                <div className="card-header">
                    <h3 className="card-title">Event Webhooks</h3>
                </div>
                <p style={{ color: 'var(--text-secondary)' }}>
                    Webhook endpoints can be configured via API using the <code>/api/v1/integrations/webhooks</code> endpoint. <br/>
                    These webhooks will trigger automatically upon completion of async analysis tasks with a signed <code>X-Hub-Signature-256</code> header.
                </p>
            </div>
        </div>
    );
}
