# 🌱 AgriDash Pro: Smart Farm Management Dashboard [Hybrid ML Recommendation System]

AgriDash Pro is a modern, data-driven web application built with **Flask** and **SQLite** designed to optimize agricultural planning. Our goal is to move beyond simple guesswork, providing personalized tools for crop management, soil health tracking, and nutrient recommendations powered by a hybrid Machine Learning pipeline.

## Key Features

  * **Robust Backend:** Built on **Flask** with a secure **SQLite** database, using parameterized queries for protection against SQL Injection.
  * **User Management:** Secure user registration, login, and password management utilizing `werkzeug.security` for robust password hashing.
  * **Crop & Soil Tracking:** Intuitive interface for farmers to record and monitor active crops, planting stages, and historical soil test results.
  * **Hybrid ML Recommendation System:** Features a unique two-stage Machine Learning approach to deliver highly accurate, yet fast, fertilizer recommendations.
  * **Dynamic Weather:** Provides localized current conditions and short-term forecasts based on the user's farm location (using mock data in this demo).

-----

## 🧠 The Hybrid ML Architecture: A Two-Stage Pipeline

Our fertilizer recommendation module is powered by a powerful, pre-trained system that leverages both deep learning for robustness and a shallow model for speed.

### Stage 1: Training (The Deep Learner - ANN)

The heavy lifting of **learning complex relationships** between soil characteristics and optimal fertilizer outcomes was handled by an **Artificial Neural Network (ANN)**.

| Component | Description |
| :--- | :--- |
| **Model** | **Artificial Neural Network (ANN)**. This model was trained extensively on large, diverse agricultural datasets. |
| **Goal** | The ANN's purpose was to thoroughly analyze the 10+ input features (NPK, pH, temperature, crop type, etc.) to **extract high-quality, weighted representations** of these features. It learns the subtle, non-linear patterns that determine fertilizer efficacy. |
| **Status** | The ANN is **completely trained** and organized the knowledge into an efficient weight matrix. This trained knowledge is implicitly transferred to the next stage. |

### Stage 2: Prediction (The Fast Predictor - KNN)

Once the complex patterns are learned by the ANN, we use a simpler, distance-based model, **K-Nearest Neighbors (KNN)**, for the final prediction output, which prioritizes speed and deployment simplicity.

| Component | Description |
| :--- | :--- |
| **Model** | **K-Nearest Neighbors (KNN) Classifier**. This model is what is deployed in the live application (`agri_dash.py`). |
| **Goal** | The KNN model is used because it offers **fast inference** and simplicity. It makes its recommendation by comparing a new input sample to the closest "neighbors" (historical, successful examples) within the feature space **organized by the ANN's learned weights**. |
| **Process** | The `agri_dash.py` code loads the **pre-trained KNN model** and the necessary **`StandardScaler`**. It performs real-time feature normalization and categorical encoding, and then uses the KNN to output a quick prediction of the optimal fertilizer type (e.g., Urea, DAP). |
| **Confidence** | We provide a heuristic **confidence score** based on the distance to the nearest neighbor. A small distance indicates the new input is very similar to a known, successful data point, yielding high confidence. |

### Why the Hybrid Approach?

This two-stage strategy gives us the best of both worlds:

1.  **High Accuracy:** We benefit from the ANN's sophisticated pattern recognition during the training phase.
2.  **Deployment Speed:** We use KNN for the prediction phase, which is faster to execute in a web application and requires less computational overhead than a deep neural network, ensuring a snappy user experience.

-----

## 🛠️ Getting Started

### Prerequisites

  * Python 3.x
  * The trained model files (`knn_model.pkl`, `scaler.pkl`) must be placed in the project root.

### Running the App

```bash
# Clone the repository
git clone [YOUR_REPO_URL]
cd AgriDash-Pro

# Install dependencies
pip install Flask numpy scikit-learn werkzeug

# Initialize the database and run the app
python agri_dash.py
```

The application will be accessible at `http://127.0.0.1:5000`.
