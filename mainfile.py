import streamlit as st
import requests

# PayPal Sandbox Credentials
PAYPAL_CLIENT_ID = st.secrets["paypal"]["client_id"]
PAYPAL_SECRET = st.secrets["paypal"]["client_secret"]
PAYPAL_API_URL = "https://api-m.sandbox.paypal.com"  # PayPal sandbox URL for testing

# URLs for success and cancel actions
BASE_URL = "https://teachersgpt.streamlit.app"  # Replace with your Streamlit app URL
SUCCESS_URL = f"{BASE_URL}?page=success"
CANCEL_URL = f"{BASE_URL}?page=cancel"

def get_access_token():
    """Get PayPal Access Token."""
    url = f"{PAYPAL_API_URL}/v1/oauth2/token"
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en_US",
    }
    data = {"grant_type": "client_credentials"}
    response = requests.post(url, headers=headers, data=data, auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET))
    response.raise_for_status()
    return response.json()["access_token"]

def create_order(access_token):
    """Create PayPal Order."""
    url = f"{PAYPAL_API_URL}/v2/checkout/orders"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": "10.00",  # Test amount
                },
                "description": "Test Payment",
            }
        ],
        "application_context": {
            "return_url": SUCCESS_URL,
            "cancel_url": CANCEL_URL,
        },
    }
    response = requests.post(url, headers=headers, json=order_data)
    response.raise_for_status()
    return response.json()

def capture_order(access_token, order_id):
    """Capture PayPal Order."""
    url = f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    """Main function to handle Streamlit UI and PayPal integration."""
    # Query parameters for handling success/cancel
    query_params = st.experimental_get_query_params()
    page = query_params.get("page", ["main"])[0]

    # Page routing
    if page == "success":
        st.title("Payment Successful")
        st.success("Your payment was completed successfully!")
        return
    elif page == "cancel":
        st.title("Payment Cancelled")
        st.warning("The payment was cancelled. Please try again.")
        return

    st.title("PayPal Payment Testing")

    # Step 1: Get Access Token
    if "access_token" not in st.session_state:
        if st.button("Get Access Token"):
            try:
                access_token = get_access_token()
                st.session_state.access_token = access_token
                st.success("Access Token Retrieved!")
            except requests.exceptions.RequestException as e:
                st.error(f"Error getting access token: {e}")

    # Step 2: Create Order
    if "access_token" in st.session_state:
        if "order" not in st.session_state:
            if st.button("Create PayPal Order"):
                try:
                    order = create_order(st.session_state.access_token)
                    st.session_state.order = order
                    approval_url = [link["href"] for link in order["links"] if link["rel"] == "approve"][0]
                    st.success("Order Created!")
                    st.write("Order Details:", order)
                    st.markdown(f"[Click here to approve payment]({approval_url})")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error creating order: {e}")

    # Step 3: Capture Payment
    if "order" in st.session_state:
        st.success("Payment Approved! You can now proceed to capture the payment.")
        order_id = st.session_state.order["id"]
        if st.button("Capture Payment"):
            try:
                capture_response = capture_order(st.session_state.access_token, order_id)
                st.success("Payment Captured Successfully!")
                # Display detailed capture response
                st.json(capture_response)

                # Optional: Extract specific details for better readability
                payer_name = capture_response["payer"]["name"]["given_name"] + " " + capture_response["payer"]["name"]["surname"]
                payer_email = capture_response["payer"]["email_address"]
                amount = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
                currency = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["currency_code"]

                # Display extracted details
                st.write(f"**Payer Name:** {payer_name}")
                st.write(f"**Payer Email:** {payer_email}")
                st.write(f"**Amount Paid:** {amount} {currency}")

            except requests.exceptions.RequestException as e:
                st.error(f"Error capturing payment: {e}")

if __name__ == "__main__":
    main()
"  this is the working code, analyse this and update my app code "from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import streamlit as st
import firebase_admin
import json
from firebase_admin import credentials, firestore,initialize_app
import random
import hashlib
import requests
import paypalrestsdk


# PayPal Credentials
PAYPAL_CLIENT_ID = st.secrets["paypal"]["client_id"]
PAYPAL_SECRET = st.secrets["paypal"]["client_secret"]
PAYPAL_API_URL = st.secrets["paypal"]["api_url"]

# Set up PayPal API credentials using sandbox


