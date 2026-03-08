# 🫀 مساعد القلب الذكي — Smart Heart Assistant

A conversational Arabic medical chatbot that collects patient information through a guided dialogue and provides personalized heart health advice.

---

## Overview

Smart Heart Assistant is a Flask-based chatbot that walks users through a structured medical intake form in Arabic, then generates tailored cardiovascular health recommendations based on their responses. Patient data is saved locally as JSON reports.

---

## Features

- 🗣️ **Fully Arabic conversational interface**
- 📋 **Multi-stage intake flow** covering demographics, lifestyle, medical history, family history, and current symptoms
- 🧠 **Smart parsing** of Arabic text with normalization and fuzzy matching
- 💡 **Personalized advice** based on BMI, smoking status, and reported symptoms
- 💾 **Auto-saves patient reports** to `patient_records/` as timestamped JSON files
- 🔄 **Session reset** endpoint to start a new conversation
- 🌐 **REST API** ready for frontend integration

---

## Project Structure

```
├── app.py               # Flask web server & API routes
├── med.py               # Chatbot logic, state machine, and medical advice engine
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html       # Frontend chat interface
└── patient_records/     # Auto-generated patient JSON reports
```

---

## Setup & Installation

### Prerequisites

- Python 3.8+
- pip

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

Copy `.env` and fill in any required keys:

```bash
cp _env .env
```

### Run the app

```bash
python app.py
```

The server starts at `http://localhost:5000`.

---

## API Endpoints

| Method | Endpoint  | Description                        |
|--------|-----------|------------------------------------|
| GET    | `/`       | Serve the chat UI                  |
| POST   | `/chat`   | Send a user message, get a reply   |
| POST   | `/reset`  | Reset the conversation state       |
| GET    | `/health` | Health check                       |

### `/chat` Request & Response

**Request:**
```json
{ "message": "ذكر" }
```

**Response:**
```json
{
  "success": true,
  "reply": "كم عمرك؟"
}
```

---

## Conversation Flow

The bot guides the user through 7 sequential stages:

1. **Greeting** — Welcome message
2. **Basic Info** — Gender, age, weight, height
3. **Smoking** — Current / former / non-smoker
4. **Physical Activity** — Exercise frequency
5. **Medical History** — Chronic conditions & medications
6. **Family History** — Heart disease in family
7. **Current Symptoms** — Chest pain, shortness of breath, palpitations, swelling

At the end, the bot generates a personalized summary with health tips and saves a JSON report.

---

## Running in CLI Mode

You can also run the chatbot directly in the terminal without the web server:

```bash
python med.py
```

---

## Disclaimer

> ⚠️ This tool is for informational purposes only and does not replace professional medical advice. In case of severe chest pain, go to the emergency room immediately.
