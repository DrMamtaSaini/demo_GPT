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

# Load the client configuration file
with open("clients_config.json") as config_file:
    clients_config = json.load(config_file)

# Function to get client configuration or a default if client_id is not found
def get_client_config(client_id):
    default_config = {
        "name": "Default Academy",
        "logo": "https://path-to-default-logo.png",
        "theme_color": "#000000"
    }
    return clients_config.get(client_id, default_config)

# Get client_id from the URL query parameter
client_id = st.experimental_get_query_params().get("client_id", ["default"])[0]
client_config = get_client_config(client_id)

# Display the customized content for each client
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

# CSS styling for purple and blue theme
st.markdown(
    """
    <style>
    body { background-color: #f5f5ff; }
    .stApp { color: #4B0082; }
    .sidebar .sidebar-content { background-color: #4B0082; color: white; }
    h1, h2, h3 { color: #4B0082; }
    .stButton>button {
        background-color: #6A5ACD;
        color: white;
        border-radius: 5px;
        font-weight: bold;
        font-size: 16px;
    }
    .stButton>button:hover { background-color: #483D8B; color: white; }
    .stFileUploader { color: #4B0082; }
    .stMarkdown { color: #4B0082; }
    .stAlert, .stSuccess { color: #228B22; background-color: #E0FFE0; border-radius: 5px; }
    </style>
    """,
    unsafe_allow_html=True
)

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
    wrapped_lines.append(current_line.strip())
    return wrapped_lines

# Function to generate a PDF file for assessment reports with custom layout
def generate_assessment_pdf(school_name, student_name, student_id, assessment_id, report_content, file_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, school_name, ln=True, align='C')
    pdf.ln(5)
    pdf.cell(0, 10, f"Assessment Report - {student_name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Student ID: {student_id}", ln=True)
    pdf.cell(0, 10, f"Assessment ID: {assessment_id}", ln=True)
    pdf.ln(10)
    for line in wrap_text(report_content, pdf):
        pdf.cell(0, 10, txt=sanitize_text(line), ln=True)
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

# Function to generate content for educational purposes
def generate_content(school_name, board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions):
    prompt = f"""
    You are an educational content creator for {school_name}. Create {content_type} for the {board} board, {standard} class. 
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
def generate_lesson_plan(school_name, subject, grade, board, duration, topic):
    prompt = f"""
    Create a comprehensive lesson plan for teaching {subject} to {grade} under the {board} board at {school_name}. 
    The lesson duration is {duration}, and the topic of the lesson is {topic}.
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
    full_text = [para.text for para in doc.paragraphs]
    return '\n'.join(full_text)

# Main function
def main():
    st.sidebar.title("EduCreate Pro")
    task = st.sidebar.selectbox("Choose a task", ["Home", "Content Creator", "Lesson Planner", "Assessment"])

    # Home screen
    if task == "Home":
        st.markdown("<h2>Welcome to EduCreate Pro</h2>", unsafe_allow_html=True)
        st.write("Your all-in-one platform for creating educational content, lesson plans, and student assessments.")
        st.write("Choose an option from the sidebar to get started!")

    # Section 1: Educational Content Creation
    elif task == "Content Creator":
        st.markdown("<h2>Educational Content Creation</h2>", unsafe_allow_html=True)
        school_name = st.text_input("Enter School Name:")
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):")
        standard = st.text_input("Enter Standard/Class (e.g., Class 10):")
        topics = st.text_input("Enter Topics (comma-separated):")
        content_type = st.selectbox("Select Content Type", ["Quizzes", "Sample Paper", "Practice Questions", "Summary Notes", "Assignments"])
        total_marks = st.number_input("Enter Total Marks", min_value=1)
        time_duration = st.text_input("Enter Time Duration (e.g., 60 minutes)")
        question_types = st.multiselect("Select Question Types", ["True/False", "Yes/No", "MCQs", "Very Short answers", "Short answers", "Long answers", "Very Long answers"])
        difficulty = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"])
        category = st.selectbox("Select Category", ["Value-based Questions", "Competency Questions", "Image-based Questions", "Paragraph-based Questions", "Mixed of your choice"])
        include_solutions = st.radio("Would you like to include solutions?", ["Yes", "No"])

        if st.button("Generate Educational Content"):
            content = generate_content(school_name, board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions == "Yes")
            st.write(content)
            file_name = f"{school_name}_{content_type}_{standard}.docx"
            save_content_as_doc(content, file_name)
            with open(file_name, "rb") as file:
                st.download_button(label="Download Content as Document", data=file.read(), file_name=file_name)

    # Section 2: Lesson Plan Creation
    elif task == "Lesson Planner":
        st.markdown("<h2>Lesson Plan Creation</h2>", unsafe_allow_html=True)
        school_name = st.text_input("Enter School Name:")
        subject = st.text_input("Enter Subject:")
        grade = st.text_input("Enter Class/Grade:")
        board = st.text_input("Enter Education Board (e.g., CBSE, ICSE):")
        duration = st.text_input("Enter Lesson Duration (e.g., 45 minutes, 1 hour):")
        topic = st.text_input("Enter Lesson Topic:")

        if st.button("Generate Lesson Plan"):
            lesson_plan = generate_lesson_plan(school_name, subject, grade, board, duration, topic)
            st.write(lesson_plan)
            docx_file_name = f"{school_name}_Lesson_Plan_{subject}_{grade}.docx"
            save_content_as_doc(lesson_plan, docx_file_name)
            with open(docx_file_name, "rb") as docx_file:
                st.download_button(label="Download Lesson Plan as DOCX", data=docx_file.read(), file_name=docx_file_name)

    # Section 3: Student Assessment Assistant
    elif task == "Assessment":
        st.markdown("<h2>Student Assessment Assistant</h2>", unsafe_allow_html=True)
        school_name = st.text_input("Enter School Name:")
        student_name = st.text_input("Enter Student Name:")
        student_id = st.text_input("Enter Student ID:")
        assessment_id = st.text_input("Enter Assessment ID:")
        class_name = st.text_input("Enter Class:")
        email_id = st.text_input("Enter Parent's Email ID:")
        question_paper = st.file_uploader("Upload Question Paper (DOCX)", type=["docx"])
        marking_scheme = st.file_uploader("Upload Marking Scheme (DOCX)", type=["docx"])
        answer_sheet = st.file_uploader("Upload Student's Answer Sheet (DOCX)", type=["docx"])

        if st.button("Generate and Send PDF Report"):
            if student_id and assessment_id and email_id and question_paper and marking_scheme and answer_sheet:
                question_paper_content = read_docx(question_paper)
                marking_scheme_content = read_docx(marking_scheme)
                answer_sheet_content = read_docx(answer_sheet)
                report_content = f"Assessment Report\n\nQuestion Paper:\n{question_paper_content}\n\nMarking Scheme:\n{marking_scheme_content}\n\nAnswer Sheet:\n{answer_sheet_content}"
                file_name = f"{school_name}_assessment_report_{student_id}.pdf"
                generate_assessment_pdf(school_name, student_name, student_id, assessment_id, report_content, file_name)
                st.success(f"PDF report generated: {file_name}")
                with open(file_name, "rb") as file:
                    st.download_button(label="Download Report as PDF", data=file.read(), file_name=file_name)
                send_email_with_pdf(email_id, f"Assessment Report for {student_name}", "Please find attached the student's assessment report.", file_name)

if __name__ == "__main__":
    main()
