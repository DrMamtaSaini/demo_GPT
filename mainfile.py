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