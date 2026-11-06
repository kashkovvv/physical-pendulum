"""Сборка PDF-отчёта: python -m report.build_report (из корня проекта).

Скрипт выполняет все расчёты, сохраняет рисунки в report/figures и собирает
report/report.pdf. Все числа в тексте берутся из результатов расчёта.
"""

from collections.abc import Sequence
import re
from io import BytesIO
from math import degrees, log10, radians, sin
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import font_manager, mathtext  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_RIGHT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen.canvas import Canvas  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import BaseDocTemplate  # noqa: E402

from physical_pendulum.config import (  # noqa: E402
    DEFAULT_INTEGRATION,
    DEFAULT_PENDULUM,
    FIGURE_DPI,
    FREE_DURATION_S,
    PERIOD_DURATION_S,
)
from physical_pendulum.pendulum import (  # noqa: E402
    ExperimentResults,
    fit_decay_rate_1_s,
    run_experiments,
)
from physical_pendulum.plots import create_pendulum_figures  # noqa: E402
from physical_pendulum.theory import (  # noqa: E402
    damped_period_s,
    exact_period_s,
    series_period_s,
    small_angle_period_s,
)


# Папки и файлы отчёта.
REPORT_DIR: Path = Path(__file__).resolve().parent
FIGURES_DIR: Path = REPORT_DIR / "figures"
PDF_PATH: Path = REPORT_DIR / "report.pdf"

# Углы, для которых в отчёте показано отношение sinθ/θ, град.
SINE_RATIO_ANGLES_DEG: tuple[float, ...] = (5.0, 60.0, 90.0)

# Типографские знаки минуса и умножения для текста PDF.
MINUS: str = "\u2212"
TIMES: str = "\u00d7"

# Дефис, который в тексте означает минус: после пробела, скобки, знака
# равенства, черты модуля или начала степени и перед числом или буквой.
MINUS_PATTERN: re.Pattern[str] = re.compile(r"(?<=[\s(=|>])-(?=[\s\w(])")

# Поля страницы и ширина текста, пт.
MARGIN: float = 50.0
FRAME_WIDTH: float = A4[0] - 2.0 * MARGIN

# Ширина колонки с номером формулы, пт.
NUMBER_WIDTH: float = 36.0

# Размер шрифта формул, пт, и разрешение их отрисовки, точек на дюйм.
EQUATION_SIZE: float = 11.0
EQUATION_DPI: int = 300

# Шрифт с кириллицей и греческими буквами.
FONT: str = "DejaVuSans"
FONT_BOLD: str = "DejaVuSans-Bold"
FONT_ITALIC: str = "DejaVuSans-Oblique"
FONT_BOLD_ITALIC: str = "DejaVuSans-BoldOblique"

ACCENT = colors.HexColor("#163c56")
MUTED = colors.HexColor("#5d7080")
BODY = ParagraphStyle("Body", fontName=FONT, fontSize=10, leading=14, spaceAfter=4)
HEADING = ParagraphStyle(
    "Heading", fontName=FONT_BOLD, fontSize=13.5, leading=18, spaceBefore=10,
    spaceAfter=6, textColor=ACCENT, keepWithNext=1,
)
TITLE = ParagraphStyle(
    "Title", fontName=FONT_BOLD, fontSize=30, leading=38, spaceAfter=18,
    textColor=ACCENT,
)
SUBTITLE = ParagraphStyle("Subtitle", fontName=FONT, fontSize=13, leading=19)
CAPTION = ParagraphStyle(
    "Caption", fontName=FONT, fontSize=8.5, leading=11, spaceBefore=2,
    spaceAfter=10, alignment=TA_CENTER, textColor=MUTED,
)
CELL = ParagraphStyle("Cell", fontName=FONT, fontSize=8.5, leading=11)
CELL_HEADER = ParagraphStyle("CellHeader", parent=CELL, fontName=FONT_BOLD)
LEAD = ParagraphStyle("Lead", parent=BODY, keepWithNext=1)
NUMBER = ParagraphStyle("Number", parent=BODY, alignment=TA_RIGHT, spaceAfter=0)
SOURCE = ParagraphStyle(
    "Source", parent=BODY, fontSize=9, leading=12.5, leftIndent=18,
    firstLineIndent=-18,
)

SOURCES: tuple[str, ...] = (
    "Попов П. В. Цифровизация физических процессов: программа курса и задания "
    "проектов (ВШПИ_прог_26-27). Проект М5 «Физический маятник», с. 12-13.",
    "OpenStax. University Physics, Volume 1. § 15.4 Pendulums. "
    "https://openstax.org/books/university-physics-volume-1/pages/15-4-pendulums",
    "OpenStax. University Physics, Volume 1. § 15.5 Damped Oscillations. "
    "https://openstax.org/books/university-physics-volume-1/pages/"
    "15-5-damped-oscillations",
    "SciPy. scipy.integrate.solve_ivp. https://docs.scipy.org/doc/scipy/"
    "reference/generated/scipy.integrate.solve_ivp.html",
    "SciPy. scipy.special.ellipk. https://docs.scipy.org/doc/scipy/"
    "reference/generated/scipy.special.ellipk.html",
)

# Номера формул по меткам; заполняются по мере сборки текста.
EQUATION_NUMBERS: dict[str, int] = {}

# Сокращения для нижних индексов в формулах mathtext.
ST: str = r"_{\mathrm{ст}}"
GR: str = r"_{\mathrm{гр}}"


def number(value: float, digits: int) -> str:
    """Число с десятичной запятой и типографским минусом."""
    return f"{value:.{digits}f}".replace(".", ",").replace("-", MINUS)


