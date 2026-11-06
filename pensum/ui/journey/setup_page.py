"""Setting up a station's task (QuestArc docs/behaviour.md, flow B). In
Pensum, Create the Task makes the task and its repeat rule from the
stage's suggested schedule in one go; or the user picks a recurring task
they already have. A bound task whose repeat a journey cannot follow
can get a new schedule or be replaced."""
from gi.repository import Adw, Gtk

from pensum.game import stages
from pensum.game.content import t
from pensum.game.sentences import plan_sentence, schedule_text
from pensum.store.repeat import rules
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.repeat_page import describe


class SetupPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.setup.title"), "journey-setup")
        self.model.listeners.append(self._changed)
        self.connect("destroy", lambda *_: self._changed in self.model.listeners
                     and self.model.listeners.remove(self._changed))
        self.refresh()

    def _changed(self):
        current = self.model.current()
        if current and current[3]["state"] in ("current", "met"):
            self.back_to_journey()
            return
        self.refresh()

    def refresh(self):
        self.clear()
        current = self.model.current()
        if not current:
            return
        run, _journey, _index, station, stage = current
        plan = self.group(t("ui.setup.plan"))
        plan.add(Adw.ActionRow(title=plan_sentence(stage), title_lines=0,
                               subtitle=t("ui.setup.suggested",
                                          schedule=schedule_text(stage["schedule"]))))
        if station["state"] == "unsupported-repeat":
            cfg = stages.bound_rule(self.window.ds, self.model.view)
            self.text("Journeys work with tasks that repeat daily, every few days or on "
                      "chosen weekdays. You could give the task the suggested schedule, "
                      "or use another task.")
            if cfg:
                row = Adw.ActionRow(title="Use the Suggested Schedule", activatable=True,
                                    subtitle=describe(cfg))
                row.connect("activated", lambda *_: self._reschedule(cfg, stage))
                self.group().add(row)
        else:
            self.text("Day Planner follows one recurring task for this station. You could "
                      "create it now, or use a recurring task you already have.")
        self.set_main(t("ui.setup.create"), lambda: self._create(run, stage, station))
        existing = stages.supported_rules(self.window.ds)
        group = self.group(t("ui.setup.existing"), t("ui.pick.supported"))
        if not existing:
            group.add(Adw.ActionRow(title=t("ui.pick.none"), title_lines=0))
        for cfg in existing:
            row = Adw.ActionRow(title=cfg.get("title") or t("ui.pick.untitled"),
                                subtitle=describe(cfg), activatable=True)
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated", lambda _r, c=cfg: self._use(run, stage, c))
            group.add(row)

    def _start_day(self, station):
        today = self.window.ds.today()
        return max(station.get("acceptedDay") or today, today)

    def _create(self, run, stage, station):
        stages.create_stage_task(self.window.ds, run["runId"], stage,
                                 self._start_day(station))
        self.window.changed()
        self.model.refresh_now()

    def _use(self, run, stage, cfg):
        stages.bind_existing(self.window.ds, run["runId"], stage["id"], cfg["id"])
        self.window.changed()
        self.model.refresh_now()

    def _reschedule(self, cfg, stage):
        rules.update(self.window.ds, cfg["id"], **stages.rule_fields(
            stage["schedule"], cfg.get("startDate") or self.window.ds.today()))
        self.window.changed()
        self.model.refresh_now()
