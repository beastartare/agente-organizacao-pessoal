const API_URL = "http://127.0.0.1:5000";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "orbia-api-request") {
    return;
  }

  handleApiRequest(message)
    .then((result) => {
      sendResponse({
        success: true,
        data: result,
      });
    })
    .catch((error) => {
      console.error("Erro na comunicação com a API do Orbia:", error);

      sendResponse({
        success: false,
        error: error.message || "Erro ao comunicar com o servidor.",
      });
    });

  return true;
});

async function handleApiRequest(message) {
  const options = {
    method: message.method || "GET",
    cache: "no-store",
  };

  if (message.body !== undefined) {
    options.headers = {
      "Content-Type": "application/json",
    };

    options.body = JSON.stringify(message.body);
  }

  const response = await fetch(`${API_URL}${message.endpoint}`, options);

  let data = {};

  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      data.message || data.detail || `Erro HTTP ${response.status}`,
    );
  }

  return data;
}
