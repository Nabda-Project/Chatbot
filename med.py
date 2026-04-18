"""
med.py  –  Cardiac intake chatbot with per-symptom question loops.
"""

import re
import requests

# ==================== CONFIG ====================
AI_URL  = "http://med-report-api-alb-124948947.us-east-1.elb.amazonaws.com/generate"
API_KEY = "REMOVED"

STAGES = ["DEMOGRAPHICS", "HISTORY", "SYMPTOM_SELECTION", "SYMPTOM_LOOP", "RED_FLAG_SCREENING", "FREE_TEXT"]

SYMPTOM_LABELS = {
    "خفقان / تسارع في ضربات القلب":   "palpitations",
    "عدم انتظام / إحساس بتوقف لحظي":      "irregular",
    "ألم أو ضغط أو ضيق في الصدر":     "chest_pain",
    "ألم في منطقة القلب تحديداً":     "heart_pain",
    "نغزات / وخز / طعنات":          "stabs",
    "ضيق أو صعوبة في التنفس":        "dyspnea",
    "دوخة / دوار / عدم اتزان":      "dizziness",
    "إغماء أو فقدان وعي":       "fainting",
    "تعب / إرهاق / ضعف عام":        "fatigue",
    "تعرق (خصوصاً عرق بارد)":       "sweating",
    "غثيان / قيء":         "nausea",
    "ألم ينتشر إلى الذراع أو الكتف أو اليد اليسرى":  "arm_radiation",
    "تنميل أو خدر في الأطراف":       "tingling",
    "رجفة / ارتعاش":         "tremor",
    "برودة في الأطراف": "cold_extremities",
    "عرض آخر":          "other",
}

CODE_TO_LABEL = {v: k for k, v in SYMPTOM_LABELS.items()}


# ==================== PER-SYMPTOM QUESTION BANKS ====================

def _build_common_questions(code: str, label: str) -> list:
    return [
        {
            "field":   f"symptom_detail.{code}.severity",
            "q":       f"ما شدة [{label}] عندما تحدث؟",
            "v":       "choice",
            "options": {
                "بسيطة / خفيفة": "mild",
                "متوسطة / مزعجة": "moderate",
                "شديدة / قوية":   "severe",
                "لا أحتمل":       "unbearable",
            },
        },
        {
            "field":   f"symptom_detail.{code}.duration_general",
            "q":       f"منذ متى وأنت تعاني من [{label}]؟",
            "v":       "choice",
            "options": {
                "بدأت اليوم":   "today",
                "منذ أيام":     "days",
                "منذ أسابيع":   "weeks",
                "منذ شهور":     "months",
                "منذ سنوات":    "years",
                "منذ الطفولة":  "since_childhood",
            },
        },
        {
            "field":   f"symptom_detail.{code}.pattern",
            "q":       f"كيف يأتي [{label}]؟",
            "v":       "choice",
            "options": {
                "مستمر طوال الوقت / موجود الآن": "continuous",
                "نوبات تأتي وتذهب":              "episodic",
                "نوبة واحدة فقط حتى الآن":       "single",
            },
        },
        {
            "field":   f"symptom_detail.{code}.episode_duration",
            "q":       f"كم تستمر نوبة [{label}] عادةً؟",
            "v":       "choice",
            "options": {
                "ثوانٍ":                   "seconds",
                "دقائق قليلة (< 5 دقائق)": "minutes_short",
                "من 5 إلى 30 دقيقة":       "minutes_long",
                "ساعات":                   "hours",
                "مستمر لا يزول":           "continuous",
            },
            "depends_on": {"field": f"symptom_detail.{code}.pattern", "equals": "episodic"},
        },
        {
            "field":   f"symptom_detail.{code}.triggers",
            "q":       f"متى يحدث [{label}] عادةً؟ (اختر كل ما ينطبق)",
            "v":       "multi_choice",
            "options": {
                "فجأة بدون سبب واضح":           "sudden",
                "في الليل":                     "night",
                "أثناء النوم (يوقظني)":          "sleep",
                "عند الاستيقاظ":                "waking",
                "عند المجهود / الرياضة / الدرج": "exertion",
                "عند الراحة":                   "rest",
                "بعد الأكل":                    "after_meals",
                "عند التوتر أو الغضب":          "emotional",
                "بعد القهوة / الشاي":           "after_caffeine",
                "بعد التدخين":                  "after_smoking",
                "مع ملامسة الماء البارد":        "cold_water",
                "مع الدورة الشهرية":             "menstruation",
            },
        },
        {
            "field":   f"symptom_detail.{code}.relieving_factors",
            "q":       f"ما الذي يخفف [{label}]؟ (اختر كل ما ينطبق)",
            "v":       "multi_choice",
            "options": {
                "الراحة":              "rest",
                "الدواء":              "medication",
                "تغيير الوضعية":       "position_change",
                "التنفس العميق":       "deep_breathing",
                "لا شيء يخففه":        "nothing",
                "يزول من تلقاء نفسه":  "self_resolves",
            },
        },
    ]


