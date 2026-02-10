# med.py
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# ================== CONFIG ==================
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel(
    "models/gemini-2.0-flash-exp",
    generation_config={
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
    }
)

# ================== CONSTANTS ==================
STAGES = [
    "GREETING",
    "BASIC_INFO",
    "SMOKING",
    "PHYSICAL_ACTIVITY",
    "DIET",
    "SLEEP",
    "STRESS",
    "CHRONIC_DISEASES",
    "MEDICATIONS",
    "FAMILY_HISTORY",
    "PREVIOUS_HEART_ISSUES",
    "CURRENT_SYMPTOMS",
    "FINAL_QUESTIONS",
    "SUMMARY",
]

SYMPTOM_LABELS = {
    "chest_pain": "ألم في الصدر",
    "shortness_of_breath": "ضيق في التنفس",
    "palpitations": "خفقان القلب",
    "dizziness": "دوخة",
    "fainting": "إغماء",
    "fatigue": "تعب غير معتاد",
    "swelling": "تورم القدمين/الساقين",
    "nausea": "غثيان",
    "sweating": "تعرق شديد",
}

# ================== STATE ==================
class ConversationState:
    def __init__(self):
        self.stage_index = 0
        self.current_field = None
        self.current_question = None
        self.retry_count = 0
        self.max_retries = 2
        self.data = {
            "timestamp": datetime.now().isoformat(),
            "basic_info": {},
            "lifestyle": {
                "smoking": {},
                "physical_activity": {},
                "diet": {},
                "sleep": {},
                "stress": {},
            },
            "medical_history": {
                "chronic_diseases": "",
                "current_medications": "",
                "family_history": {},
                "previous_heart_issues": {},
            },
            "symptoms": {},
            "conversation_history": [],
        }

    def current_stage(self):
        return STAGES[self.stage_index]

    def next_stage(self):
        self.stage_index += 1
        self.current_field = None
        self.current_question = None
        self.retry_count = 0

    def reset(self):
        self.__init__()

conversation_state = ConversationState()

# ================== HELPERS ==================
def get_nested(data, path):
    cur = data
    for k in path.split("."):
        if k not in cur:
            return None
        cur = cur[k]
    return cur

def set_nested(data, path, value):
    cur = data
    keys = path.split(".")
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value

def validate_answer(answer, vtype, **kwargs):
    answer = answer.strip()
    if vtype == "number":
        try:
            num = float(answer)
            if kwargs.get("min", -1e9) <= num <= kwargs.get("max", 1e9):
                return True, num
            return False, "رقم خارج النطاق"
        except:
            return False, "من فضلك أدخل رقم صحيح"

    if vtype == "choice":
        options = kwargs.get("options", {})
        for key, val in options.items():
            if key.lower() in answer.lower():
                return True, val
        return False, "مش فاهمك قوي 🤔 ممكن توضحي أكتر؟"

    if vtype == "text":
        if len(answer) >= 1:
            return True, answer
        return False, "الرجاء كتابة إجابة أوضح"

    return True, answer

def smart_parse(answer, vtype, options=None):
    ok, val = validate_answer(answer, vtype, options=options)
    return val if ok else None

