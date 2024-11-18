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

import streamlit as st
import openai
import json
import requests
import time
from io import BytesIO
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import openai
from docx import Document
import re
from docx import Document
from docx.shared import Inches
import matplotlib.pyplot as plt
import numpy as np

# Set OpenAI API key securely from Streamlit secrets
try:
    openai.api_key = st.secrets["api_key"]
except KeyError:
    st.error("API Key is missing in Streamlit secrets. Please add it and restart the app.")

# Load school credentials securely from Streamlit secrets
try:
    SCHOOL_CREDENTIALS = st.secrets["scho_credentials"]
except KeyError:
    st.error("School credentials are missing in Streamlit secrets. Please add them to proceed.")

# Load client configuration from JSON file with error handling
clients_config = {}
try:
    with open("clients_config.json") as config_file:
        clients_config = json.load(config_file)
except FileNotFoundError:
    st.warning("Configuration file 'clients_config.json' not found. Default settings will be used.")
except json.JSONDecodeError:
    st.error("Configuration file 'clients_config.json' is invalid. Please check the file format.")
except Exception as e:
    st.error(f"Unexpected error loading configuration: {e}")

# Helper function to retrieve client configuration based on client_id
def get_client_config(client_id):
    """Retrieves client configuration based on client_id. Returns None if not found."""
    return clients_config.get(client_id)

# Login page function with added error handling
def login_page():
    """Displays login page, authenticates users, and sets session states on successful login."""
    st.title("EduCreate Pro Login")
    
    # Collect username and password with placeholder values
    school_username = st.text_input("Username", placeholder="Enter username", key="username_input")
    school_password = st.text_input("Password", type="password", placeholder="Enter password", key="password_input")

    if st.button("Login", help="Click twice if needed to confirm login"):
        # Initialize login status to False, will update on successful authentication
        st.session_state['logged_in'] = False

        # Validate credentials against stored values in Streamlit secrets
        for school_id, credentials in SCHOOL_CREDENTIALS.items():
            if school_username == credentials["username"] and school_password == credentials["password"]:
                # Successful login: Set session state and retrieve client configuration
                st.session_state['logged_in'] = True
                st.session_state['client_id'] = school_id
                st.session_state['page'] = 'main'
                
                # Attempt to load client configuration after successful login
                client_config = get_client_config(school_id)
                if client_config:
                    st.session_state['client_config'] = client_config
                    st.success("Login successful!")
                else:
                    st.error("Client configuration not found. Please contact support.")
                break
        else:
            # Invalid credentials feedback
            st.error("Invalid credentials. Please try again or contact your administrator.")

        # Confirm if no valid credentials found in SCHOOL_CREDENTIALS
        if not st.session_state.get("logged_in"):
            st.warning("Please ensure your credentials are correct. Try again.")

def logout():
    """Handle user logout by resetting session state variables."""
    st.session_state['logged_in'] = False
    st.session_state['page'] = 'home'



