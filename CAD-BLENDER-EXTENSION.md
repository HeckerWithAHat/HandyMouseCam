# HandyMouseCam — CAD & Blender Gesture Extension

**Status:** Design doc for Phase 9+ (extends `hand-gesture-mouse-project-doc.md`)
**Scope:** Adds app-aware gesture profiles so the same hand-tracking pipeline can drive Blender and CAD/3D-printing tools (Fusion 360, FreeCAD, etc.) without reaching for the physical mouse/keyboard, while keeping the existing desktop MVP mapping intact.

---

## 1. Why this needs a new architectural piece

The MVP (Phases 0–8) has one global `GestureMapping`: pinch = click, open-hand-move = cursor, two-hand-spread = window resize. CAD and Blender need a *different* mapping for the same physical gestures (a "fist" should orbit the viewport in Blender, not do nothing on the desktop), and 3D-printing tools need yet another variant depending on their navigation scheme.

Rather than hardcoding "if Blender do X," the fix is one new component sitting between `GestureRecognizer` and the output sink:

```
GestureRecognizer
      │
      ▼
┌─────────────────────┐
│  ProfileManager      │  ← NEW
│  - polls foreground   │
│    window/process     │
│  - picks active        │
│    APP_PROFILE         │
└──────────┬───────────┘
           │
           ▼
   GestureEvent + active profile
           │
   ┌───────┴────────┐
   ▼                ▼
OSController   BlenderAPIController   (sinks — see §4)
(emulation)     (direct bpy, Path B)
```

`ProfileManager` detects the focused app via `pywin32`:

```python
import win32gui, win32process, psutil

class ProfileManager:
    def get_active_profile(self, app_profiles: dict) -> dict:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc_name = psutil.Process(pid).name()
        except psutil.NoSuchProcess:
            return app_profiles["_default"]
        for name, profile in app_profiles.items():
            if profile.get("process_match") and proc_name in profile["process_match"]:
                return profile
        return app_profiles["_default"]
```

This one addition is what makes everything below configurable instead of hardcoded — build it first (Phase 9).

---

## 2. Path A — OS-level emulation (near-term milestone)

Works for *any* app, including CAD tools with no scripting API. Reuses your existing `OSController` almost unchanged — you're just telling it to emulate different buttons/keys per active profile instead of one fixed mapping.

### 2.1 Convention this leans on

Blender and most CAD tools bind viewport navigation to the middle mouse button:

| Action | Typical binding |
|---|---|
| Orbit | Middle-mouse-drag |
| Pan | Shift + middle-mouse-drag |
| Zoom | Scroll wheel |

**Caveat:** CAD tools (Fusion 360 especially) let users pick between several navigation presets (Fusion/Inventor/SolidWorks-style), which changes these bindings. Treat the table above as the Blender-default starting point, and verify/adjust per app in its profile — that's exactly what the config-driven design in §2.3 is for.

### 2.2 Gesture vocabulary (CAD/Blender profile)

| Gesture | Navigation context (nothing selected) | Object context (selection under cursor) |
|---|---|---|
| Right hand open/flat + move | **Pan** (Shift+MMB) | — |
| Right hand fist + move | **Orbit** (MMB) | — |
| Two-hand pinch (thumb+index), spread/squeeze | **Zoom** (scroll) | — *(see disambiguation note below)* |
| Right hand thumb+index pinch, quick tap (<200ms, low movement) | Select/click | Select/click |
| Right hand thumb+index pinch-hold + move (past threshold) | — | **Grab / move (G)** |
| Right hand thumb+middle pinch-hold + move | — | **Rotate (R)** |
| Right hand thumb+ring pinch-hold + move toward/away from object | — | **Scale (S)** |
| Right hand fast short horizontal swipe, open hand | **Undo** (left) / **Redo** (right) | same |
| Left hand fist held | Multi-select modifier (Shift-click) | same |
| Left hand flat hand held ~1s | Toggle Edit/Object mode (Tab) | same |
| Right hand, index finger only extended, held | Measure/inspect cursor (CAD-specific — see §2.4) | — |

**Disambiguation note (important):** two-hand pinch-spread is mapped to **Zoom only** in Path A, never Scale. The emulation layer has no way to know whether an object is actually selected, so overloading that gesture would mean blind guessing. Scale gets its own single-hand gesture (thumb+ring) instead. Once Path B exists (§4), the add-on *can* check `bpy.context.selected_objects`, and reclaiming two-hand-spread for Scale-when-selected becomes safe — that's an explicit Path A→B improvement, not a Path A goal.

This is a starting point, not a final answer — same as your MVP doc already says about pinch thresholds: expect to retune after real use, especially anything involving the rotate/scale gestures fighting for the same hand shapes as click/drag.

### 2.3 Config-driven profiles (`config.py`)

