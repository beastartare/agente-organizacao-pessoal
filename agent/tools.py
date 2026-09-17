# arquivo com as "ferramentas" que o agente pode usar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agent.calendar import get_calendar_events, create_calendar_event
from agent.memory import get_tasks, save_task


TIMEZONE = ZoneInfo("America/Sao_Paulo")


# retorna a data e hora atual 
def get_current_time():
    return datetime.now(TIMEZONE).isoformat()

# função para obter os próximos eventos do Google Calendar
def get_calendar_events_for_period(period="today"):

    now = datetime.now(TIMEZONE)

    if period == "today":

        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end = start + timedelta(days=1)

    elif period == "tomorrow":

        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(days=1)

        end = start + timedelta(days=1)

    elif period == "week":

        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end = start + timedelta(days=7)

    else:
        raise ValueError(
            "Período inválido. Use today, tomorrow ou week."
        )

    events = get_calendar_events(
        start.isoformat(),
        end.isoformat()
    )

    if not events:
        return "Não existem eventos nesse período."

    result = []

    for event in events:

        result.append(
            f"- {event['title']} | "
            f"início: {event['start']} | "
            f"fim: {event['end']}"
        )

    return "\n".join(result)

def create_event(title, start_datetime, end_datetime,description=""):


    event = create_calendar_event(
        title=title,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        description=description
    )

    return (
        f"Evento criado com sucesso: "
        f"{event['title']} | "
        f"{event['start']} até {event['end']}"
    )

def get_user_tasks():
    tasks = get_tasks()

    if not tasks:
        return "O usuário ainda não possui tarefas ou hábitos registrados."

    result = []

    for task in tasks:

        frequency = task["frequency"]

        if frequency:
            result.append(
                f"- {task['title']} "
                f"(frequência: {frequency})"
            )
        else:
            result.append(
                f"- {task['title']}"
            )

    return "\n".join(result)


def add_user_task(
    title,
    description="",
    task_type="task",
    frequency=None
):
    save_task(
        title=title,
        description=description,
        task_type=task_type,
        frequency=frequency
    )

    return f"Tarefa '{title}' adicionada à memória do Orbia."