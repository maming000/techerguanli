async function mobileLogin() {
    const username = document.getElementById('m-username').value.trim();
    const password = document.getElementById('m-password').value.trim();
    if (!username || !password) return alert('请输入用户名和密码');

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
        window.location.href = '/m';
    } catch (e) {
        alert(e.message || '登录失败');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('auth_token')) {
        window.location.href = '/m';
        return;
    }
    const p = document.getElementById('m-password');
    if (p) p.addEventListener('keyup', (e) => { if (e.key === 'Enter') mobileLogin(); });
});
