"""QuestArc in Pensum without widgets: the choice records in
pluginUserData, the engine through gjs, setting up a stage's task and the
messages. The engine tests need gjs and QuestArc's engine
(PENSUM_QUESTARC_DIR, PENSUM_GJS; docs/journeys.md); CI sets
PENSUM_REQUIRE_ENGINE=1 so they fail instead of being skipped there."""
import base64
import gzip
import os

import pytest

from pensum.game import content, engine, records, sentences, stages
from pensum.store import defaults, tasks, validate
from pensum.store.dataset import Dataset
from pensum.store.repeat import instances
from pensum.store.repeat.instances import noon_ms

NOW = noon_ms("2026-11-04")  # Wednesday


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def test_records_round_trip_with_compression(ds):
    long_why = "x" * 2000
    records.write(ds, {"run:r": {"journeyId": "j", "why": long_why}, "build:r": {"hue": "sand"}})
    entry = next(e for e in ds.data["pluginUserData"] if e["id"] == "questarc:run:r")
    assert entry["data"].startswith("GZ1:")
    assert gzip.decompress(base64.b64decode(entry["data"][4:])).decode().startswith("{")
    ds.data["pluginUserData"].append({"id": "other-plugin:x", "data": "{}"})
    assert records.load(ds) == {"run:r": {"journeyId": "j", "why": long_why},
                                "build:r": {"hue": "sand"}}
    records.write(ds, {"build:r": ""})
    assert "build:r" not in records.load(ds)
    assert validate.problems(ds.data) == []


def test_supported_rules():
    assert stages.supported({"repeatCycle": "DAILY", "repeatEvery": 3})
    assert not stages.supported({"repeatCycle": "DAILY", "repeatEvery": 8})
    assert stages.supported({"repeatCycle": "WEEKLY", "repeatEvery": 1, "friday": True})
    assert not stages.supported({"repeatCycle": "WEEKLY", "repeatEvery": 2, "friday": True})
    assert not stages.supported({"repeatCycle": "MONTHLY", "repeatEvery": 1})
    assert not stages.supported({"repeatCycle": "DAILY", "repeatEvery": 1,
                                 "waitForCompletion": True})


def test_stage_schedules_become_rules():
    assert stages.rule_fields({"type": "daily"}, "2026-11-04")["quickSetting"] == "DAILY"
    every = stages.rule_fields({"type": "everyNDays", "n": 2}, "2026-11-04")
    assert (every["repeatCycle"], every["repeatEvery"]) == ("DAILY", 2)
    work = stages.rule_fields({"type": "weekdays", "days": ["mon", "tue", "wed", "thu", "fri"]},
                              "2026-11-04")
    assert work["quickSetting"] == "MONDAY_TO_FRIDAY"


engine_ready = content.available()
needs_engine = pytest.mark.skipif(
    not engine_ready and not os.environ.get("PENSUM_REQUIRE_ENGINE"),
    reason="needs gjs and QuestArc's engine (PENSUM_QUESTARC_DIR, PENSUM_GJS)")


@needs_engine
def test_journeys_and_texts_come_from_questarc():
    ids = [j["id"] for j in content.journeys()]
    assert {"first-things-first", "gentle-morning"} <= set(ids)
    assert content.t("gentle-morning.title") == "A gentle morning"
    assert content.t("ui.build.stations") == "Stations"
    morning = content.journey("gentle-morning")
    assert sentences.plan_sentence(morning["stages"][0]) == \
        "After getting up, I will drink a glass of water (in the kitchen)."


@needs_engine
def test_walk_a_journey_through_the_engine(ds):
    journey = content.journey("gentle-morning")
    records.write(ds, engine.action("startJourney", {"runId": "run1", "journey": journey,
                                                     "startDay": "2026-11-04"}))
    view = engine.evaluate(ds, NOW)
    assert view["active"]["stations"][0]["state"] == "unbound"

    task = stages.create_stage_task(ds, "run1", journey["stages"][0], "2026-11-04", NOW)
    assert task["title"] == "Getting up: drink a glass of water"
    cfg = ds.data["taskRepeatCfg"]["entities"][task["repeatCfgId"]]
    assert cfg["repeatCycle"] == "DAILY"
    before = engine.evaluate(ds, NOW)
    assert before["active"]["stations"][0]["state"] == "current"

    tasks.set_done(ds, task["id"], True, NOW)
    after, events = engine.evaluate_and_diff(ds, before, NOW)
    assert after["active"]["stations"][0]["completions"] == 1
    assert "totalXp" not in after and "mode" not in after
    message = sentences.message_for(events, after, content.journeys())
    assert message == "Drink a glass of water: done. 1 of 5 days."

    # The next days' instances are made by the repeat rule and count too.
    for day in ("2026-11-05", "2026-11-06", "2026-11-07", "2026-11-08"):
        now = noon_ms(day)
        new = instances.create_due(ds, now)
        assert [t["id"] for t in new] == [instances.instance_id(cfg["id"], day)]
        tasks.set_done(ds, new[0]["id"], True, now)
    view = engine.evaluate(ds, noon_ms("2026-11-08"))
    assert view["active"]["stations"][0]["state"] == "met"
    records.write(ds, engine.action("continueJourney", view["active"], journey, "2026-11-08"))
    view = engine.evaluate(ds, noon_ms("2026-11-08"))
    assert view["active"]["position"]["stage"] == 1
    assert view["problems"] == []
    assert validate.problems(ds.data) == []


@needs_engine
def test_pausing_the_bound_rule_writes_a_pause_record(ds):
    journey = content.journey("gentle-morning")
    records.write(ds, engine.action("startJourney", {"runId": "r", "journey": journey,
                                                     "startDay": "2026-11-04"}))
    stages.create_stage_task(ds, "r", journey["stages"][0], "2026-11-04", NOW)
    view = engine.evaluate(ds, NOW)
    assert stages.bound_rule(ds, view) is not None
    records.write(ds, engine.action("repeatPause", "r", "2026-11-04", True))
    assert records.load(ds)["pause:r:2026-11-04"] == {"action": "pause", "source": "repeat-cfg"}
    assert engine.evaluate(ds, NOW)["active"]["paused"] is True


def test_engine_error_without_questarc(monkeypatch, tmp_path):
    monkeypatch.setenv("PENSUM_QUESTARC_DIR", str(tmp_path))
    with pytest.raises(engine.EngineError):
        engine.run({"evaluate": {}})
