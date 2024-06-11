# #  Thanks to MADTANK:  https://github.com/madtank
# #  README:  https://github.com/madtank/autogenstudio-skills/blob/main/stackoverflow_teams/README.md

# import os
# import requests
# import json
# import sys

# class StackOverflowTeamsSearcher:
#     def __init__(self):
#         self.api_key = os.getenv("STACK_OVERFLOW_TEAMS_API_KEY")
#         if not self.api_key:
#             raise ValueError("API key not found in environment variables")
#         self.base_url = "https://api.stackoverflowteams.com/2.3/search"
#         self.headers = {"X-API-Access-Token": self.api_key}

#     def search(self, query, team_name):
#         params = {"intitle": query, "team": team_name}
#         response = requests.get(self.base_url, headers=self.headers, params=params)

#         if response.status_code != 200:
#             print(f"Error: Received status code {response.status_code}")
#             print(response.text)
#             return None

#         try:
#             data = response.json()
#             simplified_output = []
#             for item in data['items']:
#                 question = {"question": item['title']}
#                 if 'accepted_answer_id' in item:
#                     answer_id = item['accepted_answer_id']
#                     answer_url = f"https://api.stackoverflowteams.com/2.3/answers/{answer_id}"
#                     answer_params = {"team": team_name, "filter": "withbody"}
#                     answer_response = requests.get(answer_url, headers=self.headers, params=answer_params)
#                     if answer_response.status_code == 200:
#                         answer_data = answer_response.json()
#                         first_item = answer_data['items'][0]
#                         if 'body' in first_item:
#                             answer_text = first_item['body']
#                             question['answer'] = answer_text
# #                        else:
# #                            print(f"Question {item['link']} has no answer body")
# #                    else:
# #                        print(f"Error: Received status code {answer_response.status_code}")
# #                        print(answer_response.text)
# #                else:
# #                    print(f"Question {item['link']} has no answer")
#                 simplified_output.append(question)
#             return json.dumps(simplified_output, indent=4)  # Pretty-printing
#         except ValueError as e:
#             print(f"Error parsing JSON: {e}")
#             print("Response text:", response.text)
#             return None

# # Example Usage
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python stackoverflow_teams.py <query>")
#         sys.exit(1)

#     query = sys.argv[1]
#     team_name = "yourteamname"  # TODO Set your team name here
#     # Instantiate and use the StackOverflowTeamsSearcher with the query string passed in
#     searcher = StackOverflowTeamsSearcher()
#     results = searcher.search(query, team_name)
#     print(results)