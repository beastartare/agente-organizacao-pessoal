import json

from google import genai

from dotenv import load_dotenv

from agent.tools import (
    get_current_time,
    get_calendar_events_for_period,
    get_user_tasks,
    add_user_task
)

from agent.memory import (
    save_step,
    save_message,
    get_interaction_id,
    save_interaction_id,
    clear_interaction_id
)


load_dotenv()


client = genai.Client()


tools = [
    {
        "type": "function",
        "name": "get_current_time",
        "description": "Obtém a data e hora atuais.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "type": "function",
        "name": "get_calendar_events",
        "description": (
            "Consulta os eventos do Google Calendar "
            "do usuário. Use esta ferramenta quando "
            "o usuário perguntar sobre compromissos, "
            "tarefas, aulas, reuniões ou horários ocupados."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": [
                        "today",
                        "tomorrow",
                        "week"
                    ],
                    "description": (
                        "Período da consulta: "
                        "today para hoje, "
                        "tomorrow para amanhã, "
                        "week para os próximos 7 dias."
                    )
                }
            },
            "required": ["period"]
        }
    },

    {
        "type": "function",
        "name": "get_user_tasks",
        "description": (
            "Consulta as tarefas e hábitos que o usuário "
            "já informou anteriormente e que estão salvos "
            "na memória do Orbia."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "type": "function",
        "name": "add_user_task",
        "description": (
            "Registra uma nova tarefa ou hábito informado "
            "pelo usuário na memória do Orbia."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título da tarefa ou hábito."
                },
                "description": {
                    "type": "string",
                    "description": "Descrição opcional."
                },
                "task_type": {
                    "type": "string",
                    "enum": [
                        "task",
                        "habit"
                    ],
                    "description": (
                        "Tipo do registro: task para tarefa "
                        "ou habit para hábito."
                    )
                },
                "frequency": {
                    "type": "string",
                    "description": (
                        "Frequência do hábito, quando aplicável."
                    )
                }
            },
            "required": [
                "title"
            ]
        }
    }
]


available_tools = {
    "get_current_time": get_current_time,
    "get_calendar_events": get_calendar_events_for_period,
    "get_user_tasks": get_user_tasks,
    "add_user_task": add_user_task
}


SYSTEM_INSTRUCTION = """
Você é Orbia, um agente pessoal de organização.

Sua função é ajudar o usuário a organizar tarefas,
compromissos e rotina.

========================================
CONVERSA NORMAL
========================================

Responda normalmente a conversas casuais.

Não consulte o Google Calendar para perguntas que
não dependem da agenda.

Exemplos:

- Oi
- Olá
- Como você está?
- O que você pode fazer?

========================================
CONSULTA AO CALENDAR
========================================

Use a ferramenta get_calendar_events quando precisar
saber quais compromissos o usuário possui.

Exemplos:

- Quais são minhas tarefas hoje?
- O que tenho amanhã?
- Tenho algum compromisso amanhã?
- Como está minha agenda essa semana?

Nunca invente eventos que não estejam no Calendar.

========================================
PLANEJAMENTO
========================================

Quando o usuário pedir para organizar tarefas,
estudos, trabalho ou rotina:

1. Entenda o que o usuário precisa fazer.
2. Identifique o período envolvido.
3. Consulte o Google Calendar para verificar
   compromissos existentes.
4. Considere os compromissos existentes como horários
   que não devem ser ocupados.
5. Analise as informações disponíveis na conversa.
6. Monte uma proposta de organização.
7. NÃO crie eventos no Google Calendar.
8. Apresente a proposta ao usuário.
9. Pergunte se ele deseja confirmar.

========================================
TAREFAS E HÁBITOS
========================================

Quando o usuário pedir para organizar sua rotina,
considere também as tarefas e hábitos que aparecem
no histórico da conversa.

Quando for necessário consultar tarefas e hábitos
já registrados, use a ferramenta get_user_tasks.

Não invente tarefas ou hábitos.

Diferencie:

- compromissos existentes no Google Calendar;
- tarefas que precisam ser realizadas;
- hábitos recorrentes.

Ao criar uma proposta de organização, considere
as tarefas e hábitos juntamente com os compromissos
do Calendar.

IMPORTANTE:

Não registre automaticamente qualquer informação
como tarefa ou hábito.

Use add_user_task quando o usuário explicitamente
pedir para registrar, salvar, lembrar ou adicionar
uma tarefa ou hábito à memória.

Informações como:

"de segunda a sexta eu tenho aula"

devem ser tratadas como compromissos fixos da rotina,
e não automaticamente como uma tarefa ou hábito.

========================================
EVENTOS PROPOSTOS
========================================

Quando sua resposta incluir eventos que deveriam ser
adicionados ao Google Calendar, adicione ao final da
resposta um bloco exatamente neste formato:

[ORBiA_EVENTS]
[
    {
        "title": "Nome do evento",
        "start_datetime": "2026-09-16T14:00:00-03:00",
        "end_datetime": "2026-09-16T16:00:00-03:00",
        "description": "Descrição opcional"
    }
]
[/ORBiA_EVENTS]

REGRAS DO BLOCO:

- Deve conter JSON válido.
- Use aspas duplas.
- Não coloque comentários dentro do JSON.
- Use datas e horários completos.
- Use o fuso horário -03:00.
- Inclua somente eventos que estão sendo propostos.
- Não inclua eventos que já existem no Calendar.
- NÃO diga que os eventos foram criados.
- Os eventos são apenas uma proposta até o usuário confirmar.

========================================
CONFIRMAÇÃO
========================================

A aplicação Python cuidará da confirmação e criação
dos eventos.

Você não deve criar eventos diretamente.
"""


