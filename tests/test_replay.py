"""Replaying Super Productivity's ops (pensum.sync.replay, #30): each
transcribed rule, refusal of everything else, and validate.problems()
empty afterwards. The real app checks the same in tests/real_app
(check_sync.py: round 1 + the ops since == round 2)."""
from datetime import datetime

import pytest

from pensum.store import defaults, validate
from pensum.sync.replay import Unsupported, apply

NOW = int(datetime(2026, 11, 12, 12, 0).timestamp() * 1000)
TODAY = "2026-11-12"


def dataset():
    data = defaults.fresh_dataset(NOW)
    project = {**defaults.get("project"), "id": "p1", "title": "P", "taskIds": [],
               "backlogTaskIds": [], "isEnableBacklog": True}
    data["project"]["ids"].append("p1")
    data["project"]["entities"]["p1"] = project
    tag = {**defaults.get("tag"), "id": "t1", "title": "T", "taskIds": []}
    data["tag"]["ids"].append("t1")
    data["tag"]["entities"]["t1"] = tag
    return data


def task(tid, **fields):
    return {"id": tid, "title": tid, "subTaskIds": [], "timeSpentOnDay": {},
            "timeSpent": 0, "timeEstimate": 0, "isDone": False, "tagIds": [],
            "created": NOW, "attachments": [], "projectId": "p1", **fields}


def add(tid, bottom=False, backlog=False, **fields):
    return {"a": "HA", "p": {"actionPayload": {
        "task": task(tid, **fields), "isAddToBottom": bottom,
        "isAddToBacklog": backlog, "workContextId": "p1",
        "workContextType": "PROJECT"}}}


def upd(tid, **changes):
    return {"actionType": "[Task Shared] updateTask",
            "payload": {"actionPayload": {"task": {"id": tid, "changes": changes}}}}


def sub(tid, parent, **fields):
    return {"a": "TA", "p": {"actionPayload": {"task": task(tid, **fields),
                                               "parentId": parent}}}


def delete(data, tid):
    t = data["task"]["entities"][tid]
    subs = [data["task"]["entities"][s] for s in t["subTaskIds"]]
    return {"a": "HD", "p": {"actionPayload": {"task": {**t, "subTasks": subs}}}}


def run(data, *ops):
    out = apply(data, list(ops), now_ms=NOW)
    assert validate.problems(out) == []
    return out


def test_add_top_bottom_backlog_today_and_planner():
    out = run(dataset(), add("a"), add("b"), add("c", bottom=True),
              add("d", backlog=True), add("e", dueDay=TODAY, tagIds=["TODAY", "t1"]),
              add("f", dueDay="2026-11-20"))
    project = out["project"]["entities"]["p1"]
    assert project["taskIds"] == ["f", "e", "b", "a", "c"]
    assert project["backlogTaskIds"] == ["d"]
    assert out["task"]["entities"]["e"]["tagIds"] == ["t1"]  # Today is virtual
    assert out["tag"]["entities"]["TODAY"]["taskIds"] == ["e"]
    assert out["tag"]["entities"]["t1"]["taskIds"] == ["e"]
    assert out["planner"]["days"]["2026-11-20"] == ["f"]


def test_add_repeat_instance_takes_previous_place():
    data = dataset()
    data["taskRepeatCfg"]["ids"].append("r")
    data["taskRepeatCfg"]["entities"]["r"] = {"id": "r"}
    data = run(data, add("a"), add("old", repeatCfgId="r"), add("b"))
    out = run(data, add("new", repeatCfgId="r", created=NOW + 1))
    assert out["project"]["entities"]["p1"]["taskIds"] == ["b", "new", "old", "a"]


def test_subtask_inherits_parent_time_and_recalculates():
    data = run(dataset(), add("p", timeEstimate=600, timeSpentOnDay={TODAY: 60}))
    out = run(data, sub("s1", "p"), sub("s2", "p", timeEstimate=100))
    tasks = out["task"]["entities"]
    assert tasks["s1"]["timeEstimate"] == 600 and tasks["s1"]["timeSpent"] == 60
    assert tasks["p"]["subTaskIds"] == ["s1", "s2"]
    assert tasks["p"]["timeEstimate"] == 540 + 100
    assert tasks["s1"]["projectId"] == "p1" and tasks["s2"]["tagIds"] == []


def test_update_title_done_and_undone():
    data = run(dataset(), add("a"))
    out = run(data, upd("a", title="New", isDone=True, doneOn=NOW - 5))
    a = out["task"]["entities"]["a"]
    assert a["title"] == "New" and a["isDone"] and a["doneOn"] == NOW - 5
    assert a["modified"] == NOW
    out = run(out, upd("a", isDone=False))
    assert "doneOn" not in out["task"]["entities"]["a"]


