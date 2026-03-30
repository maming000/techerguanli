/**
 * 教师信息管理系统 - 通用 JS 工具
 */

const API_BASE = '';
let cachedUser = null;

/**
 * 字符转义，防止 XSS
 */
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * 封装 fetch 请求
 */
async function api(url, options = {}) {
    try {
        const token = localStorage.getItem('auth_token');
        const resp = await fetch(API_BASE + url, {
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                ...options.headers
            },
            ...options
        });
        if (resp.status === 401) {
            localStorage.removeItem('auth_token');
            cachedUser = null;
            if (!window.location.pathname.startsWith('/login')) {
                window.location.href = '/login';
            }
            throw new Error('未登录');
        }
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '请求失败' }));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        // 如文件下载则直接返回 response
        if (options.raw) return resp;
        return await resp.json();
    } catch (e) {
        showToast(e.message, 'error');
        throw e;
    }
}

/**
 * Toast 通知
 */
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * 格式化日期
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const d = new Date(dateStr);
        return d.toLocaleString('zh-CN', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit'
        });
    } catch {
        return dateStr;
    }
}

/**
 * 生成分页 HTML
 */
function renderPagination(page, totalPages, total, onPageChange) {
    if (totalPages <= 1) return '';

    let html = `<div class="pagination">
        <div class="pagination-info">共 ${total} 条记录，第 ${page}/${totalPages} 页</div>
        <div class="pagination-buttons">`;

    html += `<button class="page-btn" onclick="${onPageChange}(1)" ${page === 1 ? 'disabled' : ''}>«</button>`;
    html += `<button class="page-btn" onclick="${onPageChange}(${page - 1})" ${page === 1 ? 'disabled' : ''}>‹</button>`;

    // 显示页码按钮
    let start = Math.max(1, page - 2);
    let end = Math.min(totalPages, page + 2);
    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="${onPageChange}(${i})">${i}</button>`;
    }

    html += `<button class="page-btn" onclick="${onPageChange}(${page + 1})" ${page === totalPages ? 'disabled' : ''}>›</button>`;
    html += `<button class="page-btn" onclick="${onPageChange}(${totalPages})" ${page === totalPages ? 'disabled' : ''}>»</button>`;

    html += '</div></div>';
    return html;
}

/**
 * 渲染标签
 */
function renderTags(tags) {
    if (!tags || tags.length === 0) return '-';
    const colors = ['primary', 'success', 'warning', 'danger'];
    return tags.map((tag, i) =>
        `<span class="tag tag-${colors[i % colors.length]}">${tag}</span>`
    ).join(' ');
}

/**
 * 侧边栏高亮
 */
function initNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href === path || (path === '/' && href === '/')) {
            item.classList.add('active');
        }
    });
}

// 页面加载完成后初始化导航
document.addEventListener('DOMContentLoaded', () => {
    if (redirectToStandaloneMobile()) return;
    initNav();
    initMobileShell();
    initAuthUI();
});

function redirectToStandaloneMobile() {
    if (!shouldUseStandaloneMobile()) return false;
    const path = window.location.pathname;
    // 仅做精确路由兜底：防止手机打开桌面详情页
    if (path === '/detail') {
        window.location.replace(`/m/detail${window.location.search || ''}${window.location.hash || ''}`);
        return true;
    }
    return false;
}

function isMobileViewport() {
    return window.matchMedia('(max-width: 768px)').matches;
}

function isMobileUserAgent() {
    const ua = (navigator.userAgent || '').toLowerCase();
    return /android|iphone|ipad|ipod|mobile|windows phone|harmonyos/.test(ua);
}

function shouldUseStandaloneMobile() {
    return isMobileViewport() && isMobileUserAgent();
}

function getMobileNavItems() {
    return [
        { href: '/', icon: '📋', label: '列表' },
        { href: '/upload', icon: '📤', label: '导入' },
        { href: '/stats', icon: '📊', label: '统计' },
    ];
}

function initMobileShell() {
    if (window.location.pathname.startsWith('/login')) return;

    const oldNav = document.getElementById('mobile-bottom-nav');
    if (oldNav) oldNav.remove();

    if (!shouldUseStandaloneMobile()) {
        document.body.classList.remove('mobile-shell-enabled');
        return;
    }

    document.body.classList.add('mobile-shell-enabled');
    const nav = document.createElement('nav');
    nav.id = 'mobile-bottom-nav';
    nav.className = 'mobile-bottom-nav';

    const path = window.location.pathname;
    const links = getMobileNavItems().map((item) => {
        const active = item.href === path ? 'active' : '';
        return `<a href="${item.href}" class="mobile-nav-link ${active}" data-mobile-route="${item.href}">
            <span class="mobile-nav-icon">${item.icon}</span>
            <span>${item.label}</span>
        </a>`;
    }).join('');

    nav.innerHTML = links;
    document.body.appendChild(nav);
}

window.addEventListener('resize', () => {
    initMobileShell();
});

async function getCurrentUser() {
    if (cachedUser) return cachedUser;
    try {
        cachedUser = await api('/api/auth/me');
        return cachedUser;
    } catch (e) {
        return null;
    }
}

async function initAuthUI() {
    if (window.location.pathname.startsWith('/login')) return;
    const user = await getCurrentUser();
    if (!user) return;

    // 隐藏教师无权限入口
    if (user.role === 'teacher') {
        document.querySelectorAll('.nav-item[href="/upload"], .nav-item[href="/stats"]').forEach(el => {
            el.style.display = 'none';
        });
        document.querySelectorAll('.mobile-nav-link[data-mobile-route="/upload"], .mobile-nav-link[data-mobile-route="/stats"]').forEach(el => {
            el.style.display = 'none';
        });
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) exportBtn.style.display = 'none';
        const importBtn = document.getElementById('import-btn');
        if (importBtn) importBtn.style.display = 'none';
        const bulkBtn = document.getElementById('bulk-account-btn');
        if (bulkBtn) bulkBtn.style.display = 'none';
        const batchBar = document.getElementById('batch-bar');
        if (batchBar) batchBar.style.display = 'none';

        // 教师账号不展示管理员首页，直接进入个人详情
        if (window.location.pathname === '/' && user.teacher_id) {
            const target = shouldUseStandaloneMobile()
                ? `/m/detail?id=${user.teacher_id}`
                : `/detail?id=${user.teacher_id}`;
            window.location.replace(target);
        }
    }

    if (user.role === 'viewer') {
        const importBtn = document.getElementById('import-btn');
        if (importBtn) importBtn.style.display = 'none';
        const bulkBtn = document.getElementById('bulk-account-btn');
        if (bulkBtn) bulkBtn.style.display = 'none';
        const batchBar = document.getElementById('batch-bar');
        if (batchBar) batchBar.style.display = 'none';
        document.querySelectorAll('.nav-item[href="/assessment/start"], .mobile-nav-link[data-mobile-route="/assessment/start"]').forEach((el) => {
            el.style.display = 'none';
        });
    }

    // 追加退出按钮
    const nav = document.querySelector('.sidebar-nav');
    if (nav && !document.getElementById('logout-link')) {
        const a = document.createElement('a');
        a.href = 'javascript:void(0)';
        a.id = 'logout-link';
        a.className = 'nav-item';
        a.innerHTML = `<span class="nav-icon">🚪</span> 退出登录`;
        a.onclick = async () => {
            try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
            localStorage.removeItem('auth_token');
            cachedUser = null;
            window.location.href = '/login';
        };
        nav.appendChild(a);
    }

    if (isMobileViewport()) {
        if (!document.getElementById('mobile-logout-link')) {
            const mobileNav = document.getElementById('mobile-bottom-nav');
            if (mobileNav) {
                const logout = document.createElement('a');
                logout.href = 'javascript:void(0)';
                logout.id = 'mobile-logout-link';
                logout.className = 'mobile-nav-link';
                logout.innerHTML = `<span class="mobile-nav-icon">🚪</span><span>退出</span>`;
                logout.onclick = async () => {
                    try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
                    localStorage.removeItem('auth_token');
                    cachedUser = null;
                    window.location.href = '/login';
                };
                mobileNav.appendChild(logout);
            }
        }
    }

    // 修改密码入口
    if (nav && !document.getElementById('change-password-link')) {
        const a = document.createElement('a');
        a.href = 'javascript:void(0)';
        a.id = 'change-password-link';
        a.className = 'nav-item';
        a.innerHTML = `<span class="nav-icon">🔑</span> 修改密码`;
        a.onclick = () => showChangePasswordModal();
        nav.appendChild(a);
    }
}

async function showChangePasswordModal() {
    const oldPwd = prompt('请输入旧密码');
    if (!oldPwd) return;
    const newPwd = prompt('请输入新密码');
    if (!newPwd) return;
    const newPwd2 = prompt('请再次输入新密码');
    if (newPwd !== newPwd2) {
        showToast('两次新密码不一致', 'warning');
        return;
    }
    try {
        await api('/api/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
        });
        showToast('密码已修改', 'success');
    } catch (e) {}
}
