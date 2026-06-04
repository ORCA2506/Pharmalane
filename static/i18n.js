const TRANSLATIONS = {
  en: {
    // Navbar
    "nav.home": "Home",
    "nav.symptom_checker": "Symptom Checker",
    "nav.appointments": "Appointments",
    "nav.about": "About",
    "nav.login": "Login",
    "nav.signup": "Sign Up",
    "nav.logout": "Logout",

    // Footer
    "footer.tagline": "AI-Powered Medical Recommendation System",
    "footer.disclaimer": "⚠️ For informational purposes only. Always consult a qualified doctor.",

    // Landing — Hero
    "hero.tag": "AI-Powered Healthcare Platform",
    "hero.title": "Your Personal <span class='highlight'>Medical AI</span> Assistant",
    "hero.lead": "Enter your symptoms and get instant disease predictions, personalized medicine recommendations, diet plans, and connect with real doctors via video call.",
    "hero.btn_start": "Get Started Free",
    "hero.btn_login": "Login",
    "hero.btn_symptoms": "Check Symptoms",
    "hero.btn_appointment": "Book Appointment",
    "hero.stat1": "Diseases Detected",
    "hero.stat2": "Symptoms Analyzed",
    "hero.stat3": "Accuracy Rate",
    "hero.ai_analysis": "AI Analysis",
    "hero.realtime": "Real-time prediction",
    "hero.symptoms_detected": "Symptoms detected:",
    "hero.predicted": "Predicted Disease",
    "hero.confidence": "Confidence",
    "hero.medications": "Medications",
    "hero.diet": "Diet Plan",
    "hero.doctor_available": "Doctor Available",
    "hero.personalized": "Personalized",
    "hero.found": "found",

    // Landing — Features
    "features.badge": "Features",
    "features.title": "Everything you need for better health",
    "features.subtitle": "A complete healthcare platform powered by machine learning and real doctors.",
    "features.f1_title": "AI Symptom Analysis",
    "features.f1_desc": "Our ML model trained on thousands of cases predicts diseases from your symptoms with high accuracy using SVM classification.",
    "features.f2_title": "Medicine Recommendations",
    "features.f2_desc": "Get personalized medication suggestions, dosage guidance, and precautions tailored to your predicted condition.",
    "features.f3_title": "Video Consultations",
    "features.f3_desc": "Book appointments with certified doctors and join secure video calls directly in the app.",
    "features.f4_title": "Diet & Workout Plans",
    "features.f4_desc": "Receive disease-specific diet recommendations and workout routines to support your recovery.",
    "features.f5_title": "Smart Scheduling",
    "features.f5_desc": "Book, manage, and track doctor appointments with conflict detection.",
    "features.f6_title": "Privacy First",
    "features.f6_desc": "Your health data is encrypted and stored securely following industry-standard practices.",

    // Landing — How it works
    "how.badge": "How It Works",
    "how.title": "Get results in 3 simple steps",
    "how.s1_title": "Create Account",
    "how.s1_desc": "Sign up for free in seconds. No credit card required.",
    "how.s2_title": "Enter Symptoms",
    "how.s2_desc": "Type your symptoms or use voice input. Our AI analyzes them instantly.",
    "how.s3_title": "Get Recommendations",
    "how.s3_desc": "Receive disease prediction, medicines, diet plan, and book a doctor if needed.",

    // Landing — Testimonials
    "test.badge": "Trusted By Experts",
    "test.title": "What doctors say",

    // Landing — CTA
    "cta.title": "Ready to take control of your health?",
    "cta.subtitle": "Join thousands of users who trust Medicure for smarter healthcare decisions.",
    "cta.btn_dashboard": "Go to Dashboard",
    "cta.btn_start": "Get Started — It's Free",

    // Login
    "login.title": "Sign in to your account",
    "login.email": "Email Address",
    "login.password": "Password",
    "login.btn": "Sign In",
    "login.no_account": "Don't have an account?",
    "login.create": "Create one free",

    // Register
    "reg.title": "Create your free account",
    "reg.i_am": "I am a",
    "reg.patient": "Patient",
    "reg.doctor": "Doctor",
    "reg.name": "Full Name",
    "reg.email": "Email Address",
    "reg.specialty": "Specialty",
    "reg.password": "Password",
    "reg.btn": "Create Account",
    "reg.have_account": "Already have an account?",
    "reg.signin": "Sign in",

    // Dashboard
    "dash.title": "Symptom Checker",
    "dash.subtitle": "Enter your symptoms below to get an AI-powered disease prediction and personalized recommendations.",
    "dash.label": "Enter Symptoms",
    "dash.placeholder": "e.g. headache, fever, fatigue...",
    "dash.hint": "Type a symptom and press Enter or comma to add it",
    "dash.voice": "Voice",
    "dash.listening": "Listening...",
    "dash.analyze": "Analyze Symptoms",
    "dash.results": "Analysis Results",
    "dash.predicted": "Predicted Disease",
    "dash.precautions": "Precautions",
    "dash.medications": "Recommended Medications",
    "dash.diet": "Diet Plan",
    "dash.workout": "Workout Recommendations",
    "dash.when_doctor": "When to See a Doctor",
    "dash.consult": "Want to consult a doctor?",
    "dash.consult_sub": "Book a video appointment with a specialist.",
    "dash.book_now": "Book Now",
    "dash.disclaimer": "Always consult a licensed doctor before taking any medication.",
    "dash.how_to": "How to use",
    "dash.how_desc": "Type symptoms one by one and press Enter or comma to add them as tags. Then click Analyze.",
    "dash.examples": "Example Symptoms",
    "dash.disclaimer_title": "Disclaimer",
    "dash.disclaimer_desc": "This tool is for informational purposes only and does not replace professional medical advice.",

    // Appointments
    "appt.title": "Appointments",
    "appt.subtitle": "Book video consultations with certified doctors and manage your schedule.",
    "appt.book_title": "Book Appointment",
    "appt.select_doctor": "Select Doctor",
    "appt.date": "Date",
    "appt.time": "Time",
    "appt.select_time": "Select time slot",
    "appt.reason": "Reason for Visit",
    "appt.reason_opt": "(optional)",
    "appt.reason_ph": "Briefly describe your concern...",
    "appt.confirm": "Confirm Booking",
    "appt.my": "My Appointments",
    "appt.schedule": "Your Schedule",
    "appt.join": "Join Call",
    "appt.cancel": "Cancel",
    "appt.pay": "Pay ₹500",
    "appt.empty": "No appointments yet.",
    "appt.empty_sub": "Book your first appointment with a doctor using the form.",
    "appt.status_scheduled": "Scheduled",
    "appt.status_cancelled": "Cancelled",
    "appt.status_completed": "Completed",
    "appt.status_pending": "Payment Pending",

    // Payment
    "pay.title": "Complete Payment",
    "pay.subtitle": "Secure payment to confirm your appointment",
    "pay.doctor": "Doctor",
    "pay.specialty": "Specialty",
    "pay.date": "Date",
    "pay.time": "Time",
    "pay.reason": "Reason",
    "pay.fee": "Consultation Fee",
    "pay.btn": "Pay ₹500 Securely",
    "pay.cancel": "Cancel Booking",
    "pay.secure": "256-bit SSL encrypted · Powered by Razorpay",

    // Video Call
    "call.session": "SESSION",
    "call.patient": "Patient Consultation",
    "call.host": "You are the Host",
    "call.leave": "Leave",
    "call.setup": "Set Up Google Meet",
    "call.join_meet": "Join Google Meet",
    "call.create_meet": "Create Google Meet",
    "call.copy": "Copy Meeting Link",
    "call.back": "Back to Appointments",
    "call.waiting": "Waiting for Doctor to Set Up Meeting",
    "call.waiting_sub": "The doctor hasn't created the Google Meet link yet. Please check back closer to your appointment time.",
    "call.refresh": "Refresh to Check",
    "call.ready": "Meeting is ready.",
    "call.ready_sub": "Click below to join. The doctor will admit you from the waiting room.",
  },

  hi: {
    // Navbar
    "nav.home": "होम",
    "nav.symptom_checker": "लक्षण जाँच",
    "nav.appointments": "अपॉइंटमेंट",
    "nav.about": "हमारे बारे में",
    "nav.login": "लॉगिन",
    "nav.signup": "साइन अप",
    "nav.logout": "लॉगआउट",

    // Footer
    "footer.tagline": "AI-संचालित चिकित्सा अनुशंसा प्रणाली",
    "footer.disclaimer": "⚠️ केवल जानकारी के लिए। हमेशा किसी योग्य डॉक्टर से परामर्श लें।",

    // Landing — Hero
    "hero.tag": "AI-संचालित स्वास्थ्य सेवा मंच",
    "hero.title": "आपका व्यक्तिगत <span class='highlight'>मेडिकल AI</span> सहायक",
    "hero.lead": "अपने लक्षण दर्ज करें और तुरंत बीमारी की भविष्यवाणी, व्यक्तिगत दवा सिफारिशें, डाइट प्लान पाएं और वीडियो कॉल के जरिए असली डॉक्टरों से जुड़ें।",
    "hero.btn_start": "मुफ्त शुरू करें",
    "hero.btn_login": "लॉगिन",
    "hero.btn_symptoms": "लक्षण जाँचें",
    "hero.btn_appointment": "अपॉइंटमेंट बुक करें",
    "hero.stat1": "बीमारियाँ पहचानी गईं",
    "hero.stat2": "लक्षण विश्लेषित",
    "hero.stat3": "सटीकता दर",
    "hero.ai_analysis": "AI विश्लेषण",
    "hero.realtime": "रियल-टाइम भविष्यवाणी",
    "hero.symptoms_detected": "पहचाने गए लक्षण:",
    "hero.predicted": "अनुमानित बीमारी",
    "hero.confidence": "विश्वास स्तर",
    "hero.medications": "दवाइयाँ",
    "hero.diet": "डाइट प्लान",
    "hero.doctor_available": "डॉक्टर उपलब्ध",
    "hero.personalized": "व्यक्तिगत",
    "hero.found": "मिलीं",

    // Landing — Features
    "features.badge": "विशेषताएं",
    "features.title": "बेहतर स्वास्थ्य के लिए सब कुछ",
    "features.subtitle": "मशीन लर्निंग और असली डॉक्टरों द्वारा संचालित एक पूर्ण स्वास्थ्य सेवा मंच।",
    "features.f1_title": "AI लक्षण विश्लेषण",
    "features.f1_desc": "हमारा ML मॉडल हजारों मामलों पर प्रशिक्षित है और SVM वर्गीकरण का उपयोग करके आपके लक्षणों से बीमारियों की भविष्यवाणी करता है।",
    "features.f2_title": "दवा सिफारिशें",
    "features.f2_desc": "आपकी अनुमानित स्थिति के अनुसार व्यक्तिगत दवा सुझाव, खुराक मार्गदर्शन और सावधानियाँ पाएं।",
    "features.f3_title": "वीडियो परामर्श",
    "features.f3_desc": "प्रमाणित डॉक्टरों के साथ अपॉइंटमेंट बुक करें और ऐप में सीधे सुरक्षित वीडियो कॉल में शामिल हों।",
    "features.f4_title": "डाइट और वर्कआउट प्लान",
    "features.f4_desc": "बीमारी-विशिष्ट आहार सिफारिशें और व्यायाम दिनचर्या प्राप्त करें।",
    "features.f5_title": "स्मार्ट शेड्यूलिंग",
    "features.f5_desc": "डॉक्टर अपॉइंटमेंट बुक करें, प्रबंधित करें और ट्रैक करें।",
    "features.f6_title": "गोपनीयता पहले",
    "features.f6_desc": "आपका स्वास्थ्य डेटा एन्क्रिप्टेड और सुरक्षित रूप से संग्रहीत है।",

    // Landing — How it works
    "how.badge": "यह कैसे काम करता है",
    "how.title": "3 सरल चरणों में परिणाम पाएं",
    "how.s1_title": "खाता बनाएं",
    "how.s1_desc": "सेकंडों में मुफ्त साइन अप करें। कोई क्रेडिट कार्ड आवश्यक नहीं।",
    "how.s2_title": "लक्षण दर्ज करें",
    "how.s2_desc": "अपने लक्षण टाइप करें या वॉयस इनपुट का उपयोग करें। हमारा AI तुरंत विश्लेषण करता है।",
    "how.s3_title": "सिफारिशें पाएं",
    "how.s3_desc": "बीमारी की भविष्यवाणी, दवाइयाँ, डाइट प्लान पाएं और जरूरत पड़ने पर डॉक्टर बुक करें।",

    // Landing — Testimonials
    "test.badge": "विशेषज्ञों द्वारा विश्वसनीय",
    "test.title": "डॉक्टर क्या कहते हैं",

    // Landing — CTA
    "cta.title": "अपने स्वास्थ्य पर नियंत्रण रखने के लिए तैयार हैं?",
    "cta.subtitle": "हजारों उपयोगकर्ताओं से जुड़ें जो Medicure पर भरोसा करते हैं।",
    "cta.btn_dashboard": "डैशबोर्ड पर जाएं",
    "cta.btn_start": "शुरू करें — यह मुफ्त है",

    // Login
    "login.title": "अपने खाते में साइन इन करें",
    "login.email": "ईमेल पता",
    "login.password": "पासवर्ड",
    "login.btn": "साइन इन",
    "login.no_account": "खाता नहीं है?",
    "login.create": "मुफ्त बनाएं",

    // Register
    "reg.title": "अपना मुफ्त खाता बनाएं",
    "reg.i_am": "मैं हूँ",
    "reg.patient": "मरीज",
    "reg.doctor": "डॉक्टर",
    "reg.name": "पूरा नाम",
    "reg.email": "ईमेल पता",
    "reg.specialty": "विशेषज्ञता",
    "reg.password": "पासवर्ड",
    "reg.btn": "खाता बनाएं",
    "reg.have_account": "पहले से खाता है?",
    "reg.signin": "साइन इन करें",

    // Dashboard
    "dash.title": "लक्षण जाँचकर्ता",
    "dash.subtitle": "AI-संचालित बीमारी की भविष्यवाणी और व्यक्तिगत सिफारिशें पाने के लिए नीचे अपने लक्षण दर्ज करें।",
    "dash.label": "लक्षण दर्ज करें",
    "dash.placeholder": "जैसे सिरदर्द, बुखार, थकान...",
    "dash.hint": "एक लक्षण टाइप करें और जोड़ने के लिए Enter या कॉमा दबाएं",
    "dash.voice": "आवाज़",
    "dash.listening": "सुन रहा है...",
    "dash.analyze": "लक्षणों का विश्लेषण करें",
    "dash.results": "विश्लेषण परिणाम",
    "dash.predicted": "अनुमानित बीमारी",
    "dash.precautions": "सावधानियाँ",
    "dash.medications": "अनुशंसित दवाइयाँ",
    "dash.diet": "डाइट प्लान",
    "dash.workout": "व्यायाम सिफारिशें",
    "dash.when_doctor": "डॉक्टर से कब मिलें",
    "dash.consult": "डॉक्टर से परामर्श करना चाहते हैं?",
    "dash.consult_sub": "किसी विशेषज्ञ के साथ वीडियो अपॉइंटमेंट बुक करें।",
    "dash.book_now": "अभी बुक करें",
    "dash.disclaimer": "कोई भी दवा लेने से पहले हमेशा किसी लाइसेंस प्राप्त डॉक्टर से परामर्श लें।",
    "dash.how_to": "कैसे उपयोग करें",
    "dash.how_desc": "एक-एक करके लक्षण टाइप करें और टैग के रूप में जोड़ने के लिए Enter या कॉमा दबाएं। फिर विश्लेषण करें पर क्लिक करें।",
    "dash.examples": "उदाहरण लक्षण",
    "dash.disclaimer_title": "अस्वीकरण",
    "dash.disclaimer_desc": "यह टूल केवल जानकारी के लिए है और पेशेवर चिकित्सा सलाह का विकल्प नहीं है।",

    // Appointments
    "appt.title": "अपॉइंटमेंट",
    "appt.subtitle": "प्रमाणित डॉक्टरों के साथ वीडियो परामर्श बुक करें और अपना शेड्यूल प्रबंधित करें।",
    "appt.book_title": "अपॉइंटमेंट बुक करें",
    "appt.select_doctor": "डॉक्टर चुनें",
    "appt.date": "तारीख",
    "appt.time": "समय",
    "appt.select_time": "समय स्लॉट चुनें",
    "appt.reason": "मिलने का कारण",
    "appt.reason_opt": "(वैकल्पिक)",
    "appt.reason_ph": "अपनी समस्या संक्षेप में बताएं...",
    "appt.confirm": "बुकिंग की पुष्टि करें",
    "appt.my": "मेरी अपॉइंटमेंट",
    "appt.schedule": "आपका शेड्यूल",
    "appt.join": "कॉल में शामिल हों",
    "appt.cancel": "रद्द करें",
    "appt.pay": "₹500 भुगतान करें",
    "appt.empty": "अभी तक कोई अपॉइंटमेंट नहीं।",
    "appt.empty_sub": "फॉर्म का उपयोग करके अपनी पहली अपॉइंटमेंट बुक करें।",
    "appt.status_scheduled": "निर्धारित",
    "appt.status_cancelled": "रद्द",
    "appt.status_completed": "पूर्ण",
    "appt.status_pending": "भुगतान बाकी",

    // Payment
    "pay.title": "भुगतान पूरा करें",
    "pay.subtitle": "अपॉइंटमेंट की पुष्टि के लिए सुरक्षित भुगतान",
    "pay.doctor": "डॉक्टर",
    "pay.specialty": "विशेषज्ञता",
    "pay.date": "तारीख",
    "pay.time": "समय",
    "pay.reason": "कारण",
    "pay.fee": "परामर्श शुल्क",
    "pay.btn": "₹500 सुरक्षित रूप से भुगतान करें",
    "pay.cancel": "बुकिंग रद्द करें",
    "pay.secure": "256-बिट SSL एन्क्रिप्टेड · Razorpay द्वारा संचालित",

    // Video Call
    "call.session": "सत्र",
    "call.patient": "मरीज परामर्श",
    "call.host": "आप होस्ट हैं",
    "call.leave": "छोड़ें",
    "call.setup": "Google Meet सेट करें",
    "call.join_meet": "Google Meet में शामिल हों",
    "call.create_meet": "Google Meet बनाएं",
    "call.copy": "मीटिंग लिंक कॉपी करें",
    "call.back": "अपॉइंटमेंट पर वापस जाएं",
    "call.waiting": "डॉक्टर के मीटिंग सेट करने का इंतजार",
    "call.waiting_sub": "डॉक्टर ने अभी तक Google Meet लिंक नहीं बनाया है। अपॉइंटमेंट के समय के करीब दोबारा जाँचें।",
    "call.refresh": "जाँचने के लिए रिफ्रेश करें",
    "call.ready": "मीटिंग तैयार है।",
    "call.ready_sub": "शामिल होने के लिए नीचे क्लिक करें। डॉक्टर आपको वेटिंग रूम से अनुमति देंगे।",
  }
};

