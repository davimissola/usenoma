import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.modules.auth.routes import router as auth_router
from app.modules.products.routes import router as products_router
from app.modules.stores.routes import router as stores_router
from app.modules.users.routes import router as users_router


logger = logging.getLogger(__name__)


app = FastAPI(title='Noma')
app.add_middleware(
	CORSMiddleware, 
	allow_origins=[settings.frontend_url], 
	allow_credentials=True, 
	allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
	allow_headers=['Authorization', 'Content-Type']
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
	# Não devolve input ou ctx: eles podem conter a senha ou o corpo inteiro da requisição.
	detail = [{'loc': item['loc'], 'msg': item['msg'], 'type': item['type']} for item in error.errors()]

	return JSONResponse(status_code=422, content={'detail': detail}, headers={'Cache-Control': 'no-store'})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, error: SQLAlchemyError) -> JSONResponse:
	# Registra somente o tipo do erro, sem SQL, parâmetros ou credenciais da conexão.
	logger.error('Falha no banco de dados: %s (%s)', type(error).__name__, type(getattr(error, 'orig', None)).__name__)
	return JSONResponse(status_code=503, content={'detail': 'Não foi possível concluir a operação. Tente novamente.'}, headers={'Cache-Control': 'no-store'})


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(stores_router)
app.include_router(products_router)
