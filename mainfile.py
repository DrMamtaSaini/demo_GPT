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
                
                # Attempt to load client configuration after successful login
                client_config = get_client_config(school_id)
                if client_config:
                    st.session_state['client_config'] = client_config
                    st.success("Login successful!")
                else:
                    st.error("Client configuration not found. Please contact support.")
                    st.session_state['logged_in'] = False
                break
        else:
            # Invalid credentials feedback
            st.error("Invalid credentials. Please try again or contact your administrator.")

        # Confirm if no valid credentials found in SCHOOL_CREDENTIALS
        if not st.session_state.get("logged_in"):
            st.warning("Please ensure your credentials are correct. Try again.")




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
    """
    Generates educational content based on input parameters using OpenAI's GPT API.
    
    Args:
        board (str): Education board (e.g., CBSE, ICSE).
        standard (str): Class or grade level.
        topics (str): Topics to cover, comma-separated.
        content_type (str): Type of content (e.g., Quiz, Assignment).
        total_marks (int): Total marks for the content.
        time_duration (str): Expected time duration.
        question_types (list): List of question types (e.g., MCQs, Short answers).
        difficulty (str): Difficulty level (e.g., Easy, Medium).
        category (str): Category of questions (e.g., Value-based).
        include_solutions (bool): Whether to include solutions.

    Returns:
        tuple: Generated content as text and optional image data.
    """
    # Define prompt based on input parameters and content type
    prompt = f"""
    You are an expert educational content creator. Create {content_type} for the {board} board, {standard} class.
    Topics to cover: {topics}. The content should be designed for a total of {total_marks} marks and a time duration of {time_duration}.
    Include question types such as {', '.join(question_types)}, with an overall difficulty level of {difficulty}.
    """
    
    # Modify prompt based on category for specific types of questions
    if category == "Value-based Questions":
        prompt += """
        Create questions that prompt students to reflect on values related to the topic. Include real-life scenarios if possible.
        """
    elif category == "Competency Questions":
        prompt += """
        Create questions that test practical knowledge and problem-solving skills, encouraging students to apply learned concepts.
        """
    elif category == "Image-based Questions":
        prompt += """
        Design questions that use images as prompts for observational and critical thinking skills.
        """
        # Fetch an image for image-based questions
        image_prompt = f"Educational image related to {topics} for {standard} level."
        image_data = fetch_image(image_prompt)
    else:
        image_data = None  # No image needed for non-image-based categories

    # Optionally add solutions to the prompt
    if include_solutions:
        prompt += " Provide detailed solutions for each question."

    # Call OpenAI API for content generation with error handling
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}]
        )
        content = response['choices'][0]['message']['content'].strip()
        if not content:
            raise ValueError("Generated content is empty. Check prompt structure or try again.")
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI API error: {e}")
        return "Error generating content.", None
    except Exception as e:
        st.error(f"Unexpected error generating content: {e}")
        return "Error generating content.", None

    return content, image_data  # Return content with optional image data



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


def save_content_as_doc(content, file_name_docx, image_data=None, single_image=True):
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

# Function to save content to a DOCX file with error handling
def save_contentttttt_as_doc(content, file_name):
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
        content_type = st.selectbox("Select Content Type", ["Quizzes", "Sample Paper", "Practice Questions", "Summary Notes", "Assignments"], key="content_type_select")
        total_marks = st.number_input("Enter Total Marks", min_value=1, key="total_marks_input")
        time_duration = st.text_input("Enter Time Duration (e.g., 60 minutes)", key="time_duration_input")
        question_types = st.multiselect("Select Question Types", ["True/False", "Yes/No", "MCQs", "Very Short answers", "Short answers", "Long answers", "Very Long answers"], key="question_types_multiselect")
        difficulty = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"], key="difficulty_select")
        category = st.selectbox("Select Category", ["Value-based Questions", "Competency Questions", "Image-based Questions", "Paragraph-based Questions", "Mixed of your choice"], key="category_select")
        include_solutions = st.radio("Would you like to include solutions?", ["Yes", "No"], key="include_solutions_radio")

        # Generate content with enhanced error handling
        if st.button("Generate Educational Content"):
            if not board or not standard or not topics:
                st.warning("Please fill in all required fields.")
                return
            
            content, image_data = generate_content(
                board, standard, topics, content_type, total_marks, time_duration,
                question_types, difficulty, category, include_solutions == "Yes"
            )
            
            st.write("### Generated Educational Content")
            st.write(content)
            
            if category == "Image-based Questions" and image_data:
                st.image(image_data, caption="Generated Image for Image-based Question")
            
            # Downloadable documents
            try:
                file_name_docx = f"{content_type}_{standard}.docx"
                save_content_as_doc(content, file_name_docx, image_data=image_data, single_image=True)
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

