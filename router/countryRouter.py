import pathlib
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import os
import dotenv
from io import BytesIO
from utils.country_road_service import CountryRoadService

# 加载环境变量
dotenv.load_dotenv(".env")

countryRouter = APIRouter()

# 初始化农村公路服务（从环境变量读取配置）
API_BASE_URL = os.getenv("COUNTRY_API_BASE_URL")
API_TOKEN = os.getenv("API_TOKEN")


def get_country_road_service():
    """获取农村公路服务实例"""
    return CountryRoadService(base_url=API_BASE_URL, api_token=API_TOKEN)  # type: ignore


# 模板下载接口
@countryRouter.get("/download_template")
async def download_template():
    """模板下载接口"""
    file_path = (
        pathlib.Path(__file__).parent.parent / "src" / "农村公路导入模板_V1.0.xlsx"
    )
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="模板文件不存在")
    return FileResponse(
        path=file_path,
        filename="农村公路导入模板.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# 数据导入接口
@countryRouter.post("/import_data")
async def import_country_roads(file: UploadFile = File(...)):
    """农村公路数据导入接口"""
    print(f"接收到文件上传请求: {file.filename}")

    # 验证文件格式
    if not file.filename.endswith((".xlsx", ".xls")):  # type: ignore
        raise HTTPException(
            status_code=400, detail="文件格式错误，请上传Excel文件(.xlsx或.xls)"
        )

    try:
        # 读取文件内容
        file_content = await file.read()
        print(f"文件读取成功，大小: {len(file_content)} bytes")

        # 转化为文件类对象
        file_stream = BytesIO(file_content)

        # 获取服务实例并处理
        service = get_country_road_service()
        result = service.process_country_road_import(file_stream)

        # 根据处理结果返回相应的HTTP状态码
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "code": 0,
                    "message": result["message"],
                    "data": {
                        "total_rows": result["total_rows"],
                        "processed_rows": result["processed_rows"],
                        "failed_rows": result["failed_rows"],
                        "road_results": result["road_results"],
                    },
                },
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "code": 1,
                    "message": result["message"],
                    "data": {
                        "total_rows": result["total_rows"],
                        "processed_rows": result["processed_rows"],
                        "failed_rows": result["failed_rows"],
                        "errors": result["errors"][:10],  # 只返回前10个错误信息
                    },
                },
            )

    except Exception as e:
        error_msg = f"文件处理异常: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
