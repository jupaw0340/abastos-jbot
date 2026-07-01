from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.models.models import Product, Order, OrderItem, SystemState, Warehouse
from app.core.config import settings
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def require_login(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    return None


def get_main_warehouse(db: Session):
    return db.query(Warehouse).first()


def get_state(db: Session, warehouse_id: int):
    state = db.query(SystemState).filter_by(warehouse_id=warehouse_id).first()
    if not state:
        state = SystemState(warehouse_id=warehouse_id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


@router.get("/admin", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect
    warehouse = get_main_warehouse(db)
    state = get_state(db, warehouse.id)
    pending_count = db.query(Order).filter(Order.warehouse_id == warehouse.id, Order.status == "pendiente").count()
    queue_count = db.query(Order).filter(Order.warehouse_id == warehouse.id, Order.in_queue == True).count()
    completed_count = db.query(Order).filter(Order.warehouse_id == warehouse.id, Order.status == "completado").count()
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "warehouse": warehouse,
        "state": state,
        "pending_count": pending_count,
        "queue_count": queue_count,
        "completed_count": completed_count,
        "app_name": settings.APP_NAME,
    })


@router.get("/admin/productos", response_class=HTMLResponse)
def products(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect
    warehouse = get_main_warehouse(db)
    items = db.query(Product).filter_by(warehouse_id=warehouse.id).order_by(Product.id).all()
    return templates.TemplateResponse(request, "products.html", {
        "request": request,
        "warehouse": warehouse,
        "products": items,
        "app_name": settings.APP_NAME,
    })


@router.post("/admin/productos/guardar")
def save_products(
    db: Session = Depends(get_db),
    product_ids: list[int] = Form(...),
    price_kg_loose: list[float] = Form(...),
    price_kg_10plus: list[float] = Form(...),
    price_kg_bulk: list[float] = Form(...),
    bulk_label: list[str] = Form(...),
    available: list[int] = Form(default=[]),
):
    available_set = set(int(x) for x in available)
    for i, product_id in enumerate(product_ids):
        product = db.get(Product, product_id)
        if not product:
            continue
        product.price_kg_loose = price_kg_loose[i]
        product.price_kg_10plus = price_kg_10plus[i]
        product.price_kg_bulk = price_kg_bulk[i]
        product.bulk_label = bulk_label[i]
        product.available = product_id in available_set
    db.commit()
    return RedirectResponse("/admin/productos", status_code=303)


@router.get("/admin/pedidos", response_class=HTMLResponse)
def orders(request: Request, status: str = "pendiente", db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect
    warehouse = get_main_warehouse(db)
    query = db.query(Order).options(joinedload(Order.items)).filter(Order.warehouse_id == warehouse.id)
    if status != "todos":
        query = query.filter(Order.status == status)
    items = query.order_by(Order.created_at.desc()).limit(100).all()
    return templates.TemplateResponse(request, "orders.html", {
        "request": request,
        "warehouse": warehouse,
        "orders": items,
        "status": status,
        "app_name": settings.APP_NAME,
    })


@router.post("/admin/pedidos/{order_id}/estado")
def update_order_status(
    order_id: int,
    status: str = Form(...),
    payment_status: str = Form(...),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order:
        order.status = status
        order.payment_status = payment_status
        db.commit()
    return RedirectResponse("/admin/pedidos?status=todos", status_code=303)


@router.post("/admin/estado/cerrar")
def close_orders(db: Session = Depends(get_db)):
    warehouse = get_main_warehouse(db)
    state = get_state(db, warehouse.id)
    state.orders_open = False
    state.prices_confirmed = False
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/estado/abrir")
def open_orders(db: Session = Depends(get_db)):
    warehouse = get_main_warehouse(db)
    state = get_state(db, warehouse.id)
    state.orders_open = True
    state.prices_confirmed = True
    queued = db.query(Order).filter_by(warehouse_id=warehouse.id, in_queue=True).all()
    for order in queued:
        order.in_queue = False
        order.has_prices = True
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/folio/reiniciar")
def reset_folio(value: int = Form(...), db: Session = Depends(get_db)):
    warehouse = get_main_warehouse(db)
    state = get_state(db, warehouse.id)
    state.current_folio = value
    db.commit()
    return RedirectResponse("/admin", status_code=303)


