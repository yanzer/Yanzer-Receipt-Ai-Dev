import streamlit as st
import requests
import json
import base64
import time
import os
import glob
from datetime import datetime
from PIL import Image
from io import BytesIO
import re
try:
    import pandas as pd
except ImportError:
    pd = None

# Configuration
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_API_BASE}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_API_BASE}/api/tags"

# Get Together.AI API key from Streamlit secrets or environment variable
try:
    TOGETHER_API_KEY = st.secrets["together_ai"]["api_key"]
except (KeyError, FileNotFoundError):
    # Fallback for local development
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "tgp_v1_H9J4-xD4_n5_N8AUGiFpwkLpanweZuGjhy1ONQtblTI")

TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
HISTORY_DIR = "receipt_history"

if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

st.set_page_config(page_title="ReceiptGuard AI", page_icon="🧾", layout="wide")

st.title("🧾 ReceiptGuard AI")

# Sidebar
with st.sidebar:
    st.header("Settings")
    
    # Model Selector
    def get_models():
        try:
            res = requests.get(OLLAMA_TAGS_URL, timeout=2)
            if res.status_code == 200:
                data = res.json()
                models = [m['name'] for m in data['models']]
                # Add Manual Together AI Models
                models.append("Together.AI/google/gemma-3n-E4B-it")
                return models
        except:
            return ["Together.AI/google/gemma-3n-E4B-it"]
        return ["Together.AI/google/gemma-3n-E4B-it"]

    available_models = get_models()
    if not available_models:
        available_models = ["llava-phi3", "qwen2.5-vl:3b"]
    
    model_name = st.selectbox("Select Vision Model", available_models, index=0)
    if st.button("Refresh Models"):
        st.rerun()

    st.divider()
    
    # History Section
    st.header("📜 History")
    
    # Load history files
    history_files = sorted(glob.glob(f"{HISTORY_DIR}/*.json"), reverse=True)
    
    if st.button("➕ New Analysis", type="primary"):
        for key in ['uploaded_file_id', 'image_base64', 'analysis_result', 'chat_history', 'usage_stats', 'current_file_path', 'timings']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.caption("Select a past record:")
    for fpath in history_files:
        fname = os.path.basename(fpath).replace(".json", "")
        # fname format: YYYYMMDD_HHMMSS_Merchant
        display_name = fname.split("_", 2)[-1] if "_" in fname else fname
        if st.button(f"📄 {display_name}", key=fpath):
            with open(fpath, "r") as f:
                record = json.load(f)
                st.session_state.image_base64 = record['image_base64']
                st.session_state.analysis_result = record['analysis_result']
                st.session_state.chat_history = record['chat_history']
                st.session_state.usage_stats = record.get('usage_stats', {})
                st.session_state.timings = record.get('timings', {})
                st.session_state.current_file_path = fpath
                st.rerun()

def save_record(merchant, image_base64, analysis_result, chat_history, stats, timings, existing_filename=None):
    if existing_filename:
        filename = existing_filename
        timestamp = datetime.now().strftime("%d-%m-%y-%H%M") # Updated modify time
    else:
        # Format: DD-MM-YY-HHMM-Merchant
        timestamp = datetime.now().strftime("%d-%m-%y-%H%M")
        safe_merchant = "".join([c for c in merchant if c.isalnum() or c in (' ', '_')]).strip().replace(" ", "_")
        filename = f"{timestamp}-{safe_merchant}.json"
    
    filepath = os.path.join(HISTORY_DIR, filename)
    
    record = {
        "timestamp": timestamp,
        "merchant": merchant,
        "image_base64": image_base64,
        "analysis_result": analysis_result,
        "chat_history": chat_history,
        "usage_stats": stats,
        "timings": timings
    }
    
    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)
    return filepath