def _get_extras_for_code(code: str) -> list:
    extras = {
        "chest_pain": [
            {
                "field": f"symptom_detail.{code}.radiation",
                "q": "هل ينتشر ألم الصدر إلى مناطق أخرى؟ (اختر كل ما ينطبق)",
                "v": "multi_choice",
                "options": {
                    "لا ينتشر": "no_radiation", "الذراع / الكتف / اليد اليسرى": "left_arm",
                    "الذراع / الكتف / اليد اليمنى": "right_arm", "الظهر / بين الكتفين": "back",
                    "الرقبة": "neck", "الفك أو الأسنان": "jaw", "أعلى البطن": "upper_abdomen",
                },
            },
            {
                "field": f"symptom_detail.{code}.exertional",
                "q": "هل يزداد ألم الصدر مع المجهود ويخف مع الراحة؟",
                "v": "choice",
                "options": {"نعم": "yes", "لا": "no", "لست متأكداً": "not_sure"},
            },
            {
                "field": f"symptom_detail.{code}.quality",
                "q": "كيف تصف طبيعة ألم الصدر؟",
                "v": "choice",
                "options": {
                    "ضغط / ثقل": "pressure", "حرقة / حموضة": "burning",
                    "طعنة / وخز حاد": "stabbing", "شد / تشنج": "tightness",
                    "إحساس غريب يصعب وصفه": "vague",
                },
            },
        ],
        "heart_pain": [
            {
                "field": f"symptom_detail.{code}.radiation",
                "q": "هل ينتشر ألم منطقة القلب إلى مناطق أخرى؟ (اختر كل ما ينطبق)",
                "v": "multi_choice",
                "options": {
                    "لا ينتشر": "no_radiation", "الذراع / الكتف / اليد اليسرى": "left_arm",
                    "الرقبة": "neck", "الفك": "jaw", "الظهر": "back",
                },
            },
            {
                "field": f"symptom_detail.{code}.exertional",
                "q": "هل يزداد ألم منطقة القلب مع المجهود ويخف مع الراحة؟",
                "v": "choice",
                "options": {"نعم": "yes", "لا": "no", "لست متأكداً": "not_sure"},
            },
        ],
        "stabs": [
            {
                "field": f"symptom_detail.{code}.location",
                "q": "أين تقع النغزات / الوخز بالضبط؟",
                "v": "choice",
                "options": {
                    "منطقة القلب (اليسار)": "left_precordial", "منتصف الصدر": "central",
                    "اليمين": "right", "عشوائية تتنقل": "moving",
                },
            },
        ],
        "palpitations": [
            {
                "field": f"symptom_detail.{code}.rate_feel",
                "q": "كيف تشعر بضربات القلب أثناء الخفقان؟",
                "v": "choice",
                "options": {
                    "سريعة جداً ومنتظمة": "fast_regular", "سريعة وغير منتظمة": "fast_irregular",
                    "قوية وأشعر بها في صدري": "forceful", "أشعر بها في رقبتي": "neck_pounding",
                },
            },
        ],
        "irregular": [
            {
                "field": f"symptom_detail.{code}.skip_or_extra",
                "q": "ما أقرب وصف لما تشعر به؟",
                "v": "choice",
                "options": {
                    "إحساس بتوقف لحظي ثم عودة": "pause_then_thump",
                    "ضربة إضافية خارج النظام": "extra_beat",
                    "اضطراب كامل في الإيقاع": "full_irregular",
                    "تسارع مفاجئ ثم عودة طبيعية": "svt_like",
                },
            },
        ],
        "dyspnea": [
            {
                "field": f"symptom_detail.{code}.orthopnea",
                "q": "هل يزداد ضيق التنفس عند الاستلقاء؟",
                "v": "choice",
                "options": {"نعم، أحتاج وسائد إضافية": "yes_orthopnea", "لا": "no", "لست متأكداً": "not_sure"},
            },
            {
                "field": f"symptom_detail.{code}.exertion_level",
                "q": "ما مستوى الجهد الذي يسبب ضيق التنفس؟",
                "v": "choice",
                "options": {
                    "عند المشي السريع / صعود الدرج": "moderate_exertion",
                    "عند أدنى مجهود (المشي البطيء)": "minimal_exertion",
                    "عند الراحة التامة": "at_rest",
                    "لا يرتبط بالمجهود": "unrelated",
                },
            },
        ],
        "dizziness": [
            {
                "field": f"symptom_detail.{code}.type",
                "q": "كيف تصف الدوخة؟",
                "v": "choice",
                "options": {
                    "إحساس بالدوران (كأن الأرض تدور)": "vertigo",
                    "ضبابية / عدم وضوح": "lightheaded",
                    "إحساس بالإغماء الوشيك": "presyncope",
                    "عدم اتزان عند المشي": "imbalance",
                },
            },
        ],
        "fainting": [
            {
                "field": f"symptom_detail.{code}.full_loss",
                "q": "هل فقدت الوعي تماماً أم كاد فقط؟",
                "v": "choice",
                "options": {"فقدت الوعي تماماً": "complete_loss", "كاد يحدث / اسودّ أمامي": "near_syncope"},
            },
            {
                "field": f"symptom_detail.{code}.recovery_time",
                "q": "كم استغرق التعافي؟",
                "v": "choice",
                "options": {"ثوانٍ (< 1 دقيقة)": "seconds", "دقيقة أو أكثر": "minutes", "استدعى التدخل": "required_intervention"},
            },
        ],
        "arm_radiation": [
            {
                "field": f"symptom_detail.{code}.side",
                "q": "الانتشار في أي جانب؟",
                "v": "choice",
                "options": {"اليسار فقط": "left_only", "اليمين فقط": "right_only", "الجانبين": "both"},
            },
        ],
        "fatigue": [
            {
                "field": f"symptom_detail.{code}.exertional_change",
                "q": "هل يزداد الإرهاق مع أي مجهود؟",
                "v": "choice",
                "options": {"نعم بشكل واضح": "yes", "قليلاً": "slightly", "لا": "no"},
            },
        ],
    }
    return extras.get(code, [])


