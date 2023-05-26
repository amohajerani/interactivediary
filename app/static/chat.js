let quietMode = false

// Add event listener to checkbox
const checkbox = document.getElementById("quietToggle")
checkbox.addEventListener("change", function () {
  quietMode = this.checked
})

let chatHistory = []

function sendMessage(entry_id) {
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
      entry_id: entry_id,
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
      messageContent = `<em>${messageContent}</em>`
    }
    if (message.role === "summary") {
      historyHTML += `<strong><em>Summary: </em></strong>`
      messageContent = `<em>${messageContent}</em>`
    }
    if (message.role === "insights") {
      historyHTML += `<strong><em>Insights: </em></strong>`
      messageContent = `<em>${messageContent}</em>`
    }
    if (message.role === "actions") {
      historyHTML += `<strong><em>Actions: </em></strong>`
      messageContent = `<em>${messageContent}</em>`
    }
    historyHTML += `<p>${messageContent}</p>`
  }

  document.getElementById("history").innerHTML = historyHTML
}

// Retrieve the chat history from the rendered HTML and update chatHistory array
const chatHistoryElement = document.getElementById("history")
const initialChatHistory = chatHistoryElement.querySelectorAll("p")
for (const messageElement of initialChatHistory) {
  const role = "assistant" // Assuming all initial messages are from the assistant
  const content = messageElement.innerHTML
  chatHistory.push({ role, content })
}

function sendSummary(entry_id) {
  fetch("/analyze/summary/" + entry_id, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("summary", response, true)
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

function sendInsights(entry_id) {
  fetch("/analyze/insights/" + entry_id, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("insights", response, true)
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

function sendActions(entry_id) {
  fetch("/analyze/actions/" + entry_id, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.text())
    .then((response) => {
      appendMessageToHistory("actions", response, true)
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

async function doneFunc() {
  try {
    await fetch("/entry-done/" + entry_id);
  } catch (error) {
    console.error("An error occurred:", error);
  }
}

function submitEntryTitle(entry_id) {
  var entryTitle = document.getElementById("entryTitle").value;
  var entryTitle = titleInput.value.trim();
  // Make a POST request to the server
  fetch("/entry-title", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: entryTitle,
      entry_id: entry_id,
    }),
  }).catch((error) => {
      // Handle any errors that occurred during the request
      console.error("Error:", error)
    })
}