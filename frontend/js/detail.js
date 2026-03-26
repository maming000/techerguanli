/**
 * 教师详情页逻辑
 */

let currentTeacher = null;
let currentUser = null;
let teacherAccount = null;

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (id) {
        initUserAndLoad(id);
    } else {
        document.getElementById('detail-content').innerHTML =
            '<div class="empty-state"><div class="empty-icon">🔍</div><h3>未指定教师</h3><p>请从首页选择一个教师查看详情</p></div>';
    }
    const avatarInput = document.getElementById('avatar-input');
    if (avatarInput) {
        avatarInput.addEventListener('change', uploadAvatar);
    }
    initHeroTilt();
});

async function initUserAndLoad(id) {
    currentUser = await getCurrentUser();
    updateHeaderActions();
    await loadTeacher(id);
}

function updateHeaderActions() {
    const editBtn = document.querySelector('.header-actions .btn.btn-primary');
    const delBtn = document.querySelector('.header-actions .btn.btn-danger');
    if (!currentUser) return;
    if (currentUser.role === 'teacher') {
        if (currentTeacher && currentUser.teacher_id !== currentTeacher.id) {
            if (editBtn) editBtn.style.display = 'none';
        }
        if (delBtn) delBtn.style.display = 'none';
    }
    if (currentUser.role === 'admin') {
        if (editBtn) editBtn.style.display = '';
        if (delBtn) delBtn.style.display = '';
    } else if (currentUser.role === 'viewer') {
        if (editBtn) editBtn.style.display = 'none';
        if (delBtn) delBtn.style.display = 'none';
    }
}

async function loadTeacher(id) {
    try {
        currentTeacher = await api(`/api/teachers/${id}`);
        renderDetail(currentTeacher);
        loadLogs(id);
        updateHeaderActions();
        await loadTeacherAccount();
        renderAccountSection();
    } catch (e) {
        document.getElementById('detail-content').innerHTML =
            `<div class="empty-state"><div class="empty-icon">❌</div><h3>加载失败</h3><p>${e.message}</p></div>`;
    }
}

async function loadTeacherAccount() {
    teacherAccount = null;
    if (!currentUser || currentUser.role !== 'admin' || !currentTeacher) return;
    try {
        teacherAccount = await api(`/api/users/teacher/${currentTeacher.id}`);
    } catch (e) {}
}

function renderDetail(t) {
    const groups = [
        {
            title: '身份信息',
            fields: [
                ['name', '姓名'], ['gender', '性别'], ['id_card', '身份证号'],
                ['birth_date', '出生日期'], ['age', '年龄'], ['ethnicity', '民族'], ['native_place', '籍贯']
            ]
        },
        {
            title: '联系方式',
            fields: [
                ['mobile', '手机'], ['phone', '联系电话'], ['short_phone', '小号'],
                ['address', '家庭住址'], ['email', '邮箱']
            ]
        },
        {
            title: '任职信息',
            fields: [
                ['graduate_school', '毕业院校'], ['education', '学历'], ['political_status', '政治面貌'],
                ['title', '职称'], ['position', '职务'], ['subject', '任教学科'],
                ['hire_date', '入职日期'], ['employee_id', '工号']
            ]
        }
    ];

    let detailHtml = '';
    groups.forEach((group) => {
        detailHtml += `<section class="detail-section-card mb-16"><h3 class="detail-section-title">${group.title}</h3><div class="detail-grid">`;
        group.fields.forEach(([key, label]) => {
            detailHtml += `
                <div class="detail-item">
                    <span class="detail-label">${label}</span>
                    <span class="detail-value">${t[key] || '-'}</span>
                </div>`;
        });
        detailHtml += '</div></section>';
    });

    if (t.extra_fields && Object.keys(t.extra_fields).length > 0) {
        detailHtml += '<section class="detail-section-card"><h3 class="detail-section-title">扩展信息</h3><div class="detail-grid">';
        for (const [key, val] of Object.entries(t.extra_fields)) {
            if (key.startsWith('__profile_')) continue;
            detailHtml += `
                <div class="detail-item">
                    <span class="detail-label">${key}</span>
                    <span class="detail-value">${val || '-'}</span>
                </div>`;
        }
        detailHtml += '</div></section>';
    }

    document.getElementById('detail-content').innerHTML = detailHtml;

    // 标签
    renderTagsSection(t);
    renderProfileHero(t);

    // 更新页面标题
    document.getElementById('teacher-name').textContent = t.name || '未知教师';
    document.getElementById('teacher-meta').textContent =
        `ID: ${t.id} | 创建: ${formatDate(t.created_at)} | 更新: ${formatDate(t.updated_at)}`;
}