```python
APP_PROFILES = {
    "blender": {
        "process_match": ["blender.exe"],
        "sink": "emulate_input",          # switches to "blender_api" once Path B lands
        "gestures": {
            "OPEN_HAND_MOVE":        {"action": "pan",    "emulate": {"button": "middle", "modifiers": ["shift"]}},
            "FIST_MOVE":             {"action": "orbit",  "emulate": {"button": "middle", "modifiers": []}},
            "TWO_HAND_PINCH_SPREAD": {"action": "zoom",   "emulate": {"input": "scroll"}},
            "PINCH_INDEX_TAP":       {"action": "select", "emulate": {"button": "left", "click": True}},
            "PINCH_INDEX_HOLD_MOVE": {"action": "grab",   "emulate": {"button": "left", "drag": True}},
            "PINCH_MIDDLE_HOLD_MOVE":{"action": "rotate",  "emulate": {"key": "r", "track_mouse": True}},
            "PINCH_RING_HOLD_MOVE":  {"action": "scale",   "emulate": {"key": "s", "track_mouse": True}},
            "SWIPE_LEFT":            {"action": "undo",   "emulate": {"key_combo": ["ctrl", "z"]}},
            "SWIPE_RIGHT":           {"action": "redo",   "emulate": {"key_combo": ["ctrl", "shift", "z"]}},
            "LEFT_HAND_FLAT_HOLD":   {"action": "toggle_mode", "emulate": {"key": "tab"}},
        },
    },

    "fusion360": {
        "process_match": ["Fusion360.exe"],
        "sink": "emulate_input",
        "gestures": {
            "OPEN_HAND_MOVE":        {"action": "pan",   "emulate": {"button": "middle", "modifiers": []}},
            "FIST_MOVE":             {"action": "orbit", "emulate": {"button": "middle", "modifiers": ["shift"]}},
            "TWO_HAND_PINCH_SPREAD": {"action": "zoom",  "emulate": {"input": "scroll"}},
            "PINCH_INDEX_TAP":       {"action": "select","emulate": {"button": "left", "click": True}},
            # nav bindings above assume Fusion's default preset — verify against your actual nav-mode setting
        },
    },

    "_default": {
        "process_match": None,   # fallback: your existing MVP desktop mapping
        "sink": "emulate_input",
        "gestures": { },  # unchanged from Phase 0-8
    },
}
```

`GestureRecognizer` keeps emitting the same `GestureEvent` stream it already does — only the *lookup table* used to turn an event into an OS action changes based on which profile is active. No changes needed to the recognizer itself.

### 2.4 3D-printing-specific note

Fusion 360 / FreeCAD / Tinkercad-style tools have many more app-specific commands than Blender (sketch mode, extrude, fillet, boolean ops, measure/inspect). Don't try to gesture-map all of them up front — that's a lot of new gesture shapes competing for the same hand poses. Keep the **universal 8–10 gestures above** (nav + select + grab/rotate/scale + undo/redo + mode-toggle) consistent across every profile, and treat anything beyond that as an optional per-profile extension slot you fill in only once you know which specific commands you're actually reaching for the keyboard for. The config format already supports this — a profile's `gestures` dict can be as small or large as you want.

---

## 3. Plugin system — adding a new app profile

Goal: adding support for a new app should mean writing one small file, not touching `gesture_recognizer.py` or `controller.py`.

```
backend/
  profiles/
    __init__.py        # loader
    blender_profile.py
    fusion360_profile.py
    freecad_profile.py   # ← new app = new file like this
```

Loader (`profiles/__init__.py`):

```python
import importlib, pkgutil

def load_profiles() -> dict:
    profiles = {}
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_name}")
        if hasattr(module, "register"):
            module.register(profiles)
    return profiles
```

A new profile file just needs:

```python
# profiles/freecad_profile.py
def register(profiles: dict):
    profiles["freecad"] = {
        "process_match": ["FreeCAD.exe"],
        "sink": "emulate_input",
        "gestures": {
            "FIST_MOVE": {"action": "orbit", "emulate": {"button": "middle", "modifiers": []}},
            "OPEN_HAND_MOVE": {"action": "pan", "emulate": {"button": "middle", "modifiers": ["shift"]}},
            "TWO_HAND_PINCH_SPREAD": {"action": "zoom", "emulate": {"input": "scroll"}},
            # add more only as you find yourself needing them
        },
    }
```

That's the whole extension surface — `ProfileManager` and `OSController` don't need to know FreeCAD exists.

---

## 4. Path B — Direct Blender API integration (stretch phase)

Higher fidelity, Blender-only. Replaces synthetic mouse/keyboard events with a second transport straight into Blender's Python environment.

### 4.1 Why bother, given Path A works

Emulated input has real jank once you get past simple orbit/pan: modal operators like Grab/Rotate/Scale expect to read live mouse deltas from Blender's own event loop, so faking "hold R then move the mouse" via `pydirectinput` works but is timing-sensitive and can't be smoothed. Path B removes the middleman.