# Initialize Firebase Admin SDK
st.set_page_config(page_title="Edu Pro - Accelerate Your Growth", layout="wide")


def initialize_firebase():
    try:
        if not firebase_admin._apps:  # Avoid multiple Firebase initializations
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
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Failed to initialize Firebase: {e}")
        st.stop()

# Firebase Client
db = initialize_firebase()


# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Email Validation
def is_valid_email(email):
    """Validate email format using regex."""
    import re
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None


# Function to send verification email
def send_verification_email(recipient_email, verification_code):
    try:
        api_key = st.secrets["sendgrid"]["api_key"]
        from_email = "contact@digitaleralink.com"  # Your verified SendGrid sender email
        subject = "Email Verification - Digital Era Link"
        content = f"Your verification code is: {verification_code}"

        sg = SendGridAPIClient(api_key)
        message = Mail(
            from_email=from_email,
            to_emails=recipient_email,
            subject=subject,
            plain_text_content=content,
        )
        response = sg.send(message)
        if response.status_code == 202:
            return True
        else:
            st.error(f"Failed to send verification email. Status code: {response.status_code}")
            return False
    except KeyError as e:
        st.error(f"Secrets configuration issue: {e}")
        return False
    except Exception as e:
        st.error(f"An error occurred while sending the verification email: {e}")
        return False


# Main Function for Sign-Up/Sign-In
import uuid  # For generating unique IDs

# Main Function for Sign-Up/Sign-In
# Main Function for Sign-Up/Sign-In
def signup_signin_page():
    if "signup_stage" not in st.session_state:
        st.session_state.signup_stage = "form"
    if "email_sent" not in st.session_state:
        st.session_state.email_sent = False
    if "signup_data" not in st.session_state:
        st.session_state.signup_data = None

    st.title("Sign Up / Sign In")
    option = st.radio("Choose an option:", ["Sign Up", "Sign In"], index=0, key="signup_signin_radio")

    if option == "Sign Up":
        if st.session_state.signup_stage == "form":
            st.subheader("Register Your School")
            school_name = st.text_input("School Name", key="signup_school_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Create Password", type="password", key="signup_password")

            if st.button("Sign Up") and not st.session_state.email_sent:
                if not school_name or not email or not password:
                    st.error("Please fill in all fields.")
                elif not is_valid_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    existing_user = db.collection("schools").where("email", "==", email).stream()
                    if any(existing_user):
                        st.error("This email is already registered. Please use another email.")
                    else:
                        verification_code = random.randint(100000, 999999)
                        st.session_state.verification_code = verification_code
                        if send_verification_email(email, verification_code):
                            unique_school_id = str(uuid.uuid4())  # Generate a unique ID for the school
                            st.session_state.signup_data = {
                                "school_id": unique_school_id,
                                "school_name": school_name,
                                "email": email,
                                "password": hash_password(password),
                                "subscription_status": "free",  # Default subscription status
                                "created_on": firestore.SERVER_TIMESTAMP,  # Firestore timestamp
                                "activated_on": None,  # To be updated upon activation
                            }
                            st.session_state.signup_stage = "verify"
                            st.session_state.email_sent = True
                            st.success("Verification email sent! Enter the code below.")

        if st.session_state.signup_stage == "verify":
            st.subheader("Verify Your Email")
            verification_code_input = st.text_input("Enter Verification Code", key="verification_code_input")

            if st.button("Verify"):
                if verification_code_input.isdigit() and int(verification_code_input) == st.session_state.verification_code:
                    signup_data = st.session_state.signup_data
                    school_name = signup_data["school_name"]  # Ensure this is defined
                    school_id = str(uuid.uuid4())  # Generate a unique school ID

                    # Save the school data to the database
                    db.collection("schools").add({
                        "school_id": school_id,
                        "school_name": signup_data["school_name"],
                        "email": signup_data["email"],
                        "password": signup_data["password"],
                        "subscription_status": "free",
                        "created_on": firestore.SERVER_TIMESTAMP,
                        "activated_on": None,
                    })

                    # Assign an API key
                    available_api_key = db.collection("api_keys").where("assigned", "==", False).limit(1).stream()
                    for key in available_api_key:
                        db.collection("api_keys").document(key.id).update({
                            "assigned": True,
                            "assigned_on": firestore.SERVER_TIMESTAMP,
                            "school_id": school_id
                        })
                        st.success(f"API key assigned to {school_name}.")
                        break
                    else:
                        st.error("No API keys available. Please contact support.")

                    st.success(f"Account created successfully for {school_name}!")
                    st.session_state.signup_stage = "form"
                    st.session_state.email_sent = False
                else:
                    st.error("Invalid verification code. Please try again.")


    elif option == "Sign In":
        st.subheader("Sign In to Your Account")
        email = st.text_input("Sign-In Email", key="signin_email")
        password = st.text_input("Sign-In Password", type="password", key="signin_password")

        if st.button("Sign In"):
            if email and password:
                hashed_password = hash_password(password)
                users = db.collection("schools").where("email", "==", email).where("password", "==", hashed_password).stream()
                if any(users):
                    st.success(f"Welcome back, {email}!")
                    st.session_state.page = "subscription_page"
                else:
                    st.error("Invalid credentials.")
            else:
                st.error("Please fill in all fields.")

