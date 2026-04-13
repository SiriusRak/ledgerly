# PLACEHOLDER -- replaced in step 6
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/queue")
async def queue_page(request: Request):
    return templates.TemplateResponse("queue.html", {"request": request, "active_tab": "queue"})