def generate_assessment_report(question_paper_content, marking_scheme_content, answer_sheet_content,
                               student_name, student_id, class_name, assessment_id, exam_type, subject):
    """
    Generates a detailed assessment report based on the provided question paper, marking scheme, and answer sheet.
    """
    try:
        # Construct a prompt for OpenAI to generate the report
        prompt = f"""
You are an educational assessment assistant. Using the question paper, marking scheme, and answer sheet, evaluate the student's answers.

Please generate a detailed assessment report in the following format:

1. **Question Analysis** - For each question:
    - Topic
    - Subtopic
    - Question Number
    - Score based on answer accuracy and relevance
    - Concept Clarity (Yes/No)
    - Feedback and Suggestions

2. **Summary Report** - Include:
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

        # Call OpenAI's API to generate the report
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract the generated report content
        report_content = response['choices'][0]['message']['content']
        return report_content

    except Exception as e:
        print(f"Error in generating assessment report: {e}")
        return "Error generating the assessment report."


def student_assessment_assistant():
    """
    Collects inputs to generate student assessment reports, handles errors in report generation,
    and provides download and email options.
    """
    st.header("Student Assessment Assistant")
    
    try:
        # Student information inputs with validation
        student_name = st.text_input("Enter Student Name", key="student_name_input")
        student_id = st.text_input("Enter Student ID (alphanumeric only)", key="student_id_input")
        assessment_id = st.text_input("Enter Assessment ID", key="assessment_id_input")
        class_name = st.text_input("Enter Class", key="class_name_input")
        email_id = st.text_input("Enter Parent's Email ID", key="email_id_input")
        exam_type = st.text_input("Enter Exam Type (e.g., Midterm, Final Exam)", key="exam_type_input")
        subject = st.text_input("Enter Subject", key="subject_input")

        # Validate and sanitize inputs
        if st.button("Generate and Send Reports"):
            # Check for missing fields
            if not all([student_name, student_id, assessment_id, class_name, email_id, exam_type, subject]):
                st.warning("Please fill in all fields.")
                return

            # Validate email format
            if not validate_email(email_id):
                st.warning("Invalid email format. Please enter a valid email.")
                return

            # Validate student ID format
            if not validate_student_id(student_id):
                st.warning("Invalid Student ID format. Only alphanumeric characters are allowed.")
                return

            # Sanitize other text inputs
            student_name = sanitize_text_input(student_name)
            assessment_id = sanitize_text_input(assessment_id)
            class_name = sanitize_text_input(class_name)
            exam_type = sanitize_text_input(exam_type)
            subject = sanitize_text_input(subject)

            # File uploads with validation
            question_paper = st.file_uploader("Upload Question Paper (DOCX)", type=["docx"], key="question_paper_uploader")
            marking_scheme = st.file_uploader("Upload Marking Scheme (DOCX)", type=["docx"], key="marking_scheme_uploader")
            answer_sheet = st.file_uploader("Upload Student's Answer Sheet (DOCX)", type=["docx"], key="answer_sheet_uploader")

            if not all([question_paper, marking_scheme, answer_sheet]):
                st.warning("Please upload all required files.")
                return

            try:
                # Read content from uploaded DOCX files
                question_paper_content = read_docx(question_paper)
                marking_scheme_content = read_docx(marking_scheme)
                answer_sheet_content = read_docx(answer_sheet)

                # Generate assessment report
                report = generate_assessment_report(
                    question_paper_content, marking_scheme_content, answer_sheet_content,
                    student_name, student_id, class_name, assessment_id, exam_type, subject
                )
                st.write("## Assessment Report")
                st.write(report)

                # Extract weak topics and generate personalized materials
                weak_topics = extract_weak_topics(report)
                learning_material = generate_personalized_material(weak_topics)
                assignment = generate_personalized_assignment(weak_topics)

                # Save and display PDFs with error handling
                try:
                    assessment_report_pdf = f"assessment_report_{student_id}.pdf"
                    generatereport_pdf(report, "Assessment Report", assessment_report_pdf, student_name, student_id, assessment_id, exam_type, subject)
                    
                    learning_material_pdf = f"learning_material_{student_id}.pdf"
                    generate_pdf(learning_material, "Personalized Learning Material", learning_material_pdf)
                    
                    assignment_pdf = f"assignment_{student_id}.pdf"
                    generate_pdf(assignment, "Personalized Assignment", assignment_pdf)
                    
                    st.session_state['assessment_report_pdf'] = assessment_report_pdf
                    st.session_state['learning_material_pdf'] = learning_material_pdf
                    st.session_state['assignment_pdf'] = assignment_pdf
                    
                    st.success("All reports generated successfully and are ready for download.")
                
                except Exception as e:
                    st.error(f"Error saving PDF reports: {e}")
                    return

                # Email sending with error handling
                try:
                    subject = f"Assessment Reports for {student_name}"
                    body = f"""