### 4.2 Architecture

```
GestureRecognizer → BlenderAPIController → HTTP POST (localhost) → Blender add-on
                                                                        │
                                                              background listener
                                                              (queues incoming events)
                                                                        │
                                                          bpy.app.timers callback,
                                                          runs every tick on Blender's
                                                          own thread, drains queue,
                                                          applies to selected object
```

**Practical note:** driving Blender's *modal* operators (the ones that normally track live mouse movement, like `G`/`R`/`S`) from outside Blender's UI event loop is fragile — they're built to consume real `bpy.types.Event` objects from Blender's own input system, not injected data. The reliable pattern instead is to **skip the modal operator entirely** and apply deltas directly to object properties inside a polling timer:

```python
# inside the Blender add-on
import bpy

gesture_queue = []  # populated by the local HTTP listener thread

def process_gestures():
    while gesture_queue:
        event = gesture_queue.pop(0)
        obj = bpy.context.active_object
        if not obj:
            continue
        if event["action"] == "grab":
            obj.location.x += event["dx"] * SENSITIVITY
            obj.location.y += event["dy"] * SENSITIVITY
        elif event["action"] == "rotate":
            obj.rotation_euler.z += event["dtheta"]
        elif event["action"] == "scale":
            factor = 1 + event["ddist"] * SCALE_SENSITIVITY
            obj.scale = obj.scale * factor
    return 0.016  # ~60Hz re-registration

bpy.app.timers.register(process_gestures)
```

This also unlocks the scale-vs-zoom disambiguation noted in §2.2: `bpy.context.selected_objects` is real scene state, so the add-on itself can decide whether a two-hand-spread means "zoom the view" or "scale the object" — something Path A fundamentally can't know.

### 4.3 Transport

A minimal `http.server` (or Flask, if bundling it into the add-on's Python env is acceptable) running on a background thread inside the add-on, listening on `localhost:<port>` for JSON gesture events POSTed by `BlenderAPIController` on the main app side. Same `GestureEvent` schema as Path A — only the sink differs, which is why `APP_PROFILES["blender"]["sink"]` is a single string you flip from `"emulate_input"` to `"blender_api"` once this exists.

---

## 5. Development phases (extends Phases 0–8)

| Phase | Deliverable | Done when... |
|---|---|---|
| 9 | `ProfileManager` | Foreground window/process is detected reliably; switching focus between desktop and Blender swaps the active gesture mapping automatically |
| 10 | CAD/Blender vocabulary, Path A | Orbit/pan/zoom + select/grab/rotate/scale work via emulated input in Blender and at least one other CAD app |
| 11 | Plugin loader | A brand-new app profile (e.g. FreeCAD) can be added by writing one profile file — no changes to core recognizer/controller code |
| 12 | Blender add-on skeleton | Add-on installs, starts the local listener, and a test HTTP request can move a cube in the viewport |
| 13 | Blender add-on gesture bridge, Path B | Grab/rotate/scale on the actual selected object driven directly by live gesture events, no synthetic input involved |

---

## 6. Risks specific to this extension

- **Nav-mode variance:** CAD tools' default navigation bindings are often user-configurable (Fusion 360 especially) — verify against your actual nav preset before trusting the tables in §2.2, and keep bindings in the per-app profile config so a mismatch is a config edit, not a code change.
- **Gesture collision within one profile:** adding ~8–10 new gestures for CAD/Blender raises the chance any two of them get confused for each other (rotate vs. scale, both starting from a pinch-hold). Since the profile system already scopes these gestures to only be "live" while that app has focus, you're not fighting the desktop mapping too — but within a single profile, expect real tuning time here, same as pinch thresholds needed tuning in the MVP.
- **Scale-vs-zoom ambiguity is a Path A limitation, not a bug to fix in Path A** — see §2.2. Don't spend Path A time trying to solve it; it resolves naturally once Path B exists.
- **Path B latency:** the `bpy.app.timers` polling loop introduces its own tick-rate budget (Blender's default timer resolution) — worth profiling once built, the same way Phase 1–2 profiles WebRTC→MediaPipe latency in the base project.

---

## 7. Suggested build order

1. `ProfileManager` + `_default` fallback profile that exactly reproduces current MVP behavior (Phase 9) — should be a no-op change from the user's perspective until a second profile exists.
2. Blender profile, Path A, nav gestures only (orbit/pan/zoom) — smallest useful slice, immediately testable.
3. Add select/grab/rotate/scale to the Blender profile once nav feels solid.
4. Copy the pattern to one CAD app (Fusion 360 or FreeCAD, whichever you actually use for 3D-printing work) — this is what proves the plugin system is actually reusable and not just Blender-shaped.
5. Only then start Path B, once you know from real use which Blender interactions actually feel bad through emulation and are worth the extra transport.
