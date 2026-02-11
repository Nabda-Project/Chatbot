import json
import os
import re
import unicodedata
import logging
from datetime import datetime
from dotenv import load_dotenv

# ==================== CONFIG ====================
load_dotenv()

# ==================== STAGES ====================
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
]

STAGE_QUESTIONS = {
    "GREETING": {
        "message": "مرحباً بك في مساعد القلب الذكي 👋\nسأسألك بعض الأسئلة الطبية البسيطة لمساعدة طبيب القلب.\nهل أنت مستعد؟ (أكتب أي شيء للمتابعة)"
    },
    
    "BASIC_INFO": {
        "questions": [
            {
                "field": "basic_info.age",
                "q": "كم عمرك؟",
                "v": "number",
                "min": 1,
                "max": 120
            },
            {
                "field": "basic_info.gender",
                "q": "ما هو جنسك؟ (ذكر/أنثى)",
                "v": "choice",
                "options": {
                    "ذكر": "male",
                    "أنثى": "female"
                }
            },
            {
                "field": "basic_info.weight",
                "q": "ما هو وزنك بالكيلوجرام؟",
                "v": "number",
                "min": 20,
                "max": 300
            },
            {
                "field": "basic_info.height",
                "q": "ما هو طولك بالسنتيمتر؟",
                "v": "number",
                "min": 100,
                "max": 250
            }
        ]
    },
    
    "SMOKING": {
        "questions": [
            {
                "field": "lifestyle.smoking",
                "q": "هل تدخن؟ حدثني عن عادة التدخين لديك (نوع وكمية وسنوات)",
                "v": "text"
            }
        ]
    },
    
    "PHYSICAL_ACTIVITY": {
        "questions": [
            {
                "field": "lifestyle.physical_activity",
                "q": "كم مرة تمارس الرياضة أسبوعياً؟ وما نوعها؟",
                "v": "text"
            }
        ]
    },
    
    "DIET": {
        "questions": [
            {
                "field": "lifestyle.diet",
                "q": "صف لي نظامك الغذائي في يوم عادي",
                "v": "text"
            }
        ]
    },
    
    "SLEEP": {
        "questions": [
            {
                "field": "lifestyle.sleep",
                "q": "كم ساعة تنام في اليوم؟ وهل نومك منتظم؟",
                "v": "text"
            }
        ]
    },
    
    "STRESS": {
        "questions": [
            {
                "field": "lifestyle.stress",
                "q": "كيف تصف مستوى التوتر في حياتك اليومية؟",
                "v": "text"
            }
        ]
    },
    
    "CHRONIC_DISEASES": {
        "questions": [
            {
                "field": "medical_history.chronic_diseases",
                "q": "هل تعاني من أي أمراض مزمنة مثل السكر أو الضغط أو الكوليسترول؟",
                "v": "text"
            }
        ]
    },
    
    "MEDICATIONS": {
        "questions": [
            {
                "field": "medical_history.current_medications",
                "q": "هل تتناول أي أدوية بانتظام؟ وما هي؟",
                "v": "text"
            }
        ]
    },
    
    "FAMILY_HISTORY": {
        "questions": [
            {
                "field": "medical_history.family_history",
                "q": "هل أحد من عائلتك (أب، أم، أخوة) عانى من أمراض القلب؟",
                "v": "text"
            }
        ]
    },
    
    "PREVIOUS_HEART_ISSUES": {
        "questions": [
            {
                "field": "medical_history.previous_heart_issues",
                "q": "هل سبق وأن عانيت من مشاكل في القلب أو قمت بفحوصات للقلب؟",
                "v": "text"
            }
        ]
    },
    
    "CURRENT_SYMPTOMS": {
        "questions": [
            {
                "field": "symptoms.description",
                "q": "هل تشعر بأي أعراض حالياً؟ مثل ألم في الصدر، ضيق تنفس، خفقان، دوخة... احكي لي براحتك",
                "v": "text"
            }
        ]
    },
    
    "FINAL_QUESTIONS": {
        "questions": [
            {
                "field": "medical_history.other_concerns",
                "q": "هل هناك أي شيء آخر تود إضافته أو أي سؤال للطبيب؟",
                "v": "text"
            }
        ]
    }
}

# ==================== STATE ====================
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
                "smoking": "",
                "physical_activity": "",
                "diet": "",
                "sleep": "",
                "stress": "",
            },
            "medical_history": {
                "chronic_diseases": "",
                "current_medications": "",
                "family_history": "",
                "previous_heart_issues": "",
                "other_concerns": ""
            },
            "symptoms": {
                "description": ""
            },
            "conversation_history": [],
        }

    def current_stage(self):
        if self.stage_index < len(STAGES):
            return STAGES[self.stage_index]
        return None

    def next_stage(self):
        self.stage_index += 1
        self.current_field = None
        self.current_question = None
        self.retry_count = 0

conversation_state = ConversationState()

