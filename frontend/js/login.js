async function submitLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();
    if (!username || !password) {
        showToast('请输入用户名和密码', 'warning');
        return;
    }
    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '登录失败' }));
            throw new Error(err.detail || '登录失败');
        }
        const data = await resp.json();
        localStorage.setItem('auth_token', data.token);
        window.location.href = '/';
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function showForgotPassword() {
    const username = prompt('请输入账号');
    if (!username) return;
    const idLast6 = prompt('请输入身份证号后6位');
    if (!idLast6) return;
    const newPwd = prompt('请输入新密码');
    if (!newPwd) return;
    const newPwd2 = prompt('请再次输入新密码');
    if (newPwd !== newPwd2) {
        showToast('两次新密码不一致', 'warning');
        return;
    }
    try {
        const resp = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: username.trim(),
                id_card_last6: idLast6.trim(),
                new_password: newPwd
            })
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '重置失败' }));
            throw new Error(err.detail || '重置失败');
        }
        showToast('密码已重置，请登录', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('login-password').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') submitLogin();
    });
});
