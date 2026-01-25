# run.py (ERSATZ - robustes, diagnostisches Startskript)
# Leg dieses File als C:\Users\henri\Desktop\Twilight_Imperium_Nachbau\run.py ab (komplett überschreiben).

import sys
import importlib
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
print(f"Starting run.py from: {ROOT}")
# Ensure project root is in sys.path (so Python findet das sub-Package)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    print("Importing module 'sub.server' via importlib...")
    mod = importlib.import_module("sub.server")
    print("Module 'sub.server' loaded. Available names (sample):")
    print([n for n in dir(mod) if not n.startswith("_")][:100])
except Exception as e:
    print("Failed to import sub.server. Full traceback follows:")
    traceback.print_exc()
    sys.exit(1)

# Try to fetch create_app and socketio attributes safely
create_app = getattr(mod, "create_app", None)
socketio = getattr(mod, "socketio", None)

if create_app is None:
    print("ERROR: 'create_app' attribute not found on sub.server module.")
    print("Directory of module (all attrs):")
    print(dir(mod))
    print("Please open sub/server.py and check that a function 'create_app' is defined at top-level.")
    sys.exit(2)

if socketio is None:
    print("WARNING: 'socketio' attribute not found on sub.server module. The app may still run but websockets won't be available.")
else:
    print("'socketio' object found on sub.server.")

# create the app
try:
    app = create_app()
except Exception:
    print("Exception while calling create_app():")
    traceback.print_exc()
    sys.exit(3)

# run using socketio.run if available (keeps previous behavior)
if socketio is not None:
    print("Starting socketio.run(app) ...")
    try:
        # default host/port (matching previous)
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    except Exception:
        print("Exception while running socketio.run():")
        traceback.print_exc()
        sys.exit(4)
else:
    print("No socketio found, falling back to Flask's app.run()")
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception:
        print("Exception while running app.run():")
        traceback.print_exc()
        sys.exit(5)
