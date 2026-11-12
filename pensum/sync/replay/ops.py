"""Ops in their two shapes: compact ops of the sync files (`a` short code,
`p` payload; compact-operation.types.ts) and the full ops of SuperSync
(`actionType`, `payload`). The payload of an action-based op is
{actionPayload: <the action's fields>, entityChanges: […]}
(operation.types.ts)."""
import json

from pensum.sync import SyncError

# Short codes of the supported actions (op-log/persistence/compact/
# action-type-codes.ts at 20.0.0), transcribed as data.
CODES = {
    "HA": "[Task Shared] addTask",
    "HU": "[Task Shared] updateTask",
    "HD": "[Task Shared] deleteTask",
    "TA": "[Task] Add SubTask",
    "CU": "[Global Config] Update Global Config Section",
}


def unpack(op):
    """(action type, action fields) of one op."""
    if "a" in op:
        action = CODES.get(op["a"], f"code {op['a']}")
        payload = op.get("p")
    else:
        action = op.get("actionType", "?")
        payload = op.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError as error:
            raise SyncError("A change in the sync data is damaged.") from error
    if not isinstance(payload, dict):
        raise SyncError("A change in the sync data is damaged.")
    fields = payload.get("actionPayload", payload)
    return action, fields if isinstance(fields, dict) else {}
