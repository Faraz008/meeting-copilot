from copilot.models import Flag


def action_flags(
    *,
    status,
    owner,
    deadline_raw,
    deadline_status,
    condition,
    confidence_label,
    existing,
):
    f = set(existing)
    if status == "proposed":
        f.add(Flag.PROPOSED_NOT_COMMITTED)
    if owner is None and Flag.AMBIGUOUS_OWNER not in f:
        f.add(Flag.NO_OWNER)
    if status == "committed" and not deadline_raw:
        f.add(Flag.NO_DEADLINE)
    if deadline_raw and deadline_status == "unresolvable":
        f.add(Flag.UNRESOLVED_DEADLINE)
    if deadline_status == "ambiguous":
        f.add(Flag.AMBIGUOUS_DEADLINE)
    if condition:
        f.add(Flag.CONDITIONAL)
    if confidence_label == "low":
        f.add(Flag.LOW_CONFIDENCE)
    return sorted(f, key=lambda x: x.value)
