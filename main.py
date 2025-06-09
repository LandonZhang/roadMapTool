from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from router.countryRouter import countryRouter
from router.cityRouter import cityRouter

app = FastAPI(title="Roadmap", description="路网数据采集工具")


# 使用FastAPI的CORSMiddleware，它会处理所有CORS相关的头信息
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，可以改为特定域名列表
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有HTTP头
)

app.include_router(countryRouter, prefix="/countryside", tags=["农村公路相关接口"])  # type: ignore
app.include_router(cityRouter, prefix="/city", tags=["城市道路相关接口"])  # type: ignore

if __name__ == "__main__":
    uvicorn.run("main:app", port=8080, reload=True)
