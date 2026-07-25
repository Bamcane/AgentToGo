const API_BASE = '';

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showModal(content) {
    const overlay = document.getElementById('modal-overlay');
    const modalContent = document.getElementById('modal-content');
    if (!overlay || !modalContent) return;
    
    modalContent.innerHTML = content;
    overlay.classList.remove('hidden');
    
    overlay.onclick = (e) => {
        if (e.target === overlay) hideModal();
    };
}

function hideModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.classList.add('hidden');
}
