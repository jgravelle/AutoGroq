# prompts.py

def create_project_manager_prompt(rephrased_text):
    return f"""
                As a Project Manager, create a project plan for:
                {rephrased_text}
                Include:

                Project Outline:

                Comprehensive overview
                Logical structure
                Key Deliverables: List in order of completion


                Expert Team:

                Roles based on project needs
                Minimum necessary team size
                For each expert:
                a) Role title
                b) Key responsibilities
                c) Essential expertise



                Format:
                Project Outline:
                [Your detailed outline]
                Key Deliverables:
                [Numbered list]
                Team of Experts:
                [Description of the ideal team of experts]
            """


def get_agent_prompt(rephrased_request):
    return f"""
        Based on the following user request, please create a detailed and comprehensive description 
        of an AI agent that can effectively assist with the request:

        User Request: "{rephrased_request}"

        Provide a clear and concise description of the agent's role, capabilities, and expertise.
        The description should be efficiently written in a concise, professional and engaging manner, 
        highlighting the agent's ability to understand and respond to the request efficiently.

        Agent Description:
        """


def get_agents_prompt():
    return """
    You are an expert system designed to format the JSON describing each member of the team 
    of AI agents listed in the 'Team of Experts' section below. Follow these guidelines:
    1. Agent Roles: Clearly transcribe the titles of each agent listed.
    2. Expertise Description: Provide a brief but thorough description of each agent's expertise 
       based on the provided information.
    3. Format: Return the results in JSON format with values labeled as expert_name, description, role, goal, and backstory.
       'expert_name' should be the agent's title, not their given or proper name.

    Return ONLY the JSON array, with no other text:
    [
        {
            "expert_name": "agent_title",
            "description": "agent_description",
            "role": "agent_role",
            "goal": "agent_goal",
            "backstory": "agent_backstory"
        }
    ]
    """
        
# Contributed by ScruffyNerf
def get_generate_tool_prompt(rephrased_tool_request):
    return f'''
                Based on the rephrased tool request below, please do the following:

                1. Do step-by-step reasoning and think to better understand the request.
                2. Code the best Autogen Studio Python tool as per the request as a [tool_name].py file.
                3. Return only the tool file, no commentary, intro, or other extra text. If there ARE any non-code lines, 
                    please pre-pend them with a '#' symbol to comment them out.
                4. A proper tool will have these parts:
                   a. Imports (import libraries needed for the tool)
                   b. Function definition AND docstrings (this helps the LLM understand what the function does and how to use it)
                   c. Function body (the actual code that implements the function)
                   d. (optional) Example usage - ALWAYS commented out
                   Here is an example of a well formatted tool:

                   # Tool filename: save_file_to_disk.py
                   # Import necessary module(s)
                   import os

                   def save_file_to_disk(contents, file_name):
                   # docstrings
                   """
                   Saves the given contents to a file with the given file name.

                   Parameters:
                   contents (str): The string contents to save to the file.
                   file_name (str): The name of the file, including its extension.

                   Returns:
                   str: A message indicating the success of the operation.
                   """

                   # Body of tool

                   # Ensure the directory exists; create it if it doesn't
                   directory = os.path.dirname(file_name)
                   if directory and not os.path.exists(directory):
                      os.makedirs(directory)

                   # Write the contents to the file
                   with open(file_name, 'w') as file:
                      file.write(contents)
    
                   return f"File file_name has been saved successfully."

                   # Example usage:
                   # contents_to_save = "Hello, world!"
                   # file_name = "example.txt"
                   # print(save_file_to_disk(contents_to_save, file_name))

                Rephrased tool request: "{rephrased_tool_request}"
                '''


def get_moderator_prompt(discussion_history, goal, last_comment, last_speaker, team_members_str, current_deliverable, current_phase):
    return f"""
        This agent is our Moderator Bot. Its goal is to mediate the conversation between a team of AI agents 
        in a manner that persuades them to act in the most expeditious and thorough manner to accomplish their goal. 
        This will entail considering the user's stated goal, the conversation thus far, the descriptions 
        of all the available agent/experts in the current team, the last speaker, and their remark. 
        Based upon a holistic analysis of all the facts at hand, use logic and reasoning to decide which team member should speak next. 
        Then draft a prompt directed at that agent that persuades them to act in the most expeditious and thorough manner toward helping this team of agents 
        accomplish their goal.

        Their overall goal is: {goal}.
        The current deliverable they're working on is: {current_deliverable}
        The current implementation phase is: {current_phase}
        The last speaker was {last_speaker}, who said: {last_comment}

        Here is the current conversational discussion history: {discussion_history}

        And here are the team members and their descriptions:
        {team_members_str}

        IMPORTANT: Your response must start with "To [Agent Name]:", where [Agent Name] is one of the valid team members listed above. Do not address tools or non-existent team members.

        This agent's response should be JUST the requested prompt addressed to the next agent, and should not contain 
        any introduction, narrative, or any other superfluous text whatsoever.

        If you believe the current phase of the deliverable has been satisfactorily completed, include the exact phrase 
        "PHASE_COMPLETED" at the beginning of your response, followed by your usual prompt to the next agent focusing on 
        the next phase or deliverable.

        Remember, we are now in the {current_phase} phase. The agents should focus on actually implementing, coding, 
        testing, or deploying the solutions as appropriate for the current phase, not just planning.
    """


def get_rephrased_user_prompt(user_request):
    return f"""Act as a professional prompt engineer and refactor the following 
                user request into an optimized prompt. This agent's goal is to rephrase the request 
                with a focus on the satisfying all following the criteria without explicitly stating them:
        1. Clarity: Ensure the prompt is clear and unambiguous.
        2. Specific Instructions: Provide detailed steps or guidelines.
        3. Context: Include necessary background information.
        4. Structure: Organize the prompt logically.
        5. Language: Use concise and precise language.
        6. Examples: Offer examples to illustrate the desired output.
        7. Constraints: Define any limits or guidelines.
        8. Engagement: Make the prompt engaging and interesting.
        9. Feedback Mechanism: Suggest a way to improve or iterate on the response.

        Apply introspection and reasoning to reconsider your own prompt[s] to:
        Clarify ambiguities
        Break down complex tasks
        Provide essential context
        Structure logically
        Use precise, concise language
        Include relevant examples
        Specify constraints

        Do NOT reply with a direct response to these instructions OR the original user request. Instead, rephrase the user's request as a well-structured prompt, and
        return ONLY that rephrased prompt. Do not preface the rephrased prompt with any other text or superfluous narrative.
        Do not enclose the rephrased prompt in quotes. This agent will be successful only if it returns a well-formed rephrased prompt ready for submission as an LLM request.
        User request: "{user_request}"
        Rephrased:
    """

        