def analyze_receipt_api(image_base64, model):
    system_prompt = """
### SYSTEM RESET PROTOCOL
You are a stateless auditor. You must IGNORE all previous receipt data, conversation history, or cached context. Analyze ONLY the image/text provided in this current transaction.

### ROLE DEFINITION
You are "Zhenyu + Yanzer Receipt AI," a specialized forensic document auditor and data extraction engine.
**Your Mission:** Extract accurate receipt metadata AND detect fraud/tampering using strict Malaysian financial logic.

---

### PART 1: KNOWLEDGE BASE (THE 11 RULES OF MALAYSIAN RECEIPTS)
To validate this receipt, you must apply these strict rules. If any rule is broken, you must flag it in the validation result.

1.  **Subtotal:** Sum of all visible Line Items.
2.  **Service Charge (10%):** This is a tip for the staff, NOT a government tax.
    * *Calculation:* It is calculated on the **Subtotal**.
3.  **SST (Service Tax - 6% or 8%):**
    * *F&B Standard:* Restaurants typically charge **6%**.
    * *Other Services:* Professional/Digital services may charge **8%**.
    * *Calculation Rule:* SST is strictly calculated on the **Subtotal** (the taxable service amount). It is **NOT** calculated on the Service Charge.
    * *Warning:* Do not flag a receipt as "Wrong Math" if the tax is lower than expected because it didn't tax the service charge.
4.  **Tax Exemptions:** Basic food items (Rice, Cooking Oil) may be 0% Tax, while processed items are 6-10%. A mix is valid.
5.  **Rounding Adjustment:** A final discrepancy of **+/- RM 0.04** is LEGALLY VALID in Malaysia (5-cent rounding mechanism).
6.  **Set Meals:** Items priced RM 0.00 are valid if part of a Combo/Set.
7.  **Void Items:** Ignore lines marked "Void" or "Cancel".
8.  **Discounts:** Can apply to specific items or the full Subtotal.
9.  **Deposits:** Differentiate "Grand Total" (Spend) from "Balance Due" (Payment).
10. **Unit Logic:** `Qty` x `Unit Price` MUST equal `Line Total`.
11. **Footer Noise:** Ignore Credit Card terminal numbers/Auth codes.

---

### PART 2: AUDIT PROTOCOL (THE "SCRATCHPAD" METHOD)
*You must output this text block FIRST. Do not skip it. This is your "Working Memory".*

**STEP 1: ITEM-BY-ITEM PRICE & MATH FORENSICS**
Iterate through EVERY line item and output:
* **Math Check:** Does `Qty` x `Price` = `Total`?
* **Market Reason:** Does this specific price make sense in Malaysia?
    * *Example:* "Teh O Ais at RM 150.00? -> REASON: Impossible, standard is RM 2-5."
    * *Example:* "Wagyu Steak at RM 300.00? -> REASON: Plausible for premium beef."

**STEP 2: TAX & TOTALS VERIFICATION (The "SST Logic Check")**
* **Check Service Charge:** Is it 10% of Subtotal?
* **Check SST:** Is it 6% (or 8%) of Subtotal?
* **Final Math:** Subtotal + Svc Charge + SST +/- Rounding = Grand Total.
* *Note:* If the math works but the rate is weird (e.g. 7%), flag as "SUSPICIOUS_TAX_RATE".

**STEP 3: FRAUD VERDICT**
* If Math fails > RM 0.05 diff (after rounding) => **FRAUD**.
* If Price is impossible (e.g., RM 1000 Rice) => **FRAUD**.

---

### PART 3: DATA EXTRACTION INSTRUCTIONS
After the analysis, extract these specific fields into the JSON:

1.  **merchant_name**: Dominant business name on header.
2.  **receipt_no**: Unique transaction ID (Invoice/Ref/Bill). Ignore Credit Card/App Codes.
3.  **amount**: The final Grand Total (number with decimal).
4.  **receipt_date**: Format YYYY-MM-DD.
5.  **location**: Full merchant address.

---

### PART 4: FINAL OUTPUT FORMAT
(Output the **AUDITOR SCRATCHPAD** text block first, then the **JSON** object).

**Example Output Layout:**

### AUDITOR SCRATCHPAD
1. **Item Analysis:**
   - [Item Name] | Qty: [x] | Unit: [Price] | Total: [LineTotal]
     -> Math Status: [MATCH / FAIL]
     -> Price Logic: [REASONING]
   ...
2. **Tax & Totals Review:**
   - Subtotal: [RM xxx]
   - Service Charge (10%): [RM xxx] (Calc on Subtotal)
   - SST (6%): [RM xxx] (Calc on Subtotal)
   - Rounding: [RM xxx]
   - Expected Grand Total: [RM xxx] vs Printed: [RM xxx]
3. **Verdict:** [VALID / FRAUD]

```json
{
  "extracted_data": {
    "merchant_name": "String",
    "receipt_no": "String",
    "amount": "String",
    "receipt_date": "YYYY-MM-DD",
    "location": "String"
  },
  "validation_result": {
    "reasoning": "String",  // Summarize the Scratchpad findings here.
    "conclusion": "String"  // "Yes" (if modified/fraud) OR "No" (if valid)
  }
}
    """
    payload = {
        "model": model,
        # "format": "json", # Removed to allow Scratchpad text
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze this receipt.", "images": [image_base64]}
        ],
        "options": {"temperature": 0.1}
    }
    
    # Handle Together AI
    if model.startswith("Together.AI/"):
        real_model = model.replace("Together.AI/", "")
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Analyze this receipt according to the system prompt."},
                    {
                        "type": "image_url", 
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        # Override payload for OpenAI Compatible API
        payload = {
            "model": real_model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096,
            "stream": False
        }
        
        response = requests.post(TOGETHER_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Normalize to match Ollama output structure used by caller
        return {
            "model": real_model,
            "message": data['choices'][0]['message'],
            "eval_count": data.get('usage', {}).get('completion_tokens', 0),
            "prompt_eval_count": data.get('usage', {}).get('prompt_tokens', 0),
            "eval_duration": 0,
            "prompt_eval_duration": 0,
            "total_duration": 0
        }

    # Ollama
    response = requests.post(OLLAMA_CHAT_URL, json=payload)
    response.raise_for_status()
    return response.json()

def chat_api(history, new_question, image_base64, model):
    # Prepare messages
    messages = [{"role": "system", "content": "You are a helpful assistant analyzing a receipt. Be concise."}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Check Model Provider
    if model.startswith("Together.AI/"):
        real_model = model.replace("Together.AI/", "")
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Latest user message with image if needed
        # Note: Chat history usually carries text. We attach image to the LATEST message or just context.
        # For simplicity in this chat interface, we attach image to the 'user' query if it's the first time, 
        # but here we just attach it to current message to be safe.
        
        user_content = [
            {"type": "text", "text": new_question},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": real_model,
            "messages": messages,
            "stream": False # Use non-streaming for Together simple integration (streaming requires SSE parsing update)
        }
        
        return requests.post(TOGETHER_API_URL, json=payload, headers=headers)
        
    else:
        # Ollama
        messages.append({"role": "user", "content": new_question, "images": [image_base64]})
        payload = {"model": model, "stream": True, "messages": messages}
        return requests.post(OLLAMA_CHAT_URL, json=payload, stream=True)

# Main UI
# Main UI
tab1, tab2 = st.tabs(["Analysis Workspace", "Execution Logs"])

with tab1:
    col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Upload Receipt")
    uploaded_file = st.file_uploader("Choose an image...", type=['jpg', 'jpeg', 'png'])
    
    # Display Image (either from upload or history)
    if uploaded_file:
        # User just uploaded a file
        if 'uploaded_file_id' not in st.session_state or st.session_state.uploaded_file_id != uploaded_file.file_id:
            # New upload: reset everything
            st.session_state.image_base64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
            st.session_state.uploaded_file_id = uploaded_file.file_id
            for key in ['analysis_result', 'chat_history', 'usage_stats', 'timings', 'current_file_path']:
                if key in st.session_state: del st.session_state[key]
            
    if 'image_base64' in st.session_state:
        image = Image.open(BytesIO(base64.b64decode(st.session_state.image_base64)))
        st.image(image, caption='Receipt Image', use_column_width=True)

        if st.button("🔍 Analyze with AI", type="primary"):
            timings = {}
            t_start = time.time()
            
            with st.status("Processing Receipt...", expanded=True) as status:
                try:
                    # Step 1: Encode (Virtual step since we already have it, but for logging)
                    st.write(f"⏱️ {datetime.now().strftime('%H:%M:%S')} - Preparing image...")
                    timings['start'] = datetime.now().strftime('%H:%M:%S')
                    
                    # Step 2: API Call
                    st.write(f"⏱️ {datetime.now().strftime('%H:%M:%S')} - Sending to **{model_name}**...")
                    t_api_start = time.time()
                    full_response = analyze_receipt_api(st.session_state.image_base64, model_name)
                    t_api_end = time.time()
                    timings['api_call_duration'] = f"{t_api_end - t_api_start:.2f}s"
                    
                    # Step 3: Parse
                    st.write(f"⏱️ {datetime.now().strftime('%H:%M:%S')} - Parsing response...")
                    result_content = full_response['message']['content']
                    
                    # Extract JSON
                    json_str = None
                    # Try markdown json block
                    match = re.search(r'```json\s*(\{.*?\})\s*```', result_content, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                    else:
                        # Try finding first/last brace
                        s = result_content.find('{')
                        e = result_content.rfind('}')
                        if s != -1 and e != -1:
                            json_str = result_content[s:e+1]

                    if json_str:
                        analysis_json = json.loads(json_str)
                    else:
                        raise ValueError("Could not find valid JSON in response")
                    
                    # INJECT METADATA INTO JSON
                    analysis_json['model_used'] = full_response.get('model', model_name)
                    analysis_json['token_usage'] = {
                        "input": full_response.get('prompt_eval_count', 0),
                        "output": full_response.get('eval_count', 0)
                    }
                    # Also save the raw scratchpad text
                    analysis_json['auditor_scratchpad'] = result_content.replace(json_str if match else "", "").replace("```json", "").replace("```", "").strip()
                    
                    st.session_state.analysis_result = analysis_json
                    
                    # Stats
                    st.session_state.usage_stats = {
                        "Eval Duration": f"{full_response.get('eval_duration', 0)/1e9:.2f}s",
                        "Prompt Eval": f"{full_response.get('prompt_eval_duration', 0)/1e9:.2f}s",
                        "Total Duration": f"{full_response.get('total_duration', 0)/1e9:.2f}s",
                        "Prompt Tokens": full_response.get('prompt_eval_count', 0),
                        "Output Tokens": full_response.get('eval_count', 0),
                        "Model": full_response.get('model', 'unknown')
                    }
                    
                    timings['end'] = datetime.now().strftime('%H:%M:%S')
                    timings['total_wall_time'] = f"{time.time() - t_start:.2f}s"
                    st.session_state.timings = timings
                    
                    # Save Record
                    merchant_name = st.session_state.analysis_result.get('extracted_data', {}).get('merchant_name', 'Unknown')
                    filepath = save_record(
                        merchant_name, 
                        st.session_state.image_base64,
                        st.session_state.analysis_result,
                        [], # Initial chat history is empty
                        st.session_state.usage_stats,
                        timings
                    )
                    st.session_state.current_file_path = filepath
                    st.session_state.chat_history = []
                    
                    st.write(f"💾 Saved record to history.")
                    status.update(label="Analysis Complete!", state="complete", expanded=False)
                    st.rerun()
                    
                except Exception as e:
                    status.update(label="Analysis Failed", state="error")
                    st.error(f"Error: {str(e)}")

with col2:
    if 'analysis_result' in st.session_state:
        st.subheader("2. Analysis Results")
        
        # Timings Display
        if 'timings' in st.session_state:
            t = st.session_state.timings
            with st.expander("⏱️ Timing Breakdown", expanded=False):
                st.write(f"**Start:** {t.get('start')} | **End:** {t.get('end')}")
                st.write(f"**Model Inference Time:** {t.get('api_call_duration')}")
                st.write(f"**Total Workflow Time:** {t.get('total_wall_time')}")

        data = st.session_state.analysis_result
        extracted = data.get('extracted_data', {})
        validation = data.get('validation_result', {})
        
        # Scratchpad
        with st.expander("📝 Auditor Scratchpad & Reasoning", expanded=True):
            if 'auditor_scratchpad' in data:
                st.markdown(data['auditor_scratchpad'])
            else:
                st.write(validation.get('reasoning', 'No reasoning provided.'))

        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Merchant", extracted.get('merchant_name', 'Unknown'))
        m2.metric("Total", f"RM {extracted.get('amount', '0.00')}")
        m3.metric("Date", extracted.get('receipt_date', 'Unknown'))
        
        # Validation / Fraud Status
        st.subheader("Verdict")
        verdict = validation.get('conclusion', '').lower()
        if 'yes' in verdict or 'fraud' in verdict:
            st.error(f"⚠️ FRAUD SUSPECTED: {validation.get('conclusion')}")
        else:
             st.success(f"✅ Receipt Validated: {validation.get('conclusion')}")
        
        st.info(f"**Reasoning:** {validation.get('reasoning')}")
            
        with st.expander("View Raw JSON Data"):
            st.json(data)
            
        # Token Usage Stats
        st.markdown("---")
        st.subheader("📊 AI Consumption Stats")
        sc1, sc2, sc3 = st.columns(3)
        u_stats = st.session_state.get('usage_stats', {})
        sc1.metric("Tokens In", u_stats.get('Prompt Tokens', 0))
        sc2.metric("Tokens Out", u_stats.get('Output Tokens', 0))
        sc3.metric("Model", u_stats.get('Model', 'Unknown').split('/')[-1]) # Shorten model name if possible
            
        st.divider()
        st.subheader("3. Chat")
        
        if 'chat_history' not in st.session_state: st.session_state.chat_history = []
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        if prompt := st.chat_input("Ask about this receipt..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_resp = ""
                
                try:
                    resp = chat_api(st.session_state.chat_history[:-1], prompt, st.session_state.image_base64, model_name)
                    
                    if model_name.startswith("Together.AI/"):
                        # Non-streaming handle for Together
                        resp_json = resp.json()
                        full_resp = resp_json['choices'][0]['message']['content']
                        placeholder.markdown(full_resp)
                        st.session_state.chat_history.append({"role": "assistant", "content": full_resp})
                    else:
                        # Streaming handle for Ollama
                        for line in resp.iter_lines():
                            if line:
                                try:
                                    json_line = json.loads(line)
                                    if "message" in json_line and "content" in json_line["message"]:
                                        chunk = json_line['message']['content']
                                        full_resp += chunk
                                        placeholder.markdown(full_resp + "▌")
                                    elif "response" in json_line: # fallback for non-chat endpoints sometimes
                                        chunk = json_line['response']
                                        full_resp += chunk
                                        placeholder.markdown(full_resp + "▌")
                                except json.JSONDecodeError:
                                    continue
                                    
                        placeholder.markdown(full_resp)
                        st.session_state.chat_history.append({"role": "assistant", "content": full_resp})
                    
                    # Update saved record with new chat
                    if 'current_file_path' in st.session_state and 'analysis_result' in st.session_state:
                         save_record(
                            st.session_state.analysis_result.get('extracted_data', {}).get('merchant_name', 'Unknown'),
                            st.session_state.image_base64,
                            st.session_state.analysis_result,
                            st.session_state.chat_history,
                            st.session_state.usage_stats,
                            st.session_state.timings,
                            existing_filename=os.path.basename(st.session_state.current_file_path)
                        )
                        
                except Exception as e:
                    placeholder.error(f"Error communicating with model: {str(e)}")

# Log View Tab
with tab2:
    st.header("📜 Execution Logs")
    
    # Reload files to ensure up to date
    log_files = sorted(glob.glob(f"{HISTORY_DIR}/*.json"), reverse=True)
    
    logs_data = []
    for fpath in log_files:
        try:
            with open(fpath, 'r') as f:
                d = json.load(f)
                
                # Extract Data
                fname = os.path.basename(fpath)
                ts = d.get('timestamp', 'N/A')
                merchant = d.get('extracted_data', {}).get('merchant_name') or d.get('merchant') or 'Unknown'
                model = d.get('usage_stats', {}).get('Model', 'Unknown')
                t_in = d.get('usage_stats', {}).get('Prompt Tokens', 0)
                t_out = d.get('usage_stats', {}).get('Output Tokens', 0)
                
                # Time Taken
                timings = d.get('timings', {})
                duration = timings.get('total_wall_time', 'N/A')
                
                logs_data.append({
                    "Date & Time": ts,
                    "Merchant": merchant,
                    "Model": model,
                    "Time Taken": duration,
                    "Tokens In": t_in,
                    "Tokens Out": t_out,
                    "File Path": fpath
                })
        except Exception as e:
            continue
            
    if logs_data:
        if pd:
            df = pd.DataFrame(logs_data)
            st.dataframe(df, use_container_width=True, column_config={
                "File Path": None # Hide File Path
            })
            
            st.subheader("🔍 Inspect Log Details")
            
            # Selection
            selected_idx = st.selectbox("Select a log entry to view JSON:", range(len(logs_data)), format_func=lambda i: f"{logs_data[i]['Date & Time']} - {logs_data[i]['Merchant']}")
            
            if selected_idx is not None:
                selected_row = logs_data[selected_idx]
                st.write(f"**Viewing Log for:** {selected_row['Merchant']} ({selected_row['Date & Time']})")
                
                with open(selected_row['File Path'], 'r') as f:
                    st.json(json.load(f))
        else:
            st.table(logs_data)
            st.warning("Pandas not installed. Install pandas for a better table view.")
    else:
        st.info("No execution logs found.")

