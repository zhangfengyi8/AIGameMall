from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.accounts import router as accounts_router
from app.routers.agent_results import router as agent_results_router


app = FastAPI(title="AIGameMall API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_results_router, prefix="/api/v1")
app.include_router(accounts_router, prefix="/api/v1")
