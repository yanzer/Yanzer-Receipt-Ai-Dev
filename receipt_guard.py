import requests
import json
import re
import base64
import sys
import os

# Configuration
# 'qwen2.5-vl:3b' is a state-of-the-art multimodal model optimized for OCR.
# It uses approx 3.2GB RAM and significantly outperforms older vision models.
MODEL_NAME = "qwen2.5-vl:3b" 
API_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """
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

def encode_image(image_path):
    """Encodes an image to base64 string"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")
    
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_receipt(image_path):
    print(f"🔍 Analyzing Receipt: {image_path}")
    print(f"🧠 Model: {MODEL_NAME} (Vision)")
    
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    payload = {
        "model": MODEL_NAME,
        # "format": "json", # Removed to allow Scratchpad
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": "Analyze this receipt image according to your instructions.",
                "images": [base64_image]
            }
        ],
        "options": {
            "temperature": 0.2, # Low temperature for more analytical/precise results
            "num_ctx": 4096     # Larger context window for complex receipts
        }
    }

    print("⏳ Sending to ReceiptGuard AI (this requires the 'llava-phi3' model)...")
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        content = result['message']['content']
        
        try:
            # Parse Mixed JSON/Text
            # Extract JSON
            json_str = None
            match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                 s = content.find('{')
                 e = content.rfind('}')
                 if s != -1 and e != -1:
                     json_str = content[s:e+1]
            
            if not json_str:
                raise ValueError("No JSON found")

            json_data = json.loads(json_str)
            scratchpad = content.replace(json_str if match else "", "").replace("```json", "").replace("```", "").strip()

            print("\n📝 AUDITOR SCRATCHPAD:")
            print(scratchpad)

            # INJECT METADATA
            json_data['model_used'] = result.get('model', MODEL_NAME)
            json_data['token_usage'] = {
                "input": result.get('prompt_eval_count', 0),
                "output": result.get('eval_count', 0)
            }

            print("\n✅ ANALYSIS COMPLETE:")
            print(json.dumps(json_data, indent=2))
            
            # Save to file
            output_file = image_path + ".analysis.json"
            with open(output_file, 'w') as f:
                json.dump(json_data, f, indent=2)
            print(f"\n💾 Saved result to: {output_file}")
            
        except (json.JSONDecodeError, ValueError):
            print("\n⚠️ Warning: Model output was not valid JSON. Raw output:")
            print(content)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to Ollama. Is it running?")
    except Exception as e:
        print(f"\n❌ Error during API call: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 receipt_guard.py <path_to_receipt_image>")
        print("Example: python3 receipt_guard.py ./my_receipt.jpg")
    else:
        analyze_receipt(sys.argv[1])
