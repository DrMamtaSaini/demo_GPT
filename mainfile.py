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

from fpdf import FPDF

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
            content = generate_content(board, standard, topics, content_type, total_marks, time_duration, question_types, difficulty, category, include_solutions == "Yes")
            st.write("### Generated Educational Content")
            st.write(content)
            
            # Save as Word document
            file_name = f"{content_type}_{standard}.docx"
            save_content_as_doc(content, file_name)
            
            # Download button for the document file
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

        # Upload Question Paper, Marking Scheme, and Answer Sheet
        question_paper = st.file_uploader("Upload Question Paper (CSV)", type=["csv"])
        marking_scheme = st.file_uploader("Upload Marking Scheme (CSV)", type=["csv"])
        answer_sheet = st.file_uploader("Upload Student's Answer Sheet (CSV)", type=["csv"])

        # Generate Assessment Report and Email PDF
        if st.button("Generate and Send PDF Report"):
            if student_id and assessment_id and email_id and question_paper and marking_scheme and answer_sheet:
                # Load the CSV files
                question_paper_df = pd.read_csv(question_paper)
                marking_scheme_df = pd.read_csv(marking_scheme)
                answer_sheet_df = pd.read_csv(answer_sheet)

                # Enhanced GPT-4 prompt with explicit structure for the report
                prompt = f"""
                You are an educational assessment assistant. Analyze the student's performance and generate a well-structured report.

                Student Name: {student_name}
                Student ID: {student_id}
                Class: {class_name}
                Assessment ID: {assessment_id}

                Here is the question paper: {question_paper_df.to_string(index=False)}
                Here is the marking scheme: {marking_scheme_df.to_string(index=False)}
                Here is the student's answer sheet: {answer_sheet_df.to_string(index=False)}

                The report should include two sections clearly labeled:
                1. Question Details (include the following columns for each question):
                    - Topic
                    - Subtopic
                    - Question Number
                    - Child's Score
                    - Accuracy
                    - Concept Cleared (Yes/No)
                    - Suggestion

                2. Summary Report (include the following):
                    - Final Score
                    - Grade
                    - Overall Accuracy
                    - Overall Concept Clarity
                    - Strengths
                    - Areas of Improvement
                    - Final Remarks/Suggestions

                Please clearly separate these two sections with the labels "Question Details:" and "Summary:". Ensure that the summary section always appears, even if the student has not provided enough answers.
                """
                # Call GPT-4 API to generate assessment report
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}]
                )
                report = response['choices'][0]['message']['content']

                # Safely handle missing sections and split the report into question details and summary
                question_details = []
                summary_report = []
                
                if "Question Details:" in report and "Summary:" in report:
                    question_details_section = report.split("Question Details:")[1].split("Summary:")[0].strip()
                    question_details = [line.strip().split('\n') for line in question_details_section.split('\n') if line.strip()]
                    
                    summary_report_section = report.split("Summary:")[1].strip()
                    summary_report = summary_report_section.split('\n')
                else:
                    st.warning("One or more sections (Question Details or Summary) were not found in the report.")
                    # Fallback if summary is not found
                    summary_report = ["No Summary Found"]

                # Save the report as a PDF
                file_name = f"assessment_report_{student_id}.pdf"
                student_details = [
                    f"Student Name: {student_name}",
                    f"Student ID: {student_id}",
                    f"Class: {class_name}",
                    f"Assessment ID: {assessment_id}"
                ]
                
                # Generate PDF
                generate_pdf(student_details, summary_report, file_name)
                st.success(f"PDF report generated: {file_name}")

                # Display report on the screen
                st.write("### Assessment Report")
                st.write(report)

                # Download the report
                st.download_button(label="Download Report as PDF", data=open(file_name, 'rb').read(), file_name=file_name)

                # Send the report via email
                subject = f"Assessment Report for Student {student_name}"
                body = "Please find attached the student's assessment report."
                send_email_with_pdf(email_id, subject, body, file_name)
            else:
                st.error("Please provide all required inputs (Student Name, Class, Student ID, Assessment ID, Parent's Email, Question Paper, Marking Scheme, and Answer Sheet).")

if __name__ == "__main__":
    main()
