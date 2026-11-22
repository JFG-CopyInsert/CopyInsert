# -*- coding: utf-8 -*-
# Protocol handler behind the "Edit" menu entries of the CopyInsert extension.
# Each time the Edit menu opens, LibreOffice asks it for the state of the
# direction entries inside the four submenus. It enables only the directions
# that fit the current selection (rows: above / below, columns: left / right,
# cells: all four) and adds the word rows / columns / cells to the entry. With several
# sheet tabs selected, only the Copy submenu is enabled, with Before / After. Every entry
# is dimmed while one of the sheets involved is protected.
# The actions are the Basic macros of CopyInsertLib.CopyInsert, and all texts
# come from its Txt() function, so the menus use the same wording and
# languages as the context menus.
import time
import traceback
import uno
import unohelper
from com.sun.star.frame import XDispatchProvider, XDispatch
from com.sun.star.beans import NamedValue
from com.sun.star.lang import XInitialization, XServiceInfo

IMPL_NAME = "org.libreoffice.extension.copyinsert.EditMenuHandler"
PROTOCOL = "org.libreoffice.extension.copyinsert:"
MACRO = ("vnd.sun.star.script:CopyInsertLib.CopyInsert.%s"
         "?language=Basic&location=application")
DEBUG = False

ACTS = ("Copy", "Paste", "Cut", "Move")
MACRO_ACT = {"Copy": "Copy", "Paste": "PasteSpecial", "Cut": "Cut", "Move": "Move"}
DIRS = ("Above", "Below", "Left", "Right")
VALID_DIRS = {"cells": DIRS, "rows": ("Above", "Below"), "columns": ("Left", "Right"),
              "sheets": ("Above", "Below")}   # sheets: only for Copy; Above = before, Below = after

MODULE = "com.sun.star.sheet.SpreadsheetDocument"

_texts = {}
_keys = {"time": 0.0, "map": {}}


def _log(msg):
    if DEBUG:
        try:
            with open("/tmp/em.log", "a") as f:
                f.write(msg + "\n")
        except Exception:
            pass


def _basic(ctx, name, *args):
    mspf = ctx.getValueByName(
        "/singletons/com.sun.star.script.provider.theMasterScriptProviderFactory")
    script = mspf.createScriptProvider("").getScript(MACRO % name)
    return script.invoke(tuple(args), (), ())[0]


def _key_name(ev):
    """Text such as 'Alt+C' for a KeyEvent, or '' when the key is not handled."""
    code = ev.KeyCode
    if 512 <= code <= 537:                      # A-Z
        key = chr(65 + code - 512)
    elif 256 <= code <= 265:                    # 0-9
        key = chr(48 + code - 256)
    elif 768 <= code <= 779:                    # F1-F12
        key = "F%d" % (code - 767)
    else:
        return ""
    mods = ev.Modifiers
    return (("Ctrl+" if mods & 2 else "") + ("Alt+" if mods & 4 else "")
            + ("Shift+" if mods & 1 else "") + key)


def _shortcuts(ctx):
    """{'CopyBefore': 'Alt+C', ...}: current keys of the Start...Before macros."""
    now = time.time()
    if now - _keys["time"] < 2.0:
        return _keys["map"]
    found = {}
    try:
        acc = ctx.ServiceManager.createInstanceWithArgumentsAndContext(
            "com.sun.star.ui.ModuleAcceleratorConfiguration",
            (NamedValue("ModuleIdentifier", MODULE),), ctx)
        for ev in acc.getAllKeyEvents():
            try:
                cmd = acc.getCommandByKeyEvent(ev)
            except Exception:
                continue
            if "CopyInsertLib.CopyInsert.Start" in cmd and "Before?" in cmd:
                name = cmd.split("CopyInsert.Start")[1].split("?")[0]
                label = _key_name(ev)
                if label:
                    found[name] = label
    except Exception:
        _log(traceback.format_exc())
    _keys["time"] = now
    _keys["map"] = found
    return found


