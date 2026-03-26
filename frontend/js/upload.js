/**
 * 上传页面逻辑
 */

let pendingFiles = [];

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const previewBtn = document.getElementById('preview-btn');
    const importBtn = document.getElementById('import-btn');

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
        if (e.dataTransfer.files.length > 0) {
            setPendingFiles(e.dataTransfer.files);
        }
    });

    // 文件选择
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            setPendingFiles(e.target.files);
        }
    });

    previewBtn.addEventListener('click', () => handleFiles('preview'));
    importBtn.addEventListener('click', () => handleFiles('import'));

    initQuestionnaireForm();
});

function setPendingFiles(filesLike) {
    pendingFiles = Array.from(filesLike || []);
    const pendingWrap = document.getElementById('pending-files');
    const pendingText = document.getElementById('pending-text');
    const previewArea = document.getElementById('preview-area');
    const resultArea = document.getElementById('result-area');
    if (pendingFiles.length === 0) {
        pendingWrap.classList.add('hidden');
        return;
    }
    const fileNames = pendingFiles.map((f) => f.name).join('，');
    pendingText.textContent = `已选择 ${pendingFiles.length} 个文件：${fileNames}`;
    pendingWrap.classList.remove('hidden');
    previewArea.classList.add('hidden');
    resultArea.classList.add('hidden');
}

function getMergePolicy() {
    const el = document.getElementById('merge-policy');
    return el ? el.value : 'fill_missing';
}

function getAuthHeaders() {
    const token = localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
}

async function callUploadApi(file, endpoint) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('merge_policy', getMergePolicy());

    const resp = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        headers: getAuthHeaders()
    });

    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '上传失败' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return await resp.json();
}

async function handleFiles(mode) {
    if (pendingFiles.length === 0) {
        showToast('请先选择文件', 'warning');
        return;
    }
    const resultArea = document.getElementById('result-area');
    const previewArea = document.getElementById('preview-area');
    const progressArea = document.getElementById('progress-area');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    progressArea.classList.remove('hidden');
    previewArea.classList.add('hidden');
    resultArea.classList.add('hidden');
    progressFill.style.width = '0%';
    progressText.textContent = mode === 'preview' ? '正在分析导入影响...' : '正在导入数据...';

    const endpoint = mode === 'preview' ? '/api/upload/preview' : '/api/upload/';
    const allResults = [];
    let processed = 0;

    for (const file of pendingFiles) {
        updateProgress(file.name, processed, pendingFiles.length, mode);
        try {
            const result = await callUploadApi(file, endpoint);
            allResults.push(result);
        } catch (e) {
            allResults.push({ filename: file.name, error: e.message });
        }
        processed += 1;
        updateProgress(file.name, processed, pendingFiles.length, mode);
    }

    progressArea.classList.add('hidden');
    if (mode === 'preview') {
        previewArea.classList.remove('hidden');
        renderPreviewResults(allResults);
    } else {
        resultArea.classList.remove('hidden');
        renderResults(allResults);
    }
}

function updateProgress(filename, current, total, mode) {
    const progressText = document.getElementById('progress-text');
    const progressFill = document.getElementById('progress-fill');
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    const prefix = mode === 'preview' ? '正在分析' : '正在导入';
    progressText.textContent = `${prefix}: ${filename} (${current}/${total})`;
    progressFill.style.width = pct + '%';
}

function renderPreviewResults(results) {
    const container = document.getElementById('preview-list');
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

        const samples = (r.samples || []).map((s) => {
            const label = s.action === 'new' ? '新增' : (s.action === 'update' ? '更新' : '跳过');
            const by = s.match_by ? `（匹配: ${s.match_by}）` : '';
            return `<li>${s.name}：${label}${by}</li>`;
        }).join('');

        html += `
            <div class="card mb-16">
                <div class="card-header">
                    <h2>🔎 ${r.filename}</h2>
                </div>
                <div class="card-body">
                    <p class="text-muted mb-16">策略：<strong>${translatePolicy(r.merge_policy)}</strong></p>
                    <div class="stats-grid">
                        <div class="stat-card"><div class="stat-info"><h3>${r.total_records}</h3><p>总记录数</p></div></div>
                        <div class="stat-card"><div class="stat-info"><h3>${r.new_records}</h3><p>预计新增</p></div></div>
                        <div class="stat-card"><div class="stat-info"><h3>${r.updated_records}</h3><p>预计更新</p></div></div>
                        <div class="stat-card"><div class="stat-info"><h3>${r.skipped_records}</h3><p>预计跳过</p></div></div>
                    </div>
                    ${samples ? `<div class="mt-16"><strong>样例预览：</strong><ul>${samples}</ul></div>` : ''}
                    ${r.new_fields && r.new_fields.length > 0 ? `
                        <div class="mt-16">
                            <strong>新发现字段：</strong>
                            ${r.new_fields.map(f => `<span class="tag tag-warning">${f}</span>`).join(' ')}
                        </div>
                    ` : ''}
                    ${r.errors && r.errors.length > 0 ? `
                        <div class="mt-16" style="color: var(--danger)">
                            <strong>分析警告：</strong>
                            <ul>${r.errors.map(e => `<li>${e}</li>`).join('')}</ul>
                        </div>
                    ` : ''}
                </div>
            </div>`;
    }

    container.innerHTML = html;
    showToast('预览完成，确认无误后可直接点击“确认并开始导入”', 'info');
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
                    <p class="text-muted mb-16">策略：<strong>${translatePolicy(getMergePolicy())}</strong></p>
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

    const totalNew = results.reduce((s, r) => s + (r.new_records || 0), 0);
    const totalUpdated = results.reduce((s, r) => s + (r.updated_records || 0), 0);
    showToast(`导入完成！新增 ${totalNew} 条，更新 ${totalUpdated} 条`, 'success');
}

