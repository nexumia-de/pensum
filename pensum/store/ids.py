"""Entity ids in Super Productivity's style: nanoid, 21 characters. No GTK."""
import secrets

_ALPHABET = "useandom-26T198340PX75pxJACKVERYMINDBUSHWOLF_GQZbfghjklqvwyzrict"


def new_id(size=21):
    return "".join(secrets.choice(_ALPHABET) for _ in range(size))
