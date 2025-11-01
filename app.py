from flask import Flask, render_template, request, jsonify
import numpy as np
import tensorflow as tf
import os

app = Flask(__name__)

# --- Model Loading ---
MODEL_PATH = "model.h5"  # Ensure model.h5 is in the same directory or provide full path
if not os.path.exists(MODEL_PATH):
    print(f"Error: Model file not found at {MODEL_PATH}")
    print("Please ensure 'model.h5' is in the same directory or provide the correct path.")
    exit()

try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    exit()

# --- Enhanced Static Data for India ---
crops = {
    "cereals": [
        "Rice", "Wheat", "Maize", "Barley", "Sorghum (Jowar)",
        "Pearl Millet (Bajra)", "Finger Millet (Ragi)", "Oats",
        "Buckwheat", "Foxtail Millet", "Little Millet", "Kodo Millet",
        "Proso Millet", "Barnyard Millet"
    ],
    "pulses": [
        "Chickpea (Chana)", "Pigeon Pea (Arhar/Toor)", "Mung Bean (Moong)",
        "Urd Bean (Urad)", "Lentil (Masur)", "Peas (Matar)",
        "Cowpea (Lobia)", "Horse Gram (Kulthi)", "Moth Bean (Matki)",
        "Kidney Bean (Rajma)", "Black Gram (Urad)", "Green Gram (Moong)",
        "Bengal Gram (Chana)", "Red Gram (Arhar)", "Grass Pea (Khesari)"
    ],
    "oilseeds": [
        "Groundnut", "Mustard", "Soybean", "Sunflower", "Sesame (Til)",
        "Safflower", "Niger Seed", "Castor", "Linseed", "Coconut",
        "Oil Palm", "Cottonseed", "Rapeseed", "Palm Kernel"
    ],
    "cash_crops": [
        "Sugarcane", "Cotton", "Jute", "Tobacco", "Rubber",
        "Tea", "Coffee", "Cocoa", "Indigo", "Opium Poppy"
    ],
    "vegetables": [
        "Potato", "Tomato", "Onion", "Brinjal (Eggplant)", "Okra (Bhindi)",
        "Cauliflower", "Cabbage", "Carrot", "Radish", "Cucumber",
        "Bottle Gourd", "Bitter Gourd", "Ridge Gourd", "Snake Gourd",
        "Pumpkin", "Spinach", "Fenugreek (Methi)", "Amaranth (Chaulai)",
        "Drumstick", "Peas", "Beans", "Capsicum", "Chilli",
        "Garlic", "Ginger", "Turmeric", "Sweet Potato", "Tapioca",
        "Yam", "Colocasia"
    ],
    "fruits": [
        "Mango", "Banana", "Citrus (Orange, Lemon, Lime)", "Apple",
        "Grapes", "Pomegranate", "Guava", "Pineapple", "Papaya",
        "Watermelon", "Muskmelon", "Pear", "Peach", "Plum",
        "Apricot", "Litchi", "Jackfruit", "Ber", "Aonla (Indian Gooseberry)",
        "Custard Apple", "Jamun", "Kiwi", "Strawberry", "Fig",
        "Cherry", "Avocado", "Persimmon", "Passion Fruit", "Dragon Fruit"
    ]
}

regions = sorted([
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
])

months = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

# Comprehensive list of fertilizers commonly used in India
fertilizers = [
    "Urea", "Ammonium Sulphate (AS)", "Calcium Ammonium Nitrate (CAN)",
    "Ammonium Chloride", "Anhydrous Ammonia", "Single Super Phosphate (SSP)",
    "Double Super Phosphate (DSP)", "Triple Super Phosphate (TSP)",
    "Diammonium Phosphate (DAP)", "Monoammonium Phosphate (MAP)", "Rock Phosphate",
    "Bone Meal", "Muriate of Potash (MOP)", "Sulphate of Potash (SOP)",
    "NPK 10:26:26", "NPK 12:32:16", "NPK 14:28:14", "NPK 14:35:14",
    "NPK 15:15:15", "NPK 16:20:0", "NPK 17:17:17", "NPK 19:19:19",
    "NPK 20:20:0", "NPK 20:20:13", "NPK 28:28:0", "NPK 30:10:10",
    "Zinc Sulphate", "Zinc Oxysulphate", "Zinc EDTA", "Ferrous Sulphate",
    "Manganese Sulphate", "Copper Sulphate", "Boron (Boric Acid/Borax)",
    "Molybdenum (Ammonium Molybdate)", "Compost", "Vermicompost",
    "Farmyard Manure (FYM)", "Green Manure", "Azolla", "Rhizobium Biofertilizer",
    "Azotobacter Biofertilizer", "Phosphobacteria", "Potash Mobilizing Biofertilizer",
    "Vesicular Arbuscular Mycorrhiza (VAM)", "Sulphur-Coated Urea",
    "Neem-Coated Urea", "Gypsum", "Pyrites", "Dolomite",
    "Ammonium Nitrate", "Calcium Nitrate", "Potassium Nitrate", "Magnesium Sulphate",
    "Chelated Iron", "Water Soluble NPK (19:19:19)", "Water Soluble NPK (13:40:13)",
    "Zinc Fortified Urea", "Boron Fortified NPK", "Polymer Coated Urea",
    "Sulfur Coated Urea"
]

