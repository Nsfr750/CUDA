"""CUDA Core Monitor - PySide6 + Wand

GUI per il monitoraggio delle GPU NVIDIA:
- conteggio CUDA core (NVML con fallback SM x core/SM)
- stato live: utilizzo, memoria, temperatura, potenza, clock
- grafici storici di utilizzo, memoria, temperatura e potenza
- elenco dei processi che usano la GPU, ventola e P-state
- avvisi configurabili su soglie di temperatura e potenza
- esportazione report PNG/PDF tramite ImageMagick (Wand)
- temi scuro/chiaro, icona tray con notifiche, interfaccia multilingua
- preferenze persistenti tra le sessioni (QSettings)

Dipendenze: vedi requirements.txt (+ ImageMagick nel sistema per Wand).
"""
import csv
import datetime
import sys
from collections import deque

from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap, QPalette
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QProgressBar, QPushButton, QGroupBox, QFileDialog,
    QMessageBox, QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSystemTrayIcon, QMenu,
)

from version import APP_NAME, __version__
from logger import get_logger
import menu
from lang.language_manager import lang_manager
from gpu_backend import GpuManager, GpuInfo, GpuSample
from report import render_report, WAND_OK, MAGICK_VERSION
from widgets import Sparkline

log = get_logger(__name__)


def tr(key: str, **kw) -> str:
    """Scorciatoia per ``lang_manager.tr``."""
    return lang_manager.tr(key, **kw)


def apply_theme(app: QApplication, theme: str):
    """Applica la palette scura o quella di sistema (chiara)."""
    if theme == "dark":
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor("#2b2f33"))
        pal.setColor(QPalette.WindowText, QColor("#e6e9ec"))
        pal.setColor(QPalette.Base, QColor("#1d2124"))
        pal.setColor(QPalette.AlternateBase, QColor("#2b2f33"))
        pal.setColor(QPalette.ToolTipBase, QColor("#1d2124"))
        pal.setColor(QPalette.ToolTipText, QColor("#e6e9ec"))
        pal.setColor(QPalette.Text, QColor("#e6e9ec"))
        pal.setColor(QPalette.Button, QColor("#34393e"))
        pal.setColor(QPalette.ButtonText, QColor("#e6e9ec"))
        pal.setColor(QPalette.BrightText, Qt.red)
        pal.setColor(QPalette.Link, QColor("#76b900"))
        pal.setColor(QPalette.Highlight, QColor("#76b900"))
        pal.setColor(QPalette.HighlightedText, QColor("#0f1419"))
        app.setPalette(pal)
    else:
        app.setPalette(app.style().standardPalette())


