from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.models.models import Product, Order, OrderItem, Customer, Warehouse, SystemState
from app.services.order_service import recalculate_order


SESSIONS = {}
SESSION_TTL_MINUTES = 20

PRICE_TYPE_LABELS = {
    "kg_suelto": "Kg suelto",
    "kg_10plus": "10kg o más",
    "bulk": "Arpilla/bulto/caja",
}


def normalize(text: str) -> str:
    return (text or "").lower().strip()


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def get_text_from_message(message: dict) -> str:
    if message.get("type") == "text":
        return message.get("text", {}).get("body", "").strip()
    return ""


def get_main_warehouse(db):
    return db.query(Warehouse).first()


def get_state(db, warehouse_id: int):
    return db.query(SystemState).filter_by(warehouse_id=warehouse_id).first()


def get_or_create_customer(db, phone: str):
    phone = normalize_phone(phone)
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    if customer:
        return customer

    customer = Customer(
        phone=phone,
        display_name=phone,
        default_delivery_place=None,
        notes="Creado desde WhatsApp",
        is_active=True,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def customer_needs_name(customer: Customer) -> bool:
    return customer.display_name == customer.phone or customer.display_name.isdigit()


def start_session(phone: str, step: str = "menu"):
    SESSIONS[phone] = {
        "step": step,
        "items": [],
        "updated_at": datetime.utcnow(),
    }


def is_session_expired(session: dict) -> bool:
    updated_at = session.get("updated_at")
    if not updated_at:
        return True
    return datetime.utcnow() - updated_at > timedelta(minutes=SESSION_TTL_MINUTES)


def touch_session(phone: str):
    if phone in SESSIONS:
        SESSIONS[phone]["updated_at"] = datetime.utcnow()


def menu_text() -> str:
    return (
        "Hola 👋\n"
        "Soy *Abastos JBot*.\n\n"
        "Elige una opción:\n\n"
        "1. Hacer pedido\n"
        "2. Ver mis pedidos pendientes\n\n"
        "Responde con el número."
    )


def get_available_products(db, warehouse_id: int):
    return (
        db.query(Product)
        .filter_by(warehouse_id=warehouse_id, available=True)
        .order_by(Product.id)
        .all()
    )


def products_text(db, warehouse_id: int) -> str:
    products = get_available_products(db, warehouse_id)

    if not products:
        return "Por ahora no hay productos disponibles."

    lines = ["🌶️ *Productos disponibles*"]
    for p in products:
        lines.append(f"{p.id}. {p.name}")

    lines.append("\n0. Finalizar pedido")
    lines.append("\nResponde con el número del producto.")
    return "\n".join(lines)


def pending_orders_text(db, customer: Customer) -> str:
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id)
        .filter(Order.status.in_(["pendiente", "listo"]))
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    if not orders:
        return "No tienes pedidos pendientes."

    lines = ["Tus pedidos pendientes:"]
    for o in orders:
        lines.append(f"Folio #{o.folio} - {o.status} - ${o.total}")

    return "\n".join(lines)


def cart_summary(session: dict) -> str:
    if not session.get("items"):
        return "Tu pedido está vacío."

    lines = ["🧾 *Resumen del pedido*"]
    for idx, item in enumerate(session["items"], start=1):
        label = PRICE_TYPE_LABELS.get(item["price_type"], item["price_type"])
        lines.append(f"{idx}. {item['product_name']} - {item['quantity']} - {label}")

    delivery = session.get("delivery_place") or "Recoge en bodega"
    lines.append(f"\nEntrega/recoge: {delivery}")
    lines.append("\nResponde:")
    lines.append("*confirmar* para registrar")
    lines.append("*agregar* para agregar otro producto")
    lines.append("*cancelar* para cancelar")

    return "\n".join(lines)


def get_next_folio(db, warehouse_id: int) -> int:
    state = get_state(db, warehouse_id)
    folio = state.current_folio
    state.current_folio += 1
    db.commit()
    return folio


def create_order_from_session(db, phone: str):
    session = SESSIONS.get(phone, {})
    warehouse = get_main_warehouse(db)
    state = get_state(db, warehouse.id)
    customer = get_or_create_customer(db, phone)

    order = Order(
        folio=get_next_folio(db, warehouse.id),
        warehouse_id=warehouse.id,
        customer_id=customer.id,
        customer_name=customer.display_name,
        delivery_place=session.get("delivery_place") or None,
        pickup=False if session.get("delivery_place") else True,
        status="pendiente",
        payment_status="pendiente",
        in_queue=not state.orders_open,
        has_prices=state.orders_open,
        total=0,
    )

    for item in session.get("items", []):
        product = db.get(Product, item["product_id"])
        if not product:
            continue

        order.items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            price_type=item["price_type"],
            quantity=item["quantity"],
            unit_price=0,
            subtotal=0,
        ))

    db.add(order)
    db.flush()

    if state.orders_open:
        recalculate_order(order, db)

    db.commit()
    db.refresh(order)
    return order


