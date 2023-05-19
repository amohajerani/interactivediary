// Fetch initial list of subscriptions
fetch("/get-subscriptions")
  .then((response) => response.json())
  .then((subscriptions) => {
    const subscriptionList = document.querySelector("#subscription-list")
    subscriptions.forEach((subscription) => {
      console.log("subscription: ", subscription)
      const listItem = document.createElement("li")
      const link = document.createElement("a")
      const encodedSubscription = encodeURIComponent(subscription)
      link.href = "/subscription/" + encodedSubscription
      link.textContent = subscription
      listItem.appendChild(link)
      subscriptionList.appendChild(listItem)
    })
  })
  .catch((error) => console.log(error))

// Fetch initial list of subscribers
fetch("/get-subscribers")
  .then((response) => response.json())
  .then((subscribers) => {
    const subscriberList = document.querySelector("#subscriber-list")
    subscribers.forEach((subscriber) => {
      const listItem = document.createElement("li")
      listItem.textContent = subscriber
      const deleteButton = document.createElement("button")
      deleteButton.classList.add("btn")
      deleteButton.dataset.email = subscriber
      deleteButton.textContent = "Delete"
      deleteButton.addEventListener("click", (event) => {
        const email = deleteButton.dataset.email
        const listItem = deleteButton.parentElement
        removeSubscriber(email, listItem)
      })
      listItem.appendChild(deleteButton)
      subscriberList.appendChild(listItem)
    })
  })
  .catch((error) => console.log(error))

// Add event listener to subscribe form
const subscribeForm = document.querySelector("#subscribe-form")
subscribeForm.addEventListener("submit", (event) => {
  event.preventDefault()
  const emailInput = document.querySelector("#email")
  const email = emailInput.value
  addSubscriber(email)
  emailInput.value = ""
})

// Function to add subscriber
function addSubscriber(email) {
  fetch("/add-subscriber", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `email=${encodeURIComponent(email)}`,
  })
    .then((response) => response.text())
    .then((subscriber) => {
      const subscriberList = document.querySelector("#subscriber-list")
      const listItem = document.createElement("li")
      listItem.textContent = subscriber
      const deleteButton = document.createElement("button")
      deleteButton.classList.add("btn btn-primary")
      deleteButton.dataset.email = subscriber
      deleteButton.textContent = "Delete"
      deleteButton.addEventListener("click", (event) => {
        const email = deleteButton.dataset.email
        const listItem = deleteButton.parentElement
        removeSubscriber(email, listItem)
      })
      listItem.appendChild(deleteButton)
      subscriberList.appendChild(listItem)
    })
    .catch((error) => console.log(error))
}

// Function to remove subscriber
function removeSubscriber(email, listItem) {
  fetch("/remove-subscriber", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `email=${encodeURIComponent(email)}`,
  })
    .then((response) => {
      if (response.ok) {
        listItem.remove()
      } else {
        console.log("Error removing subscriber")
      }
    })
    .catch((error) => console.log(error))
}
