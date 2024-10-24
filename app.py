from flask import Flask, render_template, request, jsonify
import requests
import PyPDF2
import pandas as pd
import os

bot = Flask(__name__)

API_KEY = "4e08d219725c475a8623f1618397fc2e"
ENDPOINT = "https://lida.openai.azure.com/openai/deployments/college/chat/completions?api-version=2024-02-15-preview"

os.makedirs('uploads', exist_ok=True)
chat_history = []


def read_pdf(file_path):
    text_content = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text_content += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
    return text_content


def read_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        return df.to_string()
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return ""


def read_excel(file_path):
    text_content = ""
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        text_content = df.to_string()
    except Exception as e:
        print(f"Error reading Excel file: {e}")
    return text_content


@bot.route('/')
def index():
    return render_template('renderdash_frontend.html')


@bot.route('/submit', methods=['POST'])
def submit():
    file = request.files['file']
    question = request.form.get('question')

    file_path = os.path.join('uploads', file.filename)
    file.save(file_path)

    file_extension = os.path.splitext(file.filename)[-1].lower()

    if file_extension == '.pdf':
        text_content = read_pdf(file_path)
    elif file_extension == '.csv':
        text_content = read_csv(file_path)
    elif file_extension in ['.xlsx', '.xls']:
        text_content = read_excel(file_path)
    else:
        return "Unsupported file type. Please upload a PDF ,CSV file or Excel File."

    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY,
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": f"You are Business Strategy Analyst. (dont give any code) {text_content[:10000]}? {question}"
            }
        ],
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 800
    }

    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Failed to make the request. Error: {e}"

    response_data = response.json()
    api_response = response_data.get("choices", [{}])[0].get("message", {}).get("content",
                                                                                "No content received from API.")

    formatted_message = format_output(api_response)

    chat_history.append({"question": question, "answer": formatted_message})
    return jsonify(chat_history)


def format_output(api_response):
    cleaned_response = api_response.replace("*", "").strip()

    lines = cleaned_response.split("\n")
    formatted_output = ""

    for line in lines:
        line = line.strip()
        if line.startswith("###"):
            formatted_output += f"<h3>{line[4:].strip()}</h3>\n"
        elif line.startswith("##"):
            formatted_output += f"<h4>{line[3:].strip()}</h4>\n"
        elif line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith(
                "4.") or line.startswith("5.") or line.startswith("6.") or line.startswith("7.") or line.startswith(
                "8.") or line.startswith("9.") or line.startswith("10."):
            formatted_output += f"<p>{line.strip()}</p>\n"
        elif line.startswith("- "):
            formatted_output += f"<li>{line[2:].strip()}</li>\n"
        else:
            formatted_output += f"<p>{line}</p>\n"
    if "<li>" in formatted_output:
        formatted_output = f"<ul>{formatted_output}</ul>"

    return formatted_output


if __name__ == '__main__':
    bot.run(debug=True)