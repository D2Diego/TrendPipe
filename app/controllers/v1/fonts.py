from fastapi import Request
from pydantic import BaseModel

from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.services import fonts
from app.utils import utils

router = new_router()


class FontSupportRequest(BaseModel):
    font_name: str
    text: str


@router.get("/fonts", summary="List subtitle fonts available on the server")
def list_fonts_endpoint(request: Request):
    return utils.get_response(200, {"fonts": fonts.list_fonts()})


@router.post("/fonts/support", summary="Check whether a subtitle font supports text")
def check_font_support(request: Request, body: FontSupportRequest):
    try:
        supported = fonts.supports_text(body.font_name, body.text)
    except ValueError as exc:
        raise HttpException(task_id="", status_code=400, message=str(exc))
    return utils.get_response(200, {"supported": supported})
