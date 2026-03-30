let adminChart = null;

function toFixed1(v) {
    return Number(v || 0).toFixed(1);
}

function renderTeacherHistory(rows) {
    const tbody = document.getElementById('assessment-history-tbody');
    if (!rows || rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">暂无记录</td></tr>`;
        return;
    }

    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${formatDate(row.created_at)}</td>
            <td>${toFixed1(row.scores.openness)}</td>
            <td>${toFixed1(row.scores.conscientiousness)}</td>
            <td>${toFixed1(row.scores.extraversion)}</td>
            <td>${toFixed1(row.scores.agreeableness)}</td>
            <td>${toFixed1(row.scores.neuroticism)}</td>
            <td>${Math.round((row.scores.openness + row.scores.conscientiousness + row.scores.extraversion + row.scores.agreeableness + row.scores.neuroticism) / 5)}</td>
        </tr>
    `).join('');
}

function renderAdminStats(data) {
    const wrap = document.getElementById('assessment-admin-wrap');
    wrap.style.display = '';
    document.getElementById('assessment-history-wrap').style.display = 'none';

    document.getElementById('assessment-admin-total').textContent = data.total_tests || 0;
    document.getElementById('assessment-admin-avg').innerHTML = TRAIT_KEYS.map((k) => `
        <div class="assessment-score-card">
            <div class="assessment-score-head"><span>${TRAIT_LABELS[k]}</span><strong>${toFixed1(data.averages[k])}</strong></div>
            <div class="progress-bar"><div class="progress-fill" style="width:${Number(data.averages[k] || 0)}%"></div></div>
        </div>
    `).join('');

    const dom = document.getElementById('assessment-admin-dist');
    if (adminChart) adminChart.dispose();
    adminChart = echarts.init(dom);

    const bins = ['0-20', '21-40', '41-60', '61-80', '81-100'];
    adminChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: TRAIT_KEYS.map((k) => TRAIT_LABELS[k]) },
        xAxis: { type: 'category', data: bins },
        yAxis: { type: 'value', minInterval: 1 },
        series: TRAIT_KEYS.map((k) => ({
            name: TRAIT_LABELS[k],
            type: 'bar',
            data: bins.map((b) => Number((data.distributions[k] || {})[b] || 0))
        }))
    });
}

function renderAdminRecords(rows) {
    const tbody = document.getElementById('assessment-admin-records-tbody');
    if (!tbody) return;
    if (!rows || rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">暂无测评记录</td></tr>`;
        return;
    }
    tbody.innerHTML = rows.map((r) => {
        const detail = (r.answer_items || []).map((it) =>
            `<div class="assessment-answer-item"><span class="assessment-answer-q">${it.id}. ${it.text_zh || '-'}</span><span class="assessment-answer-v">选项：${it.answer}</span></div>`
        ).join('');
        return `
            <tr>
                <td>${r.username || '-'}</td>
                <td>${r.user_id || '-'}</td>
                <td>${formatDate(r.created_at)}</td>
                <td>${r.client_ip || '-'}</td>
                <td>
                    O:${toFixed1(r.scores.openness)} / C:${toFixed1(r.scores.conscientiousness)} / E:${toFixed1(r.scores.extraversion)} / A:${toFixed1(r.scores.agreeableness)} / N:${toFixed1(r.scores.neuroticism)}
                </td>
                <td><details><summary>查看30题作答</summary><div class="assessment-answer-list">${detail}</div></details></td>
            </tr>
        `;
    }).join('');
}

document.addEventListener('DOMContentLoaded', async () => {
    const user = await getCurrentUser();
    if (!user) return;

    if (user.role === 'teacher') {
        try {
            const rows = await api('/api/assessment/history');
            renderTeacherHistory(rows);
        } catch (e) {
            document.getElementById('assessment-history-tbody').innerHTML = `<tr><td colspan="7" class="text-center text-danger">${e.message}</td></tr>`;
        }
        return;
    }

    if (user.role === 'admin') {
        try {
            const [data, records] = await Promise.all([
                api('/api/assessment/stats'),
                api('/api/assessment/admin-records?limit=200')
            ]);
            renderAdminStats(data);
            renderAdminRecords(records);
        } catch (e) {
            document.getElementById('assessment-admin-wrap').innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${e.message}</p></div>`;
        }
        return;
    }

    document.getElementById('assessment-history-wrap').innerHTML = `<div class="empty-state"><h3>无权限</h3><p>当前账号不支持访问该模块。</p></div>`;
});

window.addEventListener('resize', () => {
    if (adminChart) adminChart.resize();
});
