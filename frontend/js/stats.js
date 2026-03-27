/**
 * 统计页面逻辑
 */

const chartPool = {};

document.addEventListener('DOMContentLoaded', loadStats);

async function loadStats() {
    try {
        const [stats, advanced, tagStats] = await Promise.all([
            api('/api/stats/'),
            api('/api/stats/advanced'),
            api('/api/stats/tags')
        ]);

        renderOverview(stats, advanced);
        renderGenderChart(stats.gender_stats || {});
        renderAgeChart(stats.age_stats || {});
        renderEducationChart(stats.education_stats || {});
        renderPoliticalChart(stats.political_stats || {});
        renderTitleChart(advanced.title_stats || {});
        renderSubjectChart(advanced.subject_stats || {});
        renderWorkYearsChart(advanced.work_years_stats || {});
        renderHireYearChart(advanced.hire_year_stats || {});

        renderRankList('subject-top-list', advanced.subject_top || []);
        renderRankList('title-top-list', advanced.title_top || []);
        renderRankList('school-top-list', advanced.graduate_school_top || []);
        renderCompleteness(advanced.completeness || []);
        renderTagStats(tagStats || {});
    } catch (e) {
        console.error('加载统计失败:', e);
    }
}

function renderOverview(stats, advanced) {
    const total = Number(stats.total_teachers || 0);
    const maleCount = Number((stats.gender_stats || {})['男'] || 0);
    const femaleCount = Number((stats.gender_stats || {})['女'] || 0);
    const partyMemberCount = Number(advanced.party_member_count || 0);
    const under35 = Number(advanced.under_35_count || 0);
    const seniorTitle = Number(advanced.senior_title_count || 0);
    const subjectCount = Number(advanced.subject_count || 0);

    setText('total-count', total);
    setText('male-count', maleCount);
    setText('female-count', femaleCount);
    setText('subject-count', subjectCount);
    setText('senior-title-count', seniorTitle);
    setText('under35-count', under35);

    let totalAge = 0;
    let ageCount = 0;
    for (const [range, count] of Object.entries(stats.age_stats || {})) {
        if (range === '未知') continue;
        const m = range.match(/(\d+)/);
        if (!m) continue;
        totalAge += Number(m[1]) * Number(count || 0);
        ageCount += Number(count || 0);
    }
    setText('avg-age', ageCount > 0 ? Math.round(totalAge / ageCount) : '-');

    const partyRate = total > 0 ? `${Math.round((partyMemberCount / total) * 100)}%` : '-';
    setText('party-rate', partyRate);
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function renderChart(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    if (chartPool[id]) {
        chartPool[id].destroy();
    }
    chartPool[id] = new Chart(canvas.getContext('2d'), config);
}

function renderGenderChart(data) {
    const labels = Object.keys(data);
    const values = Object.values(data);
    renderChart('gender-chart', {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: ['#2563eb', '#ec4899', '#94a3b8'],
                borderWidth: 0
            }]
        },
        options: commonRoundChartOptions('65%')
    });
}

function renderAgeChart(data) {
    const order = ['25岁以下', '25-30岁', '30-35岁', '35-40岁', '40-45岁', '45-50岁', '50-55岁', '55岁以上', '未知'];
    const labels = order.filter(k => data[k] !== undefined);
    const values = labels.map(k => data[k]);

    renderChart('age-chart', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '人数',
                data: values,
                backgroundColor: 'rgba(37, 99, 235, 0.78)',
                borderRadius: 8,
                borderSkipped: false,
                maxBarThickness: 42
            }]
        },
        options: commonBarOptions()
    });
}

function renderEducationChart(data) {
    const labels = Object.keys(data);
    const values = Object.values(data);
    renderChart('education-chart', {
        type: 'pie',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: ['#2563eb', '#16a34a', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 14, usePointStyle: true } }
            }
        }
    });
}

function renderPoliticalChart(data) {
    const labels = Object.keys(data);
    const values = Object.values(data);
    renderChart('political-chart', {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: ['#ef4444', '#f59e0b', '#16a34a', '#3b82f6', '#8b5cf6', '#94a3b8'],
                borderWidth: 0
            }]
        },
        options: commonRoundChartOptions('60%')
    });
}

