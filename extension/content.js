function createOrbiaPanel() {
  // Evita criar o painel mais de uma vez
  if (document.getElementById("orbia-panel")) {
    return;
  }

  const panel = document.createElement("div");

  panel.id = "orbia-panel";

  panel.innerHTML = `

        <div id="orbia-header">

            <div id="orbia-logo">
                🪐
            </div>

            <div id="orbia-header-text">

                <h1>
                    Orbia
                </h1>

                <p>
                    Seu agente de organização pessoal
                </p>

            </div>

            <button
                id="orbia-close"
                title="Fechar Orbia"
            >
                ×
            </button>

        </div>


        <div id="orbia-chat">

            <div class="orbia-message orbia">

                <div class="orbia-label">
                    Orbia
                </div>

                <div class="orbia-bubble">
                    Olá! Sou a Orbia, sua assistente
                    de organização. 🌟
                </div>

            </div>

        </div>


        <div id="orbia-input-area">

            <textarea
                id="orbia-input"
                placeholder="Digite suas tarefas ou perguntas..."
                rows="1"
            ></textarea>


            <button
                id="orbia-send"
                title="Enviar"
            >

                <svg
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <path
                        d="M2 21l21-9L2 3v7l15-2-15-2z"
                    />
                </svg>

            </button>

        </div>

    `;

  document.body.appendChild(panel);

  document.getElementById("orbia-close").addEventListener("click", () => {
    panel.remove();
  });

  document
    .getElementById("orbia-send")
    .addEventListener("click", sendOrbiaMessage);

  document
    .getElementById("orbia-input")
    .addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();

        sendOrbiaMessage();
      }
    });
}

async function sendOrbiaMessage() {
  const input = document.getElementById("orbia-input");

  const sendButton = document.getElementById("orbia-send");

  const text = input.value.trim();

  if (!text) {
    return;
  }

  addOrbiaMessage("user", text);

  input.value = "";

  input.style.height = "auto";

  sendButton.disabled = true;

  const typing = addTyping();

  try {
    const response = await fetch("http://127.0.0.1:5000/chat", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        message: text,
      }),
    });

    if (!response.ok) {
      throw new Error("Erro na API.");
    }

    const data = await response.json();

    typing.remove();

    addOrbiaMessage("orbia", data.response);

    // Se o Gemini criou uma proposta,
    // mostra o card de aprovação
    if (data.events && data.events.length > 0) {
      appendSchedule(data.events);
    }
  } catch (error) {
    console.error(error);

    typing.remove();

    addOrbiaMessage(
      "orbia",
      "⚠️ Não consegui me conectar ao servidor do Orbia. Verifique se o backend está rodando.",
    );
  } finally {
    sendButton.disabled = false;

    input.focus();
  }
}

function appendSchedule(events) {
  const chat = document.getElementById("orbia-chat");

  const message = document.createElement("div");

  message.className = "orbia-message orbia";

  const eventItems = events
    .map((event) => {
      const start = formatDateTime(event.start_datetime);

      const end = formatDateTime(event.end_datetime);

      return `

                        <div class="orbia-event-item">

                            <div class="orbia-event-dot"></div>

                            <div>

                                <div class="orbia-event-title">
                                    ${escapeHtml(event.title)}
                                </div>

                                <div class="orbia-event-time">
                                    ${start} → ${end}
                                </div>

                            </div>

                        </div>

                    `;
    })
    .join("");

  message.innerHTML = `

        <div class="orbia-label">
            Orbia
        </div>


        <div class="orbia-schedule-card">

            <h4>
                📅 Cronograma proposto
            </h4>


            ${eventItems}


            <button
                class="orbia-approve-btn"
            >
                ✅ Aprovar e adicionar à agenda
            </button>

        </div>

    `;

  chat.appendChild(message);

  const button = message.querySelector(".orbia-approve-btn");

  button.addEventListener("click", () => approveSchedule(button, message));

  scrollToBottom();
}

async function approveSchedule(button, message) {
  button.disabled = true;

  button.textContent = "Adicionando...";

  try {
    const response = await fetch("http://127.0.0.1:5000/approve", {
      method: "POST",
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || "Erro ao aprovar cronograma.");
    }

    button.textContent = "✅ Adicionado à agenda";

    button.classList.add("approved");

    addOrbiaMessage(
      "orbia",
      data.response ||
        "Pronto! Os eventos foram adicionados ao Google Calendar. 🎯",
    );
  } catch (error) {
    console.error(error);

    button.disabled = false;

    button.textContent = "✅ Aprovar e adicionar à agenda";

    addOrbiaMessage(
      "orbia",
      "⚠️ Não consegui adicionar os eventos ao Google Calendar.",
    );
  }
}

function addOrbiaMessage(role, text) {
  const chat = document.getElementById("orbia-chat");

  const message = document.createElement("div");

  message.className = `orbia-message ${role}`;

  const label = document.createElement("div");

  label.className = "orbia-label";

  label.textContent = role === "user" ? "Você" : "Orbia";

  const bubble = document.createElement("div");

  bubble.className = "orbia-bubble";

  bubble.textContent = text;

  message.appendChild(label);

  message.appendChild(bubble);

  chat.appendChild(message);

  scrollToBottom();
}

function addTyping() {
  const chat = document.getElementById("orbia-chat");

  const message = document.createElement("div");

  message.className = "orbia-message orbia";

  message.innerHTML = `

        <div class="orbia-label">
            Orbia
        </div>

        <div class="orbia-typing">

            <span></span>
            <span></span>
            <span></span>

        </div>

    `;

  chat.appendChild(message);

  scrollToBottom();

  return message;
}

function formatDateTime(isoString) {
  if (!isoString) {
    return "";
  }

  const date = new Date(isoString);

  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")

    .replace(/</g, "&lt;")

    .replace(/>/g, "&gt;");
}

function scrollToBottom() {
  const chat = document.getElementById("orbia-chat");

  chat.scrollTop = chat.scrollHeight;
}

createOrbiaPanel();
