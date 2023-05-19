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
        appendMessageToHistory("assistant", response, true)
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
    if (message.role === "assistant" && italic) {
      messageContent = `<em>${messageContent}</em>` // Wrap assistant message in <em> tags for italic styling
    }
    historyHTML += `<p>${messageContent}</p>`
  }
  document.getElementById("history").innerHTML = historyHTML
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
