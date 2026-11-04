"""Проверка и упаковка проекта для сдачи: python -m report.package.

Скрипт запускает автотесты и, если они прошли, собирает архив
submission/physical-pendulum-m5.zip. В архив входят исходный код пакета,
тесты, PDF-отчёт со скриптом его сборки, README.md и файлы зависимостей.
Вопросы к защите и настройки проверок стиля в архив не входят. Перед
запуском нужно собрать отчёт командой python -m report.build_report.
"""

from pathlib import Path
import subprocess
import sys
import zipfile


# Корень проекта, отчёт и архив для сдачи.
ROOT: Path = Path(__file__).resolve().parents[1]
REPORT_PDF: Path = ROOT / "report" / "report.pdf"
ARCHIVE: Path = ROOT / "submission" / "physical-pendulum-m5.zip"

# Имя корневой папки внутри архива.
ARCHIVE_ROOT: str = "physical-pendulum-m5"

# Шаблоны путей (относительно корня проекта) для файлов архива.
INCLUDED_PATTERNS: tuple[str, ...] = (
    "physical_pendulum/*.py",
    "tests/*.py",
    "report/__init__.py",
    "report/build_report.py",
    "report/report.pdf",
    "README.md",
    "requirements.txt",
    "requirements-report.txt",
)

# Сигнатура начала PDF-файла.
PDF_SIGNATURE: bytes = b"%PDF-"

# Байтов в мегабайте.
BYTES_PER_MEGABYTE: int = 1024 * 1024


def check_report(path: Path) -> None:
    """Убедиться, что PDF-отчёт собран и файл действительно является PDF."""
    if not path.is_file():
        raise SystemExit("Нет отчёта: сначала выполните python -m report.build_report")
    with path.open("rb") as report:
        if report.read(len(PDF_SIGNATURE)) != PDF_SIGNATURE:
            raise SystemExit(f"Файл {path.name} не является PDF")


def run_tests() -> bool:
    """Запустить автотесты; True — тесты прошли."""
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def project_files() -> list[Path]:
    """Перечислить файлы, которые входят в архив, по алфавиту."""
    files: set[Path] = set()
    for pattern in INCLUDED_PATTERNS:
        matches = [path for path in ROOT.glob(pattern) if path.is_file()]
        if not matches:
            raise SystemExit(f"Нет файлов для архива по шаблону {pattern}")
        files.update(matches)
    return sorted(files)


def write_archive(path: Path, files: list[Path]) -> int:
    """Записать файлы в zip-архив и вернуть их число."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, Path(ARCHIVE_ROOT) / file.relative_to(ROOT))
            count += 1
    return count


def verify_archive(path: Path) -> None:
    """Проверить контрольные суммы всех файлов архива."""
    with zipfile.ZipFile(path) as archive:
        damaged = archive.testzip()
    if damaged is not None:
        raise SystemExit(f"Ошибка контрольной суммы в архиве: {damaged}")


def main() -> None:
    """Проверить отчёт, запустить тесты и собрать архив для сдачи."""
    check_report(REPORT_PDF)
    if not run_tests():
        raise SystemExit("Тесты не пройдены; архив не создаётся")
    count = write_archive(ARCHIVE, project_files())
    verify_archive(ARCHIVE)
    size = ARCHIVE.stat().st_size / BYTES_PER_MEGABYTE
    print(f"Архив: {ARCHIVE.relative_to(ROOT)} ({count} файлов, {size:.2f} МБ)")


if __name__ == "__main__":
    main()