def scientific(value: float, digits: int = 1) -> str:
    """Число вида 1,2·10⁻¹⁴ в разметке Paragraph."""
    mantissa, exponent = f"{value:.{digits}e}".split("e")
    power = str(int(exponent)).replace("-", MINUS)
    return f"{number(float(mantissa), digits)}·10<super>{power}</super>"


def power(value: float) -> str:
    """Степень десяти вида 10⁻¹⁰ в разметке Paragraph."""
    exponent = str(round(log10(value))).replace("-", MINUS)
    return f"10<super>{exponent}</super>"


def tex_number(value: float, digits: int) -> str:
    """Число с десятичной запятой для формулы mathtext."""
    return f"{value:.{digits}f}".replace(".", "{,}")


def tex_scientific(value: float, digits: int = 1) -> str:
    """Число вида 1,2 x 10⁻¹⁴ для формулы mathtext."""
    mantissa, exponent = f"{value:.{digits}e}".split("e")
    return (f"{tex_number(float(mantissa), digits)}"
            rf"\times 10^{{{int(exponent)}}}")


def unit(text: str) -> str:
    """Единица измерения прямым шрифтом после числа в формуле."""
    return r"\ \mathrm{" + text + "}"


def typeset(text: str) -> str:
    """Заменить ASCII-минус в тексте на типографский знак."""
    return MINUS_PATTERN.sub(MINUS, text)


def paragraph(text: str) -> Paragraph:
    """Абзац; абзац без точки в конце держится вместе с формулой после него."""
    style = BODY if text.rstrip().endswith((".", ")")) else LEAD
    return Paragraph(typeset(text), style)


def heading(text: str) -> Paragraph:
    return Paragraph(text, HEADING)


def period_at(results: ExperimentResults, amplitude_deg: float) -> float:
    """Численный период для амплитуды из таблицы расчётов, с."""
    index = results.period_amplitudes_deg.index(amplitude_deg)
    return results.periods_s[index]


def ref(label: str) -> str:
    """Ссылка на формулу вида (5)."""
    return f"({EQUATION_NUMBERS[label]})"


def equation(tex: str, label: str | None = None) -> Flowable:
    """Выключная формула mathtext; с меткой получает номер справа."""
    buffer = BytesIO()
    mathtext.math_to_image(
        f"${tex}$", buffer,
        prop=FontProperties(family="DejaVu Sans", size=EQUATION_SIZE),
        dpi=EQUATION_DPI, format="png",
    )
    buffer.seek(0)
    width, height = ImageReader(buffer).getSize()
    buffer.seek(0)
    scale = 72.0 / EQUATION_DPI
    available = FRAME_WIDTH - 2.0 * NUMBER_WIDTH
    if width * scale > available:
        raise ValueError(f"Формула шире строки: {tex}")
    image = Image(buffer, width=width * scale, height=height * scale)
    if label is None:
        image.spaceBefore, image.spaceAfter = 3, 7
        return image
    if label in EQUATION_NUMBERS:
        raise ValueError(f"Метка формулы повторяется: {label}")
    EQUATION_NUMBERS[label] = len(EQUATION_NUMBERS) + 1
    body = Table(
        [[Spacer(1, 1), image, Paragraph(ref(label), NUMBER)]],
        colWidths=[NUMBER_WIDTH, available, NUMBER_WIDTH],
    )
    body.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    body.spaceBefore, body.spaceAfter = 3, 7
    return body


def figure(name: str, caption: str, width: float = FRAME_WIDTH) -> KeepTogether:
    """Рисунок из report/figures с подписью."""
    path = str(FIGURES_DIR / f"{name}.png")
    pixel_width, pixel_height = ImageReader(path).getSize()
    image = Image(path, width=width, height=width * pixel_height / pixel_width)
    return KeepTogether([image, Paragraph(typeset(caption), CAPTION)])


def table(
    caption: str, rows: Sequence[Sequence[str]], widths: Sequence[float]
) -> KeepTogether:
    """Таблица с подписью; первая строка — заголовок."""
    cells = [[Paragraph(typeset(text), CELL_HEADER) for text in rows[0]]]
    cells += [[Paragraph(typeset(text), CELL) for text in row] for row in rows[1:]]
    body = Table(cells, colWidths=list(widths))
    body.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4edf3")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7f9")]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, MUTED),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, MUTED),
    ]))
    return KeepTogether([Paragraph(caption, CAPTION), body, Spacer(1, 10)])


def title_page() -> list[Flowable]:
    return [
        Spacer(1, 170),
        Paragraph("Физический маятник", TITLE),
        Paragraph("Проект М5, курс «Цифровизация физических процессов»", SUBTITLE),
        Spacer(1, 40),
        Paragraph("Авторы: Кашков Сергей, Богославский Родион", SUBTITLE),
        Paragraph("2026", SUBTITLE),
        Spacer(1, 120),
        paragraph(
            "Маятник — графитовый стержень с латунным грузом на нижнем конце, "
            "ось проходит через верхний конец стержня. По форме тела рассчитан "
            "момент инерции, уравнение колебаний решено численно без трения и "
            "с малым вязким трением, изучена зависимость периода от амплитуды "
            "и проверено сохранение энергии. Результаты сравниваются с "
            "теоретическими формулами, вывод которых тоже приведён. Выполнена "
            "только основная часть задания."
        ),
        PageBreak(),
    ]


