function qs(id) {
    return document.getElementById(id);
}

function normalizeIdCard(idCard) {
    return String(idCard || '').trim().replace(/\s+/g, '').toUpperCase();
}

function isValidBirthDateInId(idCard) {
    if (!/^\d{17}[\dX]$/.test(idCard)) return false;
    const year = Number(idCard.slice(6, 10));
    const month = Number(idCard.slice(10, 12));
    const day = Number(idCard.slice(12, 14));
    const d = new Date(year, month - 1, day);
    return d.getFullYear() === year && d.getMonth() === month - 1 && d.getDate() === day;
}

function validateChineseIdCard(idCard) {
    const v = normalizeIdCard(idCard);
    if (!v) return { ok: false, message: '请输入身份证号' };
    if (!/^\d{17}[\dX]$/.test(v)) return { ok: false, message: '身份证号格式应为18位，最后一位可为X' };
    if (!isValidBirthDateInId(v)) return { ok: false, message: '身份证号中的出生日期无效' };
    const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
    const checkCodes = '10X98765432';
    let sum = 0;
    for (let i = 0; i < 17; i += 1) sum += Number(v[i]) * weights[i];
    const expected = checkCodes[sum % 11];
    if (v[17] !== expected) return { ok: false, message: '身份证号校验位不正确' };
    return { ok: true, normalized: v, message: '身份证号校验通过' };
}

function extractBirthGenderFromId(idCard) {
    const v = normalizeIdCard(idCard);
    if (!/^\d{17}[\dX]$/.test(v)) return null;
    const birth = `${v.slice(6, 10)}-${v.slice(10, 12)}-${v.slice(12, 14)}`;
    const gender = Number(v[16]) % 2 === 1 ? '男' : '女';
    return { birth, gender };
}

function applyDerivedFromId(idCard) {
    const ret = extractBirthGenderFromId(idCard);
    const birthInput = qs('onboard-birth-date');
    const genderSelect = document.querySelector('select[name="gender"]');
    const derivedHint = qs('id-card-derived-hint');
    if (!ret) {
        if (birthInput) birthInput.value = '';
        if (derivedHint) derivedHint.textContent = '';
        return;
    }
    if (birthInput) birthInput.value = ret.birth;
    if (genderSelect) genderSelect.value = ret.gender;
    if (derivedHint) {
        derivedHint.textContent = `已自动提取：出生日期 ${ret.birth}，性别 ${ret.gender}`;
        derivedHint.style.color = 'var(--info)';
    }
}

function updateIdCardHint(inputEl) {
    const hint = qs('id-card-hint');
    if (!inputEl || !hint) return true;
    const raw = inputEl.value || '';
    if (!raw.trim()) {
        hint.textContent = '';
        inputEl.style.borderColor = '';
        applyDerivedFromId('');
        return false;
    }
    const ret = validateChineseIdCard(raw);
    if (ret.ok) {
        hint.textContent = ret.message;
        hint.style.color = 'var(--success)';
        inputEl.style.borderColor = 'var(--success)';
        inputEl.value = ret.normalized;
        applyDerivedFromId(ret.normalized);
        return true;
    }
    hint.textContent = ret.message;
    hint.style.color = 'var(--danger)';
    inputEl.style.borderColor = 'var(--danger)';
    applyDerivedFromId('');
    return false;
}

function showOnboardResult(ok, payload) {
    const box = qs('onboard-result');
    if (!box) return;
    box.classList.remove('hidden');
    if (!ok) {
        box.innerHTML = `
            <div class="card-body">
                <h3 style="color: var(--danger);">提交失败</h3>
                <p class="text-muted" style="margin-top:8px;">${payload || '请稍后重试'}</p>
            </div>`;
        return;
    }
    box.innerHTML = `
        <div class="card-body">
            <h2 style="margin-bottom:8px;">提交成功</h2>
            <p class="text-muted">请保存以下账号信息，并尽快登录后修改密码。</p>
            <div class="detail-grid mt-16">
                <div class="detail-item">
                    <span class="detail-label">教师ID</span>
                    <span class="detail-value">${payload.teacher_id}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">账号</span>
                    <span class="detail-value">${payload.username}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">初始密码</span>
                    <span class="detail-value">${payload.password}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">登录地址</span>
                    <span class="detail-value"><a href="/login">点击前往登录</a></span>
                </div>
            </div>
        </div>`;
}

async function submitOnboard(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const submitBtn = form.querySelector('button[type="submit"]');
    const code = new URLSearchParams(window.location.search).get('code') || '';
    if (!code) {
        showOnboardResult(false, '登记链接缺少口令参数，请联系管理员重新发送链接');
        return;
    }

    const fd = new FormData(form);
    const payload = {};
    for (const [key, value] of fd.entries()) {
        const val = String(value || '').trim();
        if (val) payload[key] = val;
    }

    const idInput = form.querySelector('input[name="id_card"]');
    const idOk = updateIdCardHint(idInput);
    if (!idOk) {
        showOnboardResult(false, '身份证号校验未通过，请检查后再提交');
        return;
    }
    payload.id_card = normalizeIdCard(payload.id_card);

    if (!payload.name) {
        showOnboardResult(false, '姓名为必填项');
        return;
    }
    const required = [
        ['mobile', '手机号'],
        ['id_card', '身份证号'],
        ['subject', '任教学科'],
        ['education', '学历'],
        ['graduate_school', '毕业院校'],
        ['major', '专业'],
        ['political_status', '政治面貌'],
        ['address', '家庭住址'],
        ['ethnicity', '民族'],
        ['native_place', '籍贯'],
        ['email', '电子邮件'],
    ];
    const missing = required.filter(([k]) => !payload[k]).map(([, label]) => label);
    if (missing.length) {
        showOnboardResult(false, `以下字段为必填：${missing.join('、')}`);
        return;
    }

    submitBtn.disabled = true;
    const oldText = submitBtn.textContent;
    submitBtn.textContent = '提交中...';
    try {
        const resp = await fetch(`/api/teachers/public/onboard?code=${encodeURIComponent(code)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            showOnboardResult(false, data.detail || `HTTP ${resp.status}`);
            return;
        }
        showOnboardResult(true, data);
    } catch (err) {
        showOnboardResult(false, err.message || '网络异常');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = oldText;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const form = qs('onboard-form');
    if (form) {
        form.addEventListener('submit', submitOnboard);
        const idInput = form.querySelector('input[name="id_card"]');
        if (idInput) {
            idInput.addEventListener('input', () => {
                const raw = idInput.value || '';
                if (raw.trim().length < 18) {
                    const hint = qs('id-card-hint');
                    if (hint) {
                        hint.textContent = `已输入 ${normalizeIdCard(raw).length}/18 位`;
                        hint.style.color = 'var(--text-muted)';
                    }
                    idInput.style.borderColor = '';
                    applyDerivedFromId('');
                    return;
                }
                updateIdCardHint(idInput);
            });
            idInput.addEventListener('blur', () => updateIdCardHint(idInput));
        }
    }
});
