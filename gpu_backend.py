"""Accesso alle GPU: NVIDIA (NVML), AMD (amdsmi/pyadl/registro) e Intel.

Conteggio CUDA core: metodo diretto ``nvmlDeviceGetNumGpuCores`` con fallback
su stima ``SM x core/SM`` (conteggio SM via PyTorch, se installato) in base
alla compute capability. AMD e Intel sono rilevate al meglio delle API
disponibili; le metriche live possono essere parziali o assenti.
"""
import sys
from dataclasses import dataclass
from typing import Optional

from logger import get_logger

log = get_logger(__name__)

try:
    import pynvml
except ImportError:  # gestito a runtime
    pynvml = None

# Core CUDA per SM in base alla compute capability (major, minor)
CORES_PER_SM = {
    (2, 0): 32, (2, 1): 48,
    (3, 0): 192, (3, 5): 192, (3, 7): 192,
    (5, 0): 128, (5, 2): 128, (5, 3): 128,
    (6, 0): 64, (6, 1): 128, (6, 2): 128,
    (7, 0): 64, (7, 2): 64, (7, 5): 64,
    (8, 0): 64, (8, 6): 128, (8, 7): 128, (8, 9): 128,
    (9, 0): 128,
    (10, 0): 128, (12, 0): 128,
}


@dataclass
class GpuInfo:
    index: int
    name: str
    cuda_cores: Optional[int]
    core_source: str
    compute_cap: Optional[tuple]
    sm_count: Optional[int]
    mem_total_mb: int
    driver: str
    power_limit_w: Optional[float] = None
    vendor: str = "NVIDIA"


@dataclass
class GpuSample:
    util: int = 0
    mem_used_mb: int = 0
    temp_c: int = 0
    power_w: float = 0.0
    sm_clock: int = 0
    mem_clock: int = 0
    fan_pct: int = 0
    pstate: str = ""


def _proc_name(pid: int) -> str:
    """Nome del processo dato il PID (via psutil, se installato)."""
    try:
        import psutil
        return psutil.Process(pid).name()
    except Exception:
        return ""


class GpuBackend:
    """Enumerazione e campionamento delle GPU via NVML."""

    def __init__(self):
        self.handles = []
        self.infos: list[GpuInfo] = []
        self.error = None
        if pynvml is None:
            self.error = "Modulo 'nvidia-ml-py' non installato (pip install nvidia-ml-py)."
            log.error(self.error)
            return
        try:
            pynvml.nvmlInit()
            self._enumerate()
            log.info("GPU rilevate: %d", len(self.infos))
        except Exception as e:
            self.error = f"NVML non disponibile: {e}"
            log.error("Inizializzazione NVML fallita: %s", e)

    @staticmethod
    def _s(v):
        return v.decode() if isinstance(v, bytes) else v

    def _torch_sm(self, idx):
        try:
            import torch
            if torch.cuda.is_available() and idx < torch.cuda.device_count():
                return torch.cuda.get_device_properties(idx).multi_processor_count
        except Exception:
            pass
        return None

    def _enumerate(self):
        driver = self._s(pynvml.nvmlSystemGetDriverVersion())
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            self.handles.append(h)
            name = self._s(pynvml.nvmlDeviceGetName(h))
            mem = pynvml.nvmlDeviceGetMemoryInfo(h).total // (1024 ** 2)

            cc = None
            try:
                cc = tuple(pynvml.nvmlDeviceGetCudaComputeCapability(h))
            except Exception:
                pass

            plimit = None
            try:
                plimit = pynvml.nvmlDeviceGetEnforcedPowerLimit(h) / 1000.0
            except Exception:
                pass

            cores, source, sm = None, "n/d", None
            try:  # metodo diretto (driver recenti)
                cores = int(pynvml.nvmlDeviceGetNumGpuCores(h))
                source = "NVML"
                cps = CORES_PER_SM.get(cc)
                if cps:
                    sm = cores // cps
            except Exception:
                sm = self._torch_sm(i)
                cps = CORES_PER_SM.get(cc)
                if sm and cps:
                    cores = sm * cps
                    source = "SM x core/SM (stima)"

            log.debug("GPU %d: %s, core=%s (%s)", i, name, cores, source)
            self.infos.append(GpuInfo(i, name, cores, source, cc, sm, mem,
                                      driver, plimit))

    def sample(self, idx) -> GpuSample:
        """Legge un campione live dalla GPU ``idx``."""
        h = self.handles[idx]
        s = GpuSample()
        try:
            s.util = pynvml.nvmlDeviceGetUtilizationRates(h).gpu
            s.mem_used_mb = pynvml.nvmlDeviceGetMemoryInfo(h).used // (1024 ** 2)
            s.temp_c = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        except Exception as e:
            log.debug("Campionamento base fallito: %s", e)
        try:
            s.power_w = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
        except Exception as e:
            log.debug("Lettura potenza fallita: %s", e)
        try:
            s.sm_clock = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_SM)
            s.mem_clock = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_MEM)
        except Exception as e:
            log.debug("Lettura clock fallita: %s", e)
        try:
            s.fan_pct = pynvml.nvmlDeviceGetFanSpeed(h)
        except Exception as e:
            log.debug("Lettura ventola fallita: %s", e)
        try:
            s.pstate = f"P{pynvml.nvmlDeviceGetPerformanceState(h)}"
        except Exception as e:
            log.debug("Lettura P-state fallita: %s", e)
        return s

    def processes(self, idx) -> list[dict]:
        """Processi che usano la GPU ``idx``.

        Returns:
            Lista di ``{"pid", "name", "mem_mb"}`` ordinata per memoria
            decrescente (compute + grafica, deduplicati per PID).
        """
        h = self.handles[idx]
        procs: dict[int, int] = {}
        for getter in ("nvmlDeviceGetComputeRunningProcesses",
                       "nvmlDeviceGetGraphicsRunningProcesses"):
            try:
                for p in getattr(pynvml, getter)(h):
                    mem = getattr(p, "usedGpuMemory", 0) or 0
                    procs[p.pid] = procs.get(p.pid, 0) + mem // (1024 ** 2)
            except Exception as e:
                log.debug("%s fallita: %s", getter, e)
        return [
            {"pid": pid, "name": _proc_name(pid), "mem_mb": mb}
            for pid, mb in sorted(procs.items(),
                                  key=lambda kv: kv[1], reverse=True)
        ]

    def shutdown(self):
        if pynvml and not self.error:
            try:
                pynvml.nvmlShutdown()
            except Exception as e:
                log.debug("nvmlShutdown fallita: %s", e)