def _build_known_symptom_questions(code: str) -> list:
    label = CODE_TO_LABEL.get(code, code)
    return _build_common_questions(code, label) + _get_extras_for_code(code)


def _build_other_symptom_questions(code: str, label: str) -> list:
    return _build_common_questions(code, label)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  FIX #1: .values() بدل المفاتيح العربية                         ║
# ║  قبل كده كان بيمشي على "خفقان / تسارع..." بدل "palpitations"   ║
# ║  فكان مبيلاقيش الكود لما المستخدم يختار من القائمة            ║
# ╚══════════════════════════════════════════════════════════════════╝
SYMPTOM_QUESTION_BANKS: dict = {
    code: _build_known_symptom_questions(code)
    for code in SYMPTOM_LABELS.values() if code != "other"
}


# ==================== STAGE QUESTIONS ====================

STAGE_QUESTIONS = {
    "DEMOGRAPHICS": [
        # ╔═══════════════════════════════════════════╗
        # ║  FIX #2: شيلت سؤال "تصفها لمن" بالكامل   ║
        # ╚═══════════════════════════════════════════╝
        {
            "field": "demographics.age", "q": "كم العمر بالسنوات؟", "v": "number", "min": 1, "max": 110,
        },
        {
            "field": "demographics.sex", "q": "الجنس؟", "v": "choice",
            "options": {"ذكر": "male", "أنثى": "female"},
        },
        {
            "field": "demographics.pregnancy",
            "q": "هل أنتِ حامل حالياً أو في فترة ما بعد الولادة (خلال 6 أسابيع)؟",
            "v": "choice",
            "options": {"حامل": "pregnant", "ما بعد الولادة": "postpartum", "لا": "no"},
            # FIX #2: شلت الشرط ده لأن سؤال "تصفها لمن" اتشال
            "depends_on": {"field": "demographics.sex", "equals": "female"},
        },
        {
            "field": "demographics.weight_kg", "q": "ما هو الوزن بالكيلوجرام؟", "v": "number", "min": 3, "max": 300,
        },
        {
            "field": "demographics.height_cm", "q": "ما هو الطول بالسنتيمتر؟", "v": "number", "min": 50, "max": 250,
        },
    ],
    "HISTORY": [
        {
            "field": "history.known_cardiac", "q": "هل سبق تشخيصك بمرض في القلب؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا يوجد تشخيص سابق": "none", "ارتخاء في الصمام الميترالي": "mvp",
                "ثقب في القلب / عيب خلقي": "hole_congenital", "تضخم في القلب": "enlarged",
                "عدم انتظام في ضربات القلب / خوارج انقباض": "arrhythmia",
                "جلطة أو ذبحة صدرية أو سكتة سابقة": "prior_mi_stroke",
                "قسطرة / دعامة / عملية قلب": "catheter_stent", "تشخيص آخر": "other",
            },
        },
        {
            "field": "history.prior_workup", "q": "هل قمت سابقاً بأي من الفحوصات التالية للقلب؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا شيء": "none", "رسم قلب (ECG)": "ecg", "أشعة تلفزيونية على القلب (إيكو)": "echo",
                "هولتر (رسم قلب لمدة 24 ساعة)": "holter", "رسم قلب بالمجهود": "stress", "قسطرة تشخيصية": "cath",
            },
        },
        {
            "field": "history.chronic_conditions", "q": "هل تعاني من أي من الحالات التالية؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا شيء": "none", "ارتفاع ضغط الدم": "htn", "انخفاض ضغط الدم": "low_bp",
                "السكري": "dm", "ارتفاع الكوليسترول": "chol", "اضطراب في الغدة الدرقية": "thyroid",
                "فقر دم / أنيميا": "anemia", "القولون العصبي": "ibs", "ارتجاع / حموضة / جرثومة المعدة": "reflux",
            },
        },
        {
            "field": "history.medications",
            "q": 'ما الأدوية التي تتناولها حالياً بانتظام؟ (اذكر الاسم والجرعة إن أمكن، أو اكتب "لا شيء")',
            "v": "text",
        },
        {
            "field": "history.med_adherence", "q": "هل توقفت عن تناول أي من أدويتك مؤخراً؟",
            "v": "choice",
            "options": {"لا، ملتزم بالدواء": "compliant", "نعم، توقفت منذ أيام أو أسابيع": "recently_stopped", "أتناول جرعات غير منتظمة": "irregular"},
            "depends_on": {"field": "history.medications", "not_text_in": ["لا شيء", "لا", "none", "لا يوجد"]},
        },
        {
            "field": "history.family_history", "q": "هل يعاني أحد الأقارب من الدرجة الأولى من مرض في القلب قبل سن 55؟",
            "v": "choice", "options": {"نعم": "yes", "لا": "no", "لا أعرف": "unknown"},
        },
        {
            "field": "history.lifestyle", "q": "هل ينطبق عليك أي من التالي؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا شيء": "none", "أدخن حالياً": "smoker", "مدخن سابق وتركت": "ex_smoker",
                "أتناول كمية كبيرة من القهوة أو الشاي (أكثر من 3 أكواب يومياً)": "heavy_caffeine",
                "أمارس الرياضة بانتظام": "gym", "أتناول منشطات أو هرمونات": "supplements",
            },
        },
    ],
    "SYMPTOM_SELECTION": [
        {
            "field": "symptom_selection.chosen", "q": "ما الأعراض التي تشعر بها؟ (اختر كل ما ينطبق عليك)",
            "v": "multi_choice", "options": SYMPTOM_LABELS,
        },
    ],
    "RED_FLAG_SCREENING": [
        {
            "field": "red_flags.exertional_chest", "q": "هل يوجد ألم في الصدر يزداد مع المجهود ويخف مع الراحة؟",
            "v": "choice", "options": {"نعم": "yes", "لا": "no", "لست متأكداً": "not_sure"},
            "depends_on": {"field": "symptom_selection.chosen", "not_contains_any": ["chest_pain", "heart_pain"]},
        },
        {
            "field": "red_flags.syncope_exertion", "q": "هل سبق أن أُغمي عليك أثناء الرياضة أو المجهود الشديد؟",
            "v": "choice", "options": {"نعم": "yes", "لا": "no"},
        },
    ],
    "FREE_TEXT": [
        {
            "field": "free_text.additional",
            "q": 'هل هناك أي شيء آخر تود إضافته عن حالتك؟ (إذا لا، اكتب "لا")',
            "v": "text",
        },
    ],
}

