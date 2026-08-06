from fastapi import APIRouter, Request

router = APIRouter()


@router.get(
    "/ping",
    tags=["Health Check"],
    description="Availability of inspection services",
    response_description="pong",
)
def ping(request: Request) -> str:
    return "pong"
