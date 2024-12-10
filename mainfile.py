import streamlit as st
import firebase_admin
import json
from firebase_admin import credentials, firestore, auth
import random
import hashlib
import time
import os
from werkzeug.security import generate_password_hash, check_password_hash
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import re
import string
from streamlit_option_menu import option_menu
import imghdr

# Set page configuration
st.set_page_config(page_title="EduPro.AI - AI-Powered Education System", layout="wide", page_icon="📚")

image_path = "./n1.jpeg"
file_type = imghdr.what(image_path)
video_path = "./Teacher_s_Assistant_AI_Tool.mp4"

# Initialize Firebase Admin SDK
def initialize_firebase():
    """
    Initialize Firebase Admin SDK and return the Firestore client.
    """
    try:
        if not firebase_admin._apps:  # Check if Firebase is already initialized
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
        return firestore.client()  # Return Firestore client
    except Exception as e:
        st.error(f"Error initializing Firebase: {e}")
        return None  # Return None if Firebase initialization fails



#initialize_firebase()

db = initialize_firebase()
if db is None:
    st.error("Firebase client is None. Check Firebase initialization.")
    st.stop()
else:
    st.write("Firebase initialized successfully.")


# Apply a consistent gradient background
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #3A0CA3, #4CC9F0);
            max-width: 100%;
            padding: 0;
            color: white;
        }
        .stTextInput>div>div>input, .stButton>button {
            background-color: rgba(255, 255, 255, 0.1);
            border: 1px solid white;
            color: white;
        }
        .stButton>button:hover {
            background-color: #4895EF;
            color: white;
            transition: 0.3s ease;
        }
    </style>
""",unsafe_allow_html=True)


# Utility Functions
def is_valid_email(email):
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email)

def is_valid_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search("[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search("[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search("[0-9]", password):
        return "Password must contain at least one digit."
    return None

# Generate Random Password
def generate_random_password(length=8):
    """Generate a random password."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))



def generate_verification_code(email):
    timestamp = int(time.time()) // 60
    data = f"{email}{timestamp}"
    return hashlib.sha256(data.encode()).hexdigest()[:6]

def send_verification_email(email, code):
    try:
        sg = SendGridAPIClient(st.secrets["sendgrid"]["api_key"])
        message = Mail(
            from_email="contact@digitaleralink.com",
            to_emails=email,
            subject="Verify Your Email",
            html_content=f"""
            <p>Hi,</p>
            <p>Please verify your email by entering the code below:</p>
            <h2>{code}</h2>
            <p>Thank you,</p>
            <p>EduPro.AI Team</p>
            """
        )
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        st.error(f"Error sending verification email: {e}")
        return False

# Email Verification
def verify_email():
    st.title("Verify Your Email")
    email = st.text_input("Enter your registered email", placeholder="Enter your email")
    code = st.text_input("Enter Verification Code", placeholder="Enter the code sent to your email")

    if st.button("Verify"):
        if not email or not code:
            st.error("All fields are required.")
            return

        generated_code = generate_verification_code(email)
        if code == generated_code:
            try:
                school_ref = db.collection("schools").where("email", "==", email).stream()
                school_doc = None
                for doc in school_ref:
                    school_doc = doc.id
                    break

                if not school_doc:
                    st.error("Invalid email.")
                    return

                db.collection("schools").document(school_doc).update({"verified": True})
                st.success("Email verified successfully! You can now log in.")
            except Exception as e:
                st.error(f"Verification failed: {e}")
        else:
            st.error("Invalid verification code.")

# Register School
def register_school():
    st.markdown("<h2 style='text-align: center; color: white;'>Register School</h2>", unsafe_allow_html=True)

    school_name = st.text_input("School Name", placeholder="Enter school name")
    email = st.text_input("Email", placeholder="Enter school email")
    password = st.text_input("Password", type="password", placeholder="Enter a strong password")

    if st.button("Register"):
        if not school_name or not email or not password:
            st.error("All fields are required.")
            return

        if not is_valid_email(email):
            st.error("Invalid email format.")
            return

        password_error = is_valid_password(password)
        if password_error:
            st.error(password_error)
            return

        hashed_password = generate_password_hash(password)
        verification_code = generate_verification_code(email)

        try:
            school_data = {
                "school_id": str(random.randint(1000, 9999)),
                "school_name": school_name,
                "email": email,
                "password": hashed_password,
                "created_on": firestore.SERVER_TIMESTAMP,
                "verified": False,
            }
            db.collection("schools").add(school_data)
            if send_verification_email(email, verification_code):
                st.success("Registration successful! Please check your email to verify.")
            else:
                st.warning("Registration successful, but failed to send verification email.")
        except Exception as e:
            st.error(f"Registration failed: {e}")

