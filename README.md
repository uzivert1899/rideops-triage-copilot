# RideOps L1 Triage & Escalation Gatekeeper Copilot (v0)

This Streamlit application triages incoming and open support tickets from `rideops_support_tickets.csv`, ranks backlog urgency, predicts issue categories, and identifies likely duplicate known issues. It enforces engineering escalation diagnostics, provides L1 self-fix runbooks, and requires closure verification before tickets can be marked closed.

## Local setup and run

1. `pip install -r requirements.txt`
2. `streamlit run app.py`

## Folder structure

- `app.py`: Streamlit user interface and application workflow
- `config/rules.py`: Categories, keywords, SLA rules, runbooks, and verification items
- `src/data_loader.py`: Ticket loading, known-issue aggregation, KPIs, and queue ranking
- `src/triage_engine.py`: Category prediction, duplicate matching, and escalation/closure gates
- `src/state_store.py`: JSON persistence for demo actions
- `data/rideops_support_tickets.csv`: RideOps support ticket dataset
