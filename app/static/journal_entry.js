function shareViaEmail() {
  var email = prompt("Please enter your email address:")
  if (email) {
    var payload = {
      date: date,
      email: email,
    }
    fetch("/email_content", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then((response) => {
        if (response.ok) {
          alert("Email sent successfully!")
        } else {
          alert("Failed to send email.")
        }
      })
      .catch((error) => {
        console.error("Error:", error)
        alert("An error occurred while sending the email.")
      })
  }
}
