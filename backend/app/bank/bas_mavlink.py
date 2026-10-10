"""bas / mavlink — сообщения, поля и единицы, частоты, размер кадра, загрузка канала.

Черновик: факты вычитывает Евгений (docs/bas_samples.md). Сомнительный шаблон — enabled=False.
"""
from app.bank._base import template, choice

SPEC, TOPIC = "bas", "mavlink"


@template("bas.mavlink.message_id", SPEC, TOPIC, -1.2, "single",
          "Назначение основных сообщений MAVLink (common.xml) — базовый уровень.")
def _message_id(rng):
    text, ans = rng.choice([
        ("Какое сообщение раз в секунду сообщает тип аппарата, автопилот и режим и служит признаком «аппарат на связи»?", "HEARTBEAT"),
        ("Какое сообщение передаёт отфильтрованную позицию: широту, долготу, высоту и скорости (lat/lon в degE7)?", "GLOBAL_POSITION_INT"),
        ("Какое сообщение передаёт крен, тангаж и рыскание в радианах?", "ATTITUDE"),
        ("Каким сообщением наземная станция отправляет команду (например, MAV_CMD_NAV_TAKEOFF) с 7 параметрами?", "COMMAND_LONG"),
    ])
    return {"text": text, **choice(rng, ans, ["HEARTBEAT", "GLOBAL_POSITION_INT", "ATTITUDE", "COMMAND_LONG", "SYS_STATUS", "VFR_HUD"])}


@template("bas.mavlink.degE7", SPEC, TOPIC, -0.5, "number",
          "Перевод lat из degE7 в градусы — частая операция при разборе телеметрии.")
def _dege7(rng):
    lat = rng.randint(430000, 690000) * 1000 + rng.choice([0, 500])
    return {"text": f"В GLOBAL_POSITION_INT пришло lat = {lat} (единицы degE7). Чему равна широта в градусах? (ответ числом, точка или запятая)",
            "answer": lat / 1e7}


@template("bas.mavlink.interval", SPEC, TOPIC, 0.1, "number",
          "MAV_CMD_SET_MESSAGE_INTERVAL: интервал задаётся в микросекундах — проверка внимательности к единицам.")
def _interval(rng):
    msg = rng.choice(["ATTITUDE", "GLOBAL_POSITION_INT", "VFR_HUD", "SYS_STATUS", "GPS_RAW_INT", "LOCAL_POSITION_NED",
                      "RAW_IMU", "SCALED_PRESSURE", "BATTERY_STATUS", "RC_CHANNELS", "SERVO_OUTPUT_RAW", "ATTITUDE_QUATERNION"])
    hz = rng.choice([1, 2, 4, 5, 8, 10, 16, 20, 25, 40, 50, 100])
    if rng.random() < 0.5:
        return {"text": f"Нужно получать {msg} с частотой {hz} Гц. Какое значение param2 (интервал в микросекундах) "
                        f"передать в MAV_CMD_SET_MESSAGE_INTERVAL?", "answer": 1_000_000 // hz}
    return {"text": f"Автопилоту отправили MAV_CMD_SET_MESSAGE_INTERVAL для {msg} с param2 = {1_000_000 // hz}. "
                    f"С какой частотой (Гц) будет приходить сообщение?", "answer": hz}


@template("bas.mavlink.ground_speed", SPEC, TOPIC, 0.6, "number",
          "vx, vy в GLOBAL_POSITION_INT — в см/с; надо перевести и сложить векторно.")
def _ground_speed(rng):
    a, b, c = rng.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (12, 35, 37), (9, 40, 41)])
    m = rng.choice([x for x in range(1, 41) if c * x <= 400])          # скорость c·m/10 м/с, не больше 40
    vx, vy, v = a * m * 10, b * m * 10, c * m / 10
    if rng.random() < 0.5:
        vx, vy = vy, vx
    sx, sy = rng.choice([1, -1]), rng.choice([1, -1])
    return {"text": f"В GLOBAL_POSITION_INT пришло vx = {sx * vx}, vy = {sy * vy} (см/с). Какова горизонтальная путевая скорость в м/с?",
            "answer": v}


@template("bas.mavlink.frame_size", SPEC, TOPIC, 1.2, "number",
          "Структура кадра MAVLink 2: 10 байт заголовка + payload + 2 байта CRC (+13 подпись).")
def _frame(rng):
    payload = rng.randint(9, 255)                     # payload MAVLink 2 — до 255 байт
    signed = rng.random() < 0.4
    return {"text": f"Кадр MAVLink 2 с полезной нагрузкой {payload} байт (уже после усечения нулей), "
                    f"{'с подписью (signing)' if signed else 'без подписи'}. Сколько байт займёт кадр целиком?",
            "answer": payload + 12 + (13 if signed else 0)}


@template("bas.mavlink.link_budget", SPEC, TOPIC, 1.5, "number",
          "Загрузка телеметрийного канала: 8N1 = 10 бит на байт — senior-уровень расчёта канала.")
def _link(rng):
    baud = rng.choice([9600, 19200, 38400, 57600, 115200])
    size = rng.randint(20, 120)
    return {"text": f"Телеметрийный радиоканал UART {baud} бод, формат 8N1, других сообщений нет. Кадр сообщения — {size} байт. "
                    f"Какое максимальное целое число таких сообщений в секунду пропустит канал?",
            "answer": (baud // 10) // size}
