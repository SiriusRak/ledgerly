# PLACEHOLDER -- replaced in step 7
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request, "active_tab": "history"})
