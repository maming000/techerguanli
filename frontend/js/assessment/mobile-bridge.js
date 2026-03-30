async function api(url, options = {}) {
    return await mApi(url, options);
}

async function getCurrentUser() {
    return await mRequireAuth();
}

function showToast(message, type = 'success') {
    mShowToast(message, type);
}

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