function t(key) {
  const lang = localStorage.getItem('pl_lang') || 'en';
  return TRANSLATIONS[lang][key] || TRANSLATIONS['en'][key] || key;
}

function applyTranslations() {
  const lang = localStorage.getItem('pl_lang') || 'en';
  document.documentElement.lang = lang === 'hi' ? 'hi' : 'en';

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = TRANSLATIONS[lang][key] || TRANSLATIONS['en'][key];
    if (!val) return;
    if (el.getAttribute('data-i18n-attr')) {
      el.setAttribute(el.getAttribute('data-i18n-attr'), val);
    } else {
      el.innerHTML = val;
    }
  });

  // Update lang switcher button label
  const btn = document.getElementById('langSwitchBtn');
  if (btn) btn.innerHTML = lang === 'hi'
    ? '<span style="font-size:1.1rem">🇮🇳</span> हिंदी'
    : '<span style="font-size:1.1rem">🇬🇧</span> English';
}

function setLanguage(lang) {
  localStorage.setItem('pl_lang', lang);
  applyTranslations();
  // Hide popup
  const popup = document.getElementById('langPopup');
  if (popup) popup.style.display = 'none';
}

function toggleLang() {
  const current = localStorage.getItem('pl_lang') || 'en';
  setLanguage(current === 'en' ? 'hi' : 'en');
}

document.addEventListener('DOMContentLoaded', function () {
  // Show language popup only on first visit
  const chosen = localStorage.getItem('pl_lang');
  if (!chosen) {
    const popup = document.getElementById('langPopup');
    if (popup) popup.style.display = 'flex';
  } else {
    applyTranslations();
  }
});