def login_user():
    """
    Unified login function for Admin, Teacher, and Student roles.
    """
    st.markdown("<h2 style='text-align: center; color: white;'>Login</h2>", unsafe_allow_html=True)
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "school_id" not in st.session_state:
        st.session_state["school_id"] = None

    #st.title("Login")

    # Login Form
    email = st.text_input("Email", placeholder="Enter your email")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Login"):
        try:
            # Step 1: Check if email belongs to a school owner (Admin/Owner)
            school_ref = db.collection("schools").where("email", "==", email).stream()
            school_data = next(school_ref, None)

            if school_data:
                # Owner login
                school_id = school_data.id
                school_details = school_data.to_dict()
                if not check_password_hash(school_details["password"], password):
                    st.error("Incorrect password.")
                    return

                if not school_details.get("verified", False):
                    st.error("Email not verified. Please check your inbox.")
                    return

                # Successful login
                st.session_state["logged_in"] = True
                st.session_state["role"] = "Admin"
                st.session_state["school_id"] = school_id
                st.session_state["user_name"] = school_details.get("school_name", "Owner")
                st.success("Welcome, Admin!")
                st.session_state["page"] = "admin_dashboard"
                return

            # Step 2: Check if email belongs to a user under any school (Teacher/Student)
            schools = db.collection("schools").stream()
            user_data = None
            for school in schools:
                users_ref = db.collection("schools").document(school.id).collection("users").where("email", "==", email).stream()
                user_data = next(users_ref, None)
                if user_data:
                    school_id = school.id  # Capture the school_id
                    break

            if user_data:
                # User login
                user_details = user_data.to_dict()
                if not check_password_hash(user_details["password"], password):
                    st.error("Incorrect password.")
                    return

                if not user_details.get("verified", False):
                    st.error("Email not verified. Please check your inbox.")
                    return

                # Successful login
                st.session_state["logged_in"] = True
                st.session_state["role"] = user_details["role"]
                st.session_state["school_id"] = school_id
                st.session_state["user_name"] = user_details.get("name", "User")

                # Redirect to respective dashboard based on role
                if user_details["role"] == "Teacher":
                    st.session_state["page"] = "teacher_dashboard"
                    st.success("Welcome, Teacher!")
                elif user_details["role"] == "Student":
                    st.session_state["page"] = "student_dashboard"
                    st.success("Welcome, Student!")
                return

            # If no matching user is found
            st.error("No user found with this email.")
        except Exception as e:
            st.error(f"Authentication failed: {e}")



def send_verification_email(email, verification_code):
    """Send an email with a verification link."""
    try:
        verification_link = f"https://your-app-url.com/verify?code={verification_code}"  # Replace with actual URL
        sg = SendGridAPIClient(st.secrets["sendgrid"]["api_key"])
        message = Mail(
            from_email="contact@digitaleralink.com",
            to_emails=email,
            subject="Verify Your Account",
            html_content=f"""
            <p>Hi,</p>
            <p>Welcome to our app. To activate your account, please verify your email:</p>
            <a href="{verification_link}">Verify Email</a>
            <p>If the link doesn't work, use this code:</p>
            <h3>{verification_code}</h3>
            <p>Best regards,<br>EduPro.AI Team</p>
            """
        )
        response = sg.send(message)
        if response.status_code == 202:
            st.success("Verification email sent successfully.")
            return True
        else:
            st.error(f"Failed to send verification email. Status: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error sending verification email: {e}")
        return False




def verify_user(verification_code):
    """Verify user by their email verification code."""
    try:
        user_ref = db.collection_group("users").where("verification_code", "==", verification_code).stream()
        for doc in user_ref:
            db.collection(doc.reference.parent.parent.path).document(doc.id).update({
                "verified": True,
                "verification_code": None  # Clear the code after verification
            })
            st.success("Email verified successfully! You can now log in.")
            return True
        st.error("Invalid or expired verification code.")
        return False
    except Exception as e:
        st.error(f"Error during verification: {e}")
        return False


def email_verification_page():
    """Page to handle email verification."""
    st.title("Email Verification")
    
    # Get verification code from URL query parameters
    query_params = st.experimental_get_query_params()
    verification_code = query_params.get("code", [None])[0]
    
    if verification_code:
        if verify_user(verification_code):
            st.success("Your email has been verified! You can now log in.")
            if st.button("Go to Login"):
                st.session_state.page = "login"  # Redirect to login page
        else:
            st.error("Invalid or expired verification link.")
    else:
        st.error("No verification code provided. Please check your email.")

