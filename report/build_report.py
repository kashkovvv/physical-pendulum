"""Создать PDF и подтверждающие данные: python -m report.build_report."""
from pathlib import Path
from io import BytesIO
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER
from physical_pendulum.experiments import run_experiments, save_experiments
from physical_pendulum.plots import create_figures

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report'


def main():
    data=run_experiments()
    p=data['model']; m=data['metrics']
    save_experiments(data,OUT/'data')
    figures=create_figures(data)
    (OUT/'figures').mkdir(exist_ok=True)
    for name,fig in figures.items():
        fig.savefig(OUT/'figures'/f'{name}.png',dpi=200)
    plt.close('all')
    pdfmetrics.registerFont(TTFont('DV',font_manager.findfont('DejaVu Sans')))
    pdfmetrics.registerFont(TTFont('DVB',font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',weight='bold'))))
    pdfmetrics.registerFontFamily('DV',normal='DV',bold='DVB',italic='DV',boldItalic='DVB')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyRu',fontName='DV',fontSize=9.4,leading=14,spaceAfter=8,textColor=colors.HexColor('#243747')))
    styles.add(ParagraphStyle(name='HeadRu',fontName='DVB',fontSize=17,leading=22,spaceAfter=14,textColor=colors.HexColor('#163c56')))
    styles.add(ParagraphStyle(name='TitleRu',fontName='DVB',fontSize=28,leading=35,spaceAfter=18,textColor=colors.HexColor('#163c56')))
    styles.add(ParagraphStyle(name='SmallRu',fontName='DV',fontSize=8,leading=11,spaceAfter=6))
    styles.add(ParagraphStyle(name='CaptionRu',fontName='DV',fontSize=8,leading=11,spaceAfter=12,alignment=TA_CENTER))
    story=[]
    def body(text): story.append(Paragraph(text,styles['BodyRu']))
    def head(text): story.append(Paragraph(text,styles['HeadRu']))
    def page(): story.append(PageBreak())
    def chart(name,caption,width=475):
        fig=Image(str(OUT/'figures'/f'{name}.png'))
        fig.drawHeight=fig.imageHeight*width/fig.imageWidth; fig.drawWidth=width
        story.append(fig); story.append(Paragraph(caption,styles['CaptionRu']))
    def equation(text):
        fig=plt.figure(figsize=(7,.46)); fig.text(.5,.5,'$'+text+'$',ha='center',va='center',fontsize=13)
        buf=BytesIO(); fig.savefig(buf,format='png',dpi=200,bbox_inches='tight',pad_inches=.12); plt.close(fig); buf.seek(0)
        im=Image(buf); scale=min(1,465/im.imageWidth); im.drawWidth=im.imageWidth*scale; im.drawHeight=im.imageHeight*scale
        story.append(im); story.append(Spacer(1,7))
    def table(headers,rows,widths):
        values=[[Paragraph(escape(str(c)),styles['SmallRu']) for c in headers]]
        values += [[Paragraph(escape(str(c)),styles['SmallRu']) for c in row] for row in rows]
        t=Table(values,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4edf3')),('VALIGN',(0,0),(-1,-1),'TOP'),
                              ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f9')]),
                              ('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),
                              ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#9bb2c2'))]))
        story.append(t); story.append(Spacer(1,10))
    def footer(canvas,doc):
        canvas.setFont('DV',8); canvas.setFillColor(colors.HexColor('#607787'))
        canvas.drawString(48,28,'М5 · Физический маятник · Вычислительный проект')
        canvas.drawRightString(547,28,str(doc.page))

    story.append(Spacer(1,16))
    story.append(Paragraph('Физический<br/>маятник',styles['TitleRu']))
    body('<b>Проект М5 · Цифровизация физических процессов</b><br/>Основная часть задания. ВШПИ, 2026–2027 учебный год.')
    head('От реального прибора к проверяемой модели')
    body('Рассматривается учебный опыт по определению ускорения свободного падения с помощью составного маятника. '
         'Прототип — лабораторный прибор PASCO ME-9821 [2]. Модель учитывает массу стержня и конечные размеры груза. '
         'Исследуется, когда формула малых колебаний достаточно точна и как меняются колебания при слабом трении.')
    chart('geometry','Рис. 1. Принятая геометрия; положение груза выбрано для расчётного опыта.',400)
    body('Выполнены расчёт момента инерции, свободные нелинейные колебания, зависимость периода от амплитуды, '
         'проверка энергии, затухание и сравнение с теорией. Неваляшка, связанные маятники и вынужденные колебания '
         'относятся к дополнительным пунктам и не рассматриваются [1].')
    body('<b>Статус результатов:</b> вычислительные эксперименты с реалистичной геометрией. Натурные измерения не проводились.')

    page(); head('1. Исходные данные и момент инерции')
    table(['Величина','Значение','Происхождение'],[
        ['Длина / радиус стержня','0,417 м / 0,002 м','PASCO [2]'],
        ['Масса стержня / груза','0,001 кг / 0,100 кг','PASCO [2]'],
        ['Размеры груза w × h × d','28 × 28 × 15 мм','Внешние размеры [2]'],
        ['Расстояние до центра груза a','0,350 м','Выбрано в модели'],
        ['Ускорение g','9,80665 м/с²','Стандартное значение'],
        ['Полувремя амплитуды','30 с','Сценарий малого трения']], [185,133,157])
    body('Стержень считается однородным цилиндром, груз — однородным прямоугольным блоком. Ось проходит через '
         'верхний конец стержня; глубина d направлена вдоль оси. Отверстия и крепёж отдельно не моделируются. '
         'Паспортная масса блока распределена по его внешнему объёму; плотность сплошной латуни не предполагается.')
    body('По определению I = ∫r² dm и теореме Штейнера:')
    equation(r'I_r=m_r\left(\frac{L^2}{3}+\frac{R^2}{4}\right),\quad I_b=m_b\left(a^2+\frac{w^2+h^2}{12}\right)')
    equation(r'I=I_r+I_b,\quad S=m_rL/2+m_ba,\quad l=S/(m_r+m_b),\quad l_{eq}=I/S')
    body(f'Для выбранной конфигурации: I<sub>r</sub> = {p.rod_inertia:.8f} кг·м²; '
         f'I<sub>b</sub> = {p.bob_inertia:.8f} кг·м²; <b>I = {p.inertia:.8f} кг·м²</b>. '
         f'Масса M = {p.mass:.3f} кг, центр масс l = {p.center_of_mass:.6f} м, '
         f'приведённая длина l<sub>eq</sub> = {p.equivalent_length:.6f} м.')
    body('Глубина d не входит в момент инерции относительно выбранной оси при фиксированной массе. '
         'Формулы проверяются независимым численным интегрированием квадрата расстояния по распределению масс. '
         'Дополнительные цифры характеризуют расчёт модели, а не точность паспортных размеров.')

    page(); head('2. Уравнения и теоретические ориентиры')
    body('Угол θ отсчитывается от нижней вертикали; ω = dθ/dt. Момент тяжести равен −gS sin θ, '
         'момент вязкого трения — −bω. Начальные условия опытов: θ(0) = A, ω(0) = 0 [3, 4].')
    equation(r'\dot\theta=\omega,\qquad I\dot\omega=-gS\sin\theta-b\omega')
    equation(r'E=\frac{I\omega^2}{2}+gS(1-\cos\theta),\quad \dot E=-b\omega^2,\quad E+Q=E_0')
    body('Здесь Q(t) = ∫bω²dt — энергия, перешедшая в тепло. Без трения сохраняется E; с трением — E+Q. '
         'При малых углах sin θ ≈ θ и ω₀² = gS/I. Для произвольной амплитуды менее 180° период выводится '
         'из интеграла энергии подстановкой sin(θ/2) = sin(A/2) sin u:')
    equation(r'T_0=2\pi\sqrt{I/(gS)},\qquad T(A)=\frac{4}{\omega_0}K(m),\quad m=\sin^2(A/2)')
    equation(r'K(m)=\int_0^{\pi/2}\frac{du}{\sqrt{1-m\sin^2u}}')
    body('В SciPy ellipk аргументом служит параметр m, а не модуль √m [6]. При A → 0 период стремится к T₀; '
         'при A → 180° он расходится. Точное нелинейное решение для контроля всей траектории:')
    equation(r'\theta(t)=2\arcsin\{k\,\mathrm{sn}[K(k^2)-\omega_0t\mid k^2]\},\quad k=\sin(A/2)')
    body('Для слабого трения β = b/(2I), ω<sub>d</sub> = √(ω₀²−β²). Линейное решение с нулевой начальной скоростью:')
    equation(r'\theta(t)=A e^{-\beta t}\left[\cos(\omega_dt)+\frac{\beta}{\omega_d}\sin(\omega_dt)\right]')
    body('Синусное слагаемое обеспечивает ω(0) = 0. Амплитуда спадает экспоненциально, '
         'T<sub>d</sub> = 2π/ω<sub>d</sub>, время уменьшения амплитуды вдвое τ = ln 2/β. '
         'При больших амплитудах эта линейная формула используется только как предельный ориентир.')

    page(); head('3. Численный метод и воспроизводимость')
    body('Система для (θ, ω, Q) решается методом DOP853 из SciPy solve_ivp [5]. Это явный метод Рунге–Кутты '
         'восьмого порядка с автоматическим выбором шага. Базовые допуски: rtol = 10⁻¹⁰, atol = 10⁻¹² '
         'для величин в СИ. Максимальный шаг T₀/30 позволяет уверенно находить пересечения и экстремумы.')
    body('Период измеряется по интервалам между пересечениями θ = 0 в одном направлении (ω &lt; 0), '
         'а не по расстоянию между соседними отсчётами CSV. Максимумы находятся как события ω = 0 '
         'с переходом от положительной скорости к отрицательной. Сетка вывода не является сеткой интегратора.')
    table(['Опыт','Параметры','Проверка'],[
        ['Свободные колебания','60°; 20T₀','Точное решение; E = const'],
        ['Период и амплитуда','1–170°; 6T(A)','Эллиптический интеграл'],
        ['Затухание','5° и 60°; 60 с','Огибающая; E+Q = const'],
        ['Положение груза','15, 25, 35, 40 см; 5°','Пересчёт I и S'],
        ['Сходимость','120°; 20T(A)','rtol от 10⁻⁴ до 10⁻¹⁰']], [150,150,175])
    body('Относительная невязка энергии определяется как max|E(t)−E₀|/E₀; при трении вместо E берётся E+Q. '
         'Проверяется вся записанная траектория, а не только её последний отсчёт. Невязка периода: |Tчисл/Tтеор−1|.')
    body('<b>Воспроизведение:</b> из корня проекта выполнить установку requirements.txt, затем '
         '<font face="DVB">python -m physical_pendulum --no-show</font>. '
         'Для отчёта: установить requirements-report.txt и выполнить '
         '<font face="DVB">python -m report.build_report</font>. Тесты: '
         '<font face="DVB">python -m unittest discover -s tests -v</font>.')
    body('В report/data сохранены временные ряды, таблицы периодов, положения груза и сходимости, '
         'а также summary.json с исходными параметрами и версиями библиотек. Отчёт собирается из этих же расчётов. '
         'Сборка архива запускает тесты и сохраняет их вывод в report/test-results.txt.')

    page(); head('4. Свободные колебания и энергия')
    chart('free','Рис. 2. Колебания при 60° без трения; расчёт и точное нелинейное решение.',475)
    body(f'Период малых колебаний T₀ = <b>{p.period:.6f} с</b>. При 60° период '
         f'T = {data["periods"][4]["numerical_s"]:.6f} с. Фазовая траектория замкнута; '
         'кинетическая и потенциальная энергии периодически переходят друг в друга.')
    body(f'На интервале 20T₀ относительная невязка полной энергии равна '
         f'<b>{m["free_energy_error"]:.2e}</b>, максимальное расхождение угла с точным нелинейным '
         f'решением — {m["free_exact_angle_error_rad"]:.2e} рад. Видимое совпадение кривых подкреплено количественным сравнением.')
    body('Малое ненулевое изменение E на нижнем правом графике — ошибка интегрирования и интерполяции, '
         'а не физическое затухание. Метод не объявляется точно сохраняющим энергию: допустимость ошибки '
         'проверяется на выбранном интервале и дополнительно исследуется сходимость.')

    page(); head('5. Зависимость периода от амплитуды')
    chart('period','Рис. 3. Нелинейный период и относительная ошибка численного измерения.',475)
    table(['A, град','T числ, с','T теория, с','Рост к T₀, %','Отн. ошибка'],
          [[r['amplitude_deg'],f"{r['numerical_s']:.6f}",f"{r['theory_s']:.6f}",f"{r['excess_percent']:.3f}",f"{r['relative_error']:.2e}"] for r in data['periods']],
          [65,100,100,105,105])
    body('Период увеличивается с амплитудой: на 7,32% при 60° и на 18,03% при 90°. '
         'Около верхнего неустойчивого положения маятник движется медленно, поэтому при приближении к 180° '
         'период резко растёт. 170° — проверка нелинейной модели, не утверждение о доступном ходе реальной стойки.')

    page(); head('6. Малое трение и затухание')
    body(f'Задано τ = 30 с, откуда β = {p.beta:.6f} с⁻¹ и b = {p.damping:.6e} Н·м·с. '
         f'Отношение β/ω₀ = {p.beta/p.frequency:.4f}, добротность ≈ {m["quality_factor"]:.1f}: '
         'это режим слабого затухания. Эти значения — параметры сценария, не измерения производителя.')
    chart('damping','Рис. 4. Затухание при 5° и баланс механической энергии с теплом.',475)
    body(f'По наклону ln A(t) для максимумов получено β = {m["beta_fit_s_inverse"]:.6f} с⁻¹ '
         f'(теория {p.beta:.6f} с⁻¹). Период линейной теории {m["damped_period_linear_s"]:.6f} с; '
         f'средний численный период {m["damped_period_measured_s"]:.6f} с. '
         'Небольшое превышение объясняется конечной амплитудой.')
    body(f'Максимальная разность линейного и нелинейного угла за 60 с — '
         f'{m["damped_linear_max_error_deg"]:.3f}°. Фазовая ошибка накапливается даже при 5°. '
         f'Невязка баланса E+Q равна {m["damped_balance_error"]:.2e}. '
         'Механическая энергия убывает, а сумма с выделившимся теплом сохраняется в пределах погрешности.')

    page(); head('7. Большая амплитуда и прикладной опыт')
    chart('large_damping','Рис. 5. При затухании колебаний с 60° локальный период стремится к малому пределу.',475)
    body(f'Линейная теория не описывает начальный участок при 60°: по мере уменьшения амплитуды '
         f'уменьшается и период. Невязка E+Q за 60 с составляет {m["large_damped_balance_error"]:.2e}.')
    chart('practical','Рис. 6. Перестановка груза и ошибка определения g по формуле малых углов.',475)
    body('При обработке измерений g<sub>est</sub> = 4π²I/(S T²). Если не учитывать амплитуду, '
         f'при 5° получается {data["periods"][1]["inferred_g"]:.4f} м/с² (ошибка около −0,095%), '
         f'а при 60° — {data["periods"][4]["inferred_g"]:.4f} м/с² (около −13,17%). '
         'Практический вывод: измерять при малой амплитуде или вводить нелинейную поправку.')

    page(); head('8. Сходимость и автоматические проверки')
    chart('convergence','Рис. 7. Ужесточение допуска уменьшает ошибки периода, энергии и траектории.',475)
    table(['rtol','Вызовы RHS','Ошибка T','Ошибка E','Ошибка θ, рад'],
          [[f"{r['rtol']:.0e}",r['nfev'],f"{r['relative_period_error']:.2e}",f"{r['energy_error']:.2e}",f"{r['max_angle_error_rad']:.2e}"] for r in data['convergence']],
          [70,90,105,105,105])
    body('В опыте сходимости ограничение шага ослаблено до T₀, чтобы результат зависел от заданного допуска. '
         'Расчёт ведётся 20 периодов при 120°. Уменьшение допуска с 10⁻⁴ до 10⁻¹⁰ снижает ошибку траектории '
         'примерно с 0,088 рад до 5,3·10⁻⁸ рад. Это проверка на независимом точном решении.')
    body('Автотесты проверяют интегральный момент инерции, равновесие, малые углы, периоды до 170°, '
         'полную траекторию, отрицательное отклонение, начальный толчок, диссипацию, полувремя затухания, '
         'несколько положений груза, сходимость и некорректные входные данные. Критерии: ошибка периода '
         '&lt; 2·10⁻⁸, относительная невязка энергии &lt; 10⁻⁸ в контрольных сценариях. '
         'Число и результаты выполненных тестов зафиксированы в test-results.txt внутри архива.')

    page(); head('9. Выводы, ограничения и источники')
    body('1. Момент инерции вычислен по форме составного тела и проверен интегрированием распределения масс. '
         '2. Нелинейные свободные колебания согласуются с точным решением. '
         '3. Период существенно зависит от амплитуды; это даёт измеримую систематическую ошибку в опыте по определению g. '
         '4. Слабое вязкое трение приводит к затуханию, согласованному с линейной теорией при малых углах. '
         '5. Проверены сохранение энергии без трения, её баланс с теплом при трении и численная сходимость.')
    body('<b>Границы применимости.</b> Тело абсолютно жёсткое, ось неподвижна. Не учитываются инерция датчика, '
         'геометрия крепежа, люфты, сухое трение и квадратичное сопротивление воздуха. Паспортные размеры '
         'прибора идеализированы. Полувремя 30 с необходимо заменить измеренным при натурной проверке. '
         'Совпадение с теорией подтверждает численное решение выбранной модели, а не точность воспроизведения реального прибора.')
    body('<b>Как проверить экспериментально.</b> Снять несколько периодов при 5°, измерить положение груза и '
         'его размеры, сравнить оценку g с местным значением. По последовательным максимумам построить ln A(t) '
         'и определить β, затем b = 2Iβ. Если ln A(t) не является прямой, пересмотреть закон трения.')
    sources=[
        ('[1] П. В. Попов. ВШПИ_прог_26-27. Программа дисциплины, 2026, стр. 12–13. Исходный файл предоставлен пользователем.',None),
        ('[2] PASCO. Centripetal Force Pendulum ME-9821. Размеры и массы.', 'https://www.pasco.com/products/lab-apparatus/mechanics/centripetal-force-and-rotation/centripetal-force-pendulum'),
        ('[3] OpenStax. University Physics, §15.4 Pendulums.', 'https://openstax.org/books/university-physics-volume-1/pages/15-4-pendulums'),
        ('[4] OpenStax. §15.5 Damped Oscillations.', 'https://openstax.org/books/university-physics-volume-1/pages/15-5-damped-oscillations'),
        ('[5] SciPy. solve_ivp: DOP853, допуски и события.', 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html'),
        ('[6] SciPy. ellipk: определение K(m).', 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.ellipk.html'),
        ('[7] М3 «Полёт на Марс». Референс организации проекта.', 'https://github.com/kashkovvv/mars-flight')]
    for label,url in sources:
        text=escape(label)
        if url: text+=f' <link href="{url}" color="#24658a">Открыть источник</link>.'
        story.append(Paragraph(text,styles['SmallRu']))
    body('Дата обращения: 03.11.2026. Полные URL и статус параметров приведены в docs/sources.md. '
         'Код, исходные данные, графики и инструкции включены в архив проекта.')
    doc=SimpleDocTemplate(str(OUT/'report.pdf'),pagesize=(595.28,841.89),rightMargin=48,leftMargin=48,
                          topMargin=45,bottomMargin=48,title='М5. Физический маятник',author='Учебный проект М5')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUT/'report.pdf')


if __name__=='__main__': main()
