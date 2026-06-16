from agent import agent
from assistant_config import assistant

print(f"{assistant.name} está pronto! (ctrl+c para sair)\n")


def ask(user_input: str):
    response = agent(user_input)
    print(response)



while True:
    user_input = input("\nVocê: ")
    if not user_input.strip():
        continue
    ask(user_input)