# ================== QUESTIONS ==================
STAGE_QUESTIONS = {
    "GREETING": {"message": "مرحباً 👋\nسأسألك بعض الأسئلة الطبية البسيطة لمساعدة طبيب القلب.\nهل أنت مستعد؟ (نعم)"},
    "BASIC_INFO": {
        "questions": [
            {"field": "basic_info.age", "q": "كم عمرك؟", "v": "number", "min": 1, "max": 120},
            {"field": "basic_info.gender", "q": "الجنس؟ (ذكر/أنثى)", "v": "choice",
             "options": {"ذكر": "male", "أنثى": "female"}},
            {"field": "basic_info.weight", "q": "الوزن (كجم)؟", "v": "number", "min": 20, "max": 300},
            {"field": "basic_info.height", "q": "الطول (سم)؟", "v": "number", "min": 100, "max": 250},
        ]
    },
    "SMOKING": {
        "questions": [
            {"field": "lifestyle.smoking.status", "q": "هل تدخن؟ (لا / نعم / توقفت)", "v": "choice",
             "options": {"لا": "never", "نعم": "current", "توقفت": "quit"}},
        ],
        "follow": {
            "current": [
                {"field": "lifestyle.smoking.cigs", "q": "عدد السجائر يومياً؟", "v": "number"},
                {"field": "lifestyle.smoking.years", "q": "منذ كم سنة؟", "v": "number"},
            ],
            "quit": [
                {"field": "lifestyle.smoking.quit_years", "q": "منذ كم سنة توقفت؟", "v": "number"}
            ]
        }
    },
    "PHYSICAL_ACTIVITY": {
        "questions": [
            {"field": "lifestyle.physical_activity.level", "q": "مستوى النشاط؟ (قليل / متوسط / عالي)", "v": "choice",
             "options": {"قليل": "low", "متوسط": "moderate", "عالي": "high"}},
        ],
        "follow": {
            "moderate": [
                {"field": "lifestyle.physical_activity.type", "q": "نوع الرياضة؟", "v": "text"},
                {"field": "lifestyle.physical_activity.duration", "q": "المدة بالدقائق؟", "v": "number"},
            ],
            "high": [
                {"field": "lifestyle.physical_activity.type", "q": "نوع الرياضة؟", "v": "text"},
                {"field": "lifestyle.physical_activity.duration", "q": "المدة بالدقائق؟", "v": "number"},
            ],
        }
    },
    "DIET": {
        "questions": [
            {"field": "lifestyle.diet.salt", "q": "كمية الملح؟ (قليلة/متوسطة/كثيرة)", "v": "choice",
             "options": {"قليلة": "low", "متوسطة": "moderate", "كثيرة": "high"}},
            {"field": "lifestyle.diet.fat", "q": "أطعمة دهنية؟ (نادر/أحياناً/كثير)", "v": "choice",
             "options": {"نادر": "low", "أحياناً": "moderate", "كثير": "high"}},
        ]
    },
    "SLEEP": {"questions": [{"field": "lifestyle.sleep.hours", "q": "كم ساعة تنام؟", "v": "number", "min": 1, "max": 24}]},
    "STRESS": {"questions": [{"field": "lifestyle.stress.level", "q": "مستوى التوتر؟ (منخفض/متوسط/عالي)", "v": "choice",
                               "options": {"منخفض": "low", "متوسط": "moderate", "عالي": "high"}}]},
    "CHRONIC_DISEASES": {"questions": [{"field": "medical_history.chronic_diseases", "q": "هل لديك أمراض مزمنة؟", "v": "text"}]},
    "MEDICATIONS": {"questions": [{"field": "medical_history.current_medications", "q": "هل تتناول أدوية حالياً؟", "v": "text"}]},
    "FAMILY_HISTORY": {"questions": [{"field": "medical_history.family_history.heart", "q": "تاريخ عائلي لأمراض القلب؟", "v": "text"}]},
    "PREVIOUS_HEART_ISSUES": {"questions": [{"field": "medical_history.previous_heart_issues.history", "q": "هل عانيت من مشاكل قلبية سابقاً؟", "v": "text"}]},
    "CURRENT_SYMPTOMS": {"questions": [{"field": "symptoms.raw", "q": "هل تشعر بأي أعراض حالياً؟ احكي براحتك", "v": "text"}]},
    "FINAL_QUESTIONS": {"questions": [{"field": "additional_info", "q": "هل تريد إضافة أي شيء؟", "v": "text"}]},
}

# ================== SYMPTOM EXTRACTION ==================
def extract_symptoms(text):
    prompt = f"استخرج أعراض القلب فقط من النص التالي بصيغة JSON:\n{text}"
    try:
        r = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(r.text)
    except:
        return {}

# ================== CORE ==================
def handle_message(user_msg=""):
    state = conversation_state
    stage = state.current_stage()

    # Greeting
    if stage == "GREETING":
        state.next_stage()
        return STAGE_QUESTIONS["GREETING"]["message"]

    # Handle answer
    if user_msg and state.current_field:
        q = state.current_question
        parsed = smart_parse(user_msg, q["v"], q.get("options"))
        if parsed is not None:
            set_nested(state.data, q["field"], parsed)
            state.current_field = None
            state.current_question = None
        else:
            return "مش فاهمك قوي 🤔 ممكن توضحي أكتر؟"

    block = STAGE_QUESTIONS.get(stage)

    # Ask main questions
    if block and "questions" in block:
        for q in block["questions"]:
            if get_nested(state.data, q["field"]) is None:
                state.current_field = q["field"]
                state.current_question = q
                return q["q"]

    # Ask follow-up questions
    if block and "follow" in block:
        main_q = block["questions"][0]
        main_val = get_nested(state.data, main_q["field"])
        follow_qs = block["follow"].get(main_val, [])
        for fq in follow_qs:
            if get_nested(state.data, fq["field"]) is None:
                state.current_field = fq["field"]
                state.current_question = fq
                return fq["q"]

    # Extract symptoms after CURRENT_SYMPTOMS
    if stage == "CURRENT_SYMPTOMS":
        raw = state.data.get("symptoms", {}).get("raw", "")
        if raw and "structured" not in state.data["symptoms"]:
            state.data["symptoms"]["structured"] = extract_symptoms(raw)

    # Move to next stage
    state.next_stage()
    return handle_message()

# ================== RUN ==================
if __name__ == "__main__":
    print("🤖 مساعد القلب الذكي\n")
    msg = handle_message()
    print(msg)

    while True:
        user = input("أنت: ")
        if user.lower() in ["exit", "quit"]:
            break
        print("🤖", handle_message(user))