_VALID_CODES: dict = {}
for _stage_qs in STAGE_QUESTIONS.values():
    for _q in _stage_qs:
        if "options" in _q:
            _VALID_CODES[_q["field"]] = set(_q["options"].values())
for _code, _qs in SYMPTOM_QUESTION_BANKS.items():
    for _q in _qs:
        if "options" in _q:
            _VALID_CODES[_q["field"]] = set(_q["options"].values())


# ==================== PARSING ====================

def smart_parse(payload, q: dict):
    v     = q["v"]
    field = q["field"]

    if v == "number":
        if isinstance(payload, (int, float)):
            val = float(payload)
        else:
            nums = re.findall(r"\d+\.?\d*", str(payload))
            if not nums:
                return None
            val = float(nums[0])
        lo, hi = q.get("min"), q.get("max")
        if (lo is not None and val < lo) or (hi is not None and val > hi):
            return None
        return val

    if v == "choice":
        code  = str(payload).strip()
        valid = _VALID_CODES.get(field, set())
        if not valid and "options" in q:
            valid = set(q["options"].values())
        return code if code in valid else None

    if v == "multi_choice":
        if isinstance(payload, list):
            codes = [str(c).strip() for c in payload]
        else:
            codes = [c.strip() for c in str(payload).split(",") if c.strip()]
        valid = _VALID_CODES.get(field, set())
        if not valid and "options" in q:
            valid = set(q["options"].values())
        matched = [c for c in codes if c in valid]
        return matched if matched else None

    # text: يقبل أي نص عربي أو إنجليزي
    text = str(payload).strip()
    return text if text else None