# Landing Page
def landing_page():
    st.markdown("""
        <style>
            .stApp {background-color: #111827; color: white; font-family: 'Arial', sans-serif;}
            .main-container {text-align: center; padding-top: 10%;} /* Reduced padding */
            .header-title {font-size: 3.5rem; color: #38BDF8; font-weight: bold; margin-bottom: 20px;}
            .sub-title {font-size: 1.2rem; color: #6B7280; margin-bottom: 30px;}
            .stButton>button {
                background-color: #38BDF8; color: white; font-size: 1.2rem; font-weight: bold; padding: 12px 30px;
                border-radius: 5px; border: none; cursor: pointer; transition: 0.3s; margin-top: 20px;
            }
            .stButton>button:hover {background-color: #1E90FF;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="main-container">
            <h1 class="header-title">Accelerate Your Growth with Advanced AI</h1>
            <p class="sub-title">Experience the power of AI to enhance your school’s performance.</p>
        </div>
    """, unsafe_allow_html=True)

    # Centered "Get Started" button
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Get Started", key="get_started"):
            
            st.session_state.page = "signup_signin"

def subscription_page():
    """
    Subscription page to display pricing plans and manage navigation to payment pages.
    """
    st.markdown("""
        <style>
            .pricing-container {
                display: flex;
                justify-content: space-around;
                gap: 20px;
                margin-top: 30px;
            }
            .pricing-card {
                background-color: #1E293B;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
                text-align: center;
                color: white;
                width: 300px;
            }
            .pricing-card h2 {
                font-size: 1.5rem;
                color: #38BDF8;
                margin-bottom: 10px;
            }
            .pricing-card .price {
                font-size: 2rem;
                color: #38BDF8;
                margin-bottom: 10px;
            }
            .pricing-card ul {
                list-style: none;
                padding: 0;
                margin-bottom: 20px;
                color: #E2E8F0;
            }
            .pricing-card li {
                margin: 10px 0;
            }
            .stButton>button {
                background-color: #38BDF8;
                color: white;
                font-size: 1rem;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                border: none;
                transition: 0.3s;
            }
            .stButton>button:hover {
                background-color: #1E90FF;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #38BDF8;">Subscription Plans</h1>
            <p style="color: #6B7280;">Select the plan that works best for your school.</p>
        </div>
    """, unsafe_allow_html=True)

    # Define pricing plans
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
                    <li>Generate Question Paper</li>
                    <li>10,000 API tokens per school/month</li>
                </ul>
                <button disabled style="cursor: not-allowed; background-color: grey;">Current Plan</button>
            </div>
        """, unsafe_allow_html=True)

    # Pro Plan
    with col2:
        st.markdown("""
            <div class="pricing-card">
                <h2>Pro Plan</h2>
                <p class="price">$1/month</p>
                <ul>
                    <li>Access to 4 Modules</li>
                    <li>7M API Tokens/Month</li>
                    <li>800 Student Capacity</li>
                    <li>Priority Support</li>
                </ul>
        """, unsafe_allow_html=True)
        if st.button("Subscribe to Pro Plan"):
            # Set Pro Plan details in session state and redirect
            st.session_state["payment_amount"] = "1.00"
            st.session_state["payment_description"] = "Pro Plan Subscription for Edu Pro"
            st.session_state.page = "payment_page"

    # Enterprise Plan
    with col3:
        st.markdown("""
            <div class="pricing-card">
                <h2>Enterprise Plan</h2>
                <p class="price">$750/month</p>
                <ul>
                    <li>Access to All Modules</li>
                    <li>11M API Tokens/Month</li>
                    <li>1000 Student Capacity</li>
                    <li>Dedicated Support</li>
                </ul>
        """, unsafe_allow_html=True)
        if st.button("Subscribe to Enterprise Plan"):
            # Set Enterprise Plan details in session state and redirect
            st.session_state["payment_amount"] = "750.00"
            st.session_state["payment_description"] = "Enterprise Plan Subscription for Edu Pro"
            st.session_state.page = "payment_page"

### Updated payment_page


def payment_page():
    """
    Display the payment page for Pro or Enterprise plan.
    """
    if "payment_amount" not in st.session_state or "payment_description" not in st.session_state:
        st.error("Payment details are missing. Please try again.")
        return

    amount = st.session_state["payment_amount"]
    description = st.session_state["payment_description"]

    st.title("Payment Page")
    st.write(f"Subscribe to the {description} for ${amount}/month.")

    # Generate PayPal access token
    access_token = get_paypal_access_token()

    # Create a PayPal order
    order = create_paypal_order(access_token, amount, description)
    approval_url = [link["href"] for link in order["links"] if link["rel"] == "approve"][0]

    # Redirect user to PayPal for payment
    st.markdown(f"""
        <a href="{approval_url}" target="_blank">
            <button style="background-color: #38BDF8; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; border: none;">
                Pay Now with PayPal
            </button>
        </a>
    """, unsafe_allow_html=True)


def get_paypal_access_token():
    """Generate and return PayPal Access Token."""
    url = f"{PAYPAL_API_URL}/v1/oauth2/token"
    try:
        response = requests.post(
            url,
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
            },
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to generate PayPal access token: {e}")
        st.stop()



def create_paypal_order(access_token, amount, description):
    """Create a PayPal order for the specified amount and description."""
    url = f"{PAYPAL_API_URL}/v2/checkout/orders"
    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {"currency_code": "USD", "value": amount},
                        "description": description,
                    }
                ],
                "application_context": {
                    "return_url": f"{BASE_URL}?page=success",
                    "cancel_url": f"{BASE_URL}?page=cancel",
                },
            },
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to create PayPal order: {e}")
        st.stop()



def capture_paypal_order(access_token, order_id):
    """Capture the specified PayPal order."""
    url = f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture"
    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to capture PayPal order: {e}")
        st.stop()






def success_page():
    """Handle successful payment."""
    st.title("Payment Successful")

    # Get Query Parameters
    query_params = st.experimental_get_query_params()
    order_id = query_params.get("token", [""])[0]

    if not order_id:
        st.error("Order ID is missing from the redirect URL.")
        return

    # Generate Access Token and Capture Payment
    access_token = get_paypal_access_token()
    capture_response = capture_paypal_order(access_token, order_id)

    if capture_response and capture_response.get("status") == "COMPLETED":
        st.success("Your payment was successfully completed!")
        transaction_id = capture_response["id"]
        payer_email = capture_response["payer"]["email_address"]
        amount = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
        currency = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["currency_code"]

        st.write(f"**Transaction ID:** {transaction_id}")
        st.write(f"**Payer Email:** {payer_email}")
        st.write(f"**Amount Paid:** {amount} {currency}")
    else:
        st.error("Payment capture failed. Please contact support.")



def cancel_page():
    """Handle canceled payment."""
    st.title("Payment Canceled")
    st.warning("You have canceled the payment. Please try again or contact support if you need help.")
    if st.button("Back to Subscription Page"):
        st.session_state.page = "subscription_page"




def test_paypal_payment():
    """
    Test PayPal payment by generating an access token and creating an order.
    """
    st.title("Test PayPal Payment")

    # Step 1: Generate Access Token
    if st.button("Generate Access Token"):
        try:
            access_token = get_paypal_access_token()
            st.success("Access Token Generated Successfully!")
            st.session_state["access_token"] = access_token  # Save token for later use
        except Exception as e:
            st.error(f"Failed to generate access token: {e}")
            return

    # Step 2: Create PayPal Order
    if "access_token" in st.session_state:  # Ensure token exists before proceeding
        if st.button("Create PayPal Order"):
            try:
                order_response = create_paypal_order(st.session_state["access_token"])
                if order_response:
                    st.success("PayPal Order Created Successfully!")
                    st.write("Order Response:", order_response)

                    # Extract Approval URL
                    approval_url = [link["href"] for link in order_response["links"] if link["rel"] == "approve"][0]
                    st.markdown(f"[Pay Now]({approval_url})")  # Display PayPal approval link
            except Exception as e:
                st.error(f"Failed to create PayPal order: {e}")
    else:
        st.warning("Generate an access token first.")



# Step 3: Display Payment Page
def payment_page():
    """Display the payment page for Pro or Enterprise plans."""
    if "payment_amount" not in st.session_state or "payment_description" not in st.session_state:
        st.error("Payment details are missing. Please try again.")
        return

    amount = st.session_state["payment_amount"]
    description = st.session_state["payment_description"]

    st.title("Payment Page")
    st.write(f"You're subscribing to **{description}** for **${amount}/month**.")
    
    try:
        # Generate PayPal Access Token
        access_token = get_paypal_access_token()
        if not access_token:
            st.error("Failed to generate PayPal access token.")
            return

        # Create PayPal Order
        order = create_paypal_order(access_token, amount, description)
        if not order:
            st.error("Failed to create PayPal order. Please try again.")
            return

        # Extract Approval URL
        approval_url = next((link["href"] for link in order["links"] if link["rel"] == "approve"), None)
        if not approval_url:
            st.error("Approval URL not found in PayPal order response.")
            return

        # Display PayPal Payment Button
        st.markdown(f"""
            <div style="text-align: center; margin-top: 30px;">
                <a href="{approval_url}" target="_blank">
                    <button style="background-color: #38BDF8; color: white; font-size: 1.2rem; padding: 10px 30px; border-radius: 5px; cursor: pointer; border: none;">
                        Pay Now with PayPal
                    </button>
                </a>
            </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"An error occurred during payment processing: {e}")



