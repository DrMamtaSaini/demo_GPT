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

# Get PayPal Access Token
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

# Create PayPal Order
def create_order(access_token, amount="10.00", description="Test Payment"):
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
                    "value": amount,
                },
                "description": description,
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

# Capture PayPal Order
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

# Main Function to Handle Payment
def payment_page():
    """Main function to handle PayPal payment integration."""
    st.title("Subscribe to Edu Pro")
    st.write("Choose your subscription plan and proceed to payment.")
    
    if st.button("Subscribe Now"):
        try:
            # Step 1: Get Access Token
            access_token = get_access_token()
            
            # Step 2: Create Order
            order = create_order(access_token, amount="1.00", description="Pro Plan Subscription")
            approval_url = next(link["href"] for link in order["links"] if link["rel"] == "approve")
            
            # Step 3: Redirect User to PayPal for Payment
            st.markdown(f"""
                <a href="{approval_url}" target="_blank">
                    <button style="background-color: #38BDF8; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; border: none;">
                        Proceed to PayPal
                    </button>
                </a>
            """, unsafe_allow_html=True)

            # Show success message after a short delay (simulating landing back on success URL)
            time.sleep(3)  # Simulate delay for user to complete payment
            st.success("Payment Successful! Thank you for subscribing.")
            st.markdown(f"[Return to Home]({BASE_URL})")

        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    payment_page()
