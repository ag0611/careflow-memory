"""Synthetic demo data with planted problems. No real patients. Dates are relative to today."""
from datetime import date, timedelta

from . import audit, db, service

NAMES = ["Meera Iyer", "Arjun Deshmukh", "Fatima Sheikh", "Karthik Reddy", "Sunita Verma", "Imran Qureshi",
         "Lakshmi Menon", "Rohan Kulkarni", "Ananya Bose", "Gurpreet Singh", "Deepa Nambiar", "Vikram Joshi"]

# id, kind, patient no., dept, title, status, priority, due (days from today), last updated (days ago)
ITEMS = [
    ("TSK-001", "task", 1, "General Medicine", "Call back about rescheduled consultation", "Open", 2, -2, 3),
    ("TSK-002", "task", 2, "Cardiology", "Collect signed consent form", "Open", 3, 2, 1),
    ("TSK-003", "task", 3, "Orthopaedics", "Confirm wheelchair assistance for visit", "Open", 3, 0, 1),
    ("TSK-004", "task", 4, "Radiology", "Share scan preparation leaflet", "Open", 2, -1, 2),
    ("TSK-005", "task", 5, "Neurology", "Update insurance contact number", "Open", 3, 4, 2),
    ("REF-001", "referral", 6, "Cardiology", "Referral to cardiac rehab", "Sent", 1, -3, 9),
    ("REF-002", "referral", 2, "Neurology", "Referral to neurology outpatient clinic", "Acknowledged", 2, 1, 2),
    ("REF-003", "referral", 7, "Orthopaedics", "Referral to physiotherapy", "Created", 2, -1, 7),
    ("REF-004", "referral", 8, "Radiology", "Referral for CT scan slot", "Scheduled", 3, 3, 1),
    ("REF-005", "referral", 9, "Paediatrics", "Referral to paediatric dietitian", "Sent", 2, 2, 6),
    ("REF-006", "referral", 3, "Cardiology", "Referral to echo clinic", "Completed", 3, -5, 4),
    ("FUP-001", "followup", 1, "General Medicine", "Book two-week follow-up", "Open", 1, -4, 4),
    ("FUP-002", "followup", 10, "Paediatrics", "Book vaccination follow-up", "Open", 2, 1, 1),
    ("FUP-003", "followup", 4, "Radiology", "Book review appointment after scan", "Open", 2, 0, 1),
    ("FUP-004", "followup", 11, "Neurology", "Confirm follow-up slot", "Open", 2, -2, 5),
    ("FUP-005", "followup", 5, "Orthopaedics", "Book cast-check appointment", "Done", 3, -1, 2),
    ("RPT-001", "report", 2, "Cardiology", "Awaiting ECG report, patient needs call-back", "Awaiting", 1, -1, 4),
    ("RPT-002", "report", 6, "General Medicine", "Awaiting blood test report", "Awaiting", 2, 1, 2),
    ("RPT-003", "report", 12, "Radiology", "Awaiting X-ray report", "Awaiting", 2, 2, 1),
    ("RPT-004", "report", 8, "Neurology", "Awaiting EEG report", "Awaiting", 2, -3, 6),
    ("RPT-005", "report", 9, "Paediatrics", "Awaiting lab report", "Awaiting", 3, 3, 1),
]
# Ground truth for the demo set (after the post-handover changes below). Used by tests and the README results.
PLANTED_OVERDUE = {"TSK-001", "TSK-004", "REF-001", "REF-003", "FUP-001", "FUP-004", "RPT-001", "RPT-004", "RPT-002"}
PLANTED_STUCK = {"REF-001", "REF-003", "REF-005"}


def _d(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def _wipe() -> None:
    with db.tx() as c:
        for t in ("patients", "items", "notes", "audit", "handovers", "proposals", "llm_calls"):
            c.execute(f"DELETE FROM {t}")
        c.execute("DELETE FROM sqlite_sequence")


def reset() -> None:
    db.init()
    _wipe()
    for n, name in enumerate(NAMES, 1):
        db.x("INSERT INTO patients VALUES (?,?)", (f"PATIENT_{n:03d}", name))
    for id_, kind, p, dept, title, status, prio, due, age in ITEMS:
        db.x("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?)",
             (id_, kind, f"PATIENT_{p:03d}", dept, title, status, prio, _d(due), _d(-age - 2), _d(-age)))
        audit.log("System (seed)", "create_item", id_, "", title)
    service.build_handover("Rahul Verma (Nurse)", narrate_text=False, seed=True)  # the previous shift's handover
    # What happened after that handover: this is what the "since last shift" diff shows.
    nurse, coord = "Rahul Verma (Nurse)", "Priya Nair (Coordinator)"
    db.x("UPDATE items SET status='Done', updated_at=? WHERE id='TSK-003'", (_d(0),))
    audit.log(nurse, "update_status", "TSK-003", "Open", "Done")
    db.x("UPDATE items SET status='Scheduled', updated_at=? WHERE id='REF-002'", (_d(0),))
    audit.log(coord, "update_status", "REF-002", "Acknowledged", "Scheduled")
    db.x("UPDATE items SET due=?, updated_at=? WHERE id='RPT-002'", (_d(-1), _d(0)))
    audit.log(coord, "change_due_date", "RPT-002", _d(1), _d(-1))
    db.x("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?)",
         ("TSK-006", "task", "PATIENT_007", "Orthopaedics", "Confirm discharge paperwork pickup", "Open", 2, _d(0), _d(0), _d(0)))
    audit.log(coord, "create_item", "TSK-006", "", "Confirm discharge paperwork pickup")
    nid = db.x("INSERT INTO notes(patient_id,text,author,created_at) VALUES (?,?,?,?)",
               ("PATIENT_003", "Hard of hearing on calls. Send an SMS first, then phone.", coord, audit.now()))
    audit.log(coord, "add_note", f"NOTE-{nid}", "", "Hard of hearing on calls. Send an SMS first, then phone.")


def ensure() -> None:
    db.init()
    if not db.one("SELECT 1 x FROM items LIMIT 1"):
        reset()