def make_icon() -> QIcon:
    """Disegna l'icona dell'app: una griglia di 'core' in stile NVIDIA."""
    pm = QPixmap(64, 64)
    pm.fill(QColor("#0f1419"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    cell, step, off = 9, 12, 4
    for n in range(25):
        r, c = divmod(n, 5)
        p.fillRect(off + c * step, off + r * step, cell, cell,
                   QColor("#76b900") if n < 16 else QColor("#2a3340"))
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1250, 600)
        self.backend = GpuManager()
        self.last_sample = GpuSample()
        self._alerts_on = {"temp": False, "power": False}
        self.settings = QSettings("Tuxxle", "CudaCoreMonitor")
        self.history = deque(maxlen=3600)  # storico campioni per l'export CSV
        self._tray_hint_shown = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # --- Selezione GPU, intervallo, tema e lingua ----------------------
        top = QHBoxLayout()
        self.lbl_gpu = QLabel()
        top.addWidget(self.lbl_gpu)
        self.combo = QComboBox()
        for i in self.backend.infos:
            self.combo.addItem(f"{i.vendor} {i.index}: {i.name}", i.index)
        self.combo.currentIndexChanged.connect(self.on_gpu_changed)
        top.addWidget(self.combo, 1)

        self.lbl_refresh = QLabel()
        top.addWidget(self.lbl_refresh)
        self.interval = QSpinBox()
        self.interval.setRange(100, 5000)
        self.interval.setSingleStep(100)
        self.interval.setValue(1000)
        self.interval.valueChanged.connect(lambda v: self.timer.setInterval(v))
        top.addWidget(self.interval)
        root.addLayout(top)

        opts = QHBoxLayout()
        self.lbl_theme = QLabel()
        opts.addWidget(self.lbl_theme)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("", "dark")
        self.theme_combo.addItem("", "light")
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        opts.addWidget(self.theme_combo)
        self.lbl_lang = QLabel()
        opts.addWidget(self.lbl_lang)
        self.lang_combo = QComboBox()
        for code, name in lang_manager.languages().items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)
        opts.addWidget(self.lang_combo)
        self.chk_tray = QCheckBox()
        self.chk_tray.setChecked(False)
        opts.addWidget(self.chk_tray)
        opts.addStretch(1)
        root.addLayout(opts)

        # Layout a due colonne: comandi/info a sinistra, grafici e processi
        # a destra (tutto visibile anche su display bassi, es. 1900x600)
        cols = QHBoxLayout()
        cols.setSpacing(8)
        left = QVBoxLayout()
        right = QVBoxLayout()
        cols.addLayout(left)
        cols.addLayout(right, 1)
        root.addLayout(cols, 1)

        # --- Numero core ---------------------------------------------------
        self.lbl_cores = QLabel("--")
        f = self.font()
        f.setPointSize(28)
        f.setBold(True)
        self.lbl_cores.setFont(f)
        self.lbl_cores.setAlignment(Qt.AlignCenter)
        self.lbl_cores.setStyleSheet("color:#76b900;")
        self.lbl_source = QLabel("")
        self.lbl_source.setAlignment(Qt.AlignCenter)
        self.lbl_cores_title = QLabel(alignment=Qt.AlignCenter)
        left.addWidget(self.lbl_cores)
        left.addWidget(self.lbl_cores_title)
        left.addWidget(self.lbl_source)

        # --- Dettagli statici ----------------------------------------------
        self.box_details = QGroupBox()
        grid = QGridLayout(self.box_details)
        self.vals = {}
        self.detail_labels = []
        for r, key in enumerate(["compute_cap", "sm", "total_mem", "driver"]):
            lbl = QLabel()
            grid.addWidget(lbl, r // 2, (r % 2) * 2)
            v = QLabel("--")
            v.setStyleSheet("font-weight:600;")
            grid.addWidget(v, r // 2, (r % 2) * 2 + 1)
            self.detail_labels.append((lbl, key))
            self.vals[key] = v
        left.addWidget(self.box_details)

        # --- Stato live ----------------------------------------------------
        self.box_live = QGroupBox()
        lg = QGridLayout(self.box_live)
        self.lbl_usage = QLabel()
        self.lbl_memory = QLabel()
        self.bar_util = QProgressBar()
        self.bar_mem = QProgressBar()
        for b in (self.bar_util, self.bar_mem):
            b.setRange(0, 100)
        lg.addWidget(self.lbl_usage, 0, 0)
        lg.addWidget(self.bar_util, 0, 1)
        lg.addWidget(self.lbl_memory, 1, 0)
        lg.addWidget(self.bar_mem, 1, 1)
        self.lbl_active = QLabel()
        self.lbl_misc = QLabel("--")
        self.lbl_fan = QLabel("--")
        lg.addWidget(self.lbl_active, 2, 0, 1, 2)
        lg.addWidget(self.lbl_misc, 3, 0, 1, 2)
        lg.addWidget(self.lbl_fan, 4, 0, 1, 2)
        left.addWidget(self.box_live)

        # --- Grafici storici -----------------------------------------------
        self.box_charts = QGroupBox()
        cg = QGridLayout(self.box_charts)
        self.spark_util = Sparkline(max_value=100)
        self.spark_mem = Sparkline(max_value=100, line="#9b59b6")
        self.spark_temp = Sparkline(max_value=110, line="#e67e22")
        self.spark_power = Sparkline(max_value=None, line="#3498db")
        self.chart_labels = []
        for r, (key, spark) in enumerate([
                ("chart_usage", self.spark_util),
                ("chart_mem", self.spark_mem),
                ("chart_temp", self.spark_temp),
                ("chart_power", self.spark_power)]):
            lbl = QLabel()
            cg.addWidget(lbl, r * 2, 0)
            cg.addWidget(spark, r * 2 + 1, 0)
            self.chart_labels.append((lbl, key))
        right.addWidget(self.box_charts)

        # --- Avvisi su soglie ----------------------------------------------
        self.box_alerts = QGroupBox()
        ag = QGridLayout(self.box_alerts)
        self.chk_alerts = QCheckBox()
        self.chk_alerts.setChecked(True)
        ag.addWidget(self.chk_alerts, 0, 0, 1, 2)
        self.lbl_temp_thr = QLabel()
        self.spin_temp = QSpinBox()
        self.spin_temp.setRange(40, 115)
        self.spin_temp.setValue(85)
        self.lbl_power_thr = QLabel()
        self.spin_power = QSpinBox()
        self.spin_power.setRange(50, 1500)
        self.spin_power.setSingleStep(10)
        self.spin_power.setValue(300)
        ag.addWidget(self.lbl_temp_thr, 1, 0)
        ag.addWidget(self.spin_temp, 1, 1)
        ag.addWidget(self.lbl_power_thr, 2, 0)
        ag.addWidget(self.spin_power, 2, 1)
        self.lbl_alert = QLabel("")
        self.lbl_alert.setStyleSheet("color:#e74c3c;font-weight:bold;")
        ag.addWidget(self.lbl_alert, 3, 0, 1, 2)
        left.addWidget(self.box_alerts)
        left.addStretch(1)

        # --- Processi che usano la GPU -------------------------------------
        self.box_proc = QGroupBox()
        pg = QVBoxLayout(self.box_proc)
        self.table = QTableWidget(0, 3)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.table.setMaximumHeight(130)
        pg.addWidget(self.table)
        right.addWidget(self.box_proc)

        # --- Export + chiusura ----------------------------------------------
        bottom = QHBoxLayout()
        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self.export_report)
        self.btn_export.setEnabled(WAND_OK and bool(self.backend.infos))
        bottom.addWidget(self.btn_export)
        self.btn_csv = QPushButton()
        self.btn_csv.clicked.connect(self.export_csv)
        self.btn_csv.setEnabled(bool(self.backend.infos))
        bottom.addWidget(self.btn_csv)
        bottom.addStretch(1)
        self.lbl_im = QLabel()
        bottom.addWidget(self.lbl_im)
        self.btn_close = QPushButton()
        self.btn_close.setStyleSheet(
            "background-color:#c0392b;color:white;font-weight:bold;"
            "padding:6px 18px;")
        self.btn_close.clicked.connect(self.close)
        bottom.addWidget(self.btn_close)
        root.addLayout(bottom)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)

        # --- Icona tray -----------------------------------------------------
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(make_icon(), self)
            menu = QMenu()
            self.act_show = menu.addAction("")
            self.act_show.triggered.connect(self._show_window)
            menu.addSeparator()
            self.act_quit = menu.addAction("")
            self.act_quit.triggered.connect(QApplication.instance().quit)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self._on_tray_activated)
            self.tray.show()
        self.chk_tray.setEnabled(self.tray is not None)

        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._cleanup)

        self._load_settings()
        lang_manager.subscribe(lambda _lang: self.retranslate())
        self.retranslate()

        if self.backend.error or not self.backend.infos:
            self.lbl_cores.setText(tr("na"))
            self.lbl_source.setText(self.backend.error or tr("no_gpu"))
        else:
            self.on_gpu_changed()
            self.timer.start(self.interval.value())

    # -- helpers -----------------------------------------------------------
    def current(self) -> "GpuInfo | None":
        i = self.combo.currentIndex()
        return self.backend.infos[i] if 0 <= i < len(self.backend.infos) else None

    def retranslate(self):
        """Aggiorna tutte le stringhe UI nella lingua corrente."""
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.lbl_gpu.setText(tr("gpu"))
        self.lbl_refresh.setText(tr("refresh_ms"))
        self.lbl_theme.setText(tr("theme"))
        self.lbl_lang.setText(tr("language"))
        self.theme_combo.blockSignals(True)
        self.theme_combo.setItemText(0, tr("theme_dark"))
        self.theme_combo.setItemText(1, tr("theme_light"))
        self.theme_combo.blockSignals(False)
        self.lang_combo.blockSignals(True)
        codes = list(lang_manager.languages())
        if lang_manager.language in codes:
            self.lang_combo.setCurrentIndex(codes.index(lang_manager.language))
        self.lang_combo.blockSignals(False)
        self.lbl_cores_title.setText(tr("total_cuda_cores"))
        self.box_details.setTitle(tr("details"))
        for lbl, key in self.detail_labels:
            lbl.setText(tr(key) + ":")
        self.box_live.setTitle(tr("live"))
        self.lbl_usage.setText(tr("gpu_usage"))
        self.lbl_memory.setText(tr("memory"))
        self.box_charts.setTitle(tr("charts"))
        for lbl, key in self.chart_labels:
            lbl.setText(tr(key))
        self.box_alerts.setTitle(tr("alerts"))
        self.chk_alerts.setText(tr("enable_alerts"))
        self.lbl_temp_thr.setText(tr("temp_threshold"))
        self.lbl_power_thr.setText(tr("power_threshold"))
        self.btn_export.setText(tr("export"))
        self.btn_csv.setText(tr("export_csv"))
        self.chk_tray.setText(tr("minimize_tray"))
        self.btn_close.setText(tr("close"))
        self.table.setHorizontalHeaderLabels(
            [tr("col_pid"), tr("col_process"), tr("col_mem")])
        if self.tray:
            self.act_show.setText(tr("tray_show"))
            self.act_quit.setText(tr("tray_quit"))
            self.tray.setToolTip(f"{APP_NAME} v{__version__}")
        im_ver = MAGICK_VERSION.split(" ")[1] if WAND_OK else tr("na")
        self.lbl_im.setText(tr("im_version", v=im_ver))
        menu.build_menu(self)
        if self.backend.error or not self.backend.infos:
            self.lbl_source.setText(self.backend.error or tr("no_gpu"))
        else:
            self.on_gpu_changed()

    # -- slot ----------------------------------------------------------------
    def on_gpu_changed(self):
        info = self.current()
        if not info:
            return
        self.lbl_cores.setText(f"{info.cuda_cores:,}".replace(",", ".")
                               if info.cuda_cores else tr("na"))
        self.lbl_source.setText(tr("source", src=info.core_source))
        cc = (f"{info.compute_cap[0]}.{info.compute_cap[1]}"
              if info.compute_cap else tr("na"))
        self.vals["compute_cap"].setText(cc)
        self.vals["sm"].setText(str(info.sm_count or tr("na")))
        self.vals["total_mem"].setText(f"{info.mem_total_mb} MB")
        self.vals["driver"].setText(info.driver)
        self.spark_power.max_value = info.power_limit_w  # None = autoscala
        for s in self._sparks():
            s.clear()
        self.history.clear()
        self.refresh()

    def _sparks(self):
        return (self.spark_util, self.spark_mem,
                self.spark_temp, self.spark_power)

    def on_theme_changed(self, index: int):
        theme = self.theme_combo.itemData(index)
        apply_theme(QApplication.instance(), theme)
        for s in self._sparks():
            s.set_theme(theme)
        log.info("Tema applicato: %s", theme)

    def on_lang_changed(self, index: int):
        lang_manager.set_language(self.lang_combo.itemData(index))

    def refresh(self):
        info = self.current()
        if not info:
            return
        s = self.backend.sample(info.index)
        self.last_sample = s
        self.bar_util.setValue(s.util)
        self.bar_util.setFormat(f"{s.util}%")
        mem_pct = (int(100 * s.mem_used_mb / info.mem_total_mb)
                   if info.mem_total_mb else 0)
        self.bar_mem.setValue(mem_pct)
        self.bar_mem.setFormat(f"{s.mem_used_mb} / {info.mem_total_mb} MB")
        if info.cuda_cores:
            self.lbl_active.setText(tr(
                "active_cores",
                active=f"{int(info.cuda_cores * s.util / 100):,}".replace(",", "."),
                total=f"{info.cuda_cores:,}".replace(",", ".")))
        else:
            self.lbl_active.setText(tr("active_cores_na"))
        self.lbl_misc.setText(tr("misc_status", t=s.temp_c, p=s.power_w,
                                 sm=s.sm_clock, mem=s.mem_clock))
        self.lbl_fan.setText(tr("fan_status", fan=s.fan_pct,
                                p=s.pstate or tr("na")))
        self.spark_util.push(s.util)
        self.spark_mem.push(mem_pct)
        self.spark_temp.push(s.temp_c)
        self.spark_power.push(s.power_w)
        self.history.append((
            datetime.datetime.now().isoformat(timespec="seconds"),
            s.util, mem_pct, s.mem_used_mb, s.temp_c, s.power_w,
            s.sm_clock, s.mem_clock, s.fan_pct))
        self._update_processes(info)
        self._check_alerts(s)

    def _update_processes(self, info: GpuInfo):
        """Aggiorna la tabella dei processi che usano la GPU."""
        procs = self.backend.processes(info.index)
        self.table.setRowCount(len(procs))
        for r, p in enumerate(procs):
            for c, val in enumerate(
                    (str(p["pid"]), p["name"] or tr("na"), str(p["mem_mb"]))):
                item = self.table.item(r, c)
                if item is None:
                    item = QTableWidgetItem()
                    self.table.setItem(r, c, item)
                item.setText(val)
        self.box_proc.setTitle(f"{tr('processes')} ({len(procs)})")

    def _check_alerts(self, s: GpuSample):
        """Mostra/registra gli avvisi quando le soglie sono superate."""
        msgs = []
        if self.chk_alerts.isChecked():
            if s.temp_c > self.spin_temp.value():
                msgs.append(("temp", tr("alert_temp", t=s.temp_c,
                                        thr=self.spin_temp.value())))
            if s.power_w > self.spin_power.value():
                msgs.append(("power", tr("alert_power", p=s.power_w,
                                         thr=self.spin_power.value())))
        self.lbl_alert.setText("\n".join(m for _, m in msgs))
        for kind, msg in msgs:
            if not self._alerts_on[kind]:
                log.warning("Soglia %s superata", kind)
                if self.tray:
                    self.tray.showMessage(tr("alert_notify_title"), msg,
                                          QSystemTrayIcon.Warning, 4000)
            self._alerts_on[kind] = True
        for kind in ("temp", "power"):
            if not any(k == kind for k, _ in msgs):
                self._alerts_on[kind] = False

    def export_csv(self):
        """Esporta lo storico dei campioni in un file CSV (separatore ';')."""
        info = self.current()
        if not info:
            return
        default = f"cuda_samples_gpu{info.index}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("save_report"), default, "CSV (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["timestamp", "gpu", "util_pct", "mem_pct",
                            "mem_used_mb", "temp_c", "power_w",
                            "sm_clock_mhz", "mem_clock_mhz", "fan_pct"])
                for row in self.history:
                    w.writerow([row[0], info.name, *row[1:]])
            log.info("Storico CSV esportato in %s (%d campioni)",
                     path, len(self.history))
            QMessageBox.information(self, tr("report_saved"),
                                    tr("report_path", path=path))
        except Exception as e:
            log.exception("Esportazione CSV fallita")
            QMessageBox.critical(self, tr("wand_error"), str(e))

    def export_report(self):
        info = self.current()
        if not info:
            return
        default = f"cuda_report_gpu{info.index}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("save_report"), default, tr("filter_png_pdf"))
        if not path:
            return
        if "." not in path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]:
            path += ".png"
        try:
            render_report(info, self.last_sample, path)
            QMessageBox.information(self, tr("report_saved"),
                                    tr("report_path", path=path))
        except Exception as e:
            log.exception("Esportazione report fallita")
            QMessageBox.critical(self, tr("wand_error"), str(e))

    # -- preferenze persistenti ---------------------------------------------
    def _load_settings(self):
        s = self.settings
        theme = s.value("theme", "dark")
        self.theme_combo.setCurrentIndex(1 if theme == "light" else 0)
        lang_manager.set_language(s.value("language", "it"))
        self.interval.setValue(int(s.value("interval", 1000)))
        self.spin_temp.setValue(int(s.value("temp_threshold", 85)))
        self.spin_power.setValue(int(s.value("power_threshold", 300)))
        self.chk_alerts.setChecked(
            s.value("alerts_enabled", "true") != "false")
        self.chk_tray.setChecked(
            s.value("minimize_to_tray", "false") == "true")

    def _save_settings(self):
        s = self.settings
        s.setValue("theme", self.theme_combo.currentData())
        s.setValue("language", lang_manager.language)
        s.setValue("interval", self.interval.value())
        s.setValue("temp_threshold", self.spin_temp.value())
        s.setValue("power_threshold", self.spin_power.value())
        s.setValue("alerts_enabled",
                   "true" if self.chk_alerts.isChecked() else "false")
        s.setValue("minimize_to_tray",
                   "true" if self.chk_tray.isChecked() else "false")

    # -- tray -----------------------------------------------------------------
    def _show_window(self):
        self.showNormal()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window()

    def closeEvent(self, ev):
        if self.chk_tray.isChecked() and self.tray:
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.showMessage(APP_NAME, tr("tray_hint"),
                                      QSystemTrayIcon.Information, 3000)
            ev.ignore()
            return
        super().closeEvent(ev)

    def _cleanup(self):
        """Eseguito su ``aboutToQuit``: salva preferenze e rilascia NVML."""
        self.timer.stop()
        self._save_settings()
        self.backend.shutdown()
        log.info("Applicazione chiusa")


def main():
    log.info("Avvio %s v%s", APP_NAME, __version__)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme(app, "dark")
    app.setWindowIcon(make_icon())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