# Step 4: Capture PayPal Order
def capture_paypal_order(access_token, order_id):
    url = f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        return response.json()
    else:
        st.error(f"Failed to capture PayPal order: {response.text}")
        st.stop()




def create_payment():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": "http://localhost:5000/payment/execute",
            "cancel_url": "http://localhost:5000/payment/cancel"
        },
        "transactions": [{
            "amount": {
                "total": "1.00",
                "currency": "USD"
            },
            "description": "Pro Plan Subscription"
        }]
    })

    if payment.create():
        print("Payment created successfully")
        for link in payment.links:
            if link.rel == "approval_url":
                approval_url = link.href
                print(f"Redirect user to: {approval_url}")
                return approval_url
    else:
        print(payment.error)
        return None
def execute_payment(payment_id, payer_id):
    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        print("Payment executed successfully")
    else:
        print(payment.error)


def fetch_paypal_order(access_token, order_id):
    url = f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        order_details = response.json()
        st.write("Order Details Response:", order_details)  # Debugging log
        return order_details
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching PayPal order: {e}")
        st.write("Response Text:", response.text if response else "No response.")
        return None








# Main App Page
def main_app():
    st.title("Welcome to Edu Pro")
    st.write("This is the main app interface.")
def free_dashboard():
    """
    Free dashboard displaying modules in rows of three, with centered buttons styled as 'Explore.'
    """

    # CSS for styling
    st.markdown("""
        <style>
            .stApp {background-color: #111827; font-family: 'Arial', sans-serif; color: white;}
            .dashboard-header {text-align: center; margin-bottom: 30px;}
            .module-card {
                background-color: #1E293B; padding: 20px; border-radius: 10px;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); width: 250px; text-align: center;
                border: 2px solid transparent; transition: 0.3s; height: 200px; position: relative;
            }
            .module-card:hover {border: 2px solid #38BDF8; transform: scale(1.05);}
            .module-card h2 {font-size: 1.2rem; color: #38BDF8; margin-bottom: 10px;}
            .module-card p {color: #E2E8F0; margin-bottom: 50px;}
            .stButton>button {
                background-color: #38BDF8; color: white; font-size: 0.9rem; font-weight: bold;
                padding: 10px 20px; border-radius: 5px; border: none; cursor: pointer;
                transition: 0.3s;
                margin-top: 10px;
                margin-left: 8%; /* Adjusted to center the buttons properly */
                position: relative;
            }
            .stButton>button:hover {background-color: #1E90FF;}
            .logout-container {margin-top: 50px; text-align: center;}
            .logout-button {background-color: #FF4C4C; color: white; font-size: 1rem; font-weight: bold;
                padding: 10px 30px; border-radius: 5px; border: none; cursor: pointer;}
            .logout-button:hover {background-color: #FF3333;}
        </style>
    """, unsafe_allow_html=True)

    # Dashboard header
    st.markdown("""
        <div class="dashboard-header">
            <h1 style="color: #38BDF8;">Free Dashboard</h1>
            <p style="color: #6B7280;">Explore the available modules and upgrade for full access</p>
        </div>
    """, unsafe_allow_html=True)

    # Define modules
    modules = [
        {"name": "Grading", "description": "Evaluate and grade student performance", "free": True},
        {"name": "Performance Graph", "description": "Analyze student progress with visual insights", "free": True},
        {"name": "Generate Question Paper", "description": "Create customized question papers effortlessly", "free": True},
        {"name": "Generate Sample Paper", "description": "Generate professional sample papers", "free": False},
        {"name": "Create Assignments", "description": "Create assignments with ease", "free": False},
        {"name": "Create Interactive Quizzes", "description": "Create interactive quizzes", "free": False},
    ]

    # Display modules in rows of three
    for i in range(0, len(modules), 3):
        cols = st.columns(3)
        for idx, module in enumerate(modules[i:i + 3]):
            with cols[idx]:
                st.markdown(f"""
                    <div class="module-card">
                        <h2>{module['name']}</h2>
                        <p>{module['description']}</p>
                    </div>
                """, unsafe_allow_html=True)

                # Add button at the center of each card
                if module["free"]:
                    if st.button(f"Explore {module['name']}", key=module["name"]):
                        st.session_state.page = module["name"]
                else:
                    if st.button(module["name"], key=f"locked_{module['name']}"):
                        st.warning(f"{module['name']} is available in the Pro version. Please upgrade to access it.")

    # Locked Modules Header
    st.markdown("""
        <div class="dashboard-header">
            <h2 style="color: #38BDF8;">Pro Modules</h2>
        </div>
    """, unsafe_allow_html=True)

    # Add a logout button at the bottom center
    st.markdown("""
        <div class="logout-container">
            <button class="logout-button" onclick="alert('You have been logged out!'); window.location.reload();">
                Logout
            </button>
        </div>
    """, unsafe_allow_html=True)


