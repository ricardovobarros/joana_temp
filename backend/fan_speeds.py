# Faixas de potência de cada velocidade do ventilador, medidas pela Shelly Plug M Gen3.
#
# PREENCHER: substitui os valores de exemplo pelos que mediste (ver VENTILADOR.md).
# Cada faixa vale de MÍNIMO (incluído) até MÁXIMO (excluído), em watts.
# Abaixo do mínimo da primeira faixa, o ventilador conta como desligado.
# Uma potência fora de todas as faixas aparece como "Ligado" sem velocidade.
FAN_SPEEDS = [
    # (nome,  mínimo W, máximo W)
    ("V1", 5, 10),
    ("V2", 10, 20),
    ("V3", 20, 35),
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
