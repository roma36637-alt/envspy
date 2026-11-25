"""envspy hook for Python.

The interpreter imports this module on startup (envspy puts its directory on
PYTHONPATH). It swaps os.environ for a subclass that records every read.
Only variable NAMES are recorded, never values.
"""
import os
import sys

_LOG = os.environ.get("ENVSPY_LOG")


def _chain_next_sitecustomize():
    """Don't shadow a sitecustomize that the system or the user already has."""
    me = os.path.realpath(__file__)
    for entry in list(sys.path):
        try:
            candidate = os.path.join(entry or ".", "sitecustomize.py")
            if not os.path.isfile(candidate) or os.path.realpath(candidate) == me:
                continue
            import importlib.util

            spec = importlib.util.spec_from_file_location("_envspy_chained_sitecustomize", candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return
        except Exception:
            continue


def _install(log_path):
    import json
    import sysconfig

    stdlib = os.path.realpath(sysconfig.get_paths()["stdlib"])
    fd = os.open(
        log_path,
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
        0o600,
    )
    seen = set()
    categories = {}
    state = {"busy": False, "bulk": 0}
    bulk_expected = set()
    skip_modules = {"os", "_collections_abc", __name__}
    getitem = os._Environ.__getitem__

    def categorize(filename):
        cat = categories.get(filename)
        if cat is None:
            norm = filename.replace("\\", "/")
            if "/site-packages/" in norm or "/dist-packages/" in norm:
                cat = "lib"
            elif filename.startswith("<frozen") or os.path.realpath(filename).startswith(stdlib):
                cat = "runtime"
            else:
                cat = "app"
            categories[filename] = cat
        return cat

    def record(key, mode, was_set):
        # Always called directly from a SpyEnviron method, so frame 2 is the caller.
        if state["busy"] or state["bulk"] or not isinstance(key, str):
            return
        if bulk_expected:
            # dict(os.environ) fetches keys() first, then reads the values one by
            # one. Treat those reads as a bulk copy, not individual reads.
            if key in bulk_expected:
                bulk_expected.discard(key)
                return
            bulk_expected.clear()
        state["busy"] = True
        try:
            frame = sys._getframe(2)
            while frame is not None and frame.f_globals.get("__name__") in skip_modules:
                frame = frame.f_back
            if frame is None:
                return
            filename = frame.f_code.co_filename
            line = frame.f_lineno
            marker = (key, filename, line, mode, was_set)
            if marker in seen:
                return
            seen.add(marker)
            event = {
                "k": key,
                "m": mode,  # required | optional | default
                "s": was_set,
                "f": filename,
                "l": line,
                "c": categorize(filename),
                "p": os.getpid(),
            }
            os.write(fd, (json.dumps(event) + "\n").encode("utf-8"))
        except Exception:
            pass
        finally:
            state["busy"] = False

    class SpyEnviron(os._Environ):
        def __getitem__(self, key):
            try:
                value = getitem(self, key)
            except KeyError:
                record(key, "required", False)
                raise
            record(key, "required", True)
            return value

        def get(self, key, default=None):
            mode = "default" if default is not None else "optional"
            try:
                value = getitem(self, key)
            except KeyError:
                record(key, mode, False)
                return default
            record(key, mode, True)
            return value

        def __contains__(self, key):
            try:
                getitem(self, key)
            except KeyError:
                record(key, "optional", False)
                return False
            record(key, "optional", True)
            return True

        def setdefault(self, key, value):
            try:
                current = getitem(self, key)
            except KeyError:
                record(key, "default", False)
                self[key] = value
                return value
            record(key, "default", True)
            return current

        def pop(self, key, *default):
            mode = "default" if default else "required"
            try:
                value = getitem(self, key)
            except KeyError:
                record(key, mode, False)
                if default:
                    return default[0]
                raise
            record(key, mode, True)
            del self[key]
            return value

        def keys(self):
            # Bulk operations (dict(os.environ), json.dumps, logging) ask for
            # keys() first. Mark them so the following value reads are treated
            # as a copy rather than individual reads.
            view = super().keys()
            try:
                bulk_expected.update(view)
            except Exception:
                pass
            return view

        def __iter__(self):
            # dict(os.environ), os.environ.copy(), .items() ... are bulk copies,
            # not "the program reads this variable". Mute them while iterating.
            state["bulk"] += 1
            try:
                yield from super().__iter__()
            finally:
                state["bulk"] -= 1

    base = os.environ
    arguments = [base._data, base.encodekey, base.decodekey, base.encodevalue, base.decodevalue]
    try:
        # Python 3.14: _Environ.__init__ takes five arguments.
        spy = SpyEnviron(*arguments)
    except TypeError:
        # Python <= 3.13 also requires putenv/unsetenv.
        spy = SpyEnviron(*arguments, base.putenv, base.unsetenv)
    os.environ = spy


_chain_next_sitecustomize()
if _LOG:
    try:
        _install(_LOG)
    except Exception:
        pass