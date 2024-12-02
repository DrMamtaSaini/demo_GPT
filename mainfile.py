# Core Imports
import streamlit as st
from streamlit_option_menu import option_menu

# Firebase Integration
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

# Utility Libraries
import hashlib
import random
from io import BytesIO
import logging

# Data Handling and Visualization
import pandas as pd
import matplotlib.pyplot as plt

# API and HTTP Requests
import requests

# AI and NLP Libraries
from transformers import pipeline
from googletrans import Translator

# Payment Gateway
import paypalrestsdk



# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page Config
st.set_page_config(page_title="Edu Pro - Accelerate Your Growth", page_icon="📚", layout="wide")

# Firebase Initialization


def initialize_firebase():
    try:
        cred = credentials.Certificate({
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
        })
        if not firebase_admin._apps:  # Prevent re-initialization
            initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Firebase initialization error: {e}")
        st.stop()


# Firebase Client
db = initialize_firebase()

# Helper Functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def export_csv(data):
    output = BytesIO()
    data.to_csv(output, index=False)
    return output.getvalue()

# Navigation Menu
selected = option_menu(
    menu_title=None,
    options=["Home", "Dashboard", "Subscriptions", "Reports", "Help"],
    icons=["house", "bar-chart", "card-checklist", "file-text", "question-circle"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
)

# Route Pages Based on Selection
def app_router():
    if selected == "Home":
        landing_page()
    elif selected == "Dashboard":
        free_dashboard()
    elif selected == "Subscriptions":
        subscription_page()
    elif selected == "Reports":
        generate_reports_page()
    elif selected == "Help":
        help_center()


def landing_page():
    st.markdown("""
        <style>
            .main-container {text-align: center; padding-top: 10%;}
            .header-title {font-size: 3.5rem; color: #38BDF8; font-weight: bold; margin-bottom: 20px;}
            .sub-title {font-size: 1.2rem; color: #6B7280; margin-bottom: 30px;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="main-container">
            <h1 class="header-title">Accelerate Your Growth with AI</h1>
            <p class="sub-title">Unlock your school's potential with smart AI tools.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Get Started"):
            st.session_state.page = "signup_signin"


def subscription_page():
    st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #38BDF8;">Subscription Plans</h1>
            <p style="color: #6B7280;">Choose a plan that fits your school’s needs.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])

    # Free Plan
    with col1:
        st.markdown("""
            <div class="pricing-card">
                <h2>Free Plan</h2>
                <p class="price">$0/month</p>
                <ul>
                    <li>Grading</li>
                    <li>Performance Graph</li>
                    <li>10,000 API Tokens/Month</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    # Pro Plan
    with col2:
        st.markdown("""
            <div class="pricing-card">
                <h2>Pro Plan</h2>
                <p class="price">$20/month</p>
                <ul>
                    <li>Advanced Analytics</li>
                    <li>7M API Tokens/Month</li>
                </ul>
        """, unsafe_allow_html=True)
        if st.button("Subscribe to Pro Plan"):
            st.session_state["payment_amount"] = "20.00"
            st.session_state["payment_description"] = "Pro Plan Subscription for Edu Pro"
            st.session_state.page = "payment_page"

    # Enterprise Plan
    with col3:
        st.markdown("""
            <div class="pricing-card">
                <h2>Enterprise Plan</h2>
                <p class="price">$100/month</p>
                <ul>
                    <li>Dedicated Support</li>
                    <li>Unlimited API Tokens</li>
                </ul>
        """, unsafe_allow_html=True)
        if st.button("Subscribe to Enterprise Plan"):
            st.session_state["payment_amount"] = "100.00"
            st.session_state["payment_description"] = "Enterprise Plan Subscription for Edu Pro"
            st.session_state.page = "payment_page"


def free_dashboard():
    st.title("Dashboard")
    st.write("Welcome to the Edu Pro Dashboard. Explore available modules below.")
    
    modules = [
        {"name": "Grading", "description": "Evaluate and grade student performance"},
        {"name": "Performance Graph", "description": "Visualize student progress"},
        {"name": "Generate Question Paper", "description": "Create question papers easily"},
    ]

    for module in modules:
        st.subheader(module["name"])
        st.write(module["description"])
        if st.button(f"Explore {module['name']}"):
            st.session_state.page = module["name"]


def help_center():
    st.title("Help Center")
    st.markdown("""
        - **FAQs:** Common questions and answers.
        - **Support:** Contact us at [support@edupro.com](mailto:support@edupro.com).
    """)


from transformers import pipeline

# Initialize Chatbot
def chatbot():
    st.title("Edu Pro Assistant")
    st.write("Ask me anything about the platform!")

    # Load a pre-trained model for conversational AI (example with Hugging Face)
    chatbot = pipeline("conversational", model="microsoft/DialoGPT-medium")

    user_input = st.text_input("Your question:")
    if st.button("Send"):
        if user_input:
            response = chatbot(user_input)
            st.write("Bot:", response)
        else:
            st.warning("Please enter a question.")


def notifications():
    st.markdown("""
        <style>
            .notification-banner {
                background-color: #FFFAF0;
                border-left: 4px solid #FFA500;
                padding: 10px;
                margin-bottom: 20px;
            }
        </style>
        <div class="notification-banner">
            <p><strong>📢 New Feature:</strong> Chatbot for instant support is now live!</p>
        </div>
    """, unsafe_allow_html=True)


import matplotlib.pyplot as plt

def analytics_dashboard():
    st.title("Advanced Analytics")
    st.write("Visual insights into your usage and performance.")

    # Example: Token usage bar chart
    data = {"Month": ["January", "February", "March"], "Tokens Used": [500000, 700000, 600000]}
    df = pd.DataFrame(data)

    st.bar_chart(df.set_index("Month"))

    # Example: Subscription growth pie chart
    labels = ["Free", "Pro", "Enterprise"]
    sizes = [60, 30, 10]
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    ax.axis("equal")
    st.pyplot(fig)


from googletrans import Translator

def translate_page(content, target_language="es"):
    translator = Translator()
    translation = translator.translate(content, dest=target_language)
    return translation.text

# Example Usage
st.write(translate_page("Welcome to Edu Pro", target_language="es"))


def payment_history():
    st.title("Payment History")
    payments = [
        {"Date": "2024-01-01", "Amount": "$20", "Plan": "Pro"},
        {"Date": "2024-02-01", "Amount": "$100", "Plan": "Enterprise"}
    ]
    df = pd.DataFrame(payments)
    st.table(df)

    if st.button("Download Invoice"):
        csv = export_csv(df)
        st.download_button(label="Download Invoice", data=csv, file_name="payment_history.csv")




def profile_management():
    st.title("My Profile")
    user_data = {"Name": "John Doe", "Email": "john@example.com", "Plan": "Pro"}

    st.json(user_data)
    if st.button("Update Profile"):
        st.success("Profile updated successfully!")


def logout():
    st.session_state.clear()
    st.success("You have been logged out!")
    st.session_state.page = "landing"


from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_test_email():
    try:
        sg = SendGridAPIClient(st.secrets["sendgrid"]["api_key"])
        message = Mail(
            from_email="test@example.com",
            to_emails="recipient@example.com",
            subject="Test Email",
            plain_text_content="This is a test email."
        )
        response = sg.send(message)
        st.write(f"Email sent: {response.status_code}")
    except Exception as e:
        st.error(f"SendGrid error: {e}")

import requests

def test_paypal_credentials():
    url = f"{st.secrets['paypal']['api_url']}/v1/oauth2/token"
    try:
        response = requests.post(
            url,
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
            data={"grant_type": "client_credentials"},
            auth=(st.secrets["paypal"]["client_id"], st.secrets["paypal"]["client_secret"]),
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        st.write(f"PayPal Access Token: {token}")
    except Exception as e:
        st.error(f"PayPal credential test failed: {e}")



def app_router():
    notifications()  # Display global notifications
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    if st.session_state.page == "landing":
        landing_page()
    elif st.session_state.page == "signup_signin":
        signup_with_captcha()
    elif st.session_state.page == "dashboard":
        free_dashboard()
    elif st.session_state.page == "analytics":
        analytics_dashboard()
    elif st.session_state.page == "subscriptions":
        subscription_page()
    elif st.session_state.page == "chatbot":
        chatbot()
    elif st.session_state.page == "profile":
        profile_management()
    elif st.session_state.page == "payments":
        payment_history()
    elif st.session_state.page == "logout":
        logout()

