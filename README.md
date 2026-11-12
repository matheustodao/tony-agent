# 🎙️ Tony Agent

Assistente de voz pessoal que roda **100% local**: LLM via Ollama, agente com tool-calling via Strands Agents e síntese de voz neural em português brasileiro com Kokoro (ONNX). Sem API paga, sem enviar dados para a nuvem.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20%7C%20Qwen2.5%207B-black)
![Strands](https://img.shields.io/badge/Agent-Strands%20Agents-orange)
![Kokoro](https://img.shields.io/badge/TTS-Kokoro%20ONNX-blueviolet)
![uv](https://img.shields.io/badge/Deps-uv-DE5FE9)

## ✨ Destaques

- **Local-first:** modelo de linguagem e voz rodam na própria máquina (CPU), com privacidade total.
- **Fala enquanto pensa:** a resposta do LLM é transmitida (*streaming*) e começa a ser falada na primeira frase, sem esperar o texto completo.
- **Pipeline concorrente:** geração de texto, síntese de áudio (processo separado) e reprodução (thread dedicada) rodam em paralelo, ligados por filas.
- **Tool calling:** o agente decide quando chamar ferramentas Python (data e hora, informações de hardware) via decorator `@tool`.
- **Personalidade configurável:** system prompt com persona, tom adaptável e "honestidade radical", versionado em código.
- **Latência controlada:** warm-up do LLM e do TTS na inicialização, `keep_alive` no Ollama e sessão ONNX otimizada.

## 🏗️ Arquitetura

```
 Você (texto)
     │
     ▼
┌──────────┐   tokens (stream)   ┌───────────────────┐
│  Agent   │ ──────────────────► │  StreamingVoice   │
│ Strands  │                     │  buffer + regex   │
│ + Ollama │                     │  de pausas (.!?,) │
└────┬─────┘                     └─────────┬─────────┘
     │ tool calls                          │ frases  (multiprocessing.Queue)
     ▼                                     ▼
┌──────────┐                     ┌───────────────────┐
│  Tools   │                     │ Processo TTS      │
│ time ... │                     │ Kokoro ONNX       │
└──────────┘                     │ (voz pm_alex)     │
                                 └─────────┬─────────┘
                                           │ samples PCM 24 kHz (Queue)
                                           ▼
                                 ┌───────────────────┐
                                 │ Thread de áudio   │
                                 │ sounddevice       │
                                 └───────────────────┘
```

### Decisões técnicas

| Problema | Solução |
|---|---|
| Falar sem esperar a resposta completa | Buffer incremental que quebra o stream em frases por pontuação forte (`.!?`) e, em frases longas, por pausas fracas (`,;:`) |
| Inferência TTS bloqueando o agente (GIL) | Kokoro roda em um `multiprocessing.Process` separado |
| Áudio picotado | Fila de samples + thread única de playback |
| Markdown/emojis sendo lidos em voz alta | `clean_for_speech` remove links, títulos, listas, símbolos e emojis antes da síntese |
| Resposta antiga continuar falando em novo turno | A fila de fala é esvaziada a cada novo ciclo do agente |
| Primeira resposta lenta | Warm-up do agente e do modelo de voz na inicialização |

## 📁 Estrutura

```
tony-agent/
├── main.py              # Loop interativo (CLI)
├── agent.py             # Agent Strands + modelo Ollama + wiring da voz
├── assistant_config.py  # Persona e system prompts do Tony
├── decorators/
│   └── profiling.py     # Decorator para medir tempo de resposta
├── tools/
│   ├── time.py          # Tool: data e hora atuais
│   ├── hardware.py      # Tool: informações de SO, RAM e disco
│   ├── speak.py         # StreamingVoice: stream → frases → áudio
│   └── tts/
│       ├── process_tts.py   # Worker Kokoro ONNX + limpeza de texto
│       └── kokoro/onnx/     # Modelo e vozes (baixados, fora do git)
└── voices/               # Vozes customizadas
```

## 🚀 Como rodar

**Pré-requisitos:** Python 3.12+, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com), e `portaudio` (para `sounddevice`/`pyaudio`).

```bash
git clone <url-do-repositorio> && cd tony-agent

# modelo de linguagem
ollama pull qwen2.5:7b

# modelo de voz (Kokoro ONNX, ~350 MB, não versionado)
mkdir -p tools/tts/kokoro/onnx && cd tools/tts/kokoro/onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd -

# dependências
uv sync

# executar
uv run main.py
```

Digite sua pergunta no terminal: o Tony responde em texto **e** em voz.

### 💬 Exemplo de conversa

```text
Bom dia! Como posso ajudar você hoje?

Tony está pronto! (ctrl+c para sair)

Você: O que é suco?
Suco é uma bebida feita pela extração ou pressão de sucos de frutas, vegetais ou
ervas. Geralmente não contém adição de açúcar e pode ser consumido para obter
nutrientes direto das frutas ou vegetais usadas na preparação. Você quer saber
mais sobre sucos?

Você: Conte uma curiosidade sobre sucos
Claro! Uma curiosidade interessante sobre sucos é que eles podem ser muito
calóricos. Um copo grande de suco de laranja pode conter cerca de 200 a 300
calorias, quase o mesmo que uma fatia grande de bolo! Isso ocorre porque os
sucos retiram a fibra das frutas e concentram o açúcar natural delas.

Você: Como eu faço um suco de manga
Fazer um suco de manga é bem simples! Aqui está uma receita básica:

1. Preparação: escolha mangas maduras e lave-as bem.
2. Descascamento e corte: descasque e corte em pedaços menores.
3. Processamento: bata no liquidificador, com um pouco de água ou leite se preferir.
4. Ajuste de sabor (opcional): mel, gengibre, gotas de limão ou gelo.
5. Sirva imediatamente.
```

**Usando uma ferramenta (tool calling):** ao perguntar sobre a máquina, o agente decide sozinho chamar `get_hardware_information` e responde com dados reais.

```text
Você: Qual é informacões do meu computador?
Seu computador está rodando o sistema operacional Ubuntu 26.04.1 LTS - Linux. Ele
tem aproximadamente 19.7 GB de memória RAM e um disco rígido total de 982.2 GB,
com cerca de 652.8 GB em uso. Estes são os detalhes que pude coletar para você.
```

> A resposta é falada em voz alta conforme o texto é gerado. O tempo total por
> pergunta (medido pelo decorator `@profiling`) foi de ~12 s a ~84 s nesse teste,
> rodando em CPU com Qwen2.5 7B, e varia com o tamanho da resposta e o hardware.

## ⚙️ Configuração

| O que | Onde |
|---|---|
| Modelo, host e temperatura do LLM | `agent.py` (`OllamaModel`) |
| Persona e tom | `assistant_config.py` |
| Voz, velocidade e idioma | `tools/tts/process_tts.py` (`pm_alex`, `speed=1.2`, `pt-br`) |
| Tamanho mínimo/máximo de frase falada | `tools/speak.py` (`_MIN_WORD_TO_SPEAK`, `_MAX_WORD_COUNTER`) |
| Threads do ONNX Runtime | `tools/tts/process_tts.py` (`sess_options`) |

### Criando uma nova ferramenta

```python
from strands import tool

@tool
def minha_ferramenta(param: str) -> str:
    """Descrição que o LLM usa para decidir quando chamar."""
    return "resultado"
```

Depois registre em `agent.py`: `tools=[time.currentDateAndTime, get_hardware_information, minha_ferramenta]`.

## 🗺️ Roadmap

- [ ] Entrada por voz (STT com `faster-whisper`, já listado nas dependências)
- [ ] Mais ferramentas (agenda, busca web, controle do sistema)
- [ ] Memória de longo prazo entre sessões
- [ ] Interrupção da fala (*barge-in*)
- [ ] Testes automatizados para o pipeline de fala

## 🧰 Stack

`Python 3.12` · `Strands Agents` · `Ollama (Qwen2.5 7B)` · `Kokoro ONNX` · `ONNX Runtime` · `sounddevice` · `faster-whisper` · `uv`

## 👤 Autor

**Matheus Todao**