def handle_incoming_text(phone: str, text: str) -> str:
    db = SessionLocal()
    try:
        warehouse = get_main_warehouse(db)
        customer = get_or_create_customer(db, phone)
        lower = normalize(text)

        if phone in SESSIONS and is_session_expired(SESSIONS[phone]):
            SESSIONS.pop(phone, None)

        if lower in ["hola", "menu", "menú", "inicio", "empezar"]:
            start_session(phone, "menu")
            return menu_text()

        if lower in ["cancelar", "salir"]:
            SESSIONS.pop(phone, None)
            return "Listo, cancelé el proceso actual. Escribe *menu* para empezar otra vez."

        if phone not in SESSIONS:
            start_session(phone, "menu")

        touch_session(phone)
        session = SESSIONS[phone]
        step = session.get("step")

        if step == "menu":
            if lower in ["1", "pedido", "hacer pedido", "comprar"]:
                if customer_needs_name(customer):
                    session["step"] = "ask_name"
                    return "¿A nombre de quién será el pedido?"

                session["step"] = "ask_delivery"
                return (
                    f"Pedido a nombre de *{customer.display_name}*.\n\n"
                    "¿Será entregado en alguna bodega del mercado?\n"
                    "Responde *si* o *no*."
                )

            if lower == "2":
                return pending_orders_text(db, customer)

            return menu_text()

        if step == "ask_name":
            session["pending_customer_name"] = text.strip()
            session["step"] = "confirm_name"
            return (
                f"El pedido quedará a nombre de: *{session['pending_customer_name']}*\n\n"
                "¿Es correcto?\n"
                "Responde *si* para confirmar o escribe el nombre correcto."
            )

        if step == "confirm_name":
            if lower in ["si", "sí", "s", "correcto", "confirmar"]:
                customer.display_name = session["pending_customer_name"]
            else:
                customer.display_name = text.strip()

            customer.is_active = True
            db.commit()
            session["step"] = "ask_delivery"
            return (
                f"Perfecto, pedido a nombre de *{customer.display_name}*.\n\n"
                "¿Será entregado en alguna bodega del mercado?\n"
                "Si no se entrega en una bodega, su pedido lo estará esperando en nuestra bodega *Chiles Hernández*.\n\n"
                "Responde *si* o *no*."
            )

        if step == "ask_delivery":
            if lower in ["si", "sí", "s"]:
                session["step"] = "ask_delivery_place"
                return "Escribe el nombre de la bodega donde se entregará."

            if lower in ["no", "n"]:
                session["delivery_place"] = ""
                session["step"] = "choose_product"
                return products_text(db, warehouse.id)

            return "Responde *si* si se entrega en otra bodega o *no* si recoge en nuestra bodega."

        if step == "ask_delivery_place":
            session["pending_delivery_place"] = text.strip()
            session["step"] = "confirm_delivery_place"
            return (
                f"La entrega será en: *{session['pending_delivery_place']}*\n\n"
                "¿Es correcto?\n"
                "Responde *si* para confirmar o escribe la bodega correcta."
            )

        if step == "confirm_delivery_place":
            if lower in ["si", "sí", "s", "correcto", "confirmar"]:
                session["delivery_place"] = session["pending_delivery_place"]
            else:
                session["delivery_place"] = text.strip()

            session["step"] = "choose_product"
            return products_text(db, warehouse.id)

        if step == "choose_product":
            if lower == "0":
                if not session.get("items"):
                    return "Tu pedido está vacío. Elige un producto primero."
                session["step"] = "confirm"
                return cart_summary(session)

            try:
                product_id = int(text.strip())
            except ValueError:
                return "Responde con el número del producto o 0 para finalizar."

            product = db.get(Product, product_id)
            if not product or not product.available:
                return "Ese producto no está disponible. Elige otro número."

            session["current_product_id"] = product.id
            session["current_product_name"] = product.name
            session["step"] = "choose_price_type"
            return (
                f"Elegiste *{product.name}*.\n\n"
                "Tipo de precio:\n"
                "1. Kg suelto\n"
                "2. 10kg o más\n"
                "3. Arpilla/bulto/caja\n\n"
                "Responde 1, 2 o 3."
            )

        if step == "choose_price_type":
            mapping = {
                "1": "kg_suelto",
                "2": "kg_10plus",
                "3": "bulk",
            }

            if lower not in mapping:
                return "Responde 1, 2 o 3."

            session["current_price_type"] = mapping[lower]
            session["step"] = "ask_quantity"

            if mapping[lower] == "bulk":
                return f"¿Cuántas arpillas/bultos/cajas de *{session['current_product_name']}* quieres?"

            return f"¿Cuántos kg de *{session['current_product_name']}* quieres?"

        if step == "ask_quantity":
            try:
                quantity = float(text.strip())
            except ValueError:
                return "Escribe una cantidad válida. Ejemplo: 10"

            if quantity <= 0:
                return "La cantidad debe ser mayor a 0."

            if session["current_price_type"] == "kg_10plus" and quantity < 10:
                return "Ese precio es solo para 10kg o más. Escribe una cantidad de 10kg o más, o escribe *cancelar* para empezar de nuevo."

            session["items"].append({
                "product_id": session["current_product_id"],
                "product_name": session["current_product_name"],
                "price_type": session["current_price_type"],
                "quantity": quantity,
            })

            session["step"] = "choose_product"
            return (
                f"Agregado: *{quantity}* de *{session['current_product_name']}*.\n\n"
                + products_text(db, warehouse.id)
            )

        if step == "confirm":
            if lower == "agregar":
                session["step"] = "choose_product"
                return products_text(db, warehouse.id)

            if lower != "confirmar":
                return cart_summary(session)

            if not session.get("items"):
                session["step"] = "choose_product"
                return "Tu pedido está vacío. Elige un producto."

            order = create_order_from_session(db, phone)
            SESSIONS.pop(phone, None)

            queue_msg = ""
            if order.in_queue:
                queue_msg = "\n\nTu pedido quedó en fila y se procesará cuando se confirmen precios."

            return (
                f"✅ Pedido registrado correctamente.\n\n"
                f"Folio: *#{order.folio}*\n"
                f"Total: *${order.total}*"
                f"{queue_msg}\n\n"
                "Te avisaremos cuando esté listo."
            )

        return menu_text()

    finally:
        db.close()