# Define the functions for the module pages
def grading():
    st.title("Grading Module")
    st.write("Welcome to the Grading functionality. This is where you can evaluate and grade student performance.")
    if st.button("Back to Dashboard"):
        st.session_state.page = "free_dashboard"


def performance_graph():
    st.title("Performance Graph Module")
    st.write("This is the Performance Graph page where you can analyze student progress.")
    if st.button("Back to Dashboard"):
        st.session_state.page = "free_dashboard"


def generate_question_paper():
    st.title("Generate Question Paper Module")
    st.write("Here, you can create customized question papers effortlessly.")
    if st.button("Back to Dashboard"):
        st.session_state.page = "free_dashboard"


def logout():
    st.session_state.clear()
    st.session_state.page = "signup_signin"


# Subscription Management Page for Simple Plan Upgrades
def subscription_management():
    """
    Simple subscription management function to upgrade plans.
    """
    st.subheader("Subscription Management")
    st.write("Upgrade your plan to access more features.")

    # Display current plan and upgrade options
    school_id = st.session_state.get("school_id")
    if not school_id:
        st.error("School details not found. Please log in again.")
        return

    school_ref = db.collection("schools").document(school_id).get()
    if not school_ref.exists:
        st.error("School not found in the database.")
        return

    school_data = school_ref.to_dict()
    current_plan = school_data.get("subscription_status", "Free")

    st.write(f"**Current Plan:** {current_plan}")

    # Upgrade to Pro Plan
    if current_plan == "Free":
        if st.button("Upgrade to Pro Plan for $500/month"):
            st.session_state.page = "payment_page"
    elif current_plan == "Pro":
        st.write("You are already on the Pro plan.")
        if st.button("Upgrade to Enterprise Plan for $750/month"):
            st.session_state.page = "payment_page"
    elif current_plan == "Enterprise":
        st.info("You are already on the highest plan.")


