"""Test del backend NVML con un modulo pynvml finto."""
import types

import gpu_backend as gb


class _Mem:
    total = 8 * 1024 ** 3
    used = 1024 ** 3


class _Util:
    gpu = 42


def make_fake_nvml(cores=6144, cc=(8, 9), count=1):
    """Costruisce un finto modulo pynvml con valori prevedibili."""
    m = types.SimpleNamespace()
    m.nvmlInit = lambda: None
    m.nvmlShutdown = lambda: None
    m.nvmlSystemGetDriverVersion = lambda: b"555.99"
    m.nvmlDeviceGetCount = lambda: count
    m.nvmlDeviceGetHandleByIndex = lambda i: f"H{i}"
    m.nvmlDeviceGetName = lambda h: b"Fake GPU"
    m.nvmlDeviceGetMemoryInfo = lambda h: _Mem()
    m.nvmlDeviceGetCudaComputeCapability = lambda h: cc
    m.nvmlDeviceGetEnforcedPowerLimit = lambda h: 250000
    if cores is None:
        def _raise(h):
            raise RuntimeError("non supportato")
        m.nvmlDeviceGetNumGpuCores = _raise
    else:
        m.nvmlDeviceGetNumGpuCores = lambda h: cores
    m.nvmlDeviceGetUtilizationRates = lambda h: _Util()
    m.NVML_TEMPERATURE_GPU = 0
    m.nvmlDeviceGetTemperature = lambda h, x: 65
    m.nvmlDeviceGetPowerUsage = lambda h: 120000
    m.NVML_CLOCK_SM = 0
    m.NVML_CLOCK_MEM = 1
    m.nvmlDeviceGetClockInfo = lambda h, x: 1800
    m.nvmlDeviceGetFanSpeed = lambda h: 45
    m.nvmlDeviceGetPerformanceState = lambda h: 8
    m.nvmlDeviceGetComputeRunningProcesses = lambda h: [
        types.SimpleNamespace(pid=1234, usedGpuMemory=512 * 1024 ** 2)]
    m.nvmlDeviceGetGraphicsRunningProcesses = lambda h: [
        types.SimpleNamespace(pid=5678, usedGpuMemory=256 * 1024 ** 2)]
    return m


def test_enumerate_usa_core_nvml(monkeypatch):
    monkeypatch.setattr(gb, "pynvml", make_fake_nvml())
    b = gb.GpuBackend()
    assert b.error is None
    assert len(b.infos) == 1
    info = b.infos[0]
    assert info.name == "Fake GPU"
    assert info.cuda_cores == 6144
    assert info.core_source == "NVML"
    assert info.sm_count == 6144 // 128  # cc 8.9 -> 128 core/SM
    assert info.mem_total_mb == 8192
    assert info.driver == "555.99"
    assert info.power_limit_w == 250.0


def test_backend_senza_nvml(monkeypatch):
    monkeypatch.setattr(gb, "pynvml", None)
    b = gb.GpuBackend()
    assert b.error is not None
    assert b.infos == []


def test_fallback_sm_x_core(monkeypatch):
    monkeypatch.setattr(gb, "pynvml", make_fake_nvml(cores=None))
    monkeypatch.setattr(gb.GpuBackend, "_torch_sm", lambda self, i: 48)
    b = gb.GpuBackend()
    info = b.infos[0]
    assert info.sm_count == 48
    assert info.cuda_cores == 48 * 128
    assert info.core_source == "SM x core/SM (stima)"


def test_fallback_senza_torch(monkeypatch):
    monkeypatch.setattr(gb, "pynvml", make_fake_nvml(cores=None))
    monkeypatch.setattr(gb.GpuBackend, "_torch_sm", lambda self, i: None)
    b = gb.GpuBackend()
    info = b.infos[0]
    assert info.cuda_cores is None
    assert info.core_source == "n/d"


