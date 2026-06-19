from agent import agent
from assistant_config import assistant
from decorators.profiling import profiling

print(f"\n\n{assistant.name} está pronto! (ctrl+c para sair)\n")

@profiling
def ask(text: str):
    agent(text)

while True:
    user_input = input("\nVocê: ")
    if not user_input.strip():
        continue
    ask(user_input)
