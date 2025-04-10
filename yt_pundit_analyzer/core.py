import logging
import os
from llama_index.readers.youtube_transcript import YoutubeTranscriptReader
from llama_index.llms.gemini import Gemini
from llama_index.core.prompts import RichPromptTemplate
from ratelimiter import RateLimiter
# Import utility functions from the same package
from .utils import generate_output_filename

# --- Transcript Fetching ---
def get_transcript(url: str, reader: YoutubeTranscriptReader) -> str:
    """Fetches transcript for a given YouTube URL."""
    logging.info(f"Fetching transcript for: {url}")
    try:
        # Note: load_data expects a list of URLs
        documents = reader.load_data(ytlinks=[url])
        if not documents:
            logging.warning(f"No transcript documents found for {url}. Transcripts might be disabled or the video unavailable.")
            return "Error fetching transcript: No documents found."
        # Concatenate text from all document parts (sometimes transcripts are split)
        transcript = "\n".join([doc.get_content() for doc in documents])
        if not transcript.strip():
             logging.warning(f"Fetched transcript for {url} is empty.")
             return "Error fetching transcript: Transcript is empty."
        logging.info(f"Transcript fetched successfully for {url} (length: {len(transcript)}).")
        return transcript
    except Exception as e:
        # Catch potential errors from youtube_transcript_api or LlamaIndex reader
        logging.error(f"Failed to fetch transcript for {url}: {e}")
        return f"Error fetching transcript: {e}" # Return error message

# --- Function to save output ---
def save_output(output_folder: str, filename: str, content: str):
    """Saves content to a file in the specified folder."""
    try:
        # Create the directory if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        filepath = os.path.join(output_folder, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Output successfully saved to: {filepath}")
    except OSError as e:
        logging.error(f"Failed to create directory or save file {filepath}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving output to {filepath}: {e}")

# --- LLM Interactions ---
def analyze_video(
    video_type: str, # "Early_take" or "Retrospective"
    set_name: str,
    transcript: str,
    llm: Gemini,
    prompt_template: RichPromptTemplate, # The specific template for this type
    rate_limiter: RateLimiter,
    output_folder: str
) -> str:
    """Analyzes a single video's transcript using the LLM and saves the output."""
    if not transcript or transcript.startswith("Error fetching transcript"):
        error_msg = transcript if transcript else "Error: Transcript unavailable."
        logging.warning(f"Skipping {video_type} analysis for '{set_name}' due to: {error_msg}")
        # Optionally save an error file
        # filename = generate_output_filename(set_name, f"{video_type}_Error")
        # save_output(output_folder, filename, error_msg)
        return error_msg

    logging.info(f"Analyzing {video_type} for '{set_name}'...")
    analysis_result = f"Error analyzing {video_type}: Unknown LLM error."
    try:
        # Format prompt using the chat template structure from utils
        # Pass necessary variables expected by the Jinja template
        messages = prompt_template.format_messages(
            transcript=transcript,
            set_name=set_name
            # Ensure system_prompt_template_str was correctly embedded when creating the template
        )

        with rate_limiter: # Apply rate limiting before the API call
            logging.info(f"Making LLM call for {video_type} analysis of '{set_name}'...")
            response = llm.chat(messages)
            logging.info(f"{video_type} analysis LLM call successful for '{set_name}'.")
        analysis_result = response.message.content if response.message else "Error: Empty response from LLM."

        # Save the successful result
        filename = generate_output_filename(set_name, video_type) # e.g., 20250410_MySet_Early_take.md
        save_output(output_folder, filename, analysis_result)

    except Exception as e:
        logging.error(f"Error during {video_type} analysis LLM call for '{set_name}': {e}", exc_info=True)
        analysis_result = f"Error analyzing {video_type}: {e}"
        # Optionally save an error file
        # filename = generate_output_filename(set_name, f"{video_type}_Error")
        # save_output(output_folder, filename, analysis_result)

    return analysis_result # Return the content (or error message)

