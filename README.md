# 🧾 ReceiptGuard AI

An AI-powered receipt analysis and fraud detection system using vision language models.

## Features

- 📸 Upload and analyze receipt images
- 🔍 Automatic fraud detection using Malaysian financial rules
- 💬 Interactive chat to ask questions about receipts
- 📊 Token usage tracking and performance metrics
- 📜 Historical analysis logs
- 🤖 Support for multiple AI models (Ollama local models + Together.AI cloud models)

## Deployment on Streamlit Cloud

### Step 1: Push to GitHub
This repository is already configured for Streamlit Cloud deployment.

### Step 2: Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Select:
   - **Repository**: `yanzer/Yanzer-Receipt-Ai-Dev`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click "Deploy"

### Step 3: Configure Secrets
After deployment, add your API key:
1. In Streamlit Cloud dashboard, click on your app
2. Go to "Settings" → "Secrets"
3. Add the following:

```toml
[together_ai]
api_key = "your-together-ai-api-key-here"
```

## Local Development

### Prerequisites
- Python 3.8+
- Ollama (optional, for local models)

### Installation

```bash
# Clone the repository
git clone https://github.com/yanzer/Yanzer-Receipt-Ai-Dev.git
cd Yanzer-Receipt-Ai-Dev

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Local Configuration
Create `.streamlit/secrets.toml` (copy from template):
```bash
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml` with your API keys.

## Usage

1. **Upload Receipt**: Click "Choose an image..." to upload a receipt
2. **Analyze**: Click "🔍 Analyze with AI" to process the receipt
3. **Review Results**: View extracted data, fraud detection results, and reasoning
4. **Chat**: Ask questions about the receipt in the chat interface
5. **History**: Access previous analyses from the sidebar

## Models Supported

### Local Models (via Ollama)
- `qwen2.5-vl:3b`
- `llava-phi3`
- Any other Ollama vision model

### Cloud Models (via Together.AI)
- `google/gemma-3n-E4B-it`

## Technology Stack

- **Frontend**: Streamlit
- **AI Models**: Ollama (local) + Together.AI (cloud)
- **Image Processing**: Pillow
- **Data Management**: Pandas

## Project Structure

```
.
├── app.py                          # Main Streamlit application
├── receipt_guard.py                # Core receipt analysis logic
├── demo_ollama.py                  # Ollama integration demo
├── requirements.txt                # Python dependencies
├── .streamlit/
│   ├── config.toml                # Streamlit configuration
│   └── secrets.toml.template      # Secrets template
├── receipt_history/               # Stored analysis results
└── README.md                      # This file
```

## Features in Detail

### Fraud Detection
The system uses 11 Malaysian receipt validation rules:
1. Subtotal calculation verification
2. Service charge (10%) validation
3. SST (6% or 8%) calculation check
4. Tax exemption handling
5. Rounding adjustment (±RM 0.04)
6. Set meal pricing validation
7. Void item handling
8. Discount verification
9. Deposit vs. balance tracking
10. Unit price × quantity validation
11. Footer noise filtering

### Analysis Output
- Merchant name
- Receipt number
- Total amount
- Date
- Location
- Fraud verdict with detailed reasoning
- Token usage statistics
- Processing time metrics

## License

MIT License

## Author

Yanzer - [GitHub](https://github.com/yanzer)
