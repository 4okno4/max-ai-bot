from app.models.database import Base, engine, SessionLocal
from app.services.seed_service import seed_products

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    seed_products(db)
finally:
    db.close()