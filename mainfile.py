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

# Function to generate a PDF report with better formatting and borders
def generate_pdf(student_details, question_table, summary_report, file_name):
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Assessment Report", ln=True, align='C', border=1)
    pdf.ln(10)

    # Student Details
    pdf.set_font("Arial", size=12)
    for line in student_details:
        wrapped_lines = wrap_text(line, pdf)
        for wrapped_line in wrapped_lines:
            pdf.cell(0, 10, txt=sanitize_text(wrapped_line), ln=True, border=1)
    pdf.ln(10)

    # Question Analysis in Tabular Form
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Question Analysis", ln=True, border=1)
    pdf.set_font("Arial", size=10)
    col_widths = [30, 30, 30, 20, 20, 50]  # Customize column widths

    # Table headers
    headers = ["Topic", "Subtopic", "Question Number", "Score", "Concept Cleared", "Suggestions"]
    for idx, header in enumerate(headers):
        pdf.cell(col_widths[idx], 10, header, border=1, ln=0 if idx < len(headers) - 1 else 1)
    
    # Table rows
    for row in question_table:
        for idx, cell in enumerate(row):
            pdf.cell(col_widths[idx], 10, sanitize_text(str(cell)), border=1, ln=0 if idx < len(row) - 1 else 1)
    pdf.ln(10)

    # Summary Report
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Summary", ln=True, align='L', border=1)
    pdf.set_font("Arial", size=12)
    for line in summary_report:
        pdf.cell(0, 10, txt=sanitize_text(line), ln=True, border=1)

    # Save the PDF
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

# Function to read content from a DOCX file
def read_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# Function to save content as a Word document
def save_content_as_doc(content, file_name):
    doc = Document()
    for line in content.split('\n'):
        doc.add_paragraph(line)
    doc.save(file_name)

# Main function
def main():
    st.title("Educational Content Creator & Assessment Assistant")

    # Choose between content creation or student assessment assistant
    task = st.sidebar.selectbox("Choose a task", ["Create Educational Content", "Student Assessment Assistant"])

    # Section 1: Educational Content Creation
    if task == "Create Educational Content":
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
            content_prompt = f"Create {content_type} for the {board} board, {standard} class on {topics}. Include questions of {difficulty} difficulty in {category}. Total Marks: {total_marks}. Duration: {time_duration}."
            if include_solutions == "Yes":
                content_prompt += " Include solutions."
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": content_prompt}]
            )
            content = response['choices'][0]['message']['content']
            st.write("### Generated Educational Content")
            st.write(content)

            # Save as Word document
            file_name = f"{content_type}_{standard}.docx"
            save_content_as_doc(content, file_name)

            with open(file_name, "rb") as file:
                st.download_button(label="Download Content as Document", data=file.read(), file_name=file_name)

    # Section 2: Student Assessment Assistant
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
                Analyze the student's answer sheet using the question paper and marking scheme.

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

                Provide:
                1. Question Analysis in table format with columns:
                    - Topic
                    - Subtopic
                    - Question Number
                    - Score
                    - Concept Cleared (Yes/No)
                    - Suggestions
                2. Summary with:
                    - Final Score
                    - Grade
                    - Areas of Strength
                    - Areas for Improvement
                """

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}]
                )
                report = response['choices'][0]['message']['content']

                # Parsing and preparing data for the table and summary
                question_table = []  # Table rows as lists
                summary_report = []

                # Check if "Question Analysis:" and "Summary Report:" exist in the response
                if "Question Analysis:" in report and "Summary Report:" in report:
                    question_section = report.split("Question Analysis:")[1].split("Summary Report:")[0].strip()
                    summary_section = report.split("Summary Report:")[1].strip()

                    # Parse the question analysis into a table format
                    for line in question_section.split('\n'):
                        row = line.split('|')
                        question_table.append(row)

                    # Parse the summary section
                    summary_report = summary_section.split('\n')
                else:
                    st.warning("One or more sections (Question Analysis or Summary Report) were not found in the report.")
                    summary_report = ["No Summary Found"]

                # Generate PDF
                file_name = f"assessment_report_{student_id}.pdf"
                student_details = [
                    f"Student Name: {student_name}",
                    f"Student ID: {student_id}",
                    f"Class: {class_name}",
                    f"Assessment ID: {assessment_id}"
                ]
                
                generate_pdf(student_details, question_table, summary_report, file_name)
                st.success(f"PDF report generated: {file_name}")

                st.write("### Assessment Report")
                st.write(report)
                with open(file_name, "rb") as file:
                    st.download_button(label="Download Report as PDF", data=file.read(), file_name=file_name)

                subject = f"Assessment Report for Student {student_name}"
                body = "Please find attached the student's assessment report."
                send_email_with_pdf(email_id, subject, body, file_name)
            else:
                st.error("Please provide all required inputs.")

if __name__ == "__main__":
    main()
