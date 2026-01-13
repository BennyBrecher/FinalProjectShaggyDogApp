// Auto-refresh dashboard when images are processing
document.addEventListener('DOMContentLoaded', function() {
    // Check if there are any processing images
    const processingIndicators = document.querySelectorAll('.processing-indicator');
    const statusBadges = document.querySelectorAll('.breed-badge.processing');
    
    if (processingIndicators.length > 0 || statusBadges.length > 0) {
        // Auto-refresh every 3 seconds if images are processing
        setTimeout(function() {
            window.location.reload();
        }, 3000);
    }
});
