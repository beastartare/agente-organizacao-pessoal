# interface principal do agente
from agent.agent import process_user_input
from agent.memory import init_db

# Inicializa o banco de dados
init_db()  

print("Agente iniciado!")
print("Digite 'sair' para encerrar.")

while True:
    user_input = input("Você:")

    # condição de parada
    if user_input.lower() == "sair":
        print("Encerrando o agente. Até logo!")
        break

    # tratamento de erro para a resposta do agente
    try:
        response = process_user_input(user_input)
        print(f"Agente: {response}")
    except Exception as error:
        print(f"Ocorreu um erro inesperado: {error}")