def test_done_without_done_on_uses_now_and_drops_in_progress_tag():
    data = dataset()
    data["tag"]["ids"].append("KANBAN_IN_PROGRESS")
    data["tag"]["entities"]["KANBAN_IN_PROGRESS"] = {
        **defaults.get("tag"), "id": "KANBAN_IN_PROGRESS", "taskIds": []}
    data = run(data, add("a", tagIds=["KANBAN_IN_PROGRESS", "t1"]))
    out = run(data, upd("a", isDone=True))
    assert out["task"]["entities"]["a"]["doneOn"] == NOW
    assert out["task"]["entities"]["a"]["tagIds"] == ["t1"]


def test_done_keeps_schedule_and_today_order():
    data = run(dataset(), add("a", dueDay="2026-11-10"))
    out = run(data, upd("a", isDone=True, dueDay=TODAY, doneOn=NOW))
    assert out["task"]["entities"]["a"]["dueDay"] == "2026-11-10"
    data = run(dataset(), add("b", dueDay=TODAY))
    data["tag"]["entities"]["TODAY"]["taskIds"] = []
    out = run(data, upd("b", isDone=True, doneOn=NOW))
    assert out["tag"]["entities"]["TODAY"]["taskIds"] == ["b"]


def test_tags_change_order():
    data = run(dataset(), add("a"), add("b", tagIds=["t1"]))
    out = run(data, upd("a", tagIds=["t1"]))
    assert out["tag"]["entities"]["t1"]["taskIds"] == ["a", "b"]
    out = run(out, upd("a", tagIds=[]))
    assert out["tag"]["entities"]["t1"]["taskIds"] == ["b"]


def test_due_day_moves_between_planner_and_today():
    data = run(dataset(), add("a", dueDay="2026-11-20"))
    out = run(data, upd("a", dueDay=TODAY))
    assert out["planner"]["days"]["2026-11-20"] == []
    assert out["tag"]["entities"]["TODAY"]["taskIds"] == ["a"]
    out = run(out, upd("a", dueDay="2026-11-21"))
    assert out["tag"]["entities"]["TODAY"]["taskIds"] == []
    assert out["planner"]["days"]["2026-11-21"] == ["a"]


def test_subtask_time_and_estimate_reach_parent():
    data = run(dataset(), add("p"), sub("s1", "p", timeEstimate=100),
               sub("s2", "p", timeEstimate=50))
    out = run(data, upd("s1", timeSpentOnDay={TODAY: 30}), upd("s2", timeEstimate=80))
    p = out["task"]["entities"]["p"]
    assert p["timeSpentOnDay"] == {TODAY: 30} and p["timeSpent"] == 30
    assert p["timeEstimate"] == 70 + 80
    out = run(out, upd("s2", isDone=True, doneOn=NOW))
    assert out["task"]["entities"]["p"]["timeEstimate"] == 70


def test_delete_parent_with_subtasks_everywhere():
    data = run(dataset(), add("p", tagIds=["t1"]), sub("s", "p"), add("b"))
    data["section"]["ids"].append("x")
    data["section"]["entities"]["x"] = {"id": "x", "taskIds": ["p", "s", "b"]}
    out = run(data, delete(data, "p"))
    assert set(out["task"]["ids"]) == {"b"}
    assert out["project"]["entities"]["p1"]["taskIds"] == ["b"]
    assert out["tag"]["entities"]["t1"]["taskIds"] == []
    assert out["section"]["entities"]["x"]["taskIds"] == ["b"]


def test_delete_last_subtask_gives_times_back_to_parent():
    data = run(dataset(), add("p"), sub("s", "p", timeEstimate=90,
                                        timeSpentOnDay={TODAY: 10}))
    out = run(data, delete(data, "s"))
    p = out["task"]["entities"]["p"]
    assert p["subTaskIds"] == [] and p["timeEstimate"] == 90
    assert p["timeSpentOnDay"] == {TODAY: 10}


def test_sync_settings_change_is_local_only():
    data = dataset()
    out = run(data, {"a": "CU", "p": {"actionPayload": {"sectionKey": "sync",
                                                         "sectionCfg": {"isEnabled": True}}}})
    assert out["globalConfig"] == data["globalConfig"]


@pytest.mark.parametrize("op", [
    {"a": "ZZ", "p": {}},
    {"actionType": "[Task Shared] moveToArchive", "payload": "{}"},
    upd("a", projectId="p1"),
    add("x", deadlineDay=TODAY),
    {"a": "CU", "p": {"actionPayload": {"sectionKey": "misc", "sectionCfg": {}}}},
])
def test_refuses_what_is_not_transcribed(op):
    data = run(dataset(), add("a"))
    with pytest.raises(Unsupported):
        apply(data, [op], now_ms=NOW)


def test_replay_leaves_the_input_alone():
    data = run(dataset(), add("a"))
    before = repr(data)
    apply(data, [upd("a", title="x")], now_ms=NOW)
    assert repr(data) == before
