# =============================================================================
# STAGE_QUESTIONS for med.py — Merged from Opus 4.7 (base) + ChatGPT + GLM
# =============================================================================
# IMPORTANT: Your current med.py only supports v="number", v="choice", v="text".
# This file uses TWO new validation types you need to add to smart_parse():
#   - "multi_choice"  : user can select multiple options (comma/space separated)
#   - "depends_on"    : question is only asked if conditions are met
#
# Option format convention: {arabic_display_text: english_key}
#   This matches your existing code where user types Arabic and you store English.
#
# depends_on format:
#   Single condition:      {"field": "demo.sex", "equals": "female"}
#   Multiple conditions:   [{"field": "a", "equals": "x"}, {"field": "b", "equals": "y"}]
#   Multi-choice contains: {"field": "sx.main_symptoms", "contains_any": ["chest_pain", "heart_pain"]}
#   Any non-"none" value:  {"field": "hx.medications", "not_empty": True}
# =============================================================================

STAGES = [
    "GREETING",
    "DEMOGRAPHICS",
    "HISTORY",
    "SYMPTOMS",
    "RED_FLAG_SCREENING",
    "FREE_TEXT",
]

STAGE_QUESTIONS = {
    # -------------------------------------------------------------------------
    # DEMOGRAPHICS
    # -------------------------------------------------------------------------
    "DEMOGRAPHICS": [
        {
            "field": "demographics.pregnancy",
            "q": "هل أنتِ حامل حالياً أو في فترة ما بعد الولادة (خلال 6 أسابيع)؟",
            "v": "choice",
            "options": {
                "حامل": "pregnant",
                "ما بعد الولادة": "postpartum",
                "لا": "no",
            },
            "depends_on": [
                {"field": "demographics.sex", "equals": "female"},
                {"field": "demographics.subject", "equals": "self"},
            ],
        },
        {
            "field": "demographics.weight_kg",
            "q": "ما هو وزنك بالكيلوجرام؟",
            "v": "number",
            "min": 30,
            "max": 250,
        },
    ],

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------
    "HISTORY": [
        {
            "field": "history.known_cardiac",
            "q": "هل سبق تشخيصك بمرض في القلب؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا يوجد تشخيص سابق": "none",
                "ارتخاء في الصمام الميترالي": "mvp",
                "ثقب في القلب / عيب خلقي": "hole_congenital",
                "تضخم في القلب": "enlarged",
                "عدم انتظام في ضربات القلب / خوارج انقباض": "arrhythmia",
                "جلطة أو ذبحة صدرية أو سكتة سابقة": "prior_mi_stroke",
                "قسطرة / دعامة / عملية قلب": "catheter_stent",
                "تشخيص آخر": "other",
            },
        },
        {
            "field": "history.prior_workup",
            "q": "هل قمت سابقاً بأي من الفحوصات التالية للقلب؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا شيء": "none",
                "رسم قلب (ECG)": "ecg",
                "أشعة تلفزيونية على القلب (إيكو)": "echo",
                "هولتر (رسم قلب لمدة 24 ساعة)": "holter",
                "رسم قلب بالمجهود": "stress",
                "قسطرة تشخيصية": "cath",
                "اخرى" :"others",
            },
        },
        {
            "field": "history.chronic_conditions",
            "q": "هل تعاني من أي من الحالات التالية؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا شيء": "none",
                "ارتفاع ضغط الدم": "htn",
                "انخفاض ضغط الدم": "low_bp",
                "السكري": "dm",
                "ارتفاع الكوليسترول": "chol",
                "اضطراب في الغدة الدرقية": "thyroid",
                "فقر دم / أنيميا": "anemia",
                "القولون العصبي": "ibs",
                "ارتجاع / حموضة / جرثومة المعدة": "reflux",
                "اخرلا" : "other",
            },
        },
        {
            "field": "history.medications",
            "q": "ما الأدوية التي تتناولها حالياً بانتظام؟ (اذكر الاسم والجرعة إن أمكن، أو اكتب \"لا شيء\")",
            "v": "text",
        },

        #revision
        {
            "field": "history.med_adherence",
            "q": "هل توقفت عن تناول أي من أدويتك مؤخراً؟",
            "v": "choice",
            "options": {
                "لا، ملتزم بالدواء": "compliant",
                "نعم، توقفت منذ أيام أو أسابيع": "recently_stopped",
                "أتناول جرعات غير منتظمة": "irregular",
            },
            "depends_on": {"field": "history.medications", "not_equals_any": ["لا شيء", "لا", "none", "لا يوجد"]},
        },
        {
            "field": "history.family_history",
            "q": "هل يعاني أحد الأقارب من الدرجة الأولى بسبب مرض في القلب قبل سن 55؟",
            "v": "choice",
            "options": {
                "نعم": "yes",
                "لا": "no",
                "لا أعرف": "unknown",
            },
        },
        {
            "field": "history.lifestyle",
            "q": "هل ينطبق عليك أي من التالي؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا شيء": "none",
                "أدخن حالياً": "smoker",
                "مدخن سابق وتركت": "ex_smoker",
                "أتناول كمية كبيرة من القهوة أو النسكافيه أو الشاي (أكثر من 3 أكواب يومياً)": "heavy_caffeine",
                "أمارس الرياضة بانتظام": "gym",
                "أتناول منشطات أو هرمونات ": "supplements",
            },
        },
    ],

    # -------------------------------------------------------------------------
    # SYMPTOMS
    # -------------------------------------------------------------------------
    "SYMPTOMS": [
        #revision with AI to increase the chocies
        {
            "field": "symptoms.main_symptoms",
            "q": "ما الأعراض التي تشعر بها؟ (يمكنك اختيار أكثر من إجابة )",
            "v": "multi_choice",
            "options": {
                "خفقان / تسارع في ضربات القلب": "palpitations",
                "عدم انتظام في ضربات القلب / إحساس بتوقف القلب لحظياً": "irregular",
                "ألم أو ضغط أو ضيق في الصدر": "chest_pain",
                "ألم أو ضغط في منطقة القلب تحديداً": "heart_pain",
                "نغزات / وخز / طعنات": "stabs",
                "ضيق أو صعوبة في التنفس": "dyspnea",
                "دوخة / دوار / عدم اتزان": "dizziness",
                "إغماء أو فقدان وعي": "fainting",
                "تعب / إرهاق / ضعف عام": "fatigue",
                "تعرق (خصوصاً عرق بارد)": "sweating",
                "غثيان / قيء": "nausea",
                "ألم ينتشر إلى الذراع أو الكتف أو اليد اليسرى": "arm_radiation",
                "تنميل أو خدر في الأطراف": "tingling",
                "رجفة / ارتعاش": "tremor",
                "برودة في الأطراف": "cold_extremities",
                "عرض آخر": "other",
            },
        },
        {
            "field": "symptoms.problem_duration",
            "q": "منذ متى وأنت تعاني من هذه الأعراض بشكل عام؟",
            "v": "choice",
            "options": {
                "بدأت اليوم": "today",
                "منذ أيام": "days",
                "منذ أسابيع": "weeks",
                "منذ شهور": "months",
                "منذ سنوات": "years",
                "منذ الطفولة": "since_childhood",
            },
        },
        
        
        {
            "field": "symptoms.episode_pattern",
            "q": "كيف تأتي الأعراض؟",
            "v": "choice",
            "options": {
                "مستمرة طوال الوقت / موجودة الآن": "continuous",
                "نوبات تأتي وتذهب": "episodic",
                "نوبة واحدة فقط حتى الآن": "recent_single",
            },
        },
        
        {
            "field": "symptoms.episode_duration",
            "q": "كم تستمر النوبة الواحدة عادةً؟",
            "v": "choice",
            "options": {
                "ثوانٍ (تختفي بسرعة)": "seconds",
                "دقائق قليلة (أقل من 5 دقائق)": "minutes_short",
                "من 5 إلى 30 دقيقة": "minutes_long",
                "ساعات": "hours",
                "مستمرة لا تزول": "continuous",
            },
            "depends_on": {"field": "symptoms.episode_pattern", "equals": "episodic"},
        },
    
        {
            "field": "symptoms.triggers",
            "q": "متى تحدث الأعراض عادةً؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "فجأة بدون سبب واضح": "sudden",
                "في الليل": "night",
                "أثناء النوم (توقظني من النوم)": "sleep",
                "عند الاستيقاظ من النوم": "waking",
                "عند بذل مجهود / صعود الدرج / الرياضة": "exertion",
                "عند الراحة وأنا جالس / مستريح": "rest",
                "بعد الأكل": "after_meals",
                "عند التوتر أو الانفعال أو الغضب": "emotional",
                "بعد القهوة أو النسكافيه أو الشاي": "after_caffeine",
                "بعد التدخين": "after_smoking",
                "عند الاستحمام أو ملامسة الماء البارد": "cold_water",
                "مع الدورة الشهرية": "menstruation",
                "أثناء أو بعد الجماع": "intercourse",
            },
        },
        {
            "field": "symptoms.radiation",
            "q": "هل ينتشر الألم إلى مناطق أخرى؟ (يمكنك اختيار أكثر من إجابة)",
            "v": "multi_choice",
            "options": {
                "لا يوجد ألم": "no_pain",
                "يوجد ألم لكنه لا ينتشر": "no_radiation",
                "الذراع أو الكتف أو اليد اليسرى": "left_arm",
                "الذراع أو الكتف أو اليد اليمنى": "right_arm",
                "الظهر / بين الكتفين": "back",
                "الرقبة": "neck",
                "الفك أو الأسنان": "jaw",
                "أعلى البطن": "upper_abdomen",
                "الجهة اليسرى بشكل عام (لا أستطيع تحديدها)": "left_general",
                "الالم ثابت لا يتنقل": "non_radiating",
            },
            "depends_on": {
                "field": "symptoms.main_symptoms",
                "contains_any": ["chest_pain", "heart_pain", "stabs", "arm_radiation"],
            },
        },
        {
            "field": "symptoms.severity",
            "q": "كيف تصف شدة الأعراض عندما تحدث؟",
            "v": "choice",
            "options": {
                "بسيطة / خفيفة": "mild",
                "متوسطة / مزعجة": "moderate",
                "شديدة / قوية": "severe",
                "لا أحتمل / أشعر أنني لا أقدر على المواصلة": "unbearable",
            },
        },
    ],

    # -------------------------------------------------------------------------
    # RED_FLAG_SCREENING
    # -------------------------------------------------------------------------
    "RED_FLAG_SCREENING": [
        #revision
        {
            "field": "red_flags.exertional_relief",
            "q": "هل يزداد ألم الصدر مع المجهود ويخف مع الراحة؟",
            "v": "choice",
            "options": {
                "نعم": "yes",
                "لا": "no",
                "لست متأكداً": "not_sure",
            },
            "depends_on": {
                "field": "symptoms.main_symptoms",
                "contains_any": ["chest_pain", "heart_pain"],
            },
        },
    ],

    # -------------------------------------------------------------------------
    # FREE_TEXT
    # -------------------------------------------------------------------------
    "FREE_TEXT": [
        {
            "field": "free_text.additional",
            "q": "هل هناك أي شيء آخر تود إضافته أو شرحه عن حالتك؟ (إذا لا، اكتب \"لا\")",
            "v": "text",
        },
    ],
}
