"""Setting up a station's task (QuestArc docs/behaviour.md, flow B). In
Pensum, Create the Task makes the task and its repeat rule from the
stage's suggested schedule in one go; or the user picks a recurring task
they already have. A bound task whose repeat a journey cannot follow
can get a new schedule or be replaced. The habit a finished journey left
gets the same page when its task no longer repeats."""
from gi.repository import Adw, Gtk

from pensum.game import stages
from pensum.game.content import t
from pensum.game.sentences import plan_sentence, schedule_text
from pensum.store.repeat import rules
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.habits import habit_of
from pensum.ui.journey.pair_row import pair_group
from pensum.ui.repeat_page import describe

# QuestArc's sentences name Super Productivity's menus; Day Planner's own.
CHOOSE = ("Day Planner follows one recurring task for this station. You could "
          "create it now, or use a recurring task you already have.")
EARLIER = ("Your earlier task stays as it is. You could end or change it on its Repeat "
           "page so you don't keep both, or use it again for this station.")


class SetupPage(JourneySubpage):
    def __init__(self, window, run_id=None):
        """`run_id` names a finished journey whose habit's task no longer
        repeats (QuestArc screen 7, "Set up the task"); else the active
        journey's current station."""
        super().__init__(window, t("ui.setup.title"), "journey-setup")
        self.run_id = run_id
        self.listen(self._changed)
        self.refresh()

    def target(self):
        """(run, journey, index, station, stage) as the model's `current()`;
        for a habit its station is the habit's state and the last pairing."""
        if self.run_id is None:
            return self.model.current()
        found = habit_of(self.model, self.run_id)
        if not found:
            return None
        run, journey, stage, habit = found
        index = journey["stages"].index(stage)
        return run, journey, index, {"state": habit["state"],
                                     "pair": run["stations"][index].get("pair")}, stage

    def _changed(self):
        current = self.target()
        if current and current[3]["state"] in ("current", "met", "maintained"):
            if self.run_id is None:
                self.back_to_journey()
            elif self in self._stack():
                self.window.nav.pop_to_page(self._stack()[self._stack().index(self) - 1])
            return
        self.refresh()

    def refresh(self):
        self.clear()
        current = self.target()
        if not current:
            self.text(t("ui.error.gone"))
            return
        run, journey, index, station, stage = current
        plan = self.group(t("ui.setup.plan"))
        plan_row = Adw.ActionRow(title=plan_sentence(stage, station.get("pair"), run.get("anchor")),
                                 title_lines=0, subtitle=t("ui.setup.suggested",
                                                           schedule=schedule_text(stage["schedule"])))
        plan.add(plan_row)
        if station["state"] == "unsupported-repeat":
            cfg = stages.rule_of_binding(self.window.ds, run["runId"], stage["id"])
            self.text("Journeys work with tasks that repeat daily, every few days or on "
                      "chosen weekdays. You could give the task the suggested schedule, "
                      "or use another task.")
            if cfg:
                row = Adw.ActionRow(title="Use the Suggested Schedule", activatable=True,
                                    subtitle=describe(cfg))
                row.connect("activated", lambda *_: self._reschedule(cfg, stage))
                self.group().add(row)
        else:
            problem = stages.binding_problem(self.window.ds, run["runId"], stage["id"],
                                             self.model.view["todayStr"])
            self.text(t(f"ui.setup.{problem}") if problem else CHOOSE)
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
        # I Already Do This (flow B step 5): not for the last stage, not once
        # the station has a task, not for a station walked again.
        if self.run_id is None and station["state"] == "unbound" \
                and index + 1 < len(journey["stages"]) and station.get("stepBackDay") is None:
            skip = self.group(None, t("ui.setup.skip"))
            row = Adw.ButtonRow(title=t("ui.action.skip-stage")) if hasattr(Adw, "ButtonRow") \
                else Adw.ActionRow(title=t("ui.action.skip-stage"), activatable=True)
            row.add_css_class("pensum-journey-skip")
            row.connect("activated", lambda *_: self._skip(run, journey))
            skip.add(row)
        self._earlier(run, journey, index, station)
        pair_group(self, run, stage["id"], station.get("pair"), lambda pair: plan_row.set_title(
            plan_sentence(stage, pair, run.get("anchor"))))

    def _earlier(self, run, journey, index, station):
        """The task of the station before, while it still repeats: it stays
        as it is, and the user may open it (QuestArc flow B)."""
        if self.run_id is not None or index == 0 or station["state"] != "unbound":
            return
        cfg = stages.rule_of_stage(self.window.ds, run["runId"], journey["stages"][index - 1]["id"],
                                   self.model.view["todayStr"])
        task_id = stages.task_of_rule(self.window.ds, cfg)
        if not task_id:
            return
        group = self.group(None, EARLIER)
        row = Adw.ActionRow(title=t("ui.setup.open-earlier"), activatable=True,
                            subtitle=cfg.get("title") or "")
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda *_: self.window.show_task(task_id))
        group.add(row)

    def _skip(self, run, journey):
        """Pass the station without a task; the same page offers the next one."""
        if self.model.action("skipStage", run, journey, self.model.view["todayStr"]):
            self.refresh()

    def _start_day(self, station):
        today = self.window.ds.today()
        return max(station.get("acceptedDay") or today, today)

    def _create(self, run, stage, station):
        self._bind(lambda: stages.create_stage_task(
            self.window.ds, run["runId"], stage, self._start_day(station),
            view=self.model.view, anchor=run.get("anchor")))

    def _use(self, run, stage, cfg):
        self._bind(lambda: stages.bind_existing(self.window.ds, run["runId"], stage["id"],
                                                cfg["id"], view=self.model.view))

    def _bind(self, bind):
        def done():
            bind()
            return {}
        self.model.apply(done, "bindStage")
        self.window.changed()
        self.model.refresh_now()

    def _reschedule(self, cfg, stage):
        rules.update(self.window.ds, cfg["id"], **stages.rule_fields(
            stage["schedule"], cfg.get("startDate") or self.window.ds.today()))
        self.window.changed()
        self.model.refresh_now()
