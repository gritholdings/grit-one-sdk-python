import sys as _sys
import importlib.machinery as _machinery
import importlib.util as _util
import platform as _platform
from pathlib import Path as _Path
_PLATFORM_DIRS = {
    ("Linux", "x86_64"): "linux-x86_64",
    ("Darwin", "arm64"): "macos-aarch64",
}
_NATIVE_ROOT = _Path(__file__).resolve().parent / "_one_native"


def _load_native():
    system, machine = _platform.system(), _platform.machine()
    subdir = _PLATFORM_DIRS.get((system, machine))
    if subdir is None:
        raise ImportError(
            "grit.one has no prebuilt binary for this platform "
            f"({system}/{machine}). Shipped targets: "
            f"{sorted(_PLATFORM_DIRS.values())}."
        )
    so_path = _NATIVE_ROOT / subdir / "one.abi3.so"
    if not so_path.is_file():
        raise ImportError(
            f"grit.one binary missing at {so_path}."
        )
    loader = _machinery.ExtensionFileLoader("grit.one", str(so_path))
    spec = _util.spec_from_loader("grit.one", loader, origin=str(so_path))
    if spec is None:
        raise ImportError(f"could not build an import spec for {so_path}")
    module = _util.module_from_spec(spec)
    loader.exec_module(module)
    return module
_self = _sys.modules[__name__]
_native = _load_native()
_sys.modules[__name__] = _self
globals().update({
    _name: getattr(_native, _name)
    for _name in dir(_native)
    if not _name.startswith("_")
})
del _native, _self
