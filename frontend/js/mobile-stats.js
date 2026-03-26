async function loadMobileStats() {
    await mRequireAuth();
    const wrap = document.getElementById('m-stats-grid');
    wrap.innerHTML = '<div class="loading"><div class="spinner"></div> 加载中...</div>';
    try {
        const s = await mApi('/api/stats/');
        const male = s.gender_stats?.['男'] || 0;
        const female = s.gender_stats?.['女'] || 0;
        wrap.innerHTML = `
            <div class="stat-card"><div class="stat-icon blue">👥</div><div class="stat-info"><h3>${s.total_teachers || 0}</h3><p>教师总数</p></div></div>
            <div class="stat-card"><div class="stat-icon green">👨</div><div class="stat-info"><h3>${male}</h3><p>男教师</p></div></div>
            <div class="stat-card"><div class="stat-icon orange">👩</div><div class="stat-info"><h3>${female}</h3><p>女教师</p></div></div>`;
    } catch (e) {
        wrap.innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${e.message}</p></div>`;
    }
}

document.addEventListener('DOMContentLoaded', loadMobileStats);
