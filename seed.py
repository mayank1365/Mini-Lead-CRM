from datetime import datetime, timezone
from app.database import Base, SessionLocal, engine
from app.models import Lead, LeadStatus


def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if database is already seeded
        lead_count = db.query(Lead).count()
        if lead_count > 0:
            print(f"Database already contains {lead_count} leads. Skipping seeding.")
            return

        print("Seeding database with sample leads...")
        sample_leads = [
            Lead(
                name="Aman Gupta",
                email="aman@example.com",
                phone="+91-9876543210",
                status=LeadStatus.NEW,
                source="website",
            ),
            Lead(
                name="Priya Sharma",
                email="priya@example.com",
                phone="+91-9988776655",
                status=LeadStatus.CONTACTED,
                source="referral",
            ),
            Lead(
                name="Rohan Mehta",
                email="rohan@example.com",
                phone="+91-9123456789",
                status=LeadStatus.QUALIFIED,
                source="campaign",
            ),
            Lead(
                name="Sneha Patel",
                email="sneha@example.com",
                phone="+91-8877665544",
                status=LeadStatus.CONVERTED,
                source="website",
            ),
            Lead(
                name="Vikram Singh",
                email="vikram@example.com",
                phone="+91-7766554433",
                status=LeadStatus.LOST,
                source="referral",
            ),
        ]

        db.add_all(sample_leads)
        db.commit()
        print(f"Successfully seeded {len(sample_leads)} leads into the database.")
    except Exception as e:
        print(f"An error occurred while seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
