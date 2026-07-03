# مساعد القلب الذكي — Smart Heart Assistant

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Nabda Project](https://img.shields.io/badge/organization-Nabda--Project-red.svg)](https://github.com/Nabda-Project)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Smart Heart Assistant** is an intelligent, conversational Arabic medical chatbot designed to assist patients in pre-screening for cardiovascular conditions. By conducting structured, step-by-step interviews in Arabic, the bot collects key demographic information, lifestyle habits, medical history, family history, and current cardiac symptoms. 

This chatbot is a core mid-tier service of the **[Nabda Project](https://github.com/Nabda-Project)**, an integrated graduation project focused on cardiovascular healthcare, and is fully integrated with a companion graduation thesis and LaTeX project book.

---

## Table of Contents

- [Overview](#overview)
- [Architecture & Data Flow](#architecture--data-flow)
- [Conversation Pipeline](#conversation-pipeline)
- [Key Features](#key-features)
- [Project Directory Structure](#project-directory-structure)
- [Setup & Installation](#setup--installation)
- [Usage & Execution Modes](#usage--execution-modes)
- [API Documentation](#api-documentation)
- [Future Roadmap](#future-roadmap)
- [Medical Disclaimer](#medical-disclaimer)

---

## Overview

Traditional medical intake forms can be tedious and prone to incomplete entries. **Smart Heart Assistant** solves this by offering a friendly, conversational interface in Arabic. It utilizes:
1. **Linear State Machine Pipeline:** Guides the user sequentially through Demographics, History, and Symptom assessment.
2. **Dynamic Symptom Loops:** Recursively queries specific details (severity, duration, triggers, relieving factors) for each reported symptom.
3. **Medical Advice Engine:** Analyzes collected indicators (e.g., BMI, smoking status, symptom severity) to generate localized Arabic health advice.
4. **Backend Database Synchronization:** Securely relays the structured JSON report to the central Java Spring Boot backend database.

> [!NOTE]
> Detailed theoretical frameworks, design patterns, and engineering choices are fully documented in the companion **[Graduation Project Book](https://github.com/Nabda-Project)**.

---

## Architecture & Data Flow

The assistant acts as a mid-tier NLP processing engine that sits between the client application and the main backend architecture:

```mermaid
graph TD
    subgraph Client [Client Tier]
        A["Browser Client (HTML5/JS)<br/>index.html"] 
    end

    subgraph Mid [Mid-Tier Chatbot Service]
        B["app.py<br/>(Flask Router & Session Management)"]
        C["med.py<br/>(State Machine & Arabic NLP Parser)"]
    end

    subgraph Core [Core Backend]
        D["Java Spring Boot Backend<br/>(Patient Database Controller)"]
    end

    A -->|"POST /chat<br/>(Message payload & Session cookies)"| B
    B -->|"handle_message(sid, msg)"| C
    C -->|"1. Local Log"| E[("patient_records/<br/>(JSON & TXT)")]
    C -->|"2. POST API Relay"| D
    C -->|"3. Formulate Response"| B
    B -->|"JSON reply"| A
```

### Main Flow Logic:
1. The **Browser UI** submits messages to Flask's `/chat` endpoint.
2. Flask identifies the user session (or spins up a new one using secure cookies) and calls `med.py`.
3. The chatbot evaluates if there's a pending question:
   - **Yes:** Normalizes, validates, and stores the user's input.
   - **No:** Advances the conversation to the next stage or symptom question.
4. Once all stages are completed:
   - Generates a localized Arabic medical summary.
   - Writes patient data to a local `patient_records/report_*.json` file.
   - Automatically relays the structured report as a payload to the Spring Boot REST endpoint (`/api/chatbot/complete?patientId={id}`).

---

## Conversation Pipeline

The bot structures the Arabic conversation across 6 sequential stages:

| Stage | Focus Area | Arabic Sample Question | Validation Types |
| :--- | :--- | :--- | :--- |
| **1. GREETING** | Welcome & Info consent | مرحباً بك في مساعد القلب الذكي | Free text / Any input to start |
| **2. DEMOGRAPHICS** | Gender, Age, Height, Weight | كم عمرك؟ / ما هو وزنك بالكيلوجرام؟ | Number limits (1-110), Choice |
| **3. LIFESTYLE & HISTORY**| Smoking, Activity, Chronic conditions, Meds | هل تدخن؟ / هل تعاني من سكري أو ضغط؟ | Choices, Normalization |
| **4. SYMPTOM SELECTION** | Multi-choice symptom picker | هل تشعر بألم في الصدر، نهجان، خفقان؟ | Choice matching (fuzzy parser) |
| **5. SYMPTOM LOOP** | Deep-dive per selected symptom | ما شدة الألم؟ / هل ينتشر للذراع الأيسر؟ | Dynamic sub-questions |
| **6. RED FLAG SCREENING** | Urgent critical symptoms check | هل فقدت الوعي تماماً؟ | Priority warnings logic |

---

## Key Features

- **Arabic NLP Normalization:** Normalizes diacritics, hamzas, and letters (e.g., matching "ألم" with "الم") to ensure robust parsing of patient inputs.
- **Stateful Multi-Session Concurrency:** Supports multiple simultaneous chats using secure session tracking. Inactive sessions are cleared automatically after 2 hours to optimize memory.
- **Comprehensive Symptom Deep-Dive:** Adapts dynamically depending on symptoms selected, drilling down into exact characteristics (e.g., pain quality, chest pain radiation, trigger thresholds).
- **Dual-Format Reporting:** Saves output reports locally as standard JSON (for backend serialization) and formatted text (for direct physician reading).
- **Spring Boot Sync:** Automated REST API synchronization to persist results directly in the master health record system.

---

## Project Directory Structure

```
Chatbot/
├── .env                       # Environment configuration (API keys, backend URLs)
├── .gitignore                 # Git ignore patterns
├── README.md                  # Comprehensive project documentation
├── requirements.txt           # Python dependency declarations
├── app.py                     # Flask web server, endpoints, and CORS config
├── med.py                     # Chatbot logic, question banks, and parsing algorithms
├── model_client.py            # Client interface for calling diagnostic LLM endpoints
├── json_to_txt.py             # Utility script converting JSON reports to clean TXT
├── test_med_api.py            # API testing and validation suite
├── templates/
│   └── index.html             # Rich frontend user interface (HTML/CSS/JS)
├── patient_records/           # Automatically generated patient JSON & TXT summaries
└── under_dev/                 # Experimental features (e.g., dynamic dependency parsing)
```

---

## Setup & Installation

### Prerequisites
* Python 3.8 or higher
* Pip (Python Package Installer)
* Git

### Step-by-Step Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Nabda-Project/Chatbot.git
   cd Chatbot
   ```

2. **Set Up a Virtual Environment:**
   * **Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
   * **Linux/macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the root directory (you can copy sample values) and supply your configuration keys:
   ```properties
   GOOGLE_API_KEY=your-google-gemini-key
   BACKEND_URL=http://localhost:9091
   BACKEND_JWT_TOKEN=your-jwt-authorization-token
   BACKEND_PATIENT_ID=25
   ```

---

## Usage & Execution Modes

### 1. Web Application Mode (Default)
Run the Flask server locally:
```bash
python app.py
```
The server will boot on `http://localhost:5000`. Open this address in your browser to access the interactive chat interface.

### 2. Command-Line (CLI) Chat Mode
Run the chatbot engine directly inside the terminal for debugging:
```bash
python med.py
```

### 3. Report Conversion Utility
Convert generated patient JSON reports into human-readable text documents:
```bash
# Convert a single report
python json_to_txt.py ./patient_records/report_180835.json

# Convert all reports in a directory
python json_to_txt.py --dir ./patient_records --out ./patient_records
```

---

## API Documentation

### Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the HTML frontend interface. |
| `POST` | `/chat` | Intercepts user messages and returns the next structured chatbot question/advice. |
| `POST` | `/reset` | Resets the current chat session and clears temporary state variables. |
| `GET` | `/health` | Simple microservice health check. |

### `/chat` Payload Specifications

* **Request Body:**
  ```json
  {
    "message": "نعم، أشعر بألم في الصدر"
  }
  ```

* **Response Body:**
  ```json
  {
    "success": true,
    "done": false,
    "question": "هل يمتد هذا الألم إلى ذراعك الأيسر أو الفك؟",
    "reply": "هل يمتد هذا الألم إلى ذراعك الأيسر أو الفك؟"
  }
  ```

---

## Future Roadmap

- [ ] **Dynamic Dependency Validation:** Fully integrate the dynamic parsing script in `under_dev/stage_questions.py` to allow multi-choice answers and relational question dependencies.
- [ ] **IoT Vitals Synchronization:** Connect the frontend `/vitals` route endpoint simulations to active IoT biosensors to feed pulse, blood oxygen, and blood pressure directly to the conversational advisor.
- [ ] **AI-Assisted Diagnostic Processing:** Expand the optional LLM processing capability in `model_client.py` to provide doctor-facing clinical summaries.

---

## Medical Disclaimer

> [!WARNING]
> This chatbot is a supportive clinical intake screening application and **does not constitute professional medical advice, diagnosis, or treatment**. Always seek the advice of a qualified healthcare provider for any questions regarding a medical condition. **If you are experiencing severe chest pain, breathlessness, or immediate medical discomfort, please contact your local emergency services (e.g., 123 in Egypt) immediately.**

---

<p align="center">
  Created by the <b>Nabda Project</b> Team.
</p>
