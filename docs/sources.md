# Источники и происхождение параметров

Дата обращения к веб-источникам: 3 ноября 2026 года.

1. «ВШПИ_прог_26-27», программа дисциплины «Цифровизация физических процессов»,
   составитель П. В. Попов, 2026. М5 — стр. 12–13; М3 — стр. 12.
   Исходный файл пользователя: /home/anderrated/work/literature/ВШПИ_прог_26-27.pdf.
   Требование: только основная часть М5. Текст обязательных пунктов пересказан в README.
2. PASCO, Centripetal Force Pendulum ME-9821:
   https://www.pasco.com/products/lab-apparatus/mechanics/centripetal-force-and-rotation/centripetal-force-pendulum
   Паспортные данные: стержень 41.7 см, диаметр 4 мм, масса 0.001 кг;
   груз 100 г, внешние размеры 2.8 × 2.8 × 1.5 см. Не приводятся данные о трении.
3. OpenStax, University Physics Volume 1, §15.4 Pendulums:
   https://openstax.org/books/university-physics-volume-1/pages/15-4-pendulums
   Уравнение моментов, физический маятник, период малых колебаний.
4. OpenStax, §15.5 Damped Oscillations:
   https://openstax.org/books/university-physics-volume-1/pages/15-5-damped-oscillations
   Линейное вязкое сопротивление и экспоненциальное затухание.
5. SciPy, solve_ivp:
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
   DOP853, управление допусками, нахождение событий.
6. SciPy, ellipk:
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.ellipk.html
   Определение полного эллиптического интеграла с параметром m=k².
7. Референс структуры: https://github.com/kashkovvv/mars-flight .
   Расчёты маятника и текст отчёта написаны для М5, без переноса физики М3.

Выбранные параметры, не являющиеся измерениями: a=0.350 м; g=9.80665 м/с²
(стандартное значение, не местное измерение); время полузатухания 30 с;
идеальная форма и ориентация блока; ось на конце стержня. Размеры и массы
не имеют заявленной здесь погрешности: дополнительные цифры результатов
характеризуют математическую модель, а не точность паспортных данных.
