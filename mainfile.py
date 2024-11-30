import streamlit as st
import requests

PAYPAL_CLIENT_ID = st.secrets["paypal"]["client_id"]
PAYPAL_SECRET = st.secrets["paypal"]["client_secret"]

PAYPAL_API_URL = "https://api-m.sandbox.paypal.com"  # Use the sandbox URL for testing

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
            "return_url": "https://teachersgpt.streamlit.app?status=success",
            "cancel_url": "https://teachersgpt.streamlit.app?status=cancel",
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

# Streamlit UI
def main():
    st.title("PayPal Payment Testing")

    # Handle query parameters
    query_params = st.experimental_get_query_params()
    payment_status = query_params.get("status", [""])[0]

    if payment_status == "success":
        st.success("Payment Approved! You can now proceed to capture the payment.")
        if "order" in st.session_state:
            order_id = st.session_state.order["id"]
            if st.button("Capture Payment"):
                try:
                    capture_response = capture_order(st.session_state.access_token, order_id)
                    st.success("Payment Captured Successfully!")
                    st.write("Capture Response:", capture_response)
                except requests.exceptions.RequestException as e:
                    st.error(f"Error capturing payment: {e}")
    elif payment_status == "cancel":
        st.warning("Payment was canceled. Please try again.")
    else:
        if st.button("Get Access Token"):
            try:
                access_token = get_access_token()
                st.session_state.access_token = access_token
                st.success("Access Token Retrieved!")
            except requests.exceptions.RequestException as e:
                st.error(f"Error getting access token: {e}")

        if "access_token" in st.session_state:
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

if __name__ == "__main__":
    main()