function translatePolicy(policy) {
    if (policy === 'overwrite') return '覆盖已有字段';
    if (policy === 'skip_existing') return '重复记录跳过';
    return '仅补全缺失字段';
}

function parseExtraLines(text) {
    const extra = {};
    const lines = String(text || '').split('\n');
    for (const line of lines) {
        const raw = line.trim();
        if (!raw) continue;
        const idx = raw.indexOf('=');
        if (idx <= 0) continue;
        const key = raw.slice(0, idx).trim();
        const value = raw.slice(idx + 1).trim();
        if (!key || !value) continue;
        extra[key] = value;
    }
    return extra;
}

function initQuestionnaireForm() {
    const form = document.getElementById('questionnaire-form');
    if (!form) return;
    form.addEventListener('submit', submitQuestionnaireForm);
}

function buildQuestionnairePayload(form) {
    const data = new FormData(form);
    const payload = {};
    const extraFields = parseExtraLines(data.get('extra_lines'));

    for (const [key, val] of data.entries()) {
        if (key === 'extra_lines') continue;
        const value = String(val || '').trim();
        if (!value) continue;
        if (key === 'tags') {
            const tags = value.split(/[,，]/).map((t) => t.trim()).filter(Boolean);
            if (tags.length) payload.tags = tags;
            continue;
        }
        payload[key] = value;
    }

    if (Object.keys(extraFields).length) {
        payload.extra_fields = extraFields;
    }
    return payload;
}

function renderQuestionnaireResult(result) {
    const box = document.getElementById('questionnaire-result');
    if (!box) return;
    const actionText = result.action === 'created'
        ? '✅ 新增成功'
        : result.action === 'updated'
            ? '🔄 已去重并更新现有教师'
            : '⏭️ 命中重复且无需变更';
    const matchByMap = {
        id_card: '身份证号',
        mobile: '手机号',
        name: '姓名'
    };
    const matchText = result.matched_by ? `匹配依据：${matchByMap[result.matched_by] || result.matched_by}` : '匹配依据：无（新增）';

    box.classList.remove('hidden');
    box.innerHTML = `
        <div class="card">
            <div class="card-body">
                <h3>${actionText}</h3>
                <p class="text-muted" style="margin-top:8px;">教师ID：${result.teacher_id}</p>
                <p class="text-muted" style="margin-top:8px;">${matchText}</p>
                <p class="text-muted" style="margin-top:8px;">策略：${translatePolicy(result.merge_policy)}</p>
                <div class="mt-16">
                    <a class="btn btn-outline btn-sm" href="/detail?id=${result.teacher_id}">查看教师详情</a>
                </div>
            </div>
        </div>`;
}

async function submitQuestionnaireForm(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const submitBtn = form.querySelector('button[type="submit"]');
    const policyEl = document.getElementById('questionnaire-merge-policy');
    const policy = policyEl ? policyEl.value : 'fill_missing';
    const payload = buildQuestionnairePayload(form);

    if (!payload.name) {
        showToast('姓名为必填项', 'warning');
        return;
    }

    submitBtn.disabled = true;
    const oldText = submitBtn.textContent;
    submitBtn.textContent = '提交中...';
    try {
        const resp = await fetch(`/api/teachers/questionnaire?merge_policy=${encodeURIComponent(policy)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '提交失败' }));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }

        const result = await resp.json();
        renderQuestionnaireResult(result);
        showToast(result.message || '问卷录入成功', 'success');
        if (result.action === 'created') {
            form.reset();
        }
    } catch (err) {
        showToast(err.message || '提交失败', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = oldText;
    }
}
