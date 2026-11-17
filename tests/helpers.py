from datetime import date

from copilot.models import ActionItem, Evidence, ExtractionResult, Meeting, Turn


def seed(store, n: int = 1, approve: bool = True, mid: str = "m1"):
    turns = [
        Turn(idx=0, speaker="Priya", text="I'll send the draft by Friday."),
        Turn(idx=1, speaker="Sam", text="I'll fix the tags before launch."),
        Turn(idx=2, speaker="Dan", text="Okay, sounds good to me."),
    ]
    m = Meeting(
        meeting_id=mid,
        title="Pricing sync",
        date=date(2025, 3, 12),
        roster=["Priya", "Sam", "Dan"],
        turns=turns,
    )
    items = [
        ActionItem(
            id="act_1",
            title="Send pricing draft",
            owner="Priya",
            owner_raw="I",
            deadline=date(2025, 3, 14),
            deadline_raw="by Friday",
            confidence=0.9,
            evidence=[Evidence(turn_idx=0, quote="I'll send the draft by Friday.")],
        ),
        ActionItem(
            id="act_2",
            title="Fix analytics tags",
            owner="Sam",
            owner_raw="I",
            deadline_raw="before launch",
            confidence=0.8,
            flags=[
                "unresolved_deadline",
            ],
            evidence=[
                Evidence(
                    turn_idx=1,
                    quote="I'll fix the tags before launch.",
                )
            ],
        ),
    ][:n]
    store.begin_meeting(mid, m.title, m.date, "Asia/Kolkata")
    store.save_extraction(mid, ExtractionResult(action_items=items))
    store.finish_meeting(mid, "ok", meeting=m)
    if approve:
        for it in items:
            store.update_item(it.id, state="approved")
    return m
