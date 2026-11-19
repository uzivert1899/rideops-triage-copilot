import os
import tempfile

import pandas as pd
import streamlit as st

from config.rules import (
    CATEGORY_PLAYBOOKS,
    CLOSURE_VERIFICATION_ITEMS,
    DATA_PULL_TS,
)
from src.data_loader import (
    compute_kpis,
    get_known_issues_bank,
    load_tickets,
)
from src.state_store import load_actions, reset_actions, save_action
from src.triage_engine import (
    evaluate_closure_gate,
    evaluate_escalation_gate,
    find_similar_known_issues,
    predict_category,
    rank_open_queue,
)


st.set_page_config(
    page_title="RideOps L1 Triage Copilot",
    layout="wide",
)

AGENTS = [
    "Ananya R",
    "Arjun K",
    "Karan B",
    "Neha P",
    "Priya D",
    "Rahul T",
    "Sneha M",
    "Vikram S",
]
REQUIRED_COLUMNS = [
    "ticket_id",
    "created_at",
    "client_tier",
    "category",
    "priority",
    "description",
    "status",
]


st.sidebar.title("RideOps Triage")
active_agent = st.sidebar.selectbox("Active L1 Agent", AGENTS)

uploaded_csv = st.sidebar.file_uploader(
    "Upload a ticket CSV",
    type=["csv"],
)

df = None
if uploaded_csv is not None:
    try:
        uploaded_df = pd.read_csv(uploaded_csv)
        missing_columns = [
            column for column in REQUIRED_COLUMNS if column not in uploaded_df.columns
        ]
        if missing_columns:
            st.sidebar.error(
                "Missing required columns: " + ", ".join(missing_columns)
            )
        else:
            with tempfile.NamedTemporaryFile(
                suffix=".csv",
                delete=False,
            ) as temp_file:
                temp_file.write(uploaded_csv.getvalue())
                temp_path = temp_file.name
            df = load_tickets(temp_path)
            os.unlink(temp_path)
    except Exception as error:
        st.sidebar.error(f"Could not load uploaded CSV: {error}")

if df is None:
    df = load_tickets()

actions_log = load_actions()
known_issues = get_known_issues_bank(df)
kpis = compute_kpis(df, actions_log)

st.title("RideOps L1 Triage Copilot")

kpi_columns = st.columns(4)
kpi_columns[0].metric(
    "Open Backlog",
    kpis["open_total"],
    delta=kpis["open_total"] - 48,
)
kpi_columns[1].metric(
    "Ready Eng Verdicts to Clear",
    kpis["ready_to_close_verdicts"],
)
kpi_columns[2].metric(
    "SLA Breached (Open)",
    kpis["sla_breached_open"],
)
kpi_columns[3].metric(
    "Historical Non-Bug Escalation Rate",
    f"{kpis['historical_non_bug_esc_rate']}%",
)

if st.sidebar.button("Reset Demo State"):
    reset_actions()
    st.rerun()

tab_queue, tab_gatekeeper, tab_closure = st.tabs(
    [
        "1. Actionable Open Queue",
        "2. Triage & Escalation Gatekeeper",
        "3. Closure Verification Gate",
    ]
)

with tab_queue:
    ranked_queue = rank_open_queue(df, actions_log)

    filter_columns = st.columns(3)
    status_options = ["All"] + sorted(
        ranked_queue["status"].dropna().unique().tolist()
    )
    status_filter = filter_columns[0].selectbox(
        "Status",
        status_options,
    )
    category_options = ["All"] + sorted(
        ranked_queue["category"].dropna().unique().tolist()
    )
    category_filter = filter_columns[1].selectbox(
        "Category",
        category_options,
    )
    verdict_only = filter_columns[2].checkbox(
        "Only tickets with Eng Verdict ready"
    )

    filtered_queue = ranked_queue.copy()
    if status_filter != "All":
        filtered_queue = filtered_queue[
            filtered_queue["status"] == status_filter
        ]
    if category_filter != "All":
        filtered_queue = filtered_queue[
            filtered_queue["category"] == category_filter
        ]
    if verdict_only:
        filtered_queue = filtered_queue[
            filtered_queue["has_pending_eng_verdict"] == True
        ]

    display_columns = [
        "ticket_id",
        "priority",
        "client_tier",
        "category",
        "status",
        "eng_outcome",
        "age_hours",
        "urgency_score",
        "recommended_action",
    ]
    display_queue = filtered_queue[display_columns].copy()
    display_queue["age_hours"] = display_queue["age_hours"].round(1)

    st.dataframe(
        display_queue,
        hide_index=True,
        use_container_width=True,
        column_config={
            "ticket_id": "Ticket",
            "priority": "Priority",
            "client_tier": "Tier",
            "category": "Category",
            "status": "Status",
            "eng_outcome": "Engineering Verdict",
            "age_hours": st.column_config.NumberColumn(
                "Age (hours)",
                format="%.1f",
            ),
            "urgency_score": st.column_config.NumberColumn(
                "Urgency",
                format="%d",
            ),
            "recommended_action": "Recommended Action",
        },
    )

    ticket_options = filtered_queue["ticket_id"].tolist()
    if not ticket_options:
        st.info("No tickets match the current filters.")
    else:
        selected_ticket = st.selectbox(
            "Ticket",
            ticket_options,
        )
        if st.button("Load Ticket into Triage Copilot"):
            st.session_state["selected_ticket_id"] = selected_ticket
            st.success(f"Loaded {selected_ticket} into the Triage Copilot.")