def section_body(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    mm = 1000.0
    rows = [
        ["Величина", "Значение", "Комментарий"],
        ["Длина стержня <i>L</i>", number(100 * p.rod_length_m, 1) + " см", ""],
        ["Радиус стержня <i>R</i>", number(mm * p.rod_radius_m, 0) + " мм", ""],
        ["Плотность графита <i>ρ</i><sub>ст</sub>",
         number(p.rod_density_kg_m3 / 1e3, 1) + " г/см³", "типичная для графита"],
        ["Масса стержня <i>m</i><sub>ст</sub>",
         number(1e3 * p.rod_mass_kg, 2) + " г", "расчёт, формула (1)"],
        [f"Размеры груза <i>w</i> {TIMES} <i>h</i> {TIMES} <i>s</i>",
         f"{number(mm * p.bob_width_m, 0)} {TIMES} "
         f"{number(mm * p.bob_height_m, 0)} {TIMES} "
         f"{number(mm * p.bob_depth_m, 0)} мм",
         "<i>w</i> — поперёк стержня, <i>h</i> — вдоль стержня, "
         "<i>s</i> — вдоль оси"],
        ["Плотность латуни <i>ρ</i><sub>гр</sub>",
         number(p.bob_density_kg_m3 / 1e3, 1) + " г/см³", "типичная для латуни"],
        ["Масса груза <i>m</i><sub>гр</sub>",
         number(1e3 * p.bob_mass_kg, 2) + " г", "расчёт, формула (2)"],
        ["Ускорение свободного падения <i>g</i>",
         number(p.gravity_m_s2, 5) + " м/с²", ""],
        ["Время полузатухания амплитуды <i>t</i><sub>½</sub>",
         number(p.amplitude_half_life_s, 0) + " с", "задаёт малое трение"],
    ]
    return [
        heading("1. Постановка задачи и параметры тела"),
        paragraph(
            "Моделируется физический маятник — твёрдое тело, которое качается в "
            "вертикальной плоскости вокруг горизонтальной оси в поле тяжести. "
            "Тело составлено из двух простых форм: графитового стержня-цилиндра "
            "и латунного груза-параллелепипеда, закреплённого на нижнем конце "
            "стержня. Ось перпендикулярна плоскости качания и проходит через "
            "верхний конец стержня. Все входные параметры собраны в файле "
            "physical_pendulum/config.py."
        ),
        table("Таблица 1. Параметры маятника", rows, [195.0, 100.0, 200.0]),
        paragraph(
            "Массы стержня и груза считаются по их объёму и плотности. Стержень "
            "проходит сквозь груз, поэтому из объёма груза вычитается отверстие "
            "под стержень:"
        ),
        equation(rf"m{ST} = \rho{ST}\,\pi R^2 L = "
                 rf"{tex_number(1e3 * p.rod_mass_kg, 2)}{unit('г')}", "m_rod"),
        equation(rf"m{GR} = \rho{GR}\,(w\,h\,s - \pi R^2 h) = "
                 rf"{tex_number(1e3 * p.bob_mass_kg, 2)}{unit('г')}", "m_bob"),
        equation(rf"m = m{ST} + m{GR} = {tex_number(1e3 * p.mass_kg, 2)}{unit('г')}"),
        figure("geometry", "Рис. 1. Слева: маятник в равновесии и его размеры. "
               "Справа: отклонение на угол <i>θ</i>, сила тяжести и её плечо "
               "относительно оси. Масштаб соблюдён.", width=330.0),
    ]


def section_inertia(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    rod = p.rod_mass_kg * (p.rod_length_m**2 / 3 + p.rod_radius_m**2 / 4)
    bob = p.inertia_kg_m2 - rod
    return [
        heading("2. Момент инерции и центр масс"),
        paragraph(
            "Момент инерции тела относительно оси равен сумме моментов инерции "
            "стержня и груза:"
        ),
        equation(rf"I = I{ST} + I{GR}", "inertia_sum"),
        paragraph(
            "<b>Стержень.</b> Момент инерции цилиндра относительно поперечной оси "
            "через его центр известен; ось подвеса сдвинута на <i>L</i>/2, "
            "поэтому по теореме Штейнера:"
        ),
        equation(rf"I{ST} = m{ST}\left(\dfrac{{L^2}}{{12}} + \dfrac{{R^2}}{{4}}"
                 rf"\right) + m{ST}\left(\dfrac{{L}}{{2}}\right)^2 = "
                 rf"m{ST}\left(\dfrac{{L^2}}{{3}} + \dfrac{{R^2}}{{4}}\right)",
                 "inertia_rod"),
        paragraph(
            "<b>Груз.</b> Момент инерции параллелепипеда относительно оси через "
            "центр, параллельной ребру <i>s</i>:"
        ),
        equation(rf"I_c = m{GR}\,\dfrac{{w^2 + h^2}}{{12}}"),
        paragraph("Центр груза находится на расстоянии <i>a</i> от оси:"),
        equation(r"a = L - \dfrac{h}{2}"),
        paragraph("По теореме Штейнера:"),
        equation(rf"I{GR} = I_c + m{GR}a^2 = "
                 rf"m{GR}\left(a^2 + \dfrac{{w^2 + h^2}}{{12}}\right)", "inertia_bob"),
        paragraph(
            "<b>Центр масс.</b> Центр масс стержня лежит в его середине, центр "
            "масс груза — в центре груза. Расстояние от оси до центра масс тела:"
        ),
        equation(rf"d = \dfrac{{m{ST}\,L/2 + m{GR}\,a}}{{m{ST} + m{GR}}}",
                 "center"),
        paragraph(
            "Подставляем параметры из таблицы 1: <i>a</i> = "
            f"{number(100 * p.bob_distance_m, 1)} см, <i>d</i> = "
            f"{number(100 * p.center_of_mass_m, 2)} см, момент инерции"
        ),
        equation(rf"I = I{ST} + I{GR} = {tex_scientific(rod, 3)} + "
                 rf"{tex_scientific(bob, 3)} = "
                 rf"{tex_scientific(p.inertia_kg_m2, 4)}{unit(r'кг\cdot м^2')}"),
        paragraph(
            f"Стержень легче груза в {number(p.bob_mass_kg / p.rod_mass_kg, 0)} "
            "раз, и его доля в моменте инерции всего "
            f"{number(100 * rod / p.inertia_kg_m2, 1)} %."
        ),
    ]


def section_motion(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    return [
        heading("3. Уравнение движения и энергия"),
        paragraph(
            "Угол <i>θ</i> отсчитывается от вертикали, угловая скорость "
            "<i>ω</i> — производная угла. Тело вращается вокруг неподвижной "
            "оси, поэтому уравнение моментов относительно оси имеет вид"
        ),
        equation(r"I\ddot\theta = M"),
        paragraph(
            "Сила тяжести приложена в центре масс на расстоянии <i>d</i> от оси, "
            "её плечо при отклонении на угол <i>θ</i> равно проекции <i>d</i> на "
            "горизонталь (рис. 1). Вязкое трение в оси даёт момент, "
            "пропорциональный угловой скорости:"
        ),
        equation(r"M = -mgd\,\sin\theta - b\,\dot\theta\quad\Rightarrow\quad "
                 r"I\ddot\theta = -mgd\,\sin\theta - b\,\dot\theta", "motion"),
        paragraph(
            f"<b>Энергия.</b> Умножим {ref('motion')} на <i>ω</i> и воспользуемся "
            "тем, что"
        ),
        equation(r"\omega\dot\omega = \dfrac{d}{dt}\dfrac{\omega^2}{2},\qquad "
                 r"\omega\sin\theta = \dfrac{d}{dt}(1 - \cos\theta)"),
        paragraph("Получаем"),
        equation(r"\dfrac{d}{dt}\left[\dfrac{I\omega^2}{2} + "
                 r"mgd\,(1 - \cos\theta)\right] = -b\,\omega^2"),
        paragraph(
            "В скобках стоит полная механическая энергия: кинетическая энергия "
            "вращения и потенциальная энергия центра масс, отсчитанная от "
            "положения равновесия:"
        ),
        equation(r"E = \dfrac{I\omega^2}{2} + mgd\,(1 - \cos\theta),\qquad "
                 r"\dfrac{dE}{dt} = -b\,\omega^2 \leq 0", "energy"),
        paragraph(
            "Без трения энергия постоянна, с трением убывает. Убыль энергии "
            "переходит в теплоту <i>Q</i>, и их сумма сохраняется:"
        ),
        equation(r"Q(t) = \int_0^t b\,\omega^2\,dt,\qquad E(t) + Q(t) = E_0",
                 "balance"),
        paragraph(
            "<b>Малые колебания.</b> При малых углах синус можно заменить самим "
            f"углом. Без трения {ref('motion')} переходит в уравнение "
            "гармонических колебаний:"
        ),
        equation(r"\sin\theta \approx \theta\quad\Rightarrow\quad "
                 r"\ddot\theta + \omega_0^2\,\theta = 0,\qquad "
                 r"\omega_0 = \sqrt{\dfrac{mgd}{I}}", "harmonic"),
        paragraph(
            "Маятник отпускается без начальной скорости с отклонения <i>A</i>. "
            "Решение с такими начальными условиями и его период:"
        ),
        equation(r"\theta(0) = A,\quad \dot\theta(0) = 0\quad\Rightarrow\quad "
                 r"\theta(t) = A\cos\omega_0 t", "harmonic_solution"),
        equation(rf"T_0 = \dfrac{{2\pi}}{{\omega_0}} = "
                 rf"2\pi\sqrt{{\dfrac{{I}}{{mgd}}}} = "
                 rf"{tex_number(small_angle_period_s(p), 5)}{unit('с')}", "t0"),
        paragraph(
            "Период малых колебаний не зависит от амплитуды. Это свойство "
            "называется изохронностью [2]."
        ),
    ]


def section_period_theory() -> list[Flowable]:
    return [
        heading("4. Период при большой амплитуде"),
        paragraph(
            "При большой амплитуде замена синуса углом не годится, и период "
            "находим из закона сохранения энергии без трения. В крайнем "
            "положении угол равен <i>A</i>, а скорость равна нулю, поэтому"
        ),
        equation(r"\dfrac{I\omega^2}{2} + mgd\,(1 - \cos\theta) = "
                 r"mgd\,(1 - \cos A)\quad\Rightarrow\quad "
                 r"\omega^2 = 2\omega_0^2\,(\cos\theta - \cos A)"),
        paragraph(
            "За четверть периода маятник проходит от нуля до <i>A</i>, "
            "отсюда"
        ),
        equation(r"T = 4\int_0^A \dfrac{d\theta}{\omega} = \dfrac{4}{\omega_0}"
                 r"\int_0^A \dfrac{d\theta}{\sqrt{2\,(\cos\theta - \cos A)}}"),
        paragraph(
            "Воспользуемся формулой для косинуса через синус половинного угла "
            "и обозначим <i>k</i> синус половины амплитуды:"
        ),
        equation(r"1 - \cos\theta = 2\sin^2\dfrac{\theta}{2},\qquad "
                 r"k = \sin\dfrac{A}{2},\qquad "
                 r"\cos\theta - \cos A = 2\left(k^2 - \sin^2\dfrac{\theta}{2}"
                 r"\right)"),
        paragraph(
            "Сделаем замену переменной <i>θ</i> на <i>φ</i>. Пределы "
            "интегрирования тоже меняются:"
        ),
        equation(r"\sin\dfrac{\theta}{2} = k\sin\varphi,\qquad "
                 r"0 \leq \theta \leq A\quad\Rightarrow\quad "
                 r"0 \leq \varphi \leq \dfrac{\pi}{2}"),
        paragraph("Дифференциал и корень в знаменателе:"),
        equation(r"\dfrac{1}{2}\cos\dfrac{\theta}{2}\,d\theta = "
                 r"k\cos\varphi\,d\varphi\quad\Rightarrow\quad "
                 r"d\theta = \dfrac{2k\cos\varphi\,d\varphi}"
                 r"{\sqrt{1 - k^2\sin^2\varphi}}"),
        equation(r"\sqrt{k^2 - \sin^2\dfrac{\theta}{2}} = "
                 r"\sqrt{k^2 - k^2\sin^2\varphi} = k\cos\varphi"),
        paragraph("После подстановки множитель с косинусом сокращается:"),
        equation(r"T = \dfrac{4}{\omega_0}\int_0^{\pi/2}"
                 r"\dfrac{d\varphi}{\sqrt{1 - k^2\sin^2\varphi}} = "
                 r"\dfrac{4}{\omega_0}\,K(k^2),\qquad k^2 = \sin^2\dfrac{A}{2}",
                 "exact"),
        paragraph(
            "Здесь <i>K</i> — полный эллиптический интеграл первого рода, по "
            "определению"
        ),
        equation(r"K(m) = \int_0^{\pi/2}\dfrac{d\varphi}"
                 r"{\sqrt{1 - m\sin^2\varphi}}"),
        paragraph(
            "Через элементарные функции он не выражается. В программе он "
            "считается функцией scipy.special.ellipk(m) [5], которая принимает "
            "как раз параметр <i>m</i>, то есть квадрат <i>k</i>."
        ),
        paragraph(
            "<b>Ряд.</b> При небольших <i>k</i> разложим подынтегральную "
            "функцию по степеням <i>k</i>:"
        ),
        equation(r"\dfrac{1}{\sqrt{1 - k^2\sin^2\varphi}} \approx 1 + "
                 r"\dfrac{k^2}{2}\sin^2\varphi + \dfrac{3k^4}{8}\sin^4\varphi"),
        paragraph("Интегралы от степеней синуса:"),
        equation(r"\int_0^{\pi/2}\sin^2\varphi\,d\varphi = \dfrac{\pi}{4},\qquad "
                 r"\int_0^{\pi/2}\sin^4\varphi\,d\varphi = \dfrac{3\pi}{16}"),
        paragraph("Получаем"),
        equation(r"K(k^2) \approx \dfrac{\pi}{2}\left(1 + \dfrac{k^2}{4} + "
                 r"\dfrac{9k^4}{64}\right)"),
        paragraph("Выразим <i>k</i> через амплитуду, оставляя члены до четвёртой "
                  "степени:"),
        equation(r"k^2 = \sin^2\dfrac{A}{2} \approx \left(\dfrac{A}{2} - "
                 r"\dfrac{A^3}{48}\right)^2 \approx \dfrac{A^2}{4} - "
                 r"\dfrac{A^4}{48}"),
        equation(r"\dfrac{k^2}{4} + \dfrac{9k^4}{64} \approx \dfrac{A^2}{16} - "
                 r"\dfrac{A^4}{192} + \dfrac{9A^4}{1024} = \dfrac{A^2}{16} + "
                 r"\dfrac{11A^4}{3072}"),
        paragraph("Множитель перед скобкой равен периоду малых колебаний:"),
        equation(r"\dfrac{4}{\omega_0}\cdot\dfrac{\pi}{2} = "
                 r"\dfrac{2\pi}{\omega_0} = T_0"),
        paragraph("В итоге"),
        equation(r"T \approx T_0\left(1 + \dfrac{A^2}{16} + "
                 r"\dfrac{11A^4}{3072}\right)", "series"),
        paragraph(
            "Ряд годится, пока амплитуда заметно меньше радиана. При больших "
            f"амплитудах нужна точная формула {ref('exact')}."
        ),
    ]


def section_damped_theory(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    ratio = p.decay_rate_1_s / p.natural_frequency_rad_s
    return [
        heading("5. Малые затухающие колебания"),
        paragraph(
            f"При малых углах с трением уравнение {ref('motion')} после деления "
            "на <i>I</i> принимает вид"
        ),
        equation(r"\ddot\theta + 2\beta\,\dot\theta + \omega_0^2\,\theta = 0,"
                 r"\qquad \beta = \dfrac{b}{2I}", "damped_equation"),
        paragraph("Ищем решение в виде экспоненты:"),
        equation(r"\theta = e^{\lambda t}\quad\Rightarrow\quad "
                 r"\lambda^2 + 2\beta\lambda + \omega_0^2 = 0\quad\Rightarrow"
                 r"\quad \lambda = -\beta \pm i\,\omega_d,\qquad "
                 r"\omega_d = \sqrt{\omega_0^2 - \beta^2}"),
        paragraph(
            "Действительное решение, которое начинается с отклонения <i>A</i> "
            "без начальной скорости:"
        ),
        equation(r"\theta = A e^{-\beta t}\left(\cos\omega_d t + "
                 r"\dfrac{\beta}{\omega_d}\sin\omega_d t\right)"),
        paragraph(
            "При слабом трении второе слагаемое в скобках мало, и колебания "
            "происходят с экспоненциально убывающей амплитудой [3]:"
        ),
        equation(r"\beta \ll \omega_0\quad\Rightarrow\quad "
                 r"\theta \approx A e^{-\beta t}\cos\omega_d t,\qquad "
                 r"T_d = \dfrac{2\pi}{\omega_d}", "damped_solution"),
        paragraph(
            "Трение задаём временем <i>t</i><sub>½</sub>, за которое амплитуда "
            "уменьшается вдвое. Отсюда коэффициент затухания и коэффициент "
            "трения:"
        ),
        equation(r"e^{-\beta t_{1/2}} = \dfrac{1}{2}\quad\Rightarrow\quad "
                 r"\beta = \dfrac{\ln 2}{t_{1/2}},\qquad b = 2I\beta",
                 "half_life"),
        paragraph(
            "Энергия малых колебаний пропорциональна квадрату амплитуды: в "
            "крайнем положении скорость равна нулю и вся энергия "
            "потенциальная. Поэтому энергия убывает вдвое быстрее амплитуды:"
        ),
        equation(r"E \approx mgd\,(1 - \cos\theta_{\max}) \approx "
                 r"\dfrac{mgd\,\theta_{\max}^2}{2}\quad\Rightarrow\quad "
                 r"E \approx E_0\,e^{-2\beta t}", "damped_energy"),
        paragraph("Для нашего маятника:"),
        equation(rf"\beta = \dfrac{{\ln 2}}{{{tex_number(p.amplitude_half_life_s, 0)}"
                 rf"{unit('с')}}} = {tex_number(p.decay_rate_1_s, 4)}"
                 rf"{unit(r'с^{-1}')},\qquad b = 2I\beta = "
                 rf"{tex_scientific(p.damping_n_m_s, 2)}"
                 rf"{unit(r'Н\cdot м\cdot с')}"),
        equation(rf"\dfrac{{\beta}}{{\omega_0}} = {tex_scientific(ratio)}"),
        paragraph("Трение действительно малое."),
    ]


def section_method() -> list[Flowable]:
    return [
        heading("6. Численный метод"),
        paragraph(
            f"Уравнение {ref('motion')} решается численно методом Рунге — Кутты "
            "(функция scipy.integrate.solve_ivp [4]). Маятник отпускается без "
            "начальной скорости с отклонения на угол <i>A</i>. По найденным "
            f"<i>θ</i>(<i>t</i>) и <i>ω</i>(<i>t</i>) энергия считается по формуле "
            f"{ref('energy')}, а теплота <i>Q</i> — по формуле {ref('balance')}."
        ),
        paragraph(
            "Период находим по графику <i>θ</i>(<i>t</i>) как время между двумя "
            "соседними прохождениями положения равновесия в одну сторону; "
            "по всем колебаниям расчёта это время усредняется."
        ),
    ]


def section_free(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    small, large = results.small, results.large
    small_deg = degrees(small.amplitude_rad)
    large_deg = degrees(large.amplitude_rad)
    t0 = small_angle_period_s(p)
    return [
        heading("7. Свободные колебания без трения и сохранение энергии"),
        paragraph(
            f"При амплитуде {number(small_deg, 0)}° численное решение совпадает с "
            f"гармоническим {ref('harmonic_solution')} (рис. 2). Измеренный "
            f"период и период малых колебаний {ref('t0')}:"
        ),
        equation(rf"T_{{\mathrm{{расч}}}} = {tex_number(small.period_s, 5)}"
                 rf"{unit('с')},\qquad T_0 = {tex_number(t0, 5)}{unit('с')}"),
        paragraph(
            "Небольшая разница — это уже поправка на конечную амплитуду из "
            f"ряда {ref('series')}. При {number(large_deg, 0)}° период равен "
            f"{number(large.period_s, 5)} с, он на "
            f"{number(100 * (large.period_s / t0 - 1), 1)} % больше "
            "<i>T</i><sub>0</sub>, и численное решение заметно отстаёт от "
            "гармонического."
        ),
        figure("free", "Рис. 2. Свободные колебания при "
               f"{number(small_deg, 0)}° и {number(large_deg, 0)}°: численное "
               f"решение и гармоническое решение {ref('harmonic_solution')}. "
               "Внизу — относительная погрешность энергии (наибольшая с начала "
               "расчёта).", 360.0),
        paragraph(
            "<b>Погрешность энергии.</b> Без трения энергия "
            f"{ref('energy')} должна сохраняться. Численное решение приближённое, "
            "и вычисленная по нему энергия немного отличается от начальной. "
            "Это отличие показывает точность расчёта:"
        ),
        equation(r"\delta_E = \max_t\,\dfrac{|E(t) - E_0|}{E_0}", "energy_error"),
        equation(rf"\delta_E({number(small_deg, 0)}\degree) = "
                 rf"{tex_scientific(small.energy_relative_error)},\qquad "
                 rf"\delta_E({number(large_deg, 0)}\degree) = "
                 rf"{tex_scientific(large.energy_relative_error)}"),
        paragraph(
            "Это уровень ошибок округления чисел в компьютере, и за "
            f"{number(FREE_DURATION_S, 0)} с расчёта энергия не уходит "
            "(нижний график рис. 2). Чтобы при малых углах не терять точность "
            "на вычитании близких чисел 1 и cos <i>θ</i>, потенциальная энергия "
            "считается через синус половинного угла:"
        ),
        equation(r"U = mgd\,(1 - \cos\theta) = 2mgd\,\sin^2\dfrac{\theta}{2}"),
    ]


def section_period(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    t0 = small_angle_period_s(p)
    pairs = list(zip(results.period_amplitudes_deg, results.periods_s))
    rows = [["<i>A</i>, °", "<i>T</i><sub>расч</sub>, с", "<i>T</i><sub>ряд</sub>, с",
             "<i>T</i><sub>точн</sub>, с", "<i>δ</i><sub><i>T</i></sub>",
             "<i>T</i><sub>расч</sub> / <i>T</i><sub>0</sub>"]]
    for amplitude, period in pairs:
        exact = exact_period_s(p, radians(amplitude))
        rows.append([
            number(amplitude, 0), number(period, 5),
            number(series_period_s(p, radians(amplitude)), 5), number(exact, 5),
            scientific(period / exact - 1.0), number(period / t0, 4),
        ])
    deviation = max(abs(period / exact_period_s(p, radians(amplitude)) - 1.0)
                    for amplitude, period in pairs)

    def series_error(amplitude_deg: float) -> float:
        angle = radians(amplitude_deg)
        return 100 * (1 - series_period_s(p, angle) / exact_period_s(p, angle))

    moderate = degrees(results.large.amplitude_rad)
    first, first_period = pairs[0]
    largest, largest_period = pairs[-1]
    moderate_period = results.large.period_s
    t0 = small_angle_period_s(p)
    return [
        heading("8. Зависимость периода от амплитуды"),
        paragraph(
            "<b>Почему при малых углах период не зависит от амплитуды.</b> "
            f"В гармоническом приближении {ref('harmonic')} возвращающий момент "
            "пропорционален углу:"
        ),
        equation(r"M = -mgd\,\theta"),
        paragraph(
            "Если увеличить амплитуду вдвое, маятнику нужно пройти вдвое больший "
            "путь, но и момент в каждой точке вдвое больше, поэтому он движется "
            "вдвое быстрее. Время одного колебания остаётся тем же, период "
            f"{ref('t0')} от амплитуды не зависит."
        ),
        paragraph(
            "<b>Почему при больших углах период растёт.</b> В настоящем "
            f"уравнении {ref('motion')} момент пропорционален синусу угла, а "
            "синус растёт медленнее самого угла:"
        ),
        equation(r"M = -mgd\,\sin\theta,\qquad \sin\theta < \theta\quad "
                 r"(\theta > 0)"),
        paragraph("Отношение синуса к углу (угол в радианах):"),
        equation(
            r",\qquad ".join(
                rf"\theta = {angle_deg:g}\degree:\ "
                r"\dfrac{\sin\theta}{\theta}"
                r" \approx "
                + number(sin(radians(angle_deg)) / radians(angle_deg), 2)
                .replace(",", "{,}")
                for angle_deg in SINE_RATIO_ANGLES_DEG
            )
        ),
        paragraph(
            "При больших отклонениях маятник тянет к равновесию слабее, чем по "
            "линейному закону, он "
            "движется медленнее, и период растёт: при 60° на "
            f"{number(100 * (period_at(results, 60.0) / t0 - 1), 1)} %, при 90° на "
            f"{number(100 * (period_at(results, 90.0) / t0 - 1), 1)} % "
            "(таблица 2)."
        ),
        paragraph(
            f"Для каждой амплитуды из таблицы 2 уравнение {ref('motion')} без "
            f"трения решалось заново на {number(PERIOD_DURATION_S, 0)} с, период "
            "измерялся, как описано в разделе 6. В таблице численный "
            f"период сравнивается с рядом {ref('series')} и точной формулой "
            f"{ref('exact')}. Отличие расчёта от точной формулы:"
        ),
        equation(r"\delta_T = \dfrac{T_{\mathrm{расч}}}{T_{\mathrm{точн}}} - 1"),
        table("Таблица 2. Период колебаний: численный расчёт и теория", rows,
              [45.0, 82.0, 82.0, 82.0, 102.0, 102.0]),
        figure("period", "Рис. 3. Период колебаний в зависимости от амплитуды: "
               f"численный расчёт, ряд {ref('series')} и точная формула "
               f"{ref('exact')}.", 340.0),
        paragraph(
            f"Отношение к периоду малых колебаний растёт от "
            f"{number(first_period / t0, 4)} при {number(first, 0)}° до "
            f"{number(largest_period / t0, 3)} при {number(largest, 0)}°: при "
            f"{number(moderate, 0)}° период больше на "
            f"{number(100 * (moderate_period / t0 - 1), 1)} %, при "
            f"{number(largest, 0)}° — на "
            f"{number(100 * (largest_period / t0 - 1), 0)} %. Численный период "
            "совпадает с точной формулой:"
        ),
        equation(rf"\max\,|\delta_T| = {tex_scientific(deviation)}"),
        paragraph("Погрешность ряда относительно точной формулы:"),
        equation(r"\varepsilon = 1 - \dfrac{T_{\mathrm{ряд}}}{T_{\mathrm{точн}}}"
                 rf",\qquad \varepsilon({number(moderate, 0)}\degree) = "
                 rf"{tex_number(series_error(moderate), 2)}\%,\qquad "
                 rf"\varepsilon({number(largest, 0)}\degree) = "
                 rf"{tex_number(series_error(largest), 1)}\%"),
        paragraph(
            "Ряд хорошо работает до умеренных амплитуд, а при больших сильно "
            "занижает период (рис. 3)."
        ),
    ]


def section_damped(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    run = results.damped
    fitted = fit_decay_rate_1_s(run)
    duration = float(run.time_s[-1])
    amplitude_deg = degrees(run.amplitude_rad)
    return [
        heading("9. Затухающие колебания"),
        paragraph(
            f"С трением {ref('half_life')} маятник отпускается с "
            f"{number(amplitude_deg, 0)}°, расчёт идёт "
            f"{number(duration, 0)} с. Амплитуда уменьшается по экспоненте "
            "(рис. 4): на верхнем графике численное решение лежит внутри "
            f"теоретической огибающей из {ref('damped_solution')}, внизу слева "
            "максимумы в логарифмическом масштабе ложатся на прямую теории, "
            f"внизу справа энергия совпадает с {ref('damped_energy')}."
        ),
        figure("damped", "Рис. 4. Затухающие колебания и энергия маятника.", 360.0),
        paragraph(
            "Коэффициент затухания по численному решению найден по наклону "
            "логарифма максимумов угла от времени. Он совпадает с "
            f"теоретическим {ref('half_life')}:"
        ),
        equation(rf"\beta_{{\mathrm{{расч}}}} = {tex_number(fitted, 5)}"
                 rf"{unit(r'с^{-1}')},\qquad \beta = "
                 rf"{tex_number(p.decay_rate_1_s, 5)}{unit(r'с^{-1}')}"),
        paragraph(
            "Малое трение период почти не меняет, расчёт и теория "
            f"{ref('damped_solution')}:"
        ),
        equation(rf"T_{{\mathrm{{расч}}}} = {tex_number(run.period_s, 4)}"
                 rf"{unit('с')},\qquad T_d = {tex_number(damped_period_s(p), 4)}"
                 rf"{unit('с')}"),
        paragraph(
            "Энергия убывает из-за трения, а энергия вместе с выделившейся "
            f"теплотой остаётся равной начальной {ref('balance')}:"
        ),
        equation(rf"\delta_{{E+Q}} = \max_t\,\dfrac{{|E(t) + Q(t) - E_0|}}{{E_0}}"
                 rf" = {tex_scientific(run.balance_relative_error)}"),
    ]


def section_conclusions(results: ExperimentResults) -> list[Flowable]:
    p = results.pendulum
    t0 = small_angle_period_s(p)
    largest, largest_period = (results.period_amplitudes_deg[-1],
                               results.periods_s[-1])
    return [
        heading("10. Выводы"),
        paragraph(
            f"1. Момент инерции тела {scientific(p.inertia_kg_m2, 4)} кг·м² "
            "рассчитан по формулам для цилиндра и параллелепипеда с теоремой "
            "Штейнера."
        ),
        paragraph(
            "2. При малой амплитуде численное решение совпадает с гармоническим, "
            f"период малых колебаний {number(t0, 4)} с."
        ),
        paragraph(
            "3. Период растёт с амплитудой: при "
            f"{number(degrees(results.large.amplitude_rad), 0)}° на "
            f"{number(100 * (results.large.period_s / t0 - 1), 1)} %, при "
            f"{number(largest, 0)}° на {number(100 * (largest_period / t0 - 1), 0)} %. "
            "Численный период совпадает с точной формулой через эллиптический "
            "интеграл, ряд по степеням амплитуды годится до умеренных амплитуд."
        ),
        paragraph(
            "4. Без трения относительная погрешность энергии порядка "
            f"{power(1e-14)}, это уровень ошибок округления. С трением энергия "
            "убывает, баланс энергии и теплоты выполняется с той же точностью, "
            "амплитуда затухает по экспоненте с теоретическим коэффициентом "
            "затухания."
        ),
        heading("11. Источники"),
        *[Paragraph(f"{index}. {text}", SOURCE)
          for index, text in enumerate(SOURCES, start=1)],
    ]


def register_fonts() -> None:
    """Зарегистрировать DejaVu Sans из поставки matplotlib."""
    fonts = {
        FONT: FontProperties(family="DejaVu Sans"),
        FONT_BOLD: FontProperties(family="DejaVu Sans", weight="bold"),
        FONT_ITALIC: FontProperties(family="DejaVu Sans", style="oblique"),
        FONT_BOLD_ITALIC: FontProperties(family="DejaVu Sans", weight="bold",
                                         style="oblique"),
    }
    for name, properties in fonts.items():
        path = font_manager.findfont(properties)
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD,
                                  italic=FONT_ITALIC, boldItalic=FONT_BOLD_ITALIC)


def save_figures(results: ExperimentResults) -> None:
    FIGURES_DIR.mkdir(exist_ok=True)
    for old in FIGURES_DIR.glob("*.png"):
        old.unlink()
    for name, item in create_pendulum_figures(results).items():
        item.savefig(FIGURES_DIR / f"{name}.png", dpi=FIGURE_DPI)
        plt.close(item)


def draw_footer(canvas: Canvas, document: BaseDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 28, "Физический маятник · проект М5")
    canvas.drawRightString(A4[0] - MARGIN, 28, str(document.page))
    canvas.restoreState()


def skip_footer(canvas: Canvas, document: BaseDocTemplate) -> None:
    """Титульный лист без колонтитула."""


def main() -> None:
    register_fonts()
    EQUATION_NUMBERS.clear()
    results = run_experiments(DEFAULT_PENDULUM, DEFAULT_INTEGRATION)
    save_figures(results)
    document = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN, title="Физический маятник",
        author="Кашков Сергей, Богославский Родион",
        subject="Проект М5, курс «Цифровизация физических процессов»",
    )
    story = [
        *title_page(), *section_body(results), *section_inertia(results),
        *section_motion(results), *section_period_theory(),
        *section_damped_theory(results), *section_method(),
        *section_free(results), *section_period(results),
        *section_damped(results), *section_conclusions(results),
    ]
    document.build(story, onFirstPage=skip_footer, onLaterPages=draw_footer)
    print(f"Отчёт: {PDF_PATH}")


if __name__ == "__main__":
    main()
