"""The growing step as a strip on top of Today (#57, QuestArc behaviour,
"Build at a glance"): the small build with the flowers of the stage
under way, the journey's name and the progress in words, one line each.
It is where the habit's task is ticked off, so a tick grows its flower
here (`tick.Growth`). A tap opens the journey. Fixed height and no
wrapping, so the first task stays in view at 360 × 720."""
from gi.repository import Gtk, Pango

from pensum.game import content
from pensum.game.content import t
from pensum.game.sentences import capitalise, progress_text
from pensum.ui.journey import art
from pensum.ui.journey.growing_card import state_line
from pensum.ui.journey.place_piece import place_of_run
from pensum.ui.journey.tick import Growth
from pensum.ui.journey.valley import flowers

WIDTH, HEIGHT = 72, 48  # the build's 120 × 80 view box


def thing_of(view, run):
    """What the strip draws: the run's thing in its place, or its build
    while the run has no moment; with the hue. None without pictures."""
    place = place_of_run(view, run["runId"])
    if place:
        thing = next(th for th in place["things"] if th["runId"] == run["runId"])
        hue = place["hue"]
    else:
        thing, hue = run.get("build"), (run.get("build") or {}).get("hue")
    if not thing or content.ladder(thing.get("ladder")) is None:
        return None
    return thing, hue


def label(thing):
    """The picture in words, with the flowers counted (QuestArc journey
    design, for screen readers)."""
    ladder = content.ladder(thing["ladder"])
    version = max(1, min(thing["version"], len(ladder["versions"])))
    head = t("ui.build.label.head", name=ladder["versions"][version - 1]["title"],
             version=thing["version"], total=thing["versions"])
    if thing["version"] >= thing["versions"]:
        return t("ui.build.label.all", head=head)
    shown, total = len(flowers(thing)), art.marker_elements(ladder)
    if not shown:
        return head
    return t("ui.build.label.ready" if thing.get("ready") else "ui.build.label.not-ready",
             head=head, shown=shown, flowers=total)


class TodayStrip(Gtk.Button):
    def __init__(self, window):
        super().__init__(css_classes=["card", "pensum-today-strip"], visible=False)
        self.window = window
        self.growth = Growth()
        self.thing, self.hue, self.words = None, None, ""
        box = Gtk.Box(spacing=12)
        self.picture = Gtk.DrawingArea(content_width=WIDTH, content_height=HEIGHT,
                                       valign=Gtk.Align.CENTER,
                                       accessible_role=Gtk.AccessibleRole.PRESENTATION)
        self.picture.set_draw_func(self._draw)
        box.append(self.picture)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                        valign=Gtk.Align.CENTER, hexpand=True)
        self.title = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END,
                               css_classes=["heading"])
        self.state = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END,
                               css_classes=["caption", "dimmed"])
        words.append(self.title)
        words.append(self.state)
        box.append(words)
        box.append(Gtk.Image(icon_name="go-next-symbolic",
                             accessible_role=Gtk.AccessibleRole.PRESENTATION))
        self.set_child(box)
        self.connect("clicked", lambda *_: window.show_run())
        window.journeys.listeners.append(self.refresh)

    def refresh(self):
        """Shown on Today while a journey grows a step, unless switched
        off in the preferences."""
        model = self.window.journeys
        current = model.current() if self.window.settings.journey_strip else None
        found = thing_of(model.view, current[0]) if current else None
        if not found or self.window.list_page.context.kind != "today":
            self.set_visible(False)
            return
        run, journey, _index, station, stage = current
        self.thing, self.hue = found
        if self.growth.show((run["runId"], self.thing["version"]), len(flowers(self.thing))):
            self.growth.attach(self.picture)
        title = t(journey["title"])
        parts = [capitalise(progress_text(stage, station))] if station["state"] in ("current", "met") else []
        state = state_line(run, station, model.view["todayStr"])
        if state:
            # Only the first sentence: the strip has one line.
            parts.append(state.split(". ")[0].rstrip(".") + ".")
        line = " · ".join(parts)
        self.title.set_label(title)
        self.state.set_label(line)
        self.words = f"{title}. {label(self.thing)}. {line}"
        self.update_property([Gtk.AccessibleProperty.LABEL], [self.words])
        self.set_tooltip_text(title)
        self.set_visible(True)
        self.picture.queue_draw()

    def _draw(self, area, cr, width, height):
        if not self.thing:
            return
        ladder = content.ladder(self.thing["ladder"])
        css = art.stylesheet(art.colours(area, True, self.hue))
        versions = ladder["versions"]
        name = versions[min(max(self.thing["version"], 1), len(versions)) - 1]["art"]
        art.draw(cr, name, 0, 0, width, height, css)
        for index, flower in enumerate(flowers(self.thing)):
            art.draw_growing(cr, flower, 0, 0, width, height, css, self.growth.factor(index))
