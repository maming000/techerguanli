# 教师信息管理系统

一个本地部署的 Web 系统，用于整合和管理分散在 Excel 和 Word 中的教师数据。

## ✨ 功能特点

- 📤 **文件导入** — 支持 Excel (.xlsx/.xls) 和 Word (.docx) 格式
- 🔍 **智能识别** — 自动识别字段，未知字段自动扩展
- 🔄 **数据合并** — 按身份证号→手机号→姓名去重，不覆盖已有数据
- 📊 **统计分析** — 性别、年龄、学历、政治面貌的可视化图表
- 🏷️ **标签系统** — 自定义标签（如：班主任、骨干教师等）
- 📥 **数据导出** — 将筛选结果导出为 Excel
- 📝 **操作日志** — 记录每次数据修改的历史

## 🚀 快速启动

### 前置要求

- Python 3.8 以上

### Mac / Linux

```bash
chmod +x run.sh
./run.sh
```

### Windows

双击运行 `run.bat`

### 手动启动

```bash
# 安装依赖
pip install -r backend/requirements.txt

# 启动服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问: **http://localhost:8000**

## 📂 项目结构

```
project/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置文件
│   ├── database.py          # 数据库初始化
│   ├── models.py            # 数据模型
│   ├── routers/             # API 路由
│   │   ├── teachers.py      # 教师 CRUD
│   │   ├── upload.py        # 文件上传
│   │   ├── stats.py         # 统计分析
│   │   └── export.py        # 数据导出
│   └── services/            # 业务服务
│       ├── parser_excel.py  # Excel 解析
│       ├── parser_word.py   # Word 解析
│       ├── field_detector.py # 字段识别
│       ├── data_cleaner.py  # 数据清洗
│       └── id_card_utils.py # 身份证工具
├── frontend/                # 前端页面
├── database/                # SQLite 数据库
├── uploads/                 # 上传文件存储
├── test_data/               # 示例测试数据
├── run.sh                   # Mac/Linux 启动
├── run.bat                  # Windows 启动
└── generate_test_data.py    # 测试数据生成
```

## 🧪 测试方式

```bash
# 1. 生成测试数据
python generate_test_data.py

# 2. 启动系统
./run.sh

# 3. 打开浏览器访问 http://localhost:8000

# 4. 进入"数据导入"页面，上传 test_data/ 中的文件

# 5. 回到首页查看导入的数据，测试筛选和搜索

# 6. 进入"统计分析"查看图表

# 7. 点击教师姓名查看详情，测试编辑和标签功能
```

## 📋 API 文档

启动服务后访问 **http://localhost:8000/docs** 查看自动生成的 Swagger 文档。

主要接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/teachers/` | GET | 查询教师列表（支持分页、筛选） |
| `/api/teachers/{id}` | GET | 获取教师详情 |
| `/api/teachers/{id}` | PUT | 更新教师信息 |
| `/api/teachers/{id}` | DELETE | 删除教师 |
| `/api/upload/` | POST | 上传并解析文件 |
| `/api/stats/` | GET | 获取统计数据 |
| `/api/export/excel` | GET | 导出 Excel |
