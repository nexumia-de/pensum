"""Choose a time of day by touch: hours and minutes with large plus and
minus buttons; the numbers can also be typed."""
from gi.repository import Adw, Gtk
from pensum.i18n import _


def _spin(upper, step, value, label):
    spin = Gtk.SpinButton.new_with_range(0, upper, step)
    spin.set_orientation(Gtk.Orientation.VERTICAL)
    spin.set_wrap(True)
    spin.set_numeric(True)
    spin.set_width_chars(2)
    spin.set_increments(step, step)
    child = spin.get_first_child()
    while child:  # the on-screen keyboard shows its digits for the number
        if isinstance(child, Gtk.Text):
            child.set_input_purpose(Gtk.InputPurpose.DIGITS)
        child = child.get_next_sibling()
    spin.set_value(value)
    spin.add_css_class("pensum-time-spin")
    spin.add_css_class("title-1")
    spin.update_property([Gtk.AccessibleProperty.LABEL], [label])
    spin.set_tooltip_text(label)

    def two_digits(button):
        button.set_text(f"{button.get_value_as_int():02d}")
        return True

    spin.connect("output", two_digits)
    two_digits(spin)
    return spin


class TimePicker(Adw.Dialog):
    """`on_set(hours, minutes)` runs when Set Time is pressed."""

    def __init__(self, hours, minutes, on_set):
        super().__init__(title=_("Time"), content_width=360)
        self.on_set = on_set
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.hours = _spin(23, 1, hours, _("Hours"))
        self.minutes = _spin(59, 5, minutes, _("Minutes"))
        colon = Gtk.Label(label=":")
        colon.add_css_class("title-1")
        clock = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER,
                        margin_top=12, margin_bottom=12)
        # A clock reads hours before minutes in every writing direction.
        clock.set_direction(Gtk.TextDirection.LTR)
        for widget in (self.hours, colon, self.minutes):
            clock.append(widget)
        # The form scrolls when the on-screen keyboard takes the room.
        toolbar.set_content(Gtk.ScrolledWindow(
            child=clock, hscrollbar_policy=Gtk.PolicyType.NEVER,
            propagate_natural_height=True))
        self.apply = Gtk.Button(label=_("Set Time"), margin_top=6, margin_bottom=12,
                                margin_start=12, margin_end=12)
        self.apply.add_css_class("suggested-action")
        self.apply.add_css_class("pensum-bar-button")
        self.apply.connect("clicked", self._on_apply)
        toolbar.add_bottom_bar(self.apply)
        self.set_child(toolbar)
        # No number field has the focus when the dialog opens, so the
        # on-screen keyboard stays away until a number is tapped.
        self.set_focus(self.apply)
        self.set_default_widget(self.apply)

    def _on_apply(self, *_):
        for spin in (self.hours, self.minutes):
            spin.update()  # a number typed and not yet confirmed
        self.on_set(self.hours.get_value_as_int(), self.minutes.get_value_as_int())
        self.close()
