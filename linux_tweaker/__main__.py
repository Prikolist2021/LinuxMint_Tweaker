# -*- coding: utf-8 -*-
"""
Linux Tweaker — точка входа.

Здесь main(): создаёт окно, ставит иконку, запускает главный цикл.
"""

import sys
import os

from tkinter import Tk, messagebox, PhotoImage

from .data import APP_NAME, APP_VERSION
from .helpers import acquire_lock, release_lock, detect_lang
from .main_window import MainWindow


def _find_icon_path():
    """Ищет иконку рядом с приложением или в _MEIPASS (PyInstaller)."""
    if getattr(sys, "_MEIPASS", None):
        p = os.path.join(sys._MEIPASS, "linux-tweaker.png")
        if os.path.exists(p):
            return p
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (
        os.path.join(here, "linux-tweaker.png"),
        os.path.join(os.path.dirname(here), "linux-tweaker.png"),
        os.path.join(os.path.dirname(os.path.dirname(here)),
                     "linux-tweaker.png"),
    ):
        if os.path.exists(cand):
            return cand
    return None


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("%s v%s\npython3 linux_tweaker.py [--dry-run]"
              % (APP_NAME, APP_VERSION))
        sys.exit(0)

    if not acquire_lock():
        root = Tk()
        root.withdraw()
        lang = detect_lang()
        messagebox.showwarning(
            APP_NAME,
            "Linux Tweaker is already running." if lang == "en"
            else "Linux Tweaker уже запущен.")
        root.destroy()
        sys.exit(1)

    if os.geteuid() == 0:
        print("WARNING: Linux Tweaker should be run as a normal user, "
              "not as root. Sudo will be requested when needed.",
              file=sys.stderr)

    root = Tk()

    # Иконка приложения (и во всех диалогах тоже)
    icon_path = _find_icon_path()
    if icon_path:
        try:
            logo = PhotoImage(file=icon_path)
            root.iconphoto(True, logo)
            root._icon_ref = logo  # держим ссылку, чтобы Python не удалил
        except Exception as e:
            print("Cannot load icon: %s" % e, file=sys.stderr)

    app = MainWindow(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        release_lock()


if __name__ == "__main__":
    main()