# Signup/Signin Page
def signup_signin_page():
    # Add custom CSS for the radio button text color
    st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] label {
            color: white !important;
        }
        div[data-testid="stHorizontalBlock"] {
            padding: 10px;
            border-radius: 10px;
            background: linear-gradient(135deg, #6a00f4, #4cc9f0);
        }
        </style>
    """, unsafe_allow_html=True)

    # Welcome Heading
    #st.markdown("<h1 style='color: lightblue;'>Welcome to EduPro.AI Portal</h1>", unsafe_allow_html=True)

    # Radio Button for Sign Up/Sign In
    option = st.radio("Choose an option:", ["Sign Up", "Sign In"], index=0)

    # Render forms based on selection
    if option == "Sign Up":
       # st.markdown("<h4 style='color: white;'>Create Your School Account</h3>", unsafe_allow_html=True)
        register_school()
        verify_email()
    elif option == "Sign In":
      #  st.markdown("<h4 style='color: white;'>Sign In to Your Account</h3>", unsafe_allow_html=True)
        login_user()





# Main Page Functionality
def sign():
    # Add CSS styling to change text color inside text boxes
    st.markdown("""
        <style>
            input {
                color: black !important; /* Set the text color inside the text boxes to black */
            }
            textarea {
                color: black !important; /* Set the text color inside text areas to black */
            }
            .stTextInput > div > div > input, .stTextArea > div > div > textarea {
                background-color: rgba(255, 255, 255, 0.9) !important; /* Change background to light gray */
                border: 1px solid #cccccc !important; /* Add a border for better visibility */
                border-radius: 5px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
            .main-container {
                display: flex;
                justify-content: space-between;
                align-items: center;
                height: 100vh;
                padding: 0 5%;
            }
            .left-container {width: 40%;}
            .right-container {width: 55%; text-align: center;}
        </style>
    """, unsafe_allow_html=True)

    # Main Container
    col1, col2 = st.columns([1, 2])

    # Left Side: Sign In / Sign Up
    with col1:
        signup_signin_page()

    # Right Side: Display Image
    with col2:
        st.markdown("<div class='right-container'>", unsafe_allow_html=True)
        
        # Display image from your project directory
        

       
        
        if os.path.exists(image_path):
            st.write(f"File found: {image_path}")
            st.image(image_path, use_container_width=True, caption="Welcome to EduPro.AI")
        else:
            st.error(f"Image not found at: {image_path}")


# Admin Dashboard
def admin_dashboard():
    """
    Admin Dashboard with common features and admin-specific functionalities.
    """
    try:
        # Render Header
        header()

        # Sidebar Styling
        st.sidebar.markdown("""
            <style>
            .css-1d391kg, .css-1d391kg h3, .css-1d391kg p {
                color: #4cc9f0 !important; /* Cyan color */
                font-weight: bold !important;
            }
            .stSidebar > div {
                background-color: #1E1E1E; /* Dark background for sidebar */
            }
            </style>
        """, unsafe_allow_html=True)

        # Check for session state and school ID
        if "school_id" not in st.session_state:
            st.error("No school ID found. Please log in again.")
            st.stop()

        school_id = st.session_state["school_id"]

        # Fetch the school name dynamically
        db = initialize_firebase()
        school_doc = db.collection("schools").document(school_id).get()
        if not school_doc.exists:
            st.error("School data not found. Please contact support.")
            st.stop()

        school_name = school_doc.to_dict().get("school_name", "Your School")

        # Display School Name
        st.markdown(f"""
            <div style="text-align: center; font-size: 1.5rem; color: white; font-weight: bold; background: rgba(255, 255, 255, 0.1); padding: 10px; border-radius: 8px;">
                {school_name}
            </div>
        """, unsafe_allow_html=True)

        # Sidebar Navigation
        st.sidebar.title("Admin Navigation")
        task = st.sidebar.selectbox(
            "Select a Module",
            [
                "Dashboard Overview",
                "Manage Users",
                "Subscription Management",
                "Token Usage Analytics",
                "Educational Content Creation",
                "Student Assessment & Evaluation",
                "Curriculum & Alignment",
                "Advanced Editing & Text Generation"
            ]
        )

        # Display Sidebar Metrics
        st.sidebar.markdown("<h3 style='color: #4cc9f0; font-weight: bold;'>Key Metrics</h3>", unsafe_allow_html=True)
        try:
            # Fetch metrics dynamically from Firestore
            users_count = len(list(db.collection("schools").document(school_id).collection("users").stream()))
            token_limit = school_doc.to_dict().get("token_limit", "Unknown")
            tokens_used = school_doc.to_dict().get("tokens_used", 0)
        except Exception as e:
            st.error(f"Error fetching metrics: {e}")
            users_count, token_limit, tokens_used = 0, "Unknown", 0

        st.sidebar.markdown(f"**Total Users:** {users_count}", unsafe_allow_html=True)
        st.sidebar.markdown(f"**Token Limit:** {token_limit}", unsafe_allow_html=True)
        st.sidebar.markdown(f"**Tokens Used:** {tokens_used}", unsafe_allow_html=True)

        # Check Subscription Plan
        subscription_plan = st.session_state.get("subscription_plan", "Free")

        # Main Content Area
        if task == "Dashboard Overview":
            st.markdown("### Dashboard Overview")
            st.write("Welcome to the Admin Dashboard. Use the menu to navigate.")
        elif task == "Manage Users":
            manage_users(db, school_id)
        elif task == "Subscription Management":
            subscription_management()
        elif task == "Token Usage Analytics":
            token_usage_analytics(db, school_id)
        elif task == "Educational Content Creation":
            if subscription_plan == "Free":
                show_upgrade_message("Pro")
            else:
                content_creation_module()
        elif task == "Student Assessment & Evaluation":
            if subscription_plan == "Free":
                show_upgrade_message("Enterprise")
            else:
                assessment_module()
        elif task == "Curriculum & Alignment":
            if subscription_plan not in ["Pro", "Enterprise"]:
                show_upgrade_message("Pro")
            else:
                curriculum_module()
        elif task == "Advanced Editing & Text Generation":
            if subscription_plan != "Enterprise":
                show_upgrade_message("Enterprise")
            else:
                editing_and_text_generation_module()

        # Footer
        footer()

    except KeyError as e:
        st.error(f"Configuration error: {e}. Please log in again.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

def show_upgrade_message(required_plan):
    st.markdown(f"""
        <div style='background-color: #ffffff; padding: 10px; border-radius: 5px;'>
            <h4 style='color: #ff0000;'>Access Restricted</h4>
            <p style='color: #ff0000;'>This module is only available for the <b>{required_plan}</b> plan. Please upgrade to access this feature.</p>
        </div>
    """, unsafe_allow_html=True)

# Example Usage in a Restricted Module
def restricted_module(plan):
    current_plan = st.session_state.get("subscription_plan", "Free")
    if current_plan not in plan:
        show_upgrade_message(plan[0])  # Plan[0] specifies the required plan
    else:
        st.markdown("### Welcome to the Module!")

# Manage Users
def manage_users(db, school_id):
    st.markdown("### Manage Users")
    sub_task = st.radio("Manage Users", ["Create User", "View Users", "Edit User", "Delete User"])
    
    if sub_task == "Create User":
        st.markdown("#### Create a New User")
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["Teacher", "Admin"])
        if st.button("Create User"):
            try:
                user_data = {
                    "name": name,
                    "email": email,
                    "role": role,
                    "verified": False,
                    "created_on": firestore.SERVER_TIMESTAMP
                }
                db.collection("schools").document(school_id).collection("users").add(user_data)
                st.success(f"User '{name}' created successfully!")
            except Exception as e:
                st.error(f"Error creating user: {e}")

    elif sub_task == "View Users":
        st.markdown("#### View All Users")
        try:
            users_ref = db.collection("schools").document(school_id).collection("users").stream()
            users = [{"Name": user.to_dict().get("name", "N/A"), "Email": user.to_dict().get("email", "N/A"), "Role": user.to_dict().get("role", "N/A")} for user in users_ref]
            st.table(users)
        except Exception as e:
            st.error(f"Error fetching users: {e}")

    elif sub_task == "Edit User":
        st.markdown("#### Edit User Details")
        email = st.text_input("Enter User Email")
        new_name = st.text_input("New Name")
        new_role = st.selectbox("New Role", ["Teacher", "Admin", "Keep Existing"], index=2)
        if st.button("Update User"):
            try:
                users_ref = db.collection("schools").document(school_id).collection("users").where("email", "==", email).stream()
                user_doc = next(users_ref, None)
                if user_doc:
                    updates = {}
                    if new_name:
                        updates["name"] = new_name
                    if new_role != "Keep Existing":
                        updates["role"] = new_role
                    if updates:
                        db.collection("schools").document(school_id).collection("users").document(user_doc.id).update(updates)
                        st.success("User updated successfully!")
                    else:
                        st.warning("No changes made.")
                else:
                    st.error("User not found.")
            except Exception as e:
                st.error(f"Error updating user: {e}")

    elif sub_task == "Delete User":
        st.markdown("#### Delete a User")
        email = st.text_input("Enter User Email")
        if st.button("Delete User"):
            try:
                users_ref = db.collection("schools").document(school_id).collection("users").where("email", "==", email).stream()
                user_doc = next(users_ref, None)
                if user_doc:
                    db.collection("schools").document(school_id).collection("users").document(user_doc.id).delete()
                    st.success("User deleted successfully!")
                else:
                    st.error("User not found.")
            except Exception as e:
                st.error(f"Error deleting user: {e}")


# Subscription Management
def subscription_management(school_id):
    st.markdown("### Subscription Management")
    st.write("Manage and upgrade your subscription plan.")
    # Placeholder for subscription management logic


# Token Usage Analytics
def token_usage_analytics(db, school_id):
    st.markdown("### Token Usage Analytics")
    st.write("View and analyze token consumption trends.")
    # Placeholder for analytics logic


# Placeholder Functions for Modules
def content_creation_module():
    st.markdown("### Educational Content Creation Module")
    # Implementation based on selected submodule

def assessment_module():
    st.markdown("### Student Assessment & Evaluation Module")
    # Implementation based on selected submodule

def curriculum_module():
    st.markdown("### Curriculum & Alignment Module")
    # Implementation based on selected submodule

def editing_and_text_generation_module():
    st.markdown("### Advanced Editing & Text Generation Module")
    # Implementation based on selected submodule




def teacher_dashboard():
    #st.title("Teacher Dashboard")
    header()
    
    try:
        db = initialize_firebase()

        # Ensure school_id is in session state
        if "school_id" not in st.session_state:
            st.error("No school ID found. Please log in again.")
            st.stop()

        # Debug: Display session state school_id
       # st.write(f"Session State School ID: {st.session_state['school_id']}")

        # Fetch school data using Firestore document ID
        school_doc_id = st.session_state["school_id"]
        school_doc = db.collection("schools").document(school_doc_id).get()

        if not school_doc.exists:
            st.error("School data not found. Please contact support.")
            st.write("Debugging: Query returned no matching documents.")
            st.stop()

        # Extract school data
        school_data = school_doc.to_dict()
        school_name = school_data.get("school_name", "Your School")
        st.markdown(f"###  {school_name}")

        # Sidebar Navigation
        st.sidebar.title("Navigation & Settings")
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

        # Handle module navigation
        if task == "Home":
            st.markdown("### Home")
            st.write("Welcome to the Teacher Dashboard.")
        elif task == "Educational Content Creation":
            st.markdown("### Educational Content Creation")
            st.write("Submodules for creating content.")
        elif task == "Student Assessment & Evaluation":
            st.markdown("### Student Assessment & Evaluation")
            st.write("Submodules for assessment and evaluation.")
        elif task == "Curriculum & Alignment":
            st.markdown("### Curriculum & Alignment")
            st.write("Submodules for managing curriculum.")
        elif task == "Advanced Editing & Text Generation":
            st.markdown("### Advanced Editing & Text Generation")
            st.write("Submodules for editing and generating text.")
        elif task == "Subscription Management":
            st.markdown("### Subscription Management")
            st.write("Manage subscription details.")
        elif task == "Token Usage Analytics":
            st.markdown("### Token Usage Analytics")
            st.write("View token usage details.")

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")



def apply_theme(theme):
    """Apply the selected theme dynamically."""
    if theme == "Default":
        st.markdown("""
            <style>
                body { background-color: #f0f2f6; color: #000000; }
                .stApp { background-color: #f0f2f6; }
            </style>
        """, unsafe_allow_html=True)
    elif theme == "Dark":
        st.markdown("""
            <style>
                body { background-color: #121212; color: #e0e0e0; }
                .stApp { background-color: #121212; }
                h1, h2, h3, h4, h5, h6 { color: #ffffff; }
            </style>
        """, unsafe_allow_html=True)
    elif theme == "Light":
        st.markdown("""
            <style>
                body { background-color: #ffffff; color: #000000; }
                .stApp { background-color: #ffffff; }
                h1, h2, h3, h4, h5, h6 { color: #000000; }
            </style>
        """, unsafe_allow_html=True)
    elif theme == "Custom":
        bg_color = st.sidebar.color_picker("Select Background Color", "#ffffff")
        text_color = st.sidebar.color_picker("Select Text Color", "#000000")
        st.markdown(f"""
            <style>
                body {{ background-color: {bg_color}; color: {text_color}; }}
                .stApp {{ background-color: {bg_color}; }}
                h1, h2, h3, h4, h5, h6 {{ color: {text_color}; }}
            </style>
        """, unsafe_allow_html=True)


def display_sidebar_metrics():
    """Display key metrics in the sidebar."""
    st.sidebar.markdown("<h3>School Metrics</h3>", unsafe_allow_html=True)
    st.sidebar.markdown("""
        <style>
            .metric-box {
                padding: 10px;
                margin-bottom: 10px;
                background: linear-gradient(90deg, #4cc9f0, #4895ef);
                color: white;
                border-radius: 8px;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(
        "<div class='metric-box'><div class='metric-title'>Students Enrolled</div><div class='metric-value'>120</div></div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div class='metric-box'><div class='metric-title'>Assessments Completed</div><div class='metric-value'>45</div></div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div class='metric-box'><div class='metric-title'>API Tokens Used</div><div class='metric-value'>8,500</div></div>",
        unsafe_allow_html=True,
    )


def educational_content_navigation():
    """Handle navigation for the Educational Content Creation module."""
    subtask = st.sidebar.radio("Select a Submodule", [
        "Generate Question Paper",
        "Generate Sample Paper",
        "Generate Assignment",
        "Generate Quiz",
        "Generate Lesson Plans",
        "Generate Image-Based Questions",
        "Generate Paragraph-Based Question",
        "Generate Classroom Discussion Prompter"
    ])
    st.title(f"{subtask}")  # Display selected submodule


def student_assessment_navigation():
    """Handle navigation for the Student Assessment & Evaluation module."""
    subtask = st.sidebar.radio("Select a Submodule", [
        "Student Assessment Assistant",
        "Generate Answer Sheets",
        "Marking Scheme Generator",
        "Analyze Reports",
        "Grading",
        "Performance Graph"
    ])
    st.title(f"{subtask}")  # Display selected submodule


def curriculum_navigation():
    """Handle navigation for the Curriculum & Alignment module."""
    subtask = st.sidebar.radio("Select a Submodule", [
        "Curriculum Generator",
        "Alignment Checker"
    ])
    st.title(f"{subtask}")  # Display selected submodule


def advanced_editing_navigation():
    """Handle navigation for the Advanced Editing & Text Generation module."""
    subtask = st.sidebar.radio("Select a Submodule", [
        "Text Generation",
        "Advanced Editing"
    ])
    st.title(f"{subtask}")  # Display selected submodule

def student_dashboard():
    st.title("Student Dashboard")
    st.write("Access your learning resources.")



# Header Function
def header():
    st.markdown("""
        <style>
        .header {
            background: linear-gradient(90deg, #4cc9f0, #6a00f4); /* Cyan to Purple gradient */
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            font-family: Arial, sans-serif;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
        }
        .header h1 {
            font-size: 2.5rem;
            margin: 0;
        }
        </style>
        <div class="header">
            <h1>Welcome to EduPro.AI</h1>
        </div>
    """, unsafe_allow_html=True)

# Footer Function
def footer():
    st.markdown("""
        <style>
        .footer {
            background: linear-gradient(90deg, #6a00f4, #4cc9f0); /* Purple to Cyan gradient */
            color: white;
            text-align: center;
            padding: 15px;
            font-size: 0.9rem;
            border-radius: 8px;
            margin-top: 30px;
        }
        .footer a {
            color: #ffffff;  /* White links */
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        </style>
        <div class="footer">
            <p>© 2024 EduPro.AI | <a href="mailto:support@edupro.ai">Contact Support</a></p>
        </div>
    """, unsafe_allow_html=True)

# Navigation Menu
def menu():
    selected = option_menu(
        menu_title=None,
        options=["Home", "About", "Features", "Subscription Plans", "Help", "Login", "Logout"],
        icons=["house", "info-circle", "gear", "card-checklist", "question-circle", "key", "box-arrow-right"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {
                "padding": "0!important",
                "background": "linear-gradient(90deg, #6a00f4, #4cc9f0)",  # Purple to Cyan
            },
            "icon": {
                "color": "#ffffff",  # White icons
                "font-size": "20px",
            },
            "nav-link": {
                "font-size": "18px",
                "text-align": "center",
                "margin": "0px",
                "color": "#FFFFFF",  # White text for links
            },
            "nav-link-selected": {
                "background-color": "#ffffff",  # White highlight for selected
                "color": "#6a00f4",  # Purple text for selected
                "font-weight": "bold",
            },
        }
    )
    return selected





def about_page():
    st.markdown("""
        <style>
        .about-container {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
        }
        .about-container h2 {
            font-size: 2rem;
            margin-bottom: 10px;
        }
        .about-container p {
            font-size: 1.2rem;
            text-align: justify;
        }
        </style>
        <div class="about-container">
            <h2>About EduPro.AI</h2>
            <p>EduPro.AI is an AI-powered platform designed to revolutionize the education sector. 
            Our goal is to simplify teaching, automate grading, and provide actionable insights to educators. 
            With features like AI-powered content creation, automated assessments, and performance analytics, EduPro.AI empowers schools to focus on what matters most – student learning and growth.</p>
            <p>Built for schools of all sizes, EduPro.AI is the trusted partner for thousands of educators globally, helping them save time and improve learning outcomes.</p>
        </div>
    """, unsafe_allow_html=True)
def features_page():
    st.markdown("""
        <style>
        .features-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
        }
        .feature-card {
            flex: 1 1 calc(30% - 20px);
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.3);
        }
        .feature-card h3 {
            color: #4cc9f0;
            margin-bottom: 10px;
        }
        .feature-card p {
            color: white;
        }
        </style>
        <div class="features-container">
            <div class="feature-card">
                <h3>AI-Powered Content Creation</h3>
                <p>Create lesson plans, quizzes, and assignments with just a few clicks.</p>
            </div>
            <div class="feature-card">
                <h3>Automated Assessments</h3>
                <p>Save time with instant grading and performance analysis.</p>
            </div>
            <div class="feature-card">
                <h3>Actionable Insights</h3>
                <p>Generate detailed reports to track student progress and identify areas for improvement.</p>
            </div>
            <div class="feature-card">
                <h3>Curriculum Alignment</h3>
                <p>Plan and align curricula effortlessly with built-in alignment tools.</p>
            </div>
            <div class="feature-card">
                <h3>24/7 Support</h3>
                <p>Our team is always here to assist you with any issues or questions.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

def help_page():
    st.markdown("""
        <style>
        .help-container {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
        }
        .help-container h2 {
            font-size: 2rem;
            margin-bottom: 20px;
        }
        .help-container p {
            font-size: 1.2rem;
            text-align: justify;
            margin-bottom: 20px;
        }
        .contact {
            font-size: 1rem;
            color: #4cc9f0;
        }
        </style>
        <div class="help-container">
            <h2>Help & Support</h2>
            <p>Need assistance? Our team is here to help! Whether you're facing technical issues or have questions about our features, 
            feel free to reach out to us. We’re committed to providing the best support experience possible.</p>
            <p class="contact">Contact us at <a href="mailto:support@edupro.ai">support@edupro.ai</a></p>
            <p class="contact">Phone: +123 456 7890</p>
        </div>
    """, unsafe_allow_html=True)

def subscription_page():
    """
    Subscription plans styled with cards, centered text, and hover effects.
    """
    st.markdown("""
        <style>
        .subscription-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            padding: 20px;
        }
        .subscription-card {
            background: linear-gradient(135deg, #3A0CA3, #4CC9F0);
            border-radius: 12px;
            box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.3);
            color: white;
            width: 300px;
            text-align: center;
            padding: 20px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .subscription-card:hover {
            transform: translateY(-5px);
            box-shadow: 0px 12px 20px rgba(0, 0, 0, 0.4);
        }
        .subscription-card h4 {
            font-size: 1.8rem;
            margin-bottom: 10px;
            color: #E0FBFC;
        }
        .subscription-card .price {
            font-size: 1.5rem;
            margin-bottom: 15px;
            font-weight: bold;
        }
        .subscription-card ul {
            list-style-type: none;
            padding: 0;
            margin: 0;
        }
        .subscription-card ul li {
            font-size: 1rem;
            margin-bottom: 10px;
            color: #A8DADC;
        }
        .subscription-card button {
            margin-top: 20px;
            background-color: white;
            color: #3A0CA3;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: bold;
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        .subscription-card button:hover {
            background-color: #4CC9F0;
            color: white;
        }
        </style>
        <div class="subscription-container">
            <!-- Free Plan -->
            <div class="subscription-card">
                <h4>Free Plan</h4>
                <p class="price">$0/month</p>
                <ul>
                    <li>Grading</li>
                    <li>Performance Graph</li>
                    <li>Generate Question Paper</li>
                    <li>10,000 API tokens per school/month</li>
                </ul>
                <button onclick="window.location.href='/free_dashboard'">Choose Free Plan</button>
            </div>
            <!-- Pro Plan -->
            <div class="subscription-card">
                <h4>Pro Plan</h4>
                <p class="price">$500/month</p>
                <ul>
                    <li>Access to 4 Modules</li>
                    <li>7M API Tokens/Month</li>
                    <li>800 Student Capacity</li>
                    <li>Priority Support</li>
                </ul>
                <button onclick="window.location.href='/payment_page?plan=pro'">Choose Pro Plan</button>
            </div>
            <!-- Enterprise Plan -->
            <div class="subscription-card">
                <h4>Enterprise Plan</h4>
                <p class="price">$750/month</p>
                <ul>
                    <li>Access to All Modules</li>
                    <li>11M API Tokens/Month</li>
                    <li>1000 Student Capacity</li>
                    <li>Dedicated Support</li>
                </ul>
                <button onclick="window.location.href='/payment_page?plan=enterprise'">Choose Enterprise Plan</button>
            </div>
        </div>
    """, unsafe_allow_html=True)
def subscription_management():
    """
    Subscription plans styled with cards, centered text, and displayed horizontally with working buttons to proceed to payment.
    """
    # Custom CSS for success message and layout
    st.markdown("""
        <style>
        .stAlert > div[role="alert"] {
            background-color: #4CC9F0 !important;  /* Cyan background */
            color: white !important;             /* White text */
            font-weight: bold !important;
            border-radius: 8px;
            padding: 15px;
        }
        .subscription-container {
            display: flex;
            justify-content: center;
            gap: 20px;
            padding: 20px;
        }
        .subscription-card {
            background: linear-gradient(135deg, #3A0CA3, #4CC9F0);
            border-radius: 12px;
            box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.3);
            color: white;
            width: 300px;
            text-align: center;
            padding: 20px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .subscription-card:hover {
            transform: translateY(-5px);
            box-shadow: 0px 12px 20px rgba(0, 0, 0, 0.4);
        }
        .subscription-card h4 {
            font-size: 1.8rem;
            margin-bottom: 10px;
            color: #E0FBFC;
        }
        .subscription-card .price {
            font-size: 1.5rem;
            margin-bottom: 15px;
            font-weight: bold;
        }
        .subscription-card ul {
            list-style-type: none;
            padding: 0;
            margin: 0;
        }
        .subscription-card ul li {
            font-size: 1rem;
            margin-bottom: 10px;
            color: #A8DADC;
        }
        .subscription-card .button-container {
            margin-top: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Render the subscription plans in a horizontal layout
    st.markdown("<div class='subscription-container'>", unsafe_allow_html=True)

    # Free Plan
    st.markdown("""
        <div class='subscription-card'>
            <h4>Free Plan</h4>
            <p class='price'>$0/month</p>
            <ul>
                <li>Grading</li>
                <li>Performance Graph</li>
                <li>Generate Question Paper</li>
                <li>10,000 API tokens per school/month</li>
            </ul>
            <div class='button-container'>
                """, unsafe_allow_html=True)
    if st.button("Choose Free Plan", key="free_plan"):
        st.session_state["subscription_plan"] = "Free"
        st.success("You have selected the Free Plan!")
    st.markdown("</div></div>", unsafe_allow_html=True)

    # Pro Plan
    st.markdown("""
        <div class='subscription-card'>
            <h4>Pro Plan</h4>
            <p class='price'>$500/month</p>
            <ul>
                <li>Access to 4 Modules</li>
                <li>7M API Tokens/Month</li>
                <li>800 Student Capacity</li>
                <li>Priority Support</li>
            </ul>
            <div class='button-container'>
                """, unsafe_allow_html=True)
    if st.button("Choose Pro Plan", key="pro_plan"):
        st.session_state["subscription_plan"] = "Pro"
        st.session_state["payment_details"] = {"amount": 500, "description": "Pro Plan"}
        st.success("Redirecting to Payment Page...")
        st.session_state["page"] = "payment_page"
    st.markdown("</div></div>", unsafe_allow_html=True)

    # Enterprise Plan
    st.markdown("""
        <div class='subscription-card'>
            <h4>Enterprise Plan</h4>
            <p class='price'>$750/month</p>
            <ul>
                <li>Access to All Modules</li>
                <li>11M API Tokens/Month</li>
                <li>1000 Student Capacity</li>
                <li>Dedicated Support</li>
            </ul>
            <div class='button-container'>
                """, unsafe_allow_html=True)
    if st.button("Choose Enterprise Plan", key="enterprise_plan"):
        st.session_state["subscription_plan"] = "Enterprise"
        st.session_state["payment_details"] = {"amount": 750, "description": "Enterprise Plan"}
        st.success("Redirecting to Payment Page...")
        st.session_state["page"] = "payment_page"
    st.markdown("</div></div>", unsafe_allow_html=True)

    #st.markdown("</div>", unsafe_allow_html=True)




# Payment Page
def payment_page():
    """
    Display the payment page for Pro or Enterprise plan.
    """
    if "payment_details" not in st.session_state:
        st.error("No payment details found. Please select a subscription plan.")
        return

    details = st.session_state["payment_details"]
    amount = details["amount"]
    description = details["description"]

    st.title("Payment Page")
    st.write(f"Subscribe to the **{description}** for **${amount}/month**.")

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

def logout_page():
    st.markdown("""
        <style>
        .logout-container {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
        }
        .logout-container h2 {
            font-size: 2rem;
            margin-bottom: 20px;
        }
        .logout-container p {
            font-size: 1.2rem;
            text-align: justify;
        }
        </style>
        <div class="logout-container">
            <h2>Logged Out Successfully</h2>
            <p>You have been successfully logged out. Thank you for using EduPro.AI. We hope to see you again soon!</p>
        </div>
    """, unsafe_allow_html=True)
    st.session_state.clear()  # Clear session state on logout

# Landing Page Function
def landing_page():
    header()  # Add Header
    selected = menu()  # Display Navigation Menu

    if selected == "Home":
        # Page Background Styling
        st.markdown("""
            <style>
            [data-testid="stAppViewContainer"] {
                background: linear-gradient(135deg, #6a00f4, #4cc9f0); /* Static gradient */
                padding: 20px;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)

        # Landing Page Main Content
        st.markdown("""
            <style>
            .content-container {
                background: rgba(255, 255, 255, 0.1); /* Translucent white */
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
            }
            .content-container h2 {
                color: #ffffff;  /* White */
                text-align: center;
                font-size: 2rem;
                margin-bottom: 10px;
            }
            .content-container p {
                color: white;
                font-size: 1.2rem;
                text-align: justify;
            }
            </style>
            <div class="content-container">
                <h2>Revolutionize Education with AI</h2>
                <p>Transform your school's learning and assessment processes with EduPro.AI. 
                Leverage AI to create content, automate assessments, and generate actionable insights for teachers and administrators.</p>
            </div>
        """, unsafe_allow_html=True)

        # Video Section
        st.markdown("<h3 style='text-align: center; color: #ffffff;'>Discover EduPro.AI in Action</h3>", unsafe_allow_html=True)
        if os.path.exists(video_path):
            st.video(video_path)
        else:
            st.error("Video not found. Please check the path!")

        # Features Section with Cards
        st.markdown("<h2 style='text-align: center; color: #ffffff;'>Why Choose EduPro.AI?</h2>", unsafe_allow_html=True)
        st.markdown("""
            <style>
            .card {
                background: rgba(255, 255, 255, 0.2); /* Semi-transparent white */
                border-radius: 8px;
                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
                padding: 20px;
                text-align: center;
                transition: transform 0.3s, box-shadow 0.3s;
                cursor: pointer;
            }
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.3);
            }
            .card h4 {
                color: #4cc9f0; /* Cyan */
                margin-bottom: 10px;
            }
            .card p {
                color: white;
                font-size: 1rem;
            }
            </style>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("<div class='card'><h4>AI-Powered Content</h4><p>Create lesson plans, quizzes, and notes instantly.</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='card'><h4>Automated Grading</h4><p>Save time with AI-powered assessment tools.</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div class='card'><h4>Detailed Reports</h4><p>Get performance analytics and actionable insights.</p></div>", unsafe_allow_html=True)
        with col4:
            st.markdown("<div class='card'><h4>24/7 Support</h4><p>Our team is here to help you anytime.</p></div>", unsafe_allow_html=True)

        # Subscription Plans Section with Cards
        st.markdown("<h2 style='text-align: center; color: #ffffff;'>Subscription Plans</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("<div class='card'><h4>Free Plan</h4><p>$0/month</p><ul><li>Grading</li><li>Performance Graph</li><li>10,000 API tokens/month</li></ul></div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='card'><h4>Pro Plan</h4><p>$500/month</p><ul><li>Access to 4 Modules</li><li>7M API Tokens/Month</li><li>Priority Support</li></ul></div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div class='card'><h4>Enterprise Plan</h4><p>$750/month</p><ul><li>Access to All Modules</li><li>11M API Tokens/Month</li><li>Dedicated Support</li></ul></div>", unsafe_allow_html=True)

    elif selected == "About":
        st.title("About EduPro.AI")
        st.write("EduPro.AI is your partner in revolutionizing education through the power of AI.")
        about_page()

    elif selected == "Features":
        st.title("Features")
        st.write("Explore the powerful features that make EduPro.AI your trusted educational assistant.")
        features_page()
    elif selected == "Subscription Plans":
        st.title("Subscription Plans")
        st.write("Choose the right plan for your school's unique needs.")
        subscription_page()
    elif selected == "Help":
        st.title("Help & Support")
        st.write("Need assistance? Contact our support team for help.")
        help_page()
    elif selected == "Login":
        sign()
    elif selected == "Logout":
        logout_page()
        
    footer()  # Add Footer
def app_router():
    """Route Between Pages"""
    # Initialize session state for page routing
    if "page" not in st.session_state:
        st.session_state["page"] = "landing"

    # Route based on the current page state
    if st.session_state["page"] == "landing":
        landing_page()
    #elif st.session_state["page"] == "sign":
       # sign()
    elif st.session_state["page"] == "signup_signin":
        signup_signin_page()
    
    elif st.session_state["page"] == "admin_dashboard":
       
        admin_dashboard()
    elif st.session_state["page"] == "teacher_dashboard":
        #st.title("Teacher Dashboard")
        teacher_dashboard()
    elif st.session_state["page"] == "student_dashboard":
        st.title("Student Dashboard")

    elif st.session_state["page"] == "success":
        success_page()
    elif st.session_state["page"] == "subscription":
        subscription_page()
    elif st.session_state["page"] == "dashboard":
        free_version_dashboard()
    elif st.session_state.page == "payment_page":
        payment_page()




# Main Function
if __name__ == "__main__":
    app_router()
