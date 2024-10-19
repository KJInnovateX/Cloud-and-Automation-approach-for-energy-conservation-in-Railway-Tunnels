// Registration Form Validation
document.getElementById('registrationForm').addEventListener('submit', function(event) {
    const password = document.getElementById('password').value;
    const aadhar = document.getElementById('aadhar').value;
    const govtID = document.getElementById('govtID').files[0]; // Get the uploaded file


    // Clear error messages
    document.getElementById('aadharError').style.display = 'none';
    document.getElementById('passwordError').style.display = 'none';
    document.getElementById('govtIDError').style.display = 'none';

    let valid = true;

    // Aadhar validation: Must be 12 digits
    if (!/^\d{12}$/.test(aadhar)) {
        document.getElementById('aadharError').textContent = 'Aadhar number must be 12 digits.';
        document.getElementById('aadharError').style.display = 'block';
        valid = false;
    }


    // Password validation: Must be at least 6 characters
    if (password.length < 6) {
        document.getElementById('passwordError').textContent = 'Password must be at least 6 characters.';
        document.getElementById('passwordError').style.display = 'block';
        valid = false;
    }

    // Government ID validation: Must be a file (image/pdf)
    if (!govtID) {
        document.getElementById('govtIDError').textContent = 'Government ID is required.';
        document.getElementById('govtIDError').style.display = 'block';
        valid = false;
    }

    if (!valid) {
        event.preventDefault();  // Stop form submission if invalid
    }
});

// Real-time preview of Government ID
document.getElementById('govtID').addEventListener('change', function(event) {
    const file = event.target.files[0];
    const previewContainer = document.getElementById('govtIDPreview');
    previewContainer.innerHTML = ''; // Clear existing preview

    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            if (file.type.startsWith('image/')) {  // Only display a preview for image files
                const filePreview = document.createElement('img');
                filePreview.src = e.target.result;
                filePreview.style.maxWidth = '200px'; // Adjust image size
                previewContainer.appendChild(filePreview);
            } else {
                previewContainer.innerHTML = '<p>Preview not available for non-image files. Uploaded file: ' + file.name + '</p>';
            }
        };
        reader.readAsDataURL(file);
    }
});




