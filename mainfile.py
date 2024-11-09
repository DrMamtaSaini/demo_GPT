import streamlit as st

# Define a single user login with a username and password
USER_CREDENTIALS = {"username": "admin", "password": "password123"}

# Initialize session state for login status
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Login Page
def login_page():
    st.title("Login Page")

    # Input fields for username and password
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    # Login button
    if st.button("Login"):
        if username == USER_CREDENTIALS["username"] and password == USER_CREDENTIALS["password"]:
            # Set the logged-in state without rerunning
            st.session_state['logged_in'] = True
        else:
            st.error("Invalid username or password.")

# Main Application Content
def main_app():
    st.title("Main App Page")
    st.write("Welcome to the main content area! You are now logged in.")

    # Logout button
    if st.button("Logout"):
        st.session_state['logged_in'] = False  # Reset login status to show login page again

# Display login or main app content based on login status
if st.session_state['logged_in']:
    main_app()
else:
    login_page()
