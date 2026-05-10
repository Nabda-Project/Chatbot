"""
med.py  –  Cardiac intake chatbot with per-symptom question loops.
تم التعديل: 
1. تحويل الإجابات إلى نص عربي مفهوم يدخل للنموذج (Injection)
2. فلترة أي نص إنجليزي في المدخلات والمخرجات
3. إضافة retry logic وزيادة timeout لتجنب قطع الاتصال
"""

import re
import time
import json
import requests

# ==================== CONFIG ====================
AI_URL  = "http://100.51.212.220:8000/generate"
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

# ==================== خرائط الترجمة من الكود للعربي ====================

SEVERITY_MAP = {
    "mild": "بسيطة", "moderate": "متوسطة", "severe": "شديدة", "unbearable": "لا تحتمل",
}
DURATION_MAP = {
    "today": "بدأت اليوم", "days": "منذ أيام", "weeks": "منذ أسابيع",
    "months": "منذ شهور", "years": "منذ سنوات", "since_childhood": "منذ الطفولة",
}
PATTERN_MAP = {
    "continuous": "مستمر طوال الوقت", "episodic": "يأتي على شكل نوبات", "single": "نوبة واحدة فقط حدثت",
}
EPISODE_DURATION_MAP = {
    "seconds": "ثوانٍ", "minutes_short": "دقائق قليلة", "minutes_long": "من 5 إلى 30 دقيقة",
    "hours": "ساعات", "continuous": "مستمر لا يزول",
}
TRIGGERS_MAP = {
    "sudden": "فجأة بدون سبب واضح", "night": "في الليل", "sleep": "أثناء النوم ويوقظني",
    "waking": "عند الاستيقاظ", "exertion": "عند المجهود أو الرياضة أو صعود الدرج",
    "rest": "عند الراحة", "after_meals": "بعد الأكل", "emotional": "عند التوتر أو الغضب",
    "after_caffeine": "بعد شرب القهوة أو الشاي", "after_smoking": "بعد التدخين",
    "cold_water": "عند ملامسة الماء البارد", "menstruation": "مع الدورة الشهرية",
}
RELIEVING_MAP = {
    "rest": "الراحة", "medication": "تناول الدواء", "position_change": "تغيير الوضعية",
    "deep_breathing": "التنفس العميق", "nothing": "لا شيء يخففه", "self_resolves": "يزول من تلقاء نفسه",
}
RADIATION_MAP = {
    "no_radiation": "لا ينتشر", "left_arm": "الذراع والكتف واليد اليسرى",
    "right_arm": "الذراع والكتف واليد اليمنى", "back": "الظهر وبين الكتفين",
    "neck": "الرقبة", "jaw": "الفك أو الأسنان", "upper_abdomen": "أعلى البطن",
}
YES_NO_MAP = {
    "yes": "نعم", "no": "لا", "not_sure": "لست متأكداً",
}
QUALITY_MAP = {
    "pressure": "ضغط وثقل", "burning": "حرقة وحموضة", "stabbing": "طعنة وخز حاد",
    "tightness": "شد وتشنج", "vague": "إحساس غريب يصعب وصفه",
}
LOCATION_MAP = {
    "left_precordial": "منطقة القلب على اليسار", "central": "منتصف الصدر",
    "right": "الجانب الأيمن", "moving": "عشوائية تتنقل",
}
RATE_FEEL_MAP = {
    "fast_regular": "سريعة جداً ومنتظمة", "fast_irregular": "سريعة وغير منتظمة",
    "forceful": "قوية وأشعر بها في صدري", "neck_pounding": "أشعر بها في رقبتي",
}
SKIP_EXTRA_MAP = {
    "pause_then_thump": "إحساس بتوقف لحظي ثم عودة", "extra_beat": "ضربة إضافية خارج النظام",
    "full_irregular": "اضطراب كامل في الإيقاع", "svt_like": "تسارع مفاجئ ثم عودة طبيعية",
}
ORTHOPTHNEA_MAP = {
    "yes_orthopnea": "نعم أحتاج وسائد إضافية", "no": "لا", "not_sure": "لست متأكداً",
}
EXERTION_LEVEL_MAP = {
    "moderate_exertion": "عند المشي السريع أو صعود الدرج", "minimal_exertion": "عند أدنى مجهود كالمشي البطيء",
    "at_rest": "عند الراحة التامة", "unrelated": "لا يرتبط بالمجهود",
}
DIZZINESS_TYPE_MAP = {
    "vertigo": "إحساس بالدوران كأن الأرض تدور", "lightheaded": "ضبابية وعدم وضوح",
    "presyncope": "إحساس بالإغماء الوشيك", "imbalance": "عدم اتزان عند المشي",
}
FAINTING_LOSS_MAP = {
    "complete_loss": "فقدت الوعي تماماً", "near_syncope": "كاد يحدث واسودّ أمامي",
}
RECOVERY_TIME_MAP = {
    "seconds": "ثوانٍ أقل من دقيقة", "minutes": "دقيقة أو أكثر", "required_intervention": "استدعى تدخل طبي",
}
SIDE_MAP = {
    "left_only": "الجانب الأيسر فقط", "right_only": "الجانب الأيمن فقط", "both": "الجانبين",
}
EXERTIONAL_CHANGE_MAP = {
    "yes": "نعم بشكل واضح", "slightly": "قليلاً", "no": "لا",
}
CARDIAC_DIAGNOSIS_MAP = {
    "none": "لا يوجد تشخيص سابق", "mvp": "ارتخاء في الصمام الميترالي",
    "hole_congenital": "ثقب في القلب أو عيب خلقي", "enlarged": "تضخم في القلب",
    "arrhythmia": "عدم انتظام في ضربات القلب أو خوارج انقباض",
    "prior_mi_stroke": "جلطة أو ذبحة صدرية أو سكتة سابقة",
    "catheter_stent": "قسطرة أو دعامة أو عملية قلب", "other": "تشخيص آخر",
}
PRIOR_WORKUP_MAP = {
    "none": "لا شيء", "ecg": "رسم قلب", "echo": "أشعة تلفزيونية على القلب إيكو",
    "holter": "هولتر رسم قلب لمدة 24 ساعة", "stress": "رسم قلب بالمجهود", "cath": "قسطرة تشخيصية",
}
CHRONIC_CONDITIONS_MAP = {
    "none": "لا شيء", "htn": "ارتفاع ضغط الدم", "low_bp": "انخفاض ضغط الدم",
    "dm": "السكري", "chol": "ارتفاع الكوليسترول", "thyroid": "اضطراب في الغدة الدرقية",
    "anemia": "فقر دم أو أنيميا", "ibs": "القولون العصبي", "reflux": "ارتجاع أو حموضة أو جرثومة المعدة",
}
MED_ADHERENCE_MAP = {
    "compliant": "لا ملتزم بالدواء", "recently_stopped": "نعم توقفت منذ أيام أو أسابيع",
    "irregular": "أتناول جرعات غير منتظمة",
}
LIFESTYLE_MAP = {
    "none": "لا شيء", "smoker": "أدخن حالياً", "ex_smoker": "مدخن سابق وتركت",
    "heavy_caffeine": "أتناول كمية كبيرة من القهوة أو الشاي",
    "gym": "أمارس الرياضة بانتظام", "supplements": "أتناول منشطات أو هرمونات",
}


