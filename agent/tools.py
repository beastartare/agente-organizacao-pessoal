from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

from agent.calendar import (get_calendar_events,create_calendar_event)
from agent.memory import (get_tasks,save_task)


TIMEZONE = ZoneInfo("America/Sao_Paulo")

WEEKDAYS = {
    "segunda": 0,
    "segunda-feira": 0,
    "monday": 0,
    "terça": 1,
    "terca": 1,
    "terça-feira": 1,
    "terca-feira": 1,
    "tuesday": 1,
    "quarta": 2,
    "quarta-feira": 2,
    "wednesday": 2,
    "quinta": 3,
    "quinta-feira": 3,
    "thursday": 3,
    "sexta": 4,
    "sexta-feira": 4,
    "friday": 4,
    "sábado": 5,
    "sabado": 5,
    "saturday": 5,
    "domingo": 6,
    "sunday": 6
}


def get_current_time():
    return datetime.now(TIMEZONE).isoformat()


def _get_period_range(period):
    now = datetime.now(TIMEZONE)

    today = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    if period == "today":
        return today, today + timedelta(days=1)

    if period == "tomorrow":
        start = today + timedelta(days=1)
        return start, start + timedelta(days=1)

    if period == "week":
        return today, today + timedelta(days=7)

    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7)

    if period == "next_week":
        start = (
            today
            - timedelta(days=today.weekday())
            + timedelta(days=7)
        )

        return start, start + timedelta(days=7)

    raise ValueError(
        "Período inválido. Use today, tomorrow, week, this_week ou next_week."
    )


def _format_calendar_events(events):
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


def get_calendar_events_for_period(period="today"):
    start, end = _get_period_range(period)

    events = get_calendar_events(
        start.isoformat(),
        end.isoformat()
    )

    return _format_calendar_events(events)


def _normalize_days(days_of_week):
    if not days_of_week:
        return []

    if isinstance(days_of_week, list):
        values = days_of_week
    else:
        values = (
            str(days_of_week)
            .replace(";", ",")
            .split(",")
        )

    normalized = []

    for value in values:
        value = value.strip().lower()

        if value in WEEKDAYS:
            normalized.append(
                WEEKDAYS[value]
            )

        elif value.isdigit() and 0 <= int(value) <= 6:
            normalized.append(
                int(value)
            )

    return sorted(set(normalized))


def _get_recurring_blocks(tasks, start, end):
    blocks = []
    unscheduled = []

    current = start

    while current < end:

        for task in tasks:

            days = _normalize_days(
                task.get("days_of_week")
            )

            if current.weekday() not in days:
                continue

            start_time = task.get("start_time")
            end_time = task.get("end_time")

            if not start_time or not end_time:

                unscheduled.append({
                    "title": task["title"],
                    "description": (
                        task.get("description") or ""
                    ),
                    "frequency": (
                        task.get("frequency") or ""
                    ),
                    "date": current.date().isoformat()
                })

                continue

            blocks.append({
                "title": task["title"],
                "type": task["type"],
                "start": (
                    f"{current.date().isoformat()}"
                    f"T{start_time}:00-03:00"
                ),
                "end": (
                    f"{current.date().isoformat()}"
                    f"T{end_time}:00-03:00"
                ),
                "description": (
                    task.get("description") or ""
                )
            })

        current += timedelta(days=1)

    return blocks, unscheduled


def get_schedule_constraints(period="next_week"):
    start, end = _get_period_range(period)

    calendar_events = get_calendar_events(
        start.isoformat(),
        end.isoformat()
    )

    tasks = get_tasks()

    recurring_blocks, unscheduled = (
        _get_recurring_blocks(
            tasks,
            start,
            end
        )
    )

    result = {
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "calendar_events": calendar_events,
        "recurring_blocks": recurring_blocks,
        "tasks_without_defined_time": unscheduled,
        "rules": [
            "calendar_events são eventos já existentes no Google Calendar",
            "recurring_blocks são compromissos fixos salvos na memória",
            "calendar_events e recurring_blocks são horários ocupados",
            "novas tarefas não devem ocupar esses horários",
            "recurring_blocks devem fazer parte do cronograma",
            "recurring_blocks devem ser adicionados ao Google Calendar caso ainda não existam",
            "tasks_without_defined_time não possuem horário suficiente para bloquear um período"
        ]
    }

    print("\n[Orbia] RESTRIÇÕES DO CRONOGRAMA:")

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

    return json.dumps(
        result,
        ensure_ascii=False
    )


def get_recurring_events_for_period(period="next_week"):
    start, end = _get_period_range(period)

    tasks = get_tasks()

    recurring_blocks, _ = _get_recurring_blocks(
        tasks,
        start,
        end
    )

    events = []

    for block in recurring_blocks:

        events.append({
            "title": block["title"],
            "start_datetime": block["start"],
            "end_datetime": block["end"],
            "description": block.get(
                "description",
                ""
            )
        })

    return events


def _event_exists_in_calendar(event, calendar_events):
    event_start = datetime.fromisoformat(
        event["start_datetime"]
    )

    event_end = datetime.fromisoformat(
        event["end_datetime"]
    )

    for existing in calendar_events:

        existing_start_value = existing["start"]
        existing_end_value = existing["end"]

        if len(existing_start_value) == 10:
            existing_start = datetime.fromisoformat(
                existing_start_value
            ).replace(
                tzinfo=TIMEZONE
            )
        else:
            existing_start = datetime.fromisoformat(
                existing_start_value
            )

        if len(existing_end_value) == 10:
            existing_end = datetime.fromisoformat(
                existing_end_value
            ).replace(
                tzinfo=TIMEZONE
            )
        else:
            existing_end = datetime.fromisoformat(
                existing_end_value
            )

        same_title = (
            event["title"].strip().lower()
            == existing["title"].strip().lower()
        )

        same_start = (
            event_start == existing_start
        )

        same_end = (
            event_end == existing_end
        )

        if same_title and same_start and same_end:
            return True

    return False


