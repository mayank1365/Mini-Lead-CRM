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
        if lead_count > 10:
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
            Lead(
                name="Arjun Kapoor",
                email="arjun.k@example.com",
                phone="+91-9555443322",
                status=LeadStatus.NEW,
                source="linkedin",
            ),
            Lead(
                name="Ananya Iyer",
                email="ananya.i@example.com",
                phone="+91-9444332211",
                status=LeadStatus.CONTACTED,
                source="website",
            ),
            Lead(
                name="Siddharth Malhotra",
                email="sid.m@example.com",
                phone="+91-9333221100",
                status=LeadStatus.QUALIFIED,
                source="event",
            ),
            Lead(
                name="Ishani Verma",
                email="ishani.v@example.com",
                phone="+91-9222110099",
                status=LeadStatus.CONVERTED,
                source="referral",
            ),
            Lead(
                name="Kabir Das",
                email="kabir.d@example.com",
                phone="+91-9111009988",
                status=LeadStatus.NEW,
                source="campaign",
            ),
        ]

        for lead in sample_leads:
            # Check if lead with same email already exists before adding
            existing_lead = db.query(Lead).filter(Lead.email == lead.email).first()
            if not existing_lead:
                db.add(lead)
        
        db.commit()
        print("Successfully seeded unique leads into the database.")
    except Exception as e:
        print(f"An error occurred while seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