# ==================== PER-SYMPTOM QUESTION BANKS ====================

def _build_common_questions(code: str, label: str) -> list:
    return [
        {
            "field":   f"symptom_detail.{code}.severity",
            "q":       f"ما شدة [{label}] عندما تحدث؟",
            "v":       "choice",
            "options": {
                "بسيطة / خفيفة": "mild", "متوسطة / مزعجة": "moderate",
                "شديدة / قوية": "severe", "لا أحتمل": "unbearable",
            },
        },
        {
            "field":   f"symptom_detail.{code}.duration_general",
            "q":       f"منذ متى وأنت تعاني من [{label}]؟",
            "v":       "choice",
            "options": {
                "بدأت اليوم": "today", "منذ أيام": "days", "منذ أسابيع": "weeks",
                "منذ شهور": "months", "منذ سنوات": "years", "منذ الطفولة": "since_childhood",
            },
        },
        {
            "field":   f"symptom_detail.{code}.pattern",
            "q":       f"كيف يأتي [{label}]؟",
            "v":       "choice",
            "options": {
                "مستمر طوال الوقت / موجود الآن": "continuous",
                "نوبات تأتي وتذهب": "episodic", "نوبة واحدة فقط حتى الآن": "single",
            },
        },
        {
            "field":   f"symptom_detail.{code}.episode_duration",
            "q":       f"كم تستمر نوبة [{label}] عادةً؟",
            "v":       "choice",
            "options": {
                "ثوانٍ": "seconds", "دقائق قليلة (< 5 دقائق)": "minutes_short",
                "من 5 إلى 30 دقيقة": "minutes_long", "ساعات": "hours", "مستمر لا يزول": "continuous",
            },
            "depends_on": {"field": f"symptom_detail.{code}.pattern", "equals": "episodic"},
        },
        {
            "field":   f"symptom_detail.{code}.triggers",
            "q":       f"متى يحدث [{label}] عادةً؟ (اختر كل ما ينطبق)",
            "v":       "multi_choice",
            "options": {
                "فجأة بدون سبب واضح": "sudden", "في الليل": "night", "أثناء النوم (يوقظني)": "sleep",
                "عند الاستيقاظ": "waking", "عند المجهود / الرياضة / الدرج": "exertion", "عند الراحة": "rest",
                "بعد الأكل": "after_meals", "عند التوتر أو الغضب": "emotional", "بعد القهوة / الشاي": "after_caffeine",
                "بعد التدخين": "after_smoking", "مع ملامسة الماء البارد": "cold_water", "مع الدورة الشهرية": "menstruation",
            },
        },
        {
            "field":   f"symptom_detail.{code}.relieving_factors",
            "q":       f"ما الذي يخفف [{label}]؟ (اختر كل ما ينطبق)",
            "v":       "multi_choice",
            "options": {
                "الراحة": "rest", "الدواء": "medication", "تغيير الوضعية": "position_change",
                "التنفس العميق": "deep_breathing", "لا شيء يخففه": "nothing", "يزول من تلقاء نفسه": "self_resolves",
            },
        },
    ]

