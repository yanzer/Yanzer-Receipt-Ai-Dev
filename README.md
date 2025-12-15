# 🧾 ReceiptGuard AI

**ReceiptGuard AI** is a privacy-first, offline application that uses powerful local Large Language Models (LLMs) to analyze receipts. It runs entirely on your Mac, ensuring no financial data ever leaves your computer.

## ✨ Features
*   **📄 Intelligent OCR:** Extracts merchant, date, items, prices, and totals from images.
*   **🕵️‍♀️ Fraud Detection:** AI analyzes receipts for visual tampering, mathematical inconsistencies, and anomalies.
*   **🎁 Loyalty Calculation:** Automatically calculates points based on customizable rules (Default: 1 point per RM1).
*   **💬 Chat with Receipts:** Ask context-aware questions about your purchase history (e.g., "Did I buy milk?").
*   **💾 Local History:** Auto-saves all analyses and chat sessions to your local drive.

---

## 🛠️ Prerequisites

*   **Computer:** Mac (Apple Silicon preferred, but works on Intel Macs with 8GB+ RAM).
*   **Software:**
    *   [Ollama](https://ollama.com/) (for running AI models locally).
    *   [Python 3.9+](https://www.python.org/downloads/).

---

## 🚀 Installation Guide

### 1. Install Ollama
Ollama is the engine that runs the AI models.

*   **Newer Macs (macOS 14+):** Download directly from [ollama.com](https://ollama.com/download).
*   **Older Macs (macOS 12/13):** automatic updates might fail. You may need a specific version (e.g., v0.1.32) from the [Ollama GitHub Releases](https://github.com/ollama/ollama/releases).

### 2. Pull the AI Vision Model
Open your terminal and run the following command to download the "brain" of the application.

*   **Recommended (Fast & Smart):**
    ```bash
    ollama pull qwen2.5-vl:3b
    ```
    *This model (~2GB) is optimized for vision and fits easily in 8GB RAM.*

*   **Alternative (Legacy):**
    ```bash
    ollama pull llava-phi3
    ```

### 3. Clone/Setup Project
Create a folder for your project and add the following files:

*   `app.py` (The main Web Interface)
*   `requirements.txt` (Dependencies)

### 4. Install Dependencies
Open your terminal in the project folder and run:

```bash
pip3 install streamlit requests pillow
```

*(Note: Depending on your system, you might need to use `pip` instead of `pip3`).*

---

## 🏃‍♂️ How to Run

1.  **Start Ollama Server:**
    Ensure Ollama is running in the background. You should see the llama icon in your menu bar, or run `ollama serve` in a separate terminal.

2.  **Launch the App:**
    Run the following command in your project terminal:

    ```bash
    streamlit run app.py
    ```

3.  **Use the App:**
    *   A new browser tab will open automatically (usually at `http://localhost:8501`).
    *   **Upload** a receipt image.
    *   Click **"🔍 Analyze with AI"**.
    *   Chat with the result or view saved history in the sidebar.

---

## 📂 Project Structure

*   `app.py`: The main application code (UI, Logic, API calls).
*   `receipt_history/`: Folder where JSON records of all analyses are auto-saved.
*   `receipt_guard.py`: (Optional) A command-line version of the tool.

---

## ⚠️ Troubleshooting

*   **"Ollama connection failed":** Make sure the Ollama app is actually running. Try running `ollama list` in the terminal to verify.
*   **Analysis is slow:** On older Intel Macs, analysis can take 60-90 seconds per image. This is normal for local AI on older hardware.
*   **Model not found:** Check the "Settings" sidebar in the app and make sure the selected model matches exactly what you pulled (e.g., `qwen2.5-vl:3b`).
