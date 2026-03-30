/* global Vue, api, showToast, getCurrentUser, formatDate */

(function () {
    const { createApp, ref, computed, onMounted } = Vue;

    createApp({
        setup() {
            const teachers = ref([]);
            const loading = ref(false);
            const loadError = ref('');
            const total = ref(0);
            const page = ref(1);
            const pageSize = ref(20);
            const totalPages = ref(1);
            const selectedIds = ref([]);
            const activeFilters = ref({});

            const selectedCount = computed(() => selectedIds.value.length);
            const allChecked = computed(() => {
                if (!teachers.value.length) return false;
                const set = new Set(selectedIds.value);
                return teachers.value.every((t) => set.has(t.id));
            });

            function setSelected(id, checked) {
                const set = new Set(selectedIds.value);
                if (checked) set.add(id);
                else set.delete(id);
                selectedIds.value = Array.from(set);
            }

            function toggleSelectAll(checked) {
                if (!checked) {
                    selectedIds.value = [];
                    return;
                }
                selectedIds.value = teachers.value.map((t) => t.id);
            }

            function buildTeacherQuery(targetPage = 1) {
                const params = new URLSearchParams();
                params.set('page', String(targetPage));
                params.set('page_size', String(pageSize.value));

                const keyword = document.getElementById('search-input')?.value?.trim() || '';
                if (keyword) params.set('keyword', keyword);

                if (activeFilters.value.gender) params.set('gender', activeFilters.value.gender);
                if (activeFilters.value.political_status) params.set('political_status', activeFilters.value.political_status);
                if (activeFilters.value.max_age !== undefined) params.set('max_age', String(activeFilters.value.max_age));
                if (activeFilters.value.min_age !== undefined) params.set('min_age', String(activeFilters.value.min_age));

                const sortBy = document.getElementById('sort-by')?.value;
                const sortOrder = document.getElementById('sort-order')?.value;
                if (sortBy) {
                    params.set('sort_by', sortBy);
                    params.set('sort_order', sortOrder || 'asc');
                }

                const advanced = [
                    ['filter-gender', 'gender'],
                    ['filter-phone', 'phone'],
                    ['filter-birth-date', 'birth_date'],
                    ['filter-education', 'education'],
                    ['filter-title', 'title'],
                    ['filter-original-unit', 'original_unit'],
                    ['filter-public-service-time', 'public_service_time'],
                    ['filter-car-plate', 'car_plate'],
                    ['filter-graduate-school', 'graduate_school'],
                    ['filter-ethnicity', 'ethnicity'],
                    ['filter-address', 'address'],
                    ['filter-subject', 'subject'],
                    ['filter-hire-date', 'hire_date'],
                    ['filter-min-age', 'min_age'],
                    ['filter-max-age', 'max_age'],
                ];

                advanced.forEach(([inputId, queryKey]) => {
                    const value = document.getElementById(inputId)?.value;
                    if (!value) return;
                    if (queryKey === 'gender' && activeFilters.value.gender) return;
                    params.set(queryKey, value);
                });

                return params;
            }

            async function loadTeachers(targetPage = 1) {
                loading.value = true;
                loadError.value = '';
                page.value = targetPage;
                try {
                    const params = buildTeacherQuery(targetPage);
                    const result = await api(`/api/teachers/?${params.toString()}`);
                    teachers.value = result.data || [];
                    total.value = result.total || 0;
                    totalPages.value = result.total_pages || 1;
                    selectedIds.value = [];
                } catch (e) {
                    teachers.value = [];
                    total.value = 0;
                    totalPages.value = 1;
                    loadError.value = e.message || '加载失败';
                } finally {
                    loading.value = false;
                }
            }

            function changePageSize() {
                const size = parseInt(document.getElementById('page-size')?.value || '20', 10);
                if (!isNaN(size)) pageSize.value = size;
                loadTeachers(1);
            }

            function toggleFilter(type) {
                const btn = document.querySelector(`.filter-btn[data-filter="${type}"]`);
                if (!btn) return;
                const isActive = btn.classList.contains('active');

                document.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'));
                activeFilters.value = {};

                if (!isActive) {
                    btn.classList.add('active');
                    switch (type) {
                        case 'young':
                            activeFilters.value.max_age = 30;
                            break;
                        case 'male':
                            activeFilters.value.gender = '男';
                            break;
                        case 'female':
                            activeFilters.value.gender = '女';
                            break;
                        case 'party':
                            activeFilters.value.political_status = '中共党员';
                            break;
                        default:
                            if (type.startsWith('age-')) {
                                const base = parseInt(type.split('-')[1], 10);
                                if (!isNaN(base)) {
                                    activeFilters.value.min_age = base;
                                    activeFilters.value.max_age = base + 4;
                                }
                            }
                            break;
                    }
                }

                loadTeachers(1);
            }

            function resetFilters() {
                document.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'));
                [
                    'search-input', 'filter-gender', 'filter-phone', 'filter-birth-date', 'filter-education',
                    'filter-title', 'filter-original-unit', 'filter-public-service-time', 'filter-car-plate',
                    'filter-graduate-school', 'filter-ethnicity', 'filter-address', 'filter-subject',
                    'filter-hire-date', 'filter-min-age', 'filter-max-age', 'sort-by'
                ].forEach((id) => {
                    const el = document.getElementById(id);
                    if (el) el.value = '';
                });
                const sortOrder = document.getElementById('sort-order');
                if (sortOrder) sortOrder.value = 'asc';
                activeFilters.value = {};
                loadTeachers(1);
            }

            function teacherPhone(t) {
                return t.mobile || t.phone || '-';
            }

            async function batchDelete() {
                if (!selectedCount.value) return;
                if (!confirm(`确定要删除选中的 ${selectedCount.value} 名教师吗？此操作不可恢复。`)) return;
                let deleted = 0;
                for (const id of selectedIds.value) {
                    try {
                        await api(`/api/teachers/${id}`, { method: 'DELETE' });
                        deleted += 1;
                    } catch (_e) {}
                }
                showToast(`已删除 ${deleted} 名教师`, 'success');
                selectedIds.value = [];
                await loadTeachers(1);
                await loadQuickStats();
            }

            async function loadQuickStats() {
                const user = await getCurrentUser();
                if (!user || user.role !== 'admin') return;
                try {
                    const stats = await api('/api/stats/');
                    const totalEl = document.getElementById('total-count');
                    const maleEl = document.getElementById('male-count');
                    const femaleEl = document.getElementById('female-count');
                    const youngEl = document.getElementById('young-count');
                    if (totalEl) totalEl.textContent = stats.total_teachers;
                    if (maleEl) maleEl.textContent = stats.gender_stats['男'] || 0;
                    if (femaleEl) femaleEl.textContent = stats.gender_stats['女'] || 0;
                    let young = 0;
                    for (const [range, count] of Object.entries(stats.age_stats || {})) {
                        if (range.includes('25岁以下') || range.includes('25-30')) young += count;
                    }
                    if (youngEl) youngEl.textContent = String(young);
                } catch (_e) {}
            }

            async function loadTitleOptions() {
                const select = document.getElementById('filter-title');
                if (!select) return;
                const user = await getCurrentUser();
                if (!user || user.role !== 'admin') return;
                try {
                    const titles = await api('/api/stats/titles');
                    const current = select.value || '';
                    select.innerHTML = '<option value="">全部</option>';
                    (titles || []).forEach((t) => {
                        const opt = document.createElement('option');
                        opt.value = t;
                        opt.textContent = t;
                        if (t === current) opt.selected = true;
                        select.appendChild(opt);
                    });
                } catch (_e) {}
            }

            async function loadPendingApprovals() {
                const user = await getCurrentUser();
                const card = document.getElementById('approval-card');
                const list = document.getElementById('approval-list');
                if (!card || !list) return;
                if (!user || user.role !== 'admin') {
                    card.style.display = 'none';
                    return;
                }
                card.style.display = '';
                list.innerHTML = '<div class="loading"><div class="spinner"></div> 加载中...</div>';
                try {
                    const rows = await api('/api/teachers/audit/change-requests?status=pending&limit=50');
                    if (!rows || rows.length === 0) {
                        list.innerHTML = '<p class="text-muted">暂无待审核请求</p>';
                        return;
                    }
                    let html = '<div class="table-wrapper"><table><thead><tr><th>ID</th><th>教师</th><th>发起人</th><th>动作</th><th>时间</th><th>操作</th></tr></thead><tbody>';
                    for (const r of rows) {
                        html += `<tr>
                            <td>${r.id}</td>
                            <td>${r.teacher_name || ('#' + r.teacher_id)}</td>
                            <td>${r.requester_username || ('#' + r.requester_user_id)}</td>
                            <td>${r.action}</td>
                            <td>${formatDate(r.created_at)}</td>
                            <td>
                                <div class="btn-group">
                                    <button class="btn btn-primary btn-sm" onclick="approveRequest(${r.id})">通过</button>
                                    <button class="btn btn-danger btn-sm" onclick="rejectRequest(${r.id})">驳回</button>
                                </div>
                            </td>
                        </tr>`;
                    }
                    html += '</tbody></table></div>';
                    list.innerHTML = html;
                } catch (e) {
                    list.innerHTML = `<p class="text-danger">加载审核请求失败：${e.message}</p>`;
                }
            }

            async function approveRequest(requestId) {
                if (!confirm('确认通过该请求并立即生效？')) return;
                try {
                    await api(`/api/teachers/audit/change-requests/${requestId}/approve`, { method: 'POST' });
                    showToast('已通过并生效', 'success');
                    await loadPendingApprovals();
                    await loadTeachers(page.value);
                } catch (_e) {}
            }

            async function rejectRequest(requestId) {
                const note = prompt('可选：请输入驳回原因') || '';
                try {
                    const token = localStorage.getItem('auth_token');
                    const form = new FormData();
                    form.append('note', note);
                    const resp = await fetch(`/api/teachers/audit/change-requests/${requestId}/reject`, {
                        method: 'POST',
                        body: form,
                        headers: token ? { Authorization: `Bearer ${token}` } : {}
                    });
                    if (!resp.ok) {
                        const err = await resp.json().catch(() => ({ detail: '驳回失败' }));
                        throw new Error(err.detail || '驳回失败');
                    }
                    showToast('已驳回', 'success');
                    await loadPendingApprovals();
                } catch (e) {
                    showToast(e.message || '驳回失败', 'error');
                }
            }

            async function exportExcel() {
                const params = buildTeacherQuery(page.value);
                params.delete('page');
                params.delete('page_size');
                try {
                    const token = localStorage.getItem('auth_token');
                    const resp = await fetch(`/api/export/excel?${params.toString()}`, {
                        headers: token ? { Authorization: `Bearer ${token}` } : {}
                    });
                    if (!resp.ok) throw new Error('导出失败');
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `教师数据_${new Date().toISOString().slice(0, 10)}.xlsx`;
                    a.click();
                    URL.revokeObjectURL(url);
                    showToast('导出成功', 'success');
                } catch (e) {
                    showToast(`导出失败: ${e.message}`, 'error');
                }
            }

            async function bulkCreateAccounts() {
                if (!confirm('将为所有尚未创建账号的教师批量生成账号，并导出 Excel，是否继续？')) return;
                try {
                    const token = localStorage.getItem('auth_token');
                    const resp = await fetch('/api/users/bulk-create-export', {
                        method: 'POST',
                        headers: token ? { Authorization: `Bearer ${token}` } : {}
                    });
                    if (!resp.ok) throw new Error('批量生成账号失败');
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `教师账号_批量生成_${new Date().toISOString().slice(0, 10)}.xlsx`;
                    a.click();
                    URL.revokeObjectURL(url);
                    showToast('账号已生成并导出', 'success');
                } catch (e) {
                    showToast(`批量生成账号失败: ${e.message}`, 'error');
                }
            }

            function goToPage(p) {
                if (p < 1 || p > totalPages.value || p === page.value) return;
                loadTeachers(p);
            }

            const pageNumbers = computed(() => {
                const start = Math.max(1, page.value - 2);
                const end = Math.min(totalPages.value, page.value + 2);
                const nums = [];
                for (let i = start; i <= end; i += 1) nums.push(i);
                return nums;
            });

            // 兼容旧的 onclick 入口
            window.searchTeachers = () => loadTeachers(1);
            window.changePageSize = changePageSize;
            window.toggleFilter = toggleFilter;
            window.resetFilters = resetFilters;
            window.exportExcel = exportExcel;
            window.bulkCreateAccounts = bulkCreateAccounts;
            window.loadPendingApprovals = loadPendingApprovals;
            window.approveRequest = approveRequest;
            window.rejectRequest = rejectRequest;
            window.batchDelete = batchDelete;

            onMounted(async () => {
                await loadTeachers(1);
                await loadQuickStats();
                await loadTitleOptions();
                await loadPendingApprovals();
            });

            return {
                teachers,
                loading,
                loadError,
                total,
                page,
                pageSize,
                totalPages,
                selectedIds,
                selectedCount,
                allChecked,
                pageNumbers,
                setSelected,
                toggleSelectAll,
                changePageSize,
                goToPage,
                teacherPhone,
                batchDelete,
                loadTeachers,
            };
        }
    }).mount('#index-app');
})();
