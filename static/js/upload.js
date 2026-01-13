// Show image preview immediately when file is selected, replacing the file label
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    const fileLabel = document.querySelector('.file-label');
    
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            
            if (file && file.type.startsWith('image/')) {
                // Hide the original label text
                const labelText = fileLabel.querySelector('.file-label-text');
                if (labelText) {
                    labelText.style.display = 'none';
                }
                
                // Remove existing preview if any
                const existingPreview = fileLabel.querySelector('.file-preview-image');
                if (existingPreview) {
                    existingPreview.remove();
                }
                
                // Create preview image
                const previewImage = document.createElement('img');
                previewImage.className = 'file-preview-image';
                previewImage.alt = 'Selected image preview';
                previewImage.style.cssText = 'max-width: 100%; max-height: 300px; border-radius: 8px; margin: 0 auto; display: block;';
                
                // Use FileReader to show preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImage.src = e.target.result;
                    fileLabel.appendChild(previewImage);
                    fileLabel.classList.add('has-preview');
                };
                reader.readAsDataURL(file);
            } else {
                // If no file or invalid, restore original label
                const labelText = fileLabel.querySelector('.file-label-text');
                if (labelText) {
                    labelText.style.display = '';
                }
                const existingPreview = fileLabel.querySelector('.file-preview-image');
                if (existingPreview) {
                    existingPreview.remove();
                }
                fileLabel.classList.remove('has-preview');
            }
        });
    }
});
