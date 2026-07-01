from app.db.database import Base, engine, SessionLocal
from app.models.models import Warehouse, Product, SystemState
from app.core.config import settings


PRODUCTS = [
    ("Serrano", "arpÃ­a/bulto"),
    ("JalapeÃ±o", "arpÃ­a/bulto"),
    ("Poblano", "arpÃ­a/bulto"),
    ("GÃ¼ero", "caja"),
    ("Caloro", "arpÃ­a/bulto"),
    ("Chilaca", "arpÃ­a/bulto"),
    ("Habanero", "caja"),
    ("Cebolla blanca", "arpÃ­a/bulto"),
    ("Cebolla morada", "arpÃ­a/bulto"),
    ("Tomate", "arpÃ­a/bulto"),
    ("Ajos", "caja"),
    ("Pimientos de color", "caja"),
    ("Pimientos verdes", "caja"),
    ("Perones", "arpÃ­a/bulto"),
]


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        warehouse = db.query(Warehouse).first()
        if not warehouse:
            warehouse = Warehouse(name=settings.WAREHOUSE_NAME)
            db.add(warehouse)
            db.commit()
            db.refresh(warehouse)

        state = db.query(SystemState).filter_by(warehouse_id=warehouse.id).first()
        if not state:
            db.add(SystemState(warehouse_id=warehouse.id))
            db.commit()

        for name, bulk_label in PRODUCTS:
            exists = db.query(Product).filter_by(warehouse_id=warehouse.id, name=name).first()
            if not exists:
                db.add(Product(
                    warehouse_id=warehouse.id,
                    name=name,
                    bulk_label=bulk_label,
                    available=True,
                    price_kg_loose=0,
                    price_kg_10plus=0,
                    price_kg_bulk=0,
                ))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada.")


