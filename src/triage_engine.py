from difflib import SequenceMatcher

import pandas as pd

from config.rules import (
    CATEGORY_KEYWORDS,
    CATEGORY_PLAYBOOKS,
    CLOSURE_VERIFICATION_ITEMS,
    VALID_CATEGORIES,
)


def predict_category(description: str, current_category: str | None = None) -> dict:
    text = description.lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword in text)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    hits = max(scores.values(), default=0)

    if hits == 0:
        if current_category in VALID_CATEGORIES:
            predicted_category = current_category
        else:
            predicted_category = "Roster / booking not syncing"
    else:
        predicted_category = max(scores, key=scores.get)

    if hits >= 2:
        confidence = "High"
    elif hits == 1:
        confidence = "Medium"
    else:
        confidence = "Low"

    mismatch_warning = (
        current_category is not None
        and confidence == "High"
        and predicted_category != current_category
    )

    return {
        "predicted_category": predicted_category,
        "confidence": confidence,
        "mismatch_warning": mismatch_warning,
    }


def find_similar_known_issues(
    description: str,
    category: str,
    known_bank: pd.DataFrame,
    threshold: float = 0.65,
) -> list[dict]:
    target = description.lower().strip()
    matches = []

    for _, row in known_bank.iterrows():
        candidate = str(row["description"]).lower().strip()
        similarity = SequenceMatcher(None, target, candidate).ratio()
        same_category = row["category"] == category

        if (same_category and similarity >= threshold) or (
            not same_category and similarity >= 0.85
        ):
            matches.append(
                {
                    "ticket_id": row["ticket_id"],
                    "eng_ticket_id": row["eng_ticket_id"],
                    "eng_outcome": row["eng_outcome"],
                    "description": row["description"],
                    "occurrence_count": int(row["occurrence_count"]),
                    "similarity": similarity,
                }
            )

    matches.sort(
        key=lambda match: (-match["similarity"], -match["occurrence_count"])
    )
    return matches[:3]


def evaluate_escalation_gate(
    category: str,
    checked_items: list[str],
    duplicate_override: bool,
    duplicate_matches: list[dict],
    notes: str,
) -> dict:
    blocking_reasons = []
    required_count = len(CATEGORY_PLAYBOOKS[category]["escalation_checklist"])

    if len(checked_items) < required_count:
        blocking_reasons.append(
            "Complete all escalation checklist items before escalation."
        )
    if duplicate_matches and not duplicate_override:
        blocking_reasons.append(
            "Duplicate known issues found; confirm override to escalate."
        )
    if len(notes.strip()) < 15:
        blocking_reasons.append(
            "Escalation notes must contain at least 15 characters."
        )

    escalation_packet = ""
    if not blocking_reasons:
        escalation_packet = (
            f"Category: {category}\n"
            f"Notes: {notes.strip()}\n"
            f"Checked escalation items: {', '.join(checked_items)}"
        )

    return {
        "allowed": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
        "escalation_packet": escalation_packet,
    }


def evaluate_closure_gate(
    category: str,
    agent_name: str,
    checked_closure_items: list[str],
) -> dict:
    warnings = []
    blocking_reasons = []

    if CATEGORY_PLAYBOOKS[category]["high_reopen_risk"]:
        warnings.append(
            "High reopen-risk category: perform extra verification before closure."
        )
    if agent_name == "Karan B":
        warnings.append(
            "Closure for Karan B requires careful secondary verification."
        )

    if len(checked_closure_items) != len(CLOSURE_VERIFICATION_ITEMS):
        blocking_reasons.append(
            "Complete all mandatory closure verification items."
        )

    return {
        "allowed": not blocking_reasons,
        "warnings": warnings,
        "blocking_reasons": blocking_reasons,
    }


def rank_open_queue(df: pd.DataFrame, actions_log: dict) -> pd.DataFrame:
    priority_pts = {"P1": 100, "P2": 70, "P3": 40, "P4": 20}
    tier_pts = {"Enterprise": 25, "Mid-market": 10, "SMB": 0}

    open_tickets = df[df["status"] != "Closed"].copy()
    excluded_ids = [
        ticket_id
        for ticket_id, action in actions_log.items()
        if isinstance(action, dict)
        and action.get("new_status") == "Closed"
    ]
    if excluded_ids:
        open_tickets = open_tickets[
            ~open_tickets["ticket_id"].isin(excluded_ids)
        ].copy()

    open_tickets["urgency_score"] = (
        open_tickets["priority"].map(priority_pts).fillna(0)
        + open_tickets["client_tier"].map(tier_pts).fillna(0)
        + open_tickets["sla_breached"].fillna(False).astype(int) * 30
        + open_tickets["eng_handoffs"].fillna(0).astype(int) * 15
        + open_tickets["has_pending_eng_verdict"].fillna(False).astype(int) * 40
    )

    def recommended_action(row):
        if bool(row["has_pending_eng_verdict"]):
            outcome = row["eng_outcome"]
            if outcome == "Fixed":
                return "Close with Verification"
            if outcome == "Duplicate of known issue":
                return "Link Known Issue"
            if outcome == "Config issue - returned to L1":
                return "Apply Config Fix and Retest"
            return "Review Engineering Verdict"
        return "Run L1 Triage Checklist"

    open_tickets["recommended_action"] = open_tickets.apply(
        recommended_action,
        axis=1,
    )

    return open_tickets.sort_values(
        "urgency_score",
        ascending=False,
    ).reset_index(drop=True)
