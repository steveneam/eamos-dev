from fastapi import APIRouter, Request

from app.core.db import ping_database

router = APIRouter(tags=['health'])


@router.get('/healthz')
def healthz(request: Request) -> dict[str, str]:
    ping_database(request.app.state.db_session_factory)
    return {'status': 'ok', 'database': 'ok'}
