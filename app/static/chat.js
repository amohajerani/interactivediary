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
        appendMessageToHistory("assistant", response)
      }
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

function appendMessageToHistory(role, content) {
  chatHistory.push({ role, content })
  let historyHTML = ""
  for (const message of chatHistory) {
    historyHTML += `<p class="${message.role}"><strong>${
      message.role === "user" ? "User" : "AI"
    }:</strong> ${message.content}</p>`
  }
  document.getElementById("history").innerHTML = historyHTML
}
