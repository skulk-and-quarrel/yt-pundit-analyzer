import yaml
import os
import logging
import time
import datetime
import re
from ratelimiter import RateLimiter
from llama_index.core.prompts import RichPromptTemplate
from dotenv import load_dotenv

# --- Configuration Loading ---
def load_config(config_path="config.yaml"):
    """Loads configuration from a YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logging.info(f"Configuration loaded successfully from {config_path}")
            return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found at {config_path}. Ensure it exists.")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing configuration file {config_path}: {e}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred loading config: {e}")
        raise

def get_api_key(config):
    """Gets the Google API key, prioritizing environment variables."""
    load_dotenv() # Load .env file if it exists
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        logging.info("Loaded Google API key from environment variable.")
        return api_key

    # Fallback to config file if environment variable not set (not recommended)
    config_api_key = config.get('google_api_key')
    if config_api_key:
        logging.warning("Loading Google API key from config file. Using environment variables (.env file) is strongly recommended for security.")
        return config_api_key

    logging.error("Google API key not found in environment variables (GOOGLE_API_KEY) or config file ('google_api_key').")
    raise ValueError("Missing Google API Key. Set GOOGLE_API_KEY environment variable or add 'google_api_key' to config.yaml (less secure).")

# --- Prompt Loading ---
def load_prompt(file_path: str) -> str:
    """Loads prompt text from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prompt_text = f.read()
            logging.info(f"Prompt loaded successfully from {file_path}")
            return prompt_text
    except FileNotFoundError:
        logging.error(f"Prompt file not found: {file_path}. Ensure the path is correct in config.yaml.")
        raise
    except Exception as e:
        logging.error(f"Error loading prompt file {file_path}: {e}")
        raise

def create_chat_prompt_template(system_prompt_template_str: str) -> RichPromptTemplate:
    """
    Creates a RichPromptTemplate structured for system/user chat roles,
    expecting Jinja variables within the system prompt string.
    """
    # This template uses the loaded file content as the system prompt
    # and expects dynamic content (transcript or takeaways) in the user role.
    chat_template = """
{% chat role="system" %}
{{ system_prompt_template_str }}
{% endchat %}

{% chat role="user" %}
{% if transcript %}
{{ transcript }}
{% elif takeaways_retro and takeaways_early %}
-------------------
# Retrospective
-------------------
{{ takeaways_retro }}

-------------------
# Early Takes
-------------------
{{ takeaways_early }}
{% else %}
Please perform the analysis based on the instructions.
{% endif %}
{% endchat %}
"""
    # Pass the loaded system prompt content as a variable to the Jinja template
    return RichPromptTemplate(chat_template, system_prompt_template_str=system_prompt_template_str)


# --- Rate Limiting ---
def limited_callback(until):
    """Callback function for when rate limit is hit."""
    duration = int(round(until - time.time()))
    logging.warning(f"Rate limit hit. Sleeping for ~{duration} seconds.")
    # The ratelimiter library handles the actual sleep

def setup_rate_limiter(max_calls: int, period: int) -> RateLimiter:
    """Creates and returns a RateLimiter instance."""
    if not isinstance(max_calls, int) or max_calls <= 0:
        raise ValueError("rate_limit_calls must be a positive integer in config.yaml.")
    if not isinstance(period, int) or period <= 0:
        raise ValueError("rate_limit_period must be a positive integer in config.yaml.")
    logging.info(f"Setting up rate limiter: {max_calls} calls / {period} seconds")
    return RateLimiter(max_calls=max_calls, period=period, callback=limited_callback)


# --- Filename Generation Utility ---
def sanitize_filename(name: str) -> str:
    """Removes or replaces characters invalid for filenames."""
    # Remove characters that are definitely invalid in most OS
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace sequences of whitespace with a single underscore
    name = re.sub(r'\s+', '_', name)
    # Remove or replace other potentially problematic characters
    name = re.sub(r'[.,;!]+', '', name)
    # Limit length if necessary
    return name[:100] # Limit filename length for compatibility

def generate_output_filename(set_name: str, analysis_type: str) -> str:
    """Generates the output filename based on the specified format."""
    # analysis_type should be "Early_take", "Retrospective", or "Analysis"
    date_str = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
    sanitized_set_name = sanitize_filename(set_name)
    sanitized_type = sanitize_filename(analysis_type)
    return f"{date_str}_{sanitized_set_name}_{sanitized_type}.md"