with tab_gatekeeper:
    mode = st.radio(
        "Ticket mode",
        ["Existing Open Ticket", "Simulate New Incoming Ticket"],
        horizontal=True,
    )

    ticket = None
    description = ""
    current_category = None
    existing_ticket_id = None
    simulated_tier = None
    simulated_priority = None

    if mode == "Existing Open Ticket":
        open_ticket_ids = ranked_queue = rank_open_queue(df, actions_log)[
            "ticket_id"
        ].tolist()
        if not open_ticket_ids:
            st.info("No open tickets are available.")
        else:
            default_ticket_id = st.session_state.get("selected_ticket_id")
            default_index = (
                open_ticket_ids.index(default_ticket_id)
                if default_ticket_id in open_ticket_ids
                else 0
            )
            existing_ticket_id = st.selectbox(
                "Open Ticket",
                open_ticket_ids,
                index=default_index,
            )
            ticket_rows = df[df["ticket_id"] == existing_ticket_id]
            if not ticket_rows.empty:
                ticket = ticket_rows.iloc[0]
                description = str(ticket["description"])
                current_category = ticket["category"]
            st.text_area(
                "Issue description",
                value=description,
                key="existing_ticket_description",
                disabled=True,
            )
    else:
        description = st.text_input(
            "Issue description",
            value="",
            key="simulated_description",
        )
        tier_columns = st.columns(2)
        simulated_tier = tier_columns[0].selectbox(
            "Client tier",
            ["Enterprise", "Mid-market", "SMB"],
        )
        simulated_priority = tier_columns[1].selectbox(
            "Priority",
            ["P1", "P2", "P3", "P4"],
        )

    if description:
        prediction = predict_category(description, current_category)
        category = prediction["predicted_category"]

        prediction_columns = st.columns([2, 1])
        prediction_columns[0].write(
            f"Predicted category: **{category}**"
        )
        confidence = prediction["confidence"]
        badge_type = "success" if confidence == "High" else "warning"
        getattr(prediction_columns[1], badge_type)(
            f"Confidence: {confidence}"
        )
        if prediction["mismatch_warning"]:
            st.error(
                "Category mismatch warning: predicted category differs "
                "from the ticket's current category."
            )

        duplicate_matches = find_similar_known_issues(
            description,
            category,
            known_issues,
        )
        if duplicate_matches:
            st.subheader("Matching Known Issues")
            duplicate_table = pd.DataFrame(
                duplicate_matches
            )[
                [
                    "ticket_id",
                    "eng_ticket_id",
                    "eng_outcome",
                    "occurrence_count",
                    "similarity",
                ]
            ].copy()
            duplicate_table["similarity"] = duplicate_table["similarity"].round(3)
            st.dataframe(
                duplicate_table,
                hide_index=True,
                use_container_width=True,
            )

        left_column, right_column = st.columns(2)

        with left_column:
            st.subheader("L1 Self-Fix Config Runbook")
            for step in CATEGORY_PLAYBOOKS[category]["self_fix_steps"]:
                st.markdown(f"- {step}")

            if st.button("Resolved via L1 Runbook -> Mark Ready to Close"):
                if existing_ticket_id:
                    st.session_state["closure_ticket_id"] = existing_ticket_id
                    save_action(
                        existing_ticket_id,
                        {
                            "action": "l1_resolved",
                            "new_status": "Ready to Close",
                            "category": category,
                        },
                    )
                    st.success(
                        f"{existing_ticket_id} is ready for closure verification."
                    )
                else:
                    import hashlib

                    deflected_id = (
                        "SIM-"
                        + hashlib.sha1(description.encode("utf-8")).hexdigest()[:8]
                    )
                    save_action(
                        deflected_id,
                        {
                            "action": "l1_deflected",
                            "new_status": "Closed",
                            "category": category,
                            "description": description,
                            "client_tier": simulated_tier,
                            "priority": simulated_priority,
                        },
                    )
                    st.success(
                        f"Deflected simulated ticket {deflected_id} and logged as closed."
                    )

        with right_column:
            st.subheader("Engineering Escalation Gatekeeper")
            checked_items = []
            for item in CATEGORY_PLAYBOOKS[category]["escalation_checklist"]:
                if st.checkbox(item, key=f"escalation_{category}_{item}"):
                    checked_items.append(item)

            debug_notes = st.text_area(
                "Debug notes / logs",
                value="",
                key=f"escalation_notes_{category}",
            )

            duplicate_override = False
            if duplicate_matches:
                duplicate_override = st.checkbox(
                    "Confirm distinct new bug (override duplicate warning)",
                    key=f"duplicate_override_{category}",
                )

            escalation_gate = evaluate_escalation_gate(
                category,
                checked_items,
                duplicate_override,
                duplicate_matches,
                debug_notes,
            )

            if not escalation_gate["allowed"]:
                for reason in escalation_gate["blocking_reasons"]:
                    st.error(reason)

            approve_escalation = st.button(
                "Approve & Generate Escalation Packet",
                disabled=not escalation_gate["allowed"],
            )
            if approve_escalation:
                packet = escalation_gate["escalation_packet"]
                st.code(packet, language="text")

                packet_ticket_id = (
                    existing_ticket_id
                    if existing_ticket_id
                    else "SIM-" + __import__("hashlib").sha1(
                        description.encode("utf-8")
                    ).hexdigest()[:8]
                )
                save_action(
                    packet_ticket_id,
                    {
                        "action": "engineering_escalation",
                        "new_status": "Open",
                        "category": category,
                        "description": description,
                        "escalation_packet": packet,
                    },
                )
                st.success("Escalation packet generated and action logged.")

