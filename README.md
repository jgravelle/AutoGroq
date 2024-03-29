# AutoGroq
It's how I wish Autogen worked:  quickly, simply, and automatically.

FREE online beta:  https://autogroq-9dylrah8dfyukd4q8phea7.streamlit.app/

1 MINUTE video tutorial:  https://www.youtube.com/watch?v=CzMdqZ83eBk 

Autogroq creates your team of agent assistants on the fly.  Just type in your request!

**AutoGroq** is an AI-powered conversational assistant designed to revolutionize the way users interact with AI tools. Built with the goal of addressing the limitations of existing solutions, AutoGroq offers a user-friendly, powerful, and configuration-free experience. Our platform focuses on providing immediate and relevant assistance by automatically generating expert agents tailored to help you with any question, problem, or project, regardless of its complexity.

## Key Features

- **Dynamic Expert Agent Generation**: AutoGroq's core functionality lies in its ability to dynamically create expert agents specialized in various domains or topics, ensuring you receive the most relevant support for your inquiries.
- **Natural Conversation Flow**: Engage in intuitive and contextually aware conversations with AutoGroq's expert agents, facilitating a seamless exchange of information.
- **Code Snippet Extraction**: AutoGroq intelligently extracts and presents code snippets within a dedicated "Whiteboard" section, making it convenient to reference, copy, or modify code during your interaction.
- **Flexible Agent Management**: Customize your panel of expert agents according to your evolving project needs. Add new agents, modify their expertise, or remove them as required.
- **Advanced Prompt Rephrasing**: AutoGroq employs sophisticated natural language processing techniques to rephrase user inputs, enhancing clarity and ensuring accurate responses from expert agents.

## Getting Started

Experience AutoGroq's capabilities firsthand by accessing our online beta version: https://autogroq-9dylrah8dfyukd4q8phea7.streamlit.app/ 

Please note that AutoGroq is currently under active development, and you may encounter occasional instability as we continue to refine our platform.

## How It Works

1. **Initiation**: Begin by entering your query or request in the designated input area.
2. **Engagement**: Click the "Begin" button to initiate the interaction. AutoGroq will rephrase your request and generate the appropriate expert agents.
3. **Interaction**: Select an expert agent to receive specialized assistance tailored to your needs.
4. **Dialogue**: Continue the conversation by providing additional input or context as required, guiding the flow of information.
5. **Review**: The "Discussion" section will display your dialogue history, while the "Whiteboard" section will showcase any extracted code snippets.
6. **Reset**: Use the "Reset" button to clear the current conversation and start a new one whenever needed.

## AutoGroq Architecture

The AutoGroq codebase is structured into the following main components:

- `main.py`: The core Streamlit application responsible for managing the user interface and user interactions.
- `auto_groq_utils.py`: A utility module containing functions for API interactions, prompt refinement, code extraction, and agent management.
- `agents_management.py`: A module dedicated to the lifecycle management of expert agents, including creation, modification, and deletion.

AutoGroq leverages the Streamlit library and integrates with various APIs to enable natural language processing, code extraction, and dynamic agent generation.

## Contributing

We value your feedback and contributions in shaping the future of AutoGroq. If you encounter any issues or have ideas for new features, please share them with us on our GitHub repository.

## License

AutoGroq is proudly open-source and released under the [MIT License](https://opensource.org/licenses/MIT).

Thank you for choosing AutoGroq as your AI-powered conversational assistant. We are committed to redefining the boundaries of what AI can achieve and empowering you to tackle any question, problem, or project with ease and efficiency.
