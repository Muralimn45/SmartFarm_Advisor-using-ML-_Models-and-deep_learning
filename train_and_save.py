import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical

# --- Configuration ---
DATA_FILE = 'synthetic_crop_data_all_crops.csv'
OUTPUT_DIR = 'output_models'
MODEL_PATH = os.path.join(OUTPUT_DIR, "model.h5")
ENCODERS_PATH = os.path.join(OUTPUT_DIR, "encoders.pkl")
SCALER_PATH = os.path.join(OUTPUT_DIR, "scaler.pkl")

# ========== STEP 1: Load & Clean Dataset ==========

# Use a relative path, assuming the CSV is in the same directory as this script.
print(f"Attempting to load data from: {os.path.abspath(DATA_FILE)}")
if not os.path.exists(DATA_FILE):
    # This check prevents the script from crashing silently on file-not-found
    print(f"\nFATAL ERROR: The data file '{DATA_FILE}' was not found.")
    print(f"Please place it in the same directory as this script, or update the 'DATA_FILE' variable.")
    exit()

try:
    df_crop_recommendation = pd.read_csv(DATA_FILE)
except Exception as e:
    print(f"\nFATAL ERROR: Failed to read CSV file. Error: {e}")
    exit()

# Verify and clean columns
required_columns = [
    'N', 'P', 'K', 'Temperature(C)', 'Humidity(%)', 'Soil_pH', 'Moisture(%)',
    'Crop', 'Region', 'Month', 'Fertilizer'
]

for col in required_columns:
    if col not in df_crop_recommendation.columns:
        print(f"\nFATAL ERROR: Missing column in dataset: {col}.")
        print(f"Available columns are: {df_crop_recommendation.columns.tolist()}")
        exit()

# Clean whitespace & casing
for cat_col in ['Crop', 'Region', 'Month', 'Fertilizer']:
    df_crop_recommendation[cat_col] = df_crop_recommendation[cat_col].astype(str).str.strip().str.lower()
print("✅ Data loaded and cleaned.")


# ========== STEP 2: Encode Categorical Features ==========
label_encoders = {}
dropdowns = {}

# Encode input features
for col in ['Crop', 'Region', 'Month']:
    le = LabelEncoder()
    df_crop_recommendation[col] = le.fit_transform(df_crop_recommendation[col])
    label_encoders[col] = le
    dropdowns[col] = sorted(le.classes_)

# Encode the target feature (Fertilizer)
fertilizer_encoder = LabelEncoder()
df_crop_recommendation['Fertilizer'] = fertilizer_encoder.fit_transform(df_crop_recommendation['Fertilizer'])

# ========== STEP 3: Feature Scaling and One-Hot Encoding ==========
X = df_crop_recommendation.drop('Fertilizer', axis=1)
y = df_crop_recommendation['Fertilizer']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

y_encoded = to_categorical(y)
print("✅ Features scaled and target encoded.")


# ========== STEP 4: Split Dataset for Validation ==========
X_train, X_val, y_train, y_val = train_test_split(X_scaled, y_encoded, test_size=0.2, random_state=42)

# ========== STEP 5: Define ANN Model ==========
model = Sequential([
    Dense(128, input_dim=X.shape[1], activation='relu'),
    BatchNormalization(),
    Dropout(0.4),

    Dense(256, activation='relu'),
    BatchNormalization(),
    Dropout(0.4),

    Dense(128, activation='relu'),
    Dropout(0.3),

    Dense(y_encoded.shape[1], activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
print("✅ Model defined and compiled.")

# ========== STEP 6: Train with Early Stopping ==========
early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, verbose=1)

print("\n--- Starting Model Training ---")
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=100,
    batch_size=32,
    callbacks=[early_stop],
    verbose=1
)
print("--- Training Complete ---")

# ========== STEP 7: Save Model and Tools (Robust Save) ==========

# Create the output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    # 1. Save the Keras model
    model.save(MODEL_PATH)

    # 2. Save the Encoders and Dropdown values
    with open(ENCODERS_PATH, "wb") as f:
        pickle.dump({
            "label_encoders": label_encoders,
            "fertilizer_encoder": fertilizer_encoder,
            "dropdowns": dropdowns
        }, f)

    # 3. Save the Scaler
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    print(f"\n SUCCESS: All files saved to the '{OUTPUT_DIR}' directory.")
    print(f"   - Model: {MODEL_PATH}")
    print(f"   - Encoders: {ENCODERS_PATH}")
    print(f"   - Scaler: {SCALER_PATH}")

except Exception as e:
    print(f"\nFATAL ERROR: Failed to save model or tools. Check directory permissions. Error: {e}")