def fetch_image(prompt, retries=5):
    """
    Fetches an image from the OpenAI API based on the given prompt.
    Includes retry logic for handling rate limits and network errors.
    
    Args:
        prompt (str): Text prompt for image generation.
        retries (int): Number of retry attempts for rate limit or network issues.
    
    Returns:
        BytesIO: In-memory image data if successful, None otherwise.
    """
    for attempt in range(retries):
        try:
            # Request image generation from OpenAI
            response = openai.Image.create(prompt=prompt, n=1, size="512x512")
            image_url = response['data'][0]['url']
            
            # Attempt to fetch the image from the URL provided by OpenAI
            image_response = requests.get(image_url)
            image_response.raise_for_status()  # Ensure the request was successful
            return BytesIO(image_response.content)  # Return image as BytesIO for easy handling
            
        except openai.error.RateLimitError:
            # Handle rate limit by retrying with exponential backoff
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff for retries
                st.warning(f"Rate limit reached. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                st.error("Rate limit exceeded. Unable to fetch image after multiple attempts.")
                return None  # Return None to gracefully handle in the main app

        except requests.exceptions.RequestException as e:
            st.error(f"Network error while fetching image: {e}")
            return None  # Return None on network failure to allow error handling in the calling function

        except Exception as e:
            st.error(f"Unexpected error fetching image: {e}")
            return None  # Return None for unexpected errors
            
    # Fallback if all retries fail
    st.error("Failed to fetch image after multiple attempts.")
    return None

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



def create_quiz_document(topic, subject, class_level, max_marks, duration, num_questions, question_type, include_answers, file_path):
    """
    Creates a quiz document with questions and optional answers based on input parameters.
    
    Args:
        topic (str): Topic of the quiz.
        subject (str): Subject of the quiz.
        class_level (str): Grade or class level.
        max_marks (int): Maximum marks for the quiz.
        duration (str): Duration of the quiz.
        num_questions (int): Number of questions to include.
        question_type (str): Type of questions (e.g., MCQ, True/False).
        include_answers (bool): Whether to include answers in the document.
        file_path (str): File path to save the document.
    """
    try:
        document = Document()

        # Centered title and details
        document.add_heading('Quiz', level=1).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        document.add_heading(f'Grade: {class_level}', level=2).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        document.add_heading(f'Subject: {subject}', level=2).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        document.add_heading(f'Topic: {topic}', level=2).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        document.add_paragraph("\n")

        # Duration and Marks information
        details_paragraph = document.add_paragraph()
        details_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        details_paragraph.add_run(f'Duration: {duration}    Max. Marks: {max_marks}').bold = True

        # Initialize list to store correct answers if required
        answers = []
        
        for i in range(num_questions):
            # Generate question text and options
            subtopic = f"subtopic_{i % 3 + 1}"  # Placeholder subtopics
            question_text, options, correct_answer = generate_question_and_options(topic, class_level, question_type, subtopic)
            document.add_paragraph(f'Q{i+1}: {question_text}')
            
            # Add each option
            for option in options:
                document.add_paragraph(option)
                
            # Save correct answer if including answers
            if include_answers:
                answers.append(f'Q{i+1}: {correct_answer}')

            # Fetch and add an image if applicable
            image_prompt = f"Image of {subtopic} related to {topic}"
            image_data = fetch_image(image_prompt)
            if image_data:
                document.add_picture(image_data, width=Inches(2))
                
            document.add_paragraph("\n")  # Space between questions

        # Add answers at the end if include_answers is set to True
        if include_answers:
            document.add_paragraph("\nAnswers:\n")
            for answer in answers:
                document.add_paragraph(answer)
        else:
            document.add_paragraph("\nAnswers:\n")
            for i in range(num_questions):
                document.add_paragraph(f'Q{i+1}: ________________')

        # Save document with error handling
        document.save(file_path)
        st.success(f"Quiz document saved successfully as {file_path}")
        
    except Exception as e:
        st.error(f"Error generating quiz document: {e}")


# Function to generate a PDF file for reports



def generate_pdf(content, title, file_name):
    """
    Generates a PDF report with the provided content.
    
    Args:
        content (str): The text content to include in the PDF.
        title (str): The title for the PDF report.
        file_name (str): The file path to save the PDF.
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Title with encoding handling
        pdf.set_font("Arial", "B", 16)
        title_sanitized = sanitize_text(title)
        pdf.cell(0, 10, title_sanitized, ln=True, align='C')
        pdf.ln(10)
        
        # Content with encoding handling
        pdf.set_font("Arial", size=12)
        for line in content.split('\n'):
            pdf.cell(0, 10, sanitize_text(line), ln=True)
        
        # Save the PDF file
        pdf.output(file_name)
        st.success(f"PDF generated successfully and saved as {file_name}")
        
    except Exception as e:
        st.error(f"Error generating PDF: {e}")


# Function to send an email with PDF attachment

def send_email_with_pdf(to_email, subject, body, file_name):
    """
    Sends an email with a PDF attachment to the specified recipient.
    
    Args:
        to_email (str): Recipient's email address.
        subject (str): Email subject.
        body (str): Email body.
        file_name (str): Path to the PDF file to attach.
    """
    from_email = st.secrets.get("email")
    password = st.secrets.get("app_password")
    
    # Error handling for missing credentials
    if not from_email or not password:
        st.error("Email credentials are missing. Check Streamlit secrets.")
        return
    
    # Set up email message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach PDF file with error handling
    try:
        with open(file_name, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {file_name}')
            msg.attach(part)
    except FileNotFoundError:
        st.error(f"Attachment file {file_name} not found. Please check the file path.")
        return
    except Exception as e:
        st.error(f"Error attaching file {file_name}: {e}")
        return
    
    # Send email with error handling
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        st.success(f"Email sent to {to_email} with the attached PDF report!")
    except smtplib.SMTPException as e:
        st.error(f"SMTP error occurred: {e}")
    except Exception as e:
        st.error(f"Unexpected error sending email: {e}")



# Function to generate a quiz document
def generate_question_and_options(topic, class_level, question_type, subtopic):
    """
    Generates a question and options using OpenAI's API based on input parameters.
    
    Args:
        topic (str): Main topic for the question.
        class_level (str): Grade or class level.
        question_type (str): Type of question (e.g., MCQ).
        subtopic (str): Specific subtopic within the main topic.

    Returns:
        tuple: Question text, options, and correct answer.
    """
    prompt = (
        f"Create a {question_type} question about {subtopic} for a {class_level} level quiz on {topic}. "
        f"Include four answer choices labeled A, B, C, and D, and indicate the correct answer."
    )
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        full_text = response['choices'][0]['message']['content'].strip()
        lines = full_text.split("\n")
        question = lines[0]
        options = lines[1:5]  # First four lines after question are options
        correct_answer = lines[5] if len(lines) > 5 else "Correct Answer Not Provided"
        
        if not question or not options:
            raise ValueError("Incomplete question or options received.")
        
        return question, options, correct_answer
    
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI API error: {e}")
        return "Error generating question.", ["A) Error", "B) Error", "C) Error", "D) Error"], "Answer unavailable"
    except Exception as e:
        st.error(f"Unexpected error generating question: {e}")
        return "Error generating question.", ["A) Error", "B) Error", "C) Error", "D) Error"], "Answer unavailable"


def save_contentt_as_doc(content, file_name_docx, image_data=None, single_image=True):
    """
    Saves content as a DOCX file with optional images.
    
    Args:
        content (str): Text content to include in the document.
        file_name_docx (str): File path for saving the document.
        image_data (BytesIO): Optional image data to embed.
        single_image (bool): Whether to add a single image at the top or one per question.
    """
    try:
        document = Document()
        
        # If single_image is True, add one image at the top; if False, add one per question
        if single_image and image_data:
            document.add_picture(image_data, width=Inches(2))
            document.add_paragraph("\n")

        for line in content.split("\n"):
            document.add_paragraph(line)
            if not single_image and image_data:
                document.add_picture(image_data, width=Inches(2))
                document.add_paragraph("\n")
        
        document.save(file_name_docx)
        st.success(f"Document saved successfully as {file_name_docx}")

    except Exception as e:
        st.error(f"Error saving document {file_name_docx}: {e}")

def extract_weak_topics(assessment_content):
    """
    Identifies weak topics based on assessment content using OpenAI's API.
    
    Args:
        assessment_content (str): The assessment report content to analyze.

    Returns:
        list: Weak topics if found, else an empty list.
    """
    prompt = f"""
    Analyze the following assessment report content. Identify and list all topics and subtopics where 'Concept Clarity' is marked as 'No'.
    
    Assessment Content:
    {assessment_content}
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        weak_topics = response['choices'][0]['message']['content']
        if not weak_topics:
            raise ValueError("No weak topics identified.")
        return weak_topics.split("\n")

    except openai.error.OpenAIError as e:
        st.error(f"OpenAI API error while extracting weak topics: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error extracting weak topics: {e}")
        return []

def generate_personalized_material(weak_topics):
    """
    Generates personalized learning material based on weak topics.
    
    Args:
        weak_topics (list): List of weak topics to address.

    Returns:
        str: Learning material content.
    """
    prompt = f"Create learning material covering the following topics: {', '.join(weak_topics)}."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        material = response['choices'][0]['message']['content']
        return material if material else "No material generated."

    except openai.error.OpenAIError as e:
        st.error(f"OpenAI API error generating material: {e}")
        return "Error generating material."
    except Exception as e:
        st.error(f"Unexpected error generating material: {e}")
        return "Error generating material."


def send_email_with_attachments(to_email, subject, body, attachments):
    """
    Sends an email with multiple attachments to the specified recipient.
    
    Args:
        to_email (str): Recipient's email address.
        subject (str): Email subject.
        body (str): Email body.
        attachments (list): List of file paths for attachments.
    """
    from_email = st.secrets.get("email")
    password = st.secrets.get("app_password")
    
    if not from_email or not password:
        st.error("Email credentials missing. Check Streamlit secrets.")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        for file_path in attachments:
            try:
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename= {file_path}")
                    msg.attach(part)
            except FileNotFoundError:
                st.error(f"Attachment file {file_path} not found.")
                return
            except Exception as e:
                st.error(f"Error attaching file {file_path}: {e}")
                return
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        st.success(f"Email sent to {to_email} with attachments.")
    
    except smtplib.SMTPException as e:
        st.error(f"SMTP error: {e}")
    except Exception as e:
        st.error(f"Unexpected error sending email: {e}")










# Function to generate question using GPT based on input
def generate_question(topic, class_level, question_type, subtopic):
    try:
        prompt = f"Generate a {question_type} question on the topic '{topic}' for {class_level} on the subtopic '{subtopic}'. Include a question text and answer options."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error in generating question: {e}")
        return "Error generating question."

# Function to create a quiz document with enhanced error handling for images
def create_quiz1_document(topic, subject, class_level, max_marks, duration, num_questions, question_type, include_answers, include_images, file_path):
    document = Document()
    try:
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
        details_paragraph.add_run("    ")
        details_paragraph.add_run(f'Max. Marks: {max_marks}').bold = True
        document.add_paragraph("\n")  # Extra line for spacing

        # Loop to add questions and images
        for i in range(num_questions):
            question_text = f"Sample question {i+1} about {topic}."
            document.add_paragraph(f'Q{i+1}: {question_text}')

            # Conditionally add image if include_images is True
            if include_images:
                image_prompt = f"Image of {topic} for {class_level} related to {subject}"
                image_data = fetch_image(image_prompt)
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
                correct_answer = "B) Sample Answer"
                document.add_paragraph(f"Answer: {correct_answer}")

            document.add_paragraph("\n")  # Add spacing after each question

        # Add answer section if answers are not included inline
        if not include_answers:
            document.add_paragraph("\nAnswers:\n")
            for i in range(num_questions):
                document.add_paragraph(f'Q{i+1}: ________________')

        # Save the document to the specified file path
        document.save(file_path)
    except Exception as e:
        print(f"Error in creating quiz document: {e}")

# Function to generate an assessment report as PDF
def generatereport_pdf(content, title, filename, student_name, student_id, assessment_id, exam_type, subject):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    try:
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
    except Exception as e:
        print(f"Error in generating report PDF: {e}")

# Function to read DOCX content with debug statements
def read_docx(file):
    try:
        doc = Document(file)
        full_text = "\n".join([repr(para.text) for para in doc.paragraphs])
        print("DEBUG - Full Document Content with Hidden Characters:\n", full_text)  # Show all text details
        return full_text
    except Exception as e:
        print(f"Error reading DOCX file: {e}")
        return "Error reading file."

# Function to generate personalized assignments
def generate_personalized_assignment(weak_topics):
    try:
        prompt = f"Create an assignment based on the following topics for practice: {', '.join(weak_topics)}. Include questions that reinforce the concepts."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error generating personalized assignment: {e}")
        return "Error generating assignment."

# Function to generate a PDF file with enhanced encoding
def generate_pdf(content, title, file_name):
    pdf = FPDF()
    pdf.add_page()

    try:
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
    except Exception as e:
        print(f"Error in generating PDF: {e}")


# Function to generate a PDF file with enhanced encoding
def generatenew_pdf(content, title, file_name):
    """
    Generates a PDF report with sanitized text to handle Unicode issues.

    Args:
        content (str): The text content to include in the PDF.
        title (str): The title for the PDF report.
        file_name (str): The file path to save the PDF.
    """
    pdf = FPDF()
    pdf.add_page()

    # Set title
    pdf.set_font("Arial", "B", 16)
    sanitized_title = sanitize_text_for_pdf(title)
    pdf.cell(0, 10, sanitized_title, ln=True, align='C')
    pdf.ln(10)

    # Add content
    pdf.set_font("Arial", size=12)
    sanitized_content = sanitize_text_for_pdf(content)
    for line in sanitized_content.split("\n"):
        pdf.cell(0, 10, line, ln=True)

    # Save the PDF file
    try:
        pdf.output(file_name)
        print(f"PDF saved as {file_name}")
    except Exception as e:
        print(f"Error in saving PDF: {e}")


# Function to save content to a DOCX file with error handling
def save_content_as_doc(content, file_name):
    try:
        doc = Document()
        for line in content.split("\n"):
            doc.add_paragraph(line)
        doc.save(file_name)
    except Exception as e:
        print(f"Error saving content as DOCX: {e}")





# Function to sanitize text by replacing unsupported characters
def sanitize_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')


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
import re

def validate_email(email):
    """Validate email format."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def sanitize_text_input(text):
    """Sanitize text input to prevent special character injection."""
    return re.sub(r"[^\w\s]", "", text)  # Removes special characters except spaces and alphanumeric

def validate_student_id(student_id):
    """Validate student ID format (only alphanumeric allowed)."""
    return re.match(r"^[a-zA-Z0-9]+$", student_id) is not None


def show_home():
    """
    Displays the home page with custom-styled option cards for each section.
    """
    try:
        st.markdown("""
            <div style='text-align: center; font-size: 18px; color: #4B0082; padding: 20px 0;'>
                Welcome to your all-in-one platform for creating educational content, lesson plans, and student assessments.
            </div>
        """, unsafe_allow_html=True)

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
        
        col3, col4, col5 = st.columns(3)
        
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
        
        with col5:
            st.markdown("""
            <div class="option-card">
                <h3 style='color: #4B0082; text-align: center;'>Analyze Report and Generate Graph</h3>
                <p style='text-align: center;'>Analyze Report and Generate Graph</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div class='center' style='padding: 20px;'>", unsafe_allow_html=True)
        if st.button("Get Started Today"):
            st.session_state['task'] = "Create Educational Content"
        st.markdown("</div>", unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Error displaying home page: {e}")

def create_educational_content():
    """
    Collects input to generate educational content and handles all errors gracefully.
    """
    st.header("Educational Content Creation")
    
    try:
        # Input fields with validation messages
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):", key="board_input")
        standard = st.text_input("Enter Standard/Class (e.g., Class 10):", key="standard_input")
        topics = st.text_input("Enter Topics (comma-separated):", key="topics_input")
        content_type = st.selectbox(
            "Select Content Type",
            ["Quizzes", "Question paper", "Practice Questions", "Assignments"],
            index=3,  # Default to "Assignments"
            key="content_type_select"
        )
        total_marks = st.number_input("Enter Total Marks (optional)", min_value=10, key="total_marks_input")
        time_duration = st.text_input("Enter Time Duration (e.g., 60 minutes, optional)", key="time_duration_input")
        question_types = st.multiselect(
            "Select Question Types (optional)",
            ["True/False", "Yes/No", "MCQs", "Very Short answers", "Short answers", "Long answers", "Very Long answers"],
            key="question_types_multiselect"
        )
        difficulty = st.selectbox(
            "Select Difficulty Level (optional)", 
            ["Easy", "Medium", "Hard"], 
            key="difficulty_select"
        )
        category = st.selectbox(
            "Select Category",
            ["Value-based Questions", "Competency Questions", "Paragraph-based Questions", "Mixed of your choice"],
            index=1,  # Default to "Competency Questions"
            key="category_select"
        )
        include_solutions = st.radio(
            "Would you like to include solutions?",
            ["Yes", "No"],
            key="include_solutions_radio"
        )

        # Generate content with enhanced error handling
        if st.button("Generate Educational Content"):
            # Check for required fields
            if not board or not standard or not topics or not content_type:
                st.warning("Please fill in all required fields: Board, Standard, Topics, and Content Type.")
                return
            
            # Call the content generation function
            content = generate_content(
                board, standard, topics, content_type, total_marks, time_duration,
                question_types, difficulty, category, include_solutions == "Yes"
            )
            
            # Display generated content
            st.write("### Generated Educational Content")
            st.write(content)
            
            # Downloadable documents
            try:
                file_name_docx = f"{content_type}_{standard}.docx"
                save_content_as_doc(content, file_name_docx)
                with open(file_name_docx, "rb") as file:
                    st.download_button(label="Download Content as DOCX", data=file.read(), file_name=file_name_docx)
                
                file_name_pdf = f"{content_type}_{standard}.pdf"
                generate_pdf(content, f"{content_type} for {standard}", file_name_pdf)
                with open(file_name_pdf, "rb") as file:
                    st.download_button(label="Download Content as PDF", data=file.read(), file_name=file_name_pdf)
            
            except Exception as e:
                st.error(f"Error generating or downloading documents: {e}")

    except Exception as e:
        st.error(f"Error in educational content creation: {e}")



def create_lesson_plan():
    """
    Collects input to generate a lesson plan and provides feedback for successful or unsuccessful generation.
    """
    st.header("Lesson Plan Creation")
    
    try:
        # Input collection with validation messages
        subject = st.text_input("Enter Subject:", key="subject_input")
        grade = st.text_input("Enter Class/Grade:", key="grade_input")
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):", key="lesson_board_input")
        duration = st.text_input("Enter Lesson Duration (e.g., 45 minutes, 1 hour):", key="duration_input")
        topic = st.text_input("Enter Lesson Topic:", key="topic_input")

        # Generate lesson plan
        if st.button("Generate Lesson Plan"):
            if not subject or not grade or not board or not duration or not topic:
                st.warning("Please fill in all required fields.")
                return
            
            try:
                lesson_plan = generate_lesson_plan(subject, grade, board, duration, topic)
                st.write("### Generated Lesson Plan")
                st.write(lesson_plan)
                
                # Save lesson plan as DOCX and PDF, with error handling
                file_name_docx = f"{subject}_{grade}_LessonPlan.docx"
                save_content_as_doc(lesson_plan, file_name_docx)
                with open(file_name_docx, "rb") as file:
                    st.download_button(label="Download Lesson Plan as DOCX", data=file.read(), file_name=file_name_docx)
                
                file_name_pdf = f"{subject}_{grade}_LessonPlan.pdf"
                generate_pdf(lesson_plan, f"Lesson Plan: {subject} - Grade {grade}", file_name_pdf)
                with open(file_name_pdf, "rb") as file:
                    st.download_button(label="Download Lesson Plan as PDF", data=file.read(), file_name=file_name_pdf)
            
            except Exception as e:
                st.error(f"Error generating lesson plan or saving files: {e}")
    
    except Exception as e:
        st.error(f"Error in lesson plan creation: {e}")


