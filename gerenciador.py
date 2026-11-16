"""Gerenciador de Tarefas simples.

Como usar: python gerenciador.py
As tarefas ficam salvas no arquivo tarefas.json (na mesma pasta deste arquivo).
"""
import json
import shutil
import textwrap
from datetime import date
from itertools import zip_longest
from pathlib import Path

ARQUIVO = Path(__file__).with_name("tarefas.json")
PRIORIDADES = {"1": "alta", "2": "média", "3": "baixa"}
ORDEM_PRIORIDADE = {"alta": 0, "média": 1, "baixa": 2}
# Largura das colunas fixas: Nº(3) Feita(5) Prior.(6) Vencimento(10) Situação(9), com 2 espaços entre elas
FIXO = 3 + 2 + 5 + 2 + 6 + 2 + 10 + 2 + 9 + 2


# ---------------------------------------------------------------- dados
def carregar():
    if not ARQUIVO.exists():
        return []
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = ARQUIVO.with_suffix(".json.bak")
        ARQUIVO.replace(backup)
        print(f"Aviso: o arquivo estava corrompido. Cópia guardada em {backup.name}.")
        return []


def salvar(tarefas):
    ARQUIVO.write_text(json.dumps(tarefas, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- entradas
def ler_data(texto):
    """Aceita DD/MM, DD/MM/AA ou DD/MM/AAAA (também com - ou .). Retorna a data ou None."""
    partes = texto.strip().replace("-", "/").replace(".", "/").split("/")
    if len(partes) not in (2, 3) or not all(p.isdigit() for p in partes):
        return None
    dia, mes = int(partes[0]), int(partes[1])
    ano = date.today().year
    if len(partes) == 3:
        ano = int(partes[2])
        if ano < 100:
            ano += 2000
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def pedir_prioridade(padrao="média"):
    while True:
        valor = input(f"Prioridade: 1=alta 2=média 3=baixa (Enter = {padrao}): ").strip()
        if not valor:
            return padrao
        if valor in PRIORIDADES:
            return PRIORIDADES[valor]
        print("  Digite 1, 2 ou 3.")


def pedir_data(atual=None):
    """Enter mantém o valor atual (ou 'sem data'); '-' remove a data."""
    dica = "Enter = manter, - = remover" if atual else "Enter = sem data"
    while True:
        valor = input(f"Vencimento DD/MM/AAAA ou DD/MM ({dica}): ").strip()
        if not valor:
            return atual
        if valor == "-":
            return None
        data = ler_data(valor)
        if data:
            return data.isoformat()
        print("  Data inválida. Exemplo: 25/12/2026 ou 25/12.")


def pedir_obs(atual=""):
    """Observação opcional. Enter mantém o valor atual; '-' apaga."""
    dica = "Enter = manter, - = apagar" if atual else "Enter = nenhuma"
    valor = input(f"Observação ({dica}): ").strip()
    if not valor:
        return atual
    return "" if valor == "-" else valor


def escolher_tarefa(tarefas):
    """Pede o número da tarefa; repete se errar. Enter cancela."""
    while True:
        valor = input("Número da tarefa (Enter cancela): ").strip()
        if not valor:
            return None
        if valor.isdigit():
            for tarefa in tarefas:
                if tarefa["id"] == int(valor):
                    return tarefa
        print("  Não encontrei essa tarefa. Veja o número na lista.")


# ---------------------------------------------------------------- tela
def atrasada(tarefa, hoje):
    return bool(tarefa["vencimento"]) and not tarefa["feita"] and date.fromisoformat(tarefa["vencimento"]) < hoje


def vence_hoje(tarefa, hoje):
    return bool(tarefa["vencimento"]) and not tarefa["feita"] and date.fromisoformat(tarefa["vencimento"]) == hoje


def medidas():
    """Largura total da tabela e das colunas Título e Obs, ajustadas ao tamanho do terminal."""
    total = max(70, min(shutil.get_terminal_size((80, 24)).columns - 1, 110))
    disponivel = total - FIXO - 2
    larg_titulo = disponivel * 55 // 100
    return total, larg_titulo, disponivel - larg_titulo


def cabecalho(larg_titulo):
    return (
        f"{'Nº':>3}  {'Feita':^5}  {'Prior.':<6}  {'Vencimento':<10}  {'Situação':<9}  "
        f"{'Título':<{larg_titulo}}  Obs"
    )


def linhas_tarefa(tarefa, hoje, larg_titulo, larg_obs):
    """Uma tarefa em colunas; títulos e observações longos continuam na linha de baixo."""
    venc = date.fromisoformat(tarefa["vencimento"]).strftime("%d/%m/%Y") if tarefa["vencimento"] else "--"
    if atrasada(tarefa, hoje):
        situacao = "VENCIDA!"
    elif vence_hoje(tarefa, hoje):
        situacao = "HOJE"
    else:
        situacao = ""
    marca = "[x]" if tarefa["feita"] else "[ ]"
    titulo = textwrap.wrap(tarefa["titulo"], larg_titulo) or [""]
    obs = textwrap.wrap(tarefa.get("obs", ""), larg_obs) or [""]
    linhas = []
    for i, (parte_titulo, parte_obs) in enumerate(zip_longest(titulo, obs, fillvalue="")):
        if i == 0:
            inicio = f"{tarefa['id']:>3}  {marca:^5}  {tarefa['prioridade']:<6}  {venc:<10}  {situacao:<9}  "
        else:
            inicio = " " * FIXO
        linhas.append(f"{inicio}{parte_titulo:<{larg_titulo}}  {parte_obs}".rstrip())
    return linhas


def avisar_pendencias(tarefas):
    """Alerta em destaque sobre tarefas vencidas e que vencem hoje."""
    hoje = date.today()
    vencidas = [t for t in tarefas if atrasada(t, hoje)]
    de_hoje = [t for t in tarefas if vence_hoje(t, hoje)]
    if vencidas:
        print(f"\n!!! ATENÇÃO: você tem {len(vencidas)} tarefa(s) VENCIDA(S):")
        for t in vencidas:
            dias = (hoje - date.fromisoformat(t["vencimento"])).days
            print(f"    - Nº {t['id']} {t['titulo']} (venceu há {dias} dia(s))")
    if de_hoje:
        print(f"\n!!  Vence(m) HOJE: " + ", ".join(f"Nº {t['id']} {t['titulo']}" for t in de_hoje))


def mostrar(tarefas):
    hoje = date.today()
    total, larg_titulo, larg_obs = medidas()
    print("\n" + "=" * total)
    print(cabecalho(larg_titulo))
    print("-" * total)
    if not tarefas:
        print("  (nenhuma tarefa ainda)")
    ordenadas = sorted(
        tarefas,
        key=lambda t: (t["feita"], t["vencimento"] is None, t["vencimento"] or "", ORDEM_PRIORIDADE[t["prioridade"]]),
    )
    for tarefa in ordenadas:
        print("\n".join(linhas_tarefa(tarefa, hoje, larg_titulo, larg_obs)))
    print("=" * total)
    vencidas = sum(1 for t in tarefas if atrasada(t, hoje))
    if vencidas:
        print(f"!!! {vencidas} tarefa(s) vencida(s) - veja as marcadas com VENCIDA!")
    print()


# ---------------------------------------------------------------- ações
def adicionar(tarefas):
    titulo = input("Título da tarefa (Enter cancela): ").strip()
    if not titulo:
        print("Cancelado.")
        return
    obs = pedir_obs()
    prioridade = pedir_prioridade()
    vencimento = pedir_data()
    novo_id = max((t["id"] for t in tarefas), default=0) + 1
    tarefa = {"id": novo_id, "titulo": titulo, "prioridade": prioridade, "vencimento": vencimento, "obs": obs, "feita": False}
    tarefas.append(tarefa)
    salvar(tarefas)
    print("Tarefa adicionada!")
    if atrasada(tarefa, date.today()):
        print("!!! Atenção: essa data já passou, a tarefa foi criada como VENCIDA.")


def alternar_conclusao(tarefas):
    tarefa = escolher_tarefa(tarefas)
    if tarefa:
        tarefa["feita"] = not tarefa["feita"]
        salvar(tarefas)
        print("Tarefa concluída!" if tarefa["feita"] else "Tarefa reaberta.")


def editar(tarefas):
    tarefa = escolher_tarefa(tarefas)
    if not tarefa:
        return
    while True:  # continua editando até o usuário voltar, então dá para corrigir vários campos
        print("\nEditando esta tarefa:")
        _, larg_titulo, larg_obs = medidas()
        print(cabecalho(larg_titulo))
        print("\n".join(linhas_tarefa(tarefa, date.today(), larg_titulo, larg_obs)))
        escolha = input("O que mudar? 1=título 2=observação 3=prioridade 4=vencimento 0=voltar: ").strip()
        if escolha == "1":
            novo = input("Novo título (Enter mantém): ").strip()
            if novo:
                tarefa["titulo"] = novo
        elif escolha == "2":
            tarefa["obs"] = pedir_obs(tarefa.get("obs", ""))
        elif escolha == "3":
            tarefa["prioridade"] = pedir_prioridade(tarefa["prioridade"])
        elif escolha == "4":
            tarefa["vencimento"] = pedir_data(tarefa["vencimento"])
        elif escolha == "0":
            break
        else:
            print("  Digite 1, 2, 3, 4 ou 0.")
            continue
        salvar(tarefas)
        print("Salvo.")
        if atrasada(tarefa, date.today()):
            print("!!! Atenção: essa tarefa está VENCIDA.")


def excluir(tarefas):
    tarefa = escolher_tarefa(tarefas)
    if tarefa and input(f"Excluir '{tarefa['titulo']}'? (s/n): ").strip().lower() == "s":
        tarefas.remove(tarefa)
        salvar(tarefas)
        print("Tarefa excluída.")
    elif tarefa:
        print("Nada foi excluído.")


# ---------------------------------------------------------------- programa
def main():
    tarefas = carregar()
    acoes = {"1": adicionar, "2": alternar_conclusao, "3": editar, "4": excluir}
    print("GERENCIADOR DE TAREFAS")
    avisar_pendencias(tarefas)
    try:
        while True:
            mostrar(tarefas)
            print("1) Adicionar   2) Concluir/reabrir   3) Editar   4) Excluir   0) Sair")
            escolha = input("Escolha: ").strip()
            if escolha == "0":
                break
            acao = acoes.get(escolha)
            if acao:
                acao(tarefas)
            else:
                print("Opção inválida. Digite um número do menu.")
    except (KeyboardInterrupt, EOFError):
        print()
    print("Até logo! Suas tarefas foram salvas.")


if __name__ == "__main__":
    main()
