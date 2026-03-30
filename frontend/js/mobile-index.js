let mPage = 1;
let mPageSize = 10;
let mQuickFilter = '';

function mRenderPagination(page, totalPages) {
    const el = document.getElementById('m-pagination');
    if (!el) return;
    if (totalPages <= 1) {
        el.innerHTML = '';
        return;
    }
    el.innerHTML = `
        <div class="btn-group" style="justify-content:center;">
            <button class="btn btn-outline btn-sm" ${page <= 1 ? 'disabled' : ''} onclick="loadMobileTeachers(${page - 1})">上一页</button>
            <span class="text-muted" style="padding: 6px 10px;">${page}/${totalPages}</span>
            <button class="btn btn-outline btn-sm" ${page >= totalPages ? 'disabled' : ''} onclick="loadMobileTeachers(${page + 1})">下一页</button>
        </div>`;
}

function mCard(t) {
    return `
        <article class="card mb-12">
            <div class="card-body">
                <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
                    <a href="/m/detail?id=${t.id}" style="font-weight:700;">${t.name || '-'}</a>
                </div>
                <div class="mt-8 text-muted" style="font-size:13px;display:grid;grid-template-columns:1fr 1fr;gap:6px;">
                    <div>手机：${t.mobile || t.phone || '-'}</div>
                    <div>学科：${t.subject || '-'}</div>
                    <div>职称：${t.title || '-'}</div>
                    <div>学历：${t.education || '-'}</div>
                </div>
            </div>
        </article>`;
}

async function loadMobileTeachers(page = 1) {
    mPage = page;
    const list = document.getElementById('m-list');
    list.innerHTML = '<div class="loading"><div class="spinner"></div> 加载中...</div>';

    const kw = document.getElementById('m-keyword')?.value?.trim() || '';
    const params = new URLSearchParams({ page: String(page), page_size: String(mPageSize) });
    if (kw) params.set('keyword', kw);

    // 快捷筛选
    if (mQuickFilter === 'male') params.set('gender', '男');
    if (mQuickFilter === 'female') params.set('gender', '女');
    if (mQuickFilter === 'party') params.set('political_status', '中共党员');
    if (mQuickFilter === 'young') params.set('max_age', '30');

    // 高级筛选
    const gender = document.getElementById('m-gender')?.value || '';
    const phone = document.getElementById('m-phone')?.value?.trim() || '';
    const birthDate = document.getElementById('m-birth-date')?.value || '';
    const politicalStatus = document.getElementById('m-political-status')?.value?.trim() || '';
    const edu = document.getElementById('m-education')?.value || '';
    const title = document.getElementById('m-title')?.value?.trim() || '';
    const originalUnit = document.getElementById('m-original-unit')?.value?.trim() || '';
    const publicServiceTime = document.getElementById('m-public-service-time')?.value || '';
    const carPlate = document.getElementById('m-car-plate')?.value?.trim() || '';
    const graduateSchool = document.getElementById('m-graduate-school')?.value?.trim() || '';
    const ethnicity = document.getElementById('m-ethnicity')?.value?.trim() || '';
    const address = document.getElementById('m-address')?.value?.trim() || '';
    const subject = document.getElementById('m-subject')?.value?.trim() || '';
    const hireDate = document.getElementById('m-hire-date')?.value || '';
    const minAge = document.getElementById('m-min-age')?.value || '';
    const maxAge = document.getElementById('m-max-age')?.value || '';
    if (gender) params.set('gender', gender);
    if (phone) params.set('phone', phone);
    if (birthDate) params.set('birth_date', birthDate);
    if (politicalStatus) params.set('political_status', politicalStatus);
    if (edu) params.set('education', edu);
    if (title) params.set('title', title);
    if (originalUnit) params.set('original_unit', originalUnit);
    if (publicServiceTime) params.set('public_service_time', publicServiceTime);
    if (carPlate) params.set('car_plate', carPlate);
    if (graduateSchool) params.set('graduate_school', graduateSchool);
    if (ethnicity) params.set('ethnicity', ethnicity);
    if (address) params.set('address', address);
    if (subject) params.set('subject', subject);
    if (hireDate) params.set('hire_date', hireDate);
    if (minAge) params.set('min_age', minAge);
    if (maxAge) params.set('max_age', maxAge);

    try {
        const res = await mApi(`/api/teachers/?${params.toString()}`);
        if (!res.data || res.data.length === 0) {
            list.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><h3>暂无数据</h3></div>';
            mRenderPagination(1, 1);
            return;
        }
        list.innerHTML = res.data.map(mCard).join('');
        mRenderPagination(res.page, res.total_pages);
    } catch (e) {
        list.innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${e.message}</p></div>`;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await mRequireAuth();
    loadMobileTeachers(1);
});

function toggleMobileQuickFilter(type) {
    mQuickFilter = (mQuickFilter === type) ? '' : type;
    document.querySelectorAll('#m-quick-filters [data-qf]').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.qf === mQuickFilter);
    });
    loadMobileTeachers(1);
}

function toggleMobileAdvancedFilters() {
    const wrap = document.getElementById('m-advanced-filters');
    if (!wrap) return;
    wrap.classList.toggle('hidden');
}

function resetMobileFilters() {
    mQuickFilter = '';
    document.getElementById('m-keyword').value = '';
    if (document.getElementById('m-gender')) document.getElementById('m-gender').value = '';
    if (document.getElementById('m-phone')) document.getElementById('m-phone').value = '';
    if (document.getElementById('m-birth-date')) document.getElementById('m-birth-date').value = '';
    if (document.getElementById('m-political-status')) document.getElementById('m-political-status').value = '';
    if (document.getElementById('m-education')) document.getElementById('m-education').value = '';
    if (document.getElementById('m-title')) document.getElementById('m-title').value = '';
    if (document.getElementById('m-original-unit')) document.getElementById('m-original-unit').value = '';
    if (document.getElementById('m-public-service-time')) document.getElementById('m-public-service-time').value = '';
    if (document.getElementById('m-car-plate')) document.getElementById('m-car-plate').value = '';
    if (document.getElementById('m-graduate-school')) document.getElementById('m-graduate-school').value = '';
    if (document.getElementById('m-ethnicity')) document.getElementById('m-ethnicity').value = '';
    if (document.getElementById('m-address')) document.getElementById('m-address').value = '';
    if (document.getElementById('m-subject')) document.getElementById('m-subject').value = '';
    if (document.getElementById('m-hire-date')) document.getElementById('m-hire-date').value = '';
    if (document.getElementById('m-min-age')) document.getElementById('m-min-age').value = '';
    if (document.getElementById('m-max-age')) document.getElementById('m-max-age').value = '';
    document.querySelectorAll('#m-quick-filters [data-qf]').forEach((btn) => btn.classList.remove('active'));
    loadMobileTeachers(1);
}
