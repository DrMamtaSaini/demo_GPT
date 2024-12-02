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


def create_order(access_token, amount="10.00", description="Pro Plan Subscription"):
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


def payment_page():
    """Main function to handle the payment process."""
    st.title("Subscribe to Edu Pro")
    st.write("Choose your subscription plan and proceed to payment.")
    
    if st.button("Subscribe Now"):
        try:
            # Step 1: Get Access Token
            access_token = get_access_token()
            
            # Step 2: Create Order
            order = create_order(access_token, amount="1.00", description="Pro Plan Subscription")
            approval_url = next(link["href"] for link in order["links"] if link["rel"] == "approve")
            order_id = order["id"]
            
            # Step 3: Redirect User to PayPal for Payment
            st.markdown(f"""
                <a href="{approval_url}" target="_blank">
                    <button style="background-color: #38BDF8; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; border: none;">
                        Proceed to PayPal
                    </button>
                </a>
            """, unsafe_allow_html=True)

            st.info("Complete the payment on the PayPal window and then return to this page.")
            
            # Step 4: Capture Payment Automatically
            if "token" in st.experimental_get_query_params():
                capture_response = capture_order(access_token, order_id)
                if capture_response.get("status") == "COMPLETED":
                    st.success("Payment Successful! Thank you for subscribing.")
                else:
                    st.error("Payment not completed. Please try again.")

        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred: {e}")


def success_page():
    """Page to display payment success."""
    st.title("Payment Successful")
    st.success("Thank you for your payment! Your subscription is now active.")
    st.markdown(f"[Return to Home]({BASE_URL})")


def cancel_page():
    """Page to handle payment cancellation."""
    st.title("Payment Cancelled")
    st.warning("The payment process was cancelled. You can try again.")
    st.markdown(f"[Return to Home]({BASE_URL})")


# Routing Logic
def app_router():
    """Route the app pages based on the query parameter."""
    page = st.experimental_get_query_params().get("page", ["main"])[0]
    if page == "success":
        success_page()
    elif page == "cancel":
        cancel_page()
    else:
        payment_page()


if __name__ == "__main__":
    app_router()
