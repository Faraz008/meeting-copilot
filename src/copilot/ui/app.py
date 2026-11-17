import json
from datetime import date
from zoneinfo import ZoneInfo

import streamlit as st

from copilot import service
from copilot.config import settings
from copilot.parsers.transcript import (
    GENERIC,
    build_roster,
    parse_transcript,
)
from copilot.store import Store
from copilot.ui import helpers as H
from copilot.validate.inputs import (
    InputError,
    estimate_calls,
    prepare_turns,
)

# ------------------------------------------------------------------
# Page configuration and application setup
# ------------------------------------------------------------------

st.set_page_config(
    page_title="Meeting Co-Pilot",
    page_icon="📝",
    layout="wide",
)

NEW = "➕ New meeting"

BADGE = {
    "approved": "✅",
    "rejected": "❌",
    "pending": "⏳",
}

store = Store()


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------


def sidebar() -> tuple[str, dict]:
    meetings = store.list_meetings()

    labels = {
        meeting["id"]: (
            f"{meeting['title'] or meeting['id']} · {meeting['date']} · {meeting['status']}"
        )
        for meeting in meetings
    }

    if "_goto" in st.session_state:
        st.session_state["meeting_sel"] = st.session_state.pop("_goto")

    st.session_state.setdefault(
        "meeting_sel",
        st.query_params.get("meeting") or NEW,
    )

    ids = [NEW] + list(labels)

    if st.session_state["meeting_sel"] not in ids:
        st.session_state["meeting_sel"] = NEW

    choice = st.sidebar.selectbox(
        "Meeting",
        ids,
        key="meeting_sel",
        format_func=lambda item: NEW if item == NEW else labels[item],
    )

    if choice == NEW:
        st.query_params.pop("meeting", None)
    else:
        st.query_params["meeting"] = choice

    st.sidebar.divider()
    st.sidebar.subheader("Privacy and provider")

    providers = service.configured_providers()

    provider = st.sidebar.selectbox(
        "LLM provider",
        ["(auto, with fallback)"] + providers,
    )

    local_only = st.sidebar.toggle(
        "Local-only (Ollama, nothing leaves this machine)",
        disabled="ollama" not in providers,
    )

    redact = st.sidebar.toggle(
        "Redact emails, phones, IDs before sending to a cloud LLM",
        disabled=local_only,
    )

    if settings.demo_mode:
        st.sidebar.warning("Demo mode: integrations are disabled. Use synthetic data only.")

    return choice, {
        "provider": (None if provider.startswith("(") else provider),
        "local_only": local_only,
        "redact": redact and not local_only,
    }


# ------------------------------------------------------------------
# New meeting
# ------------------------------------------------------------------


def render_new(opts: dict) -> None:
    st.header("New meeting")

    upload = st.file_uploader(
        "Transcript (.txt, .vtt, .srt)",
        type=["txt", "vtt", "srt"],
    )

    audio_expander()

    pasted = st.text_area(
        "…or paste a transcript",
        height=160,
        key="pasted",
    )

    raw = (
        upload.getvalue().decode(
            "utf-8",
            errors="replace",
        )
        if upload
        else pasted
    )

    col1, col2, col3 = st.columns(3)

    title = col1.text_input("Title")

    meeting_date = col2.date_input(
        "Meeting date",
        value=date.today(),
    )

    timezone = col3.text_input(
        "Timezone",
        "Asia/Kolkata",
    )

    if not raw.strip():
        st.info("Upload or paste a transcript to begin.")
        return

    try:
        ZoneInfo(timezone)

        turns, warnings = prepare_turns(parse_transcript(raw))

    except InputError as exc:
        st.error(str(exc))
        return

    except Exception as exc:
        st.error(f"Cannot use this input: {exc}")
        return

    for warning in warnings:
        st.warning(warning)

    labels = build_roster(turns)

    speaker_map: dict[str, str] = {}

    generic = [speaker for speaker in labels if GENERIC.match(speaker)]

    if generic:
        st.subheader("Name the speakers")

        samples = H.speaker_samples(turns)

        for speaker in generic:
            info = samples.get(speaker, {})

            name = st.text_input(
                f"{speaker} ({info.get('turns', 0)} turns, {info.get('words', 0)} words)",
                key=f"sp_{speaker}",
                help=" | ".join(info.get("samples", [])),
            )

            if name.strip():
                speaker_map[speaker] = name.strip()

    final = list(dict.fromkeys(speaker_map.get(speaker, speaker) for speaker in labels))

    roster_input = st.text_input(
        "Roster (comma-separated)",
        ", ".join(final),
    )

    roster = [name.strip() for name in roster_input.split(",") if name.strip()]

    st.caption(f"{len(turns)} turns · about {estimate_calls(turns)} LLM calls")

    if st.button("Extract", type="primary"):
        bar = st.progress(
            0.0,
            text="Starting…",
        )

        def callback(
            stage: str,
            done: int,
            total: int,
        ) -> None:
            progress = min(
                1.0,
                done / max(1, total),
            )

            bar.progress(
                progress,
                text=f"{stage}: {done}/{total}",
            )

        outcome = service.ingest(
            raw,
            meeting_date=meeting_date,
            title=title or None,
            timezone=timezone,
            roster=roster,
            speaker_map=speaker_map,
            store=store,
            on_progress=callback,
            **opts,
        )

        if outcome.status in ("rejected", "failed"):
            st.error(outcome.error or "Extraction failed")
        else:
            st.session_state["_goto"] = outcome.meeting_id
            st.rerun()


