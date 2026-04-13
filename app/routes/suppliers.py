# PLACEHOLDER -- replaced in step 8
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/suppliers")
async def suppliers_page(request: Request):
    return templates.TemplateResponse("suppliers.html", {"request": request, "active_tab": "suppliers"})