# --- Encoding Mappings ---
crop_to_int = {crop: i for i, crop in enumerate([item for sublist in crops.values() for item in sublist])}
region_to_int = {region: i for i, region in enumerate(regions)}
month_to_int = {month: i for i, month in enumerate(months)}

EXPECTED_MODEL_INPUT_FEATURES = 10  # Adjust based on your model's input shape

@app.route("/")
def index():
    return render_template("index.html", crops=crops, regions=regions, months=months)

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()

        # Extract numerical features
        n_val = float(data.get("N"))
        p_val = float(data.get("P"))
        k_val = float(data.get("K"))
        temp_val = float(data.get("temperature"))
        humidity_val = float(data.get("humidity"))
        ph_val = float(data.get("ph"))
        moisture_val = float(data.get("moisture"))

        # Parameter validation
        parameter_ranges = {
            "N": (0, 300),
            "P": (0, 200),
            "K": (0, 250),
            "temperature": (10, 50),
            "humidity": (0, 100),
            "ph": (4.0, 9.0),
            "moisture": (0, 100)
        }

        for param, value in [
            ("N", n_val), ("P", p_val), ("K", k_val),
            ("temperature", temp_val), ("humidity", humidity_val),
            ("ph", ph_val), ("moisture", moisture_val)
        ]:
            min_val, max_val = parameter_ranges[param]
            if not (min_val <= value <= max_val):
                return jsonify({
                    "error": f"Invalid {param} value: {value}. Must be between {min_val} and {max_val}."
                }), 400

        # Categorical feature encoding
        selected_crop_str = data.get("crop")
        selected_region_str = data.get("region")
        selected_month_str = data.get("month")

        crop_encoded = crop_to_int.get(selected_crop_str)
        region_encoded = region_to_int.get(selected_region_str)
        month_encoded = month_to_int.get(selected_month_str)

        if crop_encoded is None:
            return jsonify({"error": f"Invalid crop: '{selected_crop_str}'"}), 400
        if region_encoded is None:
            return jsonify({"error": f"Invalid region: '{selected_region_str}'"}), 400
        if month_encoded is None:
            return jsonify({"error": f"Invalid month: '{selected_month_str}'"}), 400

        # Assemble features
        features = [
            n_val, p_val, k_val, temp_val, humidity_val,
            ph_val, moisture_val, float(crop_encoded),
            float(region_encoded), float(month_encoded)
        ]

        if len(features) != EXPECTED_MODEL_INPUT_FEATURES:
            return jsonify({
                "error": f"Feature count mismatch. Expected {EXPECTED_MODEL_INPUT_FEATURES} features, got {len(features)}"
            }), 500

        input_data = np.array([features], dtype=np.float32)
        prediction = model.predict(input_data)
        predicted_index = int(np.argmax(prediction))

        if 0 <= predicted_index < len(fertilizers):
            predicted_fertilizer = fertilizers[predicted_index]
        else:
            predicted_fertilizer = "Custom Fertilizer Blend"

        return jsonify({
            "fertilizer": predicted_fertilizer,
            "fertilizer_type": categorize_fertilizer(predicted_fertilizer)
        })

    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

def categorize_fertilizer(fertilizer_name):
    """Categorize the fertilizer based on its composition"""
    if "NPK" in fertilizer_name or "DAP" in fertilizer_name or "MAP" in fertilizer_name:
        return "Complex Fertilizer"
    elif "Urea" in fertilizer_name or "Ammonium" in fertilizer_name:
        return "Nitrogen Fertilizer"
    elif "Super" in fertilizer_name or "Phosphate" in fertilizer_name:
        return "Phosphatic Fertilizer"
    elif "Potash" in fertilizer_name or "Potassium" in fertilizer_name:
        return "Potassic Fertilizer"
    elif any(x in fertilizer_name for x in ["Zinc", "Iron", "Boron", "Manganese"]):
        return "Micronutrient Fertilizer"
    elif any(x in fertilizer_name for x in ["Compost", "Manure", "Biofertilizer"]):
        return "Organic Fertilizer"
    else:
        return "Special Fertilizer"

if __name__ == "__main__":
    app.run(debug=True)