class EditMenuHandler(unohelper.Base, XDispatchProvider, XDispatch,
                      XInitialization, XServiceInfo):
    def __init__(self, ctx):
        self.ctx = ctx
        self.frame = None
        self._sheets = []       # sheets of the selection, set by _kind()

    # --- XServiceInfo ---
    def getImplementationName(self):
        return IMPL_NAME

    def supportsService(self, name):
        return name == "com.sun.star.frame.ProtocolHandler"

    def getSupportedServiceNames(self):
        return ("com.sun.star.frame.ProtocolHandler",)

    # --- XInitialization ---
    def initialize(self, args):
        if args:
            self.frame = args[0]

    # --- XDispatchProvider ---
    def queryDispatch(self, url, target, flags):
        if url.Protocol == PROTOCOL:
            return self
        return None

    def queryDispatches(self, requests):
        return tuple(self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags)
                     for r in requests)

    # --- XDispatch ---
    def dispatch(self, url, args):
        try:
            if url.Path == "Disabled":      # a dimmed entry of a context menu, clicked anyway
                _basic(self.ctx, "ShowProtectedSource")
                return
            kind = self._kind()
            act, _, d = url.Path.partition(".")
            if kind is None or act not in ACTS or d not in VALID_DIRS[kind]:
                return
            if kind == "sheets":
                if act == "Copy":
                    _basic(self.ctx, "StartCopySheetsBefore" if d == "Above"
                           else "StartCopySheets")
                return
            if kind == "cells":
                name = "Start" + MACRO_ACT[act] + d
            elif d in ("Above", "Left"):
                name = "Start" + MACRO_ACT[act] + "Before"
            else:
                name = "Start" + MACRO_ACT[act]
            _basic(self.ctx, name)
        except Exception:
            _log(traceback.format_exc())

    def addStatusListener(self, listener, url):
        self._send(listener, url)

    def removeStatusListener(self, listener, url):
        pass

    # --- selection ---
    def _kind(self):
        """'rows', 'columns', 'cells' or None (nothing usable selected)."""
        self._sheets = []
        try:
            ctrl = self.frame.getController() if self.frame is not None else None
            if ctrl is None:
                return None
            model = ctrl.getModel()
            if model is None or not model.supportsService(
                    "com.sun.star.sheet.SpreadsheetDocument"):
                return None
            sel = ctrl.getSelection()
            try:
                ranges = [sel.getRangeAddress()]
            except Exception:
                try:
                    ranges = list(sel.getRangeAddresses())   # Ctrl selection
                except Exception:
                    return None     # drawing objects, ...
            if not ranges:
                return None
            self._sheets = sorted({r.Sheet for r in ranges})
            sheet_no = ranges[0].Sheet
            if any(r.Sheet != sheet_no for r in ranges):
                tabs = sorted({r.Sheet for r in ranges})
                if tabs != list(range(tabs[0], tabs[-1] + 1)):
                    return None     # sheets with gaps: not supported
                return "sheets"     # several consecutive sheet tabs selected
            sheet = model.getSheets().getByIndex(sheet_no)
            ncols = sheet.getColumns().getCount()
            nrows = sheet.getRows().getCount()
            all_rows = all(r.StartColumn == 0 and r.EndColumn == ncols - 1 for r in ranges)
            all_cols = all(r.StartRow == 0 and r.EndRow == nrows - 1 for r in ranges)
            if any(r.StartColumn == 0 and r.EndColumn == ncols - 1 and
                   r.StartRow == 0 and r.EndRow == nrows - 1 for r in ranges):
                return None         # whole sheet: nothing to offer
            if all_rows:
                return "rows"
            if all_cols:
                return "columns"
            return "cells" if len(ranges) == 1 else None
        except Exception:
            _log(traceback.format_exc())
            return None

    def _protected(self):
        """True if one of the sheets of the selection (see _kind) is protected."""
        try:
            sheets = self.frame.getController().getModel().getSheets()
            return any(sheets.getByIndex(n).isProtected() for n in self._sheets)
        except Exception:
            _log(traceback.format_exc())
            return False

    def _txt(self, key):
        if key not in _texts:
            try:
                _texts[key] = _basic(self.ctx, "Txt", key)
            except Exception:
                _log(traceback.format_exc())
                return key
        return _texts[key]

    def _before_slot(self, kind):
        """The entry that runs the ...Before macro, the one the shortcut keys start."""
        if kind == "columns":
            return "Left"
        if kind == "cells" and not self._shift_down():
            return "Left"
        return "Above"

    def _shift_down(self):
        if "shift_down" not in _texts:
            try:
                _texts["shift_down"] = bool(_basic(self.ctx, "CellsShiftDown"))
            except Exception:
                _log(traceback.format_exc())
                return True
        return _texts["shift_down"]

    def _send(self, listener, url):
        try:
            if url.Path == "Disabled":      # context menu entry of a protected sheet: dimmed
                ev = uno.createUnoStruct("com.sun.star.frame.FeatureStateEvent")
                ev.FeatureURL = url
                ev.FeatureDescriptor = ""
                ev.Source = self
                ev.Requery = False
                ev.IsEnabled = False
                listener.statusChanged(ev)
                return
            act, _, d = url.Path.partition(".")
            if act not in ACTS or d not in DIRS:
                return
            kind = self._kind()
            ok = kind is not None and d in VALID_DIRS[kind]
            if ok and self._protected():
                ok = False          # a protected sheet: every entry is dimmed
            if kind == "sheets" and act != "Copy":
                ok = False          # only the copy submenu works for sheets
            key = "dir." + d.lower()
            if ok and kind == "sheets":
                key = "dir.before" if d == "Above" else "dir.after"
            text = self._txt(key)
            if ok:
                text += " (" + self._txt("k." + kind) + ")"
            text += "..."
            # The entry that runs a Start...Before macro shows its shortcut,
            # like the same entry in the context menus.
            if ok and kind != "sheets" and d == self._before_slot(kind):
                label = _shortcuts(self.ctx).get(MACRO_ACT[act] + "Before")
                if label:
                    text += "    " + label
            ev = uno.createUnoStruct("com.sun.star.frame.FeatureStateEvent")
            ev.FeatureURL = url
            ev.FeatureDescriptor = ""
            ev.Source = self
            ev.Requery = False
            ev.IsEnabled = ok
            ev.State = text
            listener.statusChanged(ev)
        except Exception:
            _log(traceback.format_exc())


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    EditMenuHandler, IMPL_NAME, ("com.sun.star.frame.ProtocolHandler",))
