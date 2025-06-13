from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import pathlib

cityRouter = APIRouter()


# 模板下载接口
@cityRouter.get("/download_template")
async def download_template():
    """模板下载接口"""
    file_path = (
        pathlib.Path(__file__).parent.parent / "src" / "城市道路导入模板_V1.0.xlsx"
    )
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="模板文件不存在")
    return FileResponse(
        path=file_path,
        filename="城市道路导入模板.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