def test_sample(monkeypatch):
    monkeypatch.setattr(gb, "pynvml", make_fake_nvml())
    b = gb.GpuBackend()
    s = b.sample(0)
    assert s.util == 42
    assert s.mem_used_mb == 1024
    assert s.temp_c == 65
    assert s.power_w == 120.0
    assert s.sm_clock == 1800
    assert s.mem_clock == 1800
    assert s.fan_pct == 45
    assert s.pstate == "P8"


def test_processes(monkeypatch):
    monkeypatch.setattr(gb, "pynvml", make_fake_nvml())
    monkeypatch.setattr(gb, "_proc_name", lambda pid: f"proc{pid}")
    b = gb.GpuBackend()
    procs = b.processes(0)
    assert [p["pid"] for p in procs] == [1234, 5678]  # ordine per mem desc
    assert procs[0] == {"pid": 1234, "name": "proc1234", "mem_mb": 512}
    assert procs[1]["mem_mb"] == 256


def test_processes_vuoti(monkeypatch):
    fake = make_fake_nvml()
    fake.nvmlDeviceGetComputeRunningProcesses = lambda h: []
    fake.nvmlDeviceGetGraphicsRunningProcesses = lambda h: []
    monkeypatch.setattr(gb, "pynvml", fake)
    b = gb.GpuBackend()
    assert b.processes(0) == []


class _FakeBackend:
    """Backend finto per testare GpuManager senza hardware."""

    def __init__(self, infos, sample=None):
        self.infos = infos
        self.error = None
        self._sample = sample
        self.closed = False

    def sample(self, idx):
        return self._sample

    def processes(self, idx):
        return []

    def shutdown(self):
        self.closed = True


def _gpu_info(vendor="Fake"):
    return gb.GpuInfo(index=0, name=f"{vendor} GPU", cuda_cores=None,
                      core_source="n/d", compute_cap=None, sm_count=None,
                      mem_total_mb=0, driver="", vendor=vendor)


def test_gpu_manager_aggrega():
    s = gb.GpuSample(util=7)
    b1 = _FakeBackend([_gpu_info("NVIDIA"), _gpu_info("NVIDIA")], s)
    b2 = _FakeBackend([_gpu_info("AMD")], s)
    m = gb.GpuManager(backends=(lambda: b1, lambda: b2))
    assert len(m.infos) == 3
    assert [i.index for i in m.infos] == [0, 1, 2]  # rinumerati
    assert m.sample(2).util == 7  # instradato al secondo backend
    assert m.processes(0) == []
    assert m.error is None
    m.shutdown()
    assert b1.closed and b2.closed


def test_gpu_manager_senza_gpu():
    m = gb.GpuManager(backends=(lambda: _FakeBackend([]),))
    assert m.infos == []
    assert m.error is not None


def test_gpu_manager_backend_che_sollevano():
    def _boom():
        raise RuntimeError("driver assente")
    m = gb.GpuManager(backends=(_boom, lambda: _FakeBackend([_gpu_info()])))
    assert len(m.infos) == 1


def test_gpuinfo_vendor_default():
    info = gb.GpuInfo(0, "X", 1, "NVML", None, None, 0, "")
    assert info.vendor == "NVIDIA"


def test_backend_amd_intel_non_esplodono():
    """Su questa macchina possono mancare le lib: basta che non crashino."""
    for cls in (gb.AmdBackend, gb.IntelBackend):
        b = cls()
        assert isinstance(b.infos, list)
        assert b.processes(0) == [] if b.infos else True


def test_registry_adapters_tipo():
    adapters = gb._registry_adapters()
    assert isinstance(adapters, list)
    for name, mem, prov in adapters:
        assert isinstance(name, str) and isinstance(mem, int)


def test_cores_per_sm_valido():
    for cc, cores in gb.CORES_PER_SM.items():
        assert isinstance(cc, tuple) and len(cc) == 2
        assert cores > 0