# ==================== PARSERS ====================
def normalize_arabic(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[ًٌٍَُِْـ]", "", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("اً", "ا")
    text = text.replace("ة", "ه").replace("ى", "ي")
    return text.lower().strip()

def extract_number(text):
    nums = re.findall(r"\d+\.?\d*", text)
    if nums:
        return float(nums[0])
    return None

def extract_gender(text):
    normalized = normalize_arabic(text)
    male_indicators = ["ذكر", "راجل", "ولد", "رجل"]
    female_indicators = ["انثى", "أنثى", "ست", "بنت", "انثي"]
    
    for word in male_indicators:
        if normalize_arabic(word) in normalized:
            return "male"
    for word in female_indicators:
        if normalize_arabic(word) in normalized:
            return "female"
    return None

def smart_parse(text, qtype, options=None):
    if not text:
        return None
    normalized = normalize_arabic(text)
    
    if qtype == "number":
        return extract_number(text)
    elif qtype == "choice" and options:
        for key, value in options.items():
            if normalize_arabic(key) in normalized:
                return value
        if "male" in options.values() and "female" in options.values():
            gender = extract_gender(text)
            if gender:
                return gender
    elif qtype == "text":
        return text.strip()
    return None

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

# ==================== MAIN LOGIC ====================
def save_conversation():
    filename = f"patient_data/patient_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("patient_data", exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(conversation_state.data, f, ensure_ascii=False, indent=2)
    return filename

def get_next_question():
    state = conversation_state
    stage = state.current_stage()
    
    if stage is None:
        return None
    
    # Handle GREETING
    if stage == "GREETING":
        return STAGE_QUESTIONS["GREETING"]["message"]
    
    # If we're in the middle of a question, wait for answer
    if state.current_field:
        return None
    
    # Get questions for current stage
    block = STAGE_QUESTIONS.get(stage)
    if block and "questions" in block:
        for q in block["questions"]:
            if get_nested(state.data, q["field"]) is None or get_nested(state.data, q["field"]) == "":
                state.current_field = q["field"]
                state.current_question = q
                return q["q"]
    
    # No more questions in this stage - move to next
    state.next_stage()
    
    # Recursively get next question
    return get_next_question()

def generate_summary():
    """Generate a simple summary"""
    state = conversation_state
    data = state.data
    
    summary = f"""
📋 ملخص معلومات المريض:

👤 المعلومات الأساسية:
• العمر: {data['basic_info'].get('age', 'غير محدد')}
• الجنس: {data['basic_info'].get('gender', 'غير محدد')}
• الوزن: {data['basic_info'].get('weight', 'غير محدد')} كجم
• الطول: {data['basic_info'].get('height', 'غير محدد')} سم

🚬 التدخين: {data['lifestyle'].get('smoking', 'لم يذكر')}
🏃 النشاط البدني: {data['lifestyle'].get('physical_activity', 'لم يذكر')}
🥗 النظام الغذائي: {data['lifestyle'].get('diet', 'لم يذكر')}
😴 النوم: {data['lifestyle'].get('sleep', 'لم يذكر')}
😰 التوتر: {data['lifestyle'].get('stress', 'لم يذكر')}

💊 الأمراض المزمنة: {data['medical_history'].get('chronic_diseases', 'لا يوجد')}
💉 الأدوية: {data['medical_history'].get('current_medications', 'لا يوجد')}
👪 التاريخ العائلي: {data['medical_history'].get('family_history', 'لم يذكر')}
❤️ مشاكل القلب السابقة: {data['medical_history'].get('previous_heart_issues', 'لم يذكر')}

🤒 الأعراض الحالية: {data['symptoms'].get('description', 'لا توجد')}

ℹ️ ملاحظات إضافية: {data['medical_history'].get('other_concerns', 'لا يوجد')}
"""
    return summary

def handle_message(user_msg=""):
    state = conversation_state
    
    # Save user message
    if user_msg:
        state.data["conversation_history"].append({
            "role": "user",
            "content": user_msg,
            "timestamp": datetime.now().isoformat()
        })
    
    # Handle current question
    if state.current_field and state.current_question:
        q = state.current_question
        parsed = smart_parse(user_msg, q["v"], q.get("options"))
        
        if parsed is not None:
            # Validate numbers
            if q["v"] == "number":
                if "min" in q and parsed < q["min"]:
                    return f"❌ القيمة صغيرة جداً. {q['q']}"
                if "max" in q and parsed > q["max"]:
                    return f"❌ القيمة كبيرة جداً. {q['q']}"
            
            set_nested(state.data, q["field"], parsed)
            state.current_field = None
            state.current_question = None
            state.retry_count = 0
        else:
            state.retry_count += 1
            if state.retry_count >= state.max_retries:
                set_nested(state.data, q["field"], user_msg)
                state.current_field = None
                state.current_question = None
                state.retry_count = 0
                return "✅ تمام، هسجل الرد زي ما هو."
            return f"🤔 مش فاهمك قوي. {q['q']}"
    
    # Handle greeting stage
    if state.current_stage() == "GREETING" and user_msg:
        state.next_stage()
    
    # Get next question
    next_q = get_next_question()
    
    if next_q is None:
        # Conversation complete
        summary = generate_summary()
        filename = save_conversation()
        return f"{summary}\n\n✅ شكراً لمشاركتك! تم حفظ المحادثة في {filename}"
    
    # Save bot message
    state.data["conversation_history"].append({
        "role": "bot",
        "content": next_q,
        "timestamp": datetime.now().isoformat()
    })
    
    return next_q

# ==================== MAIN ====================
def main():
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🤖 مساعد القلب الذكي - Smart Heart Assistant")
    print("=" * 60)
    print("اكتب 'خروج' للإنهاء، 'حفظ' لحفظ المحادثة\n")
    
    # Start conversation
    response = handle_message()
    print(f"🤖: {response}")
    
    while True:
        user_input = input("👤: ").strip()
        
        if user_input.lower() in ['خروج', 'exit', 'quit']:
            filename = save_conversation()
            print(f"🤖: مع السلامة! تم حفظ المحادثة في {filename} 👋")
            break
        
        if user_input.lower() == 'حفظ':
            filename = save_conversation()
            print(f"🤖: تم حفظ المحادثة في {filename} ✅")
            continue
        
        if not user_input:
            continue
        
        response = handle_message(user_input)
        print(f"🤖: {response}")

if __name__ == "__main__":
    main()