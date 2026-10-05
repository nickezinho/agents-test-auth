from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Em ambiente de desenvolvimento local, inicializa as tabelas se ainda não existirem
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Limpeza de recursos
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Configuração estrita de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Set-Cookie"]
)


# Exception handler padronizado para exceções da aplicação
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "code": exc.code,
            "detail": exc.detail,
            "errors": exc.errors,
            "timestamp": exc.timestamp,
            "path": request.url.path
        }
    )


# Exception handler padronizado para erros de validação do Pydantic (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        formatted_errors.append({
            "field": field,
            "message": err.get("msg", "Erro de validação.")
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "detail": "Os dados fornecidos são inválidos.",
            "errors": formatted_errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path
        }
    )


# Inclusão de rotas
app.include_router(api_router, prefix="/api/v1")
