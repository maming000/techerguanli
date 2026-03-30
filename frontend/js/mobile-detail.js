let mCurrentTeacherRaw = null;
let mCurrentTeacherNormalized = null;
let mCurrentTeacherId = '';
let mCurrentUser = null;

function esc(v) {
    return String(v ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function iconSvg(type) {
    const map = {
        user: '<path d="M12 12a4 4 0 1 0-4-4a4 4 0 0 0 4 4Z"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
        users: '<circle cx="9" cy="9" r="3"/><circle cx="16.5" cy="10" r="2.5"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0"/><path d="M13 19a4 4 0 0 1 7 0"/>',
        calendar: '<rect x="3.5" y="5.5" width="17" height="15" rx="2.2"/><path d="M7 3.8v3.4M17 3.8v3.4M3.5 10h17"/>',
        idcard: '<rect x="3.5" y="6.5" width="17" height="11" rx="2"/><circle cx="8" cy="12" r="1.8"/><path d="M12 10h5M12 13h5M6.5 16h10.5"/>',
        flag: '<path d="M5 3.5v17"/><path d="M6.5 5h10l-2 3l2 3h-10z"/>',
        book: '<path d="M5 4.5h10.5a2 2 0 0 1 2 2V20H7a2 2 0 0 0-2 2z"/><path d="M7 4.5v17.5"/>',
        check: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 5-6"/>',
        cap: '<path d="m3.5 10 8.5-4 8.5 4-8.5 4z"/><path d="M7.2 12.2v3.1c0 1.3 2.1 2.4 4.8 2.4s4.8-1.1 4.8-2.4v-3.1"/><path d="M20.5 10v4.2"/>',
        school: '<path d="m3.5 9 8.5-4.5L20.5 9"/><path d="M5.5 10.5V19h13v-8.5"/><path d="M10 19v-5h4v5"/>',
        phone: '<rect x="7.2" y="3.2" width="9.6" height="17.6" rx="2"/><path d="M11 6h2M10 17h4"/>',
        mail: '<rect x="3.5" y="6.2" width="17" height="11.6" rx="2"/><path d="m4.5 7.5 7.5 5.2 7.5-5.2"/>',
        pin: '<path d="M12 20s6-5.2 6-10a6 6 0 1 0-12 0c0 4.8 6 10 6 10Z"/><circle cx="12" cy="10" r="2.2"/>',
        bus: '<rect x="4" y="5" width="16" height="13" rx="2"/><path d="M7 5v-1.8M17 5v-1.8M4 11h16"/><circle cx="8" cy="17.5" r="1.2"/><circle cx="16" cy="17.5" r="1.2"/>'
    };
    const body = map[type] || map.book;
    return `<svg viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
}

function renderHero(p) {
    const initial = esc((p.name || '师').slice(0, 1));
    return `
        <section class="m-cyber-hero">
            <div class="m-cyber-wave"></div>
            <div class="m-cyber-avatar-ring">
                ${p.avatar
                    ? `<img class="m-cyber-avatar" src="${esc(p.avatar)}" alt="${esc(p.name)}">`
                    : `<div class="m-cyber-avatar-placeholder">${initial}</div>`}
                <span class="m-cyber-avatar-core"></span>
            </div>
            <h2 class="m-cyber-name">${esc(p.name || '教师详情')}</h2>
            <div class="m-cyber-nameplate"></div>
        </section>
    `;
}

function iconKeyByField(fieldKey) {
    const map = {
        name: 'user',
        gender: 'user',
        id_card: 'idcard',
        birth_date: 'calendar',
        age: 'calendar',
        ethnicity: 'users',
        native_place: 'pin',
        political_status: 'flag',
        hire_date: 'calendar',
        subject: 'book',
        title: 'check',
        position: 'check',
        employee_id: 'calendar',
        civil_service_date: 'calendar',
        archive_no: 'calendar',
        education: 'cap',
        degree: 'cap',
        graduate_school: 'school',
        major: 'book',
        party_join_date: 'calendar',
        qualification: 'check',
        mobile: 'phone',
        short_phone: 'phone',
        email: 'mail',
        phone: 'phone',
        address: 'pin',
        plate_no_1: 'bus',
        plate_no_2: 'bus'
    };
    return map[fieldKey] || 'book';
}

function renderSectionCard(profile, section, no, schema) {
    const fields = schema.getVisibleFields(section, profile);
    if (!fields.length) return '';
    const rows = fields.map((f) => {
        const value = schema.display(profile[f.key]);
        return `
            <div class="m-cyber-row">
                <span class="m-cyber-icon">${iconSvg(iconKeyByField(f.key))}</span>
                <span class="m-cyber-k">${esc(f.label)}</span>
                <span class="m-cyber-v">${esc(value).replace(/\n/g, '<br>')}</span>
            </div>
        `;
    }).join('');
    return `
        <section class="m-cyber-card">
            <h3 class="m-cyber-card-title">${no}. ${section.title}</h3>
            <div class="m-cyber-card-body">${rows}</div>
        </section>
    `;
}

function renderBottomActions(id) {
    const canAssess = mCurrentUser && (mCurrentUser.role === 'teacher' || mCurrentUser.role === 'admin');
    return `
        <div class="m-cyber-actions-wrap">
            <div class="m-cyber-divider"></div>
            <div class="m-cyber-actions">
                <button class="m-cyber-btn m-cyber-btn-primary" onclick="openMobileEditModal()">编辑资料</button>
                <button class="m-cyber-btn" onclick="${canAssess ? "window.location.href='/assessment/start'" : "mShowToast('当前账号无测评权限', 'warning')"}">人格测评</button>
                <button class="m-cyber-btn" onclick="mShowToast('更多功能开发中', 'info')">更多操作</button>
            </div>
        </div>
    `;
}

const MOBILE_EDIT_FIELDS = [
    { key: 'name', label: '姓名' },
    { key: 'gender', label: '性别', type: 'select', options: ['男', '女'] },
    { key: 'id_card', label: '身份证号' },
    { key: 'birth_date', label: '出生日期' },
    { key: 'ethnicity', label: '民族' },
    { key: 'native_place', label: '籍贯' },
    { key: 'political_status', label: '政治面貌', type: 'select', options: ['中共党员', '中共预备党员', '共青团员', '民主党派', '群众'] },
    { key: 'hire_date', label: '入职日期' },
    { key: 'subject', label: '任教学科' },
    { key: 'title', label: '职称' },
    { key: 'position', label: '职务' },
    { key: 'employee_id', label: '工号' },
    { key: 'civil_service_date', label: '参公时间' },
    { key: 'archive_no', label: '档案编号' },
    { key: 'education', label: '最高学历', type: 'select', options: ['博士', '硕士', '本科', '大专', '中专', '高中'] },
    { key: 'degree', label: '最高学位' },
    { key: 'graduate_school', label: '毕业学校' },
    { key: 'major', label: '专业' },
    { key: 'party_join_date', label: '入党时间' },
    { key: 'qualification', label: '资格证书' },
    { key: 'mobile', label: '手机号码' },
    { key: 'short_phone', label: '小号' },
    { key: 'email', label: '电子邮件' },
    { key: 'phone', label: '联系电话' },
    { key: 'address', label: '家庭地址' },
    { key: 'plate_no_1', label: '车牌号码' },
    { key: 'plate_no_2', label: '车牌号码2' }
];

function openMobileEditModal() {
    if (!mCurrentTeacherRaw || !mCurrentTeacherId) return;

    const role = (mCurrentUser && mCurrentUser.role) || '';
    const meTeacherId = mCurrentUser && mCurrentUser.teacher_id;
    if (role === 'viewer') {
        mShowToast('浏览账号无编辑权限', 'warning');
        return;
    }
    if (role === 'teacher' && meTeacherId !== Number(mCurrentTeacherId)) {
        mShowToast('无权限编辑其他教师信息', 'warning');
        return;
    }

    const values = mCurrentTeacherNormalized || {};
    const form = MOBILE_EDIT_FIELDS.map((f) => {
        const v = values[f.key] || '';
        if (f.type === 'select') {
            return `
                <div class="form-group">
                    <label class="form-label">${f.label}</label>
                    <select class="form-control" id="m-edit-${f.key}">
                        <option value="">请选择</option>
                        ${f.options.map((opt) => `<option value="${opt}" ${opt === v ? 'selected' : ''}>${opt}</option>`).join('')}
                    </select>
                </div>
            `;
        }
        return `
            <div class="form-group">
                <label class="form-label">${f.label}</label>
                <input class="form-control" id="m-edit-${f.key}" value="${esc(v)}">
            </div>
        `;
    }).join('');

    const html = `
        <div class="modal-overlay" id="m-edit-modal" onclick="if(event.target===this)this.remove()">
            <div class="modal" style="max-width: 94vw;">
                <div class="modal-header">
                    <h3>编辑教师信息</h3>
                    <button class="modal-close" onclick="document.getElementById('m-edit-modal')?.remove()">×</button>
                </div>
                <div class="modal-body" style="max-height: 68vh; overflow:auto;">
                    <div style="display:grid; grid-template-columns:1fr; gap:10px;">${form}</div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline" onclick="document.getElementById('m-edit-modal')?.remove()">取消</button>
                    <button class="btn btn-primary" onclick="saveMobileTeacher()">保存</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function saveMobileTeacher() {
    if (!mCurrentTeacherId) return;
    const payload = {};
    MOBILE_EDIT_FIELDS.forEach((f) => {
        const el = document.getElementById(`m-edit-${f.key}`);
        if (el) payload[f.key] = (el.value || '').trim();
    });

    try {
        const resp = await mApi(`/api/teachers/${mCurrentTeacherId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        if (resp && resp.pending) {
            mShowToast('已提交管理员审核', 'info');
        } else {
            mShowToast('保存成功', 'success');
        }
        document.getElementById('m-edit-modal')?.remove();
        await loadMobileDetail();
    } catch (e) {
        mShowToast(e.message || '保存失败', 'error');
    }
}

async function loadMobileDetail() {
    mCurrentUser = await mRequireAuth();
    const id = new URLSearchParams(window.location.search).get('id');
    const root = document.getElementById('m-detail');
    if (!id) {
        root.innerHTML = '<div class="empty-state"><h3>缺少教师ID</h3></div>';
        return;
    }
    try {
        const raw = await mApi(`/api/teachers/${id}`);
        const schema = window.TeacherSchema;
        if (!schema) throw new Error('字段配置未加载');
        const p = schema.normalizeTeacher(raw);
        mCurrentTeacherRaw = raw;
        mCurrentTeacherNormalized = p;
        mCurrentTeacherId = id;
        document.getElementById('m-name').textContent = '教师详情';
        const cards = schema.SECTIONS.map((s, idx) => renderSectionCard(p, s, idx + 1, schema)).join('');
        root.innerHTML = `
            ${renderHero(p)}
            <div class="m-cyber-grid">${cards}</div>
            ${renderBottomActions(id)}
        `;
    } catch (e) {
        root.innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${esc(e.message)}</p></div>`;
    }
}

document.addEventListener('DOMContentLoaded', loadMobileDetail);
