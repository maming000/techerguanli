const ASSESSMENT_CACHE_KEY = 'assessment_ipip50_questions_v1';
const ASSESSMENT_LAST_RESULT_KEY = 'assessment_last_result_v1';

const TRAIT_LABELS = {
    openness: '开放性',
    conscientiousness: '尽责性',
    extraversion: '外向性',
    agreeableness: '宜人性',
    neuroticism: '情绪性'
};

const TRAIT_KEYS = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism'];

function traitLevel(score) {
    const s = Number(score || 0);
    if (s < 35) return '较低';
    if (s < 70) return '中等';
    return '较高';
}

function traitInterpretation(key, score) {
    const level = traitLevel(score);
    const map = {
        openness: {
            low: '偏好熟悉和稳定，创新探索动力相对较弱。',
            mid: '兼顾传统与创新，能在稳定中逐步改进。',
            high: '乐于探索新理念，适应变化和创新能力较强。'
        },
        conscientiousness: {
            low: '执行与计划性偏弱，易受干扰，建议加强任务管理。',
            mid: '责任感与条理性较均衡，能稳定完成工作任务。',
            high: '目标感和自律性较强，擅长计划与持续推进。'
        },
        extraversion: {
            low: '偏内向，适合深度思考和安静环境下的工作。',
            mid: '在表达与倾听之间较平衡，社交适应性良好。',
            high: '表达积极、互动性强，适合带动课堂氛围。'
        },
        agreeableness: {
            low: '沟通风格较直接，协作中需注意共情与反馈方式。',
            mid: '合作性较好，兼顾原则和关系。',
            high: '同理心和协作意识较强，团队支持度高。'
        },
        neuroticism: {
            low: '情绪较稳定，抗压和复原能力较好。',
            mid: '压力下偶有波动，整体可维持平衡。',
            high: '更易焦虑或紧张，建议加强压力管理与情绪调节。'
        }
    };
    const lv = level === '较低' ? 'low' : (level === '中等' ? 'mid' : 'high');
    return `${level}：${map[key][lv]}`;
}

function teachingSuggestion(key, score) {
    const s = Number(score || 0);
    const tips = {
        openness: s >= 70
            ? '可承担课程创新、跨学科项目设计。'
            : (s >= 35 ? '在已有教案基础上做小步迭代。' : '先从固定模板入手，再逐步增加创新环节。'),
        conscientiousness: s >= 70
            ? '适合负责年级计划、教学质量跟进。'
            : (s >= 35 ? '使用周计划与任务清单保持节奏。' : '建议引入番茄钟和复盘机制提升执行。'),
        extraversion: s >= 70
            ? '适合主讲公开课、班级活动组织。'
            : (s >= 35 ? '课堂互动与讲授可按比例平衡。' : '可增加结构化提问与小组讨论作为互动桥梁。'),
        agreeableness: s >= 70
            ? '适合家校沟通和跨组协作。'
            : (s >= 35 ? '协作时明确边界与分工即可。' : '沟通中可先复述对方观点再表达立场。'),
        neuroticism: s >= 70
            ? '建议增加情绪复盘与压力缓冲安排。'
            : (s >= 35 ? '保持作息和运动有助于稳定状态。' : '可在高压场景承担稳定推进角色。')
    };
    return tips[key];
}

async function loadAssessmentQuestions() {
    const cached = localStorage.getItem(ASSESSMENT_CACHE_KEY);
    if (cached) {
        try {
            const parsed = JSON.parse(cached);
            if (Array.isArray(parsed) && parsed.length === 50) return parsed;
        } catch {}
    }
    const resp = await fetch('/js/assessment/ipip50_questions.json', { cache: 'force-cache' });
    if (!resp.ok) throw new Error('题库加载失败');
    const questions = await resp.json();
    if (!Array.isArray(questions) || questions.length !== 50) {
        throw new Error('题库格式错误');
    }
    localStorage.setItem(ASSESSMENT_CACHE_KEY, JSON.stringify(questions));
    return questions;
}

function saveLastAssessmentResult(result) {
    sessionStorage.setItem(ASSESSMENT_LAST_RESULT_KEY, JSON.stringify(result || {}));
}

function loadLastAssessmentResult() {
    const raw = sessionStorage.getItem(ASSESSMENT_LAST_RESULT_KEY);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function clearLastAssessmentResult() {
    sessionStorage.removeItem(ASSESSMENT_LAST_RESULT_KEY);
}

