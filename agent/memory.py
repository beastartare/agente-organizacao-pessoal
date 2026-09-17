import sqlite3
import json

# caminho do banco de dados
db_path = "data/agent.db"

#função de conexão com o banco de dados
def connect_db():
    return sqlite3.connect(db_path)

# função para iniciar o banco
def init_db():
    connection = connect_db()

    connection.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    connection.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            type TEXT NOT NULL,
            frequency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    connection.execute("""
    CREATE TABLE IF NOT EXISTS pending_plans (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) """)

    connection.execute("""
    CREATE TABLE IF NOT EXISTS agent_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            interaction_id TEXT
        ) """)

    connection.commit() # Salva as alterações no banco de dados
    connection.close() # Fecha a conexão com o banco de dados

#função para salvar a mensagem. Recebe quem mandou a mensagem ("user" ou "assistant") e o conteúdo da mensagem
def save_message(message_type, data):
    connection = connect_db()

    # conversão para json antes de salvar no banco de dados (formato do agente)
    json_data = json.dumps(data, ensure_ascii=False)

    connection.execute(
        "INSERT INTO messages (type, data) VALUES (?, ?)",
        (message_type, json_data)
    )

    connection.commit()
    connection.close()
    

# função para recuperar todas as mensagens do banco de dados
def get_messages():
    connection = connect_db()

    cursor = connection.execute(
        "SELECT type, data FROM messages ORDER BY id"
    )

    rows = cursor.fetchall()

    connection.close()

    messages = []

    # Transforma o json para um dicionário 
    for message_type, data in rows:
        messages.append({
            "type": message_type,
            "data": json.loads(data)
        })

    return messages

# Função para salvar um step (passos) do Gemini no banco de dados
def save_step(step):
    data = step.model_dump()

    save_message(step.type, data)

# Função para salvar um plano pendente no banco de dados
def save_pending_plan(events):
    connection = connect_db()

    connection.execute(
        """
        INSERT OR REPLACE INTO pending_plans (id, data)
        VALUES (1, ?)
        """,
        (json.dumps(events, ensure_ascii=False),)
    )

    connection.commit()
    connection.close()

# Função para obter o plano pendente do banco de dados
def get_pending_plan():
    connection = connect_db()

    cursor = connection.execute(
        "SELECT data FROM pending_plans WHERE id = 1"
    )

    row = cursor.fetchone()

    connection.close()

    if not row:
        return None

    return json.loads(row[0])

# Função para limpar o plano pendente do banco de dados
def clear_pending_plan():
    connection = connect_db()

    connection.execute(
        "DELETE FROM pending_plans WHERE id = 1"
    )

    connection.commit()
    connection.close()

def save_task(
    title,
    description="",
    task_type="task",
    frequency=None
):
    connection = connect_db()

    cursor = connection.execute(
        """
        SELECT id
        FROM tasks
        WHERE title = ?
          AND type = ?
          AND (
              frequency = ?
              OR (frequency IS NULL AND ? IS NULL)
          )
        """,
        (
            title,
            task_type,
            frequency,
            frequency
        )
    )

    existing_task = cursor.fetchone()

    if existing_task:
        connection.close()
        return False

    connection.execute(
        """
        INSERT INTO tasks (
            title,
            description,
            type,
            frequency
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            title,
            description,
            task_type,
            frequency
        )
    )

    connection.commit()
    connection.close()

    return True

def get_tasks():
    connection = connect_db()

    cursor = connection.execute(
        """
        SELECT id, title, description, type, frequency
        FROM tasks
        ORDER BY id
        """
    )

    rows = cursor.fetchall()

    connection.close()

    tasks = []

    for row in rows:
        tasks.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "type": row[3],
            "frequency": row[4]
        })

    return tasks


def save_interaction_id(interaction_id):
    connection = connect_db()

    connection.execute(
        """
        INSERT OR REPLACE INTO agent_state (id, interaction_id)
        VALUES (1, ?)
        """,
        (interaction_id,)
    )

    connection.commit()
    connection.close()


def get_interaction_id():
    connection = connect_db()

    cursor = connection.execute(
        "SELECT interaction_id FROM agent_state WHERE id = 1"
    )

    row = cursor.fetchone()

    connection.close()

    if not row:
        return None

    return row[0]


def clear_interaction_id():
    connection = connect_db()

    connection.execute(
        "DELETE FROM agent_state WHERE id = 1"
    )

    connection.commit()
    connection.close()