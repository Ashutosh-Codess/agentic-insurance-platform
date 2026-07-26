import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

current_dir = os.path.dirname(__file__)
repo_root = os.path.dirname(current_dir)

for path in (repo_root, current_dir):
	if path not in sys.path:
		sys.path.insert(0, path)

from app.api.router import api_router
from app.core.bootstrap import seed_demo_data
from app.core.config import settings
from app.core.database import initialize_database

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8000", "http://127.0.0.1:8000"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.on_event("startup")
def startup_event():
	initialize_database()
	seed_demo_data()
