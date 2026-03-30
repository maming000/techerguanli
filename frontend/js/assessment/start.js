document.addEventListener('DOMContentLoaded', async () => {
    const user = await getCurrentUser();
    if (!user) return;

    const hint = document.getElementById('assessment-start-role-hint');
    if (user.role === 'teacher') {
        hint.textContent = '当前身份：教师，可进行测评并查看本人历史记录。';
    } else if (user.role === 'admin') {
        hint.textContent = '当前身份：管理员，可查看测试明细（账号/时间/IP/逐题作答）及汇总统计。';
    } else {
        hint.textContent = '当前身份：浏览账号，仅可查看基础信息。';
    }
});
