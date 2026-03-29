import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { analysis } from '../api';

export default function DashboardPage() {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        analysis
            .getDashboard()
            .then(setMetrics)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="loading-overlay">
                <div className="spinner" />
                <p>Loading dashboard...</p>
            </div>
        );
    }

    const m = metrics || {
        total_analyses: 0,
        analyses_today: 0,
        avg_risk_score: 0,
        risk_distribution: { low: 0, moderate: 0, high: 0, critical: 0 },
        recent_analyses: [],
    };

    const riskColor = (score) => {
        if (score <= 25) return 'var(--risk-low)';
        if (score <= 50) return 'var(--risk-moderate)';
        if (score <= 75) return 'var(--risk-high)';
        return 'var(--risk-critical)';
    };

    return (
        <>
            <div className="page-header">
                <h2>Dashboard</h2>
                <p>Overview of your underwriting analysis activity</p>
            </div>

            {/* ── Metrics Grid ── */}
            <div className="metrics-grid">
                <div className="metric-card">
                    <div className="metric-icon blue">📄</div>
                    <div className="metric-value">{m.total_analyses}</div>
                    <div className="metric-label">Total Analyses</div>
                </div>
                <div className="metric-card">
                    <div className="metric-icon green">📅</div>
                    <div className="metric-value">{m.analyses_today}</div>
                    <div className="metric-label">Today</div>
                </div>
                <div className="metric-card">
                    <div className="metric-icon amber">⚡</div>
                    <div className="metric-value" style={{ color: riskColor(m.avg_risk_score) }}>
                        {m.avg_risk_score}
                    </div>
                    <div className="metric-label">Avg Risk Score</div>
                </div>
                <div className="metric-card">
                    <div className="metric-icon purple">🎯</div>
                    <div className="metric-value">
                        {Object.values(m.risk_distribution).reduce((a, b) => a + b, 0) > 0
                            ? Math.round(
                                ((m.risk_distribution.low || 0) /
                                    Object.values(m.risk_distribution).reduce((a, b) => a + b, 1)) *
                                100
                            )
                            : 0}
                        %
                    </div>
                    <div className="metric-label">Approval Rate</div>
                </div>
            </div>

            {/* ── Risk Distribution ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '32px' }}>
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Risk Distribution</span>
                    </div>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        {Object.entries(m.risk_distribution).map(([level, count]) => (
                            <div key={level} style={{ flex: 1, textAlign: 'center' }}>
                                <div
                                    style={{
                                        height: `${Math.max(20, Math.min(120, count * 20))}px`,
                                        background: `var(--risk-${level})`,
                                        borderRadius: '6px 6px 0 0',
                                        marginBottom: '8px',
                                        opacity: 0.7,
                                        transition: 'height 0.5s ease',
                                    }}
                                />
                                <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{count}</div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                                    {level}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Quick Actions</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <button className="btn btn-primary btn-lg" onClick={() => navigate('/analyze')}>
                            🔍 New Analysis
                        </button>
                        <button className="btn btn-secondary btn-lg" onClick={() => navigate('/history')}>
                            📋 View History
                        </button>
                    </div>
                </div>
            </div>

            {/* ── Recent Analyses ── */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Recent Analyses</span>
                    {m.recent_analyses.length > 0 && (
                        <button className="btn btn-secondary" onClick={() => navigate('/history')}>
                            View All
                        </button>
                    )}
                </div>
                {m.recent_analyses.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📄</div>
                        <h3>No analyses yet</h3>
                        <p>Upload your first loan application to get started</p>
                        <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={() => navigate('/analyze')}>
                            Start Analyzing
                        </button>
                    </div>
                ) : (
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>File</th>
                                    <th>Risk Score</th>
                                    <th>Risk Level</th>
                                    <th>Recommendation</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {m.recent_analyses.map((item) => (
                                    <tr
                                        key={item.id}
                                        style={{ cursor: 'pointer' }}
                                        onClick={() => navigate(`/analysis/${item.id}`)}
                                    >
                                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{item.filename}</td>
                                        <td>
                                            <span style={{ fontWeight: 700, color: riskColor(item.overall_risk_score) }}>
                                                {item.overall_risk_score}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${item.overall_risk_level}`}>
                                                {item.overall_risk_level}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${item.recommendation.toLowerCase().replace('_', '-')}`}>
                                                {item.recommendation.replace('_', ' ')}
                                            </span>
                                        </td>
                                        <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                            {new Date(item.created_at).toLocaleDateString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </>
    );
}
