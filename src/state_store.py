import json
import os


def load_actions(log_path: str = "data/actions_log.json") -> dict:
    if not os.path.exists(log_path):
        return {}

    try:
        with open(log_path, "r", encoding="utf-8") as log_file:
            actions = json.load(log_file)
    except (json.JSONDecodeError, OSError):
        return {}

    return actions if isinstance(actions, dict) else {}


def save_action(
    ticket_id: str,
    action_record: dict,
    log_path: str = "data/actions_log.json",
) -> dict:
    parent_dir = os.path.dirname(log_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    actions = load_actions(log_path)
    actions[ticket_id] = action_record

    with open(log_path, "w", encoding="utf-8") as log_file:
        json.dump(actions, log_file, indent=2)

    return actions


def reset_actions(log_path: str = "data/actions_log.json") -> dict:
    parent_dir = os.path.dirname(log_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as log_file:
        json.dump({}, log_file, indent=2)

    return {}