function getCoverColor(t) {
    return t?.extra_fields?.__profile_cover_color || '#275bc6';
}

function getAvatarUrl(t) {
    return t?.extra_fields?.__profile_avatar || '';
}

function renderProfileHero(t) {
    const hero = document.getElementById('profile-hero');
    const avatarSlot = document.getElementById('hero-avatar-slot');
    if (!hero || !avatarSlot) return;
    const color = getCoverColor(t);
    hero.style.background = `linear-gradient(135deg, ${color} 0%, #0f2e63 100%)`;
    const avatar = getAvatarUrl(t);
    if (avatar) {
        avatarSlot.innerHTML = `<img class="profile-avatar" src="${avatar}" alt="${t.name || ''}">`;
    } else {
        avatarSlot.innerHTML = `<div class="profile-avatar-placeholder">${(t.name || '?').slice(0, 1)}</div>`;
    }
}

function initHeroTilt() {
    const hero = document.getElementById('profile-hero');
    if (!hero) return;

    hero.addEventListener('mousemove', (e) => {
        const rect = hero.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const rx = ((y / rect.height) - 0.5) * -3.2;
        const ry = ((x / rect.width) - 0.5) * 4.5;
        hero.style.transform = `perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg)`;
    });

    hero.addEventListener('mouseleave', () => {
        hero.style.transform = 'perspective(1000px) rotateX(2deg)';
    });
}

function renderTagsSection(t) {
    const container = document.getElementById('tags-section');
    const tags = t.tags || [];
    const colors = ['primary', 'success', 'warning', 'danger'];

    let html = '<div class="flex items-center gap-8" style="flex-wrap: wrap;">';
    tags.forEach((tag, i) => {
        html += `<span class="tag tag-${colors[i % colors.length]}">
            ${tag}
            <span class="tag-remove" onclick="removeTag('${tag}')">×</span>
        </span>`;
    });
    html += `<button class="btn btn-outline btn-sm" onclick="showAddTagModal()">+ 添加标签</button>`;
    html += '</div>';
    container.innerHTML = html;
}

async function removeTag(tag) {
    if (!currentTeacher) return;
    try {
        const resp = await api(`/api/teachers/${currentTeacher.id}/tags?tag=${encodeURIComponent(tag)}`, { method: 'DELETE' });
        if (resp && resp.pending) showToast('标签改动已提交管理员审核', 'info');
        else showToast('标签已删除', 'success');
        await loadTeacher(currentTeacher.id);
    } catch (e) {
        // error already shown by api()
    }
}