def compare_analyses(
    set_name: str,
    takeaways_early: str,
    takeaways_retro: str,
    llm: Gemini,
    compare_prompt_template: RichPromptTemplate,
    rate_limiter: RateLimiter,
    output_folder: str
) -> str:
    """Compares two sets of takeaways using the LLM and saves the output."""
    if takeaways_early.startswith("Error:") or takeaways_retro.startswith("Error:"):
        error_msg = "Error: Cannot compare due to error in one or both preceding analyses."
        logging.warning(f"Skipping comparison for '{set_name}' due to previous errors.")
        # Optionally save an error file
        # filename = generate_output_filename(set_name, "Analysis_Error")
        # save_output(output_folder, filename, error_msg)
        return error_msg

    logging.info(f"Comparing analyses for '{set_name}'...")
    comparison_result = "Error comparing analyses: Unknown LLM error."
    try:
        # Format the comparison prompt
        messages = compare_prompt_template.format_messages(
            takeaways_a=takeaways_early,
            takeaways_b=takeaways_retro,
            set_name=set_name
             # Ensure system_prompt_template_str was correctly embedded
        )
        with rate_limiter: # Apply rate limiting
            logging.info(f"Making LLM call for comparison of '{set_name}'...")
            response = llm.chat(messages)
            logging.info(f"Comparison LLM call successful for '{set_name}'.")
        comparison_result = response.message.content if response.message else "Error: Empty response from LLM."

        # Save the successful comparison
        filename = generate_output_filename(set_name, "Analysis") # e.g., 20250410_MySet_Analysis.md
        save_output(output_folder, filename, comparison_result)

    except Exception as e:
        logging.error(f"Error during comparison LLM call for '{set_name}': {e}", exc_info=True)
        comparison_result = f"Error comparing analyses: {e}"
        # Optionally save an error file
        # filename = generate_output_filename(set_name, "Analysis_Error")
        # save_output(output_folder, filename, comparison_result)

    return comparison_result # Return the content (or error message)

# --- Set Processing Orchestration ---
def process_video_set(
    video_set: dict, # Contains set_name, early_take obj, retrospective obj
    reader: YoutubeTranscriptReader,
    llm: Gemini,
    prompt_templates: dict, # Dict containing 'early', 'retro', 'compare' RichPromptTemplate objects
    rate_limiter: RateLimiter,
    output_folder: str
) -> dict:
    """Processes a single set of early take and retrospective videos."""
    set_name = video_set['set_name']
    early_config = video_set['early_take']
    retro_config = video_set['retrospective']
    early_url = early_config['url']
    retro_url = retro_config['url']

    logging.info(f"Processing set: '{set_name}' (Early: {early_url} | Retro: {retro_url})")

    # Determine which prompts to use (potentially overridden in config)
    # For simplicity now, we assume global prompts are used. Add logic here if needed.
    early_prompt = prompt_templates['early']
    retro_prompt = prompt_templates['retro']
    compare_prompt = prompt_templates['compare']

    # 1. Fetch Transcripts
    transcript_early = get_transcript(early_url, reader)
    transcript_retro = get_transcript(retro_url, reader)

    # 2. Analyze Early Take Video (Rate limit inside analyze_video)
    early_analysis_result = analyze_video(
        video_type="Early_take",
        set_name=set_name,
        transcript=transcript_early,
        llm=llm,
        prompt_template=early_prompt,
        rate_limiter=rate_limiter,
        output_folder=output_folder
    )

    # 3. Analyze Retrospective Video (Rate limit inside analyze_video)
    retro_analysis_result = analyze_video(
        video_type="Retrospective",
        set_name=set_name,
        transcript=transcript_retro,
        llm=llm,
        prompt_template=retro_prompt,
        rate_limiter=rate_limiter,
        output_folder=output_folder
    )

    # 4. Compare Analyses (Rate limit inside compare_analyses)
    comparison_result = compare_analyses(
        set_name=set_name,
        takeaways_early=early_analysis_result,
        takeaways_retro=retro_analysis_result,
        llm=llm,
        compare_prompt_template=compare_prompt,
        rate_limiter=rate_limiter,
        output_folder=output_folder
    )

    logging.info(f"Finished processing set: '{set_name}'")
    # Return a summary dictionary (detailed results are saved to files)
    return {
        "set_name": set_name,
        "early_take_url": early_url,
        "retrospective_url": retro_url,
        "early_take_status": "OK" if not early_analysis_result.startswith("Error:") else early_analysis_result,
        "retrospective_status": "OK" if not retro_analysis_result.startswith("Error:") else retro_analysis_result,
        "comparison_status": "OK" if not comparison_result.startswith("Error:") else comparison_result,
    }
