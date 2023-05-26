
  function deleteItem(element, entry_id) {
    var listItem = element.parentNode;
    var confirmation = confirm("Are you sure you want to delete the entry?");
    if (confirmation) {

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
        listItem.parentNode.removeChild(listItem);
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
}