const M_API_BASE = '';
let mCachedUser = null;

function mShowToast(message, type = 'success') {
    let container = document.getElementById('m-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'm-toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 2200);
}

function mToken() {
    return localStorage.getItem('auth_token');
}

async function mApi(url, options = {}) {
    const token = mToken();
    const resp = await fetch(M_API_BASE + url, {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers || {})
        },
        ...options
    });
    if (resp.status === 401) {
        localStorage.removeItem('auth_token');
        window.location.href = '/m/login';
        throw new Error('未登录');
    }
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    if (options.raw) return resp;
    return await resp.json();
}

async function mRequireAuth() {
    try {
        mCachedUser = await mApi('/api/auth/me');
        mApplyRoleUI();
        return mCachedUser;
    } catch (e) {
        window.location.href = '/m/login';
        throw e;
    }
}

function mApplyRoleUI() {
    if (!mCachedUser) return;
    const hideUploadForViewer = mCachedUser.role === 'viewer';
    const hideUploadStatsForTeacher = mCachedUser.role === 'teacher';

    if (hideUploadForViewer || hideUploadStatsForTeacher) {
        document.querySelectorAll('.m-tabbar a[href="/m/upload"]').forEach((el) => { el.style.display = 'none'; });
    }
    if (hideUploadStatsForTeacher) {
        document.querySelectorAll('.m-tabbar a[href="/m/stats"]').forEach((el) => { el.style.display = 'none'; });
    }
}

async function mobileLogout() {
    try {
        await mApi('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    localStorage.removeItem('auth_token');
    window.location.href = '/m/login';
}
