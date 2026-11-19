import pandas as pd

from config.rules import DATA_PULL_TS, SLA_HOURS_BY_PRIORITY, TIER_MULTIPLIER


def load_tickets(csv_path: str = "data/rideops_support_tickets.csv") -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].str.strip()

    created_at = pd.to_datetime(df["created_at"], errors="coerce")
    first_response_at = pd.to_datetime(df["first_response_at"], errors="coerce")
    first_closed_at = pd.to_datetime(df["first_closed_at"], errors="coerce")
    final_closed_at = pd.to_datetime(df["final_closed_at"], errors="coerce")

    df["created_at"] = created_at
    df["first_response_at"] = first_response_at
    df["first_closed_at"] = first_closed_at
    df["final_closed_at"] = final_closed_at

    data_pull_ts = pd.Timestamp(DATA_PULL_TS)
    final_close_age = (final_closed_at - created_at).dt.total_seconds() / 3600
    open_age = (data_pull_ts - created_at).dt.total_seconds() / 3600
    df["age_hours"] = final_close_age.where(
        (df["status"] == "Closed") & final_closed_at.notna(),
        open_age,
    )

    df["sla_target_hours"] = (
        df["priority"].map(SLA_HOURS_BY_PRIORITY)
        * df["client_tier"].map(TIER_MULTIPLIER)
    )
    df["sla_breached"] = df["age_hours"] > df["sla_target_hours"]
    df["has_pending_eng_verdict"] = (
        (df["status"] != "Closed") & df["eng_outcome"].notna()
    )

    return df


def get_known_issues_bank(df: pd.DataFrame) -> pd.DataFrame:
    known_outcomes = [
        "Duplicate of known issue",
        "Fixed",
        "Config issue - returned to L1",
    ]
    filtered = df[df["eng_outcome"].isin(known_outcomes)]

    return (
        filtered.groupby(["category", "description"], as_index=False)
        .agg(
            occurrence_count=("ticket_id", "count"),
            eng_ticket_id=("eng_ticket_id", "first"),
            eng_outcome=("eng_outcome", "first"),
            ticket_id=("ticket_id", "first"),
        )
        .sort_values("occurrence_count", ascending=False)
        .reset_index(drop=True)
    )


def compute_kpis(df: pd.DataFrame, actions_log: dict) -> dict:
    working = df.copy()

    for ticket_id, action_record in actions_log.items():
        if isinstance(action_record, dict) and (
            action_record.get("status") == "Closed"
            or action_record.get("new_status") == "Closed"
        ):
            mask = working["ticket_id"] == ticket_id
            working.loc[mask, "status"] = "Closed"

    open_tickets = working[working["status"] != "Closed"].copy()

    return {
        "open_total": int(len(open_tickets)),
        "open_with_l1": int((open_tickets["escalated_to_eng"] != "Yes").sum()),
        "open_with_eng": int((open_tickets["escalated_to_eng"] == "Yes").sum()),
        "ready_to_close_verdicts": int(
            open_tickets["has_pending_eng_verdict"].sum()
        ),
        "sla_breached_open": int(open_tickets["sla_breached"].sum()),
        "historical_reopen_rate": float(
            round((df["reopen_count"] > 0).mean() * 100, 1)
        ),
        "historical_non_bug_esc_rate": float(
            round(
                (
                    df[df["escalated_to_eng"] == "Yes"]["eng_outcome"] != "Fixed"
                ).mean()
                * 100,
                1,
            )
        ),
    }
