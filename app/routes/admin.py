from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.models.models import Product, Order, OrderItem, SystemState, Warehouse
from app.core.config import settings
from app.services.order_service import recalculate_open_orders, recalculate_order, close_order_day, open_order_day
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
    available_status: list[int] = Form(...),
):
    for i, product_id in enumerate(product_ids):
        product_id = int(product_id)
        product = db.get(Product, product_id)
        if not product:
            continue

        product.price_kg_loose = price_kg_loose[i]
        product.price_kg_10plus = price_kg_10plus[i]
        product.price_kg_bulk = price_kg_bulk[i]
        product.bulk_label = bulk_label[i]
        product.available = bool(int(available_status[i]))
    db.commit()
    return RedirectResponse("/admin/productos", status_code=303)



@router.get("/admin/pedidos/nuevo", response_class=HTMLResponse)
def new_order_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    warehouse = get_main_warehouse(db)
    products = db.query(Product).filter_by(warehouse_id=warehouse.id, available=True).order_by(Product.id).all()
    return templates.TemplateResponse(request, "new_order.html", {
        "request": request,
        "warehouse": warehouse,
        "products": products,
        "app_name": settings.APP_NAME,
    })


@router.post("/admin/pedidos/nuevo")
def create_manual_order(
    request: Request,
    customer_name: str = Form(...),
    delivery_place: str = Form(""),
    product_ids: list[str] = Form(...),
    price_types: list[str] = Form(...),
    quantities: list[str] = Form(...),
    db: Session = Depends(get_db),
):
    redirect = require_login(request)
    if redirect:
        return redirect

    warehouse = get_main_warehouse(db)
    state = get_state(db, warehouse.id)

    order = Order(
        folio=state.current_folio,
        warehouse_id=warehouse.id,
        customer_name=customer_name.strip(),
        delivery_place=delivery_place.strip() or None,
        pickup=False if delivery_place.strip() else True,
        status="pendiente",
        payment_status="pendiente",
        in_queue=not state.orders_open,
        has_prices=state.orders_open,
        total=0,
    )

    total = 0

    for product_id, price_type, quantity_raw in zip(product_ids, price_types, quantities):
        if not product_id or not quantity_raw:
            continue

        try:
            quantity = float(quantity_raw)
        except ValueError:
            continue

        if quantity <= 0:
            continue

        product = db.get(Product, int(product_id))
        if not product:
            continue

        if not state.orders_open:
            unit_price = 0
        elif price_type == "kg_suelto":
            unit_price = float(product.price_kg_loose)
        elif price_type == "kg_10plus":
            unit_price = float(product.price_kg_10plus)
        else:
            unit_price = float(product.price_kg_bulk)

        subtotal = quantity * unit_price

        order.items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            price_type=price_type,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
        ))

        total += subtotal

    if not order.items:
        return RedirectResponse("/admin/pedidos/nuevo", status_code=303)

    order.total = total
    state.current_folio += 1

    db.add(order)
    db.flush()

    if state.orders_open:
        recalculate_order(order, db)

    db.commit()

    return RedirectResponse("/admin/pedidos?status=pendiente", status_code=303)


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




@router.get("/admin/pedidos/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    warehouse = get_main_warehouse(db)
    order = db.query(Order).options(joinedload(Order.items)).filter(Order.id == order_id).first()

    if not order:
        return RedirectResponse("/admin/pedidos?status=todos", status_code=303)

    return templates.TemplateResponse(request, "order_detail.html", {
        "request": request,
        "warehouse": warehouse,
        "order": order,
        "app_name": settings.APP_NAME,
    })


@router.post("/admin/pedidos/{order_id}/rapido")
def quick_order_status(
    order_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order:
        order.status = status
        db.commit()
    return RedirectResponse(f"/admin/pedidos/{order_id}", status_code=303)


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




@router.post("/admin/pedidos/recalcular")
def recalculate_orders(db: Session = Depends(get_db)):
    warehouse = get_main_warehouse(db)
    recalculate_open_orders(db, warehouse.id)
    return RedirectResponse("/admin/pedidos?status=todos", status_code=303)




@router.post("/admin/pedidos/{order_id}/eliminar")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order:
        db.delete(order)
        db.commit()
    return RedirectResponse("/admin/pedidos?status=todos", status_code=303)


@router.post("/admin/estado/cerrar")
def close_orders(db: Session = Depends(get_db)):
    warehouse = get_main_warehouse(db)
    close_order_day(db, warehouse.id)
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/estado/abrir")
def open_orders(db: Session = Depends(get_db)):
    warehouse = get_main_warehouse(db)
    open_order_day(db, warehouse.id)
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/folio/reiniciar")
def reset_folio(value: int = Form(...), db: Session = Depends(get_db)):
    warehouse = get_main_warehouse(db)
    state = get_state(db, warehouse.id)
    state.current_folio = value
    db.commit()
    return RedirectResponse("/admin", status_code=303)


