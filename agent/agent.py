from agent.memory import save_message, save_pending_plan, get_pending_plan, clear_pending_plan
from agent.llm import generate_response

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

        if normalized in [
            "sim",
            "s",
            "pode",
            "pode criar",
            "confirmo",
            "confirmar"
        ]:

            from agent.tools import create_event

            # Cria os eventos da proposta
            created_events = []

            for event in pending_plan:

                result = create_event(**event)

                created_events.append(result)

            # Remove a proposta após criar os eventos
            clear_pending_plan()

            if len(created_events) == 1:

                return (
                    "Evento criado com sucesso no Google Calendar:\n"
                    f"{created_events[0]}"
                )

            return (
                f"{len(created_events)} eventos foram criados "
                "com sucesso no Google Calendar:\n\n"
                + "\n".join(
                    f"- {event}"
                    for event in created_events
                )
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

            return "Tudo bem. O evento não foi criado."

        return (
            "Tenho uma proposta aguardando confirmação. "
            "Responda 'sim' para criar os eventos "
            "ou 'não' para cancelar."
        )

    response = generate_response(user_input)

    if response is None:

        return (
            "Desculpe, não consegui gerar uma resposta. "
            "Por favor, tente novamente."
        )

    # Verifica se o Gemini propôs algum evento
    clean_response, events = extract_event_proposal(response)

    # Se existem eventos propostos, salva a proposta
    if events:

        save_pending_plan(events)

        clean_response += (
            "\n\nDeseja que eu crie esses eventos "
            "no seu Google Calendar?"
        )

    return clean_response


# função para extrair os eventos propostos pelo Gemini
def extract_event_proposal(response):

    pattern = r"\[ORBiA_EVENTS\](.*?)\[/ORBiA_EVENTS\]"

    match = re.search(
        pattern,
        response,
        re.DOTALL
    )

    # Se não existe uma proposta de evento
    if not match:

        return response, []

    json_content = match.group(1).strip()

    try:

        events = json.loads(json_content)

    except json.JSONDecodeError:

        print(
            "[Orbia] Não foi possível interpretar a proposta."
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
            "start_datetime": event["start_datetime"],
            "end_datetime": event["end_datetime"],
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

    return clean_response, valid_events