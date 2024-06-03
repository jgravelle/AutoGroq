
import datetime
import markdown2
import os
import re 

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from xml.sax.saxutils import escape


def create_agent_data(agent):
    expert_name = agent['config']['name']
    description = agent['config'].get('description', agent.get('description', ''))  # Get description from config, default to empty string if missing
    current_timestamp = datetime.datetime.now().isoformat()

    formatted_expert_name = sanitize_text(expert_name)
    formatted_expert_name = formatted_expert_name.lower().replace(' ', '_')

    sanitized_description = sanitize_text(description)
    temperature_value = 0.1  # Default value for temperature

    autogen_agent_data = {
        "type": "assistant",
        "config": {
            "name": formatted_expert_name,
            "llm_config": {
                "config_list": [
                    {
                        "user_id": "default",
                        "timestamp": current_timestamp,
                        "model": agent['config']['llm_config']['config_list'][0]['model'],
                        "base_url": None,
                        "api_type": None,
                        "api_version": None,
                        "description": "OpenAI model configuration"
                    }
                ],
                "temperature": temperature_value,
                "cache_seed": None,
                "timeout": None,
                "max_tokens": None,
                "extra_body": None
            },
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 8,
            "system_message": f"You are a helpful assistant that can act as {expert_name} who {sanitized_description}.",
            "is_termination_msg": None,
            "code_execution_config": None,
            "default_auto_reply": "",
            "description": description
        },
        "timestamp": current_timestamp,
        "user_id": "default",
        "skills": []
    }

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_folder = os.path.join(project_root, "skills")
    skill_files = [f for f in os.listdir(skill_folder) if f.endswith(".py")]

    for skill_file in skill_files:
        skill_name = os.path.splitext(skill_file)[0]
        if agent.get(skill_name, False):
            skill_file_path = os.path.join(skill_folder, skill_file)
            with open(skill_file_path, 'r') as file:
                skill_data = file.read()
            skill_json = create_skill_data(skill_data)
            autogen_agent_data["skills"].append(skill_json)

    crewai_agent_data = {
        "name": expert_name,
        "description": description,
        "verbose": True,
        "allow_delegation": True
    }

    return autogen_agent_data, crewai_agent_data


def create_skill_data(python_code):
    # Extract the function name from the Python code
    function_name_match = re.search(r"def\s+(\w+)\(", python_code)
    if function_name_match:
        function_name = function_name_match.group(1)    
    else:
        function_name = "unnamed_function"

    # Extract the skill description from the docstring
    docstring_match = re.search(r'"""(.*?)"""', python_code, re.DOTALL)
    if docstring_match:
        skill_description = docstring_match.group(1).strip()
    else:
        skill_description = "No description available"

    # Get the current timestamp
    current_timestamp = datetime.datetime.now().isoformat()

    # Create the skill data dictionary
    skill_data = {
        "title": function_name,
        "content": python_code,
        "file_name": f"{function_name}.json",
        "description": skill_description,
        "timestamp": current_timestamp,
        "user_id": "default"
    }

    return skill_data
        

def create_workflow_data(workflow):
    # Sanitize the workflow name
    sanitized_workflow_name = sanitize_text(workflow["name"])
    sanitized_workflow_name = sanitized_workflow_name.lower().replace(' ', '_')

    return workflow


def generate_pdf(text):
    # Convert Markdown to HTML
    html = markdown2.markdown(text)

    # Define styles
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_heading1 = styles["Heading1"]
    style_heading2 = styles["Heading2"]
    style_code = styles["Code"]

    # Create a BytesIO object to store the PDF data
    pdf_buffer = BytesIO()

    # Create a SimpleDocTemplate object
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

    # Create a list to hold the flowables (paragraphs, spacers, etc.)
    story = []

    # Split the HTML into lines
    lines = html.split("\n")

    # Parse the HTML and create styled paragraphs
    for line in lines:
        if line.startswith("<h1>"):
            text = line.replace("<h1>", "").replace("</h1>", "")
            story.append(Paragraph(escape(text), style_heading1))
            story.append(Spacer(1, 0.2 * inch))
        elif line.startswith("<h2>"):
            text = line.replace("<h2>", "").replace("</h2>", "")
            story.append(Paragraph(escape(text), style_heading2))
            story.append(Spacer(1, 0.1 * inch))
        elif line.startswith("<code>"):
            text = line.replace("<code>", "").replace("</code>", "")
            story.append(Paragraph(escape(text), style_code))
        else:
            story.append(Paragraph(escape(line), style_normal))

    # Build the PDF document
    doc.build(story)

    # Get the PDF data from the BytesIO object
    pdf_data = pdf_buffer.getvalue()

    return pdf_data


def sanitize_text(text): 
    # Remove non-ASCII characters 
    text = re.sub(r'[^\x00-\x7F]+', '', text) 
    # Remove non-alphanumeric characters except for standard punctuation 
    text = re.sub(r'[^a-zA-Z0-9\s.,!?:;\'"-]+', '', text) 
    return text 
