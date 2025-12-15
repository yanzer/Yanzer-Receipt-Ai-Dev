# ☁️ ReceiptGuard AI: Cloud Migration Guide (GCP + PHP + Qwen 72B)

This guide details how to recreate the **ReceiptGuard AI** system as a production-grade, hosted solution on **Google Cloud Platform (GCP)** using **PHP** and the powerful **Qwen2.5-VL-72B-Instruct** model.

---

## 🏗️ Architecture Overview

The system consists of two distinct parts hosted on GCP:

1.  **The Brain (Model Server):** A high-performance GPU Virtual Machine (VM) running the 72B model.
    *   *Software:* vLLM or Ollama (Linux).
    *   *Hardware:* **NVIDIA A100 (80GB)** or **2x NVIDIA A100 (40GB)** or **4x NVIDIA L4**.
    *   *Why?* The 72B model requires massive Video RAM (VRAM). It **cannot** run on standard CPUs.

2.  **The Application (PHP Web Server):** A lightweight web server hosting the PHP frontend and database.
    *   *Software:* Apache/Nginx + PHP 8.2 + MySQL.
    *   *Function:* Handles file uploads, saves history, chat logic, and communicates with the "Brain" via API.

---

## 🛠️ Part 1: GCP Infrastructure Setup

### 1. Create a GPU Instance (The Brain)
1.  Go to **GCP Console** > **Compute Engine** > **VM Instances**.
2.  Click **Create Instance**.
3.  **Machine Configuration:**
    *   **Series:** Accelerator Optimized (A2 or G2).
    *   **GPU:** Select **1x NVIDIA A100 (80GB)**. *(Note: You must request a Quota Increase for A100 GPUs in your region first).*
4.  **Boot Disk:**
    *   **OS:** Ubuntu 22.04 LTS (Deep Learning Image recommended).
    *   **Size:** 200GB SSD.
5.  **Firewall:** Allow HTTP/HTTPS.
6.  *Important:* Assign a **Static External IP** to this instance so your PHP app can always find it.

### 2. Install Model Server (On GPU Instance)
SSH into your new GPU instance and install the inference engine (vLLM is recommended for production 72B models).

```bash
# 1. Install Docker & Nvidia Toolkit (if using standard Ubuntu)
sudo apt update && sudo apt install -y docker.io nvidia-container-toolkit

# 2. Run Qwen2.5-VL-72B using vLLM
# This exposes an OpenAI-compatible API on port 8000
sudo docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen2.5-VL-72B-Instruct \
    --trust-remote-code \
    --max-model-len 8192
```

---

## 💻 Part 2: PHP Application Development

You can host this on a standard cheap VM (e2-micro) or Google Cloud Run.

### 1. Database Schema (MySQL)
Create a database `receipt_guard` and a table for history.

```sql
CREATE TABLE analyses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    merchant_name VARCHAR(255),
    image_path VARCHAR(255),
    grand_total DECIMAL(10,2),
    loyalty_points INT,
    input_tokens INT,
    output_tokens INT,
    process_time_seconds FLOAT,
    full_json_result JSON,
    chat_history JSON
);
```

### 2. The Assistant Prompt (System Prompt)
Use this strict prompt in your PHP code to ensure consistent JSON output with deep logic checks.

```text
You are ReceiptGuard AI, a professional document analysis engine.
Your goal is to extract structured data from the receipt image and perform logical validation.

RULES:
1. OUTPUT MUST BE STRICT VALID JSON. No markdown, no conversational text.
2. EXTRACT: "merchant", "date", "currency", "grand_total", "line_items".
3. ANALYZE FRAUD: Look for differing fonts, alignment issues, or pixelated areas (tampering).
4. LOGIC CHECK (CRITICAL): Evaluate if prices make sense. 
   - Example: A single cup of coffee shouldn't cost 100.00. 
   - If an item price is unrealistic, flag it in "caution_notes" and lower confidence.
5. REASONING: Provide a "validation_reasoning" paragraph explaining why this receipt is valid or suspicious.

JSON SCHEMA:
{
  "merchant": "string",
  "date": "string",
  "grand_total": "number",
  "currency": "string",
  "loyalty_points": "integer",
  "fraud_analysis": {
    "is_tampered": boolean,
    "issues_found": ["string"]
  },
  "caution_notes": ["string"],          // e.g. "Price of Coffee (100.00) seems unrealistic"
  "validation_reasoning": "string",     // e.g. "Receipt looks authentic but Item #2 price is suspicious."
  "line_items": [
    {"name": "string", "qty": "number", "price": "number"}
  ]
}
```

### 3. PHP Code Structure

#### `analyze.php` (Core Logic)
```php
<?php
include 'config.php';

function analyzeReceipt($imagePath) {
    $startTime = microtime(true);
    
    // 1. Encode Image
    $base64Image = base64_encode(file_get_contents($imagePath));
    
    // 2. Prepare Payload
    $modelName = "Qwen/Qwen2.5-VL-72B-Instruct";
    $data = [
        "model" => $modelName,
        "messages" => [
            ["role" => "system", "content" => "You are ReceiptGuard AI. Return ONLY JSON... (Insert Full Prompt)"],
            [
                "role" => "user", 
                "content" => [
                    ["type" => "text", "text" => "Analyze this receipt."],
                    ["type" => "image_url", "image_url" => ["url" => "data:image/jpeg;base64," . $base64Image]]
                ]
            ]
        ],
        "temperature" => 0.1,
        "max_tokens" => 2048
    ];

    // 3. Call API (cURL)
    $ch = curl_init(MODEL_API_URL);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $response = curl_exec($ch);
    curl_close($ch);
    
    $endTime = microtime(true);
    $processTime = round($endTime - $startTime, 2);
    
    // 4. Parse Result & Merge Metadata
    $apiResult = json_decode($response, true);
    $modelContent = json_decode($apiResult['choices'][0]['message']['content'], true);
    $usage = $apiResult['usage']; 

    // Final Enhanced JSON Structure
    $finalOutput = [
        "data" => $modelContent,  // The extracted receipt data
        "metadata" => [
            "model_used" => $modelName,
            "process_time_seconds" => $processTime,
            "token_usage" => [
                "input_total" => $usage['prompt_tokens'],
                "output_total" => $usage['completion_tokens'],
                "total" => $usage['total_tokens']
            ]
        ]
    ];
    
    // 5. Save and Return
    // saveToDatabase($finalOutput);
    return json_encode($finalOutput, JSON_PRETTY_PRINT);
}
?>
```

### 4. Interactive Chat Feature
To enable "Chat with Receipt", you must store the `chat_history` in your PHP session or database.

When the user asks a follow-up question:
1.  Retrieve the original parsed JSON text or the image.
2.  Send a new request to the API with the **entire conversation history** attached in the `messages` array.
3.  The 72B model will maintain context.

---

## 💰 Cost Estimation (Warning)

Hosting the **72B model** is significantly more expensive than the 3B model.
*   **A100 GPU Instance:** Approx. **$3.67 per hour** (~$2,600/month if left running 24/7).
*   **Cost Saving Tip:** Configure the instance to **Shut Down** automatically when not in use (Spot instances or Cloud Functions trigger), or downgrade to a smaller quantized model if 72B is too expensive.
