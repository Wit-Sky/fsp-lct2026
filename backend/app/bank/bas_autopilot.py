"""bas / autopilot — режимы и параметры ArduPilot/PX4, failsafe, каскад регуляторов.

Черновик: факты вычитывает Евгений (docs/bas_samples.md). Сомнительный шаблон — enabled=False.
Единицы параметров везде указаны в тексте, чтобы ответ не зависел от версии прошивки.
"""
from app.bank._base import template, choice

SPEC, TOPIC = "bas", "autopilot"


@template("bas.autopilot.modes", SPEC, TOPIC, -1.1, "single",
          "Назначение режимов полёта ArduCopter — базовый уровень оператора/разработчика.")
def _modes(rng):
    text, ans = rng.choice([
        ("Вернуться в точку взлёта и сесть.", "RTL"),
        ("Удерживать позицию и высоту по GNSS, пилот может смещать аппарат стиками.", "LOITER"),
        ("Удерживать высоту по барометру без удержания позиции (GNSS не нужен).", "ALT_HOLD"),
        ("Выполнять загруженную миссию по точкам.", "AUTO"),
        ("Принимать целевые точки от компаньон-компьютера или наземной станции в реальном времени.", "GUIDED"),
    ])
    return {"text": "Какой режим ArduCopter подходит? " + text,
            **choice(rng, ans, ["RTL", "LOITER", "ALT_HOLD", "AUTO", "GUIDED", "STABILIZE"])}


@template("bas.autopilot.params", SPEC, TOPIC, -0.4, "single",
          "За что отвечают ключевые параметры ArduCopter.")
def _params(rng):
    text, ans = rng.choice([
        ("RTL_ALT", "высота возврата домой в режиме RTL"),
        ("BATT_CAPACITY", "ёмкость аккумулятора в мА·ч"),
        ("FENCE_ENABLE", "включение геозоны"),
        ("ARMING_CHECK", "набор предполётных проверок перед армингом"),
        ("WPNAV_SPEED", "горизонтальная скорость полёта между точками миссии"),
    ])
    return {"text": f"За что отвечает параметр ArduCopter {text}?",
            **choice(rng, ans, ["высота возврата домой в режиме RTL", "ёмкость аккумулятора в мА·ч", "включение геозоны",
                                "набор предполётных проверок перед армингом", "горизонтальная скорость полёта между точками миссии"])}


@template("bas.autopilot.leg_time", SPEC, TOPIC, 0.2, "number",
          "Время прохождения участка по скорости из параметра в см/с — внимательность к единицам.")
def _leg(rng):
    v = rng.randint(8, 40) * 50
    t = rng.randint(2, 12) * 10
    return {"text": f"Скорость полёта по миссии WPNAV_SPEED = {v} (см/с). Сколько секунд займёт прямой участок длиной {v * t // 100} м "
                    f"(разгоном и торможением пренебречь)?", "answer": t}


@template("bas.autopilot.battery_time", SPEC, TOPIC, 0.6, "number",
          "Оценка времени полёта по ёмкости, току и резерву — практический расчёт.")
def _battery(rng):
    c = rng.choice([3000, 4000, 5000, 6000, 8000, 10000, 12000, 16000, 22000])
    i = rng.choice([8, 10, 12, 15, 18, 20, 25, 30])
    r = rng.choice([20, 25, 30])
    t = c * (100 - r) * 60 // (1000 * 100 * i)          # целочисленно, без ошибок округления float
    return {"text": f"Аккумулятор {c} мА·ч, средний ток в полёте {i} А, резерв на посадку {r} % ёмкости. "
                    f"Сколько полных минут можно лететь до начала посадки? (округлите вниз)", "answer": t}


@template("bas.autopilot.failsafe", SPEC, TOPIC, 1.1, "single",
          "Какой параметр задаёт реакцию на конкретный отказ — знание failsafe ArduCopter.")
def _failsafe(rng):
    text, ans = rng.choice([
        ("потеря сигнала пульта (RC)", "FS_THR_ENABLE"),
        ("потеря связи с наземной станцией", "FS_GCS_ENABLE"),
        ("низкий заряд батареи", "BATT_FS_LOW_ACT"),
        ("отказ/расхождение навигационного фильтра EKF", "FS_EKF_ACTION"),
    ])
    return {"text": f"Какой параметр ArduCopter задаёт действие при событии «{text}»?",
            **choice(rng, ans, ["FS_THR_ENABLE", "FS_GCS_ENABLE", "BATT_FS_LOW_ACT", "FS_EKF_ACTION", "FENCE_ACTION"])}


@template("bas.autopilot.cascade", SPEC, TOPIC, 1.5, "order",
          "Порядок контуров каскадного регулятора мультикоптера или этапов запуска миссии — понимание архитектуры.")
def _cascade(rng):
    if rng.random() < 0.5:
        steps = ["контур позиции", "контур скорости", "контур угла (attitude)", "контур угловой скорости (rate)", "микшер моторов"]
        text = "Расположите контуры каскадного регулятора мультикоптера от внешнего к внутреннему (по пути сигнала)."
    else:
        steps = ["загрузить миссию в автопилот", "пройти pre-arm проверки", "арминг", "переключить в AUTO и взлететь по миссии",
                 "возврат RTL и посадка"]
        text = "Расположите этапы автоматического полёта по миссии ArduCopter в правильном порядке."
    return {"text": text, "options": steps, "answer": steps}
