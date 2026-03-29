import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { analysis } from '../api';

export default function AnalysisDetailPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        analysis
            .getById(id)
            .then(setData)
            .catch((err) => setError(err.message || 'Failed to load'))
            .finally(() => setLoading(false));
    }, [id]);

    const riskColor = (level) => `var(--risk-${level})`;

    if (loading) {
        return (
            <div className="loading-overlay">
                <div className="spinner" />
                <p>Loading analysis...</p>
            </div>
        );
    }

    if (error) {
        return (
            <>
                <div className="alert error">⚠️ {error}</div>
                <button className="btn btn-secondary" onClick={() => navigate('/history')}>
                    ← Back to History
                </button>
            </>
        );
    }

    if (!data) return null;
    const r = data.analysis;

    return (
        <>
            <div className="page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
                    <button className="btn btn-secondary" onClick={() => navigate('/history')}>
                        ←
                    </button>
                    <h2 style={{ margin: 0 }}>Analysis #{data.id}</h2>
                </div>
                <p>
                    {data.filename} — {new Date(data.created_at).toLocaleString()}
                </p>
            </div>

            <div className="analysis-result">
                {/* Sidebar */}
                <div className="result-sidebar">
                    <div className="card">
                        <div className="risk-gauge">
                            <div
                                className={`risk-score-circle ${r.overall_risk_level}`}
                                style={{ '--score': r.overall_risk_score }}
                            >
                                <span className="risk-score-value" style={{ color: riskColor(r.overall_risk_level) }}>
                                    {r.overall_risk_score}
                                </span>
                                <span className="risk-score-label">Risk Score</span>
                            </div>
                            <span className={`badge ${r.overall_risk_level}`}>
                                {r.overall_risk_level.toUpperCase()} RISK
                            </span>
                        </div>
                    </div>

                    <div className="card recommendation-card">
                        <div className="recommendation-label">Recommendation</div>
                        <div className="recommendation-value">
                            <span
                                className={`badge ${r.recommendation.toLowerCase().replace('_', '-')}`}
                                style={{ fontSize: '1rem', padding: '6px 16px' }}
                            >
                                {r.recommendation.replace('_', ' ')}
                            </span>
                        </div>
                    </div>

                    <div className="card">
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                            <div style={{ marginBottom: '8px' }}>⏱️ Processing: {r.processing_time_seconds}s</div>
                            <div style={{ marginBottom: '8px' }}>📋 Guidelines: {r.guidelines_checked}</div>
                            <div>🚩 Flags: {r.risk_flags.length}</div>
                        </div>
                    </div>
                </div>

                {/* Main */}
                <div className="result-main">
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Summary</span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                            {r.summary}
                        </p>
                    </div>

                    {r.risk_flags.length > 0 && (
                        <div className="card">
                            <div className="card-header">
                                <span className="card-title">Risk Flags ({r.risk_flags.length})</span>
                            </div>
                            <div className="risk-flags-list">
                                {r.risk_flags.map((flag, i) => (
                                    <div key={i} className={`risk-flag-item ${flag.severity}`}>
                                        <div className="risk-flag-header">
                                            <span className="risk-flag-category">{flag.category}</span>
                                            <span className={`badge ${flag.severity}`}>{flag.severity}</span>
                                        </div>
                                        <div className="risk-flag-description">{flag.description}</div>
                                        <div className="risk-flag-guideline">📌 {flag.guideline_reference}</div>
                                        <div className="confidence-bar">
                                            <div
                                                className="confidence-fill"
                                                style={{ width: `${(flag.confidence * 100).toFixed(0)}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Detailed Analysis</span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                            {r.detailed_analysis}
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
}
