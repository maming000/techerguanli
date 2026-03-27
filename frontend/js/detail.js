/**
 * 教师详情页逻辑
 */

let currentTeacher = null;
let currentUser = null;
let teacherAccount = null;
let openEditOnLoad = false;

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    openEditOnLoad = window.location.hash === '#edit' || params.get('auto_edit') === '1';
    if (id) {
        initUserAndLoad(id);
    } else {
        renderPageError('未指定教师', '请从首页选择一个教师查看详情');
    }
    const avatarInput = document.getElementById('avatar-input');
    if (avatarInput) {
        avatarInput.addEventListener('change', uploadAvatar);
    }
    initDetailClock();
    initCollapseButtons();
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
        tryOpenEditFromUrl();
    } catch (e) {
        renderPageError('加载失败', e.message || '请求异常');
    }
}

function renderPageError(title, msg) {
    const target = document.getElementById('center-basic-grid')
        || document.getElementById('right-work-grid')
        || document.querySelector('.detail-cyber-content')
        || document.body;
    target.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>${title}</h3><p>${msg}</p></div>`;
}

function canEditCurrentTeacher() {
    if (!currentUser || !currentTeacher) return false;
    if (currentUser.role === 'admin') return true;
    if (currentUser.role === 'teacher' && currentUser.teacher_id === currentTeacher.id) return true;
    return false;
}

function tryOpenEditFromUrl() {
    if (!openEditOnLoad) return;
    openEditOnLoad = false;
    if (!canEditCurrentTeacher()) return;
    showEditModal();
}

async function loadTeacherAccount() {
    teacherAccount = null;
    if (!currentUser || currentUser.role !== 'admin' || !currentTeacher) return;
    try {
        teacherAccount = await api(`/api/users/teacher/${currentTeacher.id}`);
    } catch (e) {}
}

function renderDetail(t) {
    const schema = window.TeacherSchema;
    const data = schema ? schema.normalizeTeacher(t) : t;
    const isFilled = schema ? schema.isFilled : (val) => !!val;
    const display = schema ? schema.display : (val) => (val || '-');

    const profileColor = getCoverColor(t);
    const avatarUrl = getAvatarUrl(t);
    const initials = (data.name || '?').slice(0, 1);
    const avatarSlot = document.getElementById('hero-avatar-slot');
    if (avatarSlot) {
        avatarSlot.innerHTML = avatarUrl
            ? `<img class="detail-cyber-avatar" src="${avatarUrl}" alt="${display(data.name)}">`
            : `<div class="detail-cyber-avatar-placeholder">${initials}</div>`;
    }
    const profileHero = document.getElementById('profile-hero');
    if (profileHero) {
        const isMedical = document.body.classList.contains('detail-medical-page');
        if (isMedical) {
            // 医生版保持稳定浅底，避免深色封面导致姓名不可读。
            profileHero.style.background = 'linear-gradient(180deg, #fbfdff 0%, #eff5fc 100%)';
            profileHero.style.borderBottomColor = '#dce5f0';
            profileHero.style.boxShadow = `inset 0 3px 0 ${lightenHex(profileColor, 0.65)}`;
        } else {
            profileHero.style.background = `linear-gradient(140deg, ${profileColor}, #1a2f5b)`;
            profileHero.style.borderBottomColor = '';
            profileHero.style.boxShadow = '';
        }
    }

    const nameText = document.getElementById('teacher-name-text');
    if (nameText) nameText.textContent = data.name || '教师详情';
    const metaText = document.getElementById('teacher-meta');
    if (metaText) metaText.textContent = `${data.name || '未知教师'} | 教师详情页`;

    const leftOverview = document.getElementById('left-overview-grid');
    const leftRows = [
        ['性别', data.gender],
        ['职称', data.title],
        ['任教学科', data.subject],
        ['入职日期', data.hire_date],
        ['状态', t?.extra_fields?.status || '在职']
    ].filter(([, v]) => isFilled(v)).map(([k, v]) => renderKV(k, display(v), true)).join('');
    if (leftOverview) leftOverview.innerHTML = leftRows || '<div class="text-muted">暂无概览信息</div>';

    const basicFields = [
        ['身份证号', data.id_card],
        ['手机', data.mobile],
        ['小号', data.short_phone],
        ['出生日期', data.birth_date],
        ['年龄', data.age],
        ['民族', data.ethnicity],
        ['政治面貌', data.political_status],
        ['籍贯', data.native_place],
        ['户籍所在地', pickExtra(t, ['户籍所在地', '户籍地'])],
        ['邮箱 / 电子邮件', data.email],
        ['联系方式', data.phone],
        ['档案编号', data.archive_no],
        ['地址', data.address]
    ];
    fillGrid('center-basic-grid', basicFields, ['地址', '户籍所在地', '联系方式', '邮箱 / 电子邮件'], isFilled, display);

    const eduFields = [
        ['毕业院校', data.graduate_school],
        ['学历', data.education],
        ['专业', data.major],
        ['毕业时间', pickExtra(t, ['毕业时间'])],
        ['毕业年度', pickExtra(t, ['毕业年度'])],
        ['是否师范类', pickExtra(t, ['是否师范类'])],
        ['是否省内毕业生', pickExtra(t, ['是否省内毕业生', '是否省内毕业'])]
    ];
    fillGrid('right-education-grid', eduFields, [], isFilled, display);

    const workFields = [
        ['工号', data.employee_id],
        ['职称', data.title],
        ['任教学科', data.subject],
        ['入职日期', data.hire_date],
        ['原单位', pickExtra(t, ['原单位'])],
        ['参工时间', data.civil_service_date],
        ['参加工作时间', pickExtra(t, ['参加工作时间'])],
        ['支教或调入', pickExtra(t, ['支教或调入'])],
        ['入党时间', data.party_join_date]
    ];
    fillGrid('right-work-grid', workFields, [], isFilled, display);

    const extraBox = document.getElementById('right-extra-content');
    if (extraBox) {
        const plate1 = display(data.plate_no_1);
        const plate2 = display(data.plate_no_2);
        const honors = display(pickExtra(t, ['在校或工作中曾获得荣誉', '在校或在工作', '荣誉']));
        const known = new Set(['__profile_avatar', '__profile_cover_color', 'status', '户籍所在地', '户籍地', '毕业时间', '毕业年度', '是否师范类', '是否省内毕业生', '是否省内毕业', '原单位', '参加工作时间', '支教或调入', '在校或工作中曾获得荣誉', '在校或在工作', '荣誉']);
        const extraTags = Object.entries(t.extra_fields || {})
            .filter(([k, v]) => !known.has(k) && isFilled(v))
            .map(([k, v]) => `<span class="detail-cyber-extra-tag">${k}：${display(v)}</span>`)
            .join('');
        extraBox.innerHTML = `
            <div class="detail-cyber-form-grid detail-cyber-two-col">
                ${renderKV('车牌号码1', plate1)}
                ${renderKV('车牌号码2', plate2)}
            </div>
            <div class="detail-cyber-honor-box">
                <div class="detail-cyber-honor-title">在校或工作中曾获得荣誉</div>
                <div class="detail-cyber-honor-scroll">${honors}</div>
            </div>
            ${extraTags ? `<div class="detail-cyber-extra-tags">${extraTags}</div>` : ''}
        `;
    }

    // 标签
    renderTagsSection(t);
}

