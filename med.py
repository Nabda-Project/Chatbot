import json
import os
import re
import unicodedata
import logging
from datetime import datetime

# ==================== CONFIG & STAGES ====================
STAGES = [
    "GREETING",
    "BASIC_INFO",
    "SMOKING",
    "PHYSICAL_ACTIVITY",
    "MEDICAL_HISTORY",
    "FAMILY_HISTORY",
    "CURRENT_SYMPTOMS",
]

STAGE_QUESTIONS = {
    "GREETING": {
        "message": "مرحباً بك في مساعد القلب الذكي 🫀\n\nأنت مستعد؟ (أكتب أي شيء للبدء)"
    },
    "BASIC_INFO": {
        "questions": [
            {"field": "basic_info.gender", "q": "ما هو جنسك؟ (ذكر/أنثى)", "v": "choice", "options": {"ذكر": "male", "أنثى": "female"}},
            {"field": "basic_info.age", "q": "كم عمرك؟", "v": "number", "min": 1, "max": 110},
            {"field": "basic_info.weight", "q": "ما هو وزنك بالكيلوجرام؟", "v": "number", "min": 30, "max": 250},
            {"field": "basic_info.height", "q": "ما هو طولك بالسنتيمتر؟", "v": "number", "min": 100, "max": 220}
        ]
    },
    "SMOKING": {
        "questions": [
            {"field": "lifestyle.smoking", "q": "بالنسبة للتدخين، هل أنت (مدخن حالي / مدخن سابق / غير مدخن)؟", "v": "text"}
        ]
    },
    "PHYSICAL_ACTIVITY": {
        "questions": [
            {"field": "lifestyle.physical_activity", "q": "هل تمارس رياضة المشي أو أي نشاط بدني بانتظام؟ وكم مرة أسبوعياً؟", "v": "text"}
        ]
    },
    "MEDICAL_HISTORY": {
        "questions": [
            {"field": "medical_history.chronic", "q": "هل تعاني من سكري، ضغط مرتفع، أو كوليسترول؟ (اذكر المصاب به أو اكتب لا يوجد)", "v": "text"},
            {"field": "medical_history.meds", "q": "ما هي الأدوية التي تتناولها بانتظام؟", "v": "text"}
        ]
    },
    "FAMILY_HISTORY": {
        "questions": [
            {"field": "medical_history.family", "q": "هل هناك تاريخ عائلي لأمراض القلب في سن مبكرة؟", "v": "text"}
        ]
    },
    "CURRENT_SYMPTOMS": {
        "questions": [
            {"field": "symptoms.desc", "q": "أخيراً، هل تشعر بأي (نهجان، ألم في الصدر، خفقان، أو تورم بالقدم)؟", "v": "text"}
        ]
    }
}

