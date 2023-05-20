let quietMode = false

// Add event listener to checkbox
const checkbox = document.getElementById("quietToggle")
checkbox.addEventListener("change", function () {
  quietMode = this.checked
})

let chatHistory = []

function sendMessage() {
  const message = document.getElementById("message").value.trim()
  if (message === "") return
  document.getElementById("message").value = ""

  fetch("/get_response", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      quietMode: quietMode,
      msg: message,
      history: chatHistory,
    }),
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("user", message)
      if (!quietMode) {
        appendMessageToHistory("bot", response, true)
      }
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

function appendMessageToHistory(role, content, italic = false) {
  chatHistory.push({ role, content })

  let historyHTML = ""
  for (const message of chatHistory) {
    let messageContent = message.content
    if (message.role === "bot" && italic) {
      messageContent = `<em>${messageContent}</em>` // Wrap bot message in <em> tags for italic styling
    }
    historyHTML += `<p>${messageContent}</p>`
  }

  document.getElementById("history").innerHTML = historyHTML
}

// Retrieve the chat history from the rendered HTML and update chatHistory array
const chatHistoryElement = document.getElementById("history")
const initialChatHistory = chatHistoryElement.querySelectorAll("p")
for (const messageElement of initialChatHistory) {
  const role = "user" // Assuming all initial messages are from the user
  const content = messageElement.innerHTML
  chatHistory.push({ role, content })
}

function sendSummary() {
  fetch("/analyze/summary", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("analysis", response, true)
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

function sendInsights() {
  fetch("/analyze/insights", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("analysis", response, true)
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

function doneFunc() {
  window.location.href = "/"
  fetch("/analyze/done")
}
