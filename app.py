from flask import Flask, render_template, request
import requests
import string
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
from tabulate import tabulate

app = Flask(__name__)

def get_wikipedia_url(company_name):
    u_i = string.capwords(company_name)
    lists = u_i.split()
    word = "_".join(lists)
    return "https://en.wikipedia.org/wiki/" + word

def wikibot(url):
    try:
        url_open = requests.get(url)
        soup = BeautifulSoup(url_open.content, 'html.parser')

        # Extract infobox details
        infobox_details = ""
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            infobox_details += "Infobox Details:\n"
            rows = infobox.find_all('tr')
            for row in rows:
                heading = row.find('th')
                detail = row.find('td')
                if heading and detail:
                    infobox_details += "{} :: {}\n".format(heading.text.strip(), detail.text.strip())
            infobox_details += "\n"

        # Extract paragraphs
        key_information = "Key Information:\n"
        paragraphs = soup.find_all('p')
        for i in range(min(100, len(paragraphs))):  # Limiting to the first 100 paragraphs
            key_information += paragraphs[i].text.strip() + "\n"

        return infobox_details, key_information

    except Exception as e:
        return f"Error fetching or parsing data: {e}", ""

def send_data_to_api(company_data, competitor_data):
    try:
        api_key = "AIzaSyD0fToR9qJNVgWoqxLQBLdJTYTiF5Cy7iY"
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        # Format data for API request
        prompt = (
            "Compare the following two companies and provide a detailed SWOT analysis for each company in a table format:\n\n"
            "Company Data:\n"
            "Infobox:\n{company_infobox}\n\n"
            "Key Information:\n{company_key_information}\n\n"
            "Competitor Data:\n"
            "Infobox:\n{competitor_infobox}\n\n"
            "Key Information:\n{competitor_key_information}\n\n"
            "SWOT Comparison Table:\n"
            "Please provide a table comparing the Strengths, Weaknesses, Opportunities, and Threats (SWOT) for each company based on the provided data as well as compare revenue, sales, and so on."
        ).format(
            company_infobox=company_data['infobox'],
            company_key_information=company_data['key_information'],
            competitor_infobox=competitor_data['infobox'],
            competitor_key_information=competitor_data['key_information']
        )

        # Generate content using the model
        response = model.generate_content(prompt)
        print(response)

        # Extract the text from the response
        candidates = response.candidates
        if not candidates:
            raise ValueError("No candidates in response")

        table_text = candidates[0].content.parts[0].text

        # Convert Markdown table to pandas DataFrame
        df = markdown_to_df(table_text)

        # Convert DataFrame to a well-formatted table using tabulate
        table_output = tabulate(df, headers='keys', tablefmt='html')

        return table_output

    except Exception as e:
        return f"Error: {str(e)}"

def markdown_to_df(markdown_str):
    try:
        lines = [line.strip() for line in markdown_str.strip().split('\n') if line.strip()]
        if len(lines) < 2:
            raise ValueError("Not enough lines to parse a table.")

        # Extract headers
        headers = [header.strip() for header in lines[0].strip('|').split('|') if header.strip()]

        # Extract data rows
        data = []
        for line in lines[2:]:  # Skip header and separator lines
            row = [cell.strip() for cell in line.strip('|').split('|')]
            data.append(row)

        # Create DataFrame
        df = pd.DataFrame(data, columns=headers)
        return df

    except Exception as e:
        raise ValueError(f"Error parsing table: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        company_name = request.form['company_name']
        competitor_name = request.form['competitor_name']

        company_url = get_wikipedia_url(company_name)
        company_infobox, company_key_info = wikibot(company_url)

        competitor_url = get_wikipedia_url(competitor_name)
        competitor_infobox, competitor_key_info = wikibot(competitor_url)

        company_data = {
            'infobox': company_infobox,
            'key_information': company_key_info
        }

        competitor_data = {
            'infobox': competitor_infobox,
            'key_information': competitor_key_info
        }

        # Generate the comparison table
        table_output = send_data_to_api(company_data, competitor_data)

        return render_template('index.html', table_output=table_output)

    return render_template('index.html')

@app.route('/save-edits', methods=['POST'])
def save_edits():
    edited_content = request.form['edited_content']
    
    # Here you can save the edited content to a database, a file, or process it further
    # For now, we'll just print it to the console
    print("Edited content:")
    print(edited_content)
    
    # You can redirect back to the main page with a message or updated content
    return render_template('index.html', table_output=edited_content)

if __name__ == "__main__":
    app.run(debug=True)
