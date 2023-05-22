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
    }),
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("user", message)
      if (!quietMode) {
        appendMessageToHistory("bot", response)
      }
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}
let historyHTML = ""
function appendMessageToHistory(role, content) {
  if (role === "user") {
    historyHTML += `<p>${content}</p>`
  }
  if (role === "bot") {
    historyHTML += `<em>${content}</em>`
  }
  if (role === "summary") {
    historyHTML += `<strong><em>Summary: </em></strong>`
  }
  if (role === "summary") {
    historyHTML += `<em>${content}</em>`
  }
  if (role === "insights") {
    historyHTML += `<strong><em>Insights: </em></strong>`
  }
  if (role === "insights") {
    historyHTML += `<em>${content}</em>`
  }
  document.getElementById("history").innerHTML = historyHTML
}
// the snippet below is not in a function. It runs everytime you load the page.
//
// Retrieve the chat history from the rendered HTML and update chatHistory array
//const chatHistoryElement = document.getElementById("history")
//const initialChatHistory = chatHistoryElement.querySelectorAll("p")
//for (const messageElement of initialChatHistory) {
//  const role = "bot" // Assuming all initial messages are from the bot
//  const content = messageElement.innerHTML
//  chatHistory.push({ role, content })
//}

function sendSummary() {
  fetch("/analyze/summary", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("summary", response)
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
      appendMessageToHistory("insights", response)
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

function doneFunc() {
  window.location.href = "/"
  fetch("/analyze/done")
}