function showAddTagModal() {
    const presetTags = ['班主任', '骨干教师', '新教师', '优秀教师', '学科带头人', '备课组长', '教研组长'];
    let html = `
        <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
            <div class="modal">
                <div class="modal-header">
                    <h3>添加标签</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="mb-16">
                        <label class="form-label">快捷标签</label>
                        <div class="btn-group">
                            ${presetTags.map(tag => `<button class="btn btn-outline btn-sm" onclick="addTag('${tag}')">${tag}</button>`).join('')}
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">自定义标签</label>
                        <div class="flex gap-8">
                            <input type="text" id="custom-tag-input" class="form-control" placeholder="输入标签名">
                            <button class="btn btn-primary" onclick="addCustomTag()">添加</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function addTag(tag) {
    if (!currentTeacher) return;
    try {
        const resp = await api(`/api/teachers/${currentTeacher.id}/tags?tag=${encodeURIComponent(tag)}`, { method: 'POST' });
        if (resp && resp.pending) showToast('标签改动已提交管理员审核', 'info');
        else showToast(`已添加标签: ${tag}`, 'success');
        document.querySelector('.modal-overlay')?.remove();
        await loadTeacher(currentTeacher.id);
    } catch (e) { }
}

function addCustomTag() {
    const input = document.getElementById('custom-tag-input');
    const tag = input.value.trim();
    if (tag) addTag(tag);
}

function showEditModal() {
    if (!currentTeacher) return;
    const t = currentTeacher;
    const fields = [
        { key: 'name', label: '姓名' },
        { key: 'gender', label: '性别', type: 'select', options: ['男', '女'] },
        { key: 'id_card', label: '身份证号' },
        { key: 'phone', label: '联系电话' },
        { key: 'mobile', label: '手机' },
        { key: 'short_phone', label: '小号' },
        { key: 'graduate_school', label: '毕业院校' },
        { key: 'education', label: '学历', type: 'select', options: ['博士', '硕士', '本科', '大专', '中专', '高中'] },
        { key: 'political_status', label: '政治面貌', type: 'select', options: ['中共党员', '中共预备党员', '共青团员', '民主党派', '群众'] },
        { key: 'ethnicity', label: '民族' },
        { key: 'native_place', label: '籍贯' },
        { key: 'address', label: '家庭住址' },
        { key: 'email', label: '邮箱' },
        { key: 'title', label: '职称' },
        { key: 'position', label: '职务' },
        { key: 'subject', label: '任教学科' },
        { key: 'hire_date', label: '入职日期' },
        { key: 'employee_id', label: '工号' },
    ];

    let formHtml = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">';
    for (const f of fields) {
        const val = t[f.key] || '';
        if (f.type === 'select') {
            formHtml += `
                <div class="form-group">
                    <label class="form-label">${f.label}</label>
                    <select class="form-control" id="edit-${f.key}">
                        <option value="">请选择</option>
                        ${f.options.map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`).join('')}
                    </select>
                </div>`;
        } else {
            formHtml += `
                <div class="form-group">
                    <label class="form-label">${f.label}</label>
                    <input type="text" class="form-control" id="edit-${f.key}" value="${val}">
                </div>`;
        }
    }
    formHtml += '</div>';

    // 扩展字段编辑
    formHtml += '<h4 style="margin: 16px 0 8px;">扩展字段</h4>';
    formHtml += '<div id="extra-fields-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">';
    if (t.extra_fields && Object.keys(t.extra_fields).length > 0) {
        for (const [key, val] of Object.entries(t.extra_fields)) {
            formHtml += `
                <div class="form-group">
                    <label class="form-label">${key}</label>
                    <input type="text" class="form-control" data-extra="${key}" value="${val || ''}">
                </div>`;
        }
    }
    formHtml += '</div>';
    formHtml += `
        <div class="mt-12" style="display:flex; gap:8px; align-items:center;">
            <input type="text" class="form-control" id="new-extra-key" placeholder="扩展字段名称（如：原单位）" style="flex:1;">
            <input type="text" class="form-control" id="new-extra-value" placeholder="字段值" style="flex:1;">
            <button class="btn btn-outline btn-sm" onclick="addExtraField()">添加</button>
        </div>
    `;

    let html = `
        <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
            <div class="modal" style="max-width: 800px;">
                <div class="modal-header">
                    <h3>编辑教师信息</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">${formHtml}</div>
                <div class="modal-footer">
                    <button class="btn btn-outline" onclick="this.closest('.modal-overlay').remove()">取消</button>
                    <button class="btn btn-primary" onclick="saveTeacher()">保存</button>
                </div>
            </div>
        </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
}

function addExtraField() {
    const keyEl = document.getElementById('new-extra-key');
    const valEl = document.getElementById('new-extra-value');
    if (!keyEl || !valEl) return;
    const key = keyEl.value.trim();
    const val = valEl.value.trim();
    if (!key) {
        showToast('请输入扩展字段名称', 'warning');
        return;
    }
    const grid = document.getElementById('extra-fields-grid');
    if (!grid) return;
    // 防止重复字段名
    if (grid.querySelector(`[data-extra="${key}"]`)) {
        showToast('该扩展字段已存在', 'warning');
        return;
    }
    const wrapper = document.createElement('div');
    wrapper.className = 'form-group';
    wrapper.innerHTML = `
        <label class="form-label">${key}</label>
        <input type="text" class="form-control" data-extra="${key}" value="${val}">
    `;
    grid.appendChild(wrapper);
    keyEl.value = '';
    valEl.value = '';
}

async function saveTeacher() {
    if (!currentTeacher) return;
    if (currentUser && currentUser.role === 'teacher' && currentUser.teacher_id !== currentTeacher.id) {
        showToast('无权限修改他人信息', 'warning');
        return;
    }
    if (!confirm(`确定要修改教师 "${currentTeacher.name || '未知教师'}" 的信息吗？`)) return;

    const fields = ['name', 'gender', 'id_card', 'phone', 'mobile', 'short_phone',
        'graduate_school', 'education', 'political_status', 'ethnicity',
        'native_place', 'address', 'email', 'title', 'position', 'subject',
        'hire_date', 'employee_id'];

    const data = {};
    for (const f of fields) {
        const el = document.getElementById(`edit-${f}`);
        if (el) data[f] = el.value;
    }

    // 收集扩展字段
    const extraFields = {};
    document.querySelectorAll('[data-extra]').forEach(el => {
        extraFields[el.dataset.extra] = el.value;
    });
    if (Object.keys(extraFields).length > 0) {
        data.extra_fields = extraFields;
    }

    try {
        const resp = await api(`/api/teachers/${currentTeacher.id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        if (resp && resp.pending) {
            showToast('已提交管理员审核', 'info');
        } else {
            showToast('保存成功', 'success');
        }
        document.querySelector('.modal-overlay')?.remove();
        await loadTeacher(currentTeacher.id);
    } catch (e) { }
}

