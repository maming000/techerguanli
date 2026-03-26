const MOBILE_DETAIL_GROUPS = [
    {
        title: '身份信息',
        fields: [
            ['id', '序号'],
            ['name', '姓名'],
            ['gender', '性别'],
            ['id_card', '身份证号'],
            ['birth_date', '出生日期'],
            ['age', '年龄'],
            ['ethnicity', '民族'],
            ['native_place', '籍贯']
        ]
    },
    {
        title: '联系方式',
        fields: [
            ['mobile', '手机'],
            ['phone', '联系电话'],
            ['short_phone', '小号'],
            ['address', '家庭住址'],
            ['email', '邮箱']
        ]
    },
    {
        title: '任职信息',
        fields: [
            ['graduate_school', '毕业院校'],
            ['education', '学历'],
            ['political_status', '政治面貌'],
            ['title', '职称'],
            ['position', '职务'],
            ['subject', '任教学科'],
            ['hire_date', '入职日期'],
            ['employee_id', '工号']
        ]
    },
    {
        title: '系统信息',
        fields: [
            ['account_username', '教师账号'],
            ['created_at', '创建时间'],
            ['updated_at', '更新时间']
        ]
    }
];

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function hasValue(value) {
    return value !== null && value !== undefined && value !== '';
}

function formatValue(value) {
    if (!hasValue(value)) return '-';
    if (Array.isArray(value)) return value.length ? value.join('、') : '-';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
}

function mField(label, value) {
    return `<div class="detail-item"><span class="detail-label">${escapeHtml(label)}</span><span class="detail-value">${escapeHtml(formatValue(value))}</span></div>`;
}

function mSection(title, fieldsHtml) {
    return `<section class="detail-section-card mb-16"><h3 class="detail-section-title">${escapeHtml(title)}</h3><div class="detail-grid">${fieldsHtml}</div></section>`;
}

async function loadMobileDetail() {
    await mRequireAuth();
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) {
        document.getElementById('m-detail').innerHTML = '<div class="empty-state"><h3>缺少教师ID</h3></div>';
        return;
    }

    try {
        const t = await mApi(`/api/teachers/${id}`);
        document.getElementById('m-name').textContent = t.name || '教师详情';
        const renderedKeys = new Set();
        let html = '';

        MOBILE_DETAIL_GROUPS.forEach((group) => {
            let fieldsHtml = '';
            group.fields.forEach(([key, label]) => {
                renderedKeys.add(key);
                fieldsHtml += mField(label, t[key]);
            });
            html += mSection(group.title, fieldsHtml);
        });

        if (Array.isArray(t.tags)) {
            renderedKeys.add('tags');
            html += mSection('标签', mField('标签', t.tags));
        }

        const topLevelExtraKeys = Object.keys(t).filter((key) => (
            key !== 'extra_fields' &&
            !renderedKeys.has(key) &&
            typeof t[key] !== 'object'
        ));
        if (topLevelExtraKeys.length) {
            let fieldsHtml = '';
            topLevelExtraKeys.forEach((key) => {
                fieldsHtml += mField(key, t[key]);
            });
            html += mSection('其他字段', fieldsHtml);
        }

        const extraFields = t.extra_fields || {};
        const extraKeys = Object.keys(extraFields);
        if (extraKeys.length) {
            let fieldsHtml = '';
            extraKeys.forEach((key) => {
                let label = key;
                if (key === '__profile_avatar') label = '头像';
                if (key === '__profile_cover_color') label = '封面主题色';
                fieldsHtml += mField(label, extraFields[key]);
            });
            html += mSection('扩展信息', fieldsHtml);
        }

        document.getElementById('m-detail').innerHTML = html;
    } catch (e) {
        document.getElementById('m-detail').innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${e.message}</p></div>`;
    }
}

document.addEventListener('DOMContentLoaded', loadMobileDetail);
