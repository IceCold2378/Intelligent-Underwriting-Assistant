/**
 * API client — centralized HTTP communication with the backend.
 */

const API_BASE = '/api/v1';

class ApiError extends Error {
    constructor(message, status, detail) {
        super(message);
        this.status = status;
        this.detail = detail;
    }
}

function getToken() {
    return localStorage.getItem('token');
}

async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const token = getToken();

    const headers = { ...options.headers };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(url, { ...options, headers });

    if (!res.ok) {
        let errorData;
        try {
            errorData = await res.json();
        } catch {
            errorData = { message: res.statusText };
        }
        throw new ApiError(
            errorData.message || 'Request failed',
            res.status,
            errorData.detail
        );
    }

    return res.json();
}

// ── Auth ──
export const auth = {
    register: (data) =>
        request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
    login: (data) =>
        request('/auth/login', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
    getProfile: () => request('/auth/me'),
};

// ── Analysis ──
export const analysis = {
    create: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return request('/analysis', {
            method: 'POST',
            body: formData,
        });
    },
    createTask: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return request('/analysis/task', {
            method: 'POST',
            body: formData,
        });
    },
    getHistory: (page = 1, pageSize = 20) =>
        request(`/analysis/history?page=${page}&page_size=${pageSize}`),
    getById: (id) => request(`/analysis/${id}`),
    getDashboard: () => request('/analysis/dashboard/metrics'),
};

// ── Admin ──
export const admin = {
    getMetrics: () => request('/admin/system/metrics'),
    getUsers: () => request('/admin/users'),
    updateUser: (id, data) => request(`/admin/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    uploadGuidelines: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return request('/admin/guidelines', { method: 'POST', body: formData });
    },
    getApiKeys: () => request('/admin/api-keys'),
    createApiKey: (data) => request('/admin/api-keys', { method: 'POST', body: JSON.stringify(data) }),
    revokeApiKey: (id) => request(`/admin/api-keys/${id}`, { method: 'DELETE' }),
};

// ── Integrations ──
export const integrations = {
    getAll: () => request('/integrations'),
    connect: (name, config) => request(`/integrations/${name}/connect`, { method: 'POST', body: JSON.stringify(config) }),
    disconnect: (name) => request(`/integrations/${name}/disconnect`, { method: 'POST' }),
    sync: (name) => request(`/integrations/${name}/sync`, { method: 'POST' }),
};

// ── Health ──
export const health = {
    check: () => request('/health'),
};
