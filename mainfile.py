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

SCHOOL_CREDENTIALS = st.secrets["scho_credentials"]

# Initialize session states for login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'school_id' not in st.session_state:
    st.session_state['school_id'] = None
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

def login_page():
    # Show login fields only if not logged in
    if not st.session_state['logged_in']:
        st.title("School Login")
        school_username = st.text_input("Username", key="school_username_input", placeholder="Enter username")
        school_password = st.text_input("Password", type="password", key="school_password_input", placeholder="Enter password")
        
        if st.button("Login"):
            # Check credentials
            for school_id, credentials in SCHOOL_CREDENTIALS.items():
                if (school_username == credentials["username"] and school_password == credentials["password"]):
                    # Set session state for successful login
                    st.session_state['logged_in'] = True
                    st.session_state['school_id'] = school_id
                    st.session_state['api_key'] = credentials["api_key"]
                    st.experimental_rerun()  # Rerun to display main content
                    return
            st.error("Invalid credentials. Please try again.")



# Load client configuration from JSON file
with open("clients_config.json") as config_file:
    clients_config = json.load(config_file)

# Function to get client configuration
def get_client_config(client_id):
    default_config = {"name": "Default Academy", "logo": "https://path-to-default-logo.png", "theme_color": "#000000"}
    return clients_config.get(client_id, default_config)

# Simulate setting client_id after login
if 'client_id' not in st.session_state:
    # Example: Set this dynamically based on login, here setting a default for demonstration
    client_id = st.experimental_get_query_params().get("client_id", ["default"])[0]
    st.session_state['client_id'] = client_id

# Retrieve client configuration using session-stored client_id
client_config = get_client_config(st.session_state['client_id'])

# Display logo with smaller width and reduce spacing
st.image(client_config["logo"], width=120)  # Reduced width to 120 for better fit

# Display client-specific name with gradient background
st.markdown(f"""
    <div style="text-align: center; background: linear-gradient(180deg, #6A5ACD, #483D8B); padding: 5px 0;">
        <h2 style="margin: 0; font-size: 24px; color: white;">{client_config['name']}</h2>
    </div>
""", unsafe_allow_html=True)


# Function to fetch images based on topic and subtopics
def fetch_image(prompt):
    response = openai.Image.create(prompt=prompt, n=1, size="512x512")
    image_url = response['data'][0]['url']
    image_response = requests.get(image_url)
    return BytesIO(image_response.content)

