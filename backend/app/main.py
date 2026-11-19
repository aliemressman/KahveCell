from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.billing import payment_router, subscription_router
from app.api.v1.orders import router as orders_router
from app.api.v1.shops import router as shops_router
from app.db.session import create_tables


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    create_tables()
    yield


app = FastAPI(title="KahveCell API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(subscription_router)
app.include_router(payment_router)
app.include_router(shops_router)
app.include_router(orders_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=PlainTextResponse)
def read_root() -> str:
    return "çalışıyor"
