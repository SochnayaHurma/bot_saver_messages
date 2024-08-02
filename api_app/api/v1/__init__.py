from fastapi import APIRouter

from api.v1.message import router as message_router

router = APIRouter(prefix='/v1')
router.include_router(message_router)