# The remaining functions (e.g., `generate_question`, `create_quiz_document`, etc.) remain as they are.


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
        .option-card { 
            background-color: #E0E8F6; 
            padding: 20px; 
            margin: 10px; 
            border-radius: 10px; 
            text-align: center;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        }
        .option-card:hover { 
            background-color: #d1d9f5; 
            cursor: pointer; 
            transition: background-color 0.3s ease;
        }
        .stButton>button { background-color: #6A5ACD; color: white; border-radius: 8px; padding: 10px 20px; font-size: 18px; }
        .stButton>button:hover { background-color: #483D8B; }
        .stSidebar .sidebar-content { background: linear-gradient(180deg, #6A5ACD, #483D8B); color: white; }
        h1, h2, h3, h4 { color: #4B0082; }
        .center { text-align: center; }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.title("EduCreate Pro")
    task = st.sidebar.radio("Select Module", ["Home", "Create Educational Content", "Create Lesson Plan", "Student Assessment Assistant", "Personalized Learning Material", "Generate Image Based Questions"])

    # Logout functionality
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['school_id'] = None
        st.session_state['api_key'] = None
        st.experimental_rerun()

    # Home Page Layout with Cards
    if task == "Home":
        st.markdown("""
            <div style='text-align: center; font-size: 18px; color: #4B0082;'>
                Your all-in-one platform for creating educational content, lesson plans, and student assessments.
            </div>
        """, unsafe_allow_html=True)

        # Create a row of options with custom styled cards
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown('<div class="option-card">', unsafe_allow_html=True)
            st.subheader("Content Creator")
            st.write("Generate quizzes, sample papers, and assignments.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="option-card">', unsafe_allow_html=True)
            st.subheader("Lesson Planner")
            st.write("Create detailed lesson plans with learning objectives and materials.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            st.markdown('<div class="option-card">', unsafe_allow_html=True)
            st.subheader("Assessment Assistant")
            st.write("Generate comprehensive student assessments and progress reports.")
            st.markdown('</div>', unsafe_allow_html=True)

        col4, col5 = st.columns(2)

        with col4:
            st.markdown('<div class="option-card">', unsafe_allow_html=True)
            st.subheader("Personalized Learning Material")
            st.write("Generate learning material and assignment based on your assessment report.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col5:
            st.markdown('<div class="option-card">', unsafe_allow_html=True)
            st.subheader("Image Based Question Generator")
            st.write("Generate Image Based Quiz (MCQ, True/false, Yes/No type).")
            st.markdown('</div>', unsafe_allow_html=True)

        # Centered 'Get Started Today' button with message on click
        st.markdown('<div class="center">', unsafe_allow_html=True)
        if st.button("Get Started Today"):
            st.warning("Choose one task from the menu on the left to get started.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Section 1: Educational Content Creation
    elif task == "Create Educational Content":
        st.header("Educational Content Creation")
        
        # Collect basic information
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):")
        standard = st.text_input("Enter Standard/Class (e.g., Class 10):")
        topics = st.text_input("Enter Topics (comma-separated):")
        
        # Choose content type
        content_type = st.selectbox("Select Content Type", ["Quizzes", "Sample Paper", "Practice Questions", "Summary Notes", "Assignments"])

        # Collect details based on content type
        total_marks = st.number_input("Enter Total Marks", min_value=1)
        time_duration = st.text_input("Enter Time Duration (e.g., 60 minutes)")
        question_types = st.multiselect("Select Question Types", ["True/False", "Yes/No", "MCQs", "Very Short answers", "Short answers", "Long answers", "Very Long answers"])
        difficulty = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"])
        category = st.selectbox("Select Category", ["Value-based Questions", "Competency Questions", "Image-based Questions", "Paragraph-based Questions", "Mixed of your choice"])

        # Option to include solutions
        include_solutions = st.radio("Would you like to include solutions?", ["Yes", "No"])

        if st.button("Generate Educational Content"):
            content = generate_content(board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions == "Yes")
            st.write("### Generated Educational Content")
            st.write(content)
            
            # Save as Word document
            file_name = f"{content_type}_{standard}.docx"
            save_content_as_doc(content, file_name)
            
            # Download button for the document file
            with open(file_name, "rb") as file:
                st.download_button(label="Download Content as Document", data=file.read(), file_name=file_name)

    # Section 2: Lesson Plan Creation
    elif task == "Create Lesson Plan":
        st.header("Lesson Plan Creation")

        # Collect lesson plan details
        subject = st.text_input("Enter Subject:")
        grade = st.text_input("Enter Class/Grade:")
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):")
        duration = st.text_input("Enter Lesson Duration (e.g., 45 minutes, 1 hour):")
        topic = st.text_input("Enter Lesson Topic:")

        if st.button("Generate Lesson Plan"):
            lesson_plan = generate_lesson_plan(subject, grade, board, duration, topic)
            st.write("### Generated Lesson Plan")
            st.write(lesson_plan)
            
            # Save lesson plan as a Word document
            docx_file_name = f"Lesson_Plan_{subject}_{grade}.docx"
            save_content_as_doc(lesson_plan, docx_file_name)
            
            # Save lesson plan as a PDF
            pdf_file_name = f"Lesson_Plan_{subject}_{grade}.pdf"
            generate_pdf(lesson_plan, "Lesson Plan", pdf_file_name)
            
            # Download buttons for the lesson plan documents
            with open(docx_file_name, "rb") as docx_file:
                st.download_button(label="Download Lesson Plan as DOCX", data=docx_file.read(), file_name=docx_file_name)
                
            with open(pdf_file_name, "rb") as pdf_file:
                st.download_button(label="Download Lesson Plan as PDF", data=pdf_file.read(), file_name=pdf_file_name)

    # Section 3: Student Assessment Assistant
    elif task == "Student Assessment Assistant":
        st.header("Student Assessment Assistant")

        # Collect student information
        student_name = st.text_input("Enter Student Name:")
        student_id = st.text_input("Enter Student ID:")
        assessment_id = st.text_input("Enter Assessment ID:")
        class_name = st.text_input("Enter Class:")
        email_id = st.text_input("Enter Parent's Email ID:")

        # Upload Question Paper, Marking Scheme, and Answer Sheet (DOC format)
        question_paper = st.file_uploader("Upload Question Paper (DOCX)", type=["docx"])
        marking_scheme = st.file_uploader("Upload Marking Scheme (DOCX)", type=["docx"])
        answer_sheet = st.file_uploader("Upload Student's Answer Sheet (DOCX)", type=["docx"])

        # Generate Assessment Report and Email PDF
        if st.button("Generate and Send PDF Report"):
            if student_id and assessment_id and email_id and question_paper and marking_scheme and answer_sheet:
                # Read DOC files
                question_paper_content = read_docx(question_paper)
                marking_scheme_content = read_docx(marking_scheme)
                answer_sheet_content = read_docx(answer_sheet)

                # Enhanced GPT-4 prompt with explicit structure for the report
                prompt = f"""
                You are an educational assessment assistant. Using the question paper, marking scheme, and answer sheet, evaluate the student's answers.

                Student Name: {student_name}
                Student ID: {student_id}
                Class: {class_name}
                Assessment ID: {assessment_id}

                Question Paper:
                {question_paper_content}

                Marking Scheme:
                {marking_scheme_content}

                Student's Answer Sheet:
                {answer_sheet_content}

                Please provide the following in the assessment report:
                1. Question Analysis - Each question should include:
                    - Topic
                    - Subtopic
                    - Question Number
                    - Score for the answer based on accuracy and relevance
                    - Concept Clarity (Yes/No)
                    - Feedback and Suggestions

                2. Summary Report - Include:
                    - Final Score
                    - Grade
                    - Areas of Strength
                    - Areas for Improvement
                    - Final Remarks
                """
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}]
                )
                report = response['choices'][0]['message']['content']

                # Generate PDF
                file_name = f"assessment_report_{student_id}.pdf"
                generate_pdf(report, "Assessment Report", file_name)
                
                st.success(f"PDF report generated: {file_name}")

                # Display and download report
                st.write("### Assessment Report")
                st.write(report)
                with open(file_name, "rb") as file:
                    st.download_button(label="Download Report as PDF", data=file.read(), file_name=file_name)

                # Send report via email
                subject = f"Assessment Report for Student {student_name}"
                body = "Please find attached the student's assessment report."
                send_email_with_pdf(email_id, subject, body, file_name)
            else:
                st.error("Please provide all required inputs.")
    

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
       # st.write(f"Welcome, {st.session_state['school_id']}")
       # API Key: {st.session_state['api_key']}
        openai.api_key = st.session_state['api_key']  # Set OpenAI key
        main_app()
    else:
        login_page()  # Show login page if not logged in
    

if __name__ == "__main__":
    main()
  
