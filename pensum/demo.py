"""A made-up dataset for screenshots and trying Pensum (PENSUM_DEMO=1):
recorded values, never live data. No GTK."""
from datetime import datetime, timedelta

from pensum.store import contexts, defaults, tasks, tracking
from pensum.store.dataset import Context, Dataset

def demo_now():
    """10:30 today: the made-up day always is the current one, so Today is
    filled whenever the demo starts."""
    moment = datetime.now().replace(hour=10, minute=30, second=0, microsecond=0)
    return int(moment.timestamp() * 1000)


def create(now=None):
    now = now or demo_now()
    ds = Dataset(defaults.fresh_dataset(now - 86_400_000 * 30))
    ms = lambda minutes: minutes * 60_000  # noqa: E731
    # Fixed ids, so the screenshots can open a list (release.toml).
    garden = contexts.add_project(ds, "Garden", entity_id="demo-garden")
    work = contexts.add_project(ds, "Website Relaunch", entity_id="demo-website")
    calls = contexts.add_tag(ds, "calls", now, entity_id="demo-calls")
    errands = contexts.add_tag(ds, "errands", now, entity_id="demo-errands")
    today = Context.today()

    review = tasks.add_task(ds, "Review the new start page", today, now, top=False)
    tasks.move_to_project(ds, review["id"], work["id"], now)
    for title, estimate, spent in (("Check texts on 360 px", 30, 25),
                                   ("Compare loading times", 20, 0),
                                   ("Write feedback for the team", 15, 0)):
        sub = tasks.add_subtask(ds, review["id"], title, now)
        tasks.set_estimate(ds, sub["id"], ms(estimate), now)
        if spent:
            tracking.add_time(ds, sub["id"], ms(spent), now - ms(40))
    first = ds.tasks[review["subTaskIds"][0]]
    tasks.set_done(ds, first["id"], True, now - ms(10))

    call = tasks.add_task(ds, "Call the plumber about the boiler", today, now, top=False)
    tasks.set_tags(ds, call["id"], [calls["id"]], now)
    tasks.set_estimate(ds, call["id"], ms(10), now)
    tasks.set_priority(ds, call["id"], 3, now)

    seeds = tasks.add_task(ds, "Buy tomato seeds", today, now, top=False)
    tasks.move_to_project(ds, seeds["id"], garden["id"], now)
    tasks.set_tags(ds, seeds["id"], [errands["id"]], now)

    mail = tasks.add_task(ds, "Answer emails", today, now, top=False)
    tasks.set_estimate(ds, mail["id"], ms(30), now)
    tracking.add_time(ds, mail["id"], ms(35), now - ms(90))
    tasks.set_done(ds, mail["id"], True, now - ms(55))

    tasks.update(ds, review["id"], now,
                 notes="Focus on the phone layout first; the desktop "
                       "version was reviewed last week.")
    tasks.set_estimate(ds, call["id"], ms(10), now)

    for title in ("Prune the apple tree", "Order compost"):
        tasks.add_task(ds, title, Context("project", garden["id"]), now, top=False)
    plan = tasks.add_task(ds, "Plan the launch date", Context("project", work["id"]), now,
                          top=False)
    tasks.schedule_day(ds, plan["id"], (datetime.fromtimestamp(now / 1000)
                                        + timedelta(days=2)).strftime("%Y-%m-%d"), now)
    books = tasks.add_task(ds, "Return the library books", today, now, top=False)
    tasks.set_tags(ds, books["id"], [errands["id"]], now)
    tasks.schedule_day(ds, books["id"], (datetime.fromtimestamp(now / 1000)
                                         - timedelta(days=1)).strftime("%Y-%m-%d"), now)
    tracking.set_current(ds, review["subTaskIds"][1])
    return ds
