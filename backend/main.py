"""
教师信息管理系统 - FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.database import init_database
from backend.config import FRONTEND_DIR
from backend.routers import upload, teachers, stats, export

# 初始化数据库
init_database()

# 创建 FastAPI 应用
app = FastAPI(
    title="教师信息管理系统",
    description="用于整合和管理教师数据的 Web 系统",
    version="1.0.0"
)

# 注册路由
app.include_router(upload.router)
app.include_router(teachers.router)
app.include_router(stats.router)
app.include_router(export.router)

# 挂载前端静态文件
app.mount("/css", StaticFiles(directory=f"{FRONTEND_DIR}/css"), name="css")
app.mount("/js", StaticFiles(directory=f"{FRONTEND_DIR}/js"), name="js")


@app.get("/")
async def index():
    """首页"""
    return FileResponse(f"{FRONTEND_DIR}/index.html")


@app.get("/upload")
async def upload_page():
    """上传页面"""
    return FileResponse(f"{FRONTEND_DIR}/upload.html")


@app.get("/stats")
async def stats_page():
    """统计页面"""
    return FileResponse(f"{FRONTEND_DIR}/stats.html")


@app.get("/detail")
async def detail_page():
    """教师详情页面"""
    return FileResponse(f"{FRONTEND_DIR}/detail.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