async function deleteTeacher() {
    if (!currentTeacher) return;
    if (currentUser && currentUser.role !== 'admin') {
        showToast('无权限删除', 'warning');
        return;
    }
    if (!confirm(`确定要删除教师 "${currentTeacher.name}" 吗？此操作不可恢复。`)) return;

    try {
        await api(`/api/teachers/${currentTeacher.id}`, { method: 'DELETE' });
        showToast('已删除', 'success');
        setTimeout(() => window.location.href = '/', 500);
    } catch (e) { }
}

function renderAccountSection() {
    const card = document.getElementById('account-card');
    const section = document.getElementById('account-section');
    if (!card || !section) return;
    if (!currentUser || currentUser.role !== 'admin' || !currentTeacher) {
        card.style.display = 'none';
        return;
    }
    card.style.display = '';
    const accountInfo = teacherAccount
        ? `<div class="text-muted" style="margin-bottom: 8px;">当前账号：${teacherAccount.username} (ID: ${teacherAccount.id})</div>`
        : `<div class="text-muted" style="margin-bottom: 8px;">该教师尚未创建账号</div>`;
    section.innerHTML = `
        ${accountInfo}
        <div class="flex items-center gap-12" style="flex-wrap: wrap;">
            <button class="btn btn-outline" onclick="createTeacherAccount()">创建账号</button>
            <button class="btn btn-outline" onclick="resetTeacherPassword()" ${teacherAccount ? '' : 'disabled'}>重置密码</button>
            <button class="btn btn-danger" onclick="deleteTeacherAccount()" ${teacherAccount ? '' : 'disabled'}>删除账号</button>
        </div>
        <p class="text-muted mt-8" style="font-size: 12px;">账号将绑定当前教师。</p>
    `;
}

async function createTeacherAccount() {
    if (!currentTeacher) return;
    const username = prompt('请输入账号（留空自动生成）') || '';
    const password = prompt('请输入初始密码（留空自动生成）') || '';
    try {
        const resp = await api('/api/users/teacher', {
            method: 'POST',
            body: JSON.stringify({
                teacher_id: currentTeacher.id,
                username: username || null,
                password: password || null
            })
        });
        showToast(`账号已创建：${resp.username} / ${resp.password}`, 'success');
    } catch (e) {}
}