Dear Parent,

We have recently conducted an assessment for {student_name} and are sharing the evaluation reports.
Please find attached the Assessment Report, Learning Material, and Practice Assignment.
Thank you for your engagement in {student_name}'s education.

Best regards,
Your School
                    """
                    attachments = [assessment_report_pdf, learning_material_pdf, assignment_pdf]
                    send_email_with_attachments(email_id, subject, body, attachments)
                
                except Exception as e:
                    st.error(f"Error sending email: {e}")
            
            except Exception as e:
                st.error(f"Error generating assessment report: {e}")

        # Display download buttons
        if 'assessment_report_pdf' in st.session_state:
            with open(st.session_state['assessment_report_pdf'], "rb") as file:
                st.download_button(label="Download Assessment Report as PDF", data=file.read(), file_name=st.session_state['assessment_report_pdf'])

        if 'learning_material_pdf' in st.session_state:
            with open(st.session_state['learning_material_pdf'], "rb") as file:
                st.download_button(label="Download Learning Material as PDF", data=file.read(), file_name=st.session_state['learning_material_pdf'])

        if 'assignment_pdf' in st.session_state:
            with open(st.session_state['assignment_pdf'], "rb") as file:
                st.download_button(label="Download Assignment as PDF", data=file.read(), file_name=st.session_state['assignment_pdf'])
    
    except Exception as e:
        st.error(f"Error in Student Assessment Assistant: {e}")

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






def main_app():
    """
    Main application function that controls the display and functionality of each app section.
    Provides error handling and UI feedback for each module.
    """
    try:
        client_config = st.session_state.get('client_config')
        
        if client_config:
            st.image(client_config["logo"], width=120)
            st.markdown(f"""
                <div style="text-align: center; background: linear-gradient(180deg, #6A5ACD, {client_config['theme_color']}); padding: 5px 0;">
                    <h2 style="margin: 0; font-size: 24px; color: white;">{client_config['name']}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        st.sidebar.title("EduCreate Pro")
        task = st.sidebar.radio("Select Module", [
            "Home", 
            "Create Educational Content", 
            "Create Lesson Plan", 
            "Student Assessment Assistant", 
            "Generate Image Based Questions"
        ])
        
        if task == "Home":
            show_home()
        
        elif task == "Create Educational Content":
            try:
                create_educational_content()
            except Exception as e:
                st.error(f"Error in Content Creation: {e}")
        
        elif task == "Create Lesson Plan":
            try:
                create_lesson_plan()
            except Exception as e:
                st.error(f"Error in Lesson Plan Generation: {e}")
        
        elif task == "Student Assessment Assistant":
            try:
                student_assessment_assistant()
            except Exception as e:
                st.error(f"Error in Assessment Generation: {e}")
        
        elif task == "Generate Image Based Questions":
            try:
                generate_image_based_questions()
            except Exception as e:
                st.error(f"Error in Image-Based Question Generation: {e}")
        
    except KeyError as e:
        st.error(f"Configuration error: {e}. Please log in again.")
    except Exception as e:
        st.error(f"An unexpected error occurred in the main app: {e}")

    

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

