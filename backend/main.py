"""
教师信息管理系统 - FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.database import init_database
from backend.config import FRONTEND_DIR, UPLOAD_DIR
from backend.routers import upload, teachers, stats, export, auth, users

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
app.include_router(auth.router)
app.include_router(users.router)

# 挂载前端静态文件
app.mount("/css", StaticFiles(directory=f"{FRONTEND_DIR}/css"), name="css")
app.mount("/js", StaticFiles(directory=f"{FRONTEND_DIR}/js"), name="js")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


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


@app.get("/login")
async def login_page():
    """登录页面"""
    return FileResponse(f"{FRONTEND_DIR}/login.html")


@app.get("/onboard")
async def onboard_page():
    """新教师公开入职登记页"""
    return FileResponse(f"{FRONTEND_DIR}/onboard.html")


@app.get("/m")
async def mobile_index_page():
    """移动端首页"""
    return FileResponse(f"{FRONTEND_DIR}/mobile/index.html")


@app.get("/m/detail")
async def mobile_detail_page():
    """移动端详情页"""
    return FileResponse(f"{FRONTEND_DIR}/mobile/detail.html")


@app.get("/m/upload")
async def mobile_upload_page():
    """移动端上传页"""
    return FileResponse(f"{FRONTEND_DIR}/mobile/upload.html")


@app.get("/m/stats")
async def mobile_stats_page():
    """移动端统计页"""
    return FileResponse(f"{FRONTEND_DIR}/mobile/stats.html")


@app.get("/m/login")
async def mobile_login_page():
    """移动端登录页"""
    return FileResponse(f"{FRONTEND_DIR}/mobile/login.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
