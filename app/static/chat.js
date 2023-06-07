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
        messageHTML = `
<p class="assistant-text">
  ${messageContent}
  <span class="feedback">
    <button id="upButton" class="fa fa-thumbs-up"></button>
    <button id="downButton" class="fa fa-thumbs-down"></button>
  </span>
</p>`;
      } else {
        messageHTML = `<p class="assistant-text">${messageContent}</p>`;
      }
    }
    // ... rest of your code

  document.getElementById("history").innerHTML = historyHTML

  // Add event listeners after the buttons have been added to the page
  const upButton = document.getElementById("upButton")
  const downButton = document.getElementById("downButton")
  if (upButton && downButton) {
    upButton.addEventListener('click', () => sendFeedback("entry_id", messageContent, 1));
    downButton.addEventListener('click', () => sendFeedback("entry_id", messageContent, -1));
  }
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