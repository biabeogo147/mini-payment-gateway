from fastapi import FastAPI

from app.controllers.errors import app_error_handler
from app.controllers.health_controller import router as health_router
from app.controllers.payment_controller import router as payment_router
from app.controllers.provider_callback_controller import router as provider_callback_router
from app.controllers.refund_controller import router as refund_router
from app.controllers.webhook_ops_controller import router as webhook_ops_router
from app.core.errors import AppError

app = FastAPI(title="Mini Payment Gateway", version="0.1.0")

app.add_exception_handler(AppError, app_error_handler)
app.include_router(health_router)
app.include_router(payment_router)
app.include_router(refund_router)
app.include_router(provider_callback_router)
app.include_router(webhook_ops_router)
