# #  Thanks to MADTANK:  https://github.com/madtank
# #  README:  https://github.com/madtank/autogenstudio-skills/blob/main/slack/README.md

# import os
# import requests
# import json
# import re
# import sys

# class SlackSearcher:
#     def __init__(self):
#         self.api_token = os.getenv("SLACK_API_TOKEN")
#         if not self.api_token:
#             raise ValueError("Slack API token not found in environment variables")
#         self.base_url = "https://slack.com/api"
#         self.headers = {"Authorization": f"Bearer {self.api_token}"}
#         # Replace these example channel names with the actual channel names you want to search
#         self.channel_names = ["general", "random"]

#     def search(self, query):
#         query_with_channels = self.build_query_with_channels(query)
#         search_url = f"{self.base_url}/search.messages"
#         params = {"query": query_with_channels}
#         response = requests.get(search_url, headers=self.headers, params=params)

#         if response.status_code != 200:
#             print(f"Error: Received status code {response.status_code}")
#             print(response.text)
#             return None

#         try:
#             data = response.json()
#             if not data['ok']:
#                 print(f"Error: {data['error']}")
#                 return None

#             simplified_output = []
#             for message in data['messages']['matches']:
#                 simplified_message = {
#                     "user": message['user'],
#                     "text": message['text'],
#                     "permalink": message['permalink']
#                 }
#                 thread_ts = self.extract_thread_ts(message['permalink'])
#                 if thread_ts:
#                     thread_messages = self.get_thread_messages(message['channel']['id'], thread_ts)
#                     simplified_message['thread'] = thread_messages
#                 simplified_output.append(simplified_message)
#             return json.dumps(simplified_output, indent=4)  # Pretty-printing
#         except ValueError as e:
#             print(f"Error parsing JSON: {e}")
#             print("Response text:", response.text)
#             return None

#     def build_query_with_channels(self, query):
#         channel_queries = [f"in:{channel}" for channel in self.channel_names]
#         return f"{query} {' '.join(channel_queries)}"

#     def extract_thread_ts(self, permalink):
#         match = re.search(r"thread_ts=([0-9.]+)", permalink)
#         return match.group(1) if match else None

#     def get_thread_messages(self, channel_id, thread_ts):
#         thread_url = f"{self.base_url}/conversations.replies"
#         params = {"channel": channel_id, "ts": thread_ts}
#         response = requests.get(thread_url, headers=self.headers, params=params)

#         if response.status_code != 200 or not response.json()['ok']:
#             print(f"Error fetching thread messages: {response.text}")
#             return []

#         thread_messages = []
#         for message in response.json()['messages']:
#             if message['ts'] != thread_ts:  # Exclude the parent message
#                 thread_messages.append({
#                     "user": message['user'],
#                     "text": message['text']
#                 })
#         return thread_messages

# # Example Usage
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python slack_search.py <query>")
#         sys.exit(1)

#     query = sys.argv[1]
#     searcher = SlackSearcher()
#     results = searcher.search(query)
#     print(results)