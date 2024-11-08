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


import streamlit as st





# Step 1: Load the client configuration file
with open("clients_config.json") as config_file:
    clients_config = json.load(config_file)

# Step 2: Function to get client configuration or a default if client_id is not found
def get_client_config(client_id):
    default_config = {
        "name": "Default Academy",
        "logo": "https://path-to-default-logo.png",
        "theme_color": "#000000"
    }
    return clients_config.get(client_id, default_config)

# Step 3: Get client_id from the URL query parameter
client_id = st.experimental_get_query_params().get("client_id", ["default"])[0]
client_config = get_client_config(client_id)

# Step 4: Display the customized content for each client
st.image(client_config["logo"], width=200)
st.title(f"Welcome to {client_config['name']}!")
st.markdown(f"<style>.main {{ background-color: {client_config['theme_color']}; }}</style>", unsafe_allow_html=True)



st.markdown(
    f"""
    <style>
    .main {{
        background-color: {client_config["theme_color"]};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Use Streamlit's secret management to securely load your API key
openai.api_key = st.secrets["openai_api_key"]

# Function to sanitize text by replacing unsupported characters
def sanitize_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

# Function to wrap text within a cell and add borders
def wrap_text(text, pdf, max_line_length=90):
    words = text.split(' ')
    current_line = ""
    wrapped_lines = []
    
    for word in words:
        if len(current_line + word) + 1 <= max_line_length:
            current_line += word + " "
        else:
            wrapped_lines.append(current_line.strip())
            current_line = word + " "
    
    wrapped_lines.append(current_line.strip())  # Add the last line
    return wrapped_lines

# Generalized function to generate a PDF file for lesson plans or assessment reports
def generate_pdf(content, title, file_name):
    pdf = FPDF()
    pdf.add_page()

    # Set font and add a title with borders
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align='C', border=1)

    # Leave a space after the title
    pdf.ln(10)

    # Set font for the content
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        wrapped_lines = wrap_text(line, pdf)
        for wrapped_line in wrapped_lines:
            pdf.cell(0, 10, txt=sanitize_text(wrapped_line), ln=True, border=0)

    # Save the PDF
    pdf.output(file_name)

# Function to send an email with PDF attachment
def send_email_with_pdf(to_email, subject, body, file_name):
    from_email = st.secrets["email"]
    password = st.secrets["password"]

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))

    # Attach the PDF file
    with open(file_name, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {file_name}')
        msg.attach(part)

    # Send the email via Gmail's SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)
    server.sendmail(from_email, to_email, msg.as_string())
    server.quit()

    st.success(f"Email sent to {to_email} with the attached PDF report!")

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

# Function to save content as a Word document
def save_content_as_doc(content, file_name):
    doc = Document()
    for line in content.split('\n'):
        doc.add_paragraph(line)
    doc.save(file_name)

# Function to read content from a DOCX file
def read_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# Main function
def main():
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
    task = st.sidebar.radio("Select Module", ["Home", "Create Educational Content", "Create Lesson Plan", "Student Assessment Assistant"])

    if task == "Home":
        st.title("EduCreate Pro")
        st.markdown("""
            <div style='text-align: center; font-size: 18px; color: #4B0082;'>
                Your all-in-one platform for creating educational content, lesson plans, and student assessments.
            </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Content Creator")
            st.write("Generate quizzes, sample papers, and assignments.")
        with col2:
            st.subheader("Lesson Planner")
            st.write("Create detailed lesson plans with learning objectives and materials.")
        with col3:
            st.subheader("Assessment Assistant")
            st.write("Generate comprehensive student assessments and progress reports.")
        st.markdown("""
            <div style='text-align: center; margin-top: 30px;'>
                <button style="padding: 15px; font-size: 16px; background-color: #6A5ACD; color: white; border: none; border-radius: 8px; cursor: pointer;">
                    Get Started Today
                </button>
            </div>
        """, unsafe_allow_html=True)

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

if __name__ == "__main__":
    main()
