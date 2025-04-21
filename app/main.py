import os
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn

from api.routes import router as api_router

app = FastAPI(title="AI文档生成平台")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，包括Vue开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建模板和静态文件目录
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
documents_dir = static_dir / "documents"
frontend_dir = Path(__file__).parent.parent / "frontend/dist"

if not templates_dir.exists():
    templates_dir.mkdir(parents=True)
    
if not static_dir.exists():
    static_dir.mkdir(parents=True)
    
if not documents_dir.exists():
    documents_dir.mkdir(parents=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 设置模板
templates = Jinja2Templates(directory=templates_dir)

# 包含API路由
app.include_router(api_router, prefix="/api")

# 下载生成的文件
@app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    print(f"Requested file path: {file_path}")
    
    # 统一处理文件路径，确保正确解析
    if file_path.startswith("documents/"):
        # 如果路径已经包含documents/前缀，直接在static_dir中查找
        file_path_obj = static_dir / file_path
    else:
        # 否则假设它应该在documents子目录中
        file_path_obj = static_dir / "documents" / file_path
    
    print(f"Looking for file at: {file_path_obj}")
    
    if not file_path_obj.exists():
        # 尝试一个备选路径
        alternative_path = static_dir / file_path
        print(f"File not found, trying alternative path: {alternative_path}")
        
        if alternative_path.exists():
            file_path_obj = alternative_path
        else:
            raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    
    return FileResponse(path=file_path_obj, filename=file_path_obj.name)

# 健康检查端点
@app.get("/api/health")
async def health_check():
    return JSONResponse({"status": "ok"})

# 主页
@app.get("/")
async def read_root(request: Request):
    # 如果前端已构建，提供构建后的前端
    if frontend_dir.exists():
        return FileResponse(frontend_dir / "index.html")
    return templates.TemplateResponse("index.html", {"request": request})

# 为前端路由提供支持
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # 如果前端已构建，提供构建后的静态文件
    if frontend_dir.exists():
        file_path = frontend_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dir / "index.html")
    raise HTTPException(status_code=404, detail="页面不存在")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 