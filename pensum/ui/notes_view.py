"""A note shown formatted: the blocks of pensum.markdown as labels, with
checkboxes that can be ticked and links that open on a tap. Nothing of a
note is loaded or run: no web view, no pictures."""
from gi.repository import Gtk, Pango

from pensum import markdown
from pensum.i18n import _

HEADING_CLASSES = {1: "title-2", 2: "title-3", 3: "title-4"}
INDENT = 18


def open_link(label, uri):
    """A tapped link goes to the system's handler, if its scheme may."""
    target = markdown.link_target(uri)
    if target is not None:
        Gtk.UriLauncher.new(target).launch(label.get_root(), None, None)
    return True


def _label(markup, *classes):
    label = Gtk.Label(use_markup=True, wrap=True, xalign=0, hexpand=True,
                      wrap_mode=Pango.WrapMode.WORD_CHAR)
    label.set_markup(markup.replace("\x00", ""))
    for name in classes:
        label.add_css_class(name)
    label.connect("activate-link", open_link)
    return label


def _with_prefix(prefix, label):
    box = Gtk.Box(spacing=6)
    prefix.set_valign(Gtk.Align.START)
    box.append(prefix)
    box.append(label)
    return box


class NotesView(Gtk.Box):
    def __init__(self, on_toggle):
        """`on_toggle(line)` runs when the checkbox of a source line is
        ticked or unticked."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        self.on_toggle = on_toggle
        self.checks = []

    def show(self, source):
        child = self.get_first_child()
        while child:
            self.remove(child)
            child = self.get_first_child()
        self.checks = []
        blocks = markdown.parse(source)
        for block in blocks:
            self.append(self._widget(block))
        if not blocks:
            self.append(_label(_("No notes"), "dim-label"))

    def _widget(self, block):
        if block.kind == "rule":
            widget = Gtk.Separator(margin_top=6, margin_bottom=6)
        elif block.kind == "heading":
            widget = _label(block.markup, HEADING_CLASSES.get(block.level, "heading"))
            widget.set_margin_top(6)
        elif block.kind == "code":
            widget = _label(f"<tt>{block.markup}</tt>", "pensum-note-code")
            widget.set_selectable(True)
        elif block.kind == "bullet":
            widget = _with_prefix(Gtk.Label(label="•"), _label(block.markup))
        elif block.kind == "ordered":
            number = Gtk.Label(label=f"{block.number}.")
            number.add_css_class("numeric")
            widget = _with_prefix(number, _label(block.markup))
        elif block.kind == "task":
            check = Gtk.CheckButton(active=block.checked)
            check.add_css_class("pensum-touch")
            label = _label(block.markup, *(["dim-label"] if block.checked else []))
            label.set_valign(Gtk.Align.CENTER)
            check.update_property([Gtk.AccessibleProperty.LABEL], [label.get_text()])
            check.connect("toggled", lambda *_: self.on_toggle(block.line))
            self.checks.append(check)
            widget = _with_prefix(check, label)
        else:
            widget = _label(block.markup)
        if block.kind in ("bullet", "ordered", "task"):
            widget.set_margin_start(INDENT * block.level)
        if block.quoted:
            widget.add_css_class("pensum-note-quote")
        return widget
