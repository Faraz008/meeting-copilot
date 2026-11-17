import streamlit as st

from copilot import service
from copilot.config import settings
from copilot.digest import to_markdown


def render_push_tab(store, mid: str) -> None:
    d = service.digest(store, mid)

    st.download_button(
        "Download summary (Markdown)",
        to_markdown(d),
        file_name=f"{mid}.md",
        mime="text/markdown",
    )

    st.download_button(
        "Download deadlines (.ics)",
        service.ics_bytes(store, mid),
        file_name=f"{mid}.ics",
        mime="text/calendar",
    )

    if settings.demo_mode:
        st.info("Demo mode: pushing, email and Slack are disabled.")
        return

    st.divider()
    st.caption("Only **approved** items are pushed. Always preview first.")

    integrations = (
        (
            "notion",
            settings.notion_token and settings.notion_database_id,
        ),
        (
            "jira",
            settings.jira_base_url and settings.jira_api_token and settings.jira_project_key,
        ),
    )

    for name, ok in integrations:
        with st.container(border=True):
            st.subheader(name.title())

            if not ok:
                st.caption("Not configured (see docs/integrations.md).")
                continue

            c1, c2 = st.columns(2)

            if c1.button(
                "Preview (dry run)",
                key=f"dry_{name}",
            ):
                st.session_state[f"rep_{name}"] = service.push(
                    store,
                    mid,
                    name,
                    dry_run=True,
                )

            confirm = c2.checkbox(
                "I reviewed the preview",
                key=f"ok_{name}",
            )

            if c2.button(
                "Push approved items",
                key=f"push_{name}",
                disabled=not confirm,
            ):
                st.session_state[f"rep_{name}"] = service.push(
                    store,
                    mid,
                    name,
                    dry_run=False,
                )

            rep = st.session_state.get(f"rep_{name}")

            if rep:
                st.write(rep.summary())

                rows = [
                    {
                        "item": outcome.item_id,
                        "status": outcome.status,
                        "link": outcome.url,
                        "error": outcome.error,
                    }
                    for outcome in rep.outcomes
                ]

                st.dataframe(
                    rows,
                    use_container_width=True,
                )

                if rep.orphans:
                    orphan_ids = ", ".join(outcome["external_id"] or "?" for outcome in rep.orphans)

                    st.warning(
                        f"{len(rep.orphans)} previously pushed items "
                        "are no longer approved/current. "
                        "Close them manually: " + orphan_ids
                    )

    with st.container(border=True):
        st.subheader("Email")

        plans = service.email(
            store,
            mid,
            send=False,
        )

        st.caption(
            "Preview files are written to data/outbox/. Recipients come from config/roster.json."
        )

        st.dataframe(
            plans,
            use_container_width=True,
        )

        n = sum(row["status"] == "dry_run" for row in plans)

        confirm = st.checkbox(
            f"I confirm sending real email to {n} people",
            key="ok_mail",
        )

        if st.button(
            "Send",
            disabled=not (confirm and n),
        ):
            st.dataframe(
                service.email(store, mid, send=True),
                use_container_width=True,
            )

    with st.container(border=True):
        st.subheader("Slack")

        if settings.slack_webhook_url and st.button("Post summary to Slack"):
            service.slack(store, mid)
            st.success("Posted.")

        elif not settings.slack_webhook_url:
            st.caption("Set SLACK_WEBHOOK_URL to enable.")
