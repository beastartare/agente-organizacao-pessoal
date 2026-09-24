import json
from google import genai
from dotenv import load_dotenv
from agent.tools import (get_current_time, get_calendar_events_for_period, get_user_tasks, add_user_task, get_schedule_constraints)
from agent.memory import (save_step, save_message, get_interaction_id, save_interaction_id, clear_interaction_id)


# carrego as variaveis do ambiente
load_dotenv()

# 
client = genai.Client()

# lista de funções que o meu agente pode utilizar para "facilitar" o seu trabalho
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
            "Consulta os eventos existentes no Google Calendar "
            "do usuário em um determinado período."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": [
                        "today",
                        "tomorrow",
                        "week",
                        "this_week",
                        "next_week"
                    ],
                    "description": (
                        "Período da consulta. "
                        "Use today para hoje, tomorrow para amanhã, "
                        "week para os próximos 7 dias, "
                        "this_week para esta semana e "
                        "next_week para a próxima semana."
                    )
                }
            },
            "required": [
                "period"
            ]
        }
    },

    {
        "type": "function",
        "name": "get_schedule_constraints",
        "description": (
            "Consulta os compromissos existentes no Google Calendar "
            "e os compromissos fixos da rotina do usuário. "
            "Deve ser utilizada antes de montar um cronograma."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": [
                        "today",
                        "tomorrow",
                        "week",
                        "this_week",
                        "next_week"
                    ],
                    "description": (
                        "Período do cronograma."
                    )
                }
            },
            "required": [
                "period"
            ]
        }
    },

    {
        "type": "function",
        "name": "get_user_tasks",
        "description": (
            "Consulta as tarefas e hábitos registrados "
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
            "Registra uma nova tarefa ou hábito na memória "
            "do Orbia."
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
                        "Tipo do registro."
                    )
                },
                "frequency": {
                    "type": "string",
                    "description": (
                        "Frequência da tarefa ou hábito."
                    )
                },
                "days_of_week": {
                    "type": "string",
                    "description": (
                        "Dias da semana separados por vírgula."
                    )
                },
                "start_time": {
                    "type": "string",
                    "description": (
                        "Horário de início no formato HH:MM."
                    )
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "Horário de término no formato HH:MM."
                    )
                }
            },
            "required": [
                "title"
            ]
        }
    }
]

# conexão do nome da "ferramenta" com a função de fato
available_tools = {
    "get_current_time": get_current_time,
    "get_calendar_events": get_calendar_events_for_period,
    "get_schedule_constraints": get_schedule_constraints,
    "get_user_tasks": get_user_tasks,
    "add_user_task": add_user_task
}


#instrução do sistema
SYSTEM_INSTRUCTION = """
Você é o Orbia, um agente de organização pessoal.

Seu objetivo é ajudar o usuário a organizar tarefas, compromissos,
hábitos e horários utilizando as informações disponíveis no Google
Calendar e na memória do usuário.

Quando o usuário informar uma tarefa, hábito ou compromisso que deve
ser lembrado para o futuro, utilize add_user_task para registrar essa
informação na memória.

Quando o usuário pedir para montar um cronograma, utilize
get_schedule_constraints antes de elaborar a proposta.

A ferramenta get_schedule_constraints fornece:

- calendar_events: eventos que já existem no Google Calendar.
- recurring_blocks: compromissos fixos da rotina do usuário, como
  trabalho, aulas, academia, taekwondo ou outros hábitos com dias e
  horários definidos.
- tasks_without_defined_time: tarefas ou hábitos registrados na
  memória que não possuem horário definido.

calendar_events e recurring_blocks representam horários ocupados.

Nunca coloque uma nova atividade sobre um calendar_event ou
recurring_block.

Os recurring_blocks fazem parte do cronograma e devem aparecer na
programação apresentada ao usuário.

Os recurring_blocks NÃO são novas atividades.

Nunca coloque recurring_blocks dentro de [ORBiA_EVENTS].

Eventos que já existem no Google Calendar também não devem ser
colocados dentro de [ORBiA_EVENTS].

[ORBiA_EVENTS] deve conter somente as novas atividades que o Orbia
está propondo para o usuário realizar.

Por exemplo, se o usuário trabalha de segunda a sexta das 08:00 às
12:00, o trabalho deve aparecer no cronograma como compromisso fixo,
mas não deve aparecer em [ORBiA_EVENTS].

Da mesma forma, se o usuário tem Taekwondo segunda e sexta às 19:00,
o Taekwondo deve aparecer no cronograma, mas não deve aparecer em
[ORBiA_EVENTS].

O mesmo vale para qualquer outro recurring_block.

Ao apresentar um cronograma, mostre:

- eventos que já existem no Google Calendar;
- compromissos fixos da rotina;
- novas atividades sugeridas.

Não altere, remova ou mova compromissos existentes apenas para criar
espaço para novas atividades.

As novas atividades devem ser distribuídas somente nos horários livres.

Quando o usuário pedir um cronograma para "essa semana" ou
"esta semana", use this_week.

Quando o usuário pedir um cronograma para "semana que vem" ou
"próxima semana", use next_week.

Quando o usuário pedir "amanhã", use tomorrow.

Quando o usuário pedir "hoje", use today.

Se o usuário pedir um cronograma sem especificar um período,
considere o período adequado ao contexto da solicitação.

Quando o cronograma possuir novas atividades, apresente a proposta
primeiro e peça confirmação antes de criar os novos eventos.

Somente após a confirmação do usuário as novas atividades poderão
ser criadas no Google Calendar.

Quando houver novas atividades a serem criadas, use exatamente:

[ORBiA_EVENTS]
[
  {
    "title": "Título do evento",
    "start_datetime": "YYYY-MM-DDTHH:MM:SS-03:00",
    "end_datetime": "YYYY-MM-DDTHH:MM:SS-03:00",
    "description": "Descrição do evento"
  }
]
[/ORBiA_EVENTS]

Dentro de [ORBiA_EVENTS] coloque SOMENTE novas atividades.

Nunca coloque dentro de [ORBiA_EVENTS]:

- eventos que já existem no Google Calendar;
- recurring_blocks;
- trabalho;
- aulas fixas;
- hábitos recorrentes;
- compromissos fixos da rotina.

Não crie eventos duplicados.

O usuário deve decidir se deseja criar os novos eventos. Não crie
eventos automaticamente apenas porque eles foram sugeridos.

Ao apresentar o cronograma, deixe claro quais itens são compromissos
existentes ou fixos e quais são novas atividades sugeridas.
"""