with tab_closure:
    open_queue = rank_open_queue(df, actions_log)
    open_ticket_ids = open_queue["ticket_id"].tolist()

    if not open_ticket_ids:
        st.info("There are no open tickets available for closure.")
    else:
        preferred_ticket_id = (
            st.session_state.get("closure_ticket_id")
            or st.session_state.get("selected_ticket_id")
        )
        default_index = (
            open_ticket_ids.index(preferred_ticket_id)
            if preferred_ticket_id in open_ticket_ids
            else 0
        )
        selected_ticket_id = st.selectbox(
            "Open ticket",
            open_ticket_ids,
            index=default_index,
            key="closure_selected_ticket",
        )
        ticket_rows = df[df["ticket_id"] == selected_ticket_id]

        if ticket_rows.empty:
            st.info("The selected ticket is no longer available.")
        else:
            ticket = ticket_rows.iloc[0]

            detail_columns = st.columns(4)
            detail_columns[0].write(f"**Category:** {ticket['category']}")
            detail_columns[1].write(
                f"**Assigned agent:** {ticket['assigned_agent']}"
            )
            detail_columns[2].write(
                f"**Reopen count:** {ticket['reopen_count']}"
            )
            detail_columns[3].write(
                f"**Eng outcome:** "
                f"{ticket['eng_outcome'] if pd.notna(ticket['eng_outcome']) else 'None'}"
            )

            checked_items = []
            for item in CLOSURE_VERIFICATION_ITEMS:
                if st.checkbox(
                    item,
                    key=f"closure_{selected_ticket_id}_{item}",
                ):
                    checked_items.append(item)

            closure_notes = st.text_area(
                "Closure resolution note",
                value="",
                key=f"closure_notes_{selected_ticket_id}",
            )

            closure_gate = evaluate_closure_gate(
                ticket["category"],
                active_agent,
                checked_items,
            )

            for warning in closure_gate["warnings"]:
                st.warning(warning)
            if closure_gate["allowed"]:
                st.success("Closure gate allowed.")
            else:
                for reason in closure_gate["blocking_reasons"]:
                    st.error(reason)

            if st.button(
                "Confirm & Close Ticket",
                disabled=not closure_gate["allowed"],
                key=f"confirm_close_{selected_ticket_id}",
            ):
                save_action(
                    selected_ticket_id,
                    {
                        "action": "Verified Closure",
                        "new_status": "Closed",
                        "agent": active_agent,
                        "notes": closure_notes,
                        "timestamp": DATA_PULL_TS,
                    },
                )
                st.session_state["closure_ticket_id"] = selected_ticket_id
                st.rerun()
