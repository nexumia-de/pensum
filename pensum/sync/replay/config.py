"""globalConfig ops (global-config.reducer.ts, updateGlobalConfigSection)."""


def update_section(data, fields, now_ms):
    from pensum.sync.replay.tasks import Refused
    key = fields.get("sectionKey")
    if key == "sync":
        # This device's sync settings stay local; they are stripped from
        # the synced state, so another device's change does not apply.
        return
    # Other sections (misc and appFeatures are normalised by the reducer)
    # are not transcribed yet.
    raise Refused(f"settings section {key}")
