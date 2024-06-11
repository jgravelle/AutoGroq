# #  Thanks to MADTANK:  https://github.com/madtank
# #  README:  https://github.com/madtank/autogenstudio-skills/blob/main/rag/README.md

# import os
# import pickle
# import json
# import argparse

# try:
#     import tiktoken
#     from langchain_community.embeddings import HuggingFaceEmbeddings
#     from langchain_community.vectorstores import FAISS
# except ImportError:
#     raise ImportError("Please install langchain-community first.")

# # Configuration - Users/AI skill developers must update this path to their specific index folder
# # To test with sample data set index_folder to "knowledge"
# CONFIG = {
#     "index_folder": "rag/knowledge",  # TODO: Update this path before using
# }

# class DocumentRetriever:
#     def __init__(self, index_folder):
#         self.index_folder = index_folder
#         self.vectorstore = None
#         self.chunk_id_to_index = None
#         self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
#         self._init()
#         self.enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

#     def _init(self):
#         self.vectorstore = FAISS.load_local(
#             folder_path=self.index_folder,
#             embeddings=self.embeddings,
#         )
#         with open(os.path.join(self.index_folder, "chunk_id_to_index.pkl"), "rb") as f:
#             self.chunk_id_to_index = pickle.load(f)

#     def __call__(self, query: str, size: int = 5, target_length: int = 256):
#         if self.vectorstore is None:
#             raise Exception("Vectorstore not initialized")

#         result = self.vectorstore.similarity_search(query=query, k=size)
#         expanded_chunks = self.do_expand(result, target_length)

#         return json.dumps(expanded_chunks, indent=4)

#     def do_expand(self, result, target_length):
#         expanded_chunks = []
#         # do expansion
#         for r in result:
#             source = r.metadata["source"]
#             chunk_id = r.metadata["chunk_id"]
#             content = r.page_content

#             expanded_result = content
#             left_chunk_id, right_chunk_id = chunk_id - 1, chunk_id + 1
#             left_valid, right_valid = True, True
#             chunk_ids = [chunk_id]
#             while True:
#                 current_length = len(self.enc.encode(expanded_result))
#                 if f"{source}_{left_chunk_id}" in self.chunk_id_to_index:
#                     chunk_ids.append(left_chunk_id)
#                     left_chunk_index = self.vectorstore.index_to_docstore_id[
#                         self.chunk_id_to_index[f"{source}_{left_chunk_id}"]
#                     ]
#                     left_chunk = self.vectorstore.docstore.search(left_chunk_index)
#                     encoded_left_chunk = self.enc.encode(left_chunk.page_content)
#                     if len(encoded_left_chunk) + current_length < target_length:
#                         expanded_result = left_chunk.page_content + expanded_result
#                         left_chunk_id -= 1
#                         current_length += len(encoded_left_chunk)
#                     else:
#                         expanded_result += self.enc.decode(
#                             encoded_left_chunk[-(target_length - current_length) :],
#                         )
#                         current_length = target_length
#                         break
#                 else:
#                     left_valid = False

#                 if f"{source}_{right_chunk_id}" in self.chunk_id_to_index:
#                     chunk_ids.append(right_chunk_id)
#                     right_chunk_index = self.vectorstore.index_to_docstore_id[
#                         self.chunk_id_to_index[f"{source}_{right_chunk_id}"]
#                     ]
#                     right_chunk = self.vectorstore.docstore.search(right_chunk_index)
#                     encoded_right_chunk = self.enc.encode(right_chunk.page_content)
#                     if len(encoded_right_chunk) + current_length < target_length:
#                         expanded_result += right_chunk.page_content
#                         right_chunk_id += 1
#                         current_length += len(encoded_right_chunk)
#                     else:
#                         expanded_result += self.enc.decode(
#                             encoded_right_chunk[: target_length - current_length],
#                         )
#                         current_length = target_length
#                         break
#                 else:
#                     right_valid = False

#                 if not left_valid and not right_valid:
#                     break

#             expanded_chunks.append(
#                 {
#                     "chunk": expanded_result,
#                     "metadata": r.metadata,
#                     # "length": current_length,
#                     # "chunk_ids": chunk_ids
#                 },
#             )
#         return expanded_chunks

# # Example Usage
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description='Retrieve documents based on a query.')
#     parser.add_argument('query', nargs='?', type=str, help='The query to retrieve documents for.')
#     args = parser.parse_args()

#     if not args.query:
#         parser.print_help()
#         print("Error: No query provided.")
#         exit(1)

#     # Ensure the index_folder path is correctly set in CONFIG before proceeding
#     index_folder = CONFIG["index_folder"]
#     if index_folder == "path/to/your/knowledge/directory":
#         print("Error: Index folder in CONFIG has not been set. Please update it to your index folder path.")
#         exit(1)

#     # Instantiate and use the DocumentRetriever with the configured index folder
#     retriever = DocumentRetriever(index_folder=index_folder)
#     query = args.query
#     size = 5  # Number of results to retrieve
#     target_length = 256  # Target length of expanded content
#     results = retriever(query, size, target_length)
#     print(results)