# ==================== HELPERS ====================
def normalize_arabic(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[ًٌٍَُِْـ]", "", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return text.lower().strip()

def smart_parse(text, qtype, options=None):
    if not text: return None
    normalized = normalize_arabic(text)
    if qtype == "number":
        nums = re.findall(r"\d+\.?\d*", text)
        return float(nums[0]) if nums else None
    elif qtype == "choice" and options:
        for key, value in options.items():
            if normalize_arabic(key) in normalized: return value
    return text.strip()

# ==================== MEDICAL LOGIC ====================
def generate_medical_advice(data):
    advices = []
    # BMI Analysis
    try:
        w = float(data['basic_info'].get('weight', 0))
        h = float(data['basic_info'].get('height', 1)) / 100
        bmi = w / (h**2)
        if bmi > 25:
            advices.append("- 🥗 وزنك أعلى من المعدل الطبيعي؛ إنقاص الوزن يقلل العبء على عضلة القلب.")
    except: pass

    # Smoking
    smoking = normalize_arabic(str(data['lifestyle'].get('smoking', "")))
    if "حالى" in smoking or "نعم" in smoking or "بدخن" in smoking:
        advices.append("- 🚭 التدخين يسبب ضيق الشرايين؛ التوقف عنه هو أهم خطوة لحماية قلبك.")

    # Symptoms check
    symptoms = normalize_arabic(str(data['symptoms'].get('desc', "")))
    if any(word in symptoms for word in ["الم", "صدر", "نهجان", "ضيق"]):
        advices.append("- ⚠️ الأعراض التي ذكرتها تستوجب فحصاً دقيقاً (رسم قلب أو إيكو) تحت إشراف طبيب.")

    return "\n💡 **إرشادات مخصصة لحالتك:**\n" + ("\n".join(advices) if advices else "- استمر على نمط حياتك الصحي!")

def generate_general_tips():
    return """
🌟 **نصائح عامة لصحة القلب:**
• **قلل الملح:** تجنب الملح الزائد والمخللات لضبط ضغط الدم.
• **المشي:** حاول المشي لمدة 30 دقيقة يومياً بمعدل 5 أيام أسبوعياً.
• **الماء:** اشرب كميات كافية من الماء (2-3 لتر) يومياً.
• **النوم:** احصل على 7-8 ساعات من النوم المريح لدعم صحة الشرايين.
"""

# ==================== STATE MANAGEMENT ====================
class ConversationState:
    def __init__(self):
        self.stage_index = 0
        self.current_field = None
        self.current_question = None
        self.data = {"basic_info": {}, "lifestyle": {}, "medical_history": {}, "symptoms": {}, "history": []}

    def next_stage(self):
        self.stage_index += 1
        self.current_field = None

conversation_state = ConversationState()

def handle_message(user_msg=""):
    state = conversation_state
    
    # Process Answer
    if state.current_field:
        q = state.current_question
        parsed = smart_parse(user_msg, q["v"], q.get("options"))
        
        if parsed is not None:
            # Simple validation for numbers
            if q["v"] == "number" and ("min" in q and parsed < q["min"] or "max" in q and parsed > q["max"]):
                return f"❌ القيمة غير منطقية، يرجى إدخال رقم صحيح. {q['q']}"
            
            keys = q["field"].split(".")
            state.data[keys[0]][keys[1]] = parsed
            state.current_field = None
        else:
            return f"🤔 عذراً، لم أفهم الرد. {q['q']}"

    # Move to next question/stage
    while state.stage_index < len(STAGES):
        stage_name = STAGES[state.stage_index]
        if stage_name == "GREETING" and not state.data["history"]:
            state.data["history"].append("start")
            return STAGE_QUESTIONS["GREETING"]["message"]
        
        if stage_name == "GREETING": 
            state.next_stage()
            continue

        block = STAGE_QUESTIONS.get(stage_name)
        for q in block["questions"]:
            keys = q["field"].split(".")
            if state.data[keys[0]].get(keys[1]) is None:
                state.current_field = q["field"]
                state.current_question = q
                return q["q"]
        
        state.next_stage()

    # Final Summary & Advice
    advice = generate_medical_advice(state.data)
    tips = generate_general_tips()
    
    # Save Data
    os.makedirs("patient_records", exist_ok=True)
    filename = f"patient_records/report_{datetime.now().strftime('%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(state.data, f, ensure_ascii=False, indent=2)

    return f"📋 **انتهينا! إليك ملخصك الطبي:**\n{advice}\n{tips}\n\n⚠️ **تنبيه:** هذه المعلومات استرشادية ولا تغني عن زيارة الطبيب. في حال وجود ألم شديد بالصدر توجه للطوارئ فوراً.\n✅ تم حفظ تقريرك في النظام."

# ==================== RUNNER ====================
if __name__ == "__main__":
    print("--- بوت مساعد القلب الطبي يبدأ الآن ---")
    print(handle_message()) # الترحيب
    while conversation_state.stage_index < len(STAGES) or conversation_state.current_field:
        user_input = input("المريض: ")
        print(f"البوت: {handle_message(user_input)}")