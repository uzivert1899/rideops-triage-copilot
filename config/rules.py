DATA_PULL_TS = "2026-09-30 23:59:59"

VALID_CATEGORIES = [
    "Roster / booking not syncing",
    "Live tracking / GPS incorrect",
    "Report export failing",
    "Cab delay / no-show complaint",
    "How-to / feature request",
    "Login / access issue",
    "OTP / boarding issue",
    "Billing / invoice discrepancy",
    "Employee address / geocode change",
    "Driver / vehicle compliance docs",
]

SLA_HOURS_BY_PRIORITY = {"P1": 4, "P2": 12, "P3": 24, "P4": 48}
TIER_MULTIPLIER = {"Enterprise": 0.75, "Mid-market": 1.0, "SMB": 1.25}

CATEGORY_KEYWORDS = {
    "Roster / booking not syncing": [
        "roster", "booking", "cutoff", "ad-hoc", "sync", "shift", "duplicate",
    ],
    "Live tracking / GPS incorrect": [
        "gps", "tracking", "location", "frozen", "eta", "map", "jumping",
    ],
    "Report export failing": [
        "report", "export", "loading", "excel", "csv", "download", "timeout",
    ],
    "Cab delay / no-show complaint": [
        "cab", "delay", "late", "no-show", "missing", "driver", "pickup",
    ],
    "How-to / feature request": [
        "how-to", "guide", "feature", "request", "workflow", "configure", "dashboard",
    ],
    "Login / access issue": [
        "login", "password", "access", "sso", "permission", "locked", "dashboard",
    ],
    "OTP / boarding issue": [
        "otp", "boarding", "verification", "invalid", "sms", "code", "driver app",
    ],
    "Billing / invoice discrepancy": [
        "billing", "invoice", "toll", "charge", "rate card", "vendor", "discrepancy",
    ],
    "Employee address / geocode change": [
        "address", "geocode", "location", "pin", "pickup", "employee", "coordinates",
    ],
    "Driver / vehicle compliance docs": [
        "compliance", "insurance", "license", "document", "vehicle", "registration", "expired",
    ],
}

CATEGORY_PLAYBOOKS = {
    "Roster / booking not syncing": {
        "self_fix_steps": [
            "Refresh the roster and confirm the booking cutoff time.",
            "Re-run the roster import and verify the affected employee records.",
            "Ask the client to retry the booking in a private or incognito session.",
        ],
        "escalation_checklist": [
            "Capture the booking ID, employee IDs, and shift details.",
            "Record the old and new cutoff or roster values.",
            "Attach import logs or screenshots showing the sync mismatch.",
        ],
        "high_reopen_risk": True,
    },
    "Live tracking / GPS incorrect": {
        "self_fix_steps": [
            "Have the driver reopen and refresh the RideOps app.",
            "Confirm the device GPS and location permissions are enabled.",
            "Ask the client to refresh the tracking link and compare the latest timestamp.",
        ],
        "escalation_checklist": [
            "Capture the cab, trip, and employee IDs.",
            "Record the device model and app or browser version.",
            "Attach tracking timestamps and screenshots of the incorrect location.",
        ],
        "high_reopen_risk": True,
    },
    "Report export failing": {
        "self_fix_steps": [
            "Ask the client to retry the export with a smaller date range.",
            "Check whether the report opens or downloads in another browser.",
            "Verify that the selected report filters are valid.",
        ],
        "escalation_checklist": [
            "Capture the report name, filters, and date range.",
            "Record the export format and observed error message.",
            "Attach the request time and a screenshot or download log.",
        ],
        "high_reopen_risk": True,
    },
    "Cab delay / no-show complaint": {
        "self_fix_steps": [
            "Verify the trip status and current cab assignment.",
            "Check the pickup time, location, and driver contact details.",
            "Coordinate with the transport partner to confirm a replacement cab.",
        ],
        "escalation_checklist": [
            "Capture the trip ID and affected employee details.",
            "Record the scheduled and actual pickup times.",
            "Attach driver, vehicle, and dispatch notes.",
        ],
        "high_reopen_risk": False,
    },
    "How-to / feature request": {
        "self_fix_steps": [
            "Confirm the client has the required role and module access.",
            "Share the relevant RideOps guide or in-app help.",
            "Walk through the workflow using a test or training setup.",
        ],
        "escalation_checklist": [
            "Capture the intended workflow and current behavior.",
            "Identify the client role and requested feature outcome.",
            "Attach screenshots or a short reproduction of the steps.",
        ],
        "high_reopen_risk": False,
    },
    "Login / access issue": {
        "self_fix_steps": [
            "Verify the user's account status and assigned role.",
            "Ask the user to clear cached credentials and sign in again.",
            "For SSO users, confirm the identity-provider login succeeds.",
        ],
        "escalation_checklist": [
            "Capture the user email and affected application module.",
            "Record the authentication method and exact error message.",
            "Attach relevant browser or SSO logs with timestamps.",
        ],
        "high_reopen_risk": False,
    },
    "OTP / boarding issue": {
        "self_fix_steps": [
            "Confirm the employee phone number and trip are on the same account.",
            "Ask the employee to request one new OTP and retry boarding.",
            "Verify the OTP is entered within its validity window.",
        ],
        "escalation_checklist": [
            "Capture the trip ID, employee ID, and OTP delivery channel.",
            "Record the exact OTP error shown in the driver app.",
            "Attach timestamps and SMS or push-delivery evidence.",
        ],
        "high_reopen_risk": True,
    },
    "Billing / invoice discrepancy": {
        "self_fix_steps": [
            "Recheck the trip count and applicable rate card.",
            "Verify toll, vendor, tax, and discount entries on the invoice.",
            "Compare the invoice against the approved billing configuration.",
        ],
        "escalation_checklist": [
            "Capture the invoice number and discrepancy period.",
            "List the disputed trips or charges with amounts.",
            "Attach the invoice and supporting rate-card or vendor records.",
        ],
        "high_reopen_risk": False,
    },
    "Employee address / geocode change": {
        "self_fix_steps": [
            "Validate the new address and postal or locality details.",
            "Refresh the geocoded pickup location and confirm the map pin.",
            "Ask the client to rebook or update the employee's address profile.",
        ],
        "escalation_checklist": [
            "Capture the employee ID and old and new addresses.",
            "Record the geocode result and map coordinates.",
            "Attach screenshots showing the incorrect pickup location.",
        ],
        "high_reopen_risk": True,
    },
    "Driver / vehicle compliance docs": {
        "self_fix_steps": [
            "Verify the document type and expiry date in RideOps.",
            "Ask the vendor to upload a clear, valid replacement document.",
            "Confirm the vehicle or driver profile was revalidated after upload.",
        ],
        "escalation_checklist": [
            "Capture the driver or vehicle ID and document type.",
            "Record the expiry date and current compliance status.",
            "Attach the rejected or expiring document and validation message.",
        ],
        "high_reopen_risk": False,
    },
}

CLOSURE_VERIFICATION_ITEMS = [
    "Confirm the issue is resolved and the client can complete the original workflow.",
    "Record the final outcome, affected records, and any engineering ticket reference.",
    "Verify all required evidence is attached and communicate the resolution to the client.",
]
