# YT-PUNDIT-ANALYZER: YouTube Video Comparison Tool for Analyzing Pundits

> Vibe-coded 💻✨🎶 (Code: gemini-pro-2.5, Prompts: claude-sonnet-3.7)

`yt-pundit-analyzer` is a Python package that compares pair(s) of YouTube videos: a video with speculations/takes about the future, and an another video with the actual outcomes. Its purpose is to judge and evaluate the accuracy of pundit commentary. 

It leverages LlamaIndex and Google's Gemini LLM (since Gemini Pro 2.5 is just fantastic).

Workflow:
- Fetch transcripts from the pair of videos,
- Extract key takeaways (with timestamps and quotes),
- Generate a comparison between pairs of videos. 

_The process is parallelized for efficiency and includes rate limiting to respect API usage quotas._

[TODO: Update this to make it more user friendly (put the setup/configuration in a separate file for easy readability), and give more of the context]

## Features

- Fetches transcripts for specified YouTube videos using `llama-index-readers-youtube-transcript`.
- Uses Google's Gemini LLM via `llama-index-llms-gemini` for:
    - Extracting key takeaways from each video's transcript.
    - Comparing the takeaways of paired videos.
- Processes multiple video pairs in parallel using `concurrent.futures.ThreadPoolExecutor`.
- Implements robust API rate limiting using the `ratelimiter` library to avoid exceeding quotas (e.g., Google API limits).
- Configurable via a `config.yaml` file for API keys (environment variables recommended), rate limits, LLM model, and video pairs.
- Customizable LLM prompts stored in external `.txt` files.

## Setup

1. **Prerequisites:** Python 3.8+ recommended.
2. **Clone Repository:**bash git clone https://github.com/skulk-and-quarrel/yt-pundit-analyzer
3. **Create Virtual Environment (Recommended):**
    
    ```bash
    python -m venv venv
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows:
    .\venv\Scripts\activate
    ```

4. **Install Dependencies:**

```bash
pip install -r requirements.txt
```

## Configuration

1. **API Key (Required):**
    - **Recommended Method (Environment Variable):**
        - Copy the `.env.example` file to `.env`: `cp.env.example.env` (or `copy.env.example.env` on Windows).
        - Edit the `.env` file and replace `"YOUR_GOOGLE_API_KEY_HERE"` with your actual Google API key obtained from Google AI Studio or Google Cloud Console.
        - **Important:** Add `.env` to your `.gitignore` file to prevent accidentally committing your key.
    - **Alternative (Less Secure - Config File):** If you cannot use environment variables, you can uncomment the `google_api_key` line in `config.yaml` and paste your key there. This is **not recommended** for security reasons.
2. **`config.yaml`:**
    - Open `config.yaml` in a text editor.
    - **`rate_limit_calls` / `rate_limit_period`:** Adjust the API rate limit (e.g., 5 calls per 60 seconds). Check your Google API quota for appropriate values.
    - **`llm_model_name`:** Change the Gemini model if desired (e.g., `"models/gemini-pro"`).
    - **`video_pairs`:** This is the crucial part. Edit the list to include the pairs of YouTube video URLs you want to compare. Each item in the list should be another list containing exactly two valid YouTube video URLs. Add or remove pairs as needed.
3. **Prompts (Optional):**
    - To customize the instructions given to the AI, edit the text files located in the `prompts/` directory:
        - `early_take_prompt.txt` and `retrospective_prompt.txt`: Controls how takeaways are extracted.
        - `compare_takeaways_prompt.txt`: Controls how the comparison is performed.

## Running the Script

Once configured, run the main script from the project's root directory:


```bash
python main.py
```

If you placed your configuration file elsewhere, you can specify its path:

```bash
python main.py --config path/to/your_config.yaml
```

## Output

The script will process each pair of videos defined in `config.yaml`. They will be stored under the directory "output_folder".