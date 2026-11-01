# Faixas de potência de cada velocidade do ventilador, medidas pela Shelly Plug M Gen3.
#
# Medições: V1 3.3 W, V2 6.8 W, V3 8.2 W, V4 9.3 W, V5 11.3 W, V6 13.8 W, V7 15.4 W.
# O limite entre duas velocidades fica a meio das duas medições.
# Cada faixa vale de MÍNIMO (incluído) até MÁXIMO (excluído), em watts.
# Abaixo de 1.7 W o ventilador conta como desligado.
# De 16.2 W para cima é V8, sem limite superior.
FAN_SPEEDS = [
    # (nome,  mínimo W, máximo W)
    ("V1", 1.7, 5.1),
    ("V2", 5.1, 7.5),
    ("V3", 7.5, 8.8),
    ("V4", 8.8, 10.3),
    ("V5", 10.3, 12.6),
    ("V6", 12.6, 14.6),
    ("V7", 14.6, 16.2),
    ("V8", 16.2, float("inf")),
]


def classify(watts):
    """Devolve (estado, velocidade) para uma potência em watts."""
    if watts is None:
        return "unknown", None
    if watts < min(low for _, low, _ in FAN_SPEEDS):
        return "off", None
    for name, low, high in FAN_SPEEDS:
        if low <= watts < high:
            return "on", name
    return "on", None
