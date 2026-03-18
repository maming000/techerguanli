/**
 * 教师详情页逻辑
 */

let currentTeacher = null;

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (id) {
        loadTeacher(id);
    } else {
        document.getElementById('detail-content').innerHTML =
            '<div class="empty-state"><div class="empty-icon">🔍</div><h3>未指定教师</h3><p>请从首页选择一个教师查看详情</p></div>';
    }
});

async function loadTeacher(id) {
    try {
        currentTeacher = await api(`/api/teachers/${id}`);
        renderDetail(currentTeacher);
        loadLogs(id);
    } catch (e) {
        document.getElementById('detail-content').innerHTML =
            `<div class="empty-state"><div class="empty-icon">❌</div><h3>加载失败</h3><p>${e.message}</p></div>`;
    }
}

function renderDetail(t) {
    const fieldMap = {
        name: '姓名', gender: '性别', id_card: '身份证号',
        phone: '联系电话', mobile: '手机', short_phone: '小号',
        birth_date: '出生日期', age: '年龄', graduate_school: '毕业院校',
        education: '学历', political_status: '政治面貌', ethnicity: '民族',
        native_place: '籍贯', address: '家庭住址', email: '邮箱',
        title: '职称', position: '职务', subject: '任教学科',
        hire_date: '入职日期', employee_id: '工号'
    };

    // 基本信息
    let detailHtml = '<div class="detail-grid">';
    for (const [key, label] of Object.entries(fieldMap)) {
        const val = t[key];
        detailHtml += `
            <div class="detail-item">
                <span class="detail-label">${label}</span>
                <span class="detail-value">${val || '-'}</span>
            </div>`;
    }
    detailHtml += '</div>';

    // 扩展字段
    if (t.extra_fields && Object.keys(t.extra_fields).length > 0) {
        detailHtml += '<h3 style="margin-top: 24px; margin-bottom: 12px;">扩展信息</h3><div class="detail-grid">';
        for (const [key, val] of Object.entries(t.extra_fields)) {
            detailHtml += `
                <div class="detail-item">
                    <span class="detail-label">${key}</span>
                    <span class="detail-value">${val || '-'}</span>
                </div>`;
        }
        detailHtml += '</div>';
    }

    document.getElementById('detail-content').innerHTML = detailHtml;

    // 标签
    renderTagsSection(t);

    // 更新页面标题
    document.getElementById('teacher-name').textContent = t.name || '未知教师';
    document.getElementById('teacher-meta').textContent =
        `ID: ${t.id} | 创建: ${formatDate(t.created_at)} | 更新: ${formatDate(t.updated_at)}`;
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
        await api(`/api/teachers/${currentTeacher.id}/tags?tag=${encodeURIComponent(tag)}`, { method: 'DELETE' });
        showToast('标签已删除', 'success');
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
        await api(`/api/teachers/${currentTeacher.id}/tags?tag=${encodeURIComponent(tag)}`, { method: 'POST' });
        showToast(`已添加标签: ${tag}`, 'success');
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
    if (t.extra_fields && Object.keys(t.extra_fields).length > 0) {
        formHtml += '<h4 style="margin: 16px 0 8px;">扩展字段</h4><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">';
        for (const [key, val] of Object.entries(t.extra_fields)) {
            formHtml += `
                <div class="form-group">
                    <label class="form-label">${key}</label>
                    <input type="text" class="form-control" data-extra="${key}" value="${val || ''}">
                </div>`;
        }
        formHtml += '</div>';
    }

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

async function saveTeacher() {
    if (!currentTeacher) return;
    if (!confirm(`确定要修改教师 "${currentTeacher.name || '未知教师'}" 的信息吗？`)) return;

    const fields = ['name', 'gender', 'id_card', 'phone', 'mobile', 'short_phone',
        'graduate_school', 'education', 'political_status', 'ethnicity',
        'native_place', 'address', 'email', 'title', 'position', 'subject',
        'hire_date', 'employee_id'];

    const data = {};
    for (const f of fields) {
        const el = document.getElementById(`edit-${f}`);
        if (el && el.value) data[f] = el.value;
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
        await api(`/api/teachers/${currentTeacher.id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        showToast('保存成功', 'success');
        document.querySelector('.modal-overlay')?.remove();
        await loadTeacher(currentTeacher.id);
    } catch (e) { }
}

async function deleteTeacher() {
    if (!currentTeacher) return;
    if (!confirm(`确定要删除教师 "${currentTeacher.name}" 吗？此操作不可恢复。`)) return;

    try {
        await api(`/api/teachers/${currentTeacher.id}`, { method: 'DELETE' });
        showToast('已删除', 'success');
        setTimeout(() => window.location.href = '/', 500);
    } catch (e) { }
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

    let html = '<div class="table-wrapper"><table><thead><tr><th>操作</th><th>字段</th><th>旧值</th><th>新值</th><th>时间</th></tr></thead><tbody>';
    for (const log of logs) {
        html += `<tr>
            <td><span class="tag tag-primary">${log.action}</span></td>
            <td>${log.field_name || '-'}</td>
            <td class="text-muted">${log.old_value || '-'}</td>
            <td>${log.new_value || '-'}</td>
            <td class="text-muted">${formatDate(log.created_at)}</td>
        </tr>`;
    }
    html += '</tbody></table></div>';
    container.innerHTML = html;
}
