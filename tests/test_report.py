"""Test della generazione dei report (PDF puro + PNG/PDF via Wand)."""
import pytest

import report
from gpu_backend import GpuInfo, GpuSample


def _info():
    return GpuInfo(index=0, name="Fake GPU", cuda_cores=6144,
                   core_source="NVML", compute_cap=(8, 9), sm_count=48,
                   mem_total_mb=8192, driver="555.99", power_limit_w=250.0)


def _sample():
    return GpuSample(util=42, mem_used_mb=1024, temp_c=65,
                     power_w=120.0, sm_clock=1800, mem_clock=1800)


def test_build_pdf_struttura():
    rgb = b"\x10\x20\x30" * 4  # immagine 2x2
    pdf = report._build_pdf(2, 2, rgb)
    assert pdf.startswith(b"%PDF-")
    assert b"/Subtype/Image" in pdf
    assert b"/Width 2" in pdf and b"/Height 2" in pdf
    assert b"/FlateDecode" in pdf
    assert b"startxref" in pdf
    assert pdf.rstrip().endswith(b"%%EOF")


@pytest.mark.skipif(not report.WAND_OK,
                    reason="Wand/ImageMagick non disponibile")
def test_render_report_png(tmp_path):
    out = tmp_path / "report.png"
    report.render_report(_info(), _sample(), str(out))
    data = out.read_bytes()
    assert data.startswith(b"\x89PNG")


@pytest.mark.skipif(not report.WAND_OK,
                    reason="Wand/ImageMagick non disponibile")
def test_render_report_pdf(tmp_path):
    out = tmp_path / "report.pdf"
    report.render_report(_info(), _sample(), str(out))
    data = out.read_bytes()
    assert data.startswith(b"%PDF-")
    assert data.rstrip().endswith(b"%%EOF")
