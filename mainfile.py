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
def generate_pdf(student_details, summary_report, file_name):
    pdf = FPDF()
    pdf.add_page()

    # Set font and add a title with borders
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Assessment Report", ln=True, align='C', border=1)

    # Leave a space after the title
    pdf.ln(10)

    # Section 1: Student Details with border
    pdf.set_font("Arial", size=12)
    for line in student_details:
        wrapped_lines = wrap_text(line, pdf)
        for wrapped_line in wrapped_lines:
            pdf.cell(0, 10, txt=sanitize_text(wrapped_line), ln=True, border=1)

    # Add some space before the summary section
    pdf.ln(10)

    # Section 2: Summary Report with border
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(0, 10, "Summary", ln=True, align='L', border=1)
    pdf.ln(5)

    if summary_report:
        pdf.set_font("Arial", size=12)
        for line in summary_report:
            if ":" in line:
                # Make the field name bold and place it on a new line
                field, value = line.split(":", 1)
                wrapped_lines_field = wrap_text(f"{field}:", pdf)
                for wrapped_field in wrapped_lines_field:
                    pdf.set_font("Arial", size=12, style='B')
                    pdf.cell(0, 10, txt=sanitize_text(wrapped_field), ln=True, border=1)
                
                wrapped_lines_value = wrap_text(value.strip(), pdf)
                for wrapped_value in wrapped_lines_value:
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 10, txt=sanitize_text(wrapped_value), ln=True, border=1)
            else:
                # If no colon, treat as normal text
                wrapped_lines = wrap_text(line, pdf)
                for wrapped_line in wrapped_lines:
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 10, txt=sanitize_text(wrapped_line), ln=True, border=1)
    else:
        pdf.cell(200, 10, txt="No Summary Found", ln=True, border=1)

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

# Function to read content from a DOCX file
def read_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# Main function
def main():
    st.title("Educational Content Creator & Assessment Assistant")

    # Choose between content creation or student assessment assistant
    task = st.sidebar.selectbox("Choose a task", ["Create Educational Content", "Student Assessment Assistant"])

    # Section 2: Student Assessment Assistant
    if task == "Student Assessment Assistant":
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
                student_details = [
                    f"Student Name: {student_name}",
                    f"Student ID: {student_id}",
                    f"Class: {class_name}",
                    f"Assessment ID: {assessment_id}"
                ]
                
                # Split report into question analysis and summary
                if "Question Analysis" in report and "Summary Report" in report:
                    question_analysis = report.split("Question Analysis:")[1].split("Summary Report:")[0].strip()
                    summary_report = report.split("Summary Report:")[1].strip()
                else:
                    summary_report = ["No Summary Found"]
                
                generate_pdf(student_details, summary_report.split('\n'), file_name)
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
