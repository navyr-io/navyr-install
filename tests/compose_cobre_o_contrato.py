#!/usr/bin/env python3
"""Catraca: o compose distribuído entrega o que o contrato declara.

Este repositório é a TERCEIRA descrição da mesma plataforma — depois do
docker-compose interno e do chart Helm. A ADR 0006 removeu a segunda tentativa
disso (Kustomize) porque três descrições divergiram em direções opostas, e
depois as duas restantes divergiram de novo: 15 variáveis que o código lê
estavam numa e ausentes na outra.

Um instalador escrito à mão repetiria o padrão. Então ele não é escrito à mão:
`contrato/plataforma.yaml` é a descrição, e este teste reprova quando o compose
daqui deixa de cobri-la.
"""
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / "contrato" / "plataforma.yaml"
COMPOSE = RAIZ / "docker-compose.yml"

# Variáveis que o contrato declara e que NÃO pertencem ao caminho de instalação,
# cada uma com motivo. Sem justificativa a catraca vira decoração.
FORA_DO_INSTALADOR = {
    "AUTH_EXPOSE_RESET_TOKEN":  "override de desenvolvimento; expõe token de reset na resposta",
    "AUTH_EXPOSE_INVITE_TOKEN": "override de desenvolvimento; expõe token de convite na resposta",
}


def main() -> int:
    if not CONTRATO.exists():
        print(f"FALHA: {CONTRATO.name} não existe — sem contrato não há o que verificar")
        return 1

    contrato = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))

    servicos_contrato = set(contrato["topologia"]["servicos"])
    servicos_compose = set((compose.get("services") or {}).keys())

    problemas = []
    for s in sorted(servicos_contrato - servicos_compose):
        problemas.append(f"serviço {s} está no contrato e o instalador não o entrega")
    for s in sorted(servicos_compose - servicos_contrato):
        problemas.append(f"serviço {s} está no instalador e não no contrato")

    entregues = set()
    for s in (compose.get("services") or {}).values():
        env = s.get("environment") or {}
        entregues |= set(env.keys() if isinstance(env, dict)
                         else [x.split("=")[0] for x in env])

    # A regra é a SUPERFÍCIE CONFIGURÁVEL, não tudo que o código lê. Das 72
    # variáveis lidas, a maioria tem default e é botão de ajuste; o que todo
    # empacotamento precisa entregar é o subconjunto que o contrato marca como
    # configurável. É o mesmo critério que o chart Helm já usa.
    for var in contrato["superficie_configuravel"]:
        if var in entregues or var in FORA_DO_INSTALADOR:
            continue
        servicos = contrato["variaveis"].get(var, [])
        problemas.append(
            f"variável {var} é configurável (lida por {', '.join(servicos)}) "
            f"e o instalador não a entrega")

    # Contrapeso: as excluídas não podem estar vazando para o instalador.
    for var in FORA_DO_INSTALADOR:
        if var in entregues:
            problemas.append(
                f"variável {var} está marcada como fora do instalador e mesmo "
                f"assim é entregue — {FORA_DO_INSTALADOR[var]}")

    if problemas:
        print(f"FALHA: o instalador não cobre o contrato ({len(problemas)}):\n")
        for p in problemas:
            print(f"  - {p}")
        return 1

    n = len([v for v in contrato["superficie_configuravel"] if v not in FORA_DO_INSTALADOR])
    print(f"ok: {len(servicos_compose)} serviços e {n} variáveis configuráveis "
          f"chegam ao instalador; {len(FORA_DO_INSTALADOR)} fora por decisão registrada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
