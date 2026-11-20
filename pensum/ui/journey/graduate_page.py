"""Let It Graduate (QuestArc docs/behaviour.md, flow F; design rule 25):
offered when the engine says the habit can graduate, never pushed. Two
equal choices for the task, none suggested: the user ends its repeat
themselves (Day Planner never changes the task; it only opens it), or
keeps it repeating quietly (`graduate`). Back changes nothing; there is
no main action, the choice is the yes. Afterwards the same page says
what happens now."""
from gi.repository import Gtk

from pensum.game import records
from pensum.game.content import t
from pensum.game.sentences import plan_sentence
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.habits import habit_of
from pensum.i18n import N_, _

# QuestArc's sentences name Super Productivity's menus.
GRADUATED_END = N_("To end the repeat, open the task, go to its Repeat page and stop the repeat. "
                 "Day Planner does not do this for you.")
GRADUATED_KEEP = N_("The task keeps repeating as before. You could stop its repeat on its "
                  "Repeat page whenever you like.")


class GraduatePage(JourneySubpage):
    def __init__(self, window, run_id):
        super().__init__(window, t("ui.graduate.title"), None)
        self.run_id = run_id
        self.listen(self.refresh)
        self.refresh()

    def refresh(self):
        self.clear()
        self.set_main(None, None)
        found = habit_of(self.model, self.run_id)
        if not found or not (found[3].get("canGraduate") or found[3].get("graduated")):
            self.text(t("ui.error.gone"))
            return
        run, _journey, stage, habit = found
        self.group().add(Gtk.Label(label=plan_sentence(stage, run["stations"][-1].get("pair"),
                                                       run.get("anchor")),
                                   xalign=0, wrap=True, css_classes=["title-4"]))
        if habit.get("graduated"):
            self.set_title(t("ui.graduated.title"))
            self.text(t("ui.graduated.text"))
            ends = habit["graduated"]["choice"] == "end"
            self.text(_(GRADUATED_END if ends else GRADUATED_KEEP), "dimmed")
            task_id = self._task(run, stage) if ends else None
            if task_id:
                button = Gtk.Button(label=_("Open the Task"), halign=Gtk.Align.START)
                button.set_size_request(-1, 44)
                button.connect("clicked", lambda *_: self.window.show_task(task_id))
                self.group().add(button)
            self.set_main(t("ui.action.done"), self.window.show_journey)
            return
        self.text(t("ui.graduate.text"))
        self.text(t("ui.graduate.own"), "dimmed")
        self.text(t("ui.graduate.reminder"), "dimmed")
        group = self.group(t("ui.graduate.task"))
        today = self.model.view["todayStr"]
        for kind in ("end", "keep"):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_bottom=8)
            button = Gtk.Button(label=t(f"ui.graduate.{kind}"),
                                css_classes=["pensum-bar-button", "pensum-journey-graduate"])
            button.connect("clicked", lambda *_a, k=kind: self.model.action(
                "graduate", run, today, k))
            box.append(button)
            box.append(Gtk.Label(label=t(f"ui.graduate.{kind}.text"), xalign=0, wrap=True,
                                 css_classes=["caption", "dimmed"]))
            group.add(box)

    def _task(self, run, stage):
        """A live task of the habit's repeat, while the repeat exists."""
        binding = records.load(self.window.ds).get(f"binding:{run['runId']}:{stage['id']}")
        cfg_id = (binding or {}).get("repeatCfgId") if isinstance(binding, dict) else None
        if not cfg_id or cfg_id not in self.window.ds.data["taskRepeatCfg"]["entities"]:
            return None
        live = [task for task in self.window.ds.tasks.values() if task.get("repeatCfgId") == cfg_id]
        live.sort(key=lambda task: (bool(task.get("isDone")), -(task.get("created") or 0)))
        return live[0]["id"] if live else None
