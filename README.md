## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=jgravelle/AutoGroq&type=Timeline)](https://star-history.com/#jgravelle/AutoGroq&Timeline)

# AutoGroq™

AutoGroq is a groundbreaking tool that revolutionizes the way users interact with AI assistants. By dynamically generating tailored teams of AI agents based on your project requirements, AutoGroq eliminates the need for manual configuration and allows you to tackle any question, problem, or project with ease and efficiency.

## NEW THIS WEEK:  SKILL GENERATION!
![image](https://github.com/jgravelle/AutoGroq/assets/3400540/c47f6bc7-03a9-4695-86ab-46dbbda06bec)


## Why AutoGroq?

AutoGroq was born out of the realization that the traditional approach to building AI agents was backwards. Instead of creating agents in anticipation of problems, AutoGroq uses the syntax of the users' needs as the basis for constructing the perfect AI team. It's how we wished Autogen worked from the very beginning.

With AutoGroq, a fully configured workflow, team of agents, and skillset are just a few clicks and a couple of minutes away, without any programming necessary. Our rapidly growing user base of nearly 8000 developers is a testament to the power and effectiveness of AutoGroq.

![image](https://github.com/jgravelle/AutoGroq/assets/3400540/a5294491-2c78-4e07-a587-8a1eacb17a0a)

## Key Features

- **Dynamic Expert Agent Generation**: AutoGroq automatically creates expert agents specialized in various domains or topics, ensuring you receive the most relevant support for your inquiries.
- **Dynamic Workflow Generation**: With AutoGroq, you're just minutes away from having a custom team of experts working on your project. Watch our video tutorial to see it in action!
- **Natural Conversation Flow**: Engage in intuitive and contextually aware conversations with AutoGroq's expert agents, facilitating a seamless exchange of information.
- **Code Snippet Extraction**: AutoGroq intelligently extracts and presents code snippets within a dedicated "Whiteboard" section, making it convenient to reference, copy, or modify code during your interaction.
- **Flexible Agent Management**: Customize your panel of expert agents according to your evolving project needs. Add new agents, modify their expertise, or remove them as required.
- **Advanced Prompt Rephrasing**: AutoGroq employs sophisticated natural language processing techniques to rephrase user inputs, enhancing clarity and ensuring accurate responses from expert agents.
- **Bulk File Upload to Autogen**: With AutoGroq, you can import multiple agents, skills, and workflows into Autogen with a single click, saving you time and effort.
- **Support for Multiple LLMs**: AutoGroq supports Groq, ChatGPT, Ollama, and more, making it compatible with a wide range of language models. You can even create your own provider model to integrate with your preferred LLM.
- **Skill Integration**: Extend your agents' capabilities by adding custom skills. Simply drop a valid skill file into the skills folder, and it will be automatically available for your agents to use.

## Getting Started

To get started with AutoGroq, follow these steps:

1. Install Autogen following Matt Berman's instructions:  https://www.youtube.com/watch?v=mUEFwUU0IfE
2. Install Mini-conda:  https://docs.anaconda.com/free/miniconda/miniconda-install/
3. Open a command prompt and run the following commands:
   md c:\AutoGroq  
   cd c:\AutoGroq  
   conda create -n AutoGroq python=3.11  
   conda activate AutoGroq  
   git clone https://github.com/jgravelle/AutoGroq.git  
   cd AutoGroq
   pip install -r requirements.txt  
   streamlit run c:\AutoGroq\AutoGroq\main.py

## Configuration

To customize the configurations for your local environment, follow these steps:  
  
1. Create a new file called `config_local.py` in the same directory as `config.py`.  
2. Copy the contents of `config_local.py.example` into `config_local.py`.  
3. Modify the values in `config_local.py` according to your specific setup, such as API keys and URLs.  
4. Save the `config_local.py` file.  
  
Note: The `config_local.py` file is not tracked by Git, so your customizations will not be overwritten when pulling updates from the repository.  
  
## How It Works

1. **Initiation**: Begin by entering your query or request in the designated input area.
2. **Engagement**: Click the "Begin" button to initiate the interaction. AutoGroq will rephrase your request and generate the appropriate expert agents.
3. **Interaction**: Select an expert agent to receive specialized assistance tailored to your needs.
4. **Dialogue**: Continue the conversation by providing additional input or context as required, guiding the flow of information.
5. **Review**: The "Discussion" section will display your dialogue history, while the "Whiteboard" section will showcase any extracted code snippets.
6. **Reset**: Use the "Reset" button to clear the current conversation and start a new one whenever needed.

## Live Demo and Video Tutorial

Experience AutoGroq's capabilities firsthand by accessing our online beta version: [AutoGroq Live Demo](https://autogroq.streamlit.app/)

For a step-by-step guide on using AutoGroq, watch our updated video tutorials: [AutoGroq Video Tutorials](https://www.youtube.com/watch?v=hoMqUmUeifU&list=PLPu97iZ5SLTsGX3WWJjQ5GNHy7ZX66ryP&index=15)

## Contributing

We value your feedback and contributions in shaping the future of AutoGroq. If you encounter any issues or have ideas for new features, please share them with us on our [GitHub repository](https://github.com/jgravelle/AutoGroq.git).

## License

AutoGroq is proudly open-source and released under the [MIT License](https://opensource.org/licenses/MIT).

Thank you for choosing AutoGroq as your AI-powered conversational assistant. We are committed to redefining the boundaries of what AI can achieve and empowering you to tackle any question, problem, or project with ease and efficiency.

## Copyright (c)2024 J. Gravelle

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

**1. The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.**

**2. Any modifications made to the Software must clearly indicate that they are derived from the original work, and the name of the original author (J. Gravelle) must remain intact.**

**3. Redistributions of the Software in source code form must also include a prominent notice that the code has been modified from the original.**

THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

