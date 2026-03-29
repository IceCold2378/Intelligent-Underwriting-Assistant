import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { analysis } from '../api';

export default function HistoryPage() {
    const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 });
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const loadPage = (page) => {
        setLoading(true);
        analysis
            .getHistory(page)
            .then(setData)
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => { loadPage(1); }, []);

    const riskColor = (score) => {
        if (score <= 25) return 'var(--risk-low)';
        if (score <= 50) return 'var(--risk-moderate)';
        if (score <= 75) return 'var(--risk-high)';
        return 'var(--risk-critical)';
    };

    const totalPages = Math.ceil(data.total / data.page_size);

    return (
        <>
            <div className="page-header">
                <h2>Analysis History</h2>
                <p>{data.total} total analyses</p>
            </div>

            {loading ? (
                <div className="loading-overlay">
                    <div className="spinner" />
                    <p>Loading history...</p>
                </div>
            ) : data.items.length === 0 ? (
                <div className="card">
                    <div className="empty-state">
                        <div className="empty-state-icon">📋</div>
                        <h3>No analyses found</h3>
                        <p>Your analysis history will appear here</p>
                        <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={() => navigate('/analyze')}>
                            Start Analyzing
                        </button>
                    </div>
                </div>
            ) : (
                <div className="card" style={{ padding: 0 }}>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>File</th>
                                    <th>Risk Score</th>
                                    <th>Risk Level</th>
                                    <th>Recommendation</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.items.map((item) => (
                                    <tr
                                        key={item.id}
                                        style={{ cursor: 'pointer' }}
                                        onClick={() => navigate(`/analysis/${item.id}`)}
                                    >
                                        <td style={{ color: 'var(--text-muted)' }}>#{item.id}</td>
                                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                            {item.filename}
                                        </td>
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
                                            {new Date(item.created_at).toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', padding: '16px' }}>
                            <button
                                className="btn btn-secondary"
                                disabled={data.page <= 1}
                                onClick={() => loadPage(data.page - 1)}
                            >
                                ← Previous
                            </button>
                            <span style={{ display: 'flex', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                Page {data.page} of {totalPages}
                            </span>
                            <button
                                className="btn btn-secondary"
                                disabled={data.page >= totalPages}
                                onClick={() => loadPage(data.page + 1)}
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </div>
            )}
        </>
    );
}