function pickExtra(t, keys) {
    const extra = t?.extra_fields || {};
    for (const k of keys) {
        if (extra[k] !== undefined && extra[k] !== null && String(extra[k]).trim() !== '') return extra[k];
    }
    return '';
}

function lightenHex(hex, ratio = 0.8) {
    const m = String(hex || '').trim().match(/^#([0-9a-fA-F]{6})$/);
    if (!m) return '#f4f8fe';
    const raw = m[1];
    const r = parseInt(raw.slice(0, 2), 16);
    const g = parseInt(raw.slice(2, 4), 16);
    const b = parseInt(raw.slice(4, 6), 16);
    const blend = (v) => Math.round(v + (255 - v) * Math.max(0, Math.min(1, ratio)));
    const toHex = (v) => blend(v).toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function renderKV(label, value, compact = false) {
    return `<div class="detail-cyber-kv ${compact ? 'compact' : ''}">
        <span class="detail-cyber-k">${label}</span>
        <span class="detail-cyber-v">${value || '-'}</span>
    </div>`;
}

function fillGrid(containerId, rows, fullLineLabels, isFilled, display) {
    const box = document.getElementById(containerId);
    if (!box) return;
    const html = rows
        .filter(([, v]) => isFilled(v))
        .map(([k, v]) => {
            const full = fullLineLabels.includes(k) ? ' full' : '';
            return `<div class="detail-cyber-kv${full}">
                <span class="detail-cyber-k">${k}</span>
                <span class="detail-cyber-v">${display(v)}</span>
            </div>`;
        })
        .join('');
    box.innerHTML = html || '<div class="text-muted">暂无信息</div>';
}

function getCoverColor(t) {
    return t?.extra_fields?.__profile_cover_color || '#275bc6';
}

function getAvatarUrl(t) {
    return t?.extra_fields?.__profile_avatar || '';
}

function initHeroTilt() {
    // reserved
}

function initCardParallax() {
    // 已按需求关闭鼠标悬停歪斜效果
}

function playTitleBurst() {
    // removed for cleaner UI
}

function renderTagsSection(t) {
    const container = document.getElementById('tags-section');
    const tags = t.tags || [];
    const colors = ['primary', 'success', 'warning', 'danger'];

    let html = '<div class="detail-cyber-tag-row">';
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
    refreshScrollReveal();
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

    let html = '<div class="detail-cyber-log-list">';
    for (const log of logs) {
        html += `
            <div class="detail-cyber-log-item">
                <div class="detail-cyber-log-head">
                    <span class="tag tag-primary">${log.action}</span>
                    <span class="detail-cyber-k">${log.field_name || '系统记录'}</span>
                    <span class="text-muted">${formatDate(log.created_at)}</span>
                </div>
                <div class="detail-cyber-log-values">
                    <div><strong>旧值：</strong>${log.old_value || '-'}</div>
                    <div><strong>新值：</strong>${log.new_value || '-'}</div>
                </div>
            </div>`;
    }
    html += '</div>';
    container.innerHTML = html;
}

function initScrollReveal() {
    // removed for cleaner UI
}

function refreshScrollReveal() {
    // removed for cleaner UI
}

function initDetailClock() {
    const el = document.getElementById('detail-current-time');
    if (!el) return;
    const tick = () => {
        const d = new Date();
        el.textContent = d.toLocaleString('zh-CN', { hour12: false });
    };
    tick();
    setInterval(tick, 1000);
}

function initCollapseButtons() {
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.detail-collapse-btn');
        if (!btn) return;
        const targetId = btn.getAttribute('data-target');
        if (!targetId) return;
        const panel = document.getElementById(targetId);
        if (!panel) return;
        panel.classList.toggle('is-collapsed');
        btn.textContent = panel.classList.contains('is-collapsed') ? '展开' : '折叠';
    });
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