def _get_extras_for_code(code: str) -> list:
    extras = {
        "chest_pain": [
            {"field": f"symptom_detail.{code}.radiation", "q": "هل ينتشر ألم الصدر إلى مناطق أخرى؟ (اختر كل ما ينطبق)", "v": "multi_choice",
             "options": {"لا ينتشر": "no_radiation", "الذراع / الكتف / اليد اليسرى": "left_arm", "الذراع / الكتف / اليد اليمنى": "right_arm", "الظهر / بين الكتفين": "back", "الرقبة": "neck", "الفك أو الأسنان": "jaw", "أعلى البطن": "upper_abdomen"}},
            {"field": f"symptom_detail.{code}.exertional", "q": "هل يزداد ألم الصدر مع المجهود ويخف مع الراحة؟", "v": "choice", "options": {"نعم": "yes", "لا": "no", "لست متأكداً": "not_sure"}},
            {"field": f"symptom_detail.{code}.quality", "q": "كيف تصف طبيعة ألم الصدر؟", "v": "choice",
             "options": {"ضغط / ثقل": "pressure", "حرقة / حموضة": "burning", "طعنة / وخز حاد": "stabbing", "شد / تشنج": "tightness", "إحساس غريب يصعب وصفه": "vague"}},
        ],
        "heart_pain": [
            {"field": f"symptom_detail.{code}.radiation", "q": "هل ينتشر ألم منطقة القلب إلى مناطق أخرى؟ (اختر كل ما ينطبق)", "v": "multi_choice",
             "options": {"لا ينتشر": "no_radiation", "الذراع / الكتف / اليد اليسرى": "left_arm", "الرقبة": "neck", "الفك": "jaw", "الظهر": "back"}},
            {"field": f"symptom_detail.{code}.exertional", "q": "هل يزداد ألم منطقة القلب مع المجهود ويخف مع الراحة؟", "v": "choice", "options": {"نعم": "yes", "لا": "no", "لست متأكداً": "not_sure"}},
        ],
        "stabs": [
            {"field": f"symptom_detail.{code}.location", "q": "أين تقع النغزات / الوخز بالضبط؟", "v": "choice",
             "options": {"منطقة القلب (اليسار)": "left_precordial", "منتصف الصدر": "central", "اليمين": "right", "عشوائية تتنقل": "moving"}},
        ],
        "palpitations": [
            {"field": f"symptom_detail.{code}.rate_feel", "q": "كيف تشعر بضربات القلب أثناء الخفقان؟", "v": "choice",
             "options": {"سريعة جداً ومنتظمة": "fast_regular", "سريعة وغير منتظمة": "fast_irregular", "قوية وأشعر بها في صدري": "forceful", "أشعر بها في رقبتي": "neck_pounding"}},
        ],
        "irregular": [
            {"field": f"symptom_detail.{code}.skip_or_extra", "q": "ما أقرب وصف لما تشعر به؟", "v": "choice",
             "options": {"إحساس بتوقف لحظي ثم عودة": "pause_then_thump", "ضربة إضافية خارج النظام": "extra_beat", "اضطراب كامل في الإيقاع": "full_irregular", "تسارع مفاجئ ثم عودة طبيعية": "svt_like"}},
        ],
        "dyspnea": [
            {"field": f"symptom_detail.{code}.orthopnea", "q": "هل يزداد ضيق التنفس عند الاستلقاء؟", "v": "choice", "options": {"نعم، أحتاج وسائد إضافية": "yes_orthopnea", "لا": "no", "لست متأكداً": "not_sure"}},
            {"field": f"symptom_detail.{code}.exertion_level", "q": "ما مستوى الجهد الذي يسبب ضيق التنفس؟", "v": "choice",
             "options": {"عند المشي السريع / صعود الدرج": "moderate_exertion", "عند أدنى مجهود (المشي البطيء)": "minimal_exertion", "عند الراحة التامة": "at_rest", "لا يرتبط بالمجهود": "unrelated"}},
        ],
        "dizziness": [
            {"field": f"symptom_detail.{code}.type", "q": "كيف تصف الدوخة؟", "v": "choice",
             "options": {"إحساس بالدوران (كأن الأرض تدور)": "vertigo", "ضبابية / عدم وضوح": "lightheaded", "إحساس بالإغماء الوشيك": "presyncope", "عدم اتزان عند المشي": "imbalance"}},
        ],
        "fainting": [
            {"field": f"symptom_detail.{code}.full_loss", "q": "هل فقدت الوعي تماماً أم كاد فقط؟", "v": "choice", "options": {"فقدت الوعي تماماً": "complete_loss", "كاد يحدث / اسودّ أمامي": "near_syncope"}},
            {"field": f"symptom_detail.{code}.recovery_time", "q": "كم استغرق التعافي؟", "v": "choice", "options": {"ثوانٍ (< 1 دقيقة)": "seconds", "دقيقة أو أكثر": "minutes", "استدعى التدخل": "required_intervention"}},
        ],
        "arm_radiation": [
            {"field": f"symptom_detail.{code}.side", "q": "الانتشار في أي جانب؟", "v": "choice", "options": {"اليسار فقط": "left_only", "اليمين فقط": "right_only", "الجانبين": "both"}},
        ],
        "fatigue": [
            {"field": f"symptom_detail.{code}.exertional_change", "q": "هل يزداد الإرهاق مع أي مجهود؟", "v": "choice", "options": {"نعم بشكل واضح": "yes", "قليلاً": "slightly", "لا": "no"}},
        ],
    }
    return extras.get(code, [])

