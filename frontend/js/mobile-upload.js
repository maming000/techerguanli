async function mobileUpload() {
    await mRequireAuth();
    const fileInput = document.getElementById('m-file');
    const file = fileInput?.files?.[0];
    const result = document.getElementById('m-upload-result');
    if (!file) {
        result.textContent = '请先选择文件';
        return;
    }

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('merge_policy', document.getElementById('m-policy').value);
        const token = localStorage.getItem('auth_token');
        const resp = await fetch('/api/upload/', {
            method: 'POST',
            body: formData,
            headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '上传失败' }));
            throw new Error(err.detail || '上传失败');
        }
        const r = await resp.json();
        result.innerHTML = `导入完成：新增 ${r.new_records}，更新 ${r.updated_records}，跳过 ${r.skipped_records}`;
    } catch (e) {
        result.textContent = e.message || '上传失败';
    }
}

document.addEventListener('DOMContentLoaded', mRequireAuth);