# ==================== SERIALISATION ====================

def _serialize_question(q: dict, hint: str = None) -> dict:
    out = {"field": q["field"], "question_text": q["q"], "type": q["v"]}
    if "options" in q:
        out["options"] = [{"label": label, "value": code} for label, code in q["options"].items()]
    if hint:
        out["hint"] = hint
    return out


# ==================== DEPENDENCY ENGINE ====================

def _get_value(field_path: str, data: dict):
    parts = field_path.split(".")
    if len(parts) == 2:
        return data.get(parts[0], {}).get(parts[1])
    if len(parts) == 3:
        return data.get(parts[0], {}).get(parts[1], {}).get(parts[2])
    return None


def check_depends(dep, data: dict) -> bool:
    if not dep:
        return True
    if isinstance(dep, list):
        return all(check_depends(d, data) for d in dep)
    if not isinstance(dep, dict):
        return True
    field = dep.get("field")
    if not field:
        return True
    val = _get_value(field, data)
    if "equals" in dep:
        return val == dep["equals"]
    if "contains_any" in dep:
        targets = set(dep["contains_any"])
        if isinstance(val, list):
            return bool(set(val) & targets)
        return val in targets
    if "not_contains_any" in dep:
        targets = set(dep["not_contains_any"])
        if isinstance(val, list):
            return not bool(set(val) & targets)
        return val not in targets
    if "not_equals_any" in dep:
        return val not in dep["not_equals_any"]
    if "not_text_in" in dep:
        if val is None:
            return False
        lower = str(val).strip().lower()
        return not any(s.lower() in lower for s in dep["not_text_in"])
    return True


