// Main JavaScript for DLP Scanner
document.addEventListener('DOMContentLoaded', function() {
    console.log('DLP Scanner loaded');
    
    // Add any common JavaScript functionality here
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            console.log('Button clicked:', this.textContent);
        });
    });
});
