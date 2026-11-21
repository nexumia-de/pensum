"""The game view of the dataset, kept current: after each change the
engine runs (in a thread, so the window stays responsive), the events
become one toast, and pausing the bound repeat rule is recorded. The
journey comes forward when a completion reaches the station or is the
first after a gap; any other change leaves the page the user is on. With
no QuestArc record at all the engine does not run."""
import logging
import threading

from gi.repository import GLib

from pensum.game import content, engine, records, reminders, sentences, stages

log = logging.getLogger(__name__)
DELAY_MS = 300
# The engine's events that bring the journey forward: the first
# completion after a gap and the completion that reaches the station,
# where a choice waits (#57). A plain completion grows a flower in the
# strip on Today and gets the toast; several completions at once come
# from a sync or an import and only get the toast.
COMES_FORWARD = {"event.welcome-back", "event.station-reached"}


class JourneyModel:
    def __init__(self, window):
        self.window = window
        self.view = None
        self.error = None
        self._source = None
        self._running = False
        self._again = False
        self._paused_seen = {}
        # Each evaluation gets a number; a result older than the one shown
        # (a background run that finished late) is dropped.
        self._generation = 0
        self._shown = 0
        self.listeners = []

    @property
    def available(self):
        return content.available()

    def records(self):
        return records.load(self.window.ds)

    def in_use(self):
        return bool(self.records())

    def write(self, changes, guard=True):
        """Write record changes and re-evaluate at once. Every write goes
        through the engine's last check (`guardWrite`, QuestArc data model
        §2) first: a change that touches a journey of a newer QuestArc, or
        a kind this engine does not write, is refused as a whole and
        nothing is written (engine.Refused). Only removing all of
        QuestArc's data passes `guard=False`: it withdraws every record,
        also the ones this engine does not know."""
        if guard:
            changes = engine.guard_write(self.view, changes)
        if not changes:
            return
        records.write(self.window.ds, changes)
        self.window.changed()
        self.refresh_now()

    def action(self, name, *args):
        """Write the records of one of the engine's actions; False when
        nothing could be written (the user is told)."""
        return self.apply(lambda: engine.action(name, *args), name)

    def apply(self, make, name="write"):
        """Write the changes `make()` returns, through the guard; False
        when nothing could be written (the user is told)."""
        try:
            self.write(make())
            return True
        except engine.Refused as error:
            log.warning("journey action %s refused for %d record(s)", name, len(error.keys))
            self.window.toast(content.t("ui.read-only.newer"))
        except engine.EngineError as error:
            log.warning("journey action %s failed: %s", name, error)
            self.window.toast(content.t("ui.error.write"))
        return False

    # --- evaluation ----------------------------------------------------

    def schedule(self):
        """After a change in the dataset: evaluate soon."""
        if not self.available or not self.in_use():
            if self.view is not None:
                self.view = None
                self._notify()
            return
        if self._source is None:
            self._source = GLib.timeout_add(DELAY_MS, self._start)

    def _start(self):
        self._source = None
        if self._running:
            self._again = True
            return GLib.SOURCE_REMOVE
        self._running = True
        request = engine.evaluate_request(self.window.ds)
        self._generation += 1
        threading.Thread(target=self._work, args=(self.view, request, self._generation),
                         daemon=True).start()
        return GLib.SOURCE_REMOVE

    def _work(self, before, request, generation):
        try:
            result = engine.evaluate_and_diff(None, before, request=request)
            GLib.idle_add(self._done, result, None, generation)
        except engine.EngineError as error:
            GLib.idle_add(self._done, None, error, generation)

    def _done(self, result, error, generation):
        self._running = False
        if generation > self._shown:
            self._shown = generation
            self._apply(result, error)
        if self._again:
            self._again = False
            self.schedule()
        return GLib.SOURCE_REMOVE

    def refresh_now(self):
        """Evaluate in the foreground (after the user's own journey actions
        and in tests)."""
        if not self.available or not self.in_use():
            self.view = None
            self._notify()
            return
        self._generation += 1
        self._shown = self._generation
        try:
            self._apply(engine.evaluate_and_diff(self.window.ds, self.view), None)
        except engine.EngineError as error:
            self._apply(None, error)

    def _apply(self, result, error):
        if error is not None:
            log.warning("journey engine: %s", error)
            self.error = str(error)
            self._notify()
            return
        self.error = None
        view, events = result
        self.view = view
        if events:
            message = sentences.message_for(events, view, content.journeys())
            if message:
                self.window.toast(message)
        if self._record_repeat_pause(view) or self._record_reminders(view):
            return
        self._notify()
        if any(e["key"] in COMES_FORWARD for e in events or ()):
            self.window.show_run()

    def _record_repeat_pause(self, view):
        """The bound rule was paused or resumed since the last look
        (QuestArc game rules §2, pauses); True when a record was written."""
        run = view.get("active")
        cfg = stages.bound_rule(self.window.ds, view)
        if not run or not cfg:
            return False
        paused = bool(cfg.get("isPaused"))
        before = self._paused_seen.get(cfg["id"])
        self._paused_seen[cfg["id"]] = paused
        if before is None or before == paused:
            return False
        key = f"pause:{run['runId']}:{view['todayStr']}"
        if (self.records().get(key) or {}).get("action") == ("pause" if paused else "resume"):
            return False
        return self.action("repeatPause", run["runId"], view["todayStr"], paused)

    def _record_reminders(self, view):
        """Record a followed task's reminder that appeared or went (QuestArc
        game rules §9); True when a record was written."""
        changes = {}
        try:
            for run_id, stage_id, on in reminders.due(view, self.records()):
                changes.update(engine.action("reminderSeen", run_id, stage_id,
                                             view["todayStr"], on))
        except engine.EngineError as error:
            log.warning("journey reminder record failed: %s", error)
            return False
        return bool(changes) and self.apply(lambda: changes, "reminderSeen")

    def _notify(self):
        for listener in list(self.listeners):
            listener()

    # --- reading ---------------------------------------------------------

    def journey(self, journey_id):
        return content.journey(journey_id)

    def active(self):
        return (self.view or {}).get("active")

    def read_only(self):
        """The active journey when this engine cannot compute it (a newer
        QuestArc continued it, or its journey is not here): the view's
        `readOnly` entry with state `active`, else None."""
        return next((r for r in (self.view or {}).get("readOnly") or ()
                     if r.get("state") == "active"), None)

    def current(self):
        """(run, journey, index, station, stage) of the active journey."""
        run = self.active()
        if not run:
            return None
        journey = self.journey(run["journeyId"])
        index = run["position"]["stage"]
        if not journey or index >= len(journey["stages"]):
            return None
        return run, journey, index, run["stations"][index], journey["stages"][index]

