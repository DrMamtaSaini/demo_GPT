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
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        st.error(f"Error generating access token: {response.json()}")
        return None

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
    if response.status_code == 201:
        return response.json()
    else:
        st.error(f"Error creating order: {response.json()}")
        return None

def capture_order(access_token, order_id):
    """Capture PayPal Order."""
    url = f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        return response.json()
    else:
        st.error(f"Error capturing payment: {response.json()}")
        return None

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
        
        # Get Access Token
        access_token = get_access_token()
        if not access_token:
            st.error("Failed to generate access token.")
            return
        
        # Capture Payment
        capture_response = capture_order(access_token, order_id)
        if capture_response:
            st.success("Payment Captured Successfully!")
            # Display detailed capture response
            st.json(capture_response)

            # Extract specific details for better readability
            payer_name = capture_response["payer"]["name"]["given_name"] + " " + capture_response["payer"]["name"]["surname"]
            payer_email = capture_response["payer"]["email_address"]
            amount = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
            currency = capture_response["purchase_units"][0]["payments"]["captures"][0]["amount"]["currency_code"]

            # Display extracted details
            st.write(f"**Payer Name:** {payer_name}")
            st.write(f"**Payer Email:** {payer_email}")
            st.write(f"**Amount Paid:** {amount} {currency}")
        else:
            st.error("Failed to capture payment. Please check your PayPal account for the payment status.")
        return

    elif page == "cancel":
        st.title("Payment Cancelled")
        st.warning("The payment was cancelled. Please try again.")
        return

    st.title("PayPal Payment Integration")

    # Step 1: Get Access Token
    if "access_token" not in st.session_state:
        if st.button("Generate Access Token"):
            access_token = get_access_token()
            if access_token:
                st.session_state.access_token = access_token
                st.success("Access Token Retrieved!")
            else:
                st.error("Failed to retrieve access token.")

    # Step 2: Create Order
    if "access_token" in st.session_state:
        if st.button("Create PayPal Order"):
            order = create_order(st.session_state.access_token)
            if order:
                st.session_state.order = order
                approval_url = [link["href"] for link in order["links"] if link["rel"] == "approve"][0]
                st.success("Order Created!")
                st.write("Order Details:", order)
                st.markdown(f"[Click here to approve payment]({approval_url})")

if __name__ == "__main__":
    main()
