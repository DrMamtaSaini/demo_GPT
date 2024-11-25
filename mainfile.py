import streamlit as st
import paypalrestsdk
from paypalrestsdk import Payment
import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth
import json

# Initialize Firebase Admin SDK (only once)
if not firebase_admin._apps:
    # Load service account info from Streamlit secrets
    service_account_info = json.loads(st.secrets["firebase"]["service_account_key"])
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

# Firestore database instance
db = firestore.client()

# Initialize PayPal SDK
paypalrestsdk.configure({
    "mode": "sandbox",  # Use "live" for production
    "client_id": st.secrets["paypal"]["client_id"],
    "client_secret": st.secrets["paypal"]["client_secret"]
})

# Streamlit App Config
st.set_page_config(page_title="Edu Pro", page_icon="🚀", layout="wide")

# Define app logic
def app_router():
    if "page" not in st.session_state:
        st.session_state["page"] = "landing"

    if st.session_state["page"] == "landing":
        landing_page()
    elif st.session_state["page"] == "signup_signin":
        signup_page()

def landing_page():
    st.title("Welcome to Edu Pro")
    st.write("Manage your school seamlessly with AI-powered tools.")
    if st.button("Get Started"):
        st.session_state["page"] = "signup_signin"
        st.experimental_rerun()

def signup_page():
    st.title("Sign Up or Log In")
    col1, col2 = st.columns(2)

    with col1:
        st.image("https://via.placeholder.com/400", use_container_width=True)

    with col2:
        option = st.radio("Are you a new or returning user?", ["Sign Up", "Sign In"])

        if option == "Sign Up":
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
                            "amount": {"total": "100.00", "currency": "USD"},
                            "description": "School Pro Subscription"
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
                    st.warning("Please fill in all fields.")
        elif option == "Sign In":
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Log In"):
                try:
                    user = admin_auth.get_user_by_email(email)
                    school_ref = db.collection("schools").where("email", "==", email).get()
                    if school_ref:
                        school_data = school_ref[0].to_dict()
                        st.success(f"Welcome back, {school_data['name']}!")
                        st.session_state["page"] = "main_app"
                        st.experimental_rerun()
                    else:
                        st.error("School data not found.")
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")

if __name__ == "__main__":
    app_router()
