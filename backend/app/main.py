from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.routes import router as auth_router
from app.modules.users.routes import router as users_router


app = FastAPI(title='Noma')
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])

app.include_router(auth_router)
app.include_router(users_router)
