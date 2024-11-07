import streamlit as st
import openai
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
import json
import os
from docx import Document

# Load client configuration
with open("clients_config.json") as config_file:
    clients_config = json.load(config_file)

def get_client_config(client_id):
    default_config = {
        "name": "Default Academy",
        "logo": "https://path-to-default-logo.png",
        "theme_color": "#000000"
    }
    return clients_config.get(client_id, default_config)

client_id = st.experimental_get_query_params().get("client_id", ["default"])[0]
client_config = get_client_config(client_id)

# Display client-specific content
st.sidebar.image(client_config["logo"], width=100)
st.sidebar.title("EduCreate Pro")
st.sidebar.markdown("---")
st.sidebar.write(f"Welcome, {client_config['name']}!")

# Function to sanitize text for PDF
def sanitize_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

# Function to wrap text in PDF
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

# Function to generate content
def generate_content(school_name, board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions):
    prompt = f"""
    You are an educational content creator for {school_name}. Create {content_type} for the {board} board, {standard} class. 
    Topics: {topics}. Marks: {total_marks}, Time: {time_duration}. Question types: {', '.join(question_types)}. Difficulty: {difficulty}, Category: {category}.
    {"Include solutions." if include_solutions else "Exclude solutions."}
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to generate lesson plan
def generate_lesson_plan(school_name, subject, grade, board, duration, topic):
    prompt = f"""
    Create a lesson plan for {subject}, {grade} ({board}). Duration: {duration}. Topic: {topic}.
    Include objectives, resources, teaching segments, activities, and assessments.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# Function to save content as DOCX
def save_content_as_doc(content, file_name):
    doc = Document()
    for line in content.split('\n'):
        doc.add_paragraph(line)
    doc.save(file_name)

# Function to read content from a DOCX file
def read_docx(file):
    doc = Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])

# Function to generate a PDF report for assessment
def generate_assessment_pdf(school_name, student_name, student_id, assessment_id, report_content, file_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, school_name, ln=True, align='C')
    pdf.ln(10)
    pdf.cell(0, 10, f"Assessment Report - {student_name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Student ID: {student_id}", ln=True)
    pdf.cell(0, 10, f"Assessment ID: {assessment_id}", ln=True)
    pdf.ln(10)
    for line in report_content.split('\n'):
        pdf.cell(0, 10, sanitize_text(line), ln=True)
    pdf.output(file_name)

# Function to send email with PDF attachment
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

# Main function to handle all sections
def main():
    # Sidebar Navigation
    section = st.sidebar.radio("Navigation", ["Home", "Content Creator", "Lesson Planner", "Assessment"])

    # Home Section
    if section == "Home":
        st.title("Welcome to EduCreate Pro")
        st.subheader("Your all-in-one platform for educational content creation, lesson planning, and assessments.")
        st.markdown("""
        ### Modules
        - **Content Creator**: Generate quizzes, sample papers, and assignments.
        - **Lesson Planner**: Create comprehensive lesson plans with learning objectives and resources.
        - **Assessment Assistant**: Evaluate student answers and generate detailed reports.
        """)
        st.button("Get Started Today")

    # Content Creator Section
    elif section == "Content Creator":
        st.title("Content Creator")
        school_name = st.text_input("School Name")
        board = st.text_input("Education Board (e.g., CBSE, ICSE)")
        standard = st.text_input("Class/Standard (e.g., Class 10)")
        topics = st.text_input("Topics (comma-separated)")
        content_type = st.selectbox("Content Type", ["Quizzes", "Sample Paper", "Practice Questions", "Summary Notes", "Assignments"])
        total_marks = st.number_input("Total Marks", min_value=1)
        time_duration = st.text_input("Time Duration (e.g., 60 minutes)")
        question_types = st.multiselect("Question Types", ["True/False", "MCQs", "Short answers", "Long answers"])
        difficulty = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])
        category = st.selectbox("Category", ["Value-based", "Competency", "Mixed"])
        include_solutions = st.radio("Include solutions?", ["Yes", "No"])

        if st.button("Generate Content"):
            content = generate_content(school_name, board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions == "Yes")
            st.write("### Generated Content")
            st.write(content)
            doc_file_name = f"{school_name}_{content_type}_{standard}.docx"
            save_content_as_doc(content, doc_file_name)
            with open(doc_file_name, "rb") as file:
                st.download_button("Download Content as DOCX", file.read(), doc_file_name)

    # Lesson Planner Section
    elif section == "Lesson Planner":
        st.title("Lesson Planner")
        school_name = st.text_input("School Name")
        subject = st.text_input("Subject")
        grade = st.text_input("Class/Grade")
        board = st.text_input("Education Board")
        duration = st.text_input("Lesson Duration (e.g., 45 minutes)")
        topic = st.text_input("Topic")

        if st.button("Generate Lesson Plan"):
            lesson_plan = generate_lesson_plan(school_name, subject, grade, board, duration, topic)
            st.write("### Generated Lesson Plan")
            st.write(lesson_plan)
            docx_file_name = f"{school_name}_Lesson_Plan_{subject}_{grade}.docx"
            save_content_as_doc(lesson_plan, docx_file_name)
            with open(docx_file_name, "rb") as file:
                st.download_button("Download Lesson Plan as DOCX", file.read(), docx_file_name)

    # Assessment Section
    elif section == "Assessment":
        st.title("Student Assessment Assistant")
        school_name = st.text_input("School Name")
        student_name = st.text_input("Student Name")
        student_id = st.text_input("Student ID")
        assessment_id = st.text_input("Assessment ID")
        email_id = st.text_input("Parent's Email ID")
        question_paper = st.file_uploader("Upload Question Paper (DOCX)", type=["docx"])
        marking_scheme = st.file_uploader("Upload Marking Scheme (DOCX)", type=["docx"])
        answer_sheet = st.file_uploader("Upload Answer Sheet (DOCX)", type=["docx"])

        if st.button("Generate and Send Report"):
            if question_paper and marking_scheme and answer_sheet:
                question_content = read_docx(question_paper)
                marking_content = read_docx(marking_scheme)
                answer_content = read_docx(answer_sheet)
                prompt = f"Generate assessment based on:\n{question_content}\n{marking_content}\n{answer_content}"
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}]
                )
                report_content = response['choices'][0]['message']['content']
                pdf_file_name = f"{school_name}_Assessment_Report_{student_id}.pdf"
                generate_assessment_pdf(school_name, student_name, student_id, assessment_id, report_content, pdf_file_name)
                with open(pdf_file_name, "rb") as file:
                    st.download_button("Download Report as PDF", file.read(), pdf_file_name)
                send_email_with_pdf(email_id, f"Assessment Report for {student_name}", "Please find the attached assessment report.", pdf_file_name)
                st.success("Report generated and emailed successfully.")
            else:
                st.error("Please upload all required files.")

if __name__ == "__main__":
    main()