import matplotlib.pyplot as plt
from PyPDF2 import PdfReader

from fpdf import FPDF

def parse_pdf_with_openai(file):
    """
    Extracts text from the PDF file and uses OpenAI to parse topics and concept clarity.

    Args:
        file: Uploaded PDF file.
    
    Returns:
        dict: Parsed topics with their clarity percentages.
    """
    try:
        # Step 1: Extract text from the PDF
        reader = PdfReader(file)
        content = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                content += page_text

        # Debugging: Display extracted content
       # st.write("### Extracted Content")
        #st.text(content)

        # Step 2: Define the OpenAI prompt
        prompt = f"""
        The following text is an assessment report. Extract the topics and their concept clarity. 
        If a topic is marked as 'Yes' for concept clarity, set the percentage to 100. If marked as 'No', set it to 0. 
        Return the results as a JSON object with the format:
        {{
            "Topic 1": percentage,
            "Topic 2": percentage,
            ...
        }}
        
        Assessment Report:
        {content}
        """

        # Step 3: Use OpenAI to parse the report
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        parsed_data = response['choices'][0]['message']['content'].strip()

        # Step 4: Convert the response to a dictionary
        try:
            topics_data = json.loads(parsed_data)
            return topics_data
        except json.JSONDecodeError:
            st.error("Failed to parse the response into JSON format.")
            return {}

    except Exception as e:
        st.error(f"Error during parsing with OpenAI: {e}")
        return {}