function renderTitleChart(data) {
    const sorted = Object.entries(data)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    const labels = sorted.map(x => x[0]);
    const values = sorted.map(x => x[1]);

    renderChart('title-chart', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '人数',
                data: values,
                backgroundColor: 'rgba(20, 184, 166, 0.82)',
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: commonBarOptions(true)
    });
}

function renderSubjectChart(data) {
    const sorted = Object.entries(data)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 12);
    const labels = sorted.map(x => x[0]);
    const values = sorted.map(x => x[1]);

    renderChart('subject-chart', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '人数',
                data: values,
                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: commonBarOptions(true)
    });
}

function renderWorkYearsChart(data) {
    const labels = ['0-5年', '6-10年', '11-20年', '21年以上', '未知'];
    const values = labels.map(k => Number(data[k] || 0));
    renderChart('work-years-chart', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '人数',
                data: values,
                backgroundColor: ['#22c55e', '#14b8a6', '#3b82f6', '#6366f1', '#94a3b8'],
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: commonBarOptions()
    });
}

function renderHireYearChart(data) {
    const entries = Object.entries(data).sort((a, b) => a[0].localeCompare(b[0]));
    const labels = entries.map(x => x[0]);
    const values = entries.map(x => x[1]);

    renderChart('hire-year-chart', {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: '入职人数',
                data: values,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.16)',
                fill: true,
                tension: 0.3,
                pointRadius: 3
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

function commonRoundChartOptions(cutout) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        cutout,
        plugins: {
            legend: { position: 'bottom', labels: { padding: 14, usePointStyle: true } }
        }
    };
}

function commonBarOptions(horizontal = false) {
    return {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            y: horizontal
                ? { grid: { display: false } }
                : { beginAtZero: true, ticks: { stepSize: 1, precision: 0 }, grid: { color: '#eef2f7' } },
            x: horizontal
                ? { beginAtZero: true, ticks: { stepSize: 1, precision: 0 }, grid: { color: '#eef2f7' } }
                : { grid: { display: false } }
        }
    };
}

function renderRankList(containerId, rows) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!rows || rows.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无数据</p></div>';
        return;
    }

    const max = Math.max(...rows.map(x => Number(x.count || 0)), 1);
    const html = rows.map((item, idx) => {
        const pct = Math.round((Number(item.count || 0) / max) * 100);
        return `
            <div class="rank-row">
                <div class="rank-index">${idx + 1}</div>
                <div class="rank-main">
                    <div class="rank-line">
                        <span class="rank-name">${item.name}</span>
                        <span class="rank-count">${item.count}</span>
                    </div>
                    <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
                </div>
            </div>`;
    }).join('');
    container.innerHTML = `<div class="rank-list">${html}</div>`;
}

function renderCompleteness(rows) {
    const container = document.getElementById('completeness-stats');
    if (!container) return;
    if (!rows || rows.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无数据</p></div>';
        return;
    }

    const html = rows.map((row) => {
        const pct = Math.round((Number(row.ratio || 0)) * 100);
        return `
            <div class="quality-row">
                <div class="quality-head">
                    <span>${row.field}</span>
                    <span>${row.filled}/${row.total}（${pct}%）</span>
                </div>
                <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
            </div>`;
    }).join('');
    container.innerHTML = `<div class="quality-grid">${html}</div>`;
}

function renderTagStats(data) {
    const container = document.getElementById('tag-stats');
    if (!container) return;
    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无标签数据</p></div>';
        return;
    }

    const colors = ['primary', 'success', 'warning', 'danger'];
    const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
    let html = '<div class="btn-group" style="flex-wrap: wrap;">';
    sorted.forEach(([tag, count], i) => {
        html += `<span class="tag tag-${colors[i % colors.length]}" style="font-size: 14px; padding: 6px 14px;">${tag} <span class="badge">${count}</span></span>`;
    });
    html += '</div>';
    container.innerHTML = html;
}
