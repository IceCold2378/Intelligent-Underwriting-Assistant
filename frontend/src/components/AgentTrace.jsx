import React from 'react';

export default function AgentTrace({ traceSteps }) {
    if (!traceSteps || traceSteps.length === 0) {
        return null;
    }

    return (
        <div className="agent-trace card">
            <div className="card-header">
                <span className="card-title">🤖 Live Agent Execution Trace</span>
            </div>
            <div className="trace-timeline">
                {traceSteps.map((step, idx) => (
                    <div key={idx} className={`trace-step ${step.status}`}>
                        <div className="trace-icon">
                            {step.status === 'running' && <span className="spinner-small" />}
                            {step.status === 'complete' && '✅'}
                            {step.status === 'error' && '❌'}
                            {step.status === 'pending' && '⏳'}
                        </div>
                        <div className="trace-content">
                            <span className="trace-node-name">{formatNodeName(step.step)}</span>
                            <span className="trace-status-text">{step.status}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function formatNodeName(name) {
    if (!name) return 'Unknown Step';
    return name
        .split('_')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}
