// Main Lobby App JavaScript

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });
});

// Add smooth transitions
document.querySelectorAll('a, button').forEach(el => {
    el.style.transition = 'all 0.2s ease';
});
