"""How QuestArc motivates you (QuestArc design rule 26): the rules in
plain words."""
from gi.repository import Adw, Gtk

from pensum.game.content import t

TOPICS = ("small-steps", "plan", "misses", "welcome-back", "reason", "weekly", "graduation",
          "game", "not", "success")


class MotivatesPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title=t("ui.motivates.title"), tag="journey-motivates")
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        page = Adw.PreferencesPage()
        for topic in TOPICS:
            group = Adw.PreferencesGroup(title=t(f"ui.motivates.{topic}.title"))
            label = Gtk.Label(label=t(f"ui.motivates.{topic}"), xalign=0, wrap=True)
            group.add(label)
            page.add(group)
        toolbar.set_content(page)
        self.set_child(toolbar)
