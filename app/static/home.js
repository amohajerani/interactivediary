
  function deleteItem(element, entry_id) {
    var listItem = element.parentNode;

    // Send a fetch request to remove the item from the database
    fetch('/delete-entry/' + entry_id, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(response => {
      if (response.ok) {
        // On successful deletion, remove the list item from the DOM
        listItem.remove();
      } else {
        // Handle error case
        console.log('Failed to delete item');
      }
    })
    .catch(error => {
      // Handle network error
      console.log('Network error occurred');
    });
  }