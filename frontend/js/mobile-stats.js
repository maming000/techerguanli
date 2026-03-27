const mCharts = {};

async function loadMobileStats() {
    await mRequireAuth();
    const wrap = document.getElementById('m-stats-grid');
    wrap.innerHTML = '<div class="loading"><div class="spinner"></div> 加载中...</div>';

    try {
        const [s, adv, tags] = await Promise.all([
            mApi('/api/stats/'),
            mApi('/api/stats/advanced'),
            mApi('/api/stats/tags')
        ]);

        renderMobileOverview(s, adv);
        renderMobileGenderChart(s.gender_stats || {});
        renderMobileAgeChart(s.age_stats || {});
        renderMobileSubjectChart(adv.subject_stats || {});
        renderMobileWorkYearsChart(adv.work_years_stats || {});
        renderMobileTitleRank(adv.title_top || []);
        renderMobileTags(tags || {});
    } catch (e) {
        wrap.innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${e.message}</p></div>`;
    }
}

function renderMobileOverview(s, adv) {
    const wrap = document.getElementById('m-stats-grid');
    const total = Number(s.total_teachers || 0);
    const male = Number(s.gender_stats?.['男'] || 0);
    const female = Number(s.gender_stats?.['女'] || 0);
    const subjectCount = Number(adv.subject_count || 0);
    const under35 = Number(adv.under_35_count || 0);
    const senior = Number(adv.senior_title_count || 0);
    const party = Number(adv.party_member_count || 0);
    const partyRate = total > 0 ? `${Math.round((party / total) * 100)}%` : '-';

    wrap.innerHTML = `
        <div class="stat-card"><div class="stat-icon blue">👥</div><div class="stat-info"><h3>${total}</h3><p>教师总数</p></div></div>
        <div class="stat-card"><div class="stat-icon green">👨</div><div class="stat-info"><h3>${male}</h3><p>男教师</p></div></div>
        <div class="stat-card"><div class="stat-icon orange">👩</div><div class="stat-info"><h3>${female}</h3><p>女教师</p></div></div>
        <div class="stat-card"><div class="stat-icon purple">🧭</div><div class="stat-info"><h3>${subjectCount}</h3><p>学科数</p></div></div>
        <div class="stat-card"><div class="stat-icon indigo">🎯</div><div class="stat-info"><h3>${under35}</h3><p>35岁以下</p></div></div>
        <div class="stat-card"><div class="stat-icon cyan">🏅</div><div class="stat-info"><h3>${senior}</h3><p>高级职称</p></div></div>
        <div class="stat-card"><div class="stat-icon pink">🧩</div><div class="stat-info"><h3>${partyRate}</h3><p>党员占比</p></div></div>
    `;
}

function drawChart(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    if (mCharts[id]) mCharts[id].destroy();
    mCharts[id] = new Chart(canvas.getContext('2d'), config);
}

function renderMobileGenderChart(data) {
    drawChart('m-gender-chart', {
        type: 'doughnut',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: ['#2563eb', '#ec4899', '#94a3b8'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '62%',
            plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } } }
        }
    });
}

function renderMobileAgeChart(data) {
    const order = ['25岁以下', '25-30岁', '30-35岁', '35-40岁', '40-45岁', '45-50岁', '50-55岁', '55岁以上', '未知'];
    const labels = order.filter(k => data[k] !== undefined);
    const values = labels.map(k => data[k]);
    drawChart('m-age-chart', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data: values,
                label: '人数',
                backgroundColor: 'rgba(37, 99, 235, 0.82)',
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 }, grid: { color: '#eef2f7' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderMobileSubjectChart(data) {
    const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 8);
    drawChart('m-subject-chart', {
        type: 'bar',
        data: {
            labels: sorted.map(x => x[0]),
            datasets: [{
                data: sorted.map(x => x[1]),
                label: '人数',
                backgroundColor: 'rgba(99, 102, 241, 0.82)',
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 }, grid: { color: '#eef2f7' } },
                y: { grid: { display: false } }
            }
        }
    });
}

function renderMobileWorkYearsChart(data) {
    const labels = ['0-5年', '6-10年', '11-20年', '21年以上', '未知'];
    drawChart('m-workyears-chart', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data: labels.map(k => Number(data[k] || 0)),
                label: '人数',
                backgroundColor: ['#22c55e', '#14b8a6', '#3b82f6', '#6366f1', '#94a3b8'],
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 }, grid: { color: '#eef2f7' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderMobileTitleRank(rows) {
    const box = document.getElementById('m-title-rank');
    if (!box) return;
    if (!rows.length) {
        box.innerHTML = '<div class="empty-state"><p>暂无数据</p></div>';
        return;
    }
    const max = Math.max(...rows.map(r => Number(r.count || 0)), 1);
    box.innerHTML = rows.slice(0, 8).map((r, i) => {
        const pct = Math.round((Number(r.count || 0) / max) * 100);
        return `
            <div class="rank-row">
                <div class="rank-index">${i + 1}</div>
                <div class="rank-main">
                    <div class="rank-line">
                        <span class="rank-name">${r.name}</span>
                        <span class="rank-count">${r.count}</span>
                    </div>
                    <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
                </div>
            </div>
        `;
    }).join('');
}

function renderMobileTags(data) {
    const box = document.getElementById('m-tag-stats');
    if (!box) return;
    const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
    if (!entries.length) {
        box.innerHTML = '<div class="empty-state"><p>暂无标签数据</p></div>';
        return;
    }
    const colors = ['primary', 'success', 'warning', 'danger'];
    box.innerHTML = `<div class="btn-group" style="flex-wrap:wrap;">
        ${entries.slice(0, 20).map(([tag, count], i) =>
            `<span class="tag tag-${colors[i % colors.length]}" style="font-size:13px;padding:5px 12px;">${tag} <span class="badge">${count}</span></span>`
        ).join('')}
    </div>`;
}

document.addEventListener('DOMContentLoaded', loadMobileStats);