# ==================== STATE ====================

class ConversationState:
    def __init__(self):
        self.stage_index: int = 0
        self.current_question = None
        self.symptom_loop_state = None
        self.data = {
            "demographics": {},
            "history": {},
            "symptom_selection": {},
            "symptom_detail": {},
            "other_symptoms": [],
            "red_flags": {},
            "free_text": {},
            "narrative": "",
        }

states: dict = {}


# ==================== HELPERS ====================

def _store(q: dict, parsed, state: ConversationState):
    parts = q["field"].split(".")
    if len(parts) == 2:
        state.data[parts[0]][parts[1]] = parsed
    elif len(parts) == 3:
        state.data[parts[0]].setdefault(parts[1], {})
        state.data[parts[0]][parts[1]][parts[2]] = parsed
    if q["v"] == "text":
        state.data["narrative"] += str(parsed) + ". "

def _skip_q(q: dict, state: ConversationState):
    _store(q, "__skipped__", state)

def _is_answered(q: dict, state: ConversationState) -> bool:
    parts = q["field"].split(".")
    if len(parts) == 2:
        return state.data.get(parts[0], {}).get(parts[1]) is not None
    if len(parts) == 3:
        return state.data.get(parts[0], {}).get(parts[1], {}).get(parts[2]) is not None
    return False

def _other_count_question() -> dict:
    return {
        "field": "symptom_loop.other_count",
        "q": "كم عدد الأعراض الإضافية الأخرى التي تريد وصفها؟",
        "v": "number", "min": 1, "max": 10, "_transient": True,
    }

def _other_label_question(index: int) -> dict:
    return {
        "field": f"symptom_loop.other_label_{index}",
        "q": f"ما هو العرض الإضافي رقم {index + 1}؟ (اكتب وصفاً مختصراً بالعربي)",
        "v": "text", "_transient": True,
    }


# ==================== SYMPTOM LOOP ENGINE ====================

def _init_symptom_loop(state: ConversationState):
    chosen = state.data["symptom_selection"].get("chosen", [])
    if not isinstance(chosen, list):
        chosen = []

    has_other = "other" in chosen
    known     = [c for c in chosen if c != "other"]

    state.symptom_loop_state = {
        "phase":           "ask_other_count" if has_other else "ask_symptoms",
        "known_symptoms":  known,
        "other_count":     None,
        "other_labels":    [],
        "other_collected": 0,
        "combined_list":   list(known) if not has_other else [],
        "current_index":   0,
        "question_index":  0,
    }


def _get_questions_for(code: str, sls: dict) -> list:
    if code.startswith("other_"):
        idx = int(code.split("_")[1])
        label = sls["other_labels"][idx]
        return _build_other_symptom_questions(code, label)
    return SYMPTOM_QUESTION_BANKS.get(code, [])


def _get_label_for(code: str, sls: dict) -> str:
    if code.startswith("other_"):
        idx = int(code.split("_")[1])
        return sls["other_labels"][idx]
    return CODE_TO_LABEL.get(code, code)


def _next_symptom_question(state: ConversationState) -> dict | None:
    sls = state.symptom_loop_state

    # المرحلة 1: اسأل كام عرض آخر
    if sls["phase"] == "ask_other_count":
        return _other_count_question()

    # المرحلة 2: اجمع اسم كل عرض آخر
    if sls["phase"] == "ask_other_labels":
        if sls["other_collected"] < sls["other_count"]:
            return _other_label_question(sls["other_collected"])
        # جمعنا كل الأسماء → ابنِ القائمة الكاملة وانتقل
        other_codes = [f"other_{i}" for i in range(sls["other_count"])]
        sls["combined_list"] = sls["known_symptoms"] + other_codes
        sls["phase"] = "ask_symptoms"
        sls["current_index"] = 0
        sls["question_index"] = 0
        # يكمل للمرحلة 3 بدون return

    # المرحلة 3: لكل عرض اسأل نفس الأسئلة التفصيلية
    if sls["phase"] == "ask_symptoms":
        while sls["current_index"] < len(sls["combined_list"]):
            code = sls["combined_list"][sls["current_index"]]
            questions = _get_questions_for(code, sls)

            while sls["question_index"] < len(questions):
                q = questions[sls["question_index"]]

                if _is_answered(q, state):
                    sls["question_index"] += 1
                    continue

                dep = q.get("depends_on")
                if dep and not check_depends(dep, state.data):
                    _skip_q(q, state)
                    sls["question_index"] += 1
                    continue

                return q

            sls["current_index"] += 1
            sls["question_index"] = 0

    return None