async function resetTeacherPassword() {
    if (!teacherAccount) return;
    try {
        const resp = await api(`/api/users/${teacherAccount.id}/reset-password`, {
            method: 'POST',
            body: JSON.stringify({})
        });
        showToast(`新密码：${resp.password}`, 'success');
    } catch (e) {}
}

async function deleteTeacherAccount() {
    if (!teacherAccount) return;
    if (!confirm('确定要删除该账号吗？')) return;
    try {
        await api(`/api/users/${teacherAccount.id}`, { method: 'DELETE' });
        showToast('账号已删除', 'success');
        teacherAccount = null;
        renderAccountSection();
    } catch (e) {}
}

async function loadLogs(teacherId) {
    try {
        const logs = await api(`/api/teachers/${teacherId}/logs`);
        renderLogs(logs);
    } catch (e) { }
}

function renderLogs(logs) {
    const container = document.getElementById('logs-section');
    if (!logs || logs.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无修改记录</p>';
        return;
    }

    let html = '<div class="timeline">';
    for (const log of logs) {
        html += `
            <div class="timeline-item">
                <span class="timeline-dot"></span>
                <div class="timeline-title">
                    <span class="tag tag-primary">${log.action}</span>
                    <span class="timeline-field">${log.field_name || '系统记录'}</span>
                    <span class="text-muted">${formatDate(log.created_at)}</span>
                </div>
                <div class="timeline-values">
                    <div class="timeline-box"><strong>旧值：</strong>${log.old_value || '-'}</div>
                    <div class="timeline-box"><strong>新值：</strong>${log.new_value || '-'}</div>
                </div>
            </div>`;
    }
    html += '</div>';
    container.innerHTML = html;
}

async function uploadAvatar(e) {
    if (!currentTeacher) return;
    const file = e?.target?.files?.[0];
    if (!file) return;
    if (currentUser && currentUser.role === 'teacher' && currentUser.teacher_id !== currentTeacher.id) {
        showToast('无权限修改他人头像', 'warning');
        return;
    }

    try {
        const token = localStorage.getItem('auth_token');
        const formData = new FormData();
        formData.append('file', file);
        formData.append('cover_color', getCoverColor(currentTeacher));
        const resp = await fetch(`/api/teachers/${currentTeacher.id}/avatar`, {
            method: 'POST',
            body: formData,
            headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '上传失败' }));
            throw new Error(err.detail || '上传失败');
        }
        const data = await resp.json().catch(() => ({}));
        if (data && data.pending) showToast('头像改动已提交管理员审核', 'info');
        else showToast('头像上传成功', 'success');
        await loadTeacher(currentTeacher.id);
    } catch (err) {
        showToast(err.message || '头像上传失败', 'error');
    } finally {
        const avatarInput = document.getElementById('avatar-input');
        if (avatarInput) avatarInput.value = '';
    }
}

async function changeCoverColor() {
    if (!currentTeacher) return;
    if (currentUser && currentUser.role === 'teacher' && currentUser.teacher_id !== currentTeacher.id) {
        showToast('无权限修改他人主题色', 'warning');
        return;
    }
    const value = prompt('请输入主题色（例如 #2f6fed）', getCoverColor(currentTeacher));
    if (!value) return;
    if (!/^#[0-9a-fA-F]{6}$/.test(value.trim())) {
        showToast('主题色格式不正确，应为 #RRGGBB', 'warning');
        return;
    }

    try {
        const token = localStorage.getItem('auth_token');
        const formData = new FormData();
        formData.append('cover_color', value.trim().toLowerCase());
        const resp = await fetch(`/api/teachers/${currentTeacher.id}/profile-theme`, {
            method: 'POST',
            body: formData,
            headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '更新失败' }));
            throw new Error(err.detail || '更新失败');
        }
        const data = await resp.json().catch(() => ({}));
        if (data && data.pending) showToast('主题色改动已提交管理员审核', 'info');
        else showToast('主题色已更新', 'success');
        await loadTeacher(currentTeacher.id);
    } catch (e) {
        showToast(e.message || '主题色更新失败', 'error');
    }
}