import matplotlib.pyplot as plt

def generate_clarity_graph(data):
    """
    Generates a vertical bar chart for topics with concept clarity percentages.

    Args:
        data (dict): A dictionary with topics as keys and clarity percentages as values.
    """
    if not data:
        st.error("No data available to generate the graph.")
        return

    # Extract topics and percentages
    topics = list(data.keys())
    clarity_percentages = list(data.values())

    # Assign colors based on clarity zones
    colors = []
    for clarity in clarity_percentages:
        if clarity <= 30:
            colors.append("red")
        elif clarity <= 50:
            colors.append("orange")
        elif clarity <= 74:
            colors.append("yellow")
        else:
            colors.append("green")

    # Plot the vertical bar graph
    plt.figure(figsize=(12, 6))
    plt.bar(topics, clarity_percentages, color=colors, edgecolor="black")
    plt.xticks(rotation=45, ha='right', fontsize=10)  # Rotate topic labels for better readability
    plt.xlabel("Topics", fontsize=14)
    plt.ylabel("Clarity Percentage (%)", fontsize=14)
    plt.title("Concept Clarity by Topic", fontsize=16, fontweight="bold")
    plt.ylim(0, 100)  # Set y-axis limits
    plt.tight_layout()

    # Display the graph in Streamlit
    st.pyplot(plt)

def report_analysis_with_openai():
    st.header("Analyze Report Using OpenAI")
    
    uploaded_file = st.file_uploader("Upload Assessment Report (PDF)", type=["pdf"])
    
    if uploaded_file:
        try:
            # Parse the report using OpenAI
            topics_data = parse_pdf_with_openai(uploaded_file)

            # Display the parsed data
            if topics_data:
               # st.write("### Parsed Topics and Clarity")
                #st.json(topics_data)

                # Generate a graph for visualization
                st.write("### Concept Clarity Graph")
                generate_clarity_graph(topics_data)
            else:
                st.warning("No topics or concept clarity data found in the report.")
        
        except Exception as e:
            st.error(f"Error analyzing the report: {e}")




def sanitize_text_for_pdf(text):
    """Sanitizes text to ensure compatibility with PDF generation."""
    return text.encode('latin-1', 'replace').decode('latin-1')

# Example Usage
    pdf.cell(0, 10, sanitize_text_for_pdf(line), ln=True)







