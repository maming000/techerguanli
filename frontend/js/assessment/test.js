let questions = [];
let currentIndex = 0;
let answers = [];

function renderQuestion() {
    const q = questions[currentIndex];
    const total = questions.length;

    const progress = Math.round(((currentIndex + 1) / total) * 100);
    document.getElementById('assessment-progress-label').textContent = `第 ${currentIndex + 1} / ${total} 题`;
    document.getElementById('assessment-progress-fill').style.width = `${progress}%`;
    document.getElementById('assessment-question-text').textContent = q.text_zh || q.text;
    document.getElementById('assessment-question-no').textContent = `Q${q.id}`;

    document.querySelectorAll('input[name="assessment-answer"]').forEach((el) => {
        el.checked = Number(el.value) === Number(answers[currentIndex] || 0);
    });

    document.getElementById('btn-prev-question').disabled = currentIndex === 0;
    const btnNext = document.getElementById('btn-next-question');
    const isLast = currentIndex === total - 1;
    btnNext.textContent = isLast ? '提交测评' : '下一题';
}

function getCurrentSelected() {
    const selected = document.querySelector('input[name="assessment-answer"]:checked');
    return selected ? Number(selected.value) : 0;
}

async function gotoNext() {
    const selected = getCurrentSelected();
    if (!selected) {
        showToast('请先选择一个选项', 'warning');
        return;
    }
    answers[currentIndex] = selected;

    if (currentIndex < questions.length - 1) {
        currentIndex += 1;
        renderQuestion();
        return;
    }

    await submitAssessment();
}

function gotoPrev() {
    if (currentIndex === 0) return;
    const selected = getCurrentSelected();
    if (selected) answers[currentIndex] = selected;
    currentIndex -= 1;
    renderQuestion();
}

async function submitAssessment() {
    try {
        const resp = await api('/api/assessment/submit', {
            method: 'POST',
            body: JSON.stringify({
                question_ids: questions.map((q) => Number(q.id)),
                answers
            })
        });
        saveLastAssessmentResult(resp);
        window.location.href = '/assessment/result';
    } catch (e) {}
}

document.addEventListener('DOMContentLoaded', async () => {
    const user = await getCurrentUser();
    if (!user) return;

    if (user.role !== 'teacher') {
        document.getElementById('assessment-test-wrap').innerHTML = `
            <div class="empty-state">
                <h3>无权限</h3>
                <p>仅教师账号可参与人格测评。</p>
            </div>
        `;
        return;
    }

    try {
        questions = await api('/api/assessment/questions');
        answers = new Array(questions.length).fill(0);
        renderQuestion();
    } catch (e) {
        document.getElementById('assessment-test-wrap').innerHTML = `
            <div class="empty-state">
                <h3>题库加载失败</h3>
                <p>${e.message || '请稍后重试'}</p>
            </div>
        `;
        return;
    }

    document.getElementById('btn-prev-question').addEventListener('click', gotoPrev);
    document.getElementById('btn-next-question').addEventListener('click', gotoNext);
});
