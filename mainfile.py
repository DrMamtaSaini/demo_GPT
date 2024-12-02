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

def create_order(access_token, amount="10.00"):
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

        # Automatically capture payment
        order_id = query_params.get("token", [""])[0]  # Extract order ID from redirect URL
        if not order_id:
            st.error("Order ID not found in the redirect URL.")
            return

        try:
            # Get Access Token and Capture Payment
            access_token = get_access_token()
            capture_response = capture_order(access_token, order_id)

            st.success("Payment Captured Successfully!")
            # Extract specific details for better readability
            payer_name = (
                capture_response["payer"]["name"]["given_name"]
                + " "
                + capture_response["payer"]["name"]["surname"]
            )
            payer_email = capture_response["payer"]["email_address"]
            amount = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
            currency = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["currency_code"]

            # Display extracted details
            st.write(f"**Payer Name:** {payer_name}")
            st.write(f"**Payer Email:** {payer_email}")
            st.write(f"**Amount Paid:** {amount} {currency}")
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred during payment processing: {e}")
        return

    elif page == "cancel":
        st.title("Payment Cancelled")
        st.warning("The payment was cancelled. Please try again.")
        return

    st.title("PayPal Payment")

    # Create Order and Display Payment Approval Window
    if st.button("Proceed to Payment"):
        try:
            access_token = get_access_token()
            order = create_order(access_token)
            approval_url = [link["href"] for link in order["links"] if link["rel"] == "approve"][0]
            st.markdown(f"[Click here to approve payment]({approval_url})")
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred while creating the payment: {e}")

if __name__ == "__main__":
    main()
