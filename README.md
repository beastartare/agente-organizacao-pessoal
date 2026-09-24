### Orbia - Agente de Organização pessoal integrado ao Google Calendar

O Orbia é um agente de organização pessoal integrado ao Google Calendar. Com ele, o usuário pode organizar sua rotina, informando tanto compromissos fixos quanto atividades específicas para determinado horário, dia ou semana. A partir dessas informações, o Orbia monta um cronograma que pode ser aprovado ou não pelo usuário, considerando eventos já existentes no Google Calendar, hábitos e novos compromissos. O usuário também pode solicitar a criação de treinos personalizados, que podem ser adicionados à agenda após sua aprovação.

## Tecnologias utilizadas

- **Python 3.12**
- **Google Gemini 3.6 Flash**
- **Google Calendar API**
- **SQLite**
- **FastAPI**
- **JavaScript**
- **HTML**
- **CSS**
- **Chrome Extension – Manifest V3**

Principais bibliotecas Python:

- `google-genai`
- `python-dotenv`
- `google-api-python-client`
- `google-auth-httplib2`
- `google-auth-oauthlib`
- `fastapi`
- `uvicorn`

# Execução

### 1. Clonar o repositório

```bash
git clone https://github.com/beastartare/agente-organizacao-pessoal.git
cd orbia
```

### 2. Criar o ambiente virtual

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar as dependências

Com o ambiente virtual ativado:

```bash
pip install -r requirements.txt
```

### 4. Configurar a API do Gemini

O Orbia utiliza a API do Google Gemini para processar as mensagens e gerar as respostas do agente.

Para obter uma chave de API:

1. acesse: https://aistudio.google.com/app/api-keys
2. Faça login com uma conta Google.
3. Acesse a opção de criação de chave de API.
4. Crie uma nova chave.
5. Copie a chave gerada.

Na raiz do projeto, crie um arquivo chamado `.env`:

```text
orbia/
├── .env
├── api.py
├── agent/
├── extension/
└── ...
```

Dentro do `.env`, adicione:

```env
GEMINI_API_KEY=SUA_CHAVE_AQUI
```

Substitua `SUA_CHAVE_AQUI` pela chave obtida no Google AI Studio.

### 5. Configurar o Google Calendar

O Orbia utiliza a Google Calendar API para consultar eventos existentes e criar novos eventos após a aprovação do usuário.

Para configurar a API:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto ou selecione um projeto existente.
3. No menu de APIs e serviços, acesse **Biblioteca**.
4. Procure por **Google Calendar API**.
5. Clique em **Ativar**.
6. Acesse **APIs e serviços → Credenciais**.
7. Clique em **Criar credenciais**.
8. Selecione **ID do cliente OAuth**.
9. Caso seja solicitado, configure a tela de consentimento OAuth.
10. Em tipo de aplicativo, selecione **Aplicativo para computador**.
11. Crie a credencial.
12. Faça o download do arquivo JSON.
13. Renomeie o arquivo para `credentials.json`.
14. Coloque o arquivo na raiz do projeto:

```text
orbia/
├── credentials.json
├── .env
├── api.py
├── agent/
├── extension/
└── ...
```

Na primeira vez que o Orbia precisar acessar o Google Calendar, uma página de autorização do Google será aberta no navegador.

Faça login com a conta que possui o Google Calendar que será utilizado pelo Orbia e autorize o acesso solicitado.

Após a autorização, o Orbia criará automaticamente o arquivo `token.json`.

Esse arquivo será utilizado para evitar que seja necessário realizar a autorização novamente a cada execução.

### 6. Executar o backend

O backend do Orbia é executado através do arquivo `api.py`, que utiliza o Uvicorn para iniciar o servidor FastAPI.

#### Windows

Com o ambiente virtual ativado:

```powershell
python api.py
```

#### Linux/MacOS

```bash
python3 api.py
```

O backend estará disponível em:

```text
http://127.0.0.1:5000
```

Mantenha o servidor em execução enquanto utilizar o Orbia.

### 7. Carregar a extensão

Para utilizar o Orbia diretamente no Google Calendar:

1. Abra o Google Chrome.
2. Acesse:

```text
chrome://extensions/
```

3. Ative o **Modo do desenvolvedor**.
4. Clique em **Carregar sem compactação**.
5. Selecione a pasta `extension/` do projeto.
6. Acesse o [Google Calendar](https://calendar.google.com/).

A extensão do Orbia será carregada diretamente no Google Calendar.
