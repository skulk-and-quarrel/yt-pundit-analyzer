# YT-PUNDIT-ANALYZER

> YouTube Video Comparison Tool for Analyzing Pundit Predictions

## 🔍 What is this?

`yt-pundit-analyzer` helps you evaluate how accurate pundits, commentators, or experts were in their predictions. It compares:

1. A video containing predictions/opinions about future events
2. A later video showing what actually happened

Using AI, it extracts key points from both videos and generates an objective comparison of the prediction accuracy.

*Example use case: I recently used this tool to analyze Lords of Limited podcast episodes about Magic: The Gathering, comparing their early format predictions with their later assessments. See the blogpost here: https://llemre.com/lol-early-take/*

## ⚡ Quick Start

```bash
# Install
git clone https://github.com/skulk-and-quarrel/yt-pundit-analyzer
cd yt-pundit-analyzer
pip install -r requirements.txt

# Set your Google API key (see Configuration section)
cp .env.example .env
# Edit .env with your API key

# Run with default config
python main.py
```

## 🛠️ Main Function

The package performs three primary tasks:

1. **Fetch transcripts** from YouTube videos using `llama-index-readers-youtube-transcript`
2. **Extract key takeaways** from each video (with timestamps and quotes)
3. **Generate a comparison** between the paired videos

This entire process is:
- Parallelized for efficiency
- Rate-limited to respect API quotas
- Powered by Google's Gemini 2.5 Pro LLM

## ⚙️ Configuration

The only required configuration is your **Google API key**. 

Edit the `config.yaml` file to customize your analysis:

```yaml
# Prompts to use
early_take_prompt_file: "prompts/lol_early_take_prompt.txt"
retrospective_prompt_file: "prompts/lol_retrospective_prompt.txt"
compare_prompt_file: "prompts/lol_compare_takeaways_prompt.txt"

# Video sets to analyze
video_sets:
  - subject: "Example Set"
    early_take:
      url: "https://www.youtube.com/watch?v=early_prediction_video"
    retrospective:
      url: "https://www.youtube.com/watch?v=actual_outcome_video"
  
  - subject: "Another Example"
    early_take:
      url: "https://www.youtube.com/watch?v=another_prediction"
    retrospective:
      url: "https://www.youtube.com/watch?v=another_outcome"

# Optional settings (defaults work well)
output_folder: "analysis_results"  # Where results are saved
max_workers: 4                     # Parallel processing threads
llm_model_name: "models/gemini-2.5-pro-exp-03-25"
```

For detailed setup instructions, see the **Complete Setup Guide** below.

## 📋 Complete Setup Guide

<details>
<summary>Click to expand detailed setup instructions</summary>

### Prerequisites

- Python 3.8 or higher
- A Google API key with access to Gemini models

### Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/skulk-and-quarrel/yt-pundit-analyzer
cd yt-pundit-analyzer

# Set up a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: API Key Configuration

**Option 1: Environment Variables (Recommended)**
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit the `.env` file and replace `"YOUR_GOOGLE_API_KEY_HERE"` with your actual key
3. Add `.env` to your `.gitignore` to prevent accidentally sharing your key

**Option 2: Config File (Less Secure)**
1. Open `config.yaml`
2. Uncomment the `google_api_key` line
3. Add your API key directly in the file

### Step 3: Configure Video Sets

Edit the `config.yaml` file to specify which videos to compare:

```yaml
video_sets:
  - subject: "Set Name"  # A descriptive name for this comparison set
    early_take:
      url: "https://www.youtube.com/watch?v=prediction_video"
    retrospective:
      url: "https://www.youtube.com/watch?v=outcome_video"
```

Each set needs:
1. A descriptive `subject` (e.g., "Magic Set Analysis")
2. An `early_take` URL (the prediction/speculation video)
3. A `retrospective` URL (the actual outcome video)

### Step 4: Advanced Configuration (Optional)

In `config.yaml`, you can also adjust:

- **Output Settings**:
  ```yaml
  output_folder: "analysis_results"  # Where results are saved
  max_workers: 4                     # Parallel processing threads
  ```

- **API Rate Limiting**:
  ```yaml
  rate_limit_calls: 5    # Number of API calls
  rate_limit_period: 60  # Time period in seconds
  ```

- **LLM Model**:
  ```yaml
  llm_model_name: "gemini-2.5-pro-exp-03-25"  # Specify Gemini model version
  ```

- **Custom Prompts**: Configure paths to your prompt files:
  ```yaml
  early_take_prompt_file: "prompts/lol_early_take_prompt.txt"
  retrospective_prompt_file: "prompts/lol_retrospective_prompt.txt"
  compare_prompt_file: "prompts/lol_compare_takeaways_prompt.txt"
  ```

### Step 5: Run the Analysis

```bash
python main.py
```

Or specify a custom config location:

```bash
python main.py --config path/to/your_config.yaml
```

### Output

Results will be saved in the `output_folder` directory, with one file per video pair.

</details>

## 💻✨🎶 Acknowledgements

This package has been vibe-coded from scratch.
- Code: gemini-2.5-pro
- Prompts for API calls: claude-3.7-sonnet

[🔝 Back to top](#yt-pundit-analyzer)