# ---------------------------------------------------------------------------
# Rilevamento adattatori dal registro di Windows (info statiche)
# ---------------------------------------------------------------------------
_DISPLAY_CLASS_KEY = (r"SYSTEM\CurrentControlSet\Control\Class"
                      r"\{4d36e968-e325-11ce-bfc1-08002be10318}")


def _reg_str(key, name: str) -> str:
    import winreg
    try:
        v, _ = winreg.QueryValueEx(key, name)
        return v if isinstance(v, str) else ""
    except OSError:
        return ""


def _reg_mem(key) -> int:
    """VRAM dell'adattatore in MB dal registro (0 se non disponibile)."""
    import winreg
    for name in ("qwMemorySize", "AdapterRAM"):
        try:
            v, _ = winreg.QueryValueEx(key, f"HardwareInformation.{name}")
        except OSError:
            continue
        if isinstance(v, int):
            return v // (1024 ** 2)
        if isinstance(v, bytes):
            return int.from_bytes(v[:8].ljust(8, b"\0"), "little") // (1024 ** 2)
    return 0


def _registry_adapters() -> list[tuple[str, int, str]]:
    """Adattatori video dal registro Windows: ``[(nome, mem_mb, provider)]``."""
    if sys.platform != "win32":
        return []
    out = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            _DISPLAY_CLASS_KEY) as key:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(key, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(key, sub) as sk:
                        name = _reg_str(sk, "DriverDesc")
                        if name:
                            out.append((name, _reg_mem(sk),
                                        _reg_str(sk, "ProviderName")))
                except OSError:
                    continue
    except OSError as e:
        log.debug("Enumerazione registro adattatori fallita: %s", e)
    return out


# ---------------------------------------------------------------------------
# Backend AMD (amdsmi -> pyadl -> registro, tutto opzionale)
# ---------------------------------------------------------------------------
class AmdBackend:
    """GPU AMD: metriche live via amdsmi o pyadl, altrimenti solo info statiche."""

    def __init__(self):
        self.handles = []
        self.infos: list[GpuInfo] = []
        self.error = None
        self._mode = None
        self._amdsmi = None
        self._pyadl = None
        try:
            import amdsmi
            amdsmi.amdsmi_init()
            self._amdsmi = amdsmi
            self._mode = "amdsmi"
            self._enumerate_amdsmi()
            return
        except ImportError:
            pass
        except Exception as e:
            log.debug("amdsmi_init fallita: %s", e)
        try:
            import pyadl
            self._pyadl = pyadl
            self._mode = "pyadl"
            self._enumerate_pyadl()
            return
        except ImportError:
            pass
        except Exception as e:
            log.debug("pyadl fallita: %s", e)
        # Fallback: info statiche dal registro (solo Windows)
        self._enumerate_registry()
        if not self.infos:
            self.error = ("AMD: nessuna GPU rilevata (installa 'amdsmi' o "
                          "'pyadl' per le metriche live).")

    def _enumerate_amdsmi(self):
        a = self._amdsmi
        for i, h in enumerate(a.amdsmi_get_processor_handles()):
            self.handles.append(h)
            name = "AMD GPU"
            try:
                info_d = a.amdsmi_get_gpu_asic_info(h)
                name = info_d.get("market_name") or name
            except Exception:
                pass
            mem = 0
            try:
                mem = (a.amdsmi_get_gpu_memory_total(h, "vram")
                       // (1024 ** 2))
            except Exception:
                pass
            self.infos.append(GpuInfo(i, name, None, "n/d", None, None,
                                      mem, "", None, "AMD"))

    def _enumerate_pyadl(self):
        for i, d in enumerate(self._pyadl.ADLManager.getInstance()
                              .getDevices()):
            self.handles.append(d)
            name = getattr(d, "adapterName", "AMD GPU")
            if isinstance(name, bytes):
                name = name.decode(errors="replace")
            self.infos.append(GpuInfo(i, name, None, "n/d", None, None,
                                      0, "", None, "AMD"))

    def _enumerate_registry(self):
        for name, mem, prov in _registry_adapters():
            tag = f"{name} {prov}".lower()
            if any(k in tag for k in ("amd", "radeon", "advanced micro")):
                self.infos.append(GpuInfo(len(self.infos), name, None,
                                          "n/d", None, None, mem, "",
                                          None, "AMD"))

    def sample(self, idx) -> GpuSample:
        s = GpuSample()
        if self._mode == "amdsmi":
            a, h = self._amdsmi, self.handles[idx]
            try:
                s.util = a.amdsmi_get_gpu_activity(h).get(
                    "average_gfx_activity", 0)
            except Exception:
                pass
            try:
                s.mem_used_mb = a.amdsmi_get_gpu_memory_usage(
                    h, "vram") // (1024 ** 2)
            except Exception:
                pass
            try:
                s.temp_c = a.amdsmi_get_temp_metric(
                    h, a.AmdSmiTemperatureType.EDGE,
                    a.AmdSmiTemperatureMetric.CURRENT)
            except Exception:
                pass
            try:
                s.power_w = float(a.amdsmi_get_power_info(h).get(
                    "average_socket_power", 0))
            except Exception:
                pass
            try:
                s.fan_pct = a.amdsmi_get_gpu_fan_speed(h, 0)
            except Exception:
                pass
        elif self._mode == "pyadl":
            d, p = self.handles[idx], self._pyadl
            try:
                s.util = d.getCurrentUsage()
            except Exception:
                pass
            try:
                s.temp_c = d.getCurrentTemperature()
            except Exception:
                pass
            try:
                s.fan_pct = d.getCurrentFanSpeed(
                    p.ADL_DEVICE_FAN_SPEED_TYPE.FAN_SPEED_PERCENT)
            except Exception:
                pass
        return s

    def processes(self, idx) -> list[dict]:
        return []

    def shutdown(self):
        if self._mode == "amdsmi":
            try:
                self._amdsmi.amdsmi_shut_down()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Backend Intel (rilevamento da registro, solo info statiche)
# ---------------------------------------------------------------------------
class IntelBackend:
    """GPU Intel rilevate dal registro di Windows (nessuna metrica live)."""

    def __init__(self):
        self.handles = []
        self.infos: list[GpuInfo] = []
        self.error = None
        if sys.platform != "win32":
            self.error = "GPU Intel: rilevamento disponibile solo su Windows."
            return
        for name, mem, prov in _registry_adapters():
            if "intel" in f"{name} {prov}".lower():
                self.infos.append(GpuInfo(len(self.infos), name, None,
                                          "n/d", None, None, mem, "",
                                          None, "Intel"))
        if not self.infos:
            self.error = "Nessuna GPU Intel rilevata."

    def sample(self, idx) -> GpuSample:
        return GpuSample()

    def processes(self, idx) -> list[dict]:
        return []

    def shutdown(self):
        pass


# ---------------------------------------------------------------------------
# Facciata multi-vendor
# ---------------------------------------------------------------------------
class GpuManager:
    """Aggrega i backend dei vendor in una vista unica numerata globalmente.

    Args:
        backends: classi backend da usare (default: NVML, AMD, Intel).
                  Utile nei test per iniettare backend finti.
    """

    def __init__(self, backends=None):
        self._map: dict[int, tuple] = {}
        self._backends = []
        self.infos: list[GpuInfo] = []
        self.errors: list[str] = []
        for cls in (backends or (GpuBackend, AmdBackend, IntelBackend)):
            try:
                b = cls()
            except Exception as e:
                log.warning("Backend %s non disponibile: %s",
                            cls.__name__, e)
                continue
            if getattr(b, "error", None):
                self.errors.append(b.error)
            if not b.infos:
                continue
            self._backends.append(b)
            for i, info in enumerate(b.infos):
                self._map[len(self.infos)] = (b, i)
                info.index = len(self.infos)
                self.infos.append(info)
        self.error = None
        if not self.infos:
            self.error = (self.errors[0] if self.errors
                          else "Nessuna GPU supportata rilevata.")

    def sample(self, idx) -> GpuSample:
        b, i = self._map[idx]
        return b.sample(i)

    def processes(self, idx) -> list[dict]:
        b, i = self._map[idx]
        return b.processes(i) if hasattr(b, "processes") else []

    def shutdown(self):
        for b in self._backends:
            try:
                b.shutdown()
            except Exception:
                pass
