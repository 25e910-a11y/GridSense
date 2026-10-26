"""
Database Seeding Script for IoT Power Monitoring & Fault Identification System.
Seeds:
- Hierarchy: College -> Blocks -> Floors
- Devices: Main Substation Unit (XIAO-PM-001) and Feeder Monitor (XIAO-PM-002)
- Relays: 3-Phase Solid State Relays (SSR-R, SSR-Y, SSR-B) on GPIO 7, 8, 9
- Initial 3-Phase Telemetry: Nominal balanced telemetry for Phases R, Y, and B
- Role Accounts: Operator, Shift In-Charge, Electrical Engineer, Management, Technician, Admin
- Sample Fault & Maintenance Work Order
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add backend directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.database import SessionLocal, engine, Base
from app.models.college import College
from app.models.block import Block
from app.models.floor import Floor
from app.models.device import Device
from app.models.relay import Relay
from app.models.telemetry import Telemetry
from app.models.fault import Fault
from app.models.work_order import WorkOrder, WorkAttempt
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.models.user import User
from app.core.security import ensure_initial_admin, hash_password


def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("Checking existing records...")
        now = datetime.now(timezone.utc)

        # 1. College
        college = db.query(College).first()
        if not college:
            college = College(
                name="Government Engineering College",
                code="GEC-01",
            )
            db.add(college)
            db.flush()
            print(f"Created College: {college.name}")

        # 2. Blocks
        block_admin = db.query(Block).filter(Block.name == "Main Administrative Block").first()
        if not block_admin:
            block_admin = Block(
                college_id=college.id,
                name="Main Administrative Block",
                code="BLK-ADMIN",
                description="Substation distribution panel and administrative offices",
            )
            db.add(block_admin)

        block_ee = db.query(Block).filter(Block.name == "Electrical Engineering Block").first()
        if not block_ee:
            block_ee = Block(
                college_id=college.id,
                name="Electrical Engineering Block",
                code="BLK-EE",
                description="High Voltage & Power Systems Laboratory",
            )
            db.add(block_ee)
        db.flush()

        # 3. Floors
        floor_substation = db.query(Floor).filter(Floor.name == "Ground Floor Substation Panel").first()
        if not floor_substation:
            floor_substation = Floor(
                block_id=block_admin.id,
                floor_number=0,
                name="Ground Floor Substation Panel",
                description="Main 3-phase 4-wire incomer distribution panel",
            )
            db.add(floor_substation)

        floor_ee_lab = db.query(Floor).filter(Floor.name == "1st Floor Power Systems Lab").first()
        if not floor_ee_lab:
            floor_ee_lab = Floor(
                block_id=block_ee.id,
                floor_number=1,
                name="1st Floor Power Systems Lab",
                description="Laboratory Feeder panel 02",
            )
            db.add(floor_ee_lab)
        db.flush()

        # 4. Devices
        dev1 = db.query(Device).filter(Device.device_id == "XIAO-PM-001").first()
        if not dev1:
            dev1 = Device(
                device_id="XIAO-PM-001",
                name="Power Monitoring Unit 01 (Main Incomer)",
                floor_id=floor_substation.id,
                location="Admin Substation Switchgear 1A",
                firmware_version="v1.0.4-esp32s3",
                is_active=True,
                last_seen_at=now,
            )
            db.add(dev1)
        else:
            dev1.name = "Power Monitoring Unit 01 (Main Incomer)"
            dev1.floor_id = floor_substation.id
            dev1.last_seen_at = now

        dev2 = db.query(Device).filter(Device.device_id == "XIAO-PM-002").first()
        if not dev2:
            dev2 = Device(
                device_id="XIAO-PM-002",
                name="Feeder Monitor 02 (EE Power Lab)",
                floor_id=floor_ee_lab.id,
                location="EE Block Floor 1 Panel 2B",
                firmware_version="v1.0.4-esp32s3",
                is_active=True,
                last_seen_at=now,
            )
            db.add(dev2)
        db.flush()

        # 5. Relays (SSR-R, SSR-Y, SSR-B on GPIO 7, 8, 9)
        existing_relays = db.query(Relay).filter(Relay.device_id == dev1.id).all()
        if not existing_relays:
            relay_configs = [
                (1, "Phase R Solid-State Contactor (SSR-R)", 7),
                (2, "Phase Y Solid-State Contactor (SSR-Y)", 8),
                (3, "Phase B Solid-State Contactor (SSR-B)", 9),
            ]
            for num, name, pin in relay_configs:
                relay = Relay(
                    device_id=dev1.id,
                    relay_number=num,
                    name=name,
                    gpio_pin=pin,
                    commanded_state=True,
                    actual_state=None,
                    is_on=True,
                    is_active=True,
                )
                db.add(relay)
            print("Seeded SSR relays on GPIO 7, 8, 9")

        # 6. Telemetry: ensure all 3 phases (R, Y, B) exist so dashboard computes 'Normal'
        sample_time = now - timedelta(seconds=10)
        phase_data = [
            ("R", 230.4, 4.35, 982.0, 142.68, 0.98, 50.02, 34.6),
            ("Y", 229.6, 4.28, 963.0, 141.95, 0.98, 50.01, 34.9),
            ("B", 231.2, 4.41, 1001.0, 143.12, 0.98, 50.02, 35.1),
        ]

        for phase, v, c, p, e, pf, freq, temp in phase_data:
            telem = Telemetry(
                device_id=dev1.id,
                phase=phase,
                voltage=v,
                current=c,
                power=p,
                energy=e,
                power_factor=pf,
                frequency=freq,
                temperature=temp,
                sampled_at=sample_time,
                received_at=now,
                sampling_interval_ms=1000,
                transmission_reason="SCHEDULED",
                source="REAL",
                data_quality="GOOD",
            )
            db.add(telem)

        # 7. Audit log entry
        audit = AuditLog(
            actor="system_seeder",
            action="database_seeded",
            entity_type="system",
            entity_id=dev1.id,
            detail="Seeded campus hierarchy, devices, SSR relays, and 3-phase telemetry.",
            created_at=now,
        )
        db.add(audit)

        # 8. Seed Role Accounts
        ensure_initial_admin(db)

        # Operator 1: Scoped to Admin Block (Block 1)
        op1 = db.query(User).filter(User.username == "operator1").first()
        if not op1:
            db.add(User(
                username="operator1",
                password_hash=hash_password("operator123"),
                role="operator",
                assigned_block_id=block_admin.id,
                is_active=True,
                created_at=now,
            ))
        elif op1.assigned_block_id is None:
            op1.assigned_block_id = block_admin.id

        # Shift In-Charge 1: Scoped to Admin Block (Block 1)
        shift1 = db.query(User).filter(User.username == "shift_incharge1").first()
        if not shift1:
            db.add(User(
                username="shift_incharge1",
                password_hash=hash_password("shift123"),
                role="shift_incharge",
                assigned_block_id=block_admin.id,
                is_active=True,
                created_at=now,
            ))

        # Electrical Engineer 1: Campus-wide technical investigation
        eng1 = db.query(User).filter(User.username == "engineer1").first()
        if not eng1:
            db.add(User(
                username="engineer1",
                password_hash=hash_password("engineer123"),
                role="electrical_engineer",
                is_active=True,
                created_at=now,
            ))

        # Management 1: Campus-wide read-only aggregate oversight
        mgmt1 = db.query(User).filter(User.username == "mgmt1").first()
        if not mgmt1:
            db.add(User(
                username="mgmt1",
                password_hash=hash_password("mgmt123"),
                role="management",
                is_active=True,
                created_at=now,
            ))

        # Technician 1: Primary maintenance tech
        tech1 = db.query(User).filter(User.username == "technician1").first()
        if not tech1:
            db.add(User(
                username="technician1",
                password_hash=hash_password("tech123"),
                role="technician",
                is_active=True,
                created_at=now,
            ))

        # Technician 2: Secondary maintenance tech (used to verify work order isolation)
        tech2 = db.query(User).filter(User.username == "technician2").first()
        if not tech2:
            db.add(User(
                username="technician2",
                password_hash=hash_password("tech123"),
                role="technician",
                is_active=True,
                created_at=now,
            ))

        # 9. Seed Sample Fault and Work Order if none exist
        if not db.query(Fault).filter(Fault.device_id == dev1.id).first():
            sample_fault = Fault(
                device_id=dev1.id,
                phase="Y",
                fault_type="Overcurrent Alert",
                severity="warning",
                category="electrical",
                measured_value=34.2,
                expected_value=32.0,
                unit="A",
                description="Phase Y current (34.2A) exceeded nominal threshold (32.0A) during peak load",
                status="detected",
                detected_at=now - timedelta(minutes=15),
            )
            db.add(sample_fault)
            db.flush()

            sample_wo = WorkOrder(
                fault_id=sample_fault.id,
                assigned_to="technician1",
                status="assigned",
                diagnosis="Inspect Phase Y sub-panel contactors and feeder balance",
                created_by="shift_incharge1",
                created_at=now - timedelta(minutes=10),
            )
            db.add(sample_wo)
            print("Seeded sample fault and maintenance work order for demonstration")

        db.commit()
        print("Database successfully seeded with realistic 3-phase power monitoring data and full role accounts!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
