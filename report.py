"""Generazione del report GPU (PNG e PDF) tramite Wand/ImageMagick."""
import datetime
import zlib

from gpu_backend import GpuInfo, GpuSample
from lang.language_manager import lang_manager
from logger import get_logger

log = get_logger(__name__)
tr = lang_manager.tr

try:
    from wand.image import Image
    from wand.drawing import Drawing
    from wand.color import Color
    from wand.version import MAGICK_VERSION
    WAND_OK = True
except Exception:  # ImageMagick mancante o Wand non installato
    WAND_OK = False
    MAGICK_VERSION = "non disponibile"
    log.warning("Wand/ImageMagick non disponibile: export report disabilitato")

def _build_pdf(width: int, height: int, rgb: bytes) -> bytes:
    """Costruisce un PDF a pagina singola con l'immagine RGB data.

    Args:
        width: larghezza dell'immagine in pixel.
        height: altezza dell'immagine in pixel.
        rgb: dati pixel grezzi in formato RGB (3 byte per pixel).

    Returns:
        I byte del documento PDF.
    """
    compressed = zlib.compress(rgb)
    content = f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q".encode()
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        (f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 {width} {height}]"
         f"/Resources<</XObject<</Im0 4 0 R>>/ProcSet[/PDF/ImageC]>>"
         f"/Contents 5 0 R>>").encode(),
        (f"<</Type/XObject/Subtype/Image/Width {width}/Height {height}"
         f"/ColorSpace/DeviceRGB/BitsPerComponent 8/Filter/FlateDecode"
         f"/Length {len(compressed)}>>stream\n").encode()
        + compressed + b"\nendstream",
        f"<</Length {len(content)}>>stream\n".encode() + content + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    n = len(objects) + 1
    out += f"xref\n0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<</Size {n}/Root 1 0 R>>\n"
            f"startxref\n{xref_pos}\n%%EOF").encode()
    return bytes(out)


def _save_pdf(img, path: str):
    """Salva un'immagine Wand come PDF (scrittura manuale, senza delegate)."""
    pdf = _build_pdf(img.width, img.height, img.make_blob("RGB"))
    with open(path, "wb") as f:
        f.write(pdf)


def render_report(info: GpuInfo, s: GpuSample, path: str):
    """Genera un report della GPU come PNG o PDF (in base all'estensione)."""
    w, h = 960, 600
    green, dim, bg = Color("#76b900"), Color("#2a3340"), Color("#0f1419")
    white, grey = Color("#ffffff"), Color("#9aa5b1")
    cores = info.cuda_cores or 0
    active_ratio = s.util / 100.0

    with Image(width=w, height=h, background=bg) as img:
        with Drawing() as d:
            d.fill_color = green
            d.rectangle(left=0, top=0, width=w, height=10)

            d.fill_color = white
            d.font_size = 36
            d.text(40, 75, info.name)

            d.font_size = 16
            d.fill_color = grey
            ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            d.text(40, 105, tr("report_title", ts=ts))

            # Numero di core in evidenza
            d.fill_color = green
            d.font_size = 64
            d.text(40, 190, f"{cores:,}".replace(",", ".") if cores else tr("na"))
            d.font_size = 18
            d.fill_color = white
            d.text(40, 220, tr("report_cores_label", src=info.core_source))

            # Dettagli
            cc = (f"{info.compute_cap[0]}.{info.compute_cap[1]}"
                  if info.compute_cap else tr("na"))
            rows = [
                tr("report_cc", v=cc),
                tr("report_sm", v=info.sm_count or tr("na")),
                tr("report_mem", u=s.mem_used_mb, t=info.mem_total_mb),
                tr("report_util", v=s.util),
                tr("report_active", v=int(cores * active_ratio)),
                tr("report_tp", t=s.temp_c, p=s.power_w),
                tr("report_clocks", sm=s.sm_clock, mem=s.mem_clock),
                tr("report_driver", v=info.driver),
            ]
            d.font_size = 18
            d.fill_color = grey
            for i, line in enumerate(rows):
                d.text(40, 270 + i * 30, line)

            # Griglia 10x10: ogni cella = 1% dei core
            cell, gap, ox, oy = 28, 4, 560, 130
            filled = round(s.util)
            for n in range(100):
                r, c = divmod(n, 10)
                d.fill_color = green if n < filled else dim
                d.rectangle(left=ox + c * (cell + gap),
                            top=oy + (9 - r) * (cell + gap),
                            width=cell, height=cell)

            d.fill_color = grey
            d.font_size = 14
            d.text(ox, oy + 10 * (cell + gap) + 22, tr("report_grid_note"))
            d(img)

        if path.lower().endswith(".pdf"):
            _save_pdf(img, path)
        else:
            img.format = "png"
            img.save(filename=path)
    log.info("Report esportato in %s", path)
