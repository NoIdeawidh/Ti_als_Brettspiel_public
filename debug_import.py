# debug_import.py
import importlib, traceback
importlib.invalidate_caches()

try:
    import sub.server as m
    print("OK, module loaded. Visible names:")
    names = [n for n in dir(m) if not n.startswith("_")]
    print(names)
    # show whether create_app exists and socketio exists
    print("create_app present?", hasattr(m, "create_app"))
    print("socketio present?", hasattr(m, "socketio"))
except Exception:
    traceback.print_exc()
