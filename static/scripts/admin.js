function toggleAddEventForm() {
    const form = document.getElementById("add-event-form");
    form.classList.toggle("hidden");
}

function confirmDelete(eventId) {
    if (!confirm("Are you sure you want to delete this event?")) return;

    fetch(`/admin/delete/${eventId}`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() } // Include if CSRF is used
    })
    .then(response => {
        if (response.ok) {
            document.querySelector(`[data-event-id="${eventId}"]`).remove();
        } else {
            alert("Failed to delete event.");
        }
    });
}

function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}
