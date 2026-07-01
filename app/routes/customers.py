from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.models import Customer, Order, Warehouse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def require_login(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    return None


def get_main_warehouse(db: Session):
    return db.query(Warehouse).first()


@router.get("/admin/clientes", response_class=HTMLResponse)
def customers_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    warehouse = get_main_warehouse(db)
    customers = db.query(Customer).filter_by(is_active=True).order_by(Customer.display_name).all()

    return templates.TemplateResponse(request, "customers.html", {
        "request": request,
        "warehouse": warehouse,
        "customers": customers,
        "app_name": settings.APP_NAME,
    })


@router.post("/admin/clientes/nuevo")
def create_customer(
    display_name: str = Form(...),
    phone: str = Form(""),
    default_delivery_place: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    customer = Customer(
        display_name=display_name.strip(),
        phone=phone.strip() or None,
        default_delivery_place=default_delivery_place.strip() or None,
        notes=notes.strip() or None,
        is_active=True,
    )
    db.add(customer)
    db.commit()
    return RedirectResponse("/admin/clientes", status_code=303)


@router.get("/admin/clientes/{customer_id}", response_class=HTMLResponse)
def customer_detail(customer_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    warehouse = get_main_warehouse(db)
    customer = db.get(Customer, customer_id)

    if not customer:
        return RedirectResponse("/admin/clientes", status_code=303)

    orders = (
        db.query(Order)
        .filter(Order.customer_name == customer.display_name)
        .order_by(Order.created_at.desc())
        .limit(50)
        .all()
    )

    total = sum(float(o.total or 0) for o in orders)

    return templates.TemplateResponse(request, "customer_detail.html", {
        "request": request,
        "warehouse": warehouse,
        "customer": customer,
        "orders": orders,
        "total": total,
        "app_name": settings.APP_NAME,
    })
