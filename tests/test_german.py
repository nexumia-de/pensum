"""Day Planner's own texts in German (#79): with a German locale the
task manager's pages show German and none of the English texts. Needs a
display."""
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

from gi.repository import Gio  # noqa: E402

from pensum import demo  # noqa: E402
from pensum.store.dataset import Context  # noqa: E402
from journey_support import iterate, labels, window_with  # noqa: E402


@pytest.fixture
def german(monkeypatch):
    monkeypatch.setenv("LANG", "de_DE.UTF-8")


@pytest.fixture
def window(app, tmp_path, german):
    shown = window_with(app, tmp_path, demo.create())
    yield shown
    shown.close()


def check(shown, german, english):
    missing = [text for text in german if text not in shown]
    assert not missing, f"not German: {missing} in {shown}"
    found = [text for text in english if text in shown]
    assert not found, f"still English: {found}"


def menu_labels(menu):
    found = []
    for index in range(menu.get_n_items()):
        label = menu.get_item_attribute_value(index, "label", None)
        if label:
            found.append(label.get_string())
        for kind in (Gio.MENU_LINK_SECTION, Gio.MENU_LINK_SUBMENU):
            link = menu.get_item_link(index, kind)
            if link:
                found += menu_labels(link)
    return found


def test_the_lists_and_the_menus_are_german(window):
    window.show_list(Context.today())
    iterate()
    check(labels(window), ["Heute", "Projekte", "Schlagwörter"],
          ["Today", "Projects", "Tags"])
    shown = labels(window.list_page)
    check(shown, ["Alle auf Heute verschieben", "Tag abschließen"],
          ["Move All to Today", "Finish Day"])
    assert any(text.endswith("gearbeitet") for text in shown)
    assert window.list_page.get_title() == "Heute"
    window.show_list(Context("project", "demo-website"))
    iterate()
    shown = labels(window.list_page)
    check(shown, ["Website Relaunch"], ["Backlog"])
    from pensum.ui import sidebar
    check(menu_labels(sidebar.main_menu()),
          ["Sicherung importieren…", "Sicherung exportieren…", "Sync-Ordner lesen…",
           "Archivierte Projekte", "Einstellungen"],
          ["Import Backup…", "Export Backup…", "Archived Projects", "Preferences"])
    check(menu_labels(sidebar.add_menu()), ["Neues Projekt…", "Neues Schlagwort…"],
          ["New Project…", "New Tag…"])


def test_the_task_page_is_german(window):
    window.show_task(window.ds.current_task_id())
    iterate()
    page = window.visible_page()
    shown = labels(page)
    check(shown, ["Gearbeitete Zeit", "Planung", "Geplant für", "Frist", "Priorität",
                  "Wiederholung", "Notizen", "Unteraufgaben", "Aufgabe löschen"],
          ["Time Spent", "Planning", "Planned For", "Deadline", "Priority", "Repeat",
           "Notes", "Subtasks", "Delete Task"])
    assert any("insgesamt" in text for text in shown)
    assert not any("in total" in text for text in shown)


def test_the_repeat_page_is_german(window):
    from pensum.store.repeat import rules
    ds = window.ds
    task = ds.task(ds.current_task_id())
    rules.make_recurring(ds, task["id"], rules.schedule_fields(
        "MONDAY_TO_FRIDAY", ds.planned_day(task) or ds.today()))
    window.changed()
    window.show_task(task["id"])
    iterate()
    assert "Montag bis Freitag" in labels(window.visible_page())
    from pensum.ui.repeat_page import RepeatPage, describe
    window.nav.push(RepeatPage(window, task["id"]))
    iterate()
    check(labels(window.visible_page()),
          ["Wiederholung", "Pausiert", "Wiederholung beenden", "Einheit"],
          ["Repeat", "Paused", "Stop Repeating", "Unit"])
    assert describe({"repeatCycle": "DAILY", "repeatEvery": 3}) == "Alle 3 Tage"
    assert describe({"repeatCycle": "MONTHLY", "repeatEvery": 1, "monthlyLastDay": True,
                     "isPaused": True}) == "Jeden Monat am letzten Tag (pausiert)"


def test_search_is_german(window):
    window.show_search()
    iterate()
    page = window.visible_page()
    check(labels(page), ["Suche", "Aufgaben suchen"], ["Search", "Search Tasks"])
    page.entry.set_text("zzzz-nothing")
    page.refresh()
    check(labels(page), ["Keine Aufgaben gefunden", "Probiere andere Wörter."],
          ["No Tasks Found", "Try other words."])


def test_preferences_are_german(window):
    from pensum.preferences import PreferencesDialog
    dialog = PreferencesDialog(window)
    dialog.present(window)
    iterate()
    check(labels(dialog), ["Einstellungen", "Allgemein", "Erscheinungsbild", "Erinnerungen",
                           "Neuer Tag beginnt um", "Datendatei", "Automatische Sicherungen"],
          ["Preferences", "General", "Appearance", "Reminders", "Next Day Starts At",
           "Data File", "Automatic Backups"])
    dialog.close()


def test_the_sync_page_and_its_errors_are_german(window):
    window.show_sync()
    iterate()
    page = window.visible_page()
    check(labels(page), ["Sync-Ordner", "Art", "Serveradresse", "Benutzername", "Passwort",
                         "Verschlüsselungspasswort", "Ordner lesen", "Importieren…"],
          ["Sync Folder", "Kind", "Server Address", "User Name", "Password",
           "Encryption Password", "Read Folder", "Import…"])
    page.kind_row.set_selected(1)
    page.settings.sync_local_path = ""
    page.read(wait=True)
    assert "Wähle zuerst den Ordner." in labels(page)


def test_reminders_and_backup_errors_are_german(german):
    from pensum.store import backup, reminders
    assert reminders.option_labels()[:2] == ["Keine Erinnerung", "Zur geplanten Zeit"]
    with pytest.raises(backup.BackupError) as error:
        backup.parse("[1, 2")
    assert "Sicherung von Super Productivity" in str(error.value)
