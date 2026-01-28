from db.database import SessionLocal
from db.models import Lead, Workflow

def save_lead(data):
    db = SessionLocal()
    lead = Lead(**data)
    db.add(lead)
    db.commit()
    return lead.id

def save_workflow(call_sid, lead_id, state, paused=False, resume_at=None):
    db = SessionLocal()
    wf = Workflow(
        call_sid=call_sid,
        lead_id=lead_id,
        state=state,
        is_paused=paused,
        status="paused" if paused else "running",
        resume_at=resume_at,
        current_node=state.get("current_node"),
        waiting_for=state.get("waiting_for")  # optional
    )

    db.merge(wf)   # call_sid unique 
    db.commit()


def load_workflow(call_sid):
    db = SessionLocal()
    return db.query(Workflow).filter_by(call_sid=call_sid).first()

