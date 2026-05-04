# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TinyCAM** is a desktop CAM (Computer-Aided Manufacturing) application for CNC machines. It parses PCB/vector files (Gerber, Excellon, SVG), visualizes them in 2D/3D, generates G-code toolpaths, and controls GRBL-based CNC machines over serial.

## Workflow

Always implement changes in a worktree. Use `EnterWorktree` with a descriptive name before starting any implementation task.

## Running the Application

```bash
# Via shell script
./tinycam.sh

# Or directly
python3 -m tinycam.main
```

**Setup:**
```bash
pip install -r requirements.txt
```

Python 3.13, virtualenv at `.venv/`. There are no tests, no linter config, and no build system — the app runs directly as a Python module.

## Architecture

The codebase has three layers:

### 1. Data Layer (`tinycam/project/`, `tinycam/formats/`)

- `project/project.py` — `CncProject`: the document model, holds a list of `CncProjectItem`s and manages selection
- `project/item.py` — base `CncProjectItem`, subclassed by `GerberItem`, `ExcellonItem`, `SvgItem`, `RectangleItem`
- `project/jobs/` — `CncCutoutJob`, `CncIsolateJob`, `CncDrillJob`: generate G-code toolpaths from geometry
- `formats/` — parsers for Gerber, Excellon, and SVG files; produce Shapely geometry

### 2. UI Layer (`tinycam/ui/`)

- `ui/main_window.py` — `CncMainWindow` (QMainWindow): tabbed interface with 2D/3D views, menus, project/property panels, and CNC controller UI
- `ui/canvas_2d.py` — 2D orthographic view; hosts the tool system and grid
- `ui/preview_3d.py` — 3D perspective view
- `ui/view.py` — base `CncView`: shared OpenGL setup via ModernGL, framebuffer, picking
- `ui/tools/` — tool classes (`SelectTool`, `TransformTool`, `CircleTool`, `RectangleTool`, `PolylineTool`, `MarkerTool`); handle mouse events on the canvas
- `ui/commands/` — `QUndoCommand` subclasses for undoable operations (import, flip, align, scale, move, etc.)
- `ui/view_items/` — renderable wrappers around project items; split into `core/` (rendering infrastructure) and `canvas/` (canvas-specific items)

### 3. CNC Control (`tinycam/grbl.py`)

- Async serial communication with GRBL firmware via `serial_asyncio` + `qasync`
- Parses status reports, handles alarms and errors
- `ui/cnc_controller.py` — UI for jog controls, state display, and G-code console

### Core Modules

| Module | Purpose |
|--------|---------|
| `application.py` | `CncApplication(QApplication)` — manages project, settings, undo stack, task manager |
| `globals.py` | Global singletons: `geometry`, `app`, `settings`, `controller` |
| `math_types.py` | NumPy-backed `Vector2/3/4`, `Quaternion`, `Matrix33/44`, `Rect`, `Box`, `Ray`, `Plane` |
| `geometry.py` | Shapely-based geometry utilities (circles, offsets, boolean ops) |
| `settings.py` | Hierarchical typed settings with binary serialization and Qt persistence |
| `signals.py` | Custom `Signal`/`SignalInstance` with weak references (similar to Qt signals but for Python) |
| `reactive.py` | `ReactiveVar` — observable value wrapper |
| `gcode.py` | G-code builder |
| `commands.py` | G-code command definitions (travel, cut, speed) |
| `tasks.py` | Async task management |

## Key Patterns

**Signal system:** The project uses a custom signal system (`tinycam/signals.py`) in addition to Qt signals. Python-side signals use weak references to avoid memory leaks — connect with `signal.connect(callback)`.

**Settings:** Access via `globals.settings`. Settings are hierarchical strings (`general/snapping/enabled`). The binary serialization format lives in `settings.py` as `BufferReader`/`BufferWriter`.

**Geometry:** The actual geometry is abstracted with a Geometry class (providing interface to geometry functions) as well as different Shape classes (Point, Line, Polygon, Group, etc). Although those are just re-exports and wrappers of Shapely types, it could change in the future. So, Shapely itself should not occur in source code other than geometry.py. The `math_types.py` types are for 3D math/rendering and are just wrappers on NumPy/Pyrr, providing more convenience usage.

**Project items:** Everything that can be operated upon in the editor are represented by project items (project/item.py descendands). They represent core data for objects like geometry, color and other properties. On top of that, there are view items - view specific sattelite classes that handle visualization for project items in views. They could be different for 2D and 3D to provide different visualization, although currently they are the same. Project item use property system that allows to attach metadata to properties, that can be used to automatically create property inspector UI.
Project items provide signals for when they are updated which can be used to automatically update dependent objects. If certain update might take a lot of time to execute, it should be implemented as asynchronous task, which would be run by task manager.

**Commands:** Project item manipulation should be done through "commands" - an intent objects that change project and project items. The reason - allow for storing editing history and enable undo/redo functionality.

**OpenGL:** Views use ModernGL (not raw OpenGL). Rendering happens in `CncView` subclasses via `view_items/`.

**Async:** The app uses `qasync` to run an asyncio event loop inside Qt's event loop. GRBL serial I/O is fully async — use `async def` and `await` for anything touching the controller.