def student_assessment_assistant():
    """
    Collects inputs to generate student assessment reports, handles errors in report generation,
    and provides download and email options.
    """
    st.header("Student Assessment Assistant")

    try:
        # Collect student information with unique labels for each field
        student_name = st.text_input("Enter Student Name", key="student_name_input")
        student_id = st.text_input("Enter Student ID", key="student_id_input")
        assessment_id = st.text_input("Enter Assessment ID", key="assessment_id_input")
        class_name = st.text_input("Enter Class/Standard", key="class_name_input")
        email_id = st.text_input("Enter Parent's Email ID", key="email_id_input")
        exam_type = st.text_input("Enter Exam Type (e.g., Midterm, Final Exam)", key="exam_type_input")
        subject = st.text_input("Enter Subject", key="subject_input")

        # Upload files with DOCX format
        question_paper = st.file_uploader("Upload Question Paper (DOCX)", type=["docx"], key="question_paper_uploader")
        marking_scheme = st.file_uploader("Upload Marking Scheme (DOCX)", type=["docx"], key="marking_scheme_uploader")
        answer_sheet = st.file_uploader("Upload Student's Answer Sheet (DOCX)", type=["docx"], key="answer_sheet_uploader")

        if st.button("Generate and Send Reports"):
            if student_id and assessment_id and email_id and question_paper and marking_scheme and answer_sheet:
                try:
                    # Read DOCX files
                    question_paper_content = read_docx(question_paper)
                    marking_scheme_content = read_docx(marking_scheme)
                    answer_sheet_content = read_docx(answer_sheet)
                    
                    # Generate assessment report prompt
                    prompt = f"""
You are an educational assessment assistant. Using the question paper, marking scheme, and answer sheet, evaluate the student's answers.
Avoid using any special characters or bullet points for emphasis. Present the report in a clear, concise manner suitable for parents and teachers.
Please generate a detailed assessment report in the following format:

1. Question Analysis - For each question:
    - Topic
    - Subtopic
    - Question Number
    - Score based on answer accuracy and relevance
    - Concept Clarity (Yes/No)
    - Feedback and Suggestions
    - Solution if concept clarity is 'NO'

2. Summary Report - Include:
    - Final Score
    - Grade
    - Areas of Strength
    - Areas for Improvement
    - Final Remarks

Information for Report:
Student Name: {student_name}
Student ID: {student_id}
Class: {class_name}
Assessment ID: {assessment_id}
Exam Type: {exam_type}
Subject: {subject}

Question Paper:
{question_paper_content}

Marking Scheme:
{marking_scheme_content}

Answer Sheet:
{answer_sheet_content}
"""

                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "system", "content": prompt}]
                    )
                    report = response['choices'][0]['message']['content']
                    st.write(" Assessment Report")
                    st.write(report)


                    
                    # Extract weak topics from report
                    weak_topics_prompt = f"Identify topics and subtopics where 'Concept Clarity' is marked as 'No'.\n\nAssessment Report:\n{report}"
                    weak_response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": weak_topics_prompt}]
                    )
                    weak_topics = weak_response['choices'][0]['message']['content'].strip().split("\n")
                                     
                    # Clean and format the weak topics into plain text
                    formatted_weak_topics = "Weak Topics Identified:\n"
                    for line in weak_topics:
                        if line.strip():  # Exclude empty lines
                            formatted_weak_topics += line.strip() + "\n"

                    # Display weak topics in plain text format
                    st.write("### Weak Topics")
                    st.text(formatted_weak_topics)  # Use st.text for plain text display

                    

                    # Generate learning material and assignment
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
                    st.write("Personalized Learning Material")
                    st.write(learning_material)
                    st.write("Practice Assignment")
                    st.write(assignment)

                    # Generate PDFs
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

                    st.success("Reports generated successfully and are ready for download.")

                    # Email the reports to the parent
                    subject = f"Assessment Reports for {student_name}"
                    body = f"""
Dear Parent,

Please find attached the assessment reports for {student_name}:

1. *Assessment Report*: Detailed evaluation of {student_name}'s performance.
2. *Personalized Learning Material*: Resources to reinforce understanding.
3. *Practice Assignment*: Exercises to solidify learning.

Best regards,
Your School
                    """
                    attachments = [assessment_report_pdf, learning_material_pdf, assignment_pdf]
                    send_email_with_attachments(email_id, subject, body, attachments)
                
                except openai.error.OpenAIError as e:
                    st.error(f"OpenAI API error: {e}")
                except Exception as e:
                    st.error(f"Error in report generation: {e}")
            else:
                st.error("Please provide all required inputs.")

        # Display download buttons for generated reports
        if 'assessment_report_pdf' in st.session_state:
            st.write("Assessment Report")
            with open(st.session_state['assessment_report_pdf'], "rb") as file:
                st.download_button(label="Download Assessment Report as PDF", data=file.read(), file_name=st.session_state['assessment_report_pdf'])

        if 'learning_material_pdf' in st.session_state:
            st.write("Personalized Learning Material")
            with open(st.session_state['learning_material_pdf'], "rb") as file:
                st.download_button(label="Download Learning Material as PDF", data=file.read(), file_name=st.session_state['learning_material_pdf'])

        if 'assignment_pdf' in st.session_state:
            st.write("Personalized Assignment")
            with open(st.session_state['assignment_pdf'], "rb") as file:
                st.download_button(label="Download Assignment as PDF", data=file.read(), file_name=st.session_state['assignment_pdf'])
        
    except Exception as e:
        st.error(f"An error occurred in the Student Assessment Assistant: {e}")








def generate_image_based_questions():
    """
    Generates image-based questions for quizzes and provides download options for the generated documents.
    """
    st.header("Generate Image Based Questions")
    
    try:
        # Input collection with validation
        topic = st.text_input("Select a topic (e.g., Plants, Animals, Geography):", key="image_topic_input")
        subject = st.text_input("Enter the subject (e.g., Science, Geography):", key="subject_input")
        class_level = st.text_input("Select a class level (e.g., Grade 1, Grade 2):", key="class_level_input")
        max_marks = st.text_input("Enter maximum marks:", key="max_marks_input")
        duration = st.text_input("Enter duration (e.g., 1 hour):", key="duration_input")
        num_questions = st.number_input("Enter the number of questions (minimum 5):", min_value=5, key="num_questions_input")
        question_type = st.selectbox("Choose question type", ["MCQ", "true/false", "yes/no"], key="question_type_select")

        if st.button("Generate Quiz Document"):
            if not topic or not subject or not class_level or not max_marks or not duration:
                st.warning("Please fill in all required fields.")
                return

            # Generate documents with error handling
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file_without_answers, \
                     tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file_with_answers:

                    quiz_filename_without_answers = tmp_file_without_answers.name
                    quiz_filename_with_answers = tmp_file_with_answers.name

                    create_quiz_document(topic, subject, class_level, max_marks, duration, num_questions, question_type,
                                         include_answers=False, file_path=quiz_filename_without_answers)
                    create_quiz_document(topic, subject, class_level, max_marks, duration, num_questions, question_type,
                                         include_answers=True, file_path=quiz_filename_with_answers)

                    st.session_state["quiz_filename_without_answers"] = quiz_filename_without_answers
                    st.session_state["quiz_filename_with_answers"] = quiz_filename_with_answers

                st.success("Quiz documents generated successfully!")

            except Exception as e:
                st.error(f"Error generating quiz documents: {e}")

        # Download buttons with error handling
        if "quiz_filename_without_answers" in st.session_state and "quiz_filename_with_answers" in st.session_state:
            try:
                with open(st.session_state["quiz_filename_without_answers"], "rb") as file:
                    st.download_button(label="Download Quiz Document (without answers)", data=file.read(), file_name=Path(st.session_state["quiz_filename_without_answers"]).name)
                
                with open(st.session_state["quiz_filename_with_answers"], "rb") as file:
                    st.download_button(label="Download Quiz Document (with answers)", data=file.read(), file_name=Path(st.session_state["quiz_filename_with_answers"]).name)
            
            except Exception as e:
                st.error(f"Error providing download options: {e}")
    
    except Exception as e:
        st.error(f"Error in Generate Image Based Questions: {e}")



