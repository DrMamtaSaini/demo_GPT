import streamlit as st
import openai
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
import json
from docx import Document
from docx.shared import Inches
from io import BytesIO
import requests
from PyPDF2 import PdfReader
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import tempfile
from pathlib import Path
import tempfile
from pathlib import Path

from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO
from docx import Document
from docx.shared import Inches
import tempfile

# Set OpenAI API key
openai.api_key = st.secrets["api_key"]
# Load school credentials from Streamlit secrets
SCHOOL_CREDENTIALS = st.secrets["scho_credentials"]

# Load client configuration from JSON file
try:
    with open("clients_config.json") as config_file:
        clients_config = json.load(config_file)
except Exception as e:
    st.error(f"ERROR - Unable to load clients_config.json: {e}")

def get_client_config(client_id):
    """Retrieves client configuration based on client_id or returns None if not found."""
    return clients_config.get(client_id, None)

def login_page():
    """Displays the login page and sets session states on successful login."""
    st.title("EduCreate Pro Login")
    
    # Input fields for username and password
    school_username = st.text_input("Username", placeholder="Enter username", key="username_input")
    school_password = st.text_input("Password", type="password", placeholder="Enter password", key="password_input")

    if st.button("Login", help="Double Click to log in"):
        # Check credentials against stored values
        for school_id, credentials in SCHOOL_CREDENTIALS.items():
            if school_username == credentials["username"] and school_password == credentials["password"]:
                # Set session state variables on successful login
                st.session_state['logged_in'] = True
                st.session_state['client_id'] = school_id
                
                # Load client config immediately after successful login
                client_config = get_client_config(school_id)
                
                if client_config:
                    st.session_state['client_config'] = client_config
                else:
                    st.error("Client configuration not found. Please log in again.")
                    st.session_state['logged_in'] = False
                    return
        
        # If no valid credentials found
        if not st.session_state.get("logged_in"):
            st.error("Invalid credentials. Please try again.")

        
# Function to fetch images based on topic and subtopics
import openai
import requests
import time
from io import BytesIO

def fetch_image(prompt, retries=5):
    for attempt in range(retries):
        try:
            # Attempt to create an image with OpenAI's API
            response = openai.Image.create(prompt=prompt, n=1, size="512x512")
            image_url = response['data'][0]['url']
            
            # Fetch the image data from the URL
            image_response = requests.get(image_url)
            image_response.raise_for_status()  # Ensure the request was successful
            return BytesIO(image_response.content)  # Return image data in BytesIO format
            
        except openai.error.RateLimitError:
            # Handle rate limit error with exponential backoff
            if attempt < retries - 1:  # Only retry if it's not the last attempt
                wait_time = 2 ** attempt  # Exponential backoff time
                print(f"Rate limit reached. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Rate limit exceeded. Unable to fetch image.")
                return None  # Return None to handle gracefully in the main function
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch image from URL: {e}")
            return None
            
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None


# The remaining functions (e.g., `generate_question`, `create_quiz_document`, etc.) remain as they are.

# Function to generate question using GPT based on input
def generate_question(topic, class_level, question_type, subtopic):
    prompt = f"Generate a {question_type} question on the topic '{topic}' for {class_level} on the subtopic '{subtopic}'. Include a question text and answer options."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']








