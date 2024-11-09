import streamlit as st
import openai
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
import os
from docx import Document
import json
from docx.shared import Inches
from io import BytesIO
import requests
from PyPDF2 import PdfReader  # Ensure this is imported for reading PDF files


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
            st.session_state['logged_in'] = True  # Set the logged-in state
        else:
            st.error("Invalid username or password.")


openai.api_key = st.secrets["openai_api_key"]

# Function to fetch images based on topic and subtopics
def fetch_image(prompt):
    response = openai.Image.create(prompt=prompt, n=1, size="512x512")
    image_url = response['data'][0]['url']
    image_response = requests.get(image_url)
    return BytesIO(image_response.content)

# Function to generate question using GPT based on input
def generate_question(topic, class_level, question_type, subtopic):
    prompt = f"Generate a {question_type} question on the topic '{topic}' for {class_level} on the subtopic '{subtopic}'. Include a question text and answer options."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to create quiz document
def create_quiz_document(topic, class_level, num_questions, question_type):
    document = Document()
    document.add_heading(f'{topic} Quiz for {class_level}', level=1)
    subtopics = ["flowering plants", "trees", "herbs"] if topic == "Plants" else ["topic1", "topic2", "topic3"]
    
    for i in range(num_questions):
        subtopic = subtopics[i % len(subtopics)]
        question_text = generate_question(topic, class_level, question_type, subtopic)
        image_prompt = f"Image of {subtopic} for {class_level} related to {topic}"
        image = fetch_image(image_prompt)
        document.add_picture(image, width=Inches(2))
        document.add_paragraph(f'Q{i+1}: {question_text}')
        if question_type == "MCQ":
            document.add_paragraph("a) Option 1\nb) Option 2\nc) Option 3\nd) Option 4")
        elif question_type == "true/false":
            document.add_paragraph("a) True\nb) False")
        elif question_type == "yes/no":
            document.add_paragraph("a) Yes\nb) No")
        document.add_paragraph("\n")
    document.add_paragraph("\nAnswers:\n")
    for i in range(num_questions):
        document.add_paragraph(f'Q{i+1}: ________________')
    filename = f'{topic}_Quiz_{class_level}.docx'
    document.save(filename)
    return filename

# Load client configuration
with open("clients_config.json") as config_file:
    clients_config = json.load(config_file)

def get_client_config(client_id):
    default_config = {"name": "Default Academy", "logo": "https://path-to-default-logo.png", "theme_color": "#000000"}
    return clients_config.get(client_id, default_config)

client_id = st.experimental_get_query_params().get("client_id", ["default"])[0]
client_config = get_client_config(client_id)
st.image(client_config["logo"], width=200)
st.title(f"Welcome to {client_config['name']}!")
st.markdown(f"<style>.main {{ background-color: {client_config['theme_color']}; }}</style>", unsafe_allow_html=True)