def generate_detailed_answers_with_marking_scheme(question_paper_content):
    """Generates detailed answers and a marking scheme using OpenAI GPT."""
    prompt = f"""
    You are an expert educational content creator. Below is a question paper. Your task is to:
    1. Generate **detailed answers** for each question with all necessary steps and explanations.
    2. Create a **step-by-step marking scheme** with marks allocated for each component or step in the answer.
    Ensure the answers are structured, and the marking scheme aligns with the board's standards.

    Question Paper:
    {question_paper_content}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"An error occurred while generating the detailed answers and marking scheme: {e}")
        return None

def create_answer_sheet_docx(content):
    """Creates a DOCX file for the detailed answer sheet with marking scheme."""
    doc = Document()
    doc.add_heading("Detailed Answer Sheet with Marking Scheme", level=1)
    doc.add_paragraph(content)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def extract_text_from_docx(file):
    doc = Document(file)
    text = [para.text for para in doc.paragraphs if para.text.strip() != ""]
    return "\n".join(text)

# AI function to generate curriculum if not provided
def generate_curriculum(board, subject, class_level):
    prompt = f"""
    You are a curriculum expert. Generate the official curriculum for the {board} board for {subject} in {class_level}.
    Provide a detailed list of topics, subtopics, and learning objectives that align with the official guidelines.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# AI function to check alignment
def check_alignment(assignment_text, curriculum_text):
    prompt = f"""
    You are an expert curriculum alignment checker. Compare the following assignment/lesson plan with the curriculum. 
    Provide a detailed report of alignment, partial alignment, and misalignment with suggestions for improvement.

    Assignment/Lesson Plan Text:
    {assignment_text}

    Curriculum Text:
    {curriculum_text}

    Output the results in the following format:
    - Aligned Topics/Subtopics
    - Partially Aligned Topics/Subtopics
    - Not Aligned Topics/Subtopics
    - Suggestions for Improvement
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

def generate_detailed_answer_sheet(question_paper_content):
    """Generates a detailed answer sheet using OpenAI GPT."""
    prompt = f"""
    You are an AI educational assistant. Below is a question paper. Your task is to:
    1. Geneindentation error and give me code back without forgetting single line. return all lines please rate **detailed answers** for each question.
       - For theoretical questions: Provide comprehensive explanations with context, examples, and any necessary diagrams (describe in text).
       - For numerical or problem-solving questions: Show step-by-step calculations and explanations.
       - For conceptual questions: Explain the concept thoroughly with real-life examples where applicable.
    2. Ensure the numbering and structure exactly match the question paper.
    3. Provide clear formatting for each question and its answer.

    Question Paper:
    {question_paper_content}

    Deliver the answers in the following format:
    ---
    **Answer Sheet**
    **Q1:** [Detailed answer with explanation, steps, examples, etc.]
    **Q2:** [Detailed answer with explanation, steps, examples, etc.]
    ...
    ---
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"An error occurred while generating the answer sheet: {e}")
        return None

def create_answer_sheet_docx(answer_sheet_content):
    """Creates a DOCX file for the detailed answer sheet."""
    doc = Document()
    doc.add_heading("Answer Sheet", level=1)
    doc.add_paragraph("Generated Detailed Answers for the Provided Question Paper")
    doc.add_paragraph("\n")
    for line in answer_sheet_content.split("\n"):
        doc.add_paragraph(line)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# Function to generate the sample paper using AI
