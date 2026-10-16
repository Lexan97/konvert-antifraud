"""Пороги детекторов. Вынесены отдельно, чтобы оператор мог их настраивать и видеть явно.

Значения выведены из описания сценариев в ТЗ и проверены на выгрузке за 01–05.10.2026:
у каждой схемы есть запас по каждому порогу, а легитимные источники отсекаются
отдельными признаками (время работы, входящие, повторные контакты, структура номеров B).
"""

# S1 Wangiri: сотни вызовов-сбросов за несколько часов
WANGIRI_MIN_CALLS = 100
WANGIRI_MIN_SHORT = 0.8          # доля вызовов ≤ 2 с
WANGIRI_MAX_SPAN_H = 12

# S2 Робот: перебор подряд идущих номеров
ROBOT_MIN_CALLS = 100
ROBOT_MAX_SPAN_H = 4
ROBOT_MAX_STEP = 5               # медианный шаг между соседними набранными номерами
ROBOT_GROUP_DENSITY = 0.8        # у группы номеров диапазон покрыт почти без пропусков

# S3 SIM-box: только исходящие, всегда новый абонент, вызовы встык
SIMBOX_MIN_CALLS = 50
SIMBOX_MIN_UNIQUE = 0.98
SIMBOX_MAX_IN_SHARE = 0.03       # входящих не больше 3% от исходящих (у обычного абонента — десятки %)
SIMBOX_MAX_ZERO = 0.02
SIMBOX_MAX_MEDIAN_DUR = 300
SIMBOX_MIN_SPAN_H = 8
SIMBOX_MIN_NO_OVERLAP = 0.95

# S4 Клон SIM
CLONE_MIN_IMSI = 3

# S5 Цепочка переадресаций
CHAIN_STEP_S = 2                 # звенья одной цепочки идут с шагом ≤ 2 с
CHAIN_MIN_LINKS = 2              # минимум 2 переадресации подряд (B→C→D)

# S6 Карусель
CAROUSEL_MAX_DEGREE = 12
CAROUSEL_MIN_CALLS = 50
CAROUSEL_MIN_SIZE = 3
CAROUSEL_MAX_SIZE = 15
CAROUSEL_MIN_CLOSED = 0.95

# S7 Вишинг со спуфингом
VISH_MIN_CALLS = 8
VISH_LONG_MIN_S = 360
VISH_LONG_MAX_S = 1800
VISH_MIN_LONG_SHARE = 0.8
VISH_WINDOW_H = 12               # «прогрев» жертвы — в пределах 12 ч до звонка мошенника
VISH_SPOOF_MAX_DUR = 15
VISH_SPOOF_MIN_VICTIMS = 2

# Легитимные источники
LEGIT_MIN_CALLS = 100
HOTLINE_MIN_FWD = 100

# Решение
ANSWER_MIN_SCORE = 60            # номер попадает в ответ, если балл схемы ≥ порога
AUTOBLOCK_MIN_SCORE = 90

# Белый список оператора: номера, которые не блокируются никогда — банки, госслужбы, свои
# корпоративные клиенты. Файл: один номер на строку, пустые строки и строки с # игнорируются.
# Экстренные номера (112, 101–104) в файл класть не нужно, они зашиты в numbering.EMERGENCY.
WHITELIST_FILE = "data/whitelist.txt"

# Раннее обнаружение скользящим окном (konvert.early). Размеры окон — наименьшие,
# при которых на всей выгрузке нет ни одной ложной тревоги.
EARLY_WANGIRI_WINDOW = 20
EARLY_WANGIRI_SHARE = 0.9
EARLY_ROBOT_WINDOW = 10
EARLY_ROBOT_RANGE = 100

# Второй контур — модель CatBoost (konvert.ml)
ML_MIN_CALLS = 20                # модель оценивает номера, у которых есть хотя бы 20 исходящих
ML_THRESHOLD = 0.5
