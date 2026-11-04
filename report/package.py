"""Тестирование и сборка сдаваемого архива без окружения и служебных файлов."""
from pathlib import Path
import subprocess
import sys
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]


def main():
    pdf=ROOT/'report/report.pdf'
    if not pdf.is_file():
        raise SystemExit('Сначала выполните python -m report.build_report')
    if len(PdfReader(pdf).pages)<5:
        raise SystemExit('Отчёт неполный')
    result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],
                          cwd=ROOT,capture_output=True,text=True)
    log=result.stdout+result.stderr
    (ROOT/'report/test-results.txt').write_text(log,encoding='utf-8')
    print(log)
    if result.returncode:
        raise SystemExit('Тесты не пройдены; архив не создаётся')
    output=ROOT/'submission/physical-pendulum-m5.zip'
    output.parent.mkdir(exist_ok=True)
    selected=[]
    for name in ('physical_pendulum','tests','docs','report'):
        selected += [p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.suffix=='.pyc']
    selected += [ROOT/name for name in ('README.md','requirements.txt','requirements-report.txt','requirements-lock.txt','.gitignore') if (ROOT/name).exists()]
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(selected):
            archive.write(path,Path('physical-pendulum-m5')/path.relative_to(ROOT))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Ошибка контрольной суммы архива')
    print(f'Архив: {output} ({output.stat().st_size/1024/1024:.2f} МБ)')


if __name__=='__main__': main()