def generate_response(user_input):

    previous_interaction_id = get_interaction_id()

    # tratamento de erros ao gerar a resposta do Gemini
    try:

        print("[Orbia] Consultando Gemini...")

        if previous_interaction_id:

            response = client.interactions.create(
                model="gemini-3.6-flash",
                previous_interaction_id=previous_interaction_id,
                input=user_input,
                tools=tools,
                system_instruction=SYSTEM_INSTRUCTION
            )

        else:

            response = client.interactions.create(
                model="gemini-3.6-flash",
                input=user_input,
                tools=tools,
                system_instruction=SYSTEM_INSTRUCTION
            )

        print("[Orbia] Gemini respondeu.")

        function_results = []

        # Processa todos os steps retornados pelo Gemini
        for step in response.steps:

            print(
                f"[Orbia] Step recebido: {step.type}"
            )

            # Salva o step no banco de dados
            save_step(step)

            # Verifica se o Gemini solicitou uma ferramenta
            if step.type == "function_call":

                print(
                    f"[Orbia] Gemini solicitou a ferramenta: "
                    f"{step.name}"
                )

                function = available_tools.get(step.name)

                if function is None:

                    raise Exception(
                        f"Ferramenta não encontrada: {step.name}"
                    )

                # Executa a ferramenta
                print(
                    f"[Orbia] Executando {step.name}..."
                )

                result = function(**step.arguments)

                print(
                    f"[Orbia] Ferramenta {step.name} concluída."
                )

                # Cria o resultado da ferramenta
                function_result = {
                    "type": "function_result",
                    "name": step.name,
                    "call_id": step.id,
                    "result": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                result,
                                ensure_ascii=False
                            )
                        }
                    ]
                }

                # Salva o resultado no banco
                save_message(
                    "function_result",
                    function_result
                )

                function_results.append(function_result)

        # Se nenhuma ferramenta foi chamada, significa que há uma resposta final
        if not function_results:

            save_interaction_id(response.id)

            print("[Orbia] Resposta recebida.")

            return response.output_text

        print(
            "[Orbia] Enviando o resultado das ferramentas "
            "novamente para o Gemini..."
        )

        response = client.interactions.create(
            model="gemini-3.6-flash",
            previous_interaction_id=response.id,
            input=function_results,
            tools=tools,
            system_instruction=SYSTEM_INSTRUCTION
        )

        print("[Orbia] Gemini respondeu após executar as ferramentas.")

        while True:

            function_results = []

            # Processa todos os steps retornados pelo Gemini
            for step in response.steps:

                print(
                    f"[Orbia] Step recebido: {step.type}"
                )

                # Salva o step no banco de dados
                save_step(step)

                # Verifica se o Gemini solicitou uma ferramenta
                if step.type == "function_call":

                    print(
                        f"[Orbia] Gemini solicitou a ferramenta: "
                        f"{step.name}"
                    )

                    function = available_tools.get(step.name)

                    if function is None:

                        raise Exception(
                            f"Ferramenta não encontrada: {step.name}"
                        )

                    # Executa a ferramenta
                    print(
                        f"[Orbia] Executando {step.name}..."
                    )

                    result = function(**step.arguments)

                    print(
                        f"[Orbia] Ferramenta {step.name} concluída."
                    )

                    # Cria o resultado da ferramenta
                    function_result = {
                        "type": "function_result",
                        "name": step.name,
                        "call_id": step.id,
                        "result": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    result,
                                    ensure_ascii=False
                                )
                            }
                        ]
                    }

                    # Salva o resultado no banco
                    save_message(
                        "function_result",
                        function_result
                    )

                    function_results.append(function_result)

            if not function_results:

                save_interaction_id(response.id)

                print("[Orbia] Resposta recebida.")

                return response.output_text

            print(
                "[Orbia] Enviando o resultado das ferramentas "
                "novamente para o Gemini..."
            )

            response = client.interactions.create(
                model="gemini-3.6-flash",
                previous_interaction_id=response.id,
                input=function_results,
                tools=tools,
                system_instruction=SYSTEM_INSTRUCTION
            )

    except Exception as error:

        error_message = str(error)

        if "429" in error_message or "Too Many Requests" in error_message:

            print(
                "[Orbia] O Gemini está temporariamente com "
                "limite de requisições. Aguarde alguns segundos "
                "e tente novamente."
            )

        else:

            print(
                f"[Orbia] Erro ao gerar resposta: {error}"
            )

            if previous_interaction_id:

                print(
                    "[Orbia] Tentando iniciar uma nova conversa..."
                )

                clear_interaction_id()

                try:

                    response = client.interactions.create(
                        model="gemini-3.6-flash",
                        input=user_input,
                        tools=tools,
                        system_instruction=SYSTEM_INSTRUCTION
                    )

                    for step in response.steps:

                        print(
                            f"[Orbia] Step recebido: {step.type}"
                        )

                        # Salva o step no banco de dados
                        save_step(step)

                    function_results = []

                    for step in response.steps:

                        # Verifica se o Gemini solicitou uma ferramenta
                        if step.type == "function_call":

                            print(
                                f"[Orbia] Gemini solicitou a ferramenta: "
                                f"{step.name}"
                            )

                            function = available_tools.get(step.name)

                            if function is None:

                                raise Exception(
                                    f"Ferramenta não encontrada: {step.name}"
                                )

                            # Executa a ferramenta
                            print(
                                f"[Orbia] Executando {step.name}..."
                            )

                            result = function(**step.arguments)

                            print(
                                f"[Orbia] Ferramenta {step.name} concluída."
                            )

                            # Cria o resultado da ferramenta
                            function_result = {
                                "type": "function_result",
                                "name": step.name,
                                "call_id": step.id,
                                "result": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(
                                            result,
                                            ensure_ascii=False
                                        )
                                    }
                                ]
                            }

                            # Salva o resultado no banco
                            save_message(
                                "function_result",
                                function_result
                            )

                            function_results.append(function_result)

                    if not function_results:

                        save_interaction_id(response.id)

                        return response.output_text

                    response = client.interactions.create(
                        model="gemini-3.6-flash",
                        previous_interaction_id=response.id,
                        input=function_results,
                        tools=tools,
                        system_instruction=SYSTEM_INSTRUCTION
                    )

                    while True:

                        function_results = []

                        # Processa todos os steps retornados pelo Gemini
                        for step in response.steps:

                            print(
                                f"[Orbia] Step recebido: {step.type}"
                            )

                            # Salva o step no banco de dados
                            save_step(step)

                            # Verifica se o Gemini solicitou uma ferramenta
                            if step.type == "function_call":

                                print(
                                    f"[Orbia] Gemini solicitou a ferramenta: "
                                    f"{step.name}"
                                )

                                function = available_tools.get(step.name)

                                if function is None:

                                    raise Exception(
                                        f"Ferramenta não encontrada: {step.name}"
                                    )

                                # Executa a ferramenta
                                print(
                                    f"[Orbia] Executando {step.name}..."
                                )

                                result = function(**step.arguments)

                                print(
                                    f"[Orbia] Ferramenta {step.name} concluída."
                                )

                                # Cria o resultado da ferramenta
                                function_result = {
                                    "type": "function_result",
                                    "name": step.name,
                                    "call_id": step.id,
                                    "result": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(
                                                result,
                                                ensure_ascii=False
                                            )
                                        }
                                    ]
                                }

                                # Salva o resultado no banco
                                save_message(
                                    "function_result",
                                    function_result
                                )

                                function_results.append(
                                    function_result
                                )

                        if not function_results:

                            save_interaction_id(response.id)

                            return response.output_text

                        response = client.interactions.create(
                            model="gemini-3.6-flash",
                            previous_interaction_id=response.id,
                            input=function_results,
                            tools=tools,
                            system_instruction=SYSTEM_INSTRUCTION
                        )

                except Exception as retry_error:

                    print(
                        f"[Orbia] Erro ao iniciar nova conversa: "
                        f"{retry_error}"
                    )

        return None