# Token Usage Analytics
def display_token_analytics():
        st.subheader("Token Usage Analytics")
        st.markdown("""
            <style>
                .analytics-container {padding: 20px; background-color: #1E293B; border-radius: 10px;}
                .analytics-container p {color: #E2E8F0;}
                .stButton>button {background-color: #38BDF8; color: white; padding: 10px 20px; border-radius: 5px; font-size: 1rem;}
                .stButton>button:hover {background-color: #1E90FF;}
            </style>
        """, unsafe_allow_html=True)
        st.markdown("""
            <div class="analytics-container">
                <p><strong>Total Tokens Allocated:</strong> 7,000,000</p>
                <p><strong>Tokens Used This Month:</strong> 3,200,000</p>
                <p><strong>Remaining Tokens:</strong> 3,800,000</p>
            </div>
        """, unsafe_allow_html=True)
        st.bar_chart({"Tokens Used (Millions)": [3.2, 3.8], "Total Tokens (Millions)": [7.0, 7.0]})
        if st.button("Download Token Usage Report"):
            st.write("Downloading report...")


def free_version_dashboard():
    """
    Main application function that controls the display and functionality of each app section.
    Provides error handling and UI feedback for each module.
    """
    try:
        # Sidebar with improved styling for module selection
        st.sidebar.title("Navigation")
        
        # Add PayPal test button
        if st.sidebar.button("Test PayPal Payment"):
            st.session_state.page = "test_paypal_payment"

        # Sidebar module selection
        task = st.sidebar.selectbox(
            "Select a Module",
            [
                "Home",
                "Educational Content Creation",
                "Student Assessment & Evaluation",
                "Curriculum & Alignment",
                "Advanced Editing & Text Generation",
                "Subscription Management",
                "Token Usage Analytics"
            ]
        )

        # Content based on selected module
        if task == "Home":
            free_dashboard()

        elif task == "Educational Content Creation":
            subtask = st.sidebar.radio("Select a Submodule", [
                "Generate Question Paper",
                "Generate Sample Paper",
                "Generate Assignment",
                "Generate Quiz",
                "Generate Lesson Plans",
                "Generate Image-Based Questions",
                "Generate Paragraph Based Question",
                "Generate Classroom Discussion Prompter"
            ])
            if subtask == "Generate Question Paper":
                st.title("Question Paper Generator")

        elif task == "Student Assessment & Evaluation":
            subtask = st.sidebar.radio("Select a Submodule", [
                "Student Assessment Assistant",
                "Generate Answer Sheets",
                "Marking Scheme Generator",
                "Analyze Reports",
                "Grading",
                "Performance Graph"
            ])
            if subtask == "Student Assessment Assistant":
                st.title("Student Assessment Assistant")

        elif task == "Curriculum & Alignment":
            subtask = st.sidebar.radio("Select a Submodule", [
                "Curriculum Generator",
                "Alignment Checker"
            ])
            if subtask == "Curriculum Generator":
                st.title("Curriculum Generator")

        elif task == "Advanced Editing & Text Generation":
            subtask = st.sidebar.radio("Select a Submodule", [
                "Text Generation",
                "Advanced Editing"
            ])
            if subtask == "Text Generation":
                st.title("Text Generator")

        elif task == "Subscription Management":
            subscription_management()

        elif task == "Token Usage Analytics":
            display_token_analytics()

    except KeyError as e:
        st.error(f"Configuration error: {e}. Please log in again.")
    except Exception as e:
        st.error(f"An unexpected error occurred in the main app: {e}")

        
#if st.button("Logout"):
     #   logout()


# App Router
def app_router():
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    if st.session_state.page == "landing":
        landing_page()
    elif st.session_state.page == "subscription_page":
        subscription_page()
    elif st.session_state.page == "signup_signin":
        signup_signin_page()
    elif st.session_state.page == "free_dashboard":
        free_dashboard()
    elif st.session_state.page == "free version dashboard":
        free_version_dashboard()
    elif st.session_state.page == "payment_page":
        payment_page()
    elif st.session_state.page == "success":
        success_page()
    elif st.session_state.page == "cancel":
        cancel_page()
    elif st.session_state.page == "test_paypal_payment":
        test_paypal_payment()
    elif st.session_state.page == "grading":
        grading()
    elif st.session_state.page == "performance_graph":
        performance_graph()
    elif st.session_state.page == "generate_question_paper":
        generate_question_paper()
    elif st.session_state.page == "main_app":
        main_app()


if __name__ == "__main__":
    app_router()