// Function to update a slider's displayed value
function updateSliderValue(sliderId, valueSpanId) {
    const slider = document.getElementById(sliderId);
    const valueSpan = document.getElementById(valueSpanId);
    if (slider && valueSpan) {
        valueSpan.textContent = slider.value;
    }
}

// Update slider values in real-time when the user interacts
document.getElementById('N').addEventListener('input', function() {
    updateSliderValue('N', 'N-value');
});
document.getElementById('P').addEventListener('input', function() {
    updateSliderValue('P', 'P-value');
});
document.getElementById('K').addEventListener('input', function() {
    updateSliderValue('K', 'K-value');
});

// Set initial slider values on page load
document.addEventListener('DOMContentLoaded', function() {
    updateSliderValue('N', 'N-value');
    updateSliderValue('P', 'P-value');
    updateSliderValue('K', 'K-value');
});


// Form submission
document.getElementById('fertilizerForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    // Show loading indicator
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';

    // Prepare data
    const formData = {
        crop: document.getElementById('crop').value,
        region: document.getElementById('region').value,
        month: document.getElementById('month').value,
        N: parseFloat(document.getElementById('N').value), // Convert to float
        P: parseFloat(document.getElementById('P').value), // Convert to float
        K: parseFloat(document.getElementById('K').value), // Convert to float
        temperature: parseFloat(document.getElementById('temperature').value), // Convert to float
        humidity: parseFloat(document.getElementById('humidity').value), // Convert to float
        ph: parseFloat(document.getElementById('ph').value), // Convert to float
        moisture: parseFloat(document.getElementById('moisture').value) // Convert to float
    };

    try {
        // Actual fetch request to the Flask backend
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            // If the response is not OK (e.g., 400, 500 status codes)
            const errorData = await response.json();
            console.error('Server error:', errorData.error);
            // Display error message to the user
            showErrorMessage(errorData.error || 'An unknown error occurred during prediction.');
            return; // Stop execution
        }

        const data = await response.json();
        showResults(data);

    } catch (error) {
        // Catch network errors or issues with parsing the response
        console.error('Network or parsing error:', error);
        // Display error message to the user
        showErrorMessage('Could not connect to the server or process the response. Please ensure the backend server is running.');
    } finally {
        // Always re-enable the button and restore its text
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
});

function showResults(data) {
    // Update result fields
    document.getElementById('fertilizerName').textContent = data.fertilizer;
    document.getElementById('fertilizerCategory').textContent = data.fertilizer_type;
    // Use form values if the backend doesn't return them (for consistency)
    document.getElementById('resultCrop').textContent = data.crop || document.getElementById('crop').value;
    document.getElementById('resultRegion').textContent = data.region || document.getElementById('region').value;
    document.getElementById('resultMonth').textContent = data.month || document.getElementById('month').value;

    // Show information about the recommended fertilizer
    const infoTexts = {
        "Urea": "Urea is a widely used nitrogen fertilizer with 46% nitrogen content. Suitable for most crops in their vegetative growth phase.",
        "DAP": "Diammonium Phosphate (DAP) contains 18% nitrogen and 46% phosphorus. Ideal for early crop growth stages and root development.",
        "NPK 10:26:26": "Complex NPK fertilizer with nutrients in ideal ratio for flowering and fruiting stages of crops. Provides balanced nutrition.",
        "Muriate of Potash (MOP)": "Muriate of Potash (Potassium Chloride) is a common potassium fertilizer, essential for overall plant health and disease resistance.",
        "Gypsum": "Gypsum (Calcium Sulfate) is used to improve soil structure, reduce salinity, and supply calcium and sulfur.",
        "Zinc Sulphate": "Corrects zinc deficiencies, which are common in high-pH soils and vital for enzyme activity and plant growth.",
        "Compost": "Compost is an organic fertilizer that improves soil structure, water retention, and provides a slow release of nutrients.",
        "Ammonium Sulphate (AS)": "Ammonium Sulphate is a nitrogen and sulfur fertilizer, good for alkaline soils.",
        "Calcium Ammonium Nitrate (CAN)": "CAN is a neutral fertilizer, providing nitrogen and calcium, suitable for various soil types.",
        "Single Super Phosphate (SSP)": "SSP provides phosphorus and sulfur, beneficial for oilseeds and legumes.",
        "Sulphate of Potash (SOP)": "SOP is a premium potassium fertilizer, also providing sulfur, ideal for chloride-sensitive crops.",
        "NPK 12:32:16": "A common NPK blend, good for initial growth and flowering.",
        "NPK 19:19:19": "Balanced NPK for general crop growth and maintenance.",
        "Zinc Fortified Urea": "Urea fortified with zinc, addressing both nitrogen and zinc deficiencies.",
        "Custom Fertilizer Blend": "A custom blend is recommended based on specific soil and crop needs. Consult an agronomist for details."
    };

    document.getElementById('fertilizerInfo').innerHTML =
        `<strong>About this fertilizer:</strong> ${infoTexts[data.fertilizer] || 'This fertilizer is recommended based on your soil parameters and crop requirements. For more details, consult an agricultural expert.'}`;

    // Show result section
    document.getElementById('resultSection').style.display = 'block';

    // Scroll to results
    document.getElementById('resultSection').scrollIntoView({behavior: 'smooth'});
}

// Function to show an error message using a custom alert (instead of window.alert)
function showErrorMessage(message) {
    const resultSection = document.getElementById('resultSection');
    resultSection.style.display = 'block'; // Ensure the section is visible
    // Clear previous content and display the error
    resultSection.innerHTML = `
        <div class="card-body">
            <div class="alert alert-danger text-center" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i><strong>Error:</strong> ${message}
            </div>
            <p class="text-center mt-3">Please check your input values and try again, or ensure the server is running correctly.</p>
        </div>
    `;
    resultSection.scrollIntoView({behavior: 'smooth'});
}

// Save recommendation handler - using a custom message box instead of alert
document.getElementById('saveRecommendation').addEventListener('click', function() {
    const resultSection = document.getElementById('resultSection');

    // Create a temporary message box
    const messageBox = document.createElement('div');
    messageBox.className = 'alert alert-success text-center mt-3';
    messageBox.innerHTML = '<i class="fas fa-check-circle me-2"></i>Recommendation saved to your history!';
    resultSection.prepend(messageBox); // Add to the top of the result section

    // Remove the message after a few seconds
    setTimeout(() => {
        messageBox.remove();
    }, 3000);
});
