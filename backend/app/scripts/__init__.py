import app.models  # noqa: F401
from app.database.connection import Base, SessionLocal, engine
from app.database.seed import seed_categories


def main() -> None:
    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    print("Seeding default categories...")

    with SessionLocal() as db:
        seed_categories(db)

    print("Database initialization completed.")
    print(f"Database location: {engine.url.database}")


if __name__ == "__main__":
    main()
