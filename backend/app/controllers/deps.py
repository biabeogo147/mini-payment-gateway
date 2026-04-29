from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.auth import AuthenticatedMerchant
from app.services.auth_service import authenticate_merchant_request


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_authenticated_merchant(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthenticatedMerchant:
    body = await request.body()
    return authenticate_merchant_request(
        db=db,
        method=request.method,
        path=request.url.path,
        body=body,
        headers=request.headers,
    )