# Function to generate a quiz document
def generate_question_and_options(topic, class_level, question_type, subtopic):
    prompt = (
        f"Create a {question_type} question about {subtopic} for a {class_level} level quiz on {topic}. "
        f"Include four answer choices labeled A, B, C, and D, and indicate the correct answer."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    
    full_text = response.choices[0].message['content'].strip()
    lines = full_text.split("\n")
    question = lines[0]
    options = lines[1:5]
    correct_answer = lines[5] if len(lines) > 5 else "Correct Answer Not Provided"

    return question, options, correct_answer

def create_quiz_document(topic, subject, class_level, max_marks, duration, num_questions, question_type, include_answers, file_path):
    document = Document()

    # Centered main headings
    document.add_heading('Quiz', level=1).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    document.add_heading(f'Grade: {class_level}', level=2).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    document.add_heading(f'Subject: {subject}', level=2).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    document.add_heading(f'Topic: {topic}', level=2).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    document.add_paragraph("\n")

    # Duration and Max Marks, centered
    details_paragraph = document.add_paragraph()
    details_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    details_paragraph.add_run(f'Duration: {duration}    Max. Marks: {max_marks}').bold = True

    # Define subtopics based on the topic
    subtopics = ["flowering plants", "trees", "herbs"] if topic == "Plants" else ["mammals", "birds", "reptiles"]

    answers = []

    # Loop to create questions with dynamically generated content and images
    for i in range(num_questions):
        subtopic = subtopics[i % len(subtopics)]
        question_text, options, correct_answer = generate_question_and_options(topic, class_level, question_type, subtopic)

        # Add question
        document.add_paragraph(f'Q{i+1}: {question_text}')
        for option in options:
            document.add_paragraph(option)
        
        # Store correct answer for answer section if include_answers is True
        answers.append(f'Q{i+1}: {correct_answer}')

        # Generate image for each question
        image_prompt = f"Image of {subtopic} related to {topic}"
        image_data = fetch_image(image_prompt)
        if image_data:
            document.add_picture(image_data, width=Inches(2))

        document.add_paragraph("\n")  # Spacing after each question

    # Add answer section
    if include_answers:
        document.add_paragraph("\nAnswers:\n")
        for answer in answers:
            document.add_paragraph(answer)
    else:
        document.add_paragraph("\nAnswers:\n")
        for i in range(num_questions):
            document.add_paragraph(f'Q{i+1}: ________________')

    # Save the document
    document.save(file_path)




def create_quiz1_document(topic, subject, class_level, max_marks, duration, num_questions, question_type, include_answers, include_images, file_path):
    document = Document()

    # Centered main title
    document.add_heading('Quiz', level=1).alignment = 1  # Center align
    document.add_heading(f'Class: {class_level}', level=2).alignment = 1
    document.add_heading(f'Subject: {subject}', level=2).alignment = 1
    document.add_heading(f'Topic: {topic}', level=2).alignment = 1
    document.add_paragraph("\n")  # Blank line for spacing

    # Add Duration and Max Marks on the same line, centered
    details_paragraph = document.add_paragraph()
    details_paragraph.alignment = 1  # Center align
    details_paragraph.add_run(f'Duration: {duration}').bold = True
    details_paragraph.add_run("    ")  # Add space between Duration and Max Marks
    details_paragraph.add_run(f'Max. Marks: {max_marks}').bold = True
    document.add_paragraph("\n")  # Extra line for spacing

    # Loop to add questions and images
    for i in range(num_questions):
        # Placeholder question generation
        question_text = f"Sample question {i+1} about {topic}."
        
        # Add question to the document
        document.add_paragraph(f'Q{i+1}: {question_text}')
        
        # Conditionally add image if include_images is True
        if include_images:
            image_prompt = f"Image of {topic} for {class_level} related to {subject}"
            image_data = fetch_image(image_prompt)  # Assuming fetch_image is defined elsewhere
            if image_data:
                document.add_picture(image_data, width=Inches(2))
        
        # Add answer options based on question type
        if question_type == "MCQ":
            options = ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"]
            for option in options:
                document.add_paragraph(option)
        elif question_type == "true/false":
            document.add_paragraph("A) True")
            document.add_paragraph("B) False")
        elif question_type == "yes/no":
            document.add_paragraph("A) Yes")
            document.add_paragraph("B) No")
        
        # Add correct answer if include_answers is True
        if include_answers:
            correct_answer = "B) Sample Answer"  # Placeholder, replace with actual logic
            document.add_paragraph(f"Answer: {correct_answer}")
        
        document.add_paragraph("\n")  # Add spacing after each question

    # Add an answer section if answers are not included inline
    if not include_answers:
        document.add_paragraph("\nAnswers:\n")
        for i in range(num_questions):
            document.add_paragraph(f'Q{i+1}: ________________')

    # Save the document to the specified file path
    document.save(file_path)



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

def generatereport_pdf(content, title, filename, student_name, student_id, assessment_id, exam_type, subject):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title - Assessment Report
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Assessment Report", ln=True, align="C")

    # Centered Exam Type and Subject
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Exam Type: {exam_type}", ln=True, align="C")
    pdf.cell(0, 10, f"Subject: {subject}", ln=True, align="C")
    pdf.ln(10)  # Blank line for spacing

    # Detailed Summary Heading
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Detailed Summary Report", ln=True, align="L")
    pdf.ln(5)

    # Student information
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Student Name: {student_name}", ln=True)
    pdf.cell(0, 10, f"Student ID: {student_id}", ln=True)
    pdf.cell(0, 10, f"Assessment ID: {assessment_id}", ln=True)
    pdf.ln(10)

    # Add the report content
    pdf.multi_cell(0, 10, content)
    
    # Save the PDF
    pdf.output(filename)


# Function to send an email with PDF attachment
def send_email_with_pdf(to_email, subject, body, file_name):
    from_email = st.secrets["email"]
    password = st.secrets["app_password"]
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

import openai
from docx import Document
import re

def read_docx(file):
    doc = Document(file)
    full_text = "\n".join([repr(para.text) for para in doc.paragraphs])  # Use repr to show hidden characters
    print("DEBUG - Full Document Content with Hidden Characters:\n", full_text)  # Show all text details
    return full_text

def extract_weak_topics(assessment_content):
    """Uses generative AI to identify weak areas in the assessment content."""
    prompt = f"""
    Analyze the following assessment report content. Identify and list all topics and subtopics where 'Concept Clarity' is marked as 'No'. 
    Provide these as a list of weak areas based on the assessment.

    Assessment Content:
    {assessment_content}
    
    List only the topics and subtopics with low concept clarity.
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    
    weak_topics = response['choices'][0]['message']['content']
    return weak_topics.split("\n")

def generate_personalized_material(weak_topics):
    """Generates learning material for the identified weak topics using OpenAI."""
    prompt = f"Create personalized learning material covering the following topics: {', '.join(weak_topics)}. Provide explanations and examples."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

def generate_personalized_assignment(weak_topics):
    """Generates an assignment for the identified weak topics using OpenAI."""
    prompt = f"Create an assignment based on the following topics for practice: {', '.join(weak_topics)}. Include questions that reinforce the concepts."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to send an email with attachments
def send_email_with_attachments(to_email, subject, body, attachments):
    """Sends an email with multiple attachments to the specified email address."""


    
    from_email = st.secrets["email"]
    password = st.secrets["app_password"]
    
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach each file in the attachments list
    for file_path in attachments:
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {file_path}")
            msg.attach(part)
    
    # Send the email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        st.success(f"Email sent to {to_email} with attached PDF reports!")
    except Exception as e:
        st.error(f"Error sending email: {e}")



def generate_pdf(content, title, file_name):
    # Initialize PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Set title with error handling for encoding
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title.encode("latin-1", "replace").decode("latin-1"), ln=True, align='C')
    pdf.ln(10)
    
    # Add content with encoding error handling
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        sanitized_line = line.encode("latin-1", "replace").decode("latin-1")
        pdf.cell(200, 10, sanitized_line, ln=True)
    
    # Output PDF to file
    pdf.output(file_name)


def save_contentttttt_as_doc(content, file_name):
    doc = Document()
    for line in content.split("\n"):
        doc.add_paragraph(line)
    doc.save(file_name)

from docx import Document

def save_content_as_doc(content, file_name_docx):
    # Check if content is a tuple (i.e., content and image data are both returned)
    if isinstance(content, tuple):
        content, _ = content  # Extract content only, ignore image data
    
    document = Document()
    
    # Add each line of the content to the document
    for line in content.split("\n"):
        document.add_paragraph(line)
    
    # Save the document as DOCX
    document.save(file_name_docx)



# Function to sanitize text by replacing unsupported characters
def sanitize_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_content(board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions):
    prompt = f"""
    You are an expert educational content creator. Create {content_type} for the {board} board, {standard} class.
    Topics to cover: {topics}. The content should be designed for a total of {total_marks} marks and a time duration of {time_duration}.
    Include question types such as {', '.join(question_types)}, with an overall difficulty level of {difficulty}.
    """
    
    # Modify the prompt based on the category to create specific types of questions
    if category == "Value-based Questions":
        prompt += """
        Generate questions that explore students' understanding of values related to the topic. Questions should prompt them to reflect on ethical, social, or personal values connected to the subject. Provide scenarios or real-life situations where students can express how they would apply these values.
        """
    elif category == "Competency Questions":
        prompt += """
        Create questions that test the students' practical knowledge and skills on the topic. Include questions that require problem-solving, critical thinking, and application of learned concepts. Provide real-world scenarios where students can demonstrate their competencies.
        """
    elif category == "Image-based Questions":
        prompt += """
        Design questions based on an image related to the topic. For example, describe an image and ask students to observe details, make inferences, or answer questions based on what they see. Ensure the image is relevant to the topic and prompts critical thinking or observational skills.
        """
        
        # Call an image generation function to fetch a relevant image for this category
        image_prompt = f"Generate an educational image related to {topics} for {standard} level."
        image_data = fetch_image(image_prompt)  # Assuming fetch_image is defined elsewhere

        if image_data:
            # Return the generated content along with the image if available
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}]
            )
            content = response['choices'][0]['message']['content']
            return content, image_data  # Return both content and image data
        else:
            return "Image generation failed.", None  # Handle the case where image generation fails

    elif category == "Paragraph-based Questions":
        prompt += """
        Provide a short paragraph about the topic and ask questions that test comprehension and understanding. The paragraph should contain key information related to the topic, and questions should encourage students to recall facts, infer meanings, and explain concepts based on the paragraph.
        """
    elif category == "Mixed of your choice":
        prompt += """
        Generate a mix of questions including competency-based, value-based, image-based, and paragraph-based questions to give a comprehensive understanding of the topic.
        """
    
    # Include solutions if requested
    if include_solutions:
        prompt += " Include detailed solutions and explanations for each question."
    else:
        prompt += " Only provide the questions without solutions."
    
    # Call OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    
    return response['choices'][0]['message']['content'], None  # Return content without an image if not image-based

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
    client_config = st.session_state.get('client_config')
    
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

    client_config = get_client_config(st.session_state['client_id'])

    st.image(client_config["logo"], width=120)
    st.markdown(f"""
        <div style="text-align: center; background: linear-gradient(180deg, #6A5ACD, {client_config['theme_color']}); padding: 5px 0;">
            <h2 style="margin: 0; font-size: 24px; color: white;">{client_config['name']}</h2>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.title("EduCreate Pro")
    task = st.sidebar.radio("Select Module", ["Home", "Create Educational Content", "Create Lesson Plan", "Student Assessment Assistant", "Generate Image Based Questions"])

    if task == "Home":
       
        st.markdown("""
        <div style='text-align: center; font-size: 18px; color: #4B0082; padding: 20px 0;'>
            Welcome to your all-in-one platform for creating educational content, lesson plans, and student assessments.
        </div>
        """, unsafe_allow_html=True)

        # Creating a row of options with custom styled cards
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div class="option-card">
                <h3 style='color: #4B0082; text-align: center;'>Content Creator</h3>
                <p style='text-align: center;'>Generate quizzes, sample papers, and assignments for students.</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="option-card">
                <h3 style='color: #4B0082; text-align: center;'>Lesson Planner</h3>
                <p style='text-align: center;'>Create detailed lesson plans with objectives and resources.</p>
            </div>
            """, unsafe_allow_html=True)

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("""
            <div class="option-card">
                <h3 style='color: #4B0082; text-align: center;'>Assessment Assistant</h3>
                <p style='text-align: center;'>Generate comprehensive student assessments and progress reports.</p>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown("""
            <div class="option-card">
                <h3 style='color: #4B0082; text-align: center;'>Image-Based Question Generator</h3>
                <p style='text-align: center;'>Generate image-based quizzes (MCQ, True/False, Yes/No).</p>
            </div>
            """, unsafe_allow_html=True)

        # Centered 'Get Started Today' button with a message on click
        st.markdown("<div class='center' style='padding: 20px;'>", unsafe_allow_html=True)
        if st.button("Get Started Today"):
            st.session_state['task'] = "Create Educational Content"  # Set the task to "Create Educational Content"
        st.markdown("</div>", unsafe_allow_html=True)
   
        
    # The rest of the application follows the task selected in session state
    elif task == "Create Educational Content":
        st.header("Educational Content Creation")
    
        # Collect basic information
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):", key="board_input")
        standard = st.text_input("Enter Standard/Class (e.g., Class 10):", key="standard_input")
        topics = st.text_input("Enter Topics (comma-separated):", key="topics_input")
        
        # Choose content type
        content_type = st.selectbox("Select Content Type", ["Quizzes", "Sample Paper", "Practice Questions", "Summary Notes", "Assignments"], key="content_type_select")

        # Collect details based on content type
        total_marks = st.number_input("Enter Total Marks", min_value=1, key="total_marks_input")
        time_duration = st.text_input("Enter Time Duration (e.g., 60 minutes)", key="time_duration_input")
        question_types = st.multiselect("Select Question Types", ["True/False", "Yes/No", "MCQs", "Very Short answers", "Short answers", "Long answers", "Very Long answers"], key="question_types_multiselect")
        difficulty = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"], key="difficulty_select")
        category = st.selectbox("Select Category", ["Value-based Questions", "Competency Questions", "Image-based Questions", "Paragraph-based Questions", "Mixed of your choice"], key="category_select")

        # Option to include solutions
        include_solutions = st.radio("Would you like to include solutions?", ["Yes", "No"], key="include_solutions_radio")

        if st.button("Generate Educational Content"):
            content,image_data = generate_content(board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions == "Yes")
            st.write("### Generated Educational Content")
            st.write(content)
            # Display the image if image data is available
            if image_data:
                st.image(image_data, caption="Generated Image for Image-based Question")
            # Save as Word document
            file_name_docx = f"{content_type}_{standard}.docx"
            save_content_as_doc(content, file_name_docx)
            
            # Save as PDF document
            file_name_pdf = f"{content_type}_{standard}.pdf"
            generate_pdf(content, f"{content_type} for {standard}", file_name_pdf)
            
            # Download button for the DOCX file
            with open(file_name_docx, "rb") as file:
                st.download_button(label="Download Content as DOCX", data=file.read(), file_name=file_name_docx)
            
            # Download button for the PDF file
            with open(file_name_pdf, "rb") as file:
                st.download_button(label="Download Content as PDF", data=file.read(), file_name=file_name_pdf)

  

    elif task == "Create Lesson Plan":
        st.header("Lesson Plan Creation")
    
        # Collect lesson plan details
        subject = st.text_input("Enter Subject:", key="subject_input")
        grade = st.text_input("Enter Class/Grade:", key="grade_input")
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):", key="lesson_board_input")
        duration = st.text_input("Enter Lesson Duration (e.g., 45 minutes, 1 hour):", key="duration_input")
        topic = st.text_input("Enter Lesson Topic:", key="topic_input")
        
        # Generate lesson plan
        if st.button("Generate Lesson Plan"):
            lesson_plan = generate_lesson_plan(subject, grade, board, duration, topic)
            
            st.write("### Generated Lesson Plan")
            st.write(lesson_plan)
            
            # Save as Word document
            file_name_docx = f"{subject}_{grade}.docx"
            save_content_as_doc(lesson_plan, file_name_docx)
            
            # Save as PDF document
            file_name_pdf = f"{subject}_{grade}.pdf"
            generate_pdf(lesson_plan, f"Lesson Plan: {subject} - Grade {grade}", file_name_pdf)
            
            # Download button for the DOCX file
            with open(file_name_docx, "rb") as file:
                st.download_button(label="Download Lesson Plan as DOCX", data=file.read(), file_name=file_name_docx)
            
            # Download button for the PDF file
            with open(file_name_pdf, "rb") as file:
                st.download_button(label="Download Lesson Plan as PDF", data=file.read(), file_name=file_name_pdf)

    elif task == "Student Assessment Assistant":
        st.header("Student Assessment Assistant")

        # Collect student information with unique labels for each field
        student_name = st.text_input("Enter Student Name", key="student_name_input")
        student_id = st.text_input("Enter Student ID", key="student_id_input")
        assessment_id = st.text_input("Enter Assessment ID", key="assessment_id_input")
        class_name = st.text_input("Enter Class", key="class_name_input")
        email_id = st.text_input("Enter Parent's Email ID", key="email_id_input")
        # Add new input fields for Exam Type and Subject
        exam_type = st.text_input("Enter Exam Type (e.g., Midterm, Final Exam)", key="exam_type_input")
        subject = st.text_input("Enter Subject", key="subject_input")


        # Upload Question Paper, Marking Scheme, and Answer Sheet (DOC format)
        question_paper = st.file_uploader("Upload Question Paper (DOCX)", type=["docx"], key="question_paper_uploader")
        marking_scheme = st.file_uploader("Upload Marking Scheme (DOCX)", type=["docx"], key="marking_scheme_uploader")
        answer_sheet = st.file_uploader("Upload Student's Answer Sheet (DOCX)", type=["docx"], key="answer_sheet_uploader")

        if st.button("Generate and Send Reports"):
            if student_id and assessment_id and email_id and question_paper and marking_scheme and answer_sheet:
                # Read DOC files
                question_paper_content = read_docx(question_paper)
                marking_scheme_content = read_docx(marking_scheme)
                answer_sheet_content = read_docx(answer_sheet)

                # Generate the assessment report
                prompt = f"""
You are an educational assessment assistant. Using the question paper, marking scheme, and answer sheet, evaluate the student's answers.

Please generate a well-formatted assessment report without any special characters like asterisks (*) for emphasis or lists.

Include the following sections in the report:

1. **Question Analysis** - Each question should include:
    - Topic
    - Subtopic
    - Question Number
    - Score for the answer based on accuracy and relevance
    - Concept Clarity (Yes/No)
    - Feedback and Suggestions

2. **Summary Report** - Include:
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
                st.write("## Assessment Report")
                st.write(report)

                # Extract weak topics from the report using generative AI
                weak_topics_prompt = f"Identify and list topics and subtopics from the following assessment report where 'Concept Clarity' is marked as 'No'.\n\nAssessment Report:\n{report}"
                weak_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": weak_topics_prompt}]
                )
                weak_topics = weak_response['choices'][0]['message']['content'].strip().split("\n")

                # Generate personalized learning material and assignment
                learning_material_prompt = f"Create personalized learning material covering the following weak areas: {', '.join(weak_topics)}. Include explanations, examples, and practice questions."
                assignment_prompt = f"Create an assignment based on the following weak areas for the student to improve: {', '.join(weak_topics)}. Include questions that reinforce concepts with solutions."

                learning_material_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": learning_material_prompt}]
                )
                assignment_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": assignment_prompt}]
                )

                learning_material = learning_material_response['choices'][0]['message']['content']
                assignment = assignment_response['choices'][0]['message']['content']
                st.write("learning_material")
                st.write(learning_material)
                st.write("assignment_response")
                st.write(assignment)
                
                assessment_report_pdf = f"assessment_report_{student_id}.pdf"
                generatereport_pdf(report, "Assessment Report", assessment_report_pdf, student_name, student_id, assessment_id, exam_type, subject)



                learning_material_pdf = f"learning_material_{student_id}.pdf"
                generate_pdf(learning_material, "Personalized Learning Material", learning_material_pdf)

                assignment_pdf = f"assignment_{student_id}.pdf"
                generate_pdf(assignment, "Personalized Assignment", assignment_pdf)

                # Store file paths for download
                st.session_state['assessment_report_pdf'] = assessment_report_pdf
                st.session_state['learning_material_pdf'] = learning_material_pdf
                st.session_state['assignment_pdf'] = assignment_pdf

                st.success("All reports generated successfully and are ready for download.")

                # Email the PDFs to the parent
                subject = f"Assessment Reports for {student_name}"
                body = f"""
