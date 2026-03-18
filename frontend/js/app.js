/**
 * 教师信息管理系统 - 通用 JS 工具
 */

const API_BASE = '';

/**
 * 封装 fetch 请求
 */
async function api(url, options = {}) {
    try {
        const resp = await fetch(API_BASE + url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
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
document.addEventListener('DOMContentLoaded', initNav);