# Function to generate a PDF file for reports
def generate_pdf(content, title, file_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(file_name)

# Function to send an email with PDF attachment
def send_email_with_pdf(to_email, subject, body, file_name):
    from_email = st.secrets["email"]
    password = st.secrets["password"]
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    with open(file_name, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {file_name}')
        msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)
    server.sendmail(from_email, to_email, msg.as_string())
    server.quit()
    st.success(f"Email sent to {to_email} with the attached PDF report!")

st.markdown("""
    <style>
        body { background-color: #F0F2F6; }
        .stApp { color: #4B0082; }
        .sidebar .sidebar-content { background: linear-gradient(180deg, #6A5ACD, #483D8B); color: white; }
        h1, h2, h3, h4 { color: #4B0082; }
        .stButton>button { background-color: #6A5ACD; color: white; border-radius: 8px; width: 100%; padding: 10px; font-size: 16px; }
        .stButton>button:hover { background-color: #483D8B; color: white; }
        .stFileUploader { color: #4B0082; }
        .stMarkdown { color: #4B0082; }
        .stAlert, .stSuccess { color: #228B22; background-color: #E0FFE0; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# Function to read PDF content and display it for debugging
def read_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

# Improved function to extract weak topics
def extract_weak_topics(assessment_content):
    weak_topics = []
    # Adjust keywords here based on report language
    for line in assessment_content.splitlines():
        if "Concept Clarity: No" in line:
            topic_line = line.split("Concept Clarity: No")[0].strip()
            topic = topic_line.split("- Subtopic:")[0].replace("Topic:", "").strip()
            weak_topics.append(topic)
    return list(set(weak_topics))

# Function to generate personalized learning material based on weak topics
def generate_personalized_material(weak_topics):
    prompt = f"Create learning material covering the following topics where the student needs improvement: {', '.join(weak_topics)}. Provide detailed explanations and examples for each topic."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to generate personalized assignments based on weak topics
def generate_personalized_assignment(weak_topics, include_solutions):
    solution_text = "Include detailed solutions for each question." if include_solutions else "Provide only the questions without solutions."
    prompt = f"Create an assignment for the following topics where the student needs improvement: {', '.join(weak_topics)}. {solution_text}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to save content as a Word document
def save_content_as_doc(content, file_name):
    doc = Document()
    for line in content.split("\n"):
        doc.add_paragraph(line)
    doc.save(file_name)

# Function to read Word document content
def read_docx(file):
    doc = Document(file)
    full_text = [para.text for para in doc.paragraphs]
    return "\n".join(full_text)

# Function to sanitize text by replacing unsupported characters
def sanitize_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

# Function to generate content for educational purposes
def generate_content(board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions):
    prompt = f"""
    You are an educational content creator. Create {content_type} for the {board} board, {standard} class. 
    Based on the topics: {topics}. The {content_type} should be of {total_marks} marks and a time duration of {time_duration}. 
    The question types should include {', '.join(question_types)}, with a difficulty level of {difficulty}.
    The category of questions should be {category}.
    """
    
    if include_solutions:
        prompt += " Include the solution set."
    else:
        prompt += " Only include the question set without solutions."
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to generate a lesson plan
def generate_lesson_plan(subject, grade, board, duration, topic):
    prompt = f"""
    Create a comprehensive lesson plan for teaching {subject} to {grade} under the {board} board. 
    The lesson duration is {duration}, and the topic of the lesson is {topic}. The lesson plan should include:

    - Lesson Title and Duration
    - Learning Objectives
    - Materials and Resources Needed
    - Detailed Lesson Flow:
        - Introduction (5-10 minutes)
        - Core Teaching Segment with explanations and examples
        - Interactive Activities for engagement
        - Assessment and Recap to measure understanding
        - Homework/Assignments for reinforcement
    - Date and Schedule field
    Ensure flexibility to adapt to different student needs, learning speeds, and teaching styles.
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Main function
def main_app():
    # Apply custom CSS for an attractive UI
    st.markdown("""
    <style>
        body { background-color: #F0F2F6; }
        .stApp { color: #4B0082; }
        .sidebar .sidebar-content { background: linear-gradient(180deg, #6A5ACD, #483D8B); color: white; }
        h1, h2, h3, h4 { color: #4B0082; }
        .stButton>button { background-color: #6A5ACD; color: white; border-radius: 8px; width: 100%; padding: 10px; font-size: 16px; }
        .stButton>button:hover { background-color: #483D8B; color: white; }
        .stFileUploader { color: #4B0082; }
        .stMarkdown { color: #4B0082; }
        .stAlert, .stSuccess { color: #228B22; background-color: #E0FFE0; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.title("EduCreate Pro")
    task = st.sidebar.radio("Select Module", ["Home", "Create Educational Content", "Create Lesson Plan", "Student Assessment Assistant","Personalized Learning Material","Generate Image Based Questions"])
 # Add the logout button in the sidebar
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False  # Reset login status

    if task == "Home":
        st.title("EduCreate Pro")
        st.markdown("""
            <div style='text-align: center; font-size: 18px; color: #4B0082;'>
                Your all-in-one platform for creating educational content, lesson plans, and student assessments, Image Based Questions.
            </div>
        """, unsafe_allow_html=True)
        col1, col2, col3,col4,col5 = st.columns(5)
        with col1:
            st.subheader("Content Creator")
            st.write("Generate quizzes, sample papers, and assignments.")
        with col2:
            st.subheader("Lesson Planner")
            st.write("Create detailed lesson plans with learning objectives and materials.")
        with col3:
            st.subheader("Assessment Assistant")
            st.write("Generate comprehensive student assessments and progress reports.")
        with col4:
            st.subheader("Personalised Learning Material")
            st.write("Generate learning material and assignment based on your assessment report.")
        with col5:
            st.subheader("Image Based Question Generator")
            st.write("Generate Image Based Quiz (MCQ, True/false, Yes/No type)")
        
        st.markdown("""
            <div style='text-align: center; margin-top: 30px;'>
                <button style="padding: 15px; font-size: 16px; background-color: #6A5ACD; color: white; border: none; border-radius: 8px; cursor: pointer;">
                    Get Started Today
                </button>
            </div>
        """, unsafe_allow_html=True)

    elif task == "Student Assessment Assistant":
        st.header("Student Assessment Assistant")
        student_name = st.text_input("Enter Student Name:")
        student_id = st.text_input("Enter Student ID:")
        assessment_id = st.text_input("Enter Assessment ID:")
        class_name = st.text_input("Enter Class:")
        email_id = st.text_input("Enter Parent's Email ID:")
        assessment_pdf = st.file_uploader("Upload Assessment Report (PDF)", type=["pdf"])

        if st.button("Generate and Send Personalized Learning Material"):
            if student_name and student_id and assessment_id and class_name and email_id and assessment_pdf:
                # Step 1: Extract text from PDF
                assessment_content = read_pdf(assessment_pdf)

                # Step 2: Extract weak topics from the content
                weak_topics = extract_weak_topics(assessment_content)

                # If weak topics are identified, proceed to generate materials
                if weak_topics:
                    learning_material = generate_personalized_material(weak_topics)
                    assignment = generate_personalized_assignment(weak_topics, include_solutions=True)

                    # Save and send files as attachments
                    save_content_as_doc(learning_material, "Learning_Material.docx")
                    save_content_as_doc(assignment, "Assignment.docx")

                    send_email_with_pdf(email_id, "Personalized Learning Material", "Attached learning material.", "Learning_Material.docx")
                    send_email_with_pdf(email_id, "Personalized Assignment", "Attached assignment.", "Assignment.docx")
                    st.success(f"Personalized materials have been sent to {email_id}.")
                else:
                    st.warning("No weak topics identified. Please ensure the assessment report is properly formatted.")

    elif task == "Generate Image Based Questions":
        st.header("Generate Image Based Questions")
        topic = st.text_input("Select a topic (e.g., Plants, Animals, Geography, Famous Landmarks):")
        class_level = st.text_input("Select a class level (e.g., Grade 1, Grade 2, Grade 3):")
        num_questions = st.number_input("Enter the number of questions (minimum 5):", min_value=5)
        question_type = st.selectbox("Choose question type", ["MCQ", "true/false", "yes/no"])

        if st.button("Generate Quiz Document"):
            if num_questions < 5:
                st.warning("Minimum number of questions is 5. Setting to 5.")
                num_questions = 5
            quiz_filename = create_quiz_document(topic, class_level, num_questions, question_type)
            st.success(f"Quiz generated and saved as '{quiz_filename}'")
            with open(quiz_filename, "rb") as file:
                st.download_button(label="Download Quiz Document", data=file.read(), file_name=quiz_filename)
   

def main():
    if st.session_state['logged_in']:
        main_app()  # Show main app content if logged in
    else:
        login_page()  # Show login page if not logged in
    

if __name__ == "__main__":
    main()
  