def create_missing_recurring_events(events):
    if not events:
        return []

    starts = [
        datetime.fromisoformat(
            event["start_datetime"]
        )
        for event in events
    ]

    ends = [
        datetime.fromisoformat(
            event["end_datetime"]
        )
        for event in events
    ]

    range_start = min(starts)
    range_end = max(ends)

    calendar_events = get_calendar_events(
        range_start.isoformat(),
        range_end.isoformat()
    )

    created_events = []

    for event in events:

        if _event_exists_in_calendar(
            event,
            calendar_events
        ):
            print(
                "[Orbia] Compromisso fixo já existe "
                f"no Calendar: {event['title']} "
                f"{event['start_datetime']}"
            )

            continue

        created = create_calendar_event(
            title=event["title"],
            start_datetime=event["start_datetime"],
            end_datetime=event["end_datetime"],
            description=event.get(
                "description",
                ""
            )
        )

        created_events.append({
            "title": created["title"],
            "start": created["start"],
            "end": created["end"],
            "type": "fixed"
        })

    return created_events


def create_event(title, start_datetime, end_datetime, description=""):
    event = create_calendar_event(
        title=title,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        description=description
    )

    return (
        f"{event['title']} | "
        f"{event['start']} até {event['end']}"
    )


def get_user_tasks():
    tasks = get_tasks()

    if not tasks:
        return (
            "O usuário ainda não possui "
            "tarefas ou hábitos registrados."
        )

    result = []

    for task in tasks:

        result.append(
            f"- Título: {task['title']}\n"
            f"  Descrição: {task['description'] or 'Não informada'}\n"
            f"  Tipo: {task['type']}\n"
            f"  Frequência: {task['frequency'] or 'Não informada'}\n"
            f"  Dias: {task['days_of_week'] or 'Não informados'}\n"
            f"  Início: {task['start_time'] or 'Não informado'}\n"
            f"  Fim: {task['end_time'] or 'Não informado'}"
        )

    return "\n".join(result)


def add_user_task(title, description="", task_type="task", frequency=None, days_of_week=None, start_time=None, end_time=None):
    normalized_days = None

    if days_of_week:

        if isinstance(days_of_week, list):

            normalized_days = ",".join(
                str(day).strip().lower()
                for day in days_of_week
            )

        else:

            normalized_days = (
                str(days_of_week)
                .strip()
                .lower()
            )

    save_task(
        title=title,
        description=description,
        task_type=task_type,
        frequency=frequency,
        days_of_week=normalized_days,
        start_time=start_time,
        end_time=end_time
    )

    return (
        f"Tarefa '{title}' "
        "adicionada à memória do Orbia."
    )


def validate_proposed_events(events):

    if not events:
        return []

    starts = [
        datetime.fromisoformat(
            event["start_datetime"]
        )
        for event in events
    ]

    ends = [
        datetime.fromisoformat(
            event["end_datetime"]
        )
        for event in events
    ]

    range_start = min(starts)
    range_end = max(ends)

    calendar_events = get_calendar_events(
        range_start.isoformat(),
        range_end.isoformat()
    )

    tasks = get_tasks()

    conflicts = []

    for proposed in events:

        proposed_start = datetime.fromisoformat(
            proposed["start_datetime"]
        )

        proposed_end = datetime.fromisoformat(
            proposed["end_datetime"]
        )

        for existing in calendar_events:

            existing_start_value = existing["start"]
            existing_end_value = existing["end"]

            if len(existing_start_value) == 10:
                existing_start = datetime.fromisoformat(
                    existing_start_value
                ).replace(
                    tzinfo=TIMEZONE
                )
            else:
                existing_start = datetime.fromisoformat(
                    existing_start_value
                )

            if len(existing_end_value) == 10:
                existing_end = datetime.fromisoformat(
                    existing_end_value
                ).replace(
                    tzinfo=TIMEZONE
                )
            else:
                existing_end = datetime.fromisoformat(
                    existing_end_value
                )

            if (
                proposed_start < existing_end
                and proposed_end > existing_start
            ):
                conflicts.append({
                    "proposed_event": proposed["title"],
                    "conflict_type": "calendar",
                    "conflict_with": existing["title"],
                    "start": existing["start"],
                    "end": existing["end"]
                })

        for task in tasks:

            days = _normalize_days(
                task.get("days_of_week")
            )

            if proposed_start.weekday() not in days:
                continue

            start_time = task.get("start_time")
            end_time = task.get("end_time")

            if not start_time or not end_time:
                continue

            task_start = datetime.fromisoformat(
                f"{proposed_start.date().isoformat()}"
                f"T{start_time}:00-03:00"
            )

            task_end = datetime.fromisoformat(
                f"{proposed_start.date().isoformat()}"
                f"T{end_time}:00-03:00"
            )

            if (
                proposed_start < task_end
                and proposed_end > task_start
            ):
                conflicts.append({
                    "proposed_event": proposed["title"],
                    "conflict_type": "routine",
                    "conflict_with": task["title"],
                    "start": task_start.isoformat(),
                    "end": task_end.isoformat()
                })

    return conflicts