/**
 * 上传页面逻辑
 */

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const resultArea = document.getElementById('result-area');

    // 点击上传
    dropZone.addEventListener('click', () => fileInput.click());

    // 拖拽上传
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFiles(files);
        }
    });

    // 文件选择
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });
});

async function handleFiles(files) {
    const resultArea = document.getElementById('result-area');
    const progressArea = document.getElementById('progress-area');

    // 显示进度
    progressArea.classList.remove('hidden');
    resultArea.classList.add('hidden');

    let allResults = [];
    let processed = 0;

    for (const file of files) {
        updateProgress(file.name, processed, files.length);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const resp = await fetch('/api/upload/', {
                method: 'POST',
                body: formData
            });

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: '上传失败' }));
                allResults.push({ filename: file.name, error: err.detail });
            } else {
                const result = await resp.json();
                allResults.push(result);
            }
        } catch (e) {
            allResults.push({ filename: file.name, error: e.message });
        }

        processed++;
        updateProgress(file.name, processed, files.length);
    }

    // 显示结果
    progressArea.classList.add('hidden');
    resultArea.classList.remove('hidden');
    renderResults(allResults);
}

function updateProgress(filename, current, total) {
    const progressText = document.getElementById('progress-text');
    const progressFill = document.getElementById('progress-fill');
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    progressText.textContent = `正在处理: ${filename} (${current}/${total})`;
    progressFill.style.width = pct + '%';
}

function renderResults(results) {
    const container = document.getElementById('result-list');
    let html = '';

    for (const r of results) {
        if (r.error) {
            html += `
                <div class="card mb-16">
                    <div class="card-body">
                        <h3 style="color: var(--danger)">❌ ${r.filename}</h3>
                        <p class="text-muted mt-16">${r.error}</p>
                    </div>
                </div>`;
            continue;
        }

        html += `
            <div class="card mb-16">
                <div class="card-header">
                    <h2>📄 ${r.filename}</h2>
                </div>
                <div class="card-body">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-icon blue">📊</div>
                            <div class="stat-info">
                                <h3>${r.total_records}</h3>
                                <p>总记录数</p>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon green">✨</div>
                            <div class="stat-info">
                                <h3>${r.new_records}</h3>
                                <p>新增记录</p>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon orange">🔄</div>
                            <div class="stat-info">
                                <h3>${r.updated_records}</h3>
                                <p>更新记录</p>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon red">⏭️</div>
                            <div class="stat-info">
                                <h3>${r.skipped_records}</h3>
                                <p>跳过记录</p>
                            </div>
                        </div>
                    </div>
                    ${r.new_fields.length > 0 ? `
                        <div class="mt-16">
                            <strong>新发现字段：</strong>
                            ${r.new_fields.map(f => `<span class="tag tag-warning">${f}</span>`).join(' ')}
                        </div>
                    ` : ''}
                    ${r.errors.length > 0 ? `
                        <div class="mt-16" style="color: var(--danger)">
                            <strong>处理警告：</strong>
                            <ul>${r.errors.map(e => `<li>${e}</li>`).join('')}</ul>
                        </div>
                    ` : ''}
                </div>
            </div>`;
    }

    container.innerHTML = html;

    // 显示成功通知
    const totalNew = results.reduce((s, r) => s + (r.new_records || 0), 0);
    const totalUpdated = results.reduce((s, r) => s + (r.updated_records || 0), 0);
    showToast(`导入完成！新增 ${totalNew} 条，更新 ${totalUpdated} 条`, 'success');
}
