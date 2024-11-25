import streamlit as st
import paypalrestsdk
from paypalrestsdk import Payment
import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth
import json
import os

# Set up the Streamlit page configuration
st.set_page_config(
    page_title="Edu Pro - Accelerate Your Growth",
    page_icon="🚀",
    layout="wide"
)

# Initialize Firebase Admin SDK (only once)
if not firebase_admin._apps:  # Check if Firebase app is already initialized
    service_account_info = json.loads(st.secrets["firebase"]["service_account_key"])
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

# Initialize Firestore database
db = firestore.client()

# Initialize PayPal SDK
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": st.secrets["paypal"]["client_id"],
    "client_secret": st.secrets["paypal"]["client_secret"]
})


def landing_page():
    """Landing Page with a Proceed Button"""
    st.markdown("""
        <style>
            .stApp {
                background-color: #0D1117;
                color: white;
            }
            .main-container {
                text-align: center;
                margin-top: 15%;
            }
            .header-title {
                font-size: 3.5rem;
                color: #58A6FF;
            }
            .sub-title {
                font-size: 1.2rem;
                color: #8B949E;
                margin-top: 20px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="main-container">
            <h1 class="header-title">Welcome to EduPro</h1>
            <p class="sub-title">Accelerate Your Growth with AI-Powered Tools</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Get Started"):
        st.session_state["page"] = "signup_signin"
        st.experimental_rerun()


def signup_page():
    """Sign-Up and Log-In Page"""
    st.title("Sign Up or Log In")
    col1, col2 = st.columns(2)

    with col1:
        # Display image or fallback placeholder
        if os.path.exists("school.jpg"):
            st.image("school.jpg", use_container_width=True)
        else:
            st.image("https://via.placeholder.com/600x400?text=School+Image", use_container_width=True)

    with col2:
        option = st.radio("Are you a new or returning user?", ["Sign Up", "Sign In"])

        if option == "Sign Up":
            st.subheader("Register Your School")
            school_name = st.text_input("School Name")
            email = st.text_input("Admin Email")
            password = st.text_input("Password", type="password")

            if st.button("Proceed to Payment"):
                if school_name and email and password:
                    payment = Payment({
                        "intent": "sale",
                        "payer": {"payment_method": "paypal"},
                        "redirect_urls": {
                            "return_url": "http://localhost:8501/success",
                            "cancel_url": "http://localhost:8501/cancel"
                        },
                        "transactions": [{
                            "item_list": {
                                "items": [{
                                    "name": "School Pro Subscription",
                                    "sku": "subscription001",
                                    "price": "100.00",
                                    "currency": "USD",
                                    "quantity": 1
                                }]
                            },
                            "amount": {
                                "total": "100.00",
                                "currency": "USD"
                            },
                            "description": "Pro subscription for School Management Portal."
                        }]
                    })

                    if payment.create():
                        st.success("Payment created successfully!")
                        for link in payment.links:
                            if link.rel == "approval_url":
                                st.markdown(f"[Click here to pay]({link.href})")
                                st.session_state["signup_details"] = {
                                    "school_name": school_name,
                                    "email": email,
                                    "password": password,
                                }
                                break
                    else:
                        st.error(f"Error creating payment: {payment.error}")
                else:
                    st.warning("Please fill all fields.")

        elif option == "Sign In":
            st.subheader("Log In")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Log In"):
                try:
                    user = admin_auth.get_user_by_email(email)
                    school_ref = db.collection("schools").where("email", "==", email).get()
                    if school_ref:
                        school_data = school_ref[0].to_dict()
                        st.session_state["user"] = school_data
                        st.success(f"Welcome back, {school_data['name']}!")
                        st.session_state["page"] = "main_app"
                        st.experimental_rerun()
                    else:
                        st.error("School data not found.")
                except Exception as e:
                    st.error(f"Login failed: {e}")


def app_router():
    """Page Router"""
    if "page" not in st.session_state:
        st.session_state["page"] = "landing"

    if st.session_state["page"] == "landing":
        landing_page()
    elif st.session_state["page"] == "signup_signin":
        signup_page()


if __name__ == "__main__":
    app_router()