def audio_expander() -> None:
    try:
        from copilot.ui.audio_panel import (
            render_audio_panel,
        )
    except ImportError:
        return

    render_audio_panel()


# ------------------------------------------------------------------
# Review cards
# ------------------------------------------------------------------


def action_card(
    it: dict,
    meeting,
    scope: str,
) -> None:
    with st.container(border=True):
        superseded_label = " · _superseded_" if it["status"] == "superseded" else ""

        st.markdown(f"{BADGE[it['state']]} **{H.md_escape(it['title'])}**{superseded_label}")

        bits = [
            it["status"],
            f"confidence {it['confidence']:.0%}",
        ] + [H.FLAG_LABEL.get(flag, flag) for flag in it["flags"]]

        st.caption(" · ".join(bits))

        if it.get("condition"):
            st.caption("🔗 Condition: " + H.md_escape(it["condition"]))

        if it.get("deadline_options"):
            st.caption("📅 Could mean: " + ", ".join(it["deadline_options"]))

        if it["stale"]:
            st.caption("⚠️ The latest extraction no longer produces this item.")

        with st.expander("Evidence"):
            st.markdown(
                H.evidence_html(
                    meeting.turns,
                    it["evidence"],
                ),
                unsafe_allow_html=True,
            )

        current_deadline = date.fromisoformat(it["deadline"]) if it.get("deadline") else None

        owners = ["(none)"] + list(meeting.roster)

        if it.get("owner") and it["owner"] not in owners:
            owners.append(it["owner"])

        with st.form(
            f"form_{scope}_{it['id']}",
            border=False,
        ):
            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])

            title = col1.text_input(
                "Title",
                it["title"],
            )

            owner = col2.selectbox(
                "Owner",
                owners,
                index=owners.index(it.get("owner") or "(none)"),
            )

            no_deadline = col3.checkbox(
                "No deadline",
                value=current_deadline is None,
            )

            deadline = col3.date_input(
                "Deadline",
                value=current_deadline or meeting.date,
            )

            priorities = ["high", "normal", "low"]

            priority = col4.selectbox(
                "Priority",
                priorities,
                index=priorities.index(it.get("priority", "normal")),
            )

            btn1, btn2, btn3, _ = st.columns([1, 1, 1, 4])

            approve = btn1.form_submit_button("✅ Approve")

            reject = btn2.form_submit_button("❌ Reject")

            save = btn3.form_submit_button("💾 Save")

        if approve or reject or save:
            new = {
                "title": (title.strip() or it["orig"]["title"]),
                "owner": (None if owner == "(none)" else owner),
                "deadline": (None if no_deadline else deadline.isoformat()),
                "priority": priority,
            }

            state = "approved" if approve else "rejected" if reject else None

            store.update_item(
                it["id"],
                state=state,
                edits=H.compute_edits(
                    it["orig"],
                    new,
                ),
            )

            st.rerun()