# verifica se o usuário está pedindo para montar um cronograma 
def _is_planning_request(user_input):
    text = user_input.lower()

    planning_terms = [
        "cronograma",
        "organizar",
        "organize",
        "planejar",
        "planeje",
        "agenda",
        "rotina",
        "distribuir",
        "monte",
        "montar"
    ]

    return any(
        term in text
        for term in planning_terms
    )


def _create_interaction(user_input, previous_interaction_id=None):

    arguments = {
        "model": "gemini-3.6-flash",
        "tools": tools,
        "system_instruction": SYSTEM_INSTRUCTION,
        "input": user_input
    }

    if previous_interaction_id:
        arguments[
            "previous_interaction_id"
        ] = previous_interaction_id

    return client.interactions.create(
        **arguments
    )


def _execute_function_calls(response):

    function_results = []

    for step in response.steps:

        print(
            f"[Orbia] Step recebido: {step.type}"
        )

        save_step(step)

        if step.type == "function_call":

            print(
                f"[Orbia] Gemini solicitou a ferramenta: "
                f"{step.name}"
            )

            function = available_tools.get(
                step.name
            )

            if function is None:
                raise Exception(
                    f"Ferramenta não encontrada: {step.name}"
                )

            print(
                f"[Orbia] Executando {step.name}..."
            )

            result = function(
                **step.arguments
            )

            print(
                f"[Orbia] Ferramenta {step.name} concluída."
            )

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

            save_message(
                "function_result",
                function_result
            )

            function_results.append(
                function_result
            )

    return function_results


def generate_response(user_input):

    previous_interaction_id = (
        get_interaction_id()
    )

    try:

        print(
            "[Orbia] Consultando Gemini..."
        )

        response = _create_interaction(
            user_input,
            previous_interaction_id
        )

        print(
            "[Orbia] Gemini respondeu."
        )

        while True:

            function_results = (
                _execute_function_calls(
                    response
                )
            )

            if not function_results:

                save_interaction_id(
                    response.id
                )

                print(
                    "[Orbia] Resposta recebida."
                )

                return response.output_text

            print(
                "[Orbia] Enviando o resultado das "
                "ferramentas novamente para o Gemini..."
            )

            response = client.interactions.create(
                model="gemini-3.6-flash",
                previous_interaction_id=response.id,
                input=function_results,
                tools=tools,
                system_instruction=SYSTEM_INSTRUCTION
            )

            print(
                "[Orbia] Gemini respondeu após "
                "executar as ferramentas."
            )

    except Exception as error:

        error_message = str(error)

        if (
            "429" in error_message
            or "Too Many Requests" in error_message
        ):

            print(
                "[Orbia] O Gemini está temporariamente "
                "com limite de requisições. Aguarde alguns "
                "segundos e tente novamente."
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

                response = _create_interaction(
                    user_input
                )

                while True:

                    function_results = (
                        _execute_function_calls(
                            response
                        )
                    )

                    if not function_results:

                        save_interaction_id(
                            response.id
                        )

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