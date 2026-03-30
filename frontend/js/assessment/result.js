let resultChart = null;

function renderResultCards(scores) {
    const wrap = document.getElementById('assessment-result-cards');
    const html = TRAIT_KEYS.map((key) => {
        const score = Number(scores[key] || 0);
        return `
            <div class="assessment-score-card">
                <div class="assessment-score-head">
                    <span>${TRAIT_LABELS[key]}</span>
                    <strong>${score.toFixed(1)}</strong>
                </div>
                <div class="progress-bar"><div class="progress-fill" style="width:${score}%"></div></div>
                <p class="assessment-interpret">${traitInterpretation(key, score)}</p>
                <p class="assessment-suggestion"><strong>教学建议：</strong>${teachingSuggestion(key, score)}</p>
            </div>
        `;
    }).join('');
    wrap.innerHTML = html;
}

function renderRadar(scores) {
    const dom = document.getElementById('assessment-radar');
    if (!dom) return;
    if (resultChart) resultChart.dispose();
    resultChart = echarts.init(dom);

    resultChart.setOption({
        tooltip: {},
        radar: {
            indicator: TRAIT_KEYS.map((k) => ({ name: TRAIT_LABELS[k], max: 100 })),
            splitLine: { lineStyle: { color: '#dbe6f3' } },
            splitArea: { areaStyle: { color: ['rgba(79,110,247,0.03)', 'rgba(79,110,247,0.06)'] } }
        },
        series: [{
            type: 'radar',
            data: [{
                value: TRAIT_KEYS.map((k) => Number(scores[k] || 0)),
                name: '本次测评',
                areaStyle: { color: 'rgba(79,110,247,0.25)' },
                lineStyle: { color: '#4f6ef7', width: 2 },
                symbolSize: 6
            }]
        }]
    });
}

async function loadFromHistoryIfNeeded() {
    const rows = await api('/api/assessment/history');
    if (!rows || rows.length === 0) return null;
    return rows[0];
}

document.addEventListener('DOMContentLoaded', async () => {
    const user = await getCurrentUser();
    if (!user) return;

    if (user.role !== 'teacher') {
        document.getElementById('assessment-result-wrap').innerHTML = `
            <div class="empty-state">
                <h3>无权限</h3>
                <p>管理员不查看个体测评结果，可前往历史页查看汇总统计。</p>
            </div>
        `;
        return;
    }

    try {
        let result = loadLastAssessmentResult();
        if (!result || !result.scores) {
            result = await loadFromHistoryIfNeeded();
        }
        if (!result || !result.scores) {
            document.getElementById('assessment-result-wrap').innerHTML = `
                <div class="empty-state">
                    <h3>暂无测评结果</h3>
                    <p>请先完成一次测评。</p>
                </div>
            `;
            return;
        }

        document.getElementById('assessment-result-time').textContent = result.created_at || '-';
        renderResultCards(result.scores);
        renderRadar(result.scores);
    } catch (e) {
        document.getElementById('assessment-result-wrap').innerHTML = `
            <div class="empty-state">
                <h3>加载失败</h3>
                <p>${e.message || '请稍后重试'}</p>
            </div>
        `;
    }
});

window.addEventListener('resize', () => {
    if (resultChart) resultChart.resize();
});