def simple_card(
    it: dict,
    meeting,
    scope: str,
    field: str,
    label: str,
) -> None:
    with st.container(border=True):
        st.markdown(f"{BADGE[it['state']]} {H.md_escape(it[field])}")

        if it["kind"] == "question":
            if it.get("answered"):
                answer = it.get("answer_summary") or ""

                st.caption("✅ answered: " + H.md_escape(answer))
            else:
                st.caption("❓ unresolved")

        if it["stale"]:
            st.caption("⚠️ No longer produced by the latest extraction.")

        with st.expander("Evidence"):
            st.markdown(
                H.evidence_html(
                    meeting.turns,
                    it["evidence"],
                ),
                unsafe_allow_html=True,
            )

        with st.form(
            f"form_{scope}_{it['id']}",
            border=False,
        ):
            text = st.text_input(
                label,
                it[field],
            )

            answered = None

            if it["kind"] == "question":
                answered = st.checkbox(
                    "Answered",
                    value=bool(it.get("answered")),
                )

            btn1, btn2, btn3, _ = st.columns([1, 1, 1, 4])

            approve = btn1.form_submit_button("✅ Approve")

            reject = btn2.form_submit_button("❌ Reject")

            save = btn3.form_submit_button("💾 Save")

        if approve or reject or save:
            new = {field: (text.strip() or it["orig"][field])}

            if answered is not None:
                new["answered"] = answered

            state = "approved" if approve else "rejected" if reject else None

            store.update_item(
                it["id"],
                state=state,
                edits=H.compute_edits(
                    it["orig"],
                    new,
                ),
            )

            st.rerun()


FIELD = {
    "decision": ("summary", "Decision"),
    "question": ("question", "Question"),
    "followup": ("topic", "Follow-up"),
}


def card(
    it: dict,
    meeting,
    scope: str,
) -> None:
    if it["kind"] == "action":
        action_card(
            it,
            meeting,
            scope,
        )
    else:
        simple_card(
            it,
            meeting,
            scope,
            *FIELD[it["kind"]],
        )


# ------------------------------------------------------------------
# Meeting view
# ------------------------------------------------------------------


