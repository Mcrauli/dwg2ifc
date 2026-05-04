"""Non-modal banner that appears at the top of the main window when a
newer dxf2ifc release is available on GitHub.

The banner is wired by :class:`MainWindow` to:
    1. A background ``UpdateChecker`` worker that polls
       :func:`dxf2ifc.core.updater.check_for_update` once on startup.
    2. A click handler that downloads the new exe with progress and
       hands it to :func:`schedule_replace_and_restart` before
       quitting the app.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from dxf2ifc.core.updater import (
    DEFAULT_REPO,
    UpdateInfo,
    check_for_update,
    download_asset,
    is_running_bundled,
    schedule_replace_and_restart,
)


class UpdateChecker(QtCore.QObject):
    """Runs :func:`check_for_update` on a worker thread and emits the
    result back to the GUI thread.

    Silent on failure (network down, rate-limit, malformed payload):
    a no-update outcome and a check-error are both reported as ``None``.
    """

    result = QtCore.Signal(object)  # UpdateInfo | None

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)

    def start(self, *, repo: str = DEFAULT_REPO) -> None:
        runnable = _CheckRunnable(self, repo=repo)
        QtCore.QThreadPool.globalInstance().start(runnable)


class _CheckRunnable(QtCore.QRunnable):
    def __init__(self, owner: UpdateChecker, *, repo: str) -> None:
        super().__init__()
        self._owner = owner
        self._repo = repo

    def run(self) -> None:  # type: ignore[override]
        try:
            info = check_for_update(repo=self._repo)
        except Exception:  # noqa: BLE001 — never propagate to event loop
            info = None
        self._owner.result.emit(info)


class UpdateBanner(QtWidgets.QFrame):
    """Amber call-to-action strip that appears when an update is found."""

    update_requested = QtCore.Signal(object)  # UpdateInfo

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("update_banner")
        self.setProperty("role", "update_banner")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        self._label = QtWidgets.QLabel("")
        self._label.setProperty("role", "update_banner_text")
        self._label.setWordWrap(True)
        layout.addWidget(self._label, stretch=1)

        self._button = QtWidgets.QPushButton("Päivitä nyt")
        self._button.setProperty("primary", True)
        self._button.clicked.connect(self._on_clicked)
        layout.addWidget(self._button)

        self._dismiss = QtWidgets.QPushButton("Myöhemmin")
        self._dismiss.setProperty("secondary", True)
        self._dismiss.clicked.connect(self.hide)
        layout.addWidget(self._dismiss)

        self._info: UpdateInfo | None = None
        self.hide()

    def show_for(self, info: UpdateInfo) -> None:
        self._info = info
        size_mb = info.download_size / (1024 * 1024) if info.download_size else 0
        size_str = f" ({size_mb:.0f} MB)" if size_mb else ""
        self._label.setText(
            f"Uusi versio <b>{info.tag}</b> saatavilla{size_str}. "
            f"Klikkaa 'Päivitä nyt' niin lataus ja vaihto hoituu automaattisesti."
        )
        self.show()

    def _on_clicked(self) -> None:
        if self._info is not None:
            self.update_requested.emit(self._info)


class UpdateProgressDialog(QtWidgets.QProgressDialog):
    """Modal progress dialog while the new exe is downloading. Owns the
    download worker and emits :pyattr:`finished_ok` with the temp file
    path when the bytes are on disk.
    """

    finished_ok = QtCore.Signal(Path)
    failed = QtCore.Signal(str)

    def __init__(
        self,
        info: UpdateInfo,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(
            f"Ladataan {info.tag}…",
            "Peruuta",
            0,
            100,
            parent,
        )
        self.setWindowTitle("dxf2ifc — päivitys")
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self._info = info
        self._cancelled = False
        self.canceled.connect(self._on_cancel)

    def _on_cancel(self) -> None:
        self._cancelled = True

    def start(self, target_path: Path) -> None:
        worker = _DownloadRunnable(self, target_path=target_path)
        QtCore.QThreadPool.globalInstance().start(worker)

    def report_progress(self, downloaded: int, total: int) -> None:
        if total <= 0:
            return
        percent = int(downloaded * 100 / total)
        # Marshal to GUI thread — Qt requires UI updates on the main thread.
        QtCore.QMetaObject.invokeMethod(
            self,
            "setValue",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(int, percent),
        )

    def is_cancelled(self) -> bool:
        return self._cancelled


class _DownloadRunnable(QtCore.QRunnable):
    def __init__(self, owner: UpdateProgressDialog, *, target_path: Path) -> None:
        super().__init__()
        self._owner = owner
        self._target_path = target_path

    def run(self) -> None:  # type: ignore[override]
        info = self._owner._info  # noqa: SLF001 — internal API of owner

        def progress_cb(downloaded: int, total: int) -> None:
            if self._owner.is_cancelled():
                # urlopen has no clean cancel; raising aborts the loop.
                raise RuntimeError("cancelled")
            self._owner.report_progress(downloaded, total)

        try:
            download_asset(
                info.download_url,
                self._target_path,
                progress_cb=progress_cb,
            )
        except RuntimeError:
            # User cancellation — leave a partial file behind for cleanup;
            # the .part suffix means it cannot be confused with a real exe.
            return
        except Exception as exc:  # noqa: BLE001
            self._owner.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self._owner.finished_ok.emit(self._target_path)


def perform_update(
    info: UpdateInfo,
    parent: QtWidgets.QWidget | None = None,
) -> None:
    """Download + swap + restart. Quits the running app on success."""
    if not is_running_bundled():
        QtWidgets.QMessageBox.information(
            parent,
            "Päivitys",
            "Itsepäivitys on käytettävissä vain bundlatulle .exe-versiolle. "
            "Lataa uusin versio manuaalisesti:\n" + info.release_url,
        )
        return

    target = Path(tempfile.gettempdir()) / Path(info.download_url).name
    dialog = UpdateProgressDialog(info, parent)

    def on_ok(downloaded_path: Path) -> None:
        dialog.close()
        try:
            schedule_replace_and_restart(downloaded_path)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(
                parent,
                "Päivitys epäonnistui",
                f"Vaihto ei onnistunut: {type(exc).__name__}: {exc}\n"
                f"Lataa manuaalisesti: {info.release_url}",
            )
            return
        QtWidgets.QApplication.instance().quit()

    def on_fail(message: str) -> None:
        dialog.close()
        QtWidgets.QMessageBox.critical(
            parent,
            "Päivitys epäonnistui",
            f"Lataus ei onnistunut: {message}\n"
            f"Lataa manuaalisesti: {info.release_url}",
        )

    dialog.finished_ok.connect(on_ok)
    dialog.failed.connect(on_fail)
    dialog.start(target)
    dialog.exec()
