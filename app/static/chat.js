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
    let messageContent = message.content
    let messageHTML = `<p>${messageContent}</p>`;
    if (message.role === "assistant") {
      if (message === chatHistory[chatHistory.length - 1]) { // Check if it's the last message in the history
        const upButton = document.createElement('button');
        upButton.className = "fa fa-thumbs-up";
        upButton.addEventListener('click', () => sendFeedback("entry_id", messageContent, 1));

        const downButton = document.createElement('button');
        downButton.className = "fa fa-thumbs-down";
        downButton.addEventListener('click', () => sendFeedback("entry_id", messageContent, -1));

        messageHTML = `
<p class="assistant-text">
  ${messageContent}
  <span class="feedback">
    ${upButton.outerHTML}
    ${downButton.outerHTML}
  </span>
</p>`;
      } else {
        messageHTML = `<p class="assistant-text">${messageContent}</p>`;
      }
    }
    if (message.role === "insights") {
      historyHTML += `<strong><em>Insights: </em></strong>`
      messageHTML = `<em>${messageHTML}</em>`
    }
    if (message.role === "actions") {
      historyHTML += `<strong><em>Actions: </em></strong>`
      messageHTML = `<em>${messageHTML}</em>`
    }
    historyHTML += messageHTML
  }

  document.getElementById("history").innerHTML = historyHTML
}


// Retrieve the chat history from the rendered HTML and update chatHistory array
const chatHistoryElement = document.getElementById("history")
const initialChatHistory = chatHistoryElement.querySelectorAll("p")
var role = "user"
for (const messageElement of initialChatHistory) {
  const content = messageElement.innerHTML
  chatHistory.push({ role, content })
  if (role=='user') {
     role = "assistant"}
  else {role = 'user'}
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
    .then((response) => response.json()) // Parse the response as JSON
    .then((response) => {
      response.forEach((item) => {
        // Perform operations with each item in the array
        appendMessageToHistory("actions", item, true);
      });
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}


function doneFunc(entry_id) {
  fetch("/entry-done/" + entry_id)
    .then(function(response) {
      if (response.ok) {
        sendMessage(entry_id);
        window.location.href = '/';
      } else {
        console.error('Redirect failed');
      }
    })
    .catch(function(error) {
      console.error('An error occurred:', error);
    });
}


function submitEntryTitle(entry_id) {
  var entryTitle = document.getElementById("entryTitle").value;
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
function sendFeedback(entry_id, content, feedback) {
  const feedbackData = {
    entry_id: entry_id,
    content:content,
    feedback: feedback
  };
  fetch('/chat-feedback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(feedbackData)
  })
  .then(response => {
    if (response.ok) {
      console.log('Feedback sent successfully');
      // Perform any additional actions upon successful feedback submission
    } else {
      console.log('Failed to send feedback');
      // Handle any errors or display appropriate error message
    }
  })
  .catch(error => {
    console.log('Error:', error);
    // Handle any errors or display appropriate error message
  });
}