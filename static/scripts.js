async function deleteQuote(id) {
    if (confirm("Are you sure you want to delete this quote?")) {
        try {
            const response = await fetch(`/api/quotes/${id}`, { method: 'DELETE' });
            if (response.ok) {
                document.getElementById(`quote-${id}`).remove();
                alert("Quote deleted successfully");
            } else {
                alert("Failed to delete quote");
            }
        } catch (error) {
            console.error("Delete error:", error);
            alert("Error deleting quote");
        }
    }
}

function openEditModal(id, quote, author, imagePrompt, imageStyle, keywords) {
    document.getElementById('editId').value = id;
    document.getElementById('editQuote').value = quote;
    document.getElementById('editAuthor').value = author;
    document.getElementById('editImagePrompt').value = imagePrompt;
    document.getElementById('editImageStyle').value = imageStyle;
    document.getElementById('editKeywords').value = keywords;
    document.getElementById('editModal').style.display = 'block';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

async function saveEdit() {
    const id = document.getElementById('editId').value;
    const update = {
        quote: document.getElementById('editQuote').value,
        author: document.getElementById('editAuthor').value,
        image_prompt: document.getElementById('editImagePrompt').value,
        image_style: document.getElementById('editImageStyle').value,
        keywords: document.getElementById('editKeywords').value
    };
    try {
        const response = await fetch(`/api/quotes/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update)
        });
        if (response.ok) {
            location.reload(); // Refresh to show updated quote
        } else {
            alert("Failed to update quote");
        }
    } catch (error) {
        console.error("Update error:", error);
        alert("Error updating quote");
    }
}

async function downloadQuotes(format) {
    window.location.href = `/api/quotes/export/${format}`;
}

document.getElementById('shortsFilter').addEventListener('change', async function() {
    const shortsOnly = this.checked;
    try {
        const response = await fetch(`/api/quotes?shorts_only=${shortsOnly}`);
        const quotes = await response.json();
        const quotesDiv = document.getElementById('quotes');
        quotesDiv.innerHTML = '';
        quotes.forEach(quote => {
            quotesDiv.innerHTML += `
                <div class="quote" id="quote-${quote.id}">
                    <p>"${quote.quote}"</p>
                    <p class="author">- ${quote.author}</p>
                    <p class="prompt"><strong>Image Prompt:</strong> ${quote.image_prompt}</p>
                    <p><strong>Style:</strong> ${quote.image_style}</p>
                    <p><strong>Keywords:</strong> ${quote.keywords}</p>
                    <p><strong>Generated At:</strong> ${new Date(quote.timestamp).toLocaleString('en-US', { timeZone: 'Asia/Kolkata', hour12: true, hour: 'numeric', minute: '2-digit', weekday: 'long', month: 'long', day: 'numeric' })}</p>
                    <button onclick="deleteQuote(${quote.id})">Delete</button>
                    <button onclick="openEditModal(${quote.id}, '${quote.quote.replace(/'/g, "\\'")}', '${quote.author.replace(/'/g, "\\'")}', '${quote.image_prompt.replace(/'/g, "\\'")}', '${quote.image_style.replace(/'/g, "\\'")}', '${quote.keywords.replace(/'/g, "\\'")}')">Edit</button>
                </div>
            `;
        });
    } catch (error) {
        console.error("Filter error:", error);
        alert("Error filtering quotes");
    }
});
