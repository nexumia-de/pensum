"""Banners above the current station's card (QuestArc docs/behaviour.md,
screen 4): paused, a hard week with the earlier step and the user's
reason, the weekly look back and a new learning nugget. Closed banners
are remembered in Pensum's settings."""
from datetime import date

from gi.repository import Adw

from pensum.game.content import t
from pensum.game.sentences import short_date


def iso_week(day):
    year, week, _ = date.fromisoformat(day).isocalendar()
    return f"{year}-W{week:02d}"


def _banner(title, button, on_click):
    banner = Adw.Banner(title=title, revealed=True, use_markup=False)
    if button:
        banner.set_button_label(button)
        banner.connect("button-clicked", lambda *_: on_click())
    return banner


def banners(page, run, journey, index):
    model, window = page.model, page.window
    today = model.view["todayStr"]
    stage = journey["stages"][index]
    seen = window.settings.seen
    out = []

    def close(key):
        if key not in seen:
            seen.append(key)
            window.save_settings()
        page.refresh()

    if run["paused"]:
        pauses = sorted(k for k in model.records() if k.startswith(f"pause:{run['runId']}:"))
        last = pauses[-1] if pauses else None
        by_user = last and (model.records().get(last) or {}).get("action") == "pause" and \
            (model.records().get(last) or {}).get("source") == "user"
        if by_user:
            out.append(_banner(t("ui.banner.paused", date=short_date(last.split(":")[2])),
                               t("ui.action.resume"),
                               lambda: model.action("resumeJourney", run["runId"], today)))
        else:
            out.append(_banner("Paused: the task's repeat is paused. Paused days don't count.",
                               None, None))
        return out

    key = f"fallback:{run['runId']}:{today}"
    if run["offerFallback"] and key not in seen:
        previous = journey["stages"][index - 1] if index > 0 else None
        text = t("ui.banner.fallback", action=t(previous["plan"]["action"])) if previous \
            else t("ui.banner.fallback-first")
        if run.get("why"):
            text += " " + t("ui.banner.why", why=run["why"])
        out.append(_banner(text, t("ui.action.good-to-know"), lambda: close(key)))

    week_key = f"checkin:{run['runId']}:{stage['id']}:{iso_week(today)}"
    if run["checkinDue"] and week_key not in seen:
        out.append(_banner(t("ui.banner.checkin"), t("ui.action.answer"), page.show_checkin))

    nugget_key = f"nugget:{run['runId']}:{stage['id']}"
    if stage.get("nugget") and nugget_key not in seen and \
            run["stations"][index]["state"] != "ahead":
        out.append(_banner(t("ui.banner.nugget", nugget=t(stage["nugget"])),
                           t("ui.action.got-it"), lambda: close(nugget_key)))
    return out
