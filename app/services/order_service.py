from app.models.models import Order, Product


PRICE_TYPE_LABELS = {
    "kg_suelto": "Kg suelto",
    "kg_10plus": "10kg o mas",
    "bulk": "Arpilla/bulto/caja",
}


def get_unit_price(product: Product, price_type: str) -> float:
    if price_type == "kg_suelto":
        return float(product.price_kg_loose)
    if price_type == "kg_10plus":
        return float(product.price_kg_10plus)
    return float(product.price_kg_bulk)


def recalculate_order(order: Order, db) -> Order:
    total = 0

    for item in order.items:
        if not item.product_id:
            item.unit_price = 0
            item.subtotal = 0
            continue

        product = db.get(Product, item.product_id)
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
