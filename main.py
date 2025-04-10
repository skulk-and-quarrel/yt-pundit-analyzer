import logging
import concurrent.futures
import time
import argparse
import os
import sys

# Ensure the package directory is in the Python path
PACKAGE_PARENT = '.'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

try:
    from yt_pundit_analyzer.utils import (
        load_config,
        get_api_key,
        load_prompt,
        create_chat_prompt_template,
        setup_rate_limiter
    )
    from yt_pundit_analyzer.core import process_video_set
    from llama_index.readers.youtube_transcript import YoutubeTranscriptReader
    from llama_index.llms.gemini import Gemini
except ImportError as e:
    print(f"Error importing modules. Ensure main.py is in the correct directory and required packages are installed: {e}")
    sys.exit(1)


# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Main Execution ---
def run_pundit_analyzer(config_path="config.yaml", cli_output_folder=None):
    """Main function to run the YouTube video comparison."""
    start_time = time.time()
    logging.info("--- Starting YouTube Pundit Analyzer ---")
    config = None # Initialize config
    try:
        # 1. Load Configuration
        config = load_config(config_path)
        api_key = get_api_key(config) # Prioritizes .env

        # Determine output folder (CLI override takes precedence)
        output_folder = cli_output_folder if cli_output_folder else config.get('output_folder', 'analysis_results')
        os.makedirs(output_folder, exist_ok=True) # Ensure it exists
        logging.info(f"Output will be saved to: {os.path.abspath(output_folder)}")

        # Load and prepare all necessary prompt templates
        try:
            prompt_templates = {
                'early': create_chat_prompt_template(load_prompt(config['early_take_prompt_file'])),
                'retro': create_chat_prompt_template(load_prompt(config['retrospective_prompt_file'])),
                'compare': create_chat_prompt_template(load_prompt(config['compare_prompt_file']))
            }
        except KeyError as e:
             logging.error(f"Missing prompt file path key in config.yaml: {e}. Please ensure 'early_take_prompt_file', 'retrospective_prompt_file', and 'compare_prompt_file' are defined.")
             return # Exit if prompts can't be loaded
        except FileNotFoundError:
             logging.error(f"One or more prompt files specified in config.yaml were not found. Please check paths.")
             return # Exit if prompts can't be loaded


        video_sets = config.get('video_sets', []) # Get the list of sets
        if not video_sets or not isinstance(video_sets, list):
            logging.warning("No valid 'video_sets' list found in configuration. Ensure it's defined correctly in config.yaml. Exiting.")
            return

        # 2. Setup LlamaIndex Components & Rate Limiter
        reader = YoutubeTranscriptReader()
        llm = Gemini(api_key=api_key, model_name=config.get('llm_model_name', 'models/gemini-1.5-flash'))
        rate_limiter = setup_rate_limiter(
            config.get('rate_limit_calls', 5), # Use .get for safety
            config.get('rate_limit_period', 60)
        )

        # 3. Parallel Processing
        # Use max_workers from config, default to 4
        max_workers = config.get('max_workers', 4)
        # Ensure at least 1 worker, and not more than number of sets (no benefit)
        num_sets = len(video_sets)
        actual_workers = max(1, min(num_sets, max_workers))

        logging.info(f"Processing {num_sets} sets using up to {actual_workers} worker threads.")
        results_summary = []
        futures_map = {} # Dictionary to map futures back to set names

        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers, thread_name_prefix='Worker') as executor:
            # Submit tasks
            for video_set in video_sets:
                # Basic validation of the set structure
                set_name = video_set.get('set_name')
                if not set_name or \
                   not isinstance(video_set.get('early_take'), dict) or \
                   not isinstance(video_set.get('retrospective'), dict) or \
                   not video_set['early_take'].get('url') or \
                   not video_set['retrospective'].get('url'):
                    logging.warning(f"Skipping invalid video set structure in config: Set name '{set_name or 'MISSING'}'. Check URLs and structure.")
                    continue

                future = executor.submit(
                    process_video_set, # Target function in core.py
                    video_set,         # The dictionary for the current set
                    reader,            # Shared reader instance
                    llm,               # Shared LLM instance
                    prompt_templates,  # Dict with prepared prompt templates
                    rate_limiter,      # Shared rate limiter instance
                    output_folder      # Output folder path
                )
                futures_map[future] = set_name # Map future to set name for context

            if not futures_map:
                logging.warning("No valid video sets were submitted for processing.")
                return

            # Process completed tasks as they finish
            processed_count = 0
            total_tasks = len(futures_map)
            for future in concurrent.futures.as_completed(futures_map):
                set_name_completed = futures_map[future]
                processed_count += 1
                logging.info(f"Processing complete for set {processed_count}/{total_tasks}: '{set_name_completed}'")
                try:
                    result_data = future.result() # Get summary dict from process_video_set
                    results_summary.append(result_data)
                    # Print summary status (details are in files)
                    print("\n" + "="*50)
                    print(f"Summary for Set: '{result_data.get('set_name', 'N/A')}'")
                    print("-"*50)
                    print(f"Early Take URL:      {result_data.get('early_take_url', 'N/A')}")
                    print(f"Early Take Status:   {result_data.get('early_take_status', 'N/A')}")
                    print(f"Retrospective URL:   {result_data.get('retrospective_url', 'N/A')}")
                    print(f"Retrospective Status:{result_data.get('retrospective_status', 'N/A')}")
                    print(f"Comparison Status:   {result_data.get('comparison_status', 'N/A')}")
                    print(f"(Detailed results saved in folder: '{output_folder}')")
                    print("="*50 + "\n")
                except Exception as exc:
                    logging.error(f"Set '{set_name_completed}' generated an exception during processing: {exc}", exc_info=True)
                    # Store error information in the summary
                    results_summary.append({
                        "set_name": set_name_completed,
                        "error": f"Processing failed: {exc}"
                    })

        # 4. Final Summary
        logging.info(f"--- Finished processing all submitted sets ({processed_count}/{total_tasks}) ---")


    except FileNotFoundError:
        # Already logged in load_config, but good to catch here too
        logging.error(f"Configuration file '{config_path}' not found. Exiting.")
    except ValueError as e:
        # Catch specific errors like missing API key
        logging.error(f"Configuration or setup error: {e}")
    except Exception as e:
        # Catch any other unexpected errors during setup or execution
        logging.critical(f"A critical error occurred in the main execution: {e}", exc_info=True)
        if config: # Log config if loaded
             logging.info(f"Configuration used: {config}")

    finally:
        end_time = time.time()
        logging.info(f"Total execution time: {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Early vs. Retrospective YouTube videos using Gemini.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to the configuration YAML file (default: config.yaml)"
    )
    parser.add_argument(
        "--output-folder",
        default=None, # Default is None, indicating use value from config file
        help="Path to the folder where analysis results (.md files) will be saved. Overrides 'output_folder' in the config file if provided."
    )
    args = parser.parse_args()

    # Check if config file exists before proceeding
    if not os.path.exists(args.config):
         print(f"Error: Configuration file not found at '{args.config}'")
         sys.exit(1)

    run_pundit_analyzer(config_path=args.config, cli_output_folder=args.output_folder)
