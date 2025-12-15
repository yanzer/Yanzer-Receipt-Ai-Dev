# Task: Install Local LLM on Intel MacBook Pro

## Status
- [x] Analyze Hardware Constraints <!-- id: 0 -->
- [x] Download Ollama for macOS (v0.1.32 - Legacy) <!-- id: 1 -->
- [x] User Unzips and Moves Ollama to Applications <!-- id: 2 -->
- [x] Verify Installation via Terminal (Found binary at Resources path) <!-- id: 4 -->
- [x] Debug: Identify why Ollama Server is not starting <!-- id: 5 -->
- [x] Start Ollama Server Manually (verified running) <!-- id: 6 -->
- [x] Pull and Run Llama 3.2 3B Model (Success!) <!-- id: 3 -->
- [x] Task Complete! <!-- id: 7 -->

## ReceiptGuard AI (Project)
- [x] Pull Vision Model (`llava-phi3`) (In Background...) <!-- id: 10 -->
- [x] Create `receipt_guard.py` <!-- id: 11 -->
- [x] Test with Generated Receipt (Success!) <!-- id: 12 -->

## New Request: Qwen Vision (Qwen2.5-VL)
- [x] Verify Qwen2.5-VL availability and RAM usage <!-- id: 13 -->
- [x] Pull `qwen2.5-vl:3b` (In Background...) <!-- id: 14 -->
- [x] Update `receipt_guard.py` to use Qwen <!-- id: 15 -->
- [ ] Test with User Receipt (`uploaded_image_...128.jpg`) <!-- id: 17 -->
- [ ] Compare performance with LlaVA-Phi3 <!-- id: 16 -->

## Web Project (ReceiptGuard UI)
- [x] Create `app.py` (Streamlit) <!-- id: 18 -->
- [x] Install Streamlit Dependencies <!-- id: 21 -->
- [x] Run App (`streamlit run app.py`) <!-- id: 19 -->
- [x] Update UI: Model Selector (Dropdown) <!-- id: 24 -->
- [x] Update UI: Status Logs & Token Usage <!-- id: 25 -->
- [x] Add Feature: Step-by-step Timestamps <!-- id: 26 -->
- [x] Add Feature: Save/Load History Records <!-- id: 27 -->
- [x] Debug: Chat Response missing in UI (Fixed JSON parsing) <!-- id: 28 -->

## Documentation & Handoff
- [x] Create `README.md` for fresh install <!-- id: 29 -->

## Legacy Items
- [ ] Retry Qwen Pull (`qwen2.5-vl:3b`) <!-- id: 23 -->

## Programmatic Usage
- [x] Create Python Demo Script <!-- id: 8 -->
- [ ] Explain REST API (`curl`) <!-- id: 9 -->

## User Context
- Hardware: MacBook Pro 2016 (Intel i5, 8GB RAM)
- OS: macOS Monterey
- Goal: Run "powerful" open source LLM
- Constraint: 8GB RAM limits choice to <4B parameter models (Llama 3.2 3B, Phi-3).
- Path: Option A (Direct Download)
