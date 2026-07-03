# 🫀 مساعد القلب الذكي — Smart Heart Assistant

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![Flask Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg?style=flat-square)](https://flask.palletsprojects.com/)
[![Nabda Project](https://img.shields.io/badge/organization-Nabda--Project-red.svg?style=flat-square)](https://github.com/Nabda-Project)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![CORS Supported](https://img.shields.io/badge/CORS-enabled-brightgreen.svg?style=flat-square)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

The **Smart Heart Assistant** (مساعد القلب الذكي) is an intelligent, conversational medical intake chatbot designed specifically for Arabic-speaking patients. By guiding users through a friendly, natural conversation instead of a static form, it gathers comprehensive demographic, lifestyle, medical history, and cardiac symptom data.

As a core component of the **[Nabda Project](https://github.com/Nabda-Project)** (a connected cardiovascular healthcare ecosystem), this chatbot automatically generates structured case summaries and clinical reports, saving them locally and synchronizing them with a primary Spring Boot backend to assist physicians during clinical consultations.

---

## 📖 Table of Contents

- [Core Features](#-core-features)
- [Architecture & Data Flow](#-architecture--data-flow)
- [Conversational Pipeline Stages](#-conversational-pipeline-stages)
- [Project Directory Structure](#-project-directory-structure)
- [Setup & Installation](#%EF%B8%8F-setup--installation)
- [Usage & Script Utilities](#-usage--script-utilities)
- [API Reference](#-api-reference)
- [Technical Internals](#-technical-internals)
- [Data Security & Environment Protection](#-data-security--environment-protection)
- [Future Roadmap](#-future-roadmap)
- [Medical Disclaimer](#-medical-disclaimer)
- [License](#-license)

---

## 🌟 Core Features

- **Stateful Multi-Session Concurrency:** Supports multiple parallel chats simultaneously. Flask manages session tracking using secure cookie-based session identifiers (`session_id`) and automatically cleanses session history to optimize memory usage.
- **Arabic NLP & Text Normalization:** Built-in normalization filters diacritics, varying representations of characters (e.g., hamzas), and ignores English characters in text fields to ensure robust, predictable Arabic parser matching.
- **Dynamic Symptom Deep-Dive Loops:** If a patient selects specific cardiac symptoms (e.g., chest pain, dyspnea, palpitations), the engine enters a dynamic sub-question loop for each symptom, requesting severity, pattern, triggers, and localized details (e.g., pain radiation or posture-induced breathlessness).
- **Asynchronous AI Diagnostic Client:** Features a robust polling client that submits case summaries to a remote GPU-backed diagnostic AI endpoint, polls job status URLs (`poll_url`) with a backoff interval, and handles retries or timeouts gracefully.
- **Structured Clinical Reporting:** Generates dual-format outputs upon completing an intake session:
  - **Structured JSON Report:** For automated backend storage and database serialization.
  - **Formatted Arabic Narrative & Clinical Summary:** For direct reading by cardiologists.
- **Spring Boot Sync Ready:** Structured to post the resulting intake report to the central Java Spring Boot REST endpoints to build a unified patient health record.

---

## ⚙️ Architecture & Data Flow

The mid-tier Flask service coordinates NLP processing, local logging, and downstream API relays:

```mermaid
graph TD
    A["Browser Client<br/>(templates/index.html)"] -->|"POST /chat<br/>(Message payload + Cookies)"| B["Flask Web Server<br/>(app.py)"]
    B -->|"handle_message(sid, message)"| C["State & Intake Engine<br/>(med.py)"]
    
    subgraph Data & Downstream Tier
        C -->|"Saves JSON & TXT"| D[("patient_records/<br/>(Local Storage)")]
        C -->|"POST /generate (Submit Job)"| E["Diagnostic AI Endpoint<br/>(Async GPU Server)"]
        E -->|"Returns Job URL"| C
        C -->|"GET /jobs/id (Poll status)"| E
        C -->|"Relays Case Summary<br/>(REST API Sync)"| F["Spring Boot Backend<br/>(Central DB)"]
    end
    
    C -->|"Formulates next prompt"| B
    B -->|"Returns JSON response"| A
```

---

## 💬 Conversational Pipeline Stages

The intake engine guides users through 6 distinct stages, validating and converting natural inputs into medical code representations:

```mermaid
graph TD
    Start(["Start Chat"]) --> Demographics["1. Demographics<br/>(Age, Sex, Height, Weight)"]
    Demographics --> History["2. Medical History<br/>(Chronic Diseases, Meds, Lifestyle)"]
    History --> SymptomSelection["3. Symptom Selection<br/>(Multi-choice checklist)"]
    SymptomSelection --> SymptomLoop{"4. Dynamic Symptom Loop"}
    
    SymptomLoop -->|"For each chosen symptom"| AskDetails["Ask Severity, Triggers, Patterns, and Extras"]
    AskDetails --> SymptomLoop
    
    SymptomLoop -->|"Loop Finished"| RedFlags["5. Red Flags Screening<br/>(Urgent signs check)"]
    RedFlags --> FreeText["6. Free Text Notes<br/>(Additional info)"]
    FreeText --> BuildNarrative["Build Arabic Case Narrative"]
    BuildNarrative --> CallAI["Call Diagnostic AI Server"]
    SaveReport["Save JSON & TXT Reports"]
    CallAI --> SaveReport
    SaveReport --> Complete(["End Chat & Sync"])
```

### Breakdown of Stages

| Stage | Focus Area | Arabic Example Prompt | Validation Rules |
| :--- | :--- | :--- | :--- |
| **1. DEMOGRAPHICS** | Age, biological sex, weight, height, pregnancy status. | `كم العمر بالسنوات؟` | Number ranges (Age: 1-110, Weight: 3-300 kg, Height: 50-250 cm). |
| **2. HISTORY** | Prior cardiac conditions, tests, chronic illnesses, active medications, family history, and smoking. | `هل سبق تشخيصك بمرض في القلب؟` | Fuzzy Arabic matches, choices, and multi-choice selections. |
| **3. SYMPTOM_SELECTION** | Checkbox style checklist of common cardiac indicators. | `ما الأعراض التي تشعر بها؟` | Multi-choice list validation against pre-defined symptom labels. |
| **4. SYMPTOM_LOOP** | Deep-dives into characteristics of *each* checked symptom. | `ما شدة [ألم الصدر] عندما تحدث؟` | Dynamically executes sub-questions for chosen symptoms. |
| **5. RED_FLAG_SCREENING** | Checks for warning signs (exertional pain, exertional syncope). | `هل سبق أن أُغمي عليك أثناء الرياضة؟` | Yes/No/Unsure choices to screen for immediate emergency signs. |
| **6. FREE_TEXT** | Final patient remarks before generating the report. | `هل هناك أي شيء آخر تود إضافته؟` | Free text normalized, filtering out English characters. |

---

## 📂 Project Directory Structure

Below is the directory layout of the repository. Click the file links to view the source files directly:

- [app.py](file:///E:/side%20projects/GP/Chatbot/app.py) — The Flask web server entry point containing CORS config, session setup, and HTTP routes.
- [med.py](file:///E:/side%20projects/GP/Chatbot/med.py) — Core state machine, question banks, translation maps, dynamic symptom engines, and NLP utility parsers.
- [model_client.py](file:///E:/side%20projects/GP/Chatbot/model_client.py) — Interactive and command-line diagnostic client that polls remote AI endpoints.
- [json_to_txt.py](file:///E:/side%20projects/GP/Chatbot/json_to_txt.py) — Utility script to convert generated patient JSON reports into clean, human-readable text layouts for doctors.
- [test_med_api.py](file:///E:/side%20projects/GP/Chatbot/test_med_api.py) — Integration test script that exercises the diagnostic GPU endpoints.
- [templates/index.html](file:///E:/side%20projects/GP/Chatbot/templates/index.html) — Elegant, responsive Arabic RTL chat frontend interface with custom styling and animations.
- [.gitignore](file:///E:/side%20projects/GP/Chatbot/.gitignore) — Tells Git which untracked files (e.g. `.env`, `.venv`, log summaries) to ignore.
- [.env.example](file:///E:/side%20projects/GP/Chatbot/.env.example) — Config environment variable template.

---

## 🛠️ Setup & Installation

### Prerequisites

* **Python 3.8+**
* **Pip** (Python Package Installer)
* **Git**

### Step-by-Step Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Nabda-Project/Chatbot.git
   cd Chatbot
   ```

2. **Establish a Virtual Environment:**
   * **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   * **macOS/Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Copy the example environment template to create your own local configuration:
   ```bash
   cp .env.example .env
   ```
   Open the newly created `.env` file and insert your API keys and endpoints:
   ```properties
   GOOGLE_API_KEY=your-google-gemini-key
   BACKEND_URL=http://localhost:9091
   BACKEND_JWT_TOKEN=your-jwt-authorization-token
   BACKEND_PATIENT_ID=25
   ```

---

## 🚀 Usage & Script Utilities

### 1. Web Interactive Mode (Default)
Start the local Flask development server:
```bash
python app.py
```
By default, the server runs on `http://127.0.0.1:5000`. Navigate to the address in your browser to access the responsive RTL web UI.

### 2. Command-Line (CLI) Interactive Chat
To run the intake state machine directly inside your terminal (great for debugging and workflow testing):
```bash
python med.py
```

### 3. Report Conversion Utility
Convert generated patient JSON reports into clean, physician-friendly text layouts using [json_to_txt.py](file:///E:/side%20projects/GP/Chatbot/json_to_txt.py):
```bash
# Convert a single report
python json_to_txt.py ./patient_records/report_180835.json

# Convert multiple reports at once
python json_to_txt.py report_1.json report_2.json

# Convert all reports in a directory and export to a specific output path
python json_to_txt.py --dir ./patient_records --out ./patient_records/formatted_summaries
```

### 4. Diagnostic AI Client Utility
Interface directly with the GPU-based diagnostic model to query and poll responses using [model_client.py](file:///E:/side%20projects/GP/Chatbot/model_client.py):
```bash
# Interactive CLI prompting mode
python model_client.py

# One-shot command line mode
python model_client.py "أشعر بألم شديد في الصدر وضيق تنفس عند صعود الدرج"

# Pipe mode support
echo "أعاني من تسارع شديد في ضربات القلب" | python model_client.py -
```

---

## 🔌 API Reference

### Endpoints Overview

| Method | Endpoint | Description | Headers |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves the HTML frontend interface ([templates/index.html](file:///E:/side%20projects/GP/Chatbot/templates/index.html)). | — |
| `POST` | `/chat` | Submits user message and returns the next question or the final clinical diagnosis report. | `Content-Type: application/json` |
| `POST` | `/reset` | Resets the active session state and clears session cookies. | — |
| `GET` | `/health` | Simple health check endpoint returning microservice uptime status. | — |

### `/chat` Request Specs

* **Request Payload Format:**
  ```json
  {
    "message": "نعم، أشعر بألم مستمر في الصدر"
  }
  ```

* **Intermediate Response Format (More Questions):**
  ```json
  {
    "success": true,
    "done": false,
    "question": {
      "field": "symptom_detail.chest_pain.radiation",
      "question_text": "هل ينتشر ألم الصدر إلى مناطق أخرى؟ (اختر كل ما ينطبق)",
      "type": "multi_choice",
      "options": [
        {"label": "لا ينتشر", "value": "no_radiation"},
        {"label": "الذراع / الكتف / اليد اليسرى", "value": "left_arm"},
        {"label": "الذراع / الكتف / اليد اليمنى", "value": "right_arm"},
        {"label": "الظهر / بين الكتفين", "value": "back"},
        {"label": "الرقبة", "value": "neck"},
        {"label": "الفك أو الأسنان", "value": "jaw"},
        {"label": "أعلى البطن", "value": "upper_abdomen"}
      ]
    },
    "reply": "هل ينتشر ألم الصدر إلى مناطق أخرى؟ (اختر كل ما ينطبق)"
  }
  ```

* **Final Response Format (Intake Complete):**
  ```json
  {
    "success": true,
    "done": true,
    "question": null,
    "analysis_result": {
      "differential_diagnosis": "أسباب قلبية أولية محتملة نظراً لتأثر ألم الصدر بالمجهود...",
      "urgency_level": "عالية - تتطلب استشارة طبيب قلب في أسرع وقت",
      "suggested_tests": ["رسم قلب كهربائي ECG", "موجات فوق صوتية على القلب Echo"],
      "immediate_advice": "تجنب أي مجهود بدني زائد والتوجه فوراً لأقرب مستشفى عند زيادة الألم"
    },
    "reply": "📋 انتهينا من جمع البيانات... [الملخص السريري والتحليل الطبي المتكامل]"
  }
  ```

---

## ⚙️ Technical Internals

### Stateful Engine & Stage Management
The main conversational handler [handle_message](file:///E:/side%20projects/GP/Chatbot/med.py#L650) in `med.py` is powered by a state machine that tracks each session using a local memory store. 
1. When a message is received, [_get_or_create_session](file:///E:/side%20projects/GP/Chatbot/app.py#L12) in `app.py` loads the state.
2. The user's input is validated and parsed using [smart_parse](file:///E:/side%20projects/GP/Chatbot/med.py#L309).
3. The engine uses a dependency evaluation routine ([check_depends](file:///E:/side%20projects/GP/Chatbot/med.py#L371)) to check if optional questions (such as pregnancy status depending on the patient's sex) should be asked.
4. If a dynamic symptom loop is entered, the engine queues and traverses symptom-specific questions built on the fly by [_build_known_symptom_questions](file:///E:/side%20projects/GP/Chatbot/med.py#L252).

### Text Normalization & Security Filter
To maintain clinical safety:
- User free-text notes are stripped of English characters using regex filters to ensure only Arabic notes are relayed to downstream diagnostic APIs.
- Diacritics are removed, and typical character variants in Arabic (e.g. `أ`, `إ`, `آ`, `ة`, `ى`) are normalized to ensure robust option selections.

---

## 🔒 Data Security & Environment Protection

To prevent credentials from leaking into Git version history:
- Sensitive variables (API keys, JWT authorization headers, server endpoints) must be configured in a local `.env` file.
- The `.gitignore` file is strictly configured to ignore the `.env` file and any generated security reports (such as `gitleaks-report.json` or `replacements.txt`).
- **Never commit active API keys.** Ensure placeholder configurations are used for code bases before publishing.

---

## 🗺️ Future Roadmap

- [ ] **Dynamic Question Routing:** Implement conditional stage branching from `under_dev/stage_questions.py` to support deep logical trees based on nested patient history parameters.
- [ ] **IoT Sensor Sync:** Integrate the simulated frontend `/vitals` route with actual IoT hardware (e.g., smartwatches, pulse oximeters) to pull live heart rate, blood pressure, and SPO2 directly into the intake summary.
- [ ] **Physician Dashboard Integrations:** Expose webhook handlers that push live conversational transcripts to the doctor's EHR (Electronic Health Record) dashboard within Nabda's clinical suite.

---

## ⚠️ Medical Disclaimer

> [!WARNING]
> This chatbot is an intake pre-screening tool designed purely to collect clinical summaries for review by human doctors. **It does not provide professional medical diagnoses, treatments, or automated prescriptions.**
> If you are experiencing severe chest pain, tightness, radiation of pain to your jaw/left arm, sudden loss of consciousness, or immediate health emergencies, please contact your local emergency services (e.g., **123** in Egypt, **911** in the US) immediately.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.

<p align="center">
  Developed with ❤️ by the <b>Nabda Project</b> Team.
</p>