def _build_known_symptom_questions(code: str) -> list:
    label = CODE_TO_LABEL.get(code, code)
    return _build_common_questions(code, label) + _get_extras_for_code(code)

def _build_other_symptom_questions(code: str, label: str) -> list:
    return _build_common_questions(code, label)

SYMPTOM_QUESTION_BANKS: dict = {
    code: _build_known_symptom_questions(code)
    for code in SYMPTOM_LABELS.values() if code != "other"
}


# ==================== STAGE QUESTIONS ====================

STAGE_QUESTIONS = {
    "DEMOGRAPHICS": [
        {"field": "demographics.age", "q": "كم العمر بالسنوات؟", "v": "number", "min": 1, "max": 110},
        {"field": "demographics.sex", "q": "الجنس؟", "v": "choice", "options": {"ذكر": "male", "أنثى": "female"}},
        {"field": "demographics.pregnancy", "q": "هل أنتِ حامل حالياً أو في فترة ما بعد الولادة (خلال 6 أسابيع)؟", "v": "choice", "options": {"حامل": "pregnant", "ما بعد الولادة": "postpartum", "لا": "no"}, "depends_on": {"field": "demographics.sex", "equals": "female"}},
        {"field": "demographics.weight_kg", "q": "ما هو الوزن بالكيلوجرام؟", "v": "number", "min": 3, "max": 300},
        {"field": "demographics.height_cm", "q": "ما هو الطول بالسنتيمتر؟", "v": "number", "min": 50, "max": 250},
    ],
    "HISTORY": [
        {"field": "history.known_cardiac", "q": "هل سبق تشخيصك بمرض في القلب؟ (يمكنك اختيار أكثر من إجابة)", "v": "multi_choice", "options": {"لا يوجد تشخيص سابق": "none", "ارتخاء في الصمام الميترالي": "mvp", "ثقب في القلب / عيب خلقي": "hole_congenital", "تضخم في القلب": "enlarged", "عدم انتظام في ضربات القلب / خوارج انقباض": "arrhythmia", "جلطة أو ذبحة صدرية أو سكتة سابقة": "prior_mi_stroke", "قسطرة / دعامة / عملية قلب": "catheter_stent", "تشخيص آخر": "other"}},
        {"field": "history.prior_workup", "q": "هل قمت سابقاً بأي من الفحوصات التالية للقلب؟ (يمكنك اختيار أكثر من إجابة)", "v": "multi_choice", "options": {"لا شيء": "none", "رسم قلب (ECG)": "ecg", "أشعة تلفزيونية على القلب (إيكو)": "echo", "هولتر (رسم قلب لمدة 24 ساعة)": "holter", "رسم قلب بالمجهود": "stress", "قسطرة تشخيصية": "cath"}},
        {"field": "history.chronic_conditions", "q": "هل تعاني من أي من الحالات التالية؟ (يمكنك اختيار أكثر من إجابة)", "v": "multi_choice", "options": {"لا شيء": "none", "ارتفاع ضغط الدم": "htn", "انخفاض ضغط الدم": "low_bp", "السكري": "dm", "ارتفاع الكوليسترول": "chol", "اضطراب في الغدة الدرقية": "thyroid", "فقر دم / أنيميا": "anemia", "القولون العصبي": "ibs", "ارتجاع / حموضة / جرثومة المعدة": "reflux"}},
        {"field": "history.medications", "q": 'ما الأدوية التي تتناولها حالياً بانتظام؟ (اذكر الاسم والجرعة إن أمكن، أو اكتب "لا شيء")', "v": "text"},
        {"field": "history.med_adherence", "q": "هل توقفت عن تناول أي من أدويتك مؤخراً؟", "v": "choice", "options": {"لا، ملتزم بالدواء": "compliant", "نعم، توقفت منذ أيام أو أسابيع": "recently_stopped", "أتناول جرعات غير منتظمة": "irregular"}, "depends_on": {"field": "history.medications", "not_text_in": ["لا شيء", "لا", "none", "لا يوجد"]}},
        {"field": "history.family_history", "q": "هل يعاني أحد الأقارب من الدرجة الأولى من مرض في القلب قبل سن 55؟", "v": "choice", "options": {"نعم": "yes", "لا": "no", "لا أعرف": "unknown"}},
        {"field": "history.lifestyle", "q": "هل ينطبق عليك أي من التالي؟ (يمكنك اختيار أكثر من إجابة)", "v": "multi_choice", "options": {"لا شيء": "none", "أدخن حالياً": "smoker", "مدخن سابق وتركت": "ex_smoker", "أتناول كمية كبيرة من القهوة أو الشاي (أكثر من 3 أكواب يومياً)": "heavy_caffeine", "أمارس الرياضة بانتظام": "gym", "أتناول منشطات أو هرمونات": "supplements"}},
    ],
    "SYMPTOM_SELECTION": [
        {"field": "symptom_selection.chosen", "q": "ما الأعراض التي تشعر بها؟ (اختر كل ما ينطبق عليك)", "v": "multi_choice", "options": SYMPTOM_LABELS},
    ],
    "RED_FLAG_SCREENING": [
        {"field": "red_flags.exertional_chest", "q": "هل يوجد ألم في الصدر يزداد مع المجهود ويخف مع الراحة؟", "v": "choice", "options": {"نعم": "yes", "لا": "no", "لست متأكداً": "not_sure"}, "depends_on": {"field": "symptom_selection.chosen", "not_contains_any": ["chest_pain", "heart_pain"]}},
        {"field": "red_flags.syncope_exertion", "q": "هل سبق أن أُغمي عليك أثناء الرياضة أو المجهود الشديد؟", "v": "choice", "options": {"نعم": "yes", "لا": "no"}},
    ],
    "FREE_TEXT": [
        {"field": "free_text.additional", "q": 'هل هناك أي شيء آخر تود إضافته عن حالتك؟ (إذا لا، اكتب "لا")', "v": "text"},
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

    # text: فلترة الإنجليزي فقط (نحافظ على الأرقام للجرعات مثل ٥٠ مجم)
    text = str(payload).strip()
    text = re.sub(r'[a-zA-Z]', '', text).strip()
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
            "demographics": {}, "history": {}, "symptom_selection": {},
            "symptom_detail": {}, "other_symptoms": [], "red_flags": {}, "free_text": {}, "narrative": "",
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
    return {"field": "symptom_loop.other_count", "q": "كم عدد الأعراض الإضافية الأخرى التي تريد وصفها؟", "v": "number", "min": 1, "max": 10, "_transient": True}

def _other_label_question(index: int) -> dict:
    return {"field": f"symptom_loop.other_label_{index}", "q": f"ما هو العرض الإضافي رقم {index + 1}؟ (اكتب وصفاً مختصراً بالعربي)", "v": "text", "_transient": True}


# ==================== SYMPTOM LOOP ENGINE ====================

def _init_symptom_loop(state: ConversationState):
    chosen = state.data["symptom_selection"].get("chosen", [])
    if not isinstance(chosen, list):
        chosen = []
    has_other = "other" in chosen
    known     = [c for c in chosen if c != "other"]
    state.symptom_loop_state = {
        "phase": "ask_other_count" if has_other else "ask_symptoms",
        "known_symptoms": known, "other_count": None, "other_labels": [], "other_collected": 0,
        "combined_list": list(known) if not has_other else [], "current_index": 0, "question_index": 0,
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
    if sls["phase"] == "ask_other_count":
        return _other_count_question()
    if sls["phase"] == "ask_other_labels":
        if sls["other_collected"] < sls["other_count"]:
            return _other_label_question(sls["other_collected"])
        other_codes = [f"other_{i}" for i in range(sls["other_count"])]
        sls["combined_list"] = sls["known_symptoms"] + other_codes
        sls["phase"] = "ask_symptoms"
        sls["current_index"] = 0
        sls["question_index"] = 0
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
        text = str(payload).strip()
        if not text:
            return {"done": False, "question": _serialize_question(q, hint="⚠️ الرجاء كتابة وصف للعرض."), "reply": None}
        sls["other_labels"].append(text)
        sls["other_collected"] += 1
        return None
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


# ==================== 🔥 بناء النص العربي للنموذج ====================

def _translate_code(code: str, mapping: dict) -> str:
    return mapping.get(code, code)

def _dict_to_arabic_text(obj, depth=0) -> str:
    """تحويل أي dict أو list لنص عربي مسطّح قابل للقراءة"""
    if depth > 5:
        return str(obj)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, list):
        parts = [_dict_to_arabic_text(item, depth+1) for item in obj if item not in (None, "", [], {})]
        return "\n".join(p for p in parts if p.strip())
    if isinstance(obj, dict):
        parts = []
        for v in obj.values():
            text = _dict_to_arabic_text(v, depth+1)
            if text.strip():
                parts.append(text)
        return "\n".join(p for p in parts if p.strip())
    return str(obj)

def _translate_list(codes: list, mapping: dict) -> str:
    if not codes:
        return ""
    translated = [_translate_code(str(c), mapping) for c in codes if c is not None and str(c) != "__skipped__"]
    return " و".join(translated)

def _is_skipped(value) -> bool:
    return value == "__skipped__" or value is None

def _build_arabic_narrative(data: dict) -> str:
    parts = []
    
    # ========== 1. البيانات الديموغرافية ==========
    demo = data.get("demographics", {})
    demo_parts = []
    
    if demo.get("age") and not _is_skipped(demo["age"]):
        demo_parts.append(f"عمري {int(demo['age'])} سنة")
    if demo.get("sex") and not _is_skipped(demo["sex"]):
        sex_ar = _translate_code(demo["sex"], {"male": "ذكر", "female": "أنثى"})
        demo_parts.append(f"أنا {sex_ar}")
    if demo.get("weight_kg") and not _is_skipped(demo["weight_kg"]):
        demo_parts.append(f"وزني {demo['weight_kg']} كيلوجرام")
    if demo.get("height_cm") and not _is_skipped(demo["height_cm"]):
        demo_parts.append(f"طولي {demo['height_cm']} سنتيمتر")
    if demo.get("pregnancy") and not _is_skipped(demo["pregnancy"]):
        preg_ar = _translate_code(demo["pregnancy"], {"pregnant": "وحامل حالياً", "postpartum": "وفي فترة ما بعد الولادة", "no": ""})
        if preg_ar:
            demo_parts.append(preg_ar)
    if demo_parts:
        parts.append("، ".join(demo_parts) + ".")
    
    # ========== 2. التاريخ المرضي ==========
    history = data.get("history", {})
    history_parts = []
    
    cardiac = history.get("known_cardiac", [])
    if cardiac and isinstance(cardiac, list) and "none" not in cardiac:
        cardiac_ar = _translate_list(cardiac, CARDIAC_DIAGNOSIS_MAP)
        if cardiac_ar:
            history_parts.append(f"سبق تشخيصي بـ: {cardiac_ar}")
    
    workup = history.get("prior_workup", [])
    if workup and isinstance(workup, list) and "none" not in workup:
        workup_ar = _translate_list(workup, PRIOR_WORKUP_MAP)
        if workup_ar:
            history_parts.append(f"قمت بفحوصات سابقة تشمل: {workup_ar}")
    
    chronic = history.get("chronic_conditions", [])
    if chronic and isinstance(chronic, list) and "none" not in chronic:
        chronic_ar = _translate_list(chronic, CHRONIC_CONDITIONS_MAP)
        if chronic_ar:
            history_parts.append(f"أعاني من: {chronic_ar}")
    
    meds = history.get("medications", "")
    if meds and not _is_skipped(meds) and meds not in ["لا شيء", "لا", "none"]:
        history_parts.append(f"أتناول أدوية: {meds}")
        adherence = history.get("med_adherence")
        if adherence and not _is_skipped(adherence):
            adherence_ar = _translate_code(adherence, MED_ADHERENCE_MAP)
            history_parts.append(f"حالة الالتزام بالدواء: {adherence_ar}")
    
    family = history.get("family_history")
    if family and not _is_skipped(family):
        if family == "yes":
            history_parts.append("يوجد تاريخ عائلي لمرض القلب")
        elif family == "no":
            history_parts.append("لا يوجد تاريخ عائلي لمرض القلب")
    
    lifestyle = history.get("lifestyle", [])
    if lifestyle and isinstance(lifestyle, list) and "none" not in lifestyle:
        lifestyle_ar = _translate_list(lifestyle, LIFESTYLE_MAP)
        if lifestyle_ar:
            history_parts.append(f"عاداتي: {lifestyle_ar}")
            
    if history_parts:
        parts.append("، ".join(history_parts) + ".")
    
    # ========== 3. الأعراض التفصيلية ==========
    symptom_detail = data.get("symptom_detail", {})
    other_symptoms = data.get("other_symptoms", [])
    
    for code, detail in symptom_detail.items():
        if not detail:
            continue
            
        label = None
        for item in other_symptoms:
            if item.get("code") == code:
                label = item.get("label", code)
                break
        if label is None:
            label = CODE_TO_LABEL.get(code, code)
        
        symptom_sentence = f"أنا أعاني من {label}"
        
        severity = detail.get("severity")
        if severity and not _is_skipped(severity):
            symptom_sentence += f" بشدة {_translate_code(severity, SEVERITY_MAP)}"
            
        duration = detail.get("duration_general")
        if duration and not _is_skipped(duration):
            symptom_sentence += f"، {_translate_code(duration, DURATION_MAP)}"
            
        pattern = detail.get("pattern")
        if pattern and not _is_skipped(pattern):
            symptom_sentence += f"، يكون {_translate_code(pattern, PATTERN_MAP)}"
            
        episode_dur = detail.get("episode_duration")
        if episode_dur and not _is_skipped(episode_dur):
            symptom_sentence += f"، تستمر النوبة {_translate_code(episode_dur, EPISODE_DURATION_MAP)}"
            
        triggers = detail.get("triggers")
        if triggers and isinstance(triggers, list) and not all(_is_skipped(t) for t in triggers):
            triggers_ar = _translate_list(triggers, TRIGGERS_MAP)
            if triggers_ar:
                symptom_sentence += f"، يحدث عند: {triggers_ar}"
                
        relieving = detail.get("relieving_factors")
        if relieving and isinstance(relieving, list) and not all(_is_skipped(r) for r in relieving):
            relieving_ar = _translate_list(relieving, RELIEVING_MAP)
            if relieving_ar:
                symptom_sentence += f"، يخففه: {relieving_ar}"
                
        radiation = detail.get("radiation")
        if radiation and isinstance(radiation, list) and not all(_is_skipped(r) for r in radiation):
            radiation_ar = _translate_list(radiation, RADIATION_MAP)
            if radiation_ar:
                symptom_sentence += f"، ينتشر إلى: {radiation_ar}"
                
        exertional = detail.get("exertional")
        if exertional and not _is_skipped(exertional):
            symptom_sentence += f"، يزداد مع المجهود ويخف مع الراحة: {_translate_code(exertional, YES_NO_MAP)}"
            
        quality = detail.get("quality")
        if quality and not _is_skipped(quality):
            symptom_sentence += f"، طبيعة الألم: {_translate_code(quality, QUALITY_MAP)}"
            
        location = detail.get("location")
        if location and not _is_skipped(location):
            symptom_sentence += f"، مكانه: {_translate_code(location, LOCATION_MAP)}"
            
        rate_feel = detail.get("rate_feel")
        if rate_feel and not _is_skipped(rate_feel):
            symptom_sentence += f"، أشعر بضربات: {_translate_code(rate_feel, RATE_FEEL_MAP)}"
            
        skip_extra = detail.get("skip_or_extra")
        if skip_extra and not _is_skipped(skip_extra):
            symptom_sentence += f"، الوصف: {_translate_code(skip_extra, SKIP_EXTRA_MAP)}"
            
        orthopnea = detail.get("orthopnea")
        if orthopnea and not _is_skipped(orthopnea):
            symptom_sentence += f"، يزداد عند الاستلقاء: {_translate_code(orthopnea, ORTHOPTHNEA_MAP)}"
            
        exertion_level = detail.get("exertion_level")
        if exertion_level and not _is_skipped(exertion_level):
            symptom_sentence += f"، يحدث عند: {_translate_code(exertion_level, EXERTION_LEVEL_MAP)}"
            
        dizziness_type = detail.get("type")
        if dizziness_type and not _is_skipped(dizziness_type):
            symptom_sentence += f"، نوع الدوخة: {_translate_code(dizziness_type, DIZZINESS_TYPE_MAP)}"
            
        full_loss = detail.get("full_loss")
        if full_loss and not _is_skipped(full_loss):
            symptom_sentence += f"، {_translate_code(full_loss, FAINTING_LOSS_MAP)}"
            
        recovery = detail.get("recovery_time")
        if recovery and not _is_skipped(recovery):
            symptom_sentence += f"، مدة التعافي: {_translate_code(recovery, RECOVERY_TIME_MAP)}"
            
        side = detail.get("side")
        if side and not _is_skipped(side):
            symptom_sentence += f"، في: {_translate_code(side, SIDE_MAP)}"
            
        exertional_change = detail.get("exertional_change")
        if exertional_change and not _is_skipped(exertional_change):
            symptom_sentence += f"، يزداد مع المجهود: {_translate_code(exertional_change, EXERTIONAL_CHANGE_MAP)}"
            
        symptom_sentence += "."
        parts.append(symptom_sentence)
    
    # ========== 4. أعلام الخطورة ==========
    red_flags = data.get("red_flags", {})
    red_flag_parts = []
    
    exertional_chest = red_flags.get("exertional_chest")
    if exertional_chest and not _is_skipped(exertional_chest) and exertional_chest == "yes":
        red_flag_parts.append("يوجد ألم في الصدر يزداد مع المجهود")
    
    syncope_exertion = red_flags.get("syncope_exertion")
    if syncope_exertion and not _is_skipped(syncope_exertion) and syncope_exertion == "yes":
        red_flag_parts.append("حدث إغماء أثناء المجهود الشديد")
    
    if red_flag_parts:
        parts.append("ملاحظات مهمة: " + "، ".join(red_flag_parts) + ".")
        
    # ========== 5. نص إضافي حر ==========
    free_text = data.get("free_text", {}).get("additional", "")
    if free_text and not _is_skipped(free_text) and free_text not in ["لا", "لا شيء"]:
        parts.append(f"ملاحظات إضافية: {free_text}.")
    
    # ========== تجميع كل الأجزاء ==========
    full_narrative = "\n".join(str(p) for p in parts if p is not None)
    
    # فلترة نهائية لإزالة أي نص إنجليزي أو underscores متبقية
    full_narrative = re.sub(r'[a-zA-Z_]{2,}', '', str(full_narrative))
    full_narrative = re.sub(r'\s+', ' ', full_narrative).strip()
    
    return full_narrative



# ==================== ENHANCED PROMPT ENGINEERING ====================

def _build_expert_clinical_prompt(data: dict) -> str:
    """
    Transforms raw structured data into a rich, detailed prompt for the AI model.
    This replaces the flat narrative with a structured clinical brief to force 
    step-by-step reasoning and high-quality outputs from Qwen.
    """
    # We keep the flat narrative for the user UI, but build a structured one for the AI
    arabic_narrative = _build_arabic_narrative(data)
    
    prompt = f"""أنت استشاري قلب وأوعية دموية حاصل على أعلى الدرجات العلمية، ولديك خبرة تزيد عن 20 عاماً في تشخيص وعلاج أمراض القلب المعقدة. أنت تعمل في مستشفى جامعي مرجعي.

مهمتك هي تحليل الحالة السريرية التالية وتقديم تقييم طبي شامل ودقيق.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 الملخص السريري للمريض:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{arabic_narrative}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 بروتوكول التحليل المطلوب (فكر خطوة بخطوة):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. التفريق التشخيصي (Differential Diagnosis): قم أولاً بتصنيف الأعراض إلى (أسباب قلبية أولية، أسباب قلبية ثانوية، أسباب غير قلبية / نفسية جسدية).
2. التشخيص الأكثر ترجيحاً: حدد التشخيص الأقرب بناءً على تطابق الأعراض مع المعايير الطبية المعتمدة، مع ذكر السبب المنطقي لاختيارك.
3. تقييم الخطورة: قيّم درجة الخطورة بناءً على وجود أعلام خطورة (Red Flags) أو عوامل خطر، وصنفها بدقة: [بسيطة - متوسطة - عالية - طوارئ تتطلب زيارة الطوارئ فوراً].
4. خطة العمل والفحوصات: اقترح الفحوصات الدقيقة المطلوبة (مثل ECG، Echo، Holter) مع تبرير سبب طلب كل فحص لهذه الحالة تحديداً.
5. النصائح الفورية: ما الذي يجب على المريض فعله الآن؟ (مثل تجنب المجهود، تغيير الوضعية، متى يجب الذهاب للطوارئ).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تنسيق الإجابة المطلوب:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- استخدم تنسيق Markdown (عناوين، نقاط، خط عريض).
- كن دقيقاً وموجهاً في كلامك، تجنب التعميمات.
- لا تستخدم أي حرف أو كلمة إنجليزية في الرد (حتى الاختصارات الطبية، اكتبها بالعربي مثل: رسم قلب، إيكو، هولتر).
- أضف في نهاية الرد إخلاء مسؤولية طبية قصير جداً.
"""
    return prompt
# ==================== AI ====================

# ==================== AI ====================

# ==================== AI ====================

def call_ai_api(data: dict) -> dict | str:
    """
    Sends the Arabic narrative to the AI server using its async poll pattern:
      1. POST /generate  →  { poll_url: "/jobs/<id>" }
      2. GET  /jobs/<id> →  { status: "completed", result: <dict> }
                            { status: "failed", ... }
                            { status: "processing", ... }  (keep polling)

    Returns the structured result dict on success, or an Arabic error string on failure.

    NOTE: We send only the plain Arabic narrative (same format as the working test script),
    NOT the full clinical prompt — the server does its own structured extraction.
    """
    from urllib.parse import urlparse

    # Send the plain narrative exactly like the working standalone script
    narrative = _build_arabic_narrative(data)

    parsed   = urlparse(AI_URL)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    headers  = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # ── Step 1: submit job ──────────────────────────────────────────────
    # Server can be slow to accept — use a generous timeout for the initial POST
    try:
        r = requests.post(AI_URL, headers=headers, json={"text": narrative}, timeout=120)
    except requests.exceptions.ConnectionError:
        return "⚠️ لا يمكن الاتصال بالخادم الطبي."
    except requests.exceptions.Timeout:
        return "⚠️ انتهت مهلة الاتصال بالخادم."
    except Exception as exc:
        return f"⚠️ خطأ غير متوقع: {exc}"

    if r.status_code != 200:
        return f"⚠️ خطأ من الخادم: HTTP {r.status_code} — {r.text[:300]}"

    job_data  = r.json()
    poll_path = job_data.get("poll_url")
    if not poll_path:
        return f"⚠️ لم يُرجع الخادم رابط المتابعة (poll_url). الرد: {job_data}"

    poll_url = f"{base_url}{poll_path}"

    # ── Step 2: poll until done ─────────────────────────────────────────
    max_wait_seconds = 300   # 5 minutes hard cap
    poll_interval    = 2     # seconds between polls (server takes ~44s, no need to hammer)
    elapsed          = 0

    while elapsed < max_wait_seconds:
        try:
            pr = requests.get(poll_url, headers=headers, timeout=60)
        except Exception as exc:
            return f"⚠️ خطأ أثناء الاستعلام عن النتيجة: {exc}"

        if pr.status_code != 200:
            return f"⚠️ خطأ أثناء الاستعلام: HTTP {pr.status_code} — {pr.text[:300]}"

        poll_data = pr.json()
        status    = poll_data.get("status")

        if status == "completed":
            result = poll_data.get("result")
            if isinstance(result, (dict, list)):
                return result
            return result if result else "⚠️ النتيجة فارغة من الخادم."

        if status == "failed":
            # Surface the full failure payload so the caller can debug
            error_detail = poll_data.get("error") or poll_data.get("message") or poll_data.get("detail") or str(poll_data)
            return f"⚠️ فشل الخادم: {error_detail}"

        # Still processing — wait and retry
        time.sleep(poll_interval)
        elapsed += poll_interval

    return "⚠️ انتهى وقت الانتظار دون الحصول على نتيجة من الخادم."


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
            if q["v"] == "text":
                text = str(payload).strip()
                # فلترة الإنجليزي من إدخال النصوص
                text = re.sub(r'[a-zA-Z]', '', text).strip()
                if text:
                    _store(q, text, state)
                    state.current_question = None
                else:
                    return {"done": False, "question": _serialize_question(q, hint="⚠️ الرجاء كتابة إجابة باللغة العربية."), "reply": None}
            else:
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

    # استدعاء النموذج بالنص العربي المبني
    # استدعاء النموذج بالنص العربي المبني
    arabic_narrative = _build_arabic_narrative(state.data)
    server_result    = call_ai_api(state.data)

    # server_result is either the structured dict from the AI server,
    # or an Arabic error string if something went wrong.
    if isinstance(server_result, (dict, list)):
        analysis_result = server_result
        report_text     = json.dumps(server_result, ensure_ascii=False, indent=2)
    else:
        analysis_result = None
        report_text     = str(server_result)

    return {
        "done": True,
        "question": None,
        "analysis_result": analysis_result,
        "reply": (
            f"📋 انتهينا من جمع البيانات.\n\n"
            f"📝 ملخص الحالة:\n"
            f"{'─'*40}\n"
            f"{arabic_narrative}\n"
            f"{'─'*40}\n\n"
            f"🧠 التحليل السريري المتعمق:\n{report_text}"
        ),
    }


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