def render_meeting(mid: str) -> None:
    row = store.get_meeting(mid)

    if not row:
        st.error("Meeting not found.")
        return

    st.header(row["title"] or mid)

    st.caption(f"{row['date']} · {row['timezone']} · id `{mid}`")

    if row["status"] == "processing":
        st.info("Still processing. Free-tier rate limits make this slow.")

        if st.button("Refresh"):
            st.rerun()

        return

    if row["status"] in ("rejected", "failed"):
        st.error(row["error"] or "Extraction failed.")
        return

    if row["status"] == "partial":
        report = row["report"]

        st.warning(
            "**Partial result.** Some parts failed, "
            "so items may be missing. "
            f"Failed chunks: "
            f"{report.get('failed_chunks') or 'none'}; "
            f"degraded: "
            f"{report.get('degraded') or 'none'}."
        )

    for warning in row["warnings"]:
        st.caption("⚠️ " + warning)

    meeting = store.meeting_obj(mid)
    items = store.items(mid)

    live = [item for item in items if not item["stale"]]

    actions = [
        item for item in live if (item["kind"] == "action" and item["status"] != "superseded")
    ]

    metrics = st.columns(4)

    metrics[0].metric(
        "Action items",
        len(actions),
    )

    metrics[1].metric(
        "Pending review",
        sum(item["state"] == "pending" for item in live),
    )

    metrics[2].metric(
        "Approved",
        sum(item["state"] == "approved" for item in live),
    )

    metrics[3].metric(
        "Need attention",
        sum(bool(set(item["flags"]) & H.ATTENTION) for item in actions),
    )

    tabs = st.tabs(
        [
            "Action items",
            "Needs attention",
            "Decisions & questions",
            "Transcript",
            "Export & push",
        ]
    )

    t_rev, t_attn, t_dq, t_tr, t_exp = tabs

    # --------------------------------------------------------------
    # Action items
    # --------------------------------------------------------------

    with t_rev:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 3])

        show = col1.radio(
            "Show",
            [
                "Pending",
                "Approved",
                "Rejected",
                "All",
            ],
            horizontal=True,
            key="f_show",
        )

        low = col2.toggle(
            "Low confidence (<50%)",
            key="f_low",
        )

        superseded = col3.toggle(
            "Superseded",
            key="f_sup",
        )

        if col4.button(
            "Approve all clean items",
            help=("No flags, owner set, confidence ≥ 80%"),
        ):
            count = service.approve_clean(
                store,
                mid,
            )

            st.toast(f"Approved {count} items")
            st.rerun()

        shown = [
            item
            for item in items
            if (
                item["kind"] == "action"
                and (not item.get("stale", False) or show == "All")
                and (show == "All" or item["state"] == show.lower())
                and (low or item["confidence"] >= 0.5 or item["state"] != "pending")
                and (superseded or item["status"] != "superseded")
            )
        ]

        st.caption(f"{len(shown)} shown")

        for item in shown:
            action_card(
                item,
                meeting,
                "rev",
            )

    # --------------------------------------------------------------
    # Needs attention
    # --------------------------------------------------------------

    with t_attn:
        attention = [
            item
            for item in live
            if (
                item["state"] != "rejected"
                and (
                    (
                        item["kind"] == "action"
                        and item["status"] != "superseded"
                        and bool(set(item["flags"]) & H.ATTENTION)
                    )
                    or (item["kind"] == "question" and not item.get("answered"))
                )
            )
        ]

        st.caption("Items without a clear owner or deadline, and unresolved questions.")

        for item in attention:
            card(
                item,
                meeting,
                "attn",
            )

        if not attention:
            st.success("Nothing needs attention.")

    # --------------------------------------------------------------
    # Decisions and questions
    # --------------------------------------------------------------

    with t_dq:
        if st.button("Approve all decisions"):
            for item in live:
                if item["kind"] == "decision" and item["state"] == "pending":
                    store.update_item(
                        item["id"],
                        state="approved",
                    )

            st.rerun()

        for kind in (
            "decision",
            "question",
            "followup",
        ):
            group = [
                item
                for item in items
                if (
                    item["kind"] == kind
                    and (kind != "decision" or item.get("status", "active") == "active")
                )
            ]

            heading = {
                "decision": "Decisions",
                "question": "Open questions",
                "followup": "Follow-ups",
            }[kind]

            st.subheader(heading)

            for item in group:
                card(
                    item,
                    meeting,
                    "dq",
                )

            if not group:
                st.caption("None.")

    # --------------------------------------------------------------
    # Transcript
    # --------------------------------------------------------------

    with t_tr:
        options = ["(none)"] + [
            f"{item['id']}: {label[:60]}"
            for item in live
            for label in [
                (
                    item.get("title")
                    or item.get("summary")
                    or item.get("question")
                    or item.get("topic")
                    or ""
                )
            ]
        ]

        pick = st.selectbox(
            "Highlight evidence for",
            options,
        )

        highlighted = set()

        if pick != "(none)":
            selected_id = pick.split(":")[0]

            highlighted = {
                evidence["turn_idx"]
                for item in live
                if item["id"] == selected_id
                for evidence in item["evidence"]
            }

        with st.container(height=520):
            rows = []

            for turn in meeting.turns:
                style = "background:rgba(255,200,0,.2);" if turn.idx in highlighted else ""

                speaker = H.html.escape(turn.speaker or "?")

                text = H.html.escape(turn.text)

                rows.append(
                    f'<div style="{style}padding:2px 4px">'
                    '<span style="opacity:.6">'
                    f"[{turn.idx}] {speaker}:"
                    "</span> "
                    f"{text}</div>"
                )

            st.markdown(
                "".join(rows),
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------------
    # Export and push
    # --------------------------------------------------------------

    with t_exp:
        approved = [
            {key: value for key, value in item.items() if key != "orig"}
            for item in live
            if item["state"] == "approved"
        ]

        st.download_button(
            "Download approved items (JSON)",
            json.dumps(
                approved,
                indent=2,
                default=str,
            ),
            file_name=f"{mid}_approved.json",
            mime="application/json",
        )

        try:
            from copilot.ui.push_tab import (
                render_push_tab,
            )

            render_push_tab(
                store,
                mid,
            )

        except ImportError:
            st.caption("Push and email options arrive on Day 18.")


# ------------------------------------------------------------------
# Application entry point — Step 7H
# ------------------------------------------------------------------

choice, opts = sidebar()

st.title("📝 Meeting Co-Pilot")

if choice == NEW:
    render_new(opts)
else:
    render_meeting(choice)
