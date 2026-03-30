(function () {
    function isFilled(val) {
        if (val === null || val === undefined) return false;
        if (typeof val === 'string') return val.trim() !== '';
        if (Array.isArray(val)) return val.length > 0;
        return true;
    }

    function display(val) {
        if (!isFilled(val)) return '-';
        if (Array.isArray(val)) return val.join('、');
        return String(val);
    }

    function pick(obj, keys) {
        if (!obj) return '';
        for (const key of keys) {
            if (isFilled(obj[key])) return obj[key];
        }
        return '';
    }

    function normalizeKey(key) {
        return String(key || '')
            .toLowerCase()
            .replace(/\s+/g, '')
            .replace(/[-_]/g, '');
    }

    function buildNormalizedMap(obj) {
        const m = {};
        if (!obj) return m;
        Object.keys(obj).forEach((k) => {
            m[normalizeKey(k)] = obj[k];
        });
        return m;
    }

    function pickAlias(row, extra, aliases) {
        const rowNorm = buildNormalizedMap(row);
        const exNorm = buildNormalizedMap(extra);
        for (const alias of aliases) {
            if (isFilled(row && row[alias])) return row[alias];
            if (isFilled(extra && extra[alias])) return extra[alias];
            const n = normalizeKey(alias);
            if (isFilled(rowNorm[n])) return rowNorm[n];
            if (isFilled(exNorm[n])) return exNorm[n];
        }
        return '';
    }

    function pickContains(row, extra, patterns) {
        const items = [];
        if (row) {
            Object.keys(row).forEach((k) => items.push([k, row[k]]));
        }
        if (extra) {
            Object.keys(extra).forEach((k) => items.push([k, extra[k]]));
        }
        const normPatterns = (patterns || []).map((p) => normalizeKey(p));
        for (const [k, v] of items) {
            if (!isFilled(v)) continue;
            const nk = normalizeKey(k);
            if (normPatterns.some((p) => nk.includes(p))) return v;
        }
        return '';
    }

    function calcAge(birthDate) {
        if (!isFilled(birthDate)) return '';
        const d = new Date(birthDate);
        if (Number.isNaN(d.getTime())) return '';
        const now = new Date();
        let age = now.getFullYear() - d.getFullYear();
        const monthDiff = now.getMonth() - d.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < d.getDate())) age -= 1;
        return age > 0 ? String(age) : '';
    }

    function normalizeTeacher(raw) {
        const t = raw || {};
        const ex = t.extra_fields || {};
        const normalized = {
            id: t.id,
            name: pickAlias(t, ex, ['name', '姓名']),
            gender: pickAlias(t, ex, ['gender', '性别']),
            id_card: pickAlias(t, ex, ['id_card', 'idcard', '身份证号']),
            birth_date: pickAlias(t, ex, ['birth_date', 'birthday', '出生日期']),
            ethnicity: pickAlias(t, ex, ['ethnicity', 'nation', '民族']),
            native_place: pickAlias(t, ex, ['native_place', 'hometown', '籍贯']) || pickContains(t, ex, ['户籍', '籍贯']),
            political_status: pickAlias(t, ex, ['political_status', 'politics_status', '政治面貌']),
            hire_date: pickAlias(t, ex, ['hire_date', 'entry_date', '入职日期', '参加工作时间', '参加工作日期']) || pickContains(t, ex, ['入职', '参加工作']),
            subject: pickAlias(t, ex, ['subject', 'teach_subject', '任教学科']),
            title: pickAlias(t, ex, ['title', '职称']),
            position: pickAlias(t, ex, ['position', '岗位', '职务']),
            employee_id: pickAlias(t, ex, ['employee_id', 'job_no', 'staff_no', '工号']),
            civil_service_date: pickAlias(t, ex, ['civil_service_date', 'public_service_time', '参公时间', '参公日期', '参工时间', '参工日期']) || pickContains(t, ex, ['参工', '参公']),
            archive_no: pickAlias(t, ex, ['archive_no', 'dossier_no', 'file_no', 'personnel_file_no', '档案编号', '档案号', '人事档案编号']),
            education: pickAlias(t, ex, ['education', '学历']),
            degree: pickAlias(t, ex, ['degree', '学位', '最高学位']) || pickContains(t, ex, ['学位']),
            graduate_school: pickAlias(t, ex, ['graduate_school', 'school', '毕业学校', '毕业院校']),
            major: pickAlias(t, ex, ['major', '专业']),
            party_join_date: pickAlias(t, ex, ['party_join_date', 'join_party_date', '入党时间']),
            qualification: pickAlias(t, ex, ['qualification', 'certificate', '资格证书']),
            mobile: pickAlias(t, ex, ['mobile', 'mobile_phone', '手机号', '手机', '手机号码']),
            short_phone: pickAlias(t, ex, ['short_phone', 'short_mobile', 'shortphone', '小号', '短号']),
            email: pickAlias(t, ex, ['email', '邮箱', '电子邮箱', '电子邮件']),
            phone: pickAlias(t, ex, ['phone', 'tel', 'telephone', '联系电话']),
            address: pickAlias(t, ex, ['address', 'home_address', '家庭住址', '家庭地址']),
            plate_no_1: pickAlias(t, ex, ['plate_no_1', 'plate_no', 'car_plate', '车牌号码', '车牌号码1', '车牌号码１', '车牌号码一', '车牌号1', '车牌号１', '车牌号一', '车牌1', '车牌１', '车牌一']) || pickContains(t, ex, ['车牌号码1', '车牌号码１', '车牌号码一', '车牌号1', '车牌1']),
            plate_no_2: pickAlias(t, ex, ['plate_no_2', 'car_plate_2', '车牌号码2', '车牌号码２', '车牌号码二', '车牌号2', '车牌号２', '车牌号二', '车牌2', '车牌２', '车牌二']) || pickContains(t, ex, ['车牌号码2', '车牌号码２', '车牌号码二', '车牌号2', '车牌2']),
            avatar: pickAlias(t, ex, ['__profile_avatar']),
            cover_color: pickAlias(t, ex, ['__profile_cover_color'])
        };
        normalized.age = pickAlias(t, ex, ['age', '年龄']) || calcAge(normalized.birth_date);
        normalized.staff_id = isFilled(t.id) ? `T${t.id}` : '';
        normalized.role = normalized.title || '';
        return normalized;
    }

    const SECTIONS = [
        {
            key: 'identity',
            title: '身份信息',
            fields: [
                { key: 'name', label: '姓名' },
                { key: 'gender', label: '性别' },
                { key: 'id_card', label: '身份证号' },
                { key: 'birth_date', label: '出生日期' },
                { key: 'age', label: '年龄' },
                { key: 'ethnicity', label: '民族' },
                { key: 'native_place', label: '籍贯' },
                { key: 'political_status', label: '政治面貌' }
            ]
        },
        {
            key: 'position',
            title: '教职岗位',
            fields: [
                { key: 'hire_date', label: '入职日期' },
                { key: 'subject', label: '任教学科' },
                { key: 'title', label: '职称' },
                { key: 'employee_id', label: '工号' },
                { key: 'civil_service_date', label: '参公时间' },
                { key: 'archive_no', label: '档案编号' }
            ]
        },
        {
            key: 'education',
            title: '学历资质',
            fields: [
                { key: 'education', label: '最高学历' },
                { key: 'degree', label: '最高学位' },
                { key: 'graduate_school', label: '毕业学校' },
                { key: 'major', label: '专业' },
                { key: 'party_join_date', label: '入党时间' }
            ]
        },
        {
            key: 'contact',
            title: '联系方式',
            fields: [
                { key: 'mobile', label: '手机号码' },
                { key: 'short_phone', label: '小号' },
                { key: 'email', label: '电子邮件' },
                { key: 'phone', label: '联系电话' },
                { key: 'address', label: '家庭地址' },
                { key: 'plate_no_1', label: '车牌号码1' },
                { key: 'plate_no_2', label: '车牌号码2' }
            ]
        }
    ];

    function getVisibleFields(section, data) {
        return (section.fields || []).filter((f) => isFilled(data[f.key]));
    }

    window.TeacherSchema = {
        SECTIONS,
        isFilled,
        display,
        normalizeTeacher,
        getVisibleFields
    };
})();