Dear Parent,

We hope this message finds you well.

We have recently conducted an assessment for your child, {student_name}, and are pleased to share the results and resources to support their academic journey. In this email, you will find three attached documents:

1. **Assessment Report**: A comprehensive evaluation of {student_name}'s performance, highlighting areas of strength and opportunities for improvement.
2. **Personalized Learning Material**: Additional resources tailored to help reinforce understanding in specific areas where further support may be beneficial.
3. **Practice Assignment**: A set of exercises designed to help {student_name} practice and solidify their learning in identified focus areas.

Thank you for your continued support and engagement in {student_name}'s education.

Warm regards,
Your School
                """
                attachments = [assessment_report_pdf, learning_material_pdf, assignment_pdf]
                send_email_with_attachments(email_id, subject, body, attachments)
            else:
                st.error("Please provide all required inputs.")

        # Display download buttons for generated reports
        if 'assessment_report_pdf' in st.session_state:
            st.write("### Assessment Report")
            with open(st.session_state['assessment_report_pdf'], "rb") as file:
                st.download_button(label="Download Assessment Report as PDF", data=file.read(), file_name=st.session_state['assessment_report_pdf'])

        if 'learning_material_pdf' in st.session_state:
            st.write("### Personalized Learning Material")
            with open(st.session_state['learning_material_pdf'], "rb") as file:
                st.download_button(label="Download Learning Material as PDF", data=file.read(), file_name=st.session_state['learning_material_pdf'])

        if 'assignment_pdf' in st.session_state:
            st.write("### Personalized Assignment")
            with open(st.session_state['assignment_pdf'], "rb") as file:
                st.download_button(label="Download Assignment as PDF", data=file.read(), file_name=st.session_state['assignment_pdf'])
    
    
    elif task == "Generate Image Based Questions":
        
        st.header("Generate Image Based Questions")
        topic = st.text_input("Select a topic (e.g., Plants, Animals, Geography, Famous Landmarks):", key="image_topic_input")
        subject = st.text_input("Enter the subject (e.g., Science, Geography):", key="subject_input")
        class_level = st.text_input("Select a class level (e.g., Grade 1, Grade 2, Grade 3):", key="class_level_input")
        max_marks = st.text_input("Enter maximum marks:", key="max_marks_input")
        duration = st.text_input("Enter duration (e.g., 1 hour):", key="duration_input")
        num_questions = st.number_input("Enter the number of questions (minimum 5):", min_value=5, key="num_questions_input")
        question_type = st.selectbox("Choose question type", ["MCQ", "true/false", "yes/no"], key="question_type_select")

        if st.button("Generate Quiz Document"):
            if num_questions < 5:
                st.warning("Minimum number of questions is 5. Setting to 5.")
            num_questions = 5

        # Create temporary files for both versions of the document
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file_without_answers, \
                tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file_with_answers:

                quiz_filename_without_answers = tmp_file_without_answers.name
                quiz_filename_with_answers = tmp_file_with_answers.name

            # Generate the quiz document without answers
            create_quiz_document(topic, subject, class_level, max_marks, duration, num_questions, question_type,
                                 include_answers=False, file_path=quiz_filename_without_answers)

            # Generate the quiz document with answers
            create_quiz_document(topic, subject, class_level, max_marks, duration, num_questions, question_type,
                                 include_answers=True, file_path=quiz_filename_with_answers)

            # Store paths in session state for persistent download links
            st.session_state["quiz_filename_without_answers"] = quiz_filename_without_answers
            st.session_state["quiz_filename_with_answers"] = quiz_filename_with_answers

            st.success("Quiz documents generated successfully! Use the buttons below to download either version.")

    # Download buttons for both versions
            if "quiz_filename_without_answers" in st.session_state and "quiz_filename_with_answers" in st.session_state:
                with open(st.session_state["quiz_filename_without_answers"], "rb") as file:
                    st.download_button(label="Download Quiz Document (without answers)", data=file.read(),
                               file_name=Path(st.session_state["quiz_filename_without_answers"]).name)

                with open(st.session_state["quiz_filename_with_answers"], "rb") as file:
                    st.download_button(label="Download Quiz Document (with answers)", data=file.read(),
                               file_name=Path(st.session_state["quiz_filename_with_answers"]).name)



# Define main control function
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        main_app()
    else:
        login_page()

if __name__ == "__main__":
    main()

