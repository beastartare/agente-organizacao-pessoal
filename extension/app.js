const API_URL = "http://127.0.0.1:5000";
let historyLoaded = false;
let serverRetryTimer = null;

function createOrbiaPanel() {
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
    window.__orbiaClosed = true;
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

  enablePanelDragging(panel);

  loadHistory();
}

function enablePanelDragging(panel) {
  const header = panel.querySelector("#orbia-header");

  if (!header) {
    return;
  }

  let isDragging = false;
  let offsetX = 0;
  let offsetY = 0;

  header.addEventListener("pointerdown", (event) => {
    if (event.target.closest("#orbia-close")) {
      return;
    }

    isDragging = true;

    const rect = panel.getBoundingClientRect();

    offsetX = event.clientX - rect.left;
    offsetY = event.clientY - rect.top;

    panel.style.setProperty("left", `${rect.left}px`, "important");

    panel.style.setProperty("top", `${rect.top}px`, "important");

    panel.style.setProperty("right", "auto", "important");

    header.setPointerCapture(event.pointerId);

    header.style.cursor = "grabbing";
  });

  header.addEventListener("pointermove", (event) => {
    if (!isDragging) {
      return;
    }

    const panelWidth = panel.offsetWidth;
    const panelHeight = panel.offsetHeight;

    let left = event.clientX - offsetX;
    let top = event.clientY - offsetY;

    const maxLeft = window.innerWidth - panelWidth;
    const maxTop = window.innerHeight - panelHeight;

    left = Math.max(0, Math.min(left, maxLeft));

    top = Math.max(0, Math.min(top, maxTop));

    panel.style.setProperty("left", `${left}px`, "important");

    panel.style.setProperty("top", `${top}px`, "important");
  });

  header.addEventListener("pointerup", (event) => {
    isDragging = false;

    if (header.hasPointerCapture(event.pointerId)) {
      header.releasePointerCapture(event.pointerId);
    }

    header.style.cursor = "grab";
  });

  header.addEventListener("pointercancel", () => {
    isDragging = false;
    header.style.cursor = "grab";
  });
}

function requestApi(endpoint, options = {}) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      {
        type: "orbia-api-request",
        endpoint,
        method: options.method || "GET",
        body: options.body,
      },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(
            new Error(
              chrome.runtime.lastError.message ||
                "Erro na comunicação com a extensão.",
            ),
          );

          return;
        }

        if (!response) {
          reject(new Error("A extensão não respondeu à solicitação."));

          return;
        }

        if (!response.success) {
          reject(
            new Error(
              response.error || "Não foi possível comunicar com o servidor.",
            ),
          );

          return;
        }

        resolve(response.data);
      },
    );
  });
}

async function loadHistory(retry = 0) {
  const chat = document.getElementById("orbia-chat");

  if (!chat) {
    return;
  }

  try {
    const data = await requestApi("/history");

    chat.innerHTML = "";
    historyLoaded = true;

    if (!data.messages || data.messages.length === 0) {
      addOrbiaMessage(
        "orbia",
        "Olá! Sou a Orbia, sua assistente de organização. 🌟",
      );
    } else {
      data.messages.forEach((message) => {
        addOrbiaMessage(message.role, message.content);
      });
    }

    const pendingEvents = normalizePendingEvents(data.pending_plan);

    if (pendingEvents.length > 0) {
      appendSchedule(pendingEvents);
    }

    scrollToBottom();
  } catch (error) {
    console.error(error);

    if (retry < 10 && document.getElementById("orbia-panel")) {
      clearTimeout(serverRetryTimer);

      serverRetryTimer = setTimeout(() => {
        loadHistory(retry + 1);
      }, 1000);

      return;
    }

    if (!historyLoaded && document.getElementById("orbia-chat")) {
      if (chat.children.length === 0) {
        addOrbiaMessage(
          "orbia",
          "Olá! Sou a Orbia, sua assistente de organização. 🌟",
        );
      }
    }
  }
}

function normalizePendingEvents(pendingPlan) {
  if (!pendingPlan) {
    return [];
  }

  if (Array.isArray(pendingPlan)) {
    return pendingPlan;
  }

  if (Array.isArray(pendingPlan.new_events)) {
    return pendingPlan.new_events;
  }

  if (Array.isArray(pendingPlan.events)) {
    return pendingPlan.events;
  }

  return [];
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
    const data = await requestApi("/chat", {
      method: "POST",
      body: {
        message: text,
      },
    });

    typing.remove();

    addOrbiaMessage("orbia", data.response);

    const pendingEvents = normalizePendingEvents(data.events);

    if (pendingEvents.length > 0) {
      appendSchedule(pendingEvents);
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

  if (!chat || !events || events.length === 0) {
    return;
  }

  const existingPendingCard = chat.querySelector(".orbia-schedule-card");

  if (existingPendingCard) {
    existingPendingCard.parentElement.remove();
  }

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
    const data = await requestApi("/approve", {
      method: "POST",
    });

    if (!data || data.success === false) {
      throw new Error(data?.message || "Erro ao aprovar cronograma.");
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
      `⚠️ ${error.message || "Não consegui adicionar os eventos ao Google Calendar."}`,
    );
  }
}