def _handle_symptom_loop_answer(state: ConversationState, payload) -> dict | None:
    sls = state.symptom_loop_state

    if sls["phase"] == "ask_other_count":
        q = _other_count_question()
        parsed = smart_parse(payload, q)
        if parsed is None:
            return {"done": False, "question": _serialize_question(q, hint="⚠️ الرجاء إدخال رقم بين 1 و 10."), "reply": None}
        sls["other_count"] = int(parsed)
        sls["phase"] = "ask_other_labels"
        sls["other_collected"] = 0
        return None

    if sls["phase"] == "ask_other_labels":
        q = _other_label_question(sls["other_collected"])
        parsed = smart_parse(payload, q)
        if parsed is None:
            return {"done": False, "question": _serialize_question(q, hint="⚠️ الرجاء كتابة وصف للعرض."), "reply": None}
        sls["other_labels"].append(parsed)
        sls["other_collected"] += 1
        return None

    # سؤال تفصيلي لأي عرض
    code = sls["combined_list"][sls["current_index"]]
    questions = _get_questions_for(code, sls)
    q = questions[sls["question_index"]]
    parsed = smart_parse(payload, q)

    if parsed is None:
        if q["v"] == "number":
            hint = f"⚠️ القيمة خارج النطاق ({q.get('min')} – {q.get('max')})."
        elif q["v"] == "multi_choice":
            hint = "⚠️ الرجاء تحديد خيار واحد على الأقل من القائمة."
        else:
            hint = "⚠️ لم أتمكن من فهم إجابتك. الرجاء اختيار أحد الخيارات المذكورة."
        return {"done": False, "question": _serialize_question(q, hint=hint), "reply": None}

    _store(q, parsed, state)

    if q["field"].endswith(".severity"):
        label = _get_label_for(code, sls)
        sev_map = {"mild": "بسيطة", "moderate": "متوسطة", "severe": "شديدة", "unbearable": "لا تحتمل"}
        state.data["narrative"] += f"شدة {label}: {sev_map.get(parsed, parsed)}. "

    sls["question_index"] += 1
    return None


# ==================== STAGE-LEVEL QUESTION ITERATOR ====================

def _next_stage_question(state: ConversationState) -> dict | None:
    stage = STAGES[state.stage_index]
    if stage not in STAGE_QUESTIONS:
        return None
    for q in STAGE_QUESTIONS[stage]:
        if _is_answered(q, state):
            continue
        dep = q.get("depends_on")
        if dep and not check_depends(dep, state.data):
            _skip_q(q, state)
            continue
        return q
    return None


# ==================== AI ====================

def call_ai_api(narrative: str, data: dict) -> str:
    age = data["demographics"].get("age")
    sex = data["demographics"].get("sex")

    symptom_lines = []
    for code, detail in data.get("symptom_detail", {}).items():
        label = None
        for item in data.get("other_symptoms", []):
            if item["code"] == code:
                label = item["label"]
                break
        if label is None:
            label = CODE_TO_LABEL.get(code, code)

        sev = detail.get("severity", "غير محدد")
        dur = detail.get("duration_general", "غير محدد")
        symptom_lines.append(f"  - {label}: شدة={sev}, مدة={dur}")

        for key, val in detail.items():
            if key not in ("severity", "duration_general", "pattern", "episode_duration",
                           "triggers", "relieving_factors", "__skipped__"):
                if val != "__skipped__":
                    symptom_lines.append(f"    • {key}: {val}")
        triggers = detail.get("triggers")
        if triggers and isinstance(triggers, list):
            symptom_lines.append(f"    • محفزات: {', '.join(triggers)}")
        relieving = detail.get("relieving_factors")
        if relieving and isinstance(relieving, list):
            symptom_lines.append(f"    • عوامل تخفيف: {', '.join(relieving)}")

    symptoms_block = "\n".join(symptom_lines) if symptom_lines else "لم تُذكر أعراض"

    prompt = (
        "أنت طبيب قلب خبير.\n\n"
        f"العمر: {age}\nالجنس: {sex}\n\n"
        f"الأعراض التفصيلية:\n{symptoms_block}\n\n"
        f"ملاحظات إضافية:\n{narrative}\n\n"
        "اعطني:\n1. التشخيص المحتمل\n2. درجة الخطورة\n3. النصائح والخطوات المقترحة"
    )

    try:
        r = requests.post(AI_URL, headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
                          json={"text": prompt}, timeout=30)
        return r.json().get("result", "No result") if r.status_code == 200 else f"Error {r.status_code}"
    except Exception as exc:
        return f"Connection error: {exc}"


