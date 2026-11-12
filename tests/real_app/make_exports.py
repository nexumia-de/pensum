"""Write the Pensum exports the real-app test imports into Super
Productivity, without a display (docs/dev-environment.md, real app):

- fixture.json: Super Productivity's e2e backup, imported and changed
  through pensum.store as issue #2 lists;
- fresh.json: a dataset started fresh in Pensum with some data;
- demo.json: the demo dataset with QuestArc's records;
- imported.json: the changed fixture with a withdrawn QuestArc record,
  imported over the demo dataset as the import dialog does (#47): the
  demo's records that the file lacks are kept.

Next to each file, <name>.expect.json says what Super Productivity must
show after the import: counts, project titles and a few field values.
Made-up titles only, never real tasks.

    python3 tests/real_app/make_exports.py OUT_DIR [--broken]

--broken also writes broken.json: the fixture with a task pointing at a
missing project, which the test must reject.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pensum import demo  # noqa: E402
from pensum.game import records  # noqa: E402
from pensum.store import (archive, backup, contexts, dates, defaults,  # noqa: E402
                          incoming, tasks, tracking, validate)
from pensum.store.dataset import Context, Dataset  # noqa: E402
from pensum.store.repeat import instances, rules  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "test-backup-with-archives.json"
MINUTE = 60_000
# The unchanged fixture: what Super Productivity logs when it imports its
# own file is not Pensum's doing (its globalConfig is older than the app).
BASELINE = "fixture-original"


def changed_fixture(now):
    """Super Productivity's fixture, changed in every way #2 lists."""
    ds = Dataset(backup.read(FIXTURE))
    today = ds.today(now)
    garden = contexts.add_project(ds, "Real App Garden", now)
    gone = contexts.add_project(ds, "Real App Deleted", now)
    tag = contexts.add_tag(ds, "real-app-errands", now)

    parent = tasks.add_task(ds, "Real app parent", Context.today(), now)
    tasks.move_to_project(ds, parent["id"], garden["id"], now)
    tasks.set_tags(ds, parent["id"], [tag["id"]], now)
    first = tasks.add_subtask(ds, parent["id"], "Real app subtask one", now)
    second = tasks.add_subtask(ds, parent["id"], "Real app subtask two", now)
    tasks.set_estimate(ds, second["id"], 20 * MINUTE, now)
    tracking.set_current(ds, first["id"])
    tracking.add_time(ds, first["id"], 25 * MINUTE, now)
    tracking.set_current(ds, None)
    tasks.set_done(ds, first["id"], True, now)

    later = tasks.add_task(ds, "Real app planned", Context("project", garden["id"]), now)
    tasks.schedule_day(ds, later["id"], dates.shift_day(today, 2), now)

    for title in ("Real app lost one", "Real app lost two"):
        tasks.add_task(ds, title, Context("project", gone["id"]), now)
    contexts.delete_project(ds, gone["id"])

    # A daily rule started three days ago: its first instance is done and
    # archived by Finish Day, the next one is created for today.
    water = tasks.add_task(ds, "Real app water plants", Context.today(), now)
    rule = rules.make_recurring(ds, water["id"], rules.schedule_fields(
        "DAILY", dates.shift_day(today, -3)), now)
    tasks.set_done(ds, water["id"], True, now)
    done = tasks.add_task(ds, "Real app finished", Context.today(), now)
    tasks.set_done(ds, done["id"], True, now)
    inbox = Context("project", defaults.INBOX_ID)
    archive.archive_tasks(ds, [t["id"] for t in archive.finishable(ds, inbox, today)], now)
    instance = instances.create_due(ds, now)[0]

    fields = [(parent["id"], "title", "Real app parent"),
              (parent["id"], "projectId", garden["id"]),
              (parent["id"], "tagIds", [tag["id"]]),
              (parent["id"], "subTaskIds", [first["id"], second["id"]]),
              (first["id"], "isDone", True),
              (first["id"], "timeSpentOnDay", {today: 25 * MINUTE}),
              (second["id"], "timeEstimate", 20 * MINUTE),
              (later["id"], "dueDay", dates.shift_day(today, 2)),
              (instance["id"], "repeatCfgId", rule["id"])]
    archived = [water["id"], done["id"]]
    return ds, fields, archived, [garden["title"]], [gone["id"]], BASELINE


def fresh(now):
    """A dataset started in Pensum without an import."""
    ds = Dataset(defaults.fresh_dataset(now))
    home = contexts.add_project(ds, "Fresh Home", now)
    tag = contexts.add_tag(ds, "fresh-calls", now)
    call = tasks.add_task(ds, "Fresh call the bakery", Context.today(), now)
    tasks.set_tags(ds, call["id"], [tag["id"]], now)
    shelf = tasks.add_task(ds, "Fresh build the shelf", Context("project", home["id"]), now)
    sub = tasks.add_subtask(ds, shelf["id"], "Fresh buy screws", now)
    tracking.add_time(ds, sub["id"], 10 * MINUTE, now)
    inbox = tasks.add_task(ds, "Fresh inbox note", Context("project", defaults.INBOX_ID), now)
    tasks.set_done(ds, inbox["id"], True, now)
    fields = [(call["id"], "tagIds", [tag["id"]]),
              (shelf["id"], "projectId", home["id"]),
              (sub["id"], "timeSpent", 10 * MINUTE),
              (inbox["id"], "isDone", True)]
    return ds, fields, [], [home["title"]], [], None


def demo_data(now):
    ds = demo.create(now)
    task_id = ds.data["tag"]["entities"]["demo-calls"]["taskIds"][0]
    fields = [(task_id, "tagIds", ["demo-calls"]),
              (task_id, "timeEstimate", 10 * MINUTE)]
    return ds, fields, [], ["Garden", "Website Relaunch"], [], None


def imported(now):
    """The changed fixture, with one QuestArc record withdrawn, imported
    over the demo dataset: the step of Files.import_dataset that changes
    the data (Files itself needs phosh-toolkit, which this job lacks)."""
    ds, fields, archived, titles, missing, baseline = changed_fixture(now)
    records.write(ds, {"run:demo": ""})
    current = demo.create(demo.demo_now())
    incoming.keep_records(current.data, ds.data, records.PREFIX)
    stored = {e["id"]: e["data"] for e in ds.data["pluginUserData"]}
    if stored.get("questarc:run:demo") != "" or "questarc:binding:demo:focus-15" not in stored:
        raise SystemExit("imported: the import did not keep the local records")
    return ds, fields, archived, titles, missing, baseline


def expectation(ds, fields, archived, titles, missing, baseline):
    young = ds.data["archiveYoung"]["task"]["ids"]
    return {"tasks": len(ds.data["task"]["ids"]),
            "projects": len(ds.data["project"]["ids"]),
            "tags": len(ds.data["tag"]["ids"]),
            "repeatCfgs": len(ds.data["taskRepeatCfg"]["ids"]),
            "archived": sorted(set(archived) & set(young)),
            "fields": [{"id": i, "field": f, "value": v} for i, f, v in fields],
            "projectTitles": titles,
            "missingProjects": missing,
            "pluginUserData": len(ds.data.get("pluginUserData") or []),
            "baseline": baseline}


def write(out, name, made, now):
    ds, *rest = made
    found = validate.problems(ds.data)
    if found:
        raise SystemExit(f"{name}: {len(found)} problems before export, first: {found[0]}")
    backup.write(out / f"{name}.json", ds.data, now)
    expect = expectation(ds, *rest)
    (out / f"{name}.expect.json").write_text(json.dumps(expect, indent=1))
    print(f"{name}: {expect['tasks']} tasks, {expect['projects']} projects, "
          f"{expect['repeatCfgs']} repeat rules")
    return ds, expect


def write_broken(out, ds, expect, now):
    """The fixture with one task moved to a project that does not exist."""
    data = json.loads(json.dumps(ds.data))
    task_id = expect["fields"][0]["id"]
    data["task"]["entities"][task_id]["projectId"] = "real-app-missing-project"
    backup.write(out / "broken.json", data, now)
    (out / "broken.expect.json").write_text(json.dumps(expect, indent=1))
    print(f"broken: task {task_id} points at a missing project")


def main(argv):
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    now = dates.now_ms()
    (out / f"{BASELINE}.json").write_bytes(FIXTURE.read_bytes())
    fixture = write(out, "fixture", changed_fixture(now), now)
    write(out, "fresh", fresh(now), now)
    write(out, "demo", demo_data(demo.demo_now()), now)
    write(out, "imported", imported(now), now)
    if "--broken" in argv:
        write_broken(out, *fixture, now)


if __name__ == "__main__":
    main(sys.argv)
