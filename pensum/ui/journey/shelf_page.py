"""The shelf (QuestArc docs/behaviour.md, screen 7): waiting journeys to
resume; **Habits that stay**, the habits of finished journeys still
followed, with their last days, run and the quiet actions **Let It
Graduate** and the weekly look back, or **Set up the task** when its
task no longer repeats; **Running by themselves**, the
graduated habits with **Answer One Question** or **Bring It Back**; and
the finished journeys."""
from gi.repository import Adw, Gtk

from pensum.game.content import t
from pensum.game.sentences import plan_sentence, short_date
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.card import last_days
from pensum.ui.journey.habits import habits_of

FOLLOWED = ("maintained", "unbound", "unsupported-repeat")


def _label(text, *classes):
    return Gtk.Label(label=text, xalign=0, wrap=True, css_classes=list(classes))


def _quiet(label, on_click):
    button = Gtk.Button(label=label, css_classes=["flat"], halign=Gtk.Align.START)
    button.set_size_request(-1, 44)
    button.connect("clicked", lambda *_: on_click())
    return button


class ShelfPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.shelf.title"), "journey-shelf")
        self.listen(self.refresh)
        self.refresh()

    def refresh(self):
        self.clear()
        view = self.model.view or {}
        paused, finished = view.get("paused") or [], view.get("finished") or []
        if not paused and not finished:
            self.text(t("ui.shelf.empty"), "dimmed")
            return
        if paused:
            group = self.group(t("ui.shelf.paused"))
            for run in paused:
                journey = self.model.journey(run["journeyId"])
                row = Adw.ActionRow(title=t(journey["title"]) if journey else run["journeyId"],
                                    subtitle=t("ui.shelf.waiting", n=run["position"]["stage"] + 1,
                                               total=len(run["stations"])))
                button = Gtk.Button(label=t("ui.action.resume"), valign=Gtk.Align.CENTER)
                button.connect("clicked", lambda _b, r=run: self._resume(r))
                row.add_suffix(button)
                group.add(row)
        habits = habits_of(self.model)
        followed = [h for h in habits if h[3]["state"] in FOLLOWED]
        graduated = [h for h in habits if h[3]["state"] == "graduated"]
        if followed:
            group = self.group(t("ui.shelf.habits"))
            for entry in followed:
                group.add(self._followed(*entry))
        if graduated:
            group = self.group(t("ui.shelf.graduated"))
            for entry in graduated:
                group.add(self._graduated(*entry))
        if finished:
            journeys = self.group(t("ui.shelf.journeys"))
            for run in finished:
                journey = self.model.journey(run["journeyId"])
                if not journey:
                    continue
                done = [i for i, s in enumerate(run["stations"]) if s["state"] == "done"]
                end = run["stations"][done[-1]].get("doneDay") if done else None
                key = "ui.shelf.finished" if len(done) == len(run["stations"]) \
                    else "ui.shelf.ended"
                journeys.add(Adw.ActionRow(title=t(journey["title"]), subtitle=t(
                    key, start=short_date(run["startDay"]),
                    end=short_date(end) if end else "…")))

    def _entry(self, run, stage):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=10,
                      margin_bottom=6, margin_start=12, margin_end=12,
                      css_classes=["pensum-journey-habit"])
        box.append(_label(plan_sentence(stage, run["stations"][-1].get("pair"),
                                        run.get("anchor")), "heading"))
        return box

    def _followed(self, run, _journey, stage, habit):
        box = self._entry(run, stage)
        if habit.get("lastDays"):
            box.append(last_days(habit["lastDays"]))
        if habit.get("run"):
            r = habit["run"]
            box.append(_label(t("ui.card.run", current=r["current"], best=r["best"],
                                total=r["total"]), "caption", "dimmed"))
        if habit["state"] == "maintained":
            box.append(_label(t("ui.shelf.maintained"), "caption", "dimmed"))
        else:
            unbound = habit["state"] == "unbound"
            box.append(_label(t("ui.shelf.no-task" if unbound else "ui.card.unsupported"),
                              "caption", "dimmed"))
            box.append(_quiet(t("ui.action.setup" if unbound else "ui.action.change-repeat"),
                              lambda: self._push_setup(run["runId"])))
        if habit.get("backDay"):
            box.append(_label(t("ui.shelf.back", date=short_date(habit["backDay"])),
                              "caption", "dimmed"))
        if habit.get("canGraduate"):
            box.append(_quiet(t("ui.graduate.title"),
                              lambda: self._push_graduate(run["runId"])))
        if habit.get("checkinDue"):
            box.append(_quiet(t("ui.checkin.title-4" if habit.get("fourWeekly")
                                else "ui.checkin.title"),
                              lambda: self._push_checkin(run["runId"])))
        return box

    def _graduated(self, run, _journey, stage, habit):
        box = self._entry(run, stage)
        graduated = habit["graduated"]
        box.append(_label(t("ui.shelf.since", date=short_date(graduated["day"])),
                          "caption", "dimmed"))
        if graduated.get("suggestBack"):
            box.append(_label(t("ui.still.back.said"), "caption", "dimmed"))
        label = t("ui.shelf.still") if graduated.get("checkDue") else t("ui.action.bring-back")
        box.append(_quiet(label, lambda: self._push_still(run["runId"])))
        return box

    def _push_setup(self, run_id):
        from pensum.ui.journey.setup_page import SetupPage
        self.window.nav.push(SetupPage(self.window, run_id))

    def _push_graduate(self, run_id):
        from pensum.ui.journey.graduate_page import GraduatePage
        self.window.nav.push(GraduatePage(self.window, run_id))

    def _push_still(self, run_id):
        from pensum.ui.journey.still_page import StillPage
        self.window.nav.push(StillPage(self.window, run_id))

    def _push_checkin(self, run_id):
        from pensum.ui.journey.checkin_page import CheckinPage
        self.window.nav.push(CheckinPage(self.window, run_id))

    def _resume(self, run):
        active = self.model.active()
        self.model.action("resumeJourney", run["runId"], self.model.view["todayStr"],
                          active["runId"] if active else None)
        self.back_to_journey()
