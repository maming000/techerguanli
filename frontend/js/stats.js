/**
 * 统计页面逻辑
 */

document.addEventListener('DOMContentLoaded', loadStats);

async function loadStats() {
    try {
        const stats = await api('/api/stats/');
        renderOverview(stats);
        renderGenderChart(stats.gender_stats);
        renderAgeChart(stats.age_stats);
        renderEducationChart(stats.education_stats);
        renderPoliticalChart(stats.political_stats);
    } catch (e) {
        console.error('加载统计失败:', e);
    }

    // 加载标签统计
    try {
        const tagStats = await api('/api/stats/tags');
        renderTagStats(tagStats);
    } catch (e) {
        console.error('加载标签统计失败:', e);
    }
}

function renderOverview(stats) {
    document.getElementById('total-count').textContent = stats.total_teachers;

    const maleCount = stats.gender_stats['男'] || 0;
    const femaleCount = stats.gender_stats['女'] || 0;
    document.getElementById('male-count').textContent = maleCount;
    document.getElementById('female-count').textContent = femaleCount;

    // 计算平均年龄（近似值）
    let totalAge = 0, ageCount = 0;
    for (const [range, count] of Object.entries(stats.age_stats)) {
        if (range === '未知') continue;
        // 提取年龄范围的中位数
        const match = range.match(/(\d+)/);
        if (match) {
            totalAge += parseInt(match[1]) * count;
            ageCount += count;
        }
    }
    const avgAge = ageCount > 0 ? Math.round(totalAge / ageCount) : '-';
    document.getElementById('avg-age').textContent = avgAge;
}

function renderGenderChart(data) {
    const ctx = document.getElementById('gender-chart').getContext('2d');
    const labels = Object.keys(data);
    const values = Object.values(data);
    const colors = ['#4f6ef7', '#f472b6', '#94a3b8'];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 20, usePointStyle: true }
                }
            }
        }
    });
}

function renderAgeChart(data) {
    const ctx = document.getElementById('age-chart').getContext('2d');
    // 按年龄范围排序
    const order = ['25岁以下', '25-30岁', '30-35岁', '35-40岁', '40-45岁', '45-50岁', '50-55岁', '55岁以上', '未知'];
    const sorted = order.filter(k => data[k] !== undefined);
    const labels = sorted;
    const values = sorted.map(k => data[k]);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '人数',
                data: values,
                backgroundColor: 'rgba(79, 110, 247, 0.8)',
                borderRadius: 6,
                borderSkipped: false,
                maxBarThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, precision: 0 },
                    grid: { color: '#f1f5f9' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

function renderEducationChart(data) {
    const ctx = document.getElementById('education-chart').getContext('2d');
    const labels = Object.keys(data);
    const values = Object.values(data);
    const colors = ['#4f6ef7', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899'];

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 16, usePointStyle: true }
                }
            }
        }
    });
}

function renderPoliticalChart(data) {
    const ctx = document.getElementById('political-chart').getContext('2d');
    const labels = Object.keys(data);
    const values = Object.values(data);
    const colors = ['#ef4444', '#f59e0b', '#22c55e', '#4f6ef7', '#8b5cf6', '#94a3b8'];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 16, usePointStyle: true }
                }
            }
        }
    });
}

function renderTagStats(data) {
    const container = document.getElementById('tag-stats');
    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无标签数据</p></div>';
        return;
    }

    const colors = ['primary', 'success', 'warning', 'danger'];
    let html = '<div class="btn-group" style="flex-wrap: wrap;">';
    let i = 0;
    for (const [tag, count] of Object.entries(data)) {
        html += `<span class="tag tag-${colors[i % colors.length]}" style="font-size: 14px; padding: 6px 14px;">${tag} <span class="badge">${count}</span></span>`;
        i++;
    }
    html += '</div>';
    container.innerHTML = html;
}
