const API_URL = "http://127.0.0.1:5000";

const chatArea = document.getElementById("chat-area");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const toast = document.getElementById("toast");

userInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();

    sendMessage();
  }
});

sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("input", () => {
  userInput.style.height = "auto";

  userInput.style.height = Math.min(userInput.scrollHeight, 100) + "px";
});

async function sendMessage() {
  const text = userInput.value.trim();

  if (!text) {
    return;
  }

  appendMessage("user", text);

  userInput.value = "";

  userInput.style.height = "auto";

  sendBtn.disabled = true;

  const typing = appendTyping();

  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        message: text,
      }),
    });

    typing.remove();

    if (!response.ok) {
      throw new Error("Erro ao comunicar com o servidor.");
    }

    const data = await response.json();

    appendMessage("orbia", data.response);
  } catch (error) {
    typing.remove();

    appendMessage("orbia", "Não consegui me conectar ao servidor do Orbia.");

    showToast("Servidor offline.", "error");

    console.error(error);
  } finally {
    sendBtn.disabled = false;

    userInput.focus();
  }
}

function appendMessage(role, text) {
  const div = document.createElement("div");

  div.className = `message ${role}`;

  const label = document.createElement("div");

  label.className = "label";

  label.textContent = role === "user" ? "Você" : "Orbia";

  const bubble = document.createElement("div");

  bubble.className = "bubble";

  bubble.textContent = text;

  div.appendChild(label);

  div.appendChild(bubble);

  chatArea.appendChild(div);

  scrollToBottom();
}

function appendTyping() {
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

  scrollToBottom();

  return div;
}

function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function showToast(message, type = "") {
  toast.textContent = message;

  toast.className = `toast ${type} show`;

  setTimeout(() => {
    toast.className = "toast";
  }, 3500);
}
