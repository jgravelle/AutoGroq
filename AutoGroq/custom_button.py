import streamlit as st
import streamlit.components.v1 as components

def custom_button(expert_name, index, next_agent):
    button_style = """
        <style>
        .custom-button {
            background-color: #f0f0f0;
            color: black;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.25rem;
            cursor: pointer;
        }
        .custom-button.active {
            background-color: green;
            color: white;
        }
        </style>
    """

    button_class = "custom-button active" if next_agent == expert_name else "custom-button"
    button_html = f'<button class="{button_class}">{expert_name}</button>'

    components.html(button_style + button_html, height=50)

def agent_button(expert_name, index, next_agent):
    custom_button(expert_name, index, next_agent)