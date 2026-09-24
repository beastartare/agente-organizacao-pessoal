from agent.memory import (save_message, save_pending_plan, get_pending_plan, clear_pending_plan)
from agent.llm import generate_response
from agent.tools import (validate_proposed_events, get_recurring_events_for_period, create_missing_recurring_events, create_event)

import json
import re

# função para processar a entrada do usuário e gerar a resposta do agente
def process_user_input(user_input):

    # Salva a mensagem do usuário no histórico
    save_message(
        "user_input",
        {
            "content": [
                {
                    "type": "text",
                    "text": user_input
                }
            ]
        }
    )

    # Verifica se existe uma proposta aguardando confirmação
    pending_plan = get_pending_plan()

    if pending_plan:

        normalized = user_input.lower().strip()

        # se a resposta para o plano perdente for uma confirmação -> fluxo de geração de eventos
        if normalized in [
            "sim",
            "s",
            "pode",
            "pode criar",
            "confirmo",
            "confirmar"
        ]:

            #busca os compromissos fixos
            fixed_events = pending_plan.get(
                "fixed_events",
                []
            )

            #busca os novos compromissos
            new_events = pending_plan.get(
                "new_events",
                []
            )

            # valida se há conflito de horarios
            conflicts = validate_proposed_events(
                new_events
            )

            # cancela o planejamento
            if conflicts:

                clear_pending_plan()

                conflict_lines = []

                for conflict in conflicts:

                    conflict_lines.append(
                        f"- {conflict['proposed_event']} "
                        f"conflita com "
                        f"{conflict['conflict_with']} "
                        f"({conflict['start']} até "
                        f"{conflict['end']})."
                    )

                return (
                    "Não criei os eventos porque detectei "
                    "conflitos com compromissos existentes "
                    "ou com sua rotina:\n\n"
                    + "\n".join(conflict_lines)
                    + "\n\nO cronograma pendente foi cancelado."
                )

            # verifica quais compromissos fixos ainda não estão no Google Calendar
            created_fixed = (
                create_missing_recurring_events(
                    fixed_events
                )
            )

            # lista para armazenar os eventos efetivamente criados
            created_new = []

            for event in new_events:

                # envia os dados do eventos para a função que cria os eventos
                result = create_event(
                    **event
                )

                # armazena os resultados dessa criação
                created_new.append(
                    result
                )

            # Remove a proposta após criar os eventos
            clear_pending_plan()

            # resposta ao usuário
            total_created = (
                len(created_fixed)
                + len(created_new)
            )

            if total_created == 0:

                return (
                    "Os compromissos e tarefas do "
                    "cronograma já estavam registrados "
                    "no Google Calendar."
                )

            created_lines = []

            for event in created_fixed:

                created_lines.append(
                    f"- {event['title']} | "
                    f"{event['start']} até "
                    f"{event['end']}"
                )

            for event in created_new:

                created_lines.append(
                    f"- {event}"
                )

            return (
                "Cronograma criado com sucesso "
                "no Google Calendar:\n\n"
                + "\n".join(created_lines)
            )

        if normalized in [
            "não",
            "nao",
            "n",
            "cancelar",
            "cancela"
        ]:

            # Remove a proposta sem criar os eventos
            clear_pending_plan()

            return (
                "Tudo bem. O cronograma não foi criado."
            )

        return (
            "Tenho um cronograma aguardando confirmação. "
            "Responda 'sim' para criar os eventos "
            "ou 'não' para cancelar."
        )

    response = generate_response(
        user_input
    )

    if response is None:

        return (
            "Desculpe, não consegui gerar uma resposta. "
            "Por favor, tente novamente."
        )

    # Verifica se o Gemini propôs algum evento
    clean_response, new_events = extract_event_proposal(
        response
    )

    # lista para os eventos fixos
    fixed_events = []

    if new_events:

        #detecta o periodo do planejamento (ex: hoje, amanha, na semana..)
        period = detect_period_from_response(
            response
        )

        #busco os eventos fixos para aquele periodo
        fixed_events = get_recurring_events_for_period(
            period
        )

        #verifica  se há conflitos
        conflicts = validate_proposed_events(
            new_events
        )

        if conflicts:

            conflict_lines = []

            for conflict in conflicts:

                conflict_lines.append(
                    f"- {conflict['proposed_event']} "
                    f"conflita com "
                    f"{conflict['conflict_with']} "
                    f"({conflict['start']} até "
                    f"{conflict['end']})."
                )

            return (
                clean_response
                + "\n\nNão posso propor esses eventos "
                "porque detectei conflitos com "
                "compromissos existentes ou com sua rotina:\n\n"
                + "\n".join(conflict_lines)
                + "\n\nNenhum evento foi salvo para aprovação."
            )

        #se não houver, cria o plano pendente
        save_pending_plan(
            {
                "fixed_events": fixed_events,
                "new_events": new_events
            }
        )

    #retorna a resposta
    return clean_response 


# função para buscar o periodo de planejamento
def detect_period_from_response(response):

    text = response.lower()

    if (
        "próxima semana" in text
        or "proxima semana" in text
    ):
        return "next_week"

    if (
        "esta semana" in text
        or "essa semana" in text
    ):
        return "this_week"

    if "amanhã" in text or "amanha" in text:
        return "tomorrow"

    if "hoje" in text:
        return "today"

    return "this_week"


# função para extrair os eventos propostos pelo Gemini
def extract_event_proposal(response):

    pattern = (
        r"\[ORBiA_EVENTS\](.*?)"
        r"\[/ORBiA_EVENTS\]"
    )

    match = re.search(
        pattern,
        response,
        re.DOTALL
    )

    # Se não existe uma proposta de evento
    if not match:

        return response, []

    json_content = match.group(
        1
    ).strip()

    try:

        events = json.loads(
            json_content
        )

    except json.JSONDecodeError:

        print(
            "[Orbia] Não foi possível interpretar "
            "a proposta."
        )

        return response, []

    # Verifica se o Gemini realmente retornou uma lista
    if not isinstance(events, list):

        return response, []

    valid_events = []

    for event in events:

        if not isinstance(event, dict):

            continue

        required_fields = [
            "title",
            "start_datetime",
            "end_datetime"
        ]

        # Verifica se o evento possui os dados necessários
        if not all(
            field in event
            for field in required_fields
        ):

            continue

        valid_events.append({
            "title": event["title"],
            "start_datetime": event[
                "start_datetime"
            ],
            "end_datetime": event[
                "end_datetime"
            ],
            "description": event.get(
                "description",
                ""
            )
        })

    # Remove o bloco técnico da resposta que será mostrada ao usuário
    clean_response = (
        response[:match.start()]
        + response[match.end():]
    ).strip()

    if valid_events:

        clean_response += (
            "\n\nDeseja que eu crie esses eventos "
            "e os compromissos fixos no seu "
            "Google Calendar?"
        )

    return clean_response, valid_events