# ==================== MAIN ENGINE ====================

def handle_message(session_id: str, payload=None) -> dict:
    state = states.setdefault(session_id, ConversationState())
    in_symptom_loop = (STAGES[state.stage_index] == "SYMPTOM_LOOP")

    if state.current_question is not None and payload not in (None, "", [], {}):
        if in_symptom_loop:
            err = _handle_symptom_loop_answer(state, payload)
            if err is not None:
                return err
            state.current_question = None
        else:
            q = state.current_question
            parsed = smart_parse(payload, q)
            if parsed is None:
                if q["v"] == "number":
                    hint = f"⚠️ القيمة خارج النطاق ({q.get('min')} – {q.get('max')})."
                elif q["v"] == "multi_choice":
                    hint = "⚠️ الرجاء تحديد خيار واحد على الأقل."
                else:
                    hint = "⚠️ لم أتمكن من فهم إجابتك."
                return {"done": False, "question": _serialize_question(q, hint=hint), "reply": None}
            _store(q, parsed, state)
            state.current_question = None

    while state.stage_index < len(STAGES):
        stage = STAGES[state.stage_index]

        if stage == "SYMPTOM_LOOP":
            if state.symptom_loop_state is None:
                _init_symptom_loop(state)

            q = _next_symptom_question(state)
            if q is None:
                sls = state.symptom_loop_state
                if sls.get("other_labels"):
                    for i, label in enumerate(sls["other_labels"]):
                        state.data["other_symptoms"].append({"code": f"other_{i}", "label": label})
                state.stage_index += 1
                continue

            state.current_question = q
            return {"done": False, "question": _serialize_question(q), "reply": None}

        if stage not in STAGE_QUESTIONS:
            state.stage_index += 1
            continue

        q = _next_stage_question(state)
        if q is None:
            state.stage_index += 1
            continue

        state.current_question = q
        return {"done": False, "question": _serialize_question(q), "reply": None}

    report = call_ai_api(state.data["narrative"], state.data)
    return {"done": True, "question": None, "reply": f"📋 انتهينا من الأسئلة\n\n🧠 التحليل الطبي:\n{report}"}


def reset_session(session_id: str):
    states.pop(session_id, None)


# ==================== CLI test runner ====================
if __name__ == "__main__":
    sid = "cli_test"
    result = handle_message(sid)
    while not result["done"]:
        q = result["question"]
        print(f"\n🤖 البوت: {q['question_text']}")
        if q.get("hint"):
            print(f"  ↳ {q['hint']}")
        if "options" in q:
            for i, opt in enumerate(q["options"], 1):
                print(f"  {i}. {opt['label']}")
            if q["type"] == "multi_choice":
                raw = input("اختيارك (أرقام مفصولة بفاصلة): ").strip()
                indices = [int(x) - 1 for x in raw.split(",") if x.strip().isdigit()]
                answer = [q["options"][i]["value"] for i in indices if 0 <= i < len(q["options"])]
            else:
                raw = input("اختيارك (رقم): ").strip()
                idx = int(raw) - 1 if raw.isdigit() else -1
                answer = q["options"][idx]["value"] if 0 <= idx < len(q["options"]) else ""
        else:
            answer = input("إجابتك: ").strip()
        result = handle_message(sid, answer)
    print(f"\n{result['reply']}")