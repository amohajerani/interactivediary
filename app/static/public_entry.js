   // JavaScript code to handle form submission and update comments dynamically

    // Listen for form submission
    document.getElementById("commentForm").addEventListener("submit", function(event) {
        event.preventDefault(); // Prevent the default form submission
  
        // Get form data
        var formData = new FormData(this);
  
        // Send form data to the server
        fetch(this.action, {
          method: this.method,
          body: formData
        })
        .then(response => response.json()) // Assuming the server returns comments in JSON format
        .then(data => {
          // Update the comments section with the new comment
          var commentsContainer = document.getElementById("commentsContainer");
  
          // Clear the existing comments
          commentsContainer.innerHTML = "";
        console.log(data)
          // Render the updated comments
          data.forEach(function(comment) {
            var commentDiv = document.createElement("div");
            var commentParagraph = document.createElement("p");
            commentParagraph.textContent = comment.text;
            commentDiv.appendChild(commentParagraph);
            commentsContainer.appendChild(commentDiv);
  
            var hrElement = document.createElement("hr");
            hrElement.className = "faint-line";
            commentsContainer.appendChild(hrElement);
          });
        })
        .catch(error => {
          console.error("Error:", error);
        });
      });