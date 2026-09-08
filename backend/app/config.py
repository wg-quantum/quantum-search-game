"""Runtime configuration, read from the environment once at import time.

With nothing set the app behaves exactly as it did before this module existed:
Aer only, dev CORS origins, no static frontend, hardware mode off. Every value
below is therefore optional, and a bad value fails loudly at startup rather
than at the first request.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Local development reads backend/.env; it is gitignored and holds the IBM
# Quantum token. Deployments inject the same names as real environment
# variables, which take precedence (load_dotenv does not override).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")

# QPU seconds are the scarce resource: the Open Plan grants ~10 minutes (600 s)
# per month, and a measured downscaled job bills 2 s. 6/day is ~180 jobs/month
# ~= 360 s, which leaves headroom instead of spending the whole budget on the
# ceiling. These caps are process-wide (not per-user) precisely because a public
# deployment shares one token — see docs/DEPLOY.md.
DEFAULT_JOBS_PER_HOUR = 3
DEFAULT_JOBS_PER_DAY = 6
DEFAULT_SHOTS = 1024
MAX_SHOTS = 4096


def _str(name: str) -> str | None:
    raw = os.getenv(name, "").strip()
    return raw or None


def _int(name: str, default: int, *, minimum: int = 0) -> int:
    raw = _str(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from None
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}, got {value}")
    return value


def _bool(name: str, default: bool) -> bool:
    raw = _str(name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in ("1", "true", "yes", "on"):
        return True
    if lowered in ("0", "false", "no", "off"):
        return False
    raise RuntimeError(f"{name} must be a boolean, got {raw!r}")


@dataclass(frozen=True)
class HardwareSettings:
    """IBM Quantum credentials and quota guards."""

    token: str | None = None
    instance: str | None = None
    channel: str = "ibm_quantum_platform"
    backend_name: str | None = None  # None => least_busy operational QPU
    shots: int = DEFAULT_SHOTS
    max_jobs_per_hour: int = DEFAULT_JOBS_PER_HOUR
    max_jobs_per_day: int = DEFAULT_JOBS_PER_DAY
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "HardwareSettings":
        token = _str("IBM_QUANTUM_TOKEN")
        shots = _int("IBM_QUANTUM_SHOTS", DEFAULT_SHOTS, minimum=1)
        if shots > MAX_SHOTS:
            raise RuntimeError(f"IBM_QUANTUM_SHOTS must be <= {MAX_SHOTS}, got {shots}")
        return cls(
            token=token,
            instance=_str("IBM_QUANTUM_INSTANCE"),
            channel=_str("IBM_QUANTUM_CHANNEL") or "ibm_quantum_platform",
            backend_name=_str("IBM_QUANTUM_BACKEND"),
            shots=shots,
            max_jobs_per_hour=_int(
                "IBM_QUANTUM_MAX_JOBS_PER_HOUR", DEFAULT_JOBS_PER_HOUR, minimum=1
            ),
            max_jobs_per_day=_int(
                "IBM_QUANTUM_MAX_JOBS_PER_DAY", DEFAULT_JOBS_PER_DAY, minimum=1
            ),
            # A token is necessary but not sufficient: HARDWARE_ENABLED=0 turns
            # the feature off without removing the credential.
            enabled=bool(token) and _bool("HARDWARE_ENABLED", True),
        )


@dataclass(frozen=True)
class Settings:
    allowed_origins: tuple[str, ...] = DEV_ORIGINS
    static_dir: Path | None = None
    hardware: HardwareSettings = field(default_factory=HardwareSettings)

    @classmethod
    def from_env(cls) -> "Settings":
        origins = _str("ALLOWED_ORIGINS")
        static = _str("STATIC_DIR")
        static_path = Path(static).resolve() if static else _default_static_dir()
        return cls(
            allowed_origins=(
                tuple(o.strip() for o in origins.split(",") if o.strip())
                if origins
                else DEV_ORIGINS
            ),
            static_dir=static_path,
            hardware=HardwareSettings.from_env(),
        )


def _default_static_dir() -> Path | None:
    """The built frontend, as the Docker image lays it out. None when absent.

    app/static/ — inside the package, next to this file, which is where the
    Dockerfile copies the Vite build to.
    """
    candidate = Path(__file__).resolve().parent / "static"
    return candidate if (candidate / "index.html").is_file() else None
