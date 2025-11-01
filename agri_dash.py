from flask import Flask, render_template_string, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from datetime import datetime, timedelta
import numpy as np
import pickle
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

# ==============================================================================
# --- HTML CONTENT TEMPLATES (Jinja2) ---
# ==============================================================================

LANDING_PAGE_CONTENT = """
<div class="p-5 mb-4 bg-light rounded-3 text-center" style="margin-top: 60px;">
    <div class="container-fluid py-5">
        <h1 class="display-5 fw-bold text-success"><i class="fas fa-leaf me-2"></i>AgriDash Pro</h1>
        <p class="col-md-8 fs-4 mx-auto">Your smart companion for modern, profitable, and sustainable agriculture. Get personalized fertilizer recommendations, real-time weather, and crop management tools.</p>
        <hr class="my-4">
        <p>Log in or register to unlock your personalized farm dashboard.</p>
        <a class="btn btn-primary btn-lg me-2" href="{{ url_for('login') }}" role="button"><i class="fas fa-sign-in-alt me-2"></i>Login</a>
        <a class="btn btn-success btn-lg" href="{{ url_for('register') }}" role="button"><i class="fas fa-user-plus me-2"></i>Register Now</a>
    </div>
</div>
<div class="row text-center">
    <div class="col-md-4">
        <div class="p-3 border rounded-3 h-100">
            <i class="fas fa-flask fa-3x text-info mb-3"></i>
            <h4>Soil Analytics</h4>
            <p>Get data-driven recommendations for NPK and pH levels.</p>
        </div>
    </div>
    <div class="col-md-4">
        <div class="p-3 border rounded-3 h-100">
            <i class="fas fa-cloud-sun fa-3x text-warning mb-3"></i>
            <h4>Weather Insights</h4>
            <p>5-day forecasts and farming advisories specific to your location.</p>
        </div>
    </div>
    <div class="col-md-4">
        <div class="p-3 border rounded-3 h-100">
            <i class="fas fa-robot fa-3x text-primary mb-3"></i>
            <h4>ML Predictions</h4>
            <p>Use our KNN model to predict the most suitable fertilizer.</p>
        </div>
    </div>
</div>
"""

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgriDash Pro | {{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #007bff;
            --success-color: #28a745;
            --info-color: #17a2b8;
            --warning-color: #ffc107;
            --auth-bg: #f8f9fa;
        }
        body {
            background-color: var(--auth-bg);
            padding-bottom: 60px; /* Space for fixed footer */
        }
        .navbar {
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .auth-card {
            margin-top: 50px;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        .stat-card {
            border-radius: 15px;
            transition: transform 0.3s;
            cursor: pointer;
            min-height: 150px;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .weather-card {
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .forecast-day {
            background-color: #f1f1f1;
            border-left: 5px solid var(--primary-color);
            border-radius: 10px;
            transition: all 0.2s;
        }
        .forecast-day:hover {
            background-color: #e9ecef;
        }
        .soil-status-excellent { color: #28a745; font-weight: bold; }
        .soil-status-good { color: #20c997; font-weight: bold; }
        .soil-status-fair { color: #ffc107; font-weight: bold; }
        .soil-status-poor { color: #dc3545; font-weight: bold; }
        .footer {
            position: fixed;
            bottom: 0;
            width: 100%;
            background-color: #343a40;
            color: white;
            padding: 10px 0;
            font-size: 0.85rem;
            box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.1);
        }
    </style>
</head>
<body>

    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('home') }}">
                <i class="fas fa-leaf me-2"></i>AgriDash Pro
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('crop_management') }}">Crops</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('fertilizer') }}">Soil & Fert.</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('weather') }}">Weather</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('contact') }}">Contact</a>
                    </li>
                </ul>
                <div class="d-flex">
                    {% if g.user %}
                    <a class="btn btn-sm btn-info me-2" href="{{ url_for('profile') }}">
                        <i class="fas fa-user-circle me-1"></i> {{ g.user.full_name.split()[0] }}
                    </a>
                    <a class="btn btn-sm btn-danger" href="{{ url_for('logout') }}">
                        <i class="fas fa-sign-out-alt me-1"></i> Logout
                    </a>
                    {% else %}
                    <a class="btn btn-sm btn-light me-2" href="{{ url_for('login') }}">
                        <i class="fas fa-sign-in-alt me-1"></i> Login
                    </a>
                    <a class="btn btn-sm btn-light" href="{{ url_for('register') }}">
                        <i class="fas fa-user-plus me-1"></i> Register
                    </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </nav>

    <main class="container mt-5 pt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <footer class="footer mt-5">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <p>&copy; 2025 AgriDash Pro </p>
                </div>
                <div class="col-md-6 text-md-end">
                    <p>📞 Support: +91 1800-AGRIHELP | ✉️ help@agridash.com</p>
                </div>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

FORGOT_PASSWORD_CONTENT = """
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card auth-card">
            <div class="card-header bg-warning text-dark text-center">
                <h4 class="mb-0"><i class="fas fa-key me-2"></i> Reset Password</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="email" class="form-label">Email Address</label>
                        <input type="email" class="form-control" id="email" name="email" required 
                               placeholder="Enter your registered email address">
                        <div class="form-text">We'll send you a password reset link</div>
                    </div>
                    <button type="submit" class="btn btn-warning w-100">
                        <i class="fas fa-paper-plane me-2"></i> Send Reset Link
                    </button>
                </form>
                <div class="text-center mt-3">
                    <p>Remember your password? <a href="{{ url_for('login') }}">Login here</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
"""

RESET_PASSWORD_CONTENT = """
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card auth-card">
            <div class="card-header bg-primary text-white text-center">
                <h4 class="mb-0"><i class="fas fa-lock me-2"></i> Set New Password</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="password" class="form-label">New Password</label>
                        <input type="password" class="form-control" id="password" name="password" required 
                               placeholder="Enter new password" minlength="6">
                        <div class="form-text">Password must be at least 6 characters</div>
                    </div>
                    <div class="mb-3">
                        <label for="confirm_password" class="form-label">Confirm Password</label>
                        <input type="password" class="form-control" id="confirm_password" name="confirm_password" required 
                               placeholder="Confirm new password">
                    </div>
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="fas fa-check me-2"></i> Reset Password
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
"""

LOGIN_CONTENT = """
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card auth-card">
            <div class="card-header bg-primary text-white text-center">
                <h4 class="mb-0"><i class="fas fa-sign-in-alt me-2"></i> Login to AgriDash Pro</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="identifier" class="form-label">Username or Email</label>
                        <input type="text" class="form-control" id="identifier" name="identifier" required 
                               placeholder="Enter username or email">
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <div class="input-group">
                            <input type="password" class="form-control" id="password" name="password" required 
                                   placeholder="Your password">
                            <button class="btn btn-outline-secondary" type="button" id="togglePassword">
                                <i class="fas fa-eye" id="toggleIcon"></i>
                            </button>
                        </div>
                    </div>
                    <div class="d-flex justify-content-between mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="" id="rememberMe">
                            <label class="form-check-label" for="rememberMe">
                                Remember me
                            </label>
                        </div>
                        <a href="{{ url_for('forgot_password') }}" class="text-decoration-none">Forgot Password?</a>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="fas fa-sign-in-alt me-2"></i> Login
                    </button>
                </form>
                <div class="text-center mt-3">
                    <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
document.getElementById('togglePassword').addEventListener('click', function() { 
    const passwordInput = document.getElementById('password'); 
    const toggleIcon = document.getElementById('toggleIcon'); 
    if (passwordInput.type === 'password') { 
        passwordInput.type = 'text'; 
        toggleIcon.classList.remove('fa-eye'); 
        toggleIcon.classList.add('fa-eye-slash'); 
    } else { 
        passwordInput.type = 'password'; 
        toggleIcon.classList.remove('fa-eye-slash'); 
        toggleIcon.classList.add('fa-eye'); 
    } 
});
</script>
"""

REGISTER_CONTENT = """
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card auth-card">
            <div class="card-header bg-success text-white text-center">
                <h4 class="mb-0"><i class="fas fa-user-plus me-2"></i> Create Your AgriDash Pro Account</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="username" class="form-label">Username</label>
                            <input type="text" class="form-control" id="username" name="username" required 
                                   placeholder="Choose a unique username">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="email" class="form-label">Email Address</label>
                            <input type="email" class="form-control" id="email" name="email" required 
                                   placeholder="your@email.com">
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="phone" class="form-label">Phone Number</label>
                            <input type="tel" class="form-control" id="phone" name="phone" required 
                                   placeholder="+91 1234567890">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="full_name" class="form-label">Full Name</label>
                            <input type="text" class="form-control" id="full_name" name="full_name" required 
                                   placeholder="Your full name">
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="farm_name" class="form-label">Farm Name</label>
                            <input type="text" class="form-control" id="farm_name" name="farm_name" required 
                                   placeholder="Name of your farm">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="location" class="form-label">Location</label>
                            <input type="text" class="form-control" id="location" name="location" required 
                                   placeholder="City/District" value="Delhi">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label for="total_land" class="form-label">Total Land (acres)</label>
                        <input type="number" step="0.01" class="form-control" id="total_land" name="total_land" required 
                               placeholder="Total farmland in acres" value="10">
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="password" class="form-label">Password</label>
                            <input type="password" class="form-control" id="password" name="password" required 
                                   placeholder="Create a strong password" minlength="6">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="confirm_password" class="form-label">Confirm Password</label>
                            <input type="password" class="form-control" id="confirm_password" name="confirm_password" required 
                                   placeholder="Re-enter password">
                        </div>
                    </div>
                    <button type="submit" class="btn btn-success w-100">
                        <i class="fas fa-check-circle me-2"></i> Register
                    </button>
                </form>
                <div class="text-center mt-3">
                    <p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
"""

DASHBOARD_CONTENT = """
<div class="row mb-4">
    <div class="col-12">
        <h2 class="mb-4">
            <i class="fas fa-chart-line me-2"></i>
            Welcome back, {{ user.full_name.split()[0] }}!
        </h2>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-3 mb-3">
        <div class="stat-card card bg-success text-white">
            <div class="card-body text-center">
                <i class="fas fa-leaf fa-3x mb-2"></i>
                <h3>{{ crops|length }}</h3>
                <p class="mb-0">Active Crops</p>
            </div>
        </div>
    </div>
    <div class="col-md-3 mb-3">
        <div class="stat-card card bg-primary text-white">
            <div class="card-body text-center">
                <i class="fas fa-map fa-3x mb-2"></i>
                <h3>{{ "%.1f"|format(total_acreage) }}</h3>
                <p class="mb-0">Acres Under Cultivation</p>
            </div>
        </div>
    </div>
    <div class="col-md-3 mb-3">
        <div class="stat-card card bg-info text-white">
            <div class="card-body text-center">
                <i class="fas fa-cloud-sun fa-3x mb-2"></i>
                <h3>{{ weather.temperature }}°C</h3>
                <p class="mb-0">{{ weather.description }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-3 mb-3">
        <div class="stat-card card bg-warning text-dark">
            <div class="card-body text-center">
                <i class="fas fa-flask fa-3x mb-2"></i>
                <h3>{{ last_test_date }}</h3>
                <p class="mb-0">Last Soil Test</p>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8 mb-4">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0"><i class="fas fa-seedling me-2"></i>Your Crops</h5>
            </div>
            <div class="card-body">
                {% if crops %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Crop</th>
                                <th>Acres</th>
                                <th>Stage</th>
                                <th>Planted</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for crop in crops[:5] %}
                            <tr>
                                <td><strong>{{ crop.crop_type }}</strong></td>
                                <td>{{ crop.acre }}</td>
                                <td><span class="badge bg-info">{{ crop.stage }}</span></td>
                                <td>{{ crop.planting_date }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <a href="{{ url_for('crop_management') }}" class="btn btn-success">
                    <i class="fas fa-plus me-2"></i>Manage Crops
                </a>
                {% else %}
                <p class="text-muted">No crops added yet.</p>
                <a href="{{ url_for('crop_management') }}" class="btn btn-success">
                    <i class="fas fa-plus me-2"></i>Add Your First Crop
                </a>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="col-md-4 mb-4">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0"><i class="fas fa-flask me-2"></i>Soil Health</h5>
            </div>
            <div class="card-body">
                {% if soil_data %}
                <div class="mb-3">
                    <strong>Nitrogen (N):</strong>
                    <span class="{{ get_soil_status_class(soil_data.nitrogen_level) }}">
                        {{ soil_data.nitrogen_level }}
                    </span>
                </div>
                <div class="mb-3">
                    <strong>Phosphorus (P):</strong>
                    <span class="{{ get_soil_status_class(soil_data.phosphorus_level) }}">
                        {{ soil_data.phosphorus_level }}
                    </span>
                </div>
                <div class="mb-3">
                    <strong>Potassium (K):</strong>
                    <span class="{{ get_soil_status_class(soil_data.potassium_level) }}">
                        {{ soil_data.potassium_level }}
                    </span>
                </div>
                <div class="mb-3">
                    <strong>pH Level:</strong> {{ "%.1f"|format(soil_data.ph_level) }}
                </div>
                {% else %}
                <p class="text-muted">No soil test data available.</p>
                {% endif %}
                <a href="{{ url_for('fertilizer') }}" class="btn btn-primary">
                    <i class="fas fa-vial me-2"></i>View Details
                </a>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-warning text-dark">
                <h5 class="mb-0"><i class="fas fa-lightbulb me-2"></i>Today's Recommendation</h5>
            </div>
            <div class="card-body">
                {% if dashboard_rec %}
                <div class="alert alert-{{ 'success' if dashboard_rec.status == 'Good' else 'warning' }}">
                    <strong>{{ dashboard_rec.status }}:</strong> {{ dashboard_rec.message }}
                </div>
                <p>{{ dashboard_rec.recommendation }}</p>
                {% else %}
                <p>No recommendations available at this time.</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>
"""

WEATHER_CONTENT = """
<div class="row mb-4">
    <div class="col-12">
        <h2 class="mb-4">
            <i class="fas fa-cloud-sun me-2"></i>
            Weather Intelligence for {{ weather.city }}
        </h2>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-6 mb-4">
        <div class="weather-card card">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0"><i class="fas fa-thermometer-half me-2"></i>Current Weather</h5>
            </div>
            <div class="card-body text-center">
                <div class="display-1 mb-3">{{ weather.icon }}</div>
                <h2 class="mb-3">{{ weather.temperature }}°C</h2>
                <p class="lead">{{ weather.description }}</p>
                <div class="row mt-4">
                    <div class="col-6">
                        <i class="fas fa-tint fa-2x text-info"></i>
                        <p class="mb-0"><strong>Humidity</strong></p>
                        <p>{{ weather.humidity }}%</p>
                    </div>
                    <div class="col-6">
                        <i class="fas fa-wind fa-2x text-primary"></i>
                        <p class="mb-0"><strong>Wind</strong></p>
                        <p>{{ weather.wind }}</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-6 mb-4">
        <div class="weather-card card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0"><i class="fas fa-calendar-week me-2"></i>5-Day Forecast</h5>
            </div>
            <div class="card-body">
                {% for day in forecast %}
                <div class="forecast-day d-flex justify-content-between align-items-center p-3 mb-2 rounded">
                    <div>
                        <strong>{{ day.day }}</strong>
                        <br>
                        <small class="text-muted">{{ day.condition }}</small>
                    </div>
                    <div class="text-center">
                        <span class="fs-2">{{ day.icon }}</span>
                    </div>
                    <div class="text-end">
                        <span class="text-danger"><strong>{{ day.high }}°</strong></span>
                        <span class="text-muted"> / {{ day.low }}°</span>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0"><i class="fas fa-book me-2"></i>Farming Advisory</h5>
            </div>
            <div class="card-body">
                <h6><i class="fas fa-check-circle text-success me-2"></i>Based on current conditions:</h6>
                <ul>
                    <li>Temperature is optimal for most crops. Continue regular irrigation.</li>
                    <li>Humidity levels are good. Monitor for fungal diseases.</li>
                    <li>No extreme weather predicted. Safe to proceed with field operations.</li>
                    <li>Consider applying fertilizers in the next 2-3 days when soil moisture is adequate.</li>
                </ul>
            </div>
        </div>
    </div>
</div>
"""

FERTILIZER_CONTENT = """
<div class="row mb-4">
    <div class="col-12">
        <h2 class="mb-4">
            <i class="fas fa-flask me-2"></i>
            Fertilizer & Soil Management
        </h2>
    </div>
</div>

{% if ml_model_available %}
<div class="alert alert-info">
    <i class="fas fa-robot me-2"></i>
    <strong>New!</strong> Try our <a href="{{ url_for('ml_fertilizer_predictor') }}" class="alert-link">KNN-Powered Fertilizer Predictor</a> 
    for advanced recommendations based on K-Nearest Neighbors algorithm.
</div>
{% endif %}

<div class="row mb-4">
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0"><i class="fas fa-vial me-2"></i>Latest Soil Test Results</h5>
            </div>
            <div class="card-body">
                {% if soil_data %}
                {% set latest = soil_data[0] %}
                <p><strong>Test Date:</strong> {{ latest.test_date }}</p>
                <hr>
                <div class="row text-center mb-3">
                    <div class="col-4">
                        <h3 class="{{ get_soil_status_class(latest.nitrogen_level) }}">{{ latest.nitrogen_level }}</h3>
                        <p class="mb-0">Nitrogen (N)</p>
                    </div>
                    <div class="col-4">
                        <h3 class="{{ get_soil_status_class(latest.phosphorus_level) }}">{{ latest.phosphorus_level }}</h3>
                        <p class="mb-0">Phosphorus (P)</p>
                    </div>
                    <div class="col-4">
                        <h3 class="{{ get_soil_status_class(latest.potassium_level) }}">{{ latest.potassium_level }}</h3>
                        <p class="mb-0">Potassium (K)</p>
                    </div>
                </div>
                <p><strong>pH Level:</strong> {{ "%.1f"|format(latest.ph_level) }}</p>
                {% if latest.recommendations %}
                <p><strong>Notes:</strong> {{ latest.recommendations }}</p>
                {% endif %}
                {% else %}
                <p class="text-muted">No soil test data available. Add your first test below.</p>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0"><i class="fas fa-clipboard-check me-2"></i>Fertilizer Recommendation</h5>
            </div>
            <div class="card-body">
                {% if crops %}
                <form method="GET" class="mb-3">
                    <label for="crop" class="form-label">Select Crop:</label>
                    <select name="crop" id="crop" class="form-select" onchange="this.form.submit()">
                        {% for crop in crops %}
                        <option value="{{ crop.crop_type }}" {% if crop.crop_type == selected_crop %}selected{% endif %}>
                            {{ crop.crop_type }}
                        </option>
                        {% endfor %}
                    </select>
                </form>
                {% endif %}

                {% if recommendation %}
                <div class="alert alert-{{ 'success' if recommendation.status == 'Good' else 'warning' }}">
                    <strong>{{ recommendation.status }}:</strong> {{ recommendation.message }}
                </div>
                <p>{{ recommendation.recommendation }}</p>
                {% else %}
                <p class="text-muted">Add crops and soil test data to get recommendations.</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-warning text-dark">
                <h5 class="mb-0"><i class="fas fa-plus-circle me-2"></i>Add New Soil Test Result</h5>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="row">
                        <div class="col-md-3 mb-3">
                            <label for="test_date" class="form-label">Test Date</label>
                            <input type="date" class="form-control" id="test_date" name="test_date" 
                                   value="{{ current_date }}" required>
                        </div>
                        <div class="col-md-3 mb-3">
                            <label for="n_level" class="form-label">Nitrogen Level</label>
                            <select class="form-select" id="n_level" name="n_level" required>
                                <option value="Very Low">Very Low</option>
                                <option value="Low">Low</option>
                                <option value="Medium" selected>Medium</option>
                                <option value="High">High</option>
                                <option value="Very High">Very High</option>
                            </select>
                        </div>
                        <div class="col-md-3 mb-3">
                            <label for="p_level" class="form-label">Phosphorus Level</label>
                            <select class="form-select" id="p_level" name="p_level" required>
                                <option value="Very Low">Very Low</option>
                                <option value="Low">Low</option>
                                <option value="Medium" selected>Medium</option>
                                <option value="High">High</option>
                                <option value="Very High">Very High</option>
                            </select>
                        </div>
                        <div class="col-md-3 mb-3">
                            <label for="k_level" class="form-label">Potassium Level</label>
                            <select class="form-select" id="k_level" name="k_level" required>
                                <option value="Very Low">Very Low</option>
                                <option value="Low">Low</option>
                                <option value="Medium" selected>Medium</option>
                                <option value="High">High</option>
                                <option value="Very High">Very High</option>
                            </select>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="ph_level" class="form-label">pH Level</label>
                            <input type="number" step="0.1" min="4" max="9" class="form-control" 
                                   id="ph_level" name="ph_level" value="6.5" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="recommendations" class="form-label">Additional Notes (Optional)</label>
                            <input type="text" class="form-control" id="recommendations" name="recommendations" 
                                   placeholder="Any observations or lab recommendations">
                        </div>
                    </div>
                    <button type="submit" name="soil_test_submit" class="btn btn-warning">
                        <i class="fas fa-save me-2"></i>Save Test Result
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>

{% if soil_data and soil_data|length > 1 %}
<div class="row mt-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0"><i class="fas fa-history me-2"></i>Soil Test History</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>N</th>
                                <th>P</th>
                                <th>K</th>
                                <th>pH</th>
                                <th>Notes</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for test in soil_data[1:] %}
                            <tr>
                                <td>{{ test.test_date }}</td>
                                <td class="{{ get_soil_status_class(test.nitrogen_level) }}">{{ test.nitrogen_level }}</td>
                                <td class="{{ get_soil_status_class(test.phosphorus_level) }}">{{ test.phosphorus_level }}</td>
                                <td class="{{ get_soil_status_class(test.potassium_level) }}">{{ test.potassium_level }}</td>
                                <td>{{ "%.1f"|format(test.ph_level) }}</td>
                                <td>{{ test.recommendations or '-' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endif %}
"""

ML_PREDICTOR_CONTENT = """
<div class="row mb-4">
    <div class="col-12">
        <h2 class="mb-4">
            <i class="fas fa-robot me-2"></i>
            KNN-Powered Fertilizer Predictor
        </h2>
        <p class="lead">Get personalized fertilizer recommendations using K-Nearest Neighbors machine learning algorithm</p>
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            <strong>How it works:</strong> The KNN algorithm analyzes your farm parameters and compares them with similar cases in our database to provide the most suitable fertilizer recommendation.
        </div>
    </div>
</div>

{% if not ml_model_available %}
<div class="alert alert-danger">
    <i class="fas fa-exclamation-triangle me-2"></i>
    <strong>KNN Model Not Available:</strong> The machine learning model could not be loaded. Please ensure knn_model.pkl and scaler.pkl are in the application directory.
</div>
{% endif %}

<div class="row">
    <div class="col-lg-8 mx-auto">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0"><i class="fas fa-brain me-2"></i>Enter Your Farm Parameters</h5>
            </div>
            <div class="card-body">
                <form id="mlPredictionForm">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="crop" class="form-label"><i class="fas fa-seedling me-1"></i>Crop Type</label>
                            <select class="form-select" id="crop" name="crop" required>
                                <optgroup label="Cereals">
                                    {% for crop in crops.cereals %}
                                    <option value="{{ crop }}">{{ crop }}</option>
                                    {% endfor %}
                                </optgroup>
                                <optgroup label="Pulses">
                                    {% for crop in crops.pulses %}
                                    <option value="{{ crop }}">{{ crop }}</option>
                                    {% endfor %}
                                </optgroup>
                                <optgroup label="Oilseeds">
                                    {% for crop in crops.oilseeds %}
                                    <option value="{{ crop }}">{{ crop }}</option>
                                    {% endfor %}
                                </optgroup>
                                <optgroup label="Cash Crops">
                                    {% for crop in crops.cash_crops %}
                                    <option value="{{ crop }}">{{ crop }}</option>
                                    {% endfor %}
                                </optgroup>
                                <optgroup label="Vegetables">
                                    {% for crop in crops.vegetables %}
                                    <option value="{{ crop }}">{{ crop }}</option>
                                    {% endfor %}
                                </optgroup>
                                <optgroup label="Fruits">
                                    {% for crop in crops.fruits %}
                                    <option value="{{ crop }}">{{ crop }}</option>
                                    {% endfor %}
                                </optgroup>
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="region" class="form-label"><i class="fas fa-map-marker-alt me-1"></i>Region</label>
                            <select class="form-select" id="region" name="region" required>
                                {% for region in regions %}
                                <option value="{{ region }}">{{ region }}</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="month" class="form-label"><i class="fas fa-calendar me-1"></i>Month</label>
                            <select class="form-select" id="month" name="month" required>
                                {% for month in months %}
                                <option value="{{ month }}">{{ month }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="temperature" class="form-label"><i class="fas fa-thermometer-half me-1"></i>Temperature (°C)</label>
                            <input type="number" class="form-control" id="temperature" name="temperature" 
                                   min="10" max="50" step="0.1" value="25" required>
                            <div class="form-text">Range: 10-50°C</div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label for="N" class="form-label"><i class="fas fa-flask me-1"></i>Nitrogen (N)</label>
                            <input type="number" class="form-control" id="N" name="N" 
                                   min="0" max="300" value="50" required>
                            <div class="form-text">Range: 0-300</div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="P" class="form-label"><i class="fas fa-flask me-1"></i>Phosphorus (P)</label>
                            <input type="number" class="form-control" id="P" name="P" 
                                   min="0" max="200" value="30" required>
                            <div class="form-text">Range: 0-200</div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="K" class="form-label"><i class="fas fa-flask me-1"></i>Potassium (K)</label>
                            <input type="number" class="form-control" id="K" name="K" 
                                   min="0" max="250" value="40" required>
                            <div class="form-text">Range: 0-250</div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label for="humidity" class="form-label"><i class="fas fa-tint me-1"></i>Humidity (%)</label>
                            <input type="number" class="form-control" id="humidity" name="humidity" 
                                   min="0" max="100" value="65" required>
                            <div class="form-text">Range: 0-100%</div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="ph" class="form-label"><i class="fas fa-vial me-1"></i>pH Level</label>
                            <input type="number" class="form-control" id="ph" name="ph" 
                                   min="4" max="9" step="0.1" value="6.5" required>
                            <div class="form-text">Range: 4.0-9.0</div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label for="moisture" class="form-label"><i class="fas fa-droplet me-1"></i>Soil Moisture (%)</label>
                            <input type="number" class="form-control" id="moisture" name="moisture" 
                                   min="0" max="100" value="50" required>
                            <div class="form-text">Range: 0-100%</div>
                        </div>
                    </div>

                    <div class="d-grid">
                        <button type="submit" class="btn btn-success btn-lg" {% if not ml_model_available %}disabled{% endif %}>
                            <i class="fas fa-magic me-2"></i>Get KNN Recommendation
                        </button>
                    </div>
                </form>

                <div id="loadingSpinner" class="text-center mt-4" style="display:none;">
                    <div class="spinner-border text-success" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Analyzing with KNN algorithm...</p>
                </div>

                <div id="predictionResult" class="mt-4" style="display:none;">
                    <div class="alert alert-success">
                        <h5><i class="fas fa-check-circle me-2"></i>Recommended Fertilizer</h5>
                        <h3 id="fertilizerName" class="mb-2"></h3>
                        <p class="mb-1"><strong>Type:</strong> <span id="fertilizerType"></span></p>
                        <p class="mb-1"><strong>Confidence Score:</strong> <span id="confidenceScore" class="badge bg-success"></span></p>
                        <p class="mb-0"><strong>Algorithm:</strong> <span id="algorithmUsed" class="badge bg-info"></span></p>
                    </div>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Note:</strong> This recommendation is based on K-Nearest Neighbors analysis of similar farm conditions in our database.
                    </div>
                </div>

                <div id="predictionError" class="mt-4 alert alert-danger" style="display:none;">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <span id="errorMessage"></span>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.getElementById('mlPredictionForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        crop: document.getElementById('crop').value,
        region: document.getElementById('region').value,
        month: document.getElementById('month').value,
        temperature: parseFloat(document.getElementById('temperature').value),
        N: parseFloat(document.getElementById('N').value),
        P: parseFloat(document.getElementById('P').value),
        K: parseFloat(document.getElementById('K').value),
        humidity: parseFloat(document.getElementById('humidity').value),
        ph: parseFloat(document.getElementById('ph').value),
        moisture: parseFloat(document.getElementById('moisture').value)
    };
    document.getElementById('predictionResult').style.display = 'none';
    document.getElementById('predictionError').style.display = 'none';
    document.getElementById('loadingSpinner').style.display = 'block'; 

    try { 
        const response = await fetch('/predict', { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json', 
            }, 
            body: JSON.stringify(formData) 
        });
        const data = await response.json(); 
        document.getElementById('loadingSpinner').style.display = 'none'; 

        if (response.ok) { 
            document.getElementById('fertilizerName').textContent = data.fertilizer; 
            document.getElementById('fertilizerType').textContent = data.fertilizer_type;
            document.getElementById('confidenceScore').textContent = data.confidence.toFixed(2) + '%'; 
            document.getElementById('algorithmUsed').textContent = data.algorithm; 
            document.getElementById('predictionResult').style.display = 'block'; 
        } else { 
            document.getElementById('errorMessage').textContent = data.error || 'Prediction failed';
            document.getElementById('predictionError').style.display = 'block'; 
        } 
    } catch (error) { 
        document.getElementById('loadingSpinner').style.display = 'none'; 
        document.getElementById('errorMessage').textContent = 'Network error: ' + error.message;
        document.getElementById('predictionError').style.display = 'block'; 
    } 
});
</script>
"""

CROP_MANAGEMENT_CONTENT = """ 
<div class="row mb-4"> 
    <div class="col-12"> 
        <h2 class="mb-4"> 
            <i class="fas fa-tractor me-2"></i> Crop Management 
        </h2> 
    </div> 
</div> 
<div class="row"> 
    <div class="col-lg-8 mb-4"> 
        <div class="card"> 
            <div class="card-header bg-success text-white"> 
                <h5 class="mb-0"><i class="fas fa-list me-2"></i>Your Active Crops</h5> 
            </div> 
            <div class="card-body"> 
                {% if user_crops %} 
                <div class="table-responsive"> 
                    <table class="table table-hover"> 
                        <thead> 
                            <tr> 
                                <th>Crop Type</th> 
                                <th>Acreage</th> 
                                <th>Stage</th> 
                                <th>Planted Date</th> 
                                <th>Action</th> 
                            </tr> 
                        </thead> 
                        <tbody> 
                            {% for crop in user_crops %} 
                            <tr> 
                                <td><strong>{{ crop.crop_type }}</strong></td> 
                                <td>{{ crop.acre }}</td> 
                                <td><span class="badge bg-info">{{ crop.stage }}</span></td> 
                                <td>{{ crop.planting_date }}</td> 
                                <td> 
                                    <form method="POST" action="{{ url_for('crop_management') }}" style="display:inline;"> 
                                        <input type="hidden" name="crop_id" value="{{ crop.id }}"> 
                                        <button type="submit" name="delete_crop" class="btn btn-sm btn-danger" 
                                                onclick="return confirm('Are you sure you want to delete this crop?')"> 
                                            <i class="fas fa-trash"></i> 
                                        </button> 
                                    </form> 
                                </td> 
                            </tr> 
                            {% endfor %} 
                        </tbody> 
                    </table> 
                </div> 
                {% else %} 
                <p class="text-muted text-center py-4">No crops added yet. Add your first crop using the form.</p> 
                {% endif %} 
            </div> 
        </div> 
    </div> 
    <div class="col-lg-4 mb-4"> 
        <div class="card"> 
            <div class="card-header bg-primary text-white"> 
                <h5 class="mb-0"><i class="fas fa-plus-circle me-2"></i>Add New Crop</h5> 
            </div> 
            <div class="card-body"> 
                <form method="POST"> 
                    <div class="mb-3"> 
                        <label for="crop_type" class="form-label">Crop Type</label> 
                        <input type="text" class="form-control" id="crop_type" name="crop_type" placeholder="e.g., Wheat, Rice" required> 
                    </div> 
                    <div class="mb-3"> 
                        <label for="acre" class="form-label">Acreage</label> 
                        <input type="number" step="0.01" class="form-control" id="acre" name="acre" placeholder="Enter acres" required> 
                    </div> 
                    <div class="mb-3"> 
                        <label for="stage" class="form-label">Growth Stage</label> 
                        <select class="form-select" id="stage" name="stage" required> 
                            <option value="Planting">Planting</option> 
                            <option value="Growing" selected>Growing</option> 
                            <option value="Flowering">Flowering</option> 
                            <option value="Harvesting">Harvesting</option> 
                        </select> 
                    </div> 
                    <div class="mb-3"> 
                        <label for="planting_date" class="form-label">Planting Date</label> 
                        <input type="date" class="form-control" id="planting_date" name="planting_date" required> 
                    </div> 
                    <button type="submit" name="add_crop" class="btn btn-primary w-100"> 
                        <i class="fas fa-plus me-2"></i>Add Crop 
                    </button> 
                </form> 
            </div> 
        </div> 
    </div> 
</div> 
"""

PROFILE_CONTENT = """ 
<div class="row mb-4"> 
    <div class="col-12"> 
        <h2 class="mb-4"> 
            <i class="fas fa-user me-2"></i> User Profile 
        </h2> 
    </div> 
</div> 
<div class="row"> 
    <div class="col-lg-8 mb-4"> 
        <div class="card"> 
            <div class="card-header bg-primary text-white"> 
                <h5 class="mb-0"><i class="fas fa-edit me-2"></i>Edit Profile Details</h5> 
            </div> 
            <div class="card-body"> 
                <form method="POST"> 
                    <div class="row"> 
                        <div class="col-md-6 mb-3"> 
                            <label for="full_name" class="form-label">Full Name</label> 
                            <input type="text" class="form-control" id="full_name" name="full_name" required 
                                   value="{{ user.full_name }}"> 
                        </div> 
                        <div class="col-md-6 mb-3"> 
                            <label for="email" class="form-label">Email Address</label> 
                            <input type="email" class="form-control" id="email" name="email" required 
                                   value="{{ user.email }}"> 
                        </div> 
                    </div> 
                    <div class="row"> 
                        <div class="col-md-6 mb-3"> 
                            <label for="phone" class="form-label">Phone Number</label> 
                            <input type="tel" class="form-control" id="phone" name="phone" required 
                                   value="{{ user.phone }}"> 
                        </div> 
                        <div class="col-md-6 mb-3"> 
                            <label for="farm_name" class="form-label">Farm Name</label> 
                            <input type="text" class="form-control" id="farm_name" name="farm_name" required 
                                   value="{{ user.farm_name }}"> 
                        </div> 
                    </div> 
                    <div class="row"> 
                        <div class="col-md-6 mb-3"> 
                            <label for="location" class="form-label">Location</label> 
                            <input type="text" class="form-control" id="location" name="location" required 
                                   value="{{ user.location }}"> 
                        </div> 
                        <div class="col-md-6 mb-3"> 
                            <label for="total_land" class="form-label">Total Land (acres)</label> 
                            <input type="number" step="0.01" class="form-control" id="total_land" name="total_land" required 
                                   value="{{ user.total_land }}"> 
                        </div> 
                    </div> 
                    <button type="submit" class="btn btn-primary"> 
                        <i class="fas fa-save me-2"></i>Update Profile 
                    </button> 
                </form> 
            </div> 
        </div> 
        <div class="card mt-4"> 
            <div class="card-header bg-warning text-dark"> 
                <h5 class="mb-0"><i class="fas fa-info-circle me-2"></i>Account Information</h5> 
            </div> 
            <div class="card-body"> 
                <p><strong>Username:</strong> {{ user.username }} <span class="badge bg-secondary">Cannot be changed</span></p> 
                <p><strong>Account Created:</strong> {{ user.member_since }}</p> 
                <p class="text-muted mb-0"><i class="fas fa-shield-alt me-2"></i>Your password is securely encrypted</p> 
            </div> 
        </div> 
    </div> 
</div>
"""

CONTACT_CONTENT = """
<div class="row mb-4"> 
    <div class="col-12"> 
        <h2 class="mb-4"> 
            <i class="fas fa-envelope me-2"></i> Contact & Support 
        </h2> 
    </div> 
</div> 
<div class="row"> 
    <div class="col-lg-8 mb-4"> 
        <div class="card"> 
            <div class="card-header bg-success text-white"> 
                <h5 class="mb-0"><i class="fas fa-question-circle me-2"></i> Send us a message</h5> 
            </div> 
            <div class="card-body"> 
                <p>Have a question or need technical support? Fill out the form below.</p>
                <form method="POST">
                    <div class="mb-3">
                        <label for="subject" class="form-label">Subject</label>
                        <input type="text" class="form-control" id="subject" name="subject" required placeholder="e.g., Issue with dashboard, Feature request">
                    </div>
                    <div class="mb-3">
                        <label for="message" class="form-label">Message</label>
                        <textarea class="form-control" id="message" name="message" rows="5" required placeholder="Describe your issue or request in detail"></textarea>
                    </div>
                    <button type="submit" class="btn btn-success">
                        <i class="fas fa-paper-plane me-2"></i> Send Message
                    </button>
                </form>
            </div>
        </div> 
    </div> 
    <div class="col-lg-4 mb-4">
        <div class="card">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0"><i class="fas fa-headset me-2"></i> Support Info</h5>
            </div>
            <div class="card-body">
                <p><strong>Email:</strong> help@agridash.com</p>
                <p><strong>Phone:</strong> +91 1800-AGRIHELP</p>
                <p><strong>Hours:</strong> Mon - Fri, 9 AM - 5 PM IST</p>
                <hr>
                <h6>Active Users: {{ all_users|length }}</h6>
            </div>
        </div>
    </div>
</div>
"""


# ==============================================================================
# --- Flask App Initialization ---
# ==============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

# ==============================================================================
# --- KNN Model Loading ---
# ==============================================================================

MODEL_PATH = "knn_model.pkl"
SCALER_PATH = "scaler.pkl"
knn_model = None
scaler = None
ml_model_available = False

if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
    try:
        with open(MODEL_PATH, 'rb') as f:
            knn_model = pickle.load(f)
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)

        # Check if the loaded model has the necessary properties
        if hasattr(knn_model, 'predict') and hasattr(scaler, 'transform'):
            ml_model_available = True
        else:
            print("Warning: Loaded files do not appear to be valid scikit-learn model/scaler objects.")

    except Exception as e:
        print(f"Error loading KNN model or scaler: {e}")

# ==============================================================================
# --- ML/App Data ---
# ==============================================================================

crops_ml = {
    "cereals": ["Rice", "Wheat", "Maize (Corn)", "Barley", "Oats", "Ragi (Finger Millet)", "Jowar (Sorghum)",
                "Bajra (Pearl Millet)"],
    "pulses": ["Horse Gram (Kulthi)", "Moth Bean (Matki)", "Kidney Bean (Rajma)", "Black Gram (Urad)",
               "Green Gram (Moong)", "Bengal Gram (Chana)", "Red Gram (Arhar)", "Grass Pea (Khesari)"],
    "oilseeds": ["Groundnut", "Mustard", "Soybean", "Sunflower", "Sesame (Til)", "Safflower", "Niger Seed", "Castor",
                 "Linseed", "Coconut", "Oil Palm", "Cottonseed", "Rapeseed", "Palm Kernel"],
    "cash_crops": ["Sugarcane", "Cotton", "Jute", "Tobacco", "Rubber", "Tea", "Coffee", "Cocoa", "Indigo",
                   "Opium Poppy"],
    "vegetables": ["Potato", "Tomato", "Onion", "Brinjal (Eggplant)", "Okra (Bhindi)", "Cauliflower", "Cabbage",
                   "Carrot", "Radish", "Cucumber", "Bottle Gourd", "Bitter Gourd", "Ridge Gourd", "Snake Gourd",
                   "Pumpkin", "Spinach", "Fenugreek (Methi)", "Amaranth (Chaulai)", "Drumstick", "Peas", "Beans",
                   "Capsicum", "Chilli", "Garlic", "Ginger", "Turmeric", "Sweet Potato", "Tapioca", "Yam", "Colocasia"],
    "fruits": ["Mango", "Banana", "Citrus (Orange, Lemon, Lime)", "Apple", "Grapes", "Pomegranate", "Guava",
               "Pineapple", "Papaya", "Watermelon", "Muskmelon", "Pear", "Peach", "Plum", "Apricot", "Litchi",
               "Jackfruit", "Ber", "Aonla (Indian Gooseberry)", "Custard Apple", "Jamun", "Kiwi", "Strawberry", "Fig",
               "Cherry", "Avocado", "Persimmon", "Passion Fruit", "Dragon Fruit"]
}

regions_ml = sorted([
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi"
])

months_ml = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

fertilizers_ml = sorted([
    # Nitrogenous Fertilizers
    "Ammonium Nitrate (AN)", "Ammonium Sulphate (AS)", "Ammonium Thiosulphate",
    "Calcium Ammonium Nitrate (CAN)", "Urea", "UAN (Urea Ammonium Nitrate) Solution",
    "Nitrate of Soda", "Potassium Nitrate (KNO3)", "Sodium Nitrate", "Liquid Nitrogen Fertilizers",

    # Phosphatic Fertilizers
    "Single Super Phosphate (SSP)", "Triple Super Phosphate (TSP)", "Di-Ammonium Phosphate (DAP)",
    "Mono-Ammonium Phosphate (MAP)", "Rock Phosphate", "Bone Meal", "Calcium Phosphate",

    # Potassic Fertilizers
    "Muriate of Potash (MOP) / Potassium Chloride", "Sulphate of Potash (SOP)", "Potassium Sulphate",

    # Micronutrient Fertilizers
    "Zinc Sulphate", "Copper Sulphate", "Magnesium Sulphate (Epsom Salt)", "Manganese Sulphate",
    "Ferrous Sulphate", "Boron Fertilizers (e.g., Borax)", "Chelated Zinc", "Chelated Iron",
    "Chelated Copper", "Chelated Manganese",

    # Organic Fertilizers
    "Compost", "Farm Yard Manure (FYM)", "Chicken Manure", "Sheep Manure", "Cow Manure",
    "Vermicompost (Worm Castings)", "Bone Meal", "Blood Meal", "Feather Meal", "Fish Meal",
    "Alfalfa Meal", "Kelp Meal", "Seaweed Extract", "Green Manure", "Worm Castings", "Humus",

    # Specialty Fertilizers
    "Osmocote (Controlled-Release Fertilizer)", "Polyon", "Nutricote", "Humic Acids", "Fulvic Acids",
    "Organomineral Fertilizers", "NPK Fertilizers (Water-Soluble)", "Liquid Fertilizers",
    "Custom NPK Mixes", "Custom Micronutrient Mixes",

    # Liquid & Foliar Fertilizers
    "Liquid Zinc", "Liquid Iron", "Liquid Copper", "Liquid Fertilizer (Balanced NPK)",
    "Foliar Sprays (NPK or Micronutrient-based)", "Seaweed-based Foliar Fertilizers",

    # Biological Fertilizers
    "Rhizobium-based Fertilizers", "Azotobacter-based Fertilizers", "Cyanobacteria-based Fertilizers",
    "Arbuscular Mycorrhizal Fungi (AMF)", "Ectomycorrhizal Fungi", "Bacillus-based Fertilizers",
    "Pseudomonas-based Fertilizers",

    # Emerging & Advanced Fertilizers
    "Nano Nitrogen Fertilizers", "Nano Phosphorus Fertilizers", "Fertilizers with Sensor-based Delivery",
    "Fertilizers with Controlled Release Technology", "Nano-Encapsulated Nutrients",
    "Fully Water-soluble NPK", "Fertilizers for Irrigation Systems", "Slow-Release Nitrogen Fertilizers",
    "Enhanced Efficiency Fertilizers (e.g., Urease Inhibitors)",

    # Other Fertilizers
    "Gypsum", "Lime (Agricultural Lime)", "Sulphur (Elemental and Bentonite)", "Barium Sulphate",
    "Calcium Carbonate", "Calcium Magnesium Fertilizers", "Sodium Sulphate", "Magnesium Oxide"
])

# Create integer mappings for ML model input
crop_to_int = {crop: i for i, crop in enumerate([item for sublist in crops_ml.values() for item in sublist])}
region_to_int = {region: i for i, region in enumerate(regions_ml)}
month_to_int = {month: i for i, month in enumerate(months_ml)}
EXPECTED_MODEL_INPUT_FEATURES = 10


# ==============================================================================
# --- Database Functions ---
# ==============================================================================

def init_db():
    """Initialize SQLite database with users table if it doesn't exist."""
    conn = sqlite3.connect('agridash.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            farm_name TEXT NOT NULL,
            location TEXT DEFAULT 'Delhi',
            total_land REAL DEFAULT 10.0,
            member_since TEXT DEFAULT CURRENT_DATE,
            reset_token TEXT,
            token_expiry DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            acre REAL NOT NULL,
            crop_type TEXT NOT NULL,
            stage TEXT NOT NULL,
            planting_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS soil_testing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            test_date TEXT NOT NULL,
            nitrogen_level TEXT,
            phosphorus_level TEXT,
            potassium_level TEXT,
            ph_level REAL,
            recommendations TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()


def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect('agridash.db')
    conn.row_factory = sqlite3.Row
    return conn


# --- User Retrieval Functions ---

def get_user_by_id(user_id):
    """Retrieve a user by their ID."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user


def get_user_by_email(email):
    """Retrieve a user by their email address."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user


def get_user_by_identifier(identifier):
    """Retrieve a user by their username or email."""
    conn = get_db_connection()
    # Check for username first
    user = conn.execute('SELECT * FROM users WHERE username = ?', (identifier,)).fetchone()
    if not user:
        # Check for email if not found by username
        user = conn.execute('SELECT * FROM users WHERE email = ?', (identifier,)).fetchone()
    conn.close()
    return user


def get_user_by_reset_token(token):
    """Retrieve a user by their reset token, only if it hasn't expired."""
    conn = get_db_connection()
    # Ensure token_expiry is not NULL and is greater than the current time
    user = conn.execute(
        'SELECT * FROM users WHERE reset_token = ? AND token_expiry > datetime("now")',
        (token,)
    ).fetchone()
    conn.close()
    return user


def set_reset_token(user_id, token):
    """Set a password reset token and 1-hour expiry for the user."""
    conn = get_db_connection()
    # Set token expiry to 1 hour from now
    expiry_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn.execute(
            'UPDATE users SET reset_token = ?, token_expiry = ? WHERE id = ?',
            (token, expiry_time, user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Set reset token error: {e}")
        return False
    finally:
        conn.close()


def get_all_users():
    """Retrieve all users from the database."""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return users


# --- User CRUD Functions ---

def create_user(username, password_hash, email, phone, full_name, farm_name, location, total_land):
    """Create a new user in the database."""
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO users (username, password_hash, email, phone, full_name, farm_name, location, total_land) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (username, password_hash, email, phone, full_name, farm_name, location, total_land)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Integrity error: {e}")
        return False
    finally:
        conn.close()


def update_password(user_id, password_hash):
    """Update user password."""
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE users SET password_hash = ?, reset_token = NULL, token_expiry = NULL WHERE id = ?',
            (password_hash, user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Password update error: {e}")
        return False
    finally:
        conn.close()


def update_user_profile(user_id, email, phone, full_name, farm_name, location, total_land):
    """Update user profile details."""
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE users SET email = ?, phone = ?, full_name = ?, farm_name = ?, location = ?, total_land = ? WHERE id = ?',
            (email, phone, full_name, farm_name, location, total_land, user_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Profile update integrity error: {e}")
        return False
    finally:
        conn.close()


# --- Crop CRUD Functions ---

def add_user_crop(user_id, acre, crop_type, stage, planting_date):
    """Add a new crop for the user."""
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO crops (user_id, acre, crop_type, stage, planting_date) VALUES (?, ?, ?, ?, ?)',
            (user_id, acre, crop_type, stage, planting_date)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Add crop error: {e}")
        return False
    finally:
        conn.close()


def get_user_crops(user_id):
    """Retrieve all crops for the given user."""
    conn = get_db_connection()
    crops = conn.execute(
        'SELECT * FROM crops WHERE user_id = ? ORDER BY planting_date DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return crops


def delete_user_crop(crop_id, user_id):
    """Delete a crop belonging to the user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM crops WHERE id = ? AND user_id = ?',
        (crop_id, user_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


# --- Soil Testing Functions ---

def get_soil_testing_data(user_id):
    """Retrieve all soil test results for the user, newest first."""
    conn = get_db_connection()
    data = conn.execute(
        'SELECT * FROM soil_testing WHERE user_id = ? ORDER BY test_date DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return data


def get_last_soil_test_date(soil_data):
    """Get the date of the most recent soil test."""
    if soil_data:
        return soil_data[0]['test_date']
    return 'N/A'


def add_soil_test_result(user_id, test_date, n_level, p_level, k_level, ph_level, recommendations):
    """Add a new soil test result for the user."""
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO soil_testing (user_id, test_date, nitrogen_level, phosphorus_level, potassium_level, ph_level, recommendations) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, test_date, n_level, p_level, k_level, ph_level, recommendations)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Add soil test error: {e}")
        return False
    finally:
        conn.close()


# ==============================================================================
# --- Static Data/Simulation Functions ---
# ==============================================================================

STATIC_WEATHER = {
    'Delhi': {'temperature': 28, 'description': 'Sunny with haze', 'humidity': 65, 'icon': '☀️', 'wind': '5 km/h'},
    'Pune': {'temperature': 24, 'description': 'Partly Cloudy', 'humidity': 70, 'icon': '⛅', 'wind': '10 km/h'},
    'Shimla': {'temperature': 15, 'description': 'Cloudy, chance of rain', 'humidity': 60, 'icon': '☁️',
               'wind': '8 km/h'},
    'Bangalore': {'temperature': 26, 'description': 'Clear skies', 'humidity': 68, 'icon': '☀️', 'wind': '7 km/h'},
    'Mumbai': {'temperature': 30, 'description': 'Humid and Overcast', 'humidity': 80, 'icon': '🌧️', 'wind': '12 km/h'},
    'Hyderabad': {'temperature': 27, 'description': 'Light Rain', 'humidity': 75, 'icon': '🌧️', 'wind': '8 km/h'}
}


def get_weather_data(location):
    """Fetches weather data for a given location, defaulting to Delhi if location is unknown."""
    city = location.title()  # Capitalize first letter of each word
    if city in STATIC_WEATHER:
        data = STATIC_WEATHER[city].copy()
        data['city'] = city
        data['forecast'] = [
            {'day': 'Tomorrow', 'condition': 'Sunny', 'high': 29, 'low': 20, 'icon': '☀️'},
            {'day': 'Day 3', 'condition': 'Partly Cloudy', 'high': 27, 'low': 18, 'icon': '⛅'},
            {'day': 'Day 4', 'condition': 'Light Rain', 'high': 25, 'low': 17, 'icon': '🌧️'},
        ]
        return data

    # Fallback to Delhi if user location is not in static data
    data = STATIC_WEATHER['Delhi'].copy()
    data['city'] = 'Delhi'
    data['forecast'] = [
        {'day': 'Tomorrow', 'condition': 'Sunny', 'high': 29, 'low': 20, 'icon': '☀️'},
        {'day': 'Day 3', 'condition': 'Partly Cloudy', 'high': 27, 'low': 18, 'icon': '⛅'},
        {'day': 'Day 4', 'condition': 'Light Rain', 'high': 25, 'low': 17, 'icon': '🌧️'},
    ]
    return data


def get_fertilizer_recommendation(soil_data, crop_type):
    """Generates a fertilizer recommendation based on the latest soil test data."""
    if not soil_data:
        return None

    recent_test = soil_data[0]
    n_status = recent_test['nitrogen_level']
    p_status = recent_test['phosphorus_level']
    k_status = recent_test['potassium_level']
    ph = recent_test['ph_level']

    # Simple rule-based recommendation logic (can be expanded)
    base_rec = "Maintain current regimen. "
    if n_status in ['Low', 'Very Low']:
        base_rec += "Increase Nitrogen (N) application (e.g., Urea). "
    if p_status in ['Low', 'Very Low']:
        base_rec += "Increase Phosphorus (P) application (e.g., DAP). "
    if k_status in ['Low', 'Very Low']:
        base_rec += "Increase Potassium (K) application (e.g., Muriate of Potash). "

    if ph < 6.0:
        base_rec += "Soil pH is low (acidic). Consider liming (Calcium Carbonate). "
    elif ph > 7.5:
        base_rec += "Soil pH is high (alkaline). Consider Sulphur application. "

    if base_rec == "Maintain current regimen. ":
        base_rec += "Soil levels are balanced."
        status = "Good"
    else:
        status = "Needs Adjustment"

    return {
        'status': status,
        'message': f"Recommendation for **{crop_type.title()}** based on soil test from **{recent_test['test_date']}**.",
        'recommendation': base_rec
    }


def get_soil_status_class(level):
    """Utility to map soil levels to CSS classes."""
    if level in ['High', 'Very High']:
        return 'soil-status-excellent'
    elif level == 'Medium':
        return 'soil-status-good'
    elif level == 'Low':
        return 'soil-status-fair'
    else:
        return 'soil-status-poor'


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
    elif any(x in fertilizer_name for x in ["Compost", "Organic"]):
        return "Organic Fertilizer"
    else:
        return "Specialty Fertilizer"


def send_reset_email(recipient_email, token):
    """Sends a password reset email to the user."""
    try:
        reset_link = url_for('reset_password', token=token, _external=True)
        subject = "AgriDash Pro Password Reset Request"
        body = f"""
        Dear User,

        You have requested a password reset for your AgriDash Pro account.

        Please click on the link below to reset your password:
        {reset_link}

        This link will expire in 1 hour. If you did not request a password reset, please ignore this email.

        Thank you,
        The AgriDash Pro Team
        """

        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Use a local test server if real server is not configured
        if 'your-email@gmail.com' in app.config['MAIL_USERNAME']:
            print(f"--- FAKE EMAIL SENT ---\nTo: {recipient_email}\nLink: {reset_link}\n-------------------------")
            return True

        # Use the actual configured SMTP server
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ==============================================================================
# --- Utility Functions & Decorators ---
# ==============================================================================

def login_required(f):
    """Decorator to protect routes that require authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def calculate_total_acreage(crops):
    """Calculates the total acreage under cultivation."""
    return sum(float(crop['acre']) for crop in crops) if crops else 0


@app.before_request
def load_logged_in_user_and_weather():
    """Load user data and weather into Flask's global context 'g'."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        # Default to Delhi weather
        g.weather = get_weather_data('Delhi')
    else:
        g.user = get_user_by_id(user_id)
        if g.user and g.user['location']:
            g.weather = get_weather_data(g.user['location'])
        else:
            # Fallback to Delhi weather if user is logged in but location is missing
            g.weather = get_weather_data('Delhi')


# ==============================================================================
# --- Flask Routes ---
# ==============================================================================

@app.route('/', methods=['GET'])
def home():
    """Renders the landing page."""
    # FIX: Check for logged-in user and redirect to dashboard, otherwise show generic landing page.
    if g.user:
        return redirect(url_for('dashboard'))

    return render_template_string(BASE_TEMPLATE + LANDING_PAGE_CONTENT, title='Welcome')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if g.user:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')

        user = get_user_by_identifier(identifier)

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            flash(f'Welcome back, {user["full_name"].split()[0]}!', 'success')
            next_url = request.args.get('next') or url_for('dashboard')
            return redirect(next_url)
        else:
            flash('Login failed. Check your credentials.', 'error')

    return render_template_string(BASE_TEMPLATE + LOGIN_CONTENT, title='Login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles new user registration."""
    if g.user:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username').lower()
        email = request.form.get('email').lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        full_name = request.form.get('full_name')
        farm_name = request.form.get('farm_name')
        location = request.form.get('location')
        total_land = request.form.get('total_land')

        # Basic validation
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email format.', 'error')
        elif password != confirm_password:
            flash('Passwords do not match.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        elif get_user_by_identifier(username) or get_user_by_email(email):
            flash('Username or Email already registered.', 'error')
        else:
            try:
                total_land = float(total_land)
            except ValueError:
                flash('Total land must be a number.', 'error')
                return redirect(url_for('register'))

            password_hash = generate_password_hash(password)

            if create_user(username, password_hash, email, phone, full_name, farm_name, location, total_land):
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed due to a database error.', 'error')

    return render_template_string(BASE_TEMPLATE + REGISTER_CONTENT, title='Register')


@app.route('/logout')
def logout():
    """Handles user logout."""
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handles the forgot password request."""
    if g.user:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = get_user_by_email(email)

        if user:
            token = secrets.token_urlsafe(32)
            if set_reset_token(user['id'], token):
                if send_reset_email(email, token):
                    flash('A password reset link has been sent to your email.', 'success')
                else:
                    flash('Failed to send reset email. Please check server settings.', 'error')
            else:
                flash('An error occurred while setting the reset token.', 'error')
        else:
            # Security measure: flash success even if email not found to prevent user enumeration
            flash('If an account exists with that email, a password reset link has been sent.', 'success')

        return redirect(url_for('forgot_password'))

    return render_template_string(BASE_TEMPLATE + FORGOT_PASSWORD_CONTENT, title='Forgot Password')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles the actual password reset using the token."""
    if g.user:
        return redirect(url_for('dashboard'))

    user = get_user_by_reset_token(token)

    if not user:
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template_string(BASE_TEMPLATE + RESET_PASSWORD_CONTENT, title='Reset Password')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template_string(BASE_TEMPLATE + RESET_PASSWORD_CONTENT, title='Reset Password')

        password_hash = generate_password_hash(password)
        if update_password(user['id'], password_hash):
            flash('Your password has been updated. You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('An error occurred during password update.', 'error')

    return render_template_string(BASE_TEMPLATE + RESET_PASSWORD_CONTENT, title='Reset Password')


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Renders the user's main dashboard."""
    user_crops = get_user_crops(g.user['id'])
    total_acreage = calculate_total_acreage(user_crops)
    soil_data = get_soil_testing_data(g.user['id'])
    last_test_date = get_last_soil_test_date(soil_data)

    # Get recommendation for dashboard (using the first crop found for simplicity)
    dashboard_rec = None
    if user_crops and soil_data:
        dashboard_rec = get_fertilizer_recommendation(soil_data, user_crops[0]['crop_type'])

    # FIX: Add weather=g.weather to the context to resolve UndefinedError
    return render_template_string(
        BASE_TEMPLATE + DASHBOARD_CONTENT,
        title='Dashboard',
        user=g.user,
        crops=user_crops,
        total_acreage=total_acreage,
        last_test_date=last_test_date,
        soil_data=soil_data[0] if soil_data else None,
        get_soil_status_class=get_soil_status_class,
        dashboard_rec=dashboard_rec,
        weather=g.weather  # <--- ADDED THIS LINE
    )


@app.route('/weather', methods=['GET'])
@login_required
def weather():
    """Renders the weather intelligence page."""
    # g.weather is loaded in @app.before_request
    return render_template_string(
        BASE_TEMPLATE + WEATHER_CONTENT,
        title='Weather Intelligence',
        weather=g.weather,
        forecast=g.weather['forecast']
    )


@app.route('/fertilizer', methods=['GET', 'POST'])
@login_required
def fertilizer():
    """Handles the fertilizer and soil management page and form submissions."""
    user_crops = get_user_crops(g.user['id'])
    soil_data = get_soil_testing_data(g.user['id'])

    selected_crop = request.args.get('crop')
    if not selected_crop and user_crops:
        selected_crop = user_crops[0]['crop_type']

    recommendation = None
    if soil_data and selected_crop:
        recommendation = get_fertilizer_recommendation(soil_data, selected_crop)

    if request.method == 'POST':
        if 'soil_test_submit' in request.form:
            test_date = request.form.get('test_date')
            n_level = request.form.get('n_level')
            p_level = request.form.get('p_level')
            k_level = request.form.get('k_level')
            ph_level = request.form.get('ph_level')
            recommendations_text = request.form.get('recommendations')

            try:
                ph_level = float(ph_level)
            except ValueError:
                flash('pH Level must be a number.', 'error')
                return redirect(url_for('fertilizer'))

            if add_soil_test_result(g.user['id'], test_date, n_level, p_level, k_level, ph_level, recommendations_text):
                flash('New soil test results added successfully! Recalculating recommendations.', 'success')
            else:
                flash('Failed to add soil test results.', 'error')

            return redirect(url_for('fertilizer'))

    return render_template_string(
        BASE_TEMPLATE + FERTILIZER_CONTENT,
        title='Fertilizer & Soil Management',
        crops=user_crops,
        soil_data=soil_data,
        recommendation=recommendation,
        selected_crop=selected_crop,
        get_soil_status_class=get_soil_status_class,
        current_date=datetime.now().strftime('%Y-%m-%d'),
        ml_model_available=ml_model_available
    )


@app.route('/ml-fertilizer-predictor', methods=['GET'])
@login_required
def ml_fertilizer_predictor():
    """Renders the KNN-based fertilizer prediction page."""
    return render_template_string(
        BASE_TEMPLATE + ML_PREDICTOR_CONTENT,
        title='KNN Fertilizer Predictor',
        crops=crops_ml,
        regions=regions_ml,
        months=months_ml,
        ml_model_available=ml_model_available
    )


@app.route('/predict', methods=['POST'])
@login_required
def predict():
    """KNN-based fertilizer prediction endpoint."""
    if not ml_model_available:
        return jsonify({"error": "KNN model is not available. Please ensure knn_model.pkl and scaler.pkl exist."}), 503

    try:
        data = request.get_json()
        n_val = float(data.get("N"))
        p_val = float(data.get("P"))
        k_val = float(data.get("K"))
        temp_val = float(data.get("temperature"))
        humidity_val = float(data.get("humidity"))
        ph_val = float(data.get("ph"))
        moisture_val = float(data.get("moisture"))

        # Convert categorical data to integers using the global mappings
        crop_name = data.get("crop")
        region_name = data.get("region")
        month_name = data.get("month")

        crop_int = crop_to_int.get(crop_name)
        region_int = region_to_int.get(region_name)
        month_int = month_to_int.get(month_name)

        if any(v is None for v in [crop_int, region_int, month_int]):
            return jsonify({"error": "Invalid categorical input value."}), 400

        # Features array creation (must match model's training order)
        features = np.array(
            [crop_int, region_int, month_int, temp_val, humidity_val, ph_val, moisture_val, n_val, p_val, k_val])

        # FIX: Reshape the 1D array to a 2D array for the scaler and model.
        features_reshaped = features.reshape(1, -1)
        features_scaled = scaler.transform(features_reshaped)

        # Get the predicted index/label
        predicted_index = knn_model.predict(features_scaled)[0]

        # Calculate confidence score (distance to nearest neighbor heuristic)
        distances, indices = knn_model.kneighbors(features_scaled)
        distance = distances[0][0]
        # This is a heuristic and not a true probability, assuming max distance is 10
        confidence = 1 - (distance / 10)
        confidence = max(0, min(1, confidence))  # Clamp between 0 and 1

        # Map the predicted index back to a fertilizer name
        if 0 <= predicted_index < len(fertilizers_ml):
            predicted_fertilizer = fertilizers_ml[predicted_index]
        else:
            predicted_fertilizer = "Custom Fertilizer Blend"

        return jsonify({
            "fertilizer": predicted_fertilizer,
            "fertilizer_type": categorize_fertilizer(predicted_fertilizer),
            "confidence": float(confidence * 100),  # Return as percentage
            "algorithm": "K-Nearest Neighbors (KNN)"
        })

    except (KeyError, ValueError, IndexError) as e:
        return jsonify({"error": f"Invalid input data or format: {str(e)}"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/crop-management', methods=['GET', 'POST'])
@login_required
def crop_management():
    """Renders the crop management page."""
    user_crops = get_user_crops(g.user['id'])

    if request.method == 'POST':
        if 'add_crop' in request.form:
            acre = request.form.get('acre')
            crop_type = request.form.get('crop_type')
            stage = request.form.get('stage')
            planting_date = request.form.get('planting_date')

            try:
                acre = float(acre)
                if acre <= 0:
                    flash('Acreage must be a positive number.', 'error')
                    return redirect(url_for('crop_management'))
            except ValueError:
                flash('Acreage must be a number.', 'error')
                return redirect(url_for('crop_management'))

            if add_user_crop(g.user['id'], acre, crop_type, stage, planting_date):
                flash(f'{crop_type} added successfully!', 'success')
            else:
                flash('Failed to add crop.', 'error')

            return redirect(url_for('crop_management'))

        elif 'delete_crop' in request.form:
            crop_id = request.form.get('crop_id')
            if delete_user_crop(crop_id, g.user['id']):
                flash('Crop deleted successfully.', 'success')
            else:
                flash('Failed to delete crop.', 'error')

            return redirect(url_for('crop_management'))

    return render_template_string(
        BASE_TEMPLATE + CROP_MANAGEMENT_CONTENT,
        title='Crop Management',
        user_crops=user_crops
    )


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Handles the user profile page and update submissions."""
    if request.method == 'POST':
        email = request.form.get('email').lower()
        phone = request.form.get('phone')
        full_name = request.form.get('full_name')
        farm_name = request.form.get('farm_name')
        location = request.form.get('location')
        total_land = request.form.get('total_land')

        try:
            total_land = float(total_land)
        except ValueError:
            flash('Total land must be a number.', 'error')
            return redirect(url_for('profile'))

        if update_user_profile(g.user['id'], email, phone, full_name, farm_name, location, total_land):
            flash('Profile updated successfully!', 'success')
            # Reload user data to update g.user for the current request
            g.user = get_user_by_id(g.user['id'])
        else:
            flash('Profile update failed. Email or phone might already be in use.', 'error')

        return redirect(url_for('profile'))

    return render_template_string(
        BASE_TEMPLATE + PROFILE_CONTENT,
        title='User Profile',
        user=g.user
    )


@app.route('/contact', methods=['GET'])
@login_required
def contact():
    """Renders the contact and support page."""
    all_users = get_all_users()
    return render_template_string(
        BASE_TEMPLATE + CONTACT_CONTENT,
        title='Contact Support',
        all_users=all_users
    )


# Run initialization and the app
if __name__ == '__main__':
    init_db()
    # Note: To send actual emails, you must replace the placeholder mail credentials
    # and use an app-specific password for a service like Gmail.
    print(f"ML Model Available: {ml_model_available}")
    app.run(debug=True)