def generate_sample_paper(board, subject, grade, max_marks, medium):
    prompt = f"""
    You are an expert in educational content creation. Generate a sample paper strictly following the official pattern of the {board} board.
    The subject is '{subject}' for grade '{grade}'. The maximum marks for the paper are {max_marks}, and the medium of the paper is '{medium}'.
    Ensure the following:
    1. The sample paper should strictly follow the board's format and guidelines.
    2. Include all sections and instructions as per the board's official pattern (e.g., MCQs, short answers, long answers).
    3. Adhere to the difficulty level and marks distribution prescribed by the board.
    4. Avoid adding any fields or formats not part of the official pattern.

    Generate content in the {medium} language.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to create a Word document with the generated sample paper
def create_docx(content):
    doc = Document()
    doc.add_paragraph(content)
    doc_buffer = BytesIO()
    doc.save(doc_buffer)
    doc_buffer.seek(0)
    return doc_buffer

def generate_discussion_prompts(topic, grade, subject):
    """
    Generate discussion questions based on the topic, grade, and subject using gpt-3.5-turbo.
    """
    try:
        # Construct the prompt for the GPT model
        prompt = (
            f"Generate 5 creative and engaging discussion questions for a classroom lesson on the topic "
            f"'{topic}' for {grade} students in {subject}. Ensure the questions are age-appropriate, "
            f"interactive, and designed to encourage critical thinking."
        )
        
        # Call the OpenAI GPT model with the required 'messages' parameter
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use gpt-3.5-turbo
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        # Extract the generated content
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"An error occurred: {e}"


def main_app():
    """
    Main application function that controls the display and functionality of each app section.
    Provides error handling and UI feedback for each module.
    """
    if st.button("Logout"):
        logout()

    try:
        client_config = st.session_state.get('client_config')

        # Display client logo and name with theme color and style
        if client_config:
            st.markdown(f"""
                <div style="text-align: center; background: linear-gradient(180deg, #6A5ACD, {client_config['theme_color']}); padding: 10px 0; border-radius: 8px;">
                    <h2 style="margin: 0; font-size: 24px; color: white;">{client_config['name']}</h2>
                </div>
            """, unsafe_allow_html=True)

        # Sidebar with improved styling for module selection
        st.sidebar.markdown("""
            <style>
                .sidebar-title { font-size: 22px; color: #4B0082; margin-bottom: 15px; text-align: center; }
            </style>
        """, unsafe_allow_html=True)
        st.sidebar.markdown("<div class='sidebar-title'>EduCreate Pro Dashboard</div>", unsafe_allow_html=True)

        # Task Selection
        task = st.sidebar.radio("Select Module", [
            "Home",
            "Create Educational Content",
            "Create Lesson Plan",
            "Student Assessment Assistant",
            "Generate Image Based Questions",
            "Analyze Report and Generate Graph",
            "Text Generation",
            "Curriculum Generator",
            "Assignment Generator",
            "Marking Scheme Generator",
            "Alignment Checker",
            "Advanced Editing",
            "Generate Answer Sheet",
            "Sample Paper Generator",
            "Classroom Discussion Prompter",
            "Subscription & Premium Features"
        ])

        # Dynamic Theme Selection
        theme = st.sidebar.selectbox(
            "Choose Theme", ["Default", "Dark", "Light", "Custom"]
        )

        # Apply the selected theme dynamically
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

        # AI Model Selection
        ai_model = st.sidebar.radio("Choose AI Model", ["gpt-3.5-turbo", "gpt-4"])

        # Function to call OpenAI API based on selected model
        def call_openai_api(prompt, max_tokens=1000):
            response = openai.ChatCompletion.create(
                model=ai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response["choices"][0]["message"]["content"]

        # Content based on selected module
        if task == "Home":
            show_home()

        elif task == "Create Educational Content":
            st.info("Setting up Content Creator...")
            create_educational_content()

        elif task == "Create Lesson Plan":
            st.info("Setting up Lesson Planner...")
            create_lesson_plan()

        elif task == "Student Assessment Assistant":
            st.info("Setting up Assessment Assistant...")
            student_assessment_assistant()

        elif task == "Generate Image Based Questions":
            st.info("Setting up Image-Based Question Generator...")
            generate_image_based_questions()

        elif task == "Analyze Report and Generate Graph":
            st.info("Setting up Report Analysis Module...")
            report_analysis_with_openai()

        elif task == "Text Generation":
            st.title("AI Writing Assistant")
            prompt = st.text_area("Enter your prompt for text generation:")
            tone = st.selectbox("Select Tone", ["Formal", "Casual", "Creative", "Professional"])
            length = st.slider("Select Content Length", 50, 1000, step=50)

            if st.button("Generate Text"):
                generated_text = call_openai_api(
                    f"Tone: {tone}\nLength: {length} words\nPrompt: {prompt}"
                )
                st.write(generated_text)

        elif task == "Curriculum Generator":
            st.title("Curriculum Generator")
            board = st.selectbox("Select Board", ["CBSE", "ICSE", "IB", "State Board", "Others"])
            grade = st.selectbox("Select Grade", ["Grade 1", "Grade 5", "Grade 10", "Grade 12", "Others"])
            subject = st.selectbox("Select Subject", ["Mathematics", "Science", "History", "Others"])

            if st.button("Generate Curriculum"):
                curriculum = call_openai_api(
                    f"Generate a detailed curriculum for {subject} for {board}, {grade}.",
                    max_tokens=1500,
                )
                st.write(curriculum)

        elif task == "Assignment Generator":
            st.title("Assignment Generator")
            # Select inputs
            board = st.selectbox("Select Board", ["CBSE", "ICSE", "IB", "State Board", "Others"])
            subject = st.selectbox("Select Subject", ["Mathematics", "Science", "English", "Others"])
            grade = st.selectbox("Select Grade", ["Grade 1", "Grade 5", "Grade 10", "Grade 12", "Others"])
            topic = st.text_input("Enter Topic (Optional)", placeholder="e.g., Algebra, Photosynthesis")
            marks = st.number_input("Enter Maximum Marks", min_value=10, max_value=100, value=50)

            if st.button("Generate Assignment"):
                assignment_prompt = f"Generate an assignment for {subject} for {grade} worth {marks} marks."
                if board:
                    assignment_prompt += f" Follow the {board} curriculum."
                if topic:
                    assignment_prompt += f" Focus on the topic: {topic}."

                assignment = call_openai_api(assignment_prompt, max_tokens=1500)
                st.write(assignment)

        elif task == "Marking Scheme Generator":
            st.title("Marking Scheme Generator")
            st.markdown("""
                1. Upload your question paper in .docx format.
                2. The AI will generate **detailed answers** and a **step-by-step marking scheme**.
                3. Download the generated answer sheet and marking scheme as a .docx file.
            """)

            uploaded_file = st.file_uploader("Upload Question Paper (.docx)", type=["docx"])

            if uploaded_file and st.button("Generate Answer Sheet & Marking Scheme"):
                with st.spinner("Generating detailed answers and marking scheme..."):
                    question_paper_content = read_docx(uploaded_file)

                    if not question_paper_content.strip():
                        st.error("The uploaded question paper appears to be empty.")
                        return

                    detailed_content = generate_detailed_answers_with_marking_scheme(question_paper_content)

                    if detailed_content:
                        answer_sheet_file = create_answer_sheet_docx(detailed_content)
                        st.success("Answer sheet and marking scheme generated successfully!")
                        st.download_button(
                            label="Download Answer Sheet with Marking Scheme",
                            data=answer_sheet_file,
                            file_name="Detailed_Answer_Sheet_with_Marking_Scheme.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    else:
                        st.error("Failed to generate the detailed answers and marking scheme.")


        elif task == "Alignment Checker":
            st.title("Curriculum Alignment Checker")
            board = st.selectbox("Select Board", ["CBSE", "ICSE", "IGCSE", "State Board", "Enter Manually"])
            if board == "Enter Manually":
                board = st.text_input("Enter Board Name")
            
            subject = st.selectbox("Select Subject", ["Mathematics", "Science", "English", "Social Studies", "Enter Manually"])
            if subject == "Enter Manually":
                subject = st.text_input("Enter Subject Name")
            
            class_level = st.selectbox("Select Class/Grade", [f"Class {i}" for i in range(1, 13)] + ["Enter Manually"])
            if class_level == "Enter Manually":
                class_level = st.text_input("Enter Class/Grade")

            st.write("Upload the Assignment, Lesson Plan, or Question Paper:")
            assignment_file = st.file_uploader("Upload DOCX file", type=["docx"])

            st.write("Upload the Curriculum File (Optional):")
            curriculum_file = st.file_uploader("Upload Curriculum DOCX file", type=["docx"])

            if st.button("Check Curriculum Alignment"):
                try:
                    assignment_text = extract_text_from_docx(assignment_file) if assignment_file else ""
                    curriculum_text = extract_text_from_docx(curriculum_file) if curriculum_file else ""

                    if not curriculum_text:
                        curriculum_text = generate_curriculum(board, subject, class_level)

                    alignment_report = check_alignment(assignment_text, curriculum_text)
                    st.subheader("Alignment Report")
                    st.write(alignment_report)

                    doc = Document()
                    doc.add_heading("Curriculum Alignment Report", level=1)
                    doc.add_paragraph(alignment_report)
                    doc.save("alignment_report.docx")

                    with open("alignment_report.docx", "rb") as file:
                        st.download_button("Download Alignment Report", file, "alignment_report.docx")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        elif task == "Advanced Editing":
            st.title("Advanced Text Editing")
            text = st.text_area("Enter Text for Editing:")
            option = st.selectbox("Choose Editing Type", ["Grammar Check", "Rewrite", "Summarize"])

            if st.button("Edit Text"):
                try:
                    edited_text = call_openai_api(
                        f"Perform {option} on the following text:\n{text}", max_tokens=500
                    )
                    st.write(edited_text)
                except Exception as e:
                    st.error(f"Error during text editing: {e}")

        elif task == "Generate Answer Sheet":
            st.title("Answer Sheet Generator")
            st.markdown("""
                1. Upload your question paper in .docx format.
                2. The AI will generate **detailed answers** for each question.
                3. Download the generated answer sheet as a .docx file.
            """)

            uploaded_file = st.file_uploader("Upload Question Paper (.docx)", type=["docx"])

            if uploaded_file and st.button("Generate Detailed Answer Sheet"):
                try:
                    question_paper_content = read_docx(uploaded_file)

                    if not question_paper_content.strip():
                        st.error("The uploaded question paper appears to be empty.")
                        return

                    answer_sheet_content = generate_detailed_answer_sheet(question_paper_content)

                    if answer_sheet_content:
                        answer_sheet_file = create_answer_sheet_docx(answer_sheet_content)
                        st.success("Detailed answer sheet generated successfully!")
                        st.download_button(
                            "Download Detailed Answer Sheet",
                            data=answer_sheet_file,
                            file_name="Detailed_Answer_Sheet.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    else:
                        st.error("Failed to generate the detailed answer sheet.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")



        elif task == "Sample Paper Generator":
            st.title("Board-Specific Sample Paper Generator")
            predefined_boards = ["CBSE", "ICSE", "IB", "Cambridge", "State Board"]
            predefined_subjects = ["Mathematics", "Science", "English", "History"]
            predefined_grades = ["Grade 1", "Grade 5", "Grade 10", "Grade 12"]
            predefined_mediums = ["English", "Hindi", "French"]

            board = st.selectbox("Select Board:", predefined_boards + ["Other"])
            if board == "Other":
                board = st.text_input("Enter Board:")

            subject = st.selectbox("Select Subject:", predefined_subjects + ["Other"])
            if subject == "Other":
                subject = st.text_input("Enter Subject:")

            grade = st.selectbox("Select Grade:", predefined_grades + ["Other"])
            if grade == "Other":
                grade = st.text_input("Enter Grade:")

            max_marks = st.number_input("Maximum Marks:", min_value=10, value=100)

            if st.button("Generate Sample Paper"):
                paper_content = generate_sample_paper(board, subject, grade, max_marks)
                st.write(paper_content)

        
        
         
               
    
        elif task == "Classroom Discussion Prompter":
            st.title("Classroom Discussion Prompter")
            st.markdown("### Make your lessons more interactive with creative discussion prompts!")

    # User inputs
            topic = st.text_input("Enter the lesson topic:", placeholder="e.g., Photosynthesis, World War II, Algebra")
            grade = st.selectbox("Select the grade level:", ["Grade 1", "Grade 5", "Grade 8", "Grade 12"])
            subject = st.selectbox("Select the subject:", ["Mathematics", "Science", "History", "Geography", "English", "Others"])

            if st.button("Generate Discussion Prompts"):
                if topic and grade and subject:
                    with st.spinner("Generating discussion prompts..."):
                        prompts = generate_discussion_prompts(topic, grade, subject)
                        st.subheader("Suggested Discussion Prompts:")
                        st.write(prompts)
                else:
                    st.error("Please fill in all the fields to generate discussion prompts.")

        elif task == "Subscription & Premium Features":
            st.title("Upgrade to Premium")
            st.markdown("### Support advanced AI features by subscribing to our service.")
            payment_gateway = st.radio("Choose Payment Method", ["Stripe", "PayPal"])

            if st.button("Subscribe Now"):
                try:
                    if payment_gateway == "Stripe":
                        st.markdown("[Subscribe with Stripe](https://stripe.com/)")
                    elif payment_gateway == "PayPal":
                        st.markdown("[Subscribe with PayPal](https://paypal.com/)")
                except Exception as e:
                    st.error(f"Error in Subscription: {e}")
        


    except KeyError as e:
        st.error(f"Configuration error: {e}. Please log in again.")
    except Exception as e:
        st.error(f"An unexpected error occurred in the main app: {e}")





    




def landing_page():
    # Set page configuration for a better display on landing page
    st.set_page_config(page_title="EduPro - Transform Your Teaching Experience", page_icon="📘")
    
    # Apply custom CSS for the landing page design
    st.markdown(
        """
        <style>
            /* Centered main container styling */
            .container {
                text-align: center;
                margin-top: 15%;
                max-width: 800px;
                margin-left: auto;
                margin-right: auto;
            }
            
            /* Logo styling */
            .logo {
                font-size: 36px;
                font-weight: 700;
                color: #5A5DF5;
                display: inline-flex;
                align-items: center;
                gap: 10px;
                font-family: 'Arial', sans-serif;
                margin-bottom: 20px;
            }
            .logo-icon {
                font-size: 40px;
                color: #9933FF;
            }

            /* Headline styling */
            .headline {
                font-size: 44px;
                font-weight: 800;
                color: #4B0082;
                line-height: 1.2;
                margin-bottom: 10px;
                font-family: 'Arial', sans-serif;
            }
            .highlight {
                color: #5A5DF5;
                font-weight: 800;
            }

            /* Subtext styling */
            .subtext {
                font-size: 20px;
                color: #666;
                margin-bottom: 40px;
                font-family: 'Arial', sans-serif;
            }

            /* Button container */
            .button-container {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 30px;
            }

            /* Button styling */
            .stButton>button {
                font-size: 18px;
                font-weight: 600;
                padding: 15px 50px;
                border-radius: 10px;
                transition: all 0.3s ease;
                cursor: pointer;
                border: none;
                font-family: 'Arial', sans-serif;
            }
            /* Primary button style */
            .stButton>button.primary {
                background: linear-gradient(90deg, #5A5DF5, #9933FF);
                color: white;
                font-weight: 700;
                box-shadow: 0px 6px 15px rgba(90, 93, 245, 0.4);
            }
            .stButton>button.primary:hover {
                background: linear-gradient(90deg, #4A4CE3, #802DD4);
                box-shadow: 0px 8px 18px rgba(90, 93, 245, 0.6);
            }
            /* Secondary button style */
            .stButton>button.secondary {
                background-color: #E0E1FF;
                color: #5A5DF5;
                font-weight: 700;
                box-shadow: 0px 4px 10px rgba(224, 225, 255, 0.6);
            }
            .stButton>button.secondary:hover {
                background-color: #D0D1F7;
                box-shadow: 0px 6px 12px rgba(224, 225, 255, 0.8);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Main content for the landing page
    st.markdown('<div class="container">', unsafe_allow_html=True)
    
    # Logo
    st.markdown('<div class="logo"><span class="logo-icon">📘</span>EduPro</div>', unsafe_allow_html=True)
    
    # Headline with highlighted text
    st.markdown(
        """
        <div class="headline">
            Transform your<br><span class="highlight">teaching experience</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Subtext below the headline
    st.markdown(
        '<div class="subtext">Create personalized assessments, generate content, and track student progress with our AI-powered educational platform.</div>',
        unsafe_allow_html=True
    )
    
    # Button container with primary and secondary buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get started ➔", key="get_started", help="Click to proceed to the login page"):
            st.session_state['page'] = 'login'  # Set page to 'login' to navigate to login page
    with col2:
        st.button("Learn more", key="learn_more", help="Click to learn more about EduPro")

    st.markdown('</div>', unsafe_allow_html=True)

    
# Ensure that session state for 'page' is initialized
if 'page' not in st.session_state:
    st.session_state['page'] = 'home'  # Set a default value, e.g., 'home'

# Main function to handle navigation
# Main function to handle page navigation
def main():
    if st.session_state['page'] == 'home':
        landing_page()
    elif st.session_state['page'] == 'login':
        login_page()
    elif st.session_state['page'] == 'main' and st.session_state['logged_in']:
        main_app()
    else:
        st.error("An error occurred. Please refresh the page.")

if __name__ == "__main__":
    main()


