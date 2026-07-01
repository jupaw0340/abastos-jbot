from app.models.models import Order, Product, SystemState


PRICE_TYPE_LABELS = {
    "kg_suelto": "Kg suelto",
    "kg_10plus": "10kg o mas",
    "bulk": "Arpilla/bulto/caja",
}


def get_price_type_label(price_type: str) -> str:
    return PRICE_TYPE_LABELS.get(price_type, price_type)


def get_unit_price(product: Product, price_type: str) -> float:
    if price_type == "kg_suelto":
        return float(product.price_kg_loose)
    if price_type == "kg_10plus":
        return float(product.price_kg_10plus)
    return float(product.price_kg_bulk)


def recalculate_order(order: Order, db) -> Order:
    total = 0

    for item in order.items:
        product = db.get(Product, item.product_id) if item.product_id else None

        if not product:
            item.unit_price = 0
            item.subtotal = 0
            continue

        unit_price = get_unit_price(product, item.price_type)
        subtotal = float(item.quantity) * unit_price

        item.product_name = product.name
        item.unit_price = unit_price
        item.subtotal = subtotal
        total += subtotal

    order.total = total
    order.has_prices = True
    order.in_queue = False
    return order


def recalculate_open_orders(db, warehouse_id: int) -> int:
    orders = (
        db.query(Order)
        .filter(Order.warehouse_id == warehouse_id)
        .filter(Order.status.in_(["pendiente", "listo"]))
        .all()
    )

    for order in orders:
        recalculate_order(order, db)

    db.commit()
    return len(orders)


def close_order_day(db, warehouse_id: int) -> SystemState:
    state = db.query(SystemState).filter_by(warehouse_id=warehouse_id).first()
    state.orders_open = False
    state.prices_confirmed = False
    db.commit()
    return state


def open_order_day(db, warehouse_id: int) -> SystemState:
    state = db.query(SystemState).filter_by(warehouse_id=warehouse_id).first()
    state.orders_open = True
    state.prices_confirmed = True

    queued = db.query(Order).filter_by(warehouse_id=warehouse_id, in_queue=True).all()
    for order in queued:
        order.in_queue = False
        order.has_prices = True

    db.commit()
    recalculate_open_orders(db, warehouse_id)
    return state