function addOrbiaMessage(role, text) {
  const chat = document.getElementById("orbia-chat");

  if (!chat) {
    return;
  }

  const message = document.createElement("div");

  message.className = `orbia-message ${role}`;

  const label = document.createElement("div");

  label.className = "orbia-label";

  label.textContent = role === "user" ? "Você" : "Orbia";

  const bubble = document.createElement("div");

  bubble.className = "orbia-bubble";

  bubble.innerHTML = formatMessage(text);

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

function formatMessage(text) {
  if (!text) {
    return "";
  }

  let result = escapeHtml(text);

  result = result.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  result = result.replace(/\n/g, "<br>");

  return result;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function scrollToBottom() {
  const chat = document.getElementById("orbia-chat");

  if (!chat) {
    return;
  }

  chat.scrollTop = chat.scrollHeight;
}

function initPopup() {
  const chatArea = document.getElementById("chat-area");

  const userInput = document.getElementById("user-input");

  const sendBtn = document.getElementById("send-btn");

  if (!chatArea || !userInput || !sendBtn) {
    return;
  }

  userInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      sendPopupMessage();
    }
  });

  sendBtn.addEventListener("click", sendPopupMessage);

  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";

    userInput.style.height = Math.min(userInput.scrollHeight, 100) + "px";
  });

  loadPopupHistory();
}

async function sendPopupMessage() {
  const userInput = document.getElementById("user-input");

  const sendBtn = document.getElementById("send-btn");

  const text = userInput.value.trim();

  if (!text) {
    return;
  }

  appendPopupMessage("user", text);

  userInput.value = "";

  userInput.style.height = "auto";

  sendBtn.disabled = true;

  const typing = appendPopupTyping();

  try {
    const data = await requestApi("/chat", {
      method: "POST",
      body: {
        message: text,
      },
    });

    typing.remove();

    appendPopupMessage("orbia", data.response);

    const pendingEvents = normalizePendingEvents(data.events);

    if (pendingEvents.length > 0) {
      appendPopupSchedule(pendingEvents);
    }
  } catch (error) {
    typing.remove();

    appendPopupMessage(
      "orbia",
      "Não consegui me conectar ao servidor do Orbia.",
    );

    console.error(error);
  } finally {
    sendBtn.disabled = false;

    userInput.focus();
  }
}

async function loadPopupHistory(retry = 0) {
  const chatArea = document.getElementById("chat-area");

  if (!chatArea) {
    return;
  }

  try {
    const data = await requestApi("/history");

    chatArea.innerHTML = "";

    if (!data.messages || data.messages.length === 0) {
      appendPopupMessage(
        "orbia",
        "Olá! Sou a Orbia, sua assistente de organização. 🌟",
      );
    } else {
      data.messages.forEach((message) => {
        appendPopupMessage(message.role, message.content);
      });
    }

    const pendingEvents = normalizePendingEvents(data.pending_plan);

    if (pendingEvents.length > 0) {
      appendPopupSchedule(pendingEvents);
    }

    scrollPopupToBottom();
  } catch (error) {
    console.error(error);

    if (retry < 10) {
      setTimeout(() => {
        loadPopupHistory(retry + 1);
      }, 1000);
    }
  }
}

function appendPopupSchedule(events) {
  const chatArea = document.getElementById("chat-area");

  if (!chatArea || !events || events.length === 0) {
    return;
  }

  const message = document.createElement("div");

  message.className = "message orbia";

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
    <div class="label">
      Orbia
    </div>

    <div class="orbia-schedule-card">
      <h4>
        📅 Cronograma proposto
      </h4>

      ${eventItems}

      <button class="orbia-approve-btn">
        ✅ Aprovar e adicionar à agenda
      </button>
    </div>
  `;

  chatArea.appendChild(message);

  const button = message.querySelector(".orbia-approve-btn");

  button.addEventListener("click", () => approvePopupSchedule(button));

  scrollPopupToBottom();
}

async function approvePopupSchedule(button) {
  button.disabled = true;

  button.textContent = "Adicionando...";

  try {
    const data = await requestApi("/approve", {
      method: "POST",
    });

    if (!data || data.success === false) {
      throw new Error(data?.message || "Erro ao aprovar cronograma.");
    }

    button.textContent = "✅ Adicionado à agenda";

    button.classList.add("approved");

    appendPopupMessage(
      "orbia",
      data.response ||
        "Pronto! Os eventos foram adicionados ao Google Calendar. 🎯",
    );
  } catch (error) {
    console.error(error);

    button.disabled = false;

    button.textContent = "✅ Aprovar e adicionar à agenda";

    appendPopupMessage(
      "orbia",
      `⚠️ ${error.message || "Não consegui adicionar os eventos ao Google Calendar."}`,
    );
  }
}

function appendPopupMessage(role, text) {
  const chatArea = document.getElementById("chat-area");

  if (!chatArea) {
    return;
  }

  const div = document.createElement("div");

  div.className = `message ${role}`;

  const label = document.createElement("div");

  label.className = "label";

  label.textContent = role === "user" ? "Você" : "Orbia";

  const bubble = document.createElement("div");

  bubble.className = "bubble";

  bubble.innerHTML = formatMessage(text);

  div.appendChild(label);

  div.appendChild(bubble);

  chatArea.appendChild(div);

  scrollPopupToBottom();
}

function appendPopupTyping() {
  const chatArea = document.getElementById("chat-area");

  const div = document.createElement("div");

  div.className = "message orbia";

  div.innerHTML = `
        <div class="label">
            Orbia
        </div>

        <div class="typing">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;

  chatArea.appendChild(div);

  scrollPopupToBottom();

  return div;
}

function scrollPopupToBottom() {
  const chatArea = document.getElementById("chat-area");

  if (!chatArea) {
    return;
  }

  chatArea.scrollTop = chatArea.scrollHeight;
}

function initializeOrbia() {
  if (
    window.location.hostname === "calendar.google.com" &&
    !window.__orbiaInitialized
  ) {
    window.__orbiaInitialized = true;

    createOrbiaPanel();
  }

  if (document.getElementById("orbia-popup")) {
    initPopup();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeOrbia);
} else {
  initializeOrbia();
}
