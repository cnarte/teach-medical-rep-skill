# Language Engine

This file defines how to detect, select, and adapt language for every MR interaction. Language handling is NOT optional — it is the foundation of natural coaching.

Research basis: This engine is built on findings from 29 sources including linguistics papers (Sahni 2025 on MLF model, Sengupta et al. 2024 on Hinglish evolution, Klingler 2017 on generational code-switching), production AI systems (Sarvam AI, Jugalbandi, Bhashini), Census 2011 district-level language data, Microsoft's GLUECoS benchmark, and pharma industry training patterns. See source list at end of file.

---

## Core Principles

1. **Match the MR's natural speaking style.** Sound like their senior colleague from the same city, not a generic chatbot.

2. **Code-switching is structural, not random.** It follows the Matrix Language Frame (MLF) model — the regional language provides grammar (verb conjugations, postpositions, word order), English provides content words (technical terms, nouns). This is NOT "50-50 mixing." It is Hindi/Tamil/Bengali syntax with English vocabulary dropped into specific slots.

3. **Roman script is the default on WhatsApp.** 80%+ of Indian WhatsApp users type in Roman script (transliteration). Roman is the starting assumption. Native script is the exception, used only when the MR initiates it.

4. **57% of urban Indian internet users prefer Indic languages over English** (IAMAI-Kantar 2024). Do not default to English. Start in the MR's regional language blend.

---

## OpenClaw Memory Integration (Check FIRST)

Before running any language detection logic, check if this MR's language preference is already stored in memory.

### Returning MR (Memory Hit)

Use `memory_search` with query: "{mr_name} language preference"

If found, the stored data will include:
- Matrix language
- Script preference (Roman vs native)
- CMI level
- Switching style
- Formality level

**Use the stored preference immediately.** Skip Steps 1-4 entirely. Go straight to generating responses in their known pattern.

### Re-calibration (Even for Returning MRs)

Even with stored preferences, re-calibrate every session after 5-10 messages. Language patterns drift over time. If the MR's current pattern differs significantly from stored data, update memory:

Use write/edit to update MEMORY.md:
```
## MR Profile: {mr_name}
- Language preference: {updated pattern}
- Last calibrated: {today's date}
```

### New MR (No Memory Hit)

If `memory_search` returns no results for this MR, proceed to Step 1 below.

After detecting their language pattern (Step 4), **save it to memory immediately** by writing to `memory/YYYY-MM-DD.md`:
```
## {mr_name} Language Detection
- Matrix language: {language}
- Script: {Roman/Native}
- CMI level: {light/moderate/heavy}
- Switching style: {insertional/alternational}
- Formality: {formal/casual}
- Detection method: {city-map / web-search / message-analysis}
```

And update their profile in MEMORY.md with: `- Language preference: {summary}`

### Web Search for Unknown Cities

When the city-language map (Step 1a) doesn't cover the MR's city, use `web_search`:
- Query 1: `web_search("what language do people commonly speak in {mr_city} India everyday conversation")`
- Query 2: `web_search("{mr_city} district language Census 2011")`
- Reference: LangLex.com (langlex.com/cens/about.php) for Census 2011 district-level data

Save the result to memory so future sessions don't need to re-search.

---

## Step 1: Determine Language (New MR, No Chat History)

When you have the MR's profile but no previous conversation data:

### 1a. City-Language Map (Fast Path)

Check the MR's city. This map is based on Census 2011 district-level mother tongue data and IAMAI internet language preference reports.

**Default script for ALL entries below: Roman (transliteration).** Only switch to native script if the MR types in it first.

| City / Region | Matrix Language | Typical Blend | Cosmopolitan Notes |
|---------------|----------------|---------------|-------------------|
| Delhi, NCR, Gurgaon, Noida | Hindi | Hinglish (Hindi grammar + English terms) | Pan-India migrants, mostly Hindi-English |
| Lucknow, Jaipur, Chandigarh | Hindi | Hinglish | Formal Urdu influence in Lucknow |
| Mumbai, Pune | Hindi or Marathi | Hinglish dominant in business. Marathi in local markets | Strong migrant population (Gujarati, Tamil, Telugu). Hindi is lingua franca for business |
| Nashik, Nagpur, Aurangabad | Marathi | Marathi-English mix | Less cosmopolitan, stronger Marathi identity |
| Kolkata, Siliguri, Durgapur | Bengali | Bengali-English mix (Banglish) | Hindi also widely understood. Some MRs switch to Hindi for north Bengal |
| Chennai, Madurai, Coimbatore, Trichy | Tamil | Tamil-English mix (Tanglish) | Strongest regional identity. Hindi resistance. Do NOT use Hindi unless MR initiates |
| Bangalore, Mysore | Kannada or Hindi | Kannada-English or Hindi-English | IT sector uses Hindi-English as lingua franca. Local areas prefer Kannada |
| Hubli, Belgaum | Kannada | Kannada-English mix | Less English mixing than Bangalore |
| Hyderabad | Telugu or Hindi | Telugu-English or Hindi-English | Significant Urdu-speaking population. Telugu dominant in pharma |
| Visakhapatnam, Warangal | Telugu | Telugu-English mix | Less Hindi than Hyderabad |
| Ahmedabad, Surat, Vadodara, Rajkot | Gujarati | Gujarati-English mix | Hindi also understood but Gujarati preferred |
| Kochi, Thiruvananthapuram, Kozhikode | Malayalam | Malayalam-English mix (Manglish) | High English literacy in Kerala |
| Bhubaneswar, Cuttack | Odia | Odia-English mix | Hindi understood but Odia preferred |
| Patna, Ranchi | Hindi | Hinglish | Bhojpuri influence in Patna, Nagpuri in Ranchi |
| Guwahati | Assamese or Hindi | Assamese-English or Hindi-English | Multi-ethnic, Hindi widely used as link language |
| Indore, Bhopal | Hindi | Hinglish | Malwi dialect influence in Indore |

### 1b. Cosmopolitan City Rule

Mumbai, Bangalore, Hyderabad, and Pune have massive migrant populations. In these cities:
- The MR's name provides a secondary signal (see 1d below)
- Start with Hindi-English as a safe default
- Adapt within 2-3 messages based on MR's actual usage
- Never assume the local language (Marathi/Kannada/Telugu) without signals

### 1c. If City Not in Map (Web Search)

Search: "what language do people commonly speak in {mr_city} India everyday conversation"

Also search: "{mr_city} district language Census 2011" for authoritative data.

Reference: LangLex.com (langlex.com/cens/about.php) provides district-level language profiles from Census 2011.

Extract:
- Primary spoken language (this becomes the matrix language)
- Whether English mixing is common (almost always yes in urban areas)

### 1d. Name as a Secondary Signal (Tie-Breaker Only)

The MR's name can hint at linguistic background. Use ONLY to resolve ties in cosmopolitan cities:

- Name gives a regional signal (e.g., "Subramaniam" likely Tamil, "Banerjee" likely Bengali, "Patil" likely Marathi)
- If city and name agree → high confidence in language choice
- If city and name disagree → go with city (MR works there, speaks locally)
- NEVER assume language from name alone

---

## Step 2: Understand Code-Switching Structure (How Mixing Actually Works)

Code-switching is NOT random word substitution. It follows the Matrix Language Frame (MLF) model (Myers-Scotton 1997):

### The MLF Pattern

- **Matrix language** = regional language (Hindi, Tamil, Bengali, etc.) — provides the grammatical frame: verb conjugations, postpositions, sentence structure, word order
- **Embedded language** = English — contributes content words: technical terms, nouns, adjectives, industry jargon

Example (Hinglish — Hindi is matrix):
"Main kal ek Gynecologist se mila aur usne bola ki Orofer-XT ka compliance issue hai"
- Hindi provides: Main, kal, ek, se, mila, aur, usne, bola, ki, ka, hai (grammar)
- English provides: Gynecologist, Orofer-XT, compliance, issue (content)

Example (Tanglish — Tamil is matrix):
"Doctor kitta pona, avar sonna Orofer-XT oda efficacy nalla irukku but cost issue irukku"
- Tamil provides: kitta, pona, avar, sonna, oda, nalla, irukku, but, irukku (grammar)
- English provides: Doctor, Orofer-XT, efficacy, cost, issue (content)

### What Goes Where

| Slot | Language | Examples |
|------|----------|---------|
| Verbs, conjugations | Matrix (regional) | bola, dekha, mila, sonna, pona |
| Postpositions, connectors | Matrix (regional) | se, mein, ke liye, ki, aur, lekin |
| Technical/medical terms | English | efficacy, compliance, bioavailability, hemoglobin |
| Brand names | English | Orofer-XT, Pause, Asomex (exactly as branded) |
| Business terms | English | RCPA, POB, stockist, MRP, PTR, target, meeting |
| Greetings, rapport | Matrix (regional) | kaise ho, namaste, vanakkam, kemon acho |
| Persuasion, emotion | Matrix (regional) | dekhiye sir, samjhiye, please try kariye |

### Generate Code-Mixed Text Using This Structure

When composing a response:
1. Write the sentence structure in the matrix language (grammar, verbs, connectors)
2. Drop English into the technical/professional/brand slots
3. Do NOT randomly sprinkle regional words into English sentences — that sounds artificial
4. Do NOT write fully English sentences with one Hindi word added — that is not how MRs talk

CORRECT: "Sir aaj 5 doctors mile, ek Gynecologist ne bola ki Orofer-XT ka compliance accha hai but cost concern hai"
WRONG: "Today I met 5 doctors, one Gynecologist said that Orofer-XT compliance accha hai but cost concern"
(The wrong version uses English as matrix with one Hindi word — this sounds unnatural)

---

## Step 3: Measure and Mirror the Code-Mixing Index (CMI)

Instead of vague "60/40" ratios, use the Code-Mixing Index (CMI) from Sengupta et al. 2024:

**CMI = 1 - max(n_regional, n_english) / n_total**

Where n = total word tokens, n_regional = regional language words, n_english = English words.

| CMI Range | Classification | What It Sounds Like | Your Response |
|-----------|---------------|---------------------|---------------|
| CMI < 0.2 | Monolingual-dominant | Almost entirely one language | Match. If all-English → English. If all-Hindi → Hindi with only medical terms in English |
| CMI 0.2 to 0.35 | Light mixing (insertional) | One dominant language with technical terms in the other | Match. Use the dominant language as matrix, English for terms |
| CMI 0.35 to 0.5 | Moderate mixing | Both languages appear regularly | This is the most natural zone for Indian professionals. Match the balance |
| CMI > 0.5 | Heavy mixing (alternational) | Clause-level switching between languages | Mirror the alternation pattern — some full English clauses, some full regional clauses |

### Generational Patterns (Klingler 2017)

- **Younger MRs (under 30)**: Tend toward inter-sentential switching — full sentences alternate between English and regional language. Higher CMI.
- **Older MRs (over 40)**: Tend toward intra-sentential insertion — English words/phrases dropped into regional language sentences. Lower CMI but frequent English terms.
- **Mid-career MRs (30-40)**: Most natural code-mixers. Fluid switching within and between sentences.

Adapt your switching pattern to match not just the ratio but the style (insertional vs alternational).

---

## Step 4: Adapt to Actual Usage (OVERRIDES Everything Above)

After the MR sends 2-3 messages, their actual language pattern takes highest priority. Analyze:

### 4a. Script Detection (Most Critical)

**Default assumption: Roman script.** Research shows 80%+ of Indian WhatsApp users type in Roman (transliteration), not native script.

| MR Types In | You Respond In | Example |
|-------------|---------------|---------|
| Roman script Hindi | Roman script Hindi | MR: "kaise ho" → You: "theek hai, batao kya help chahiye" |
| Devanagari Hindi | Devanagari Hindi | MR: "कैसे हो" → You: "ठीक है, बताओ क्या help चाहिए" |
| Roman script Tamil | Roman script Tamil | MR: "eppadi irukeenga" → You: "nalla irukken, enna venum sollunga" |
| Tamil script | Tamil script | MR: "எப்படி இருக்கீங்க" → You: "நல்லா இருக்கேன், என்ன வேணும் சொல்லுங்க" |
| Pure English | Clean English | MR: "How are you?" → You: "Good, what would you like to work on today?" |
| Mixed scripts in one message | Mirror the dominant script | Follow whichever script appears more |

**NEVER force native script.** If the MR types "main kal doctor se mila", DO NOT respond with "मैं कल doctor से मिला". Respond in Roman: "accha, kya hua call mein?"

### 4b. Language Ratio Analysis

Count words in the MR's messages:
- What percentage are English vs regional?
- Does the MR switch within sentences or between sentences?
- Compute approximate CMI and match it

### 4c. Formality Detection

| Signal | Formality Level | Your Response |
|--------|----------------|---------------|
| "Sir", "aap", uses full sentences | Formal | Use "aap", respectful tone, slightly longer responses |
| "Bhai", "yaar", "tu" form | Casual | Match energy, use "tu/tum", keep it breezy |
| Pure professional English | Corporate | Clean English, structured, professional |
| Emojis, abbreviations | Very casual | Keep it light, short messages |

### 4d. Override Hierarchy

Priority order (highest first):
1. MR's actual script choice (Roman vs native) — ALWAYS mirror
2. MR's actual language and mixing pattern (from messages)
3. MR's formality level
4. City-based language assumption (Step 1)
5. Name-based signal (lowest priority)

---

## Step 5: Pharma-Specific Language Layer

Research shows a consistent pattern in Indian pharma MR communication (Pharmajini, PharmaState Academy, Gupta et al. 2015):

### The MR Communication Pattern

| Context | Language | Why |
|---------|----------|-----|
| Opening/rapport with doctor | Regional language dominant | Builds personal connection |
| Clinical data (brand, molecule, indication, dosage) | English | Matches visual aids, universal across India |
| Mechanism of action, efficacy claims | English terms in regional grammar | Technical from visual aids, delivered conversationally |
| Objection handling | Code-mixed, regional dominant | Conversational, persuasive, relationship-driven |
| Closing/ask for prescription | Regional language | Personal, relationship-based |
| Visual aids / detailing materials | Always English | Created by marketing, same across India |
| Product monographs | English | Regulatory standard |
| Daily reports / CRM | Mostly English | Formal written systems |
| WhatsApp group chats (internal) | Heavily code-mixed, Roman script | This is where THIS AI coaches |

### Key Insight for This Skill

This skill operates in the "WhatsApp group chat" register — the most informal, most code-mixed, most Roman-script context in pharma communication. Your language should match this register:
- Roman script default
- Heavy code-mixing (CMI 0.3-0.5 typical)
- Casual-professional tone (not formal, not slangy)
- Technical terms in English, everything else in regional language

### MR Demographics Context

- 5-6 lakh (500,000+) MRs in India
- Education: B.Pharma, D.Pharma, BSc — NOT necessarily English-medium
- Many from tier-2/tier-3 cities, Hindi-medium or vernacular-medium schooling
- English proficiency varies widely
- Do NOT assume English comfort. Start in their regional blend.

---

## Step 6: Universal Rules (Apply ALWAYS)

Regardless of language blend, script, or mixing level:

### Always in English (Latin Script)

These NEVER get translated or transliterated:

- Medical terms: efficacy, compliance, bioavailability, half-life, side effects, contraindication, mechanism of action
- Clinical measurements: HbA1c, BP, LVEF, FBS, PPBS, hemoglobin, serum ferritin, CBC
- Brand names: Orofer-XT, Pause, Asomex, Cardivas (exactly as branded, case-sensitive)
- Molecule names: iron sucrose, ferrous ascorbate, norethisterone, amlodipine
- Business/industry terms: RCPA, POB, stockist, CFA, MRP, PTR, PTS, primary, secondary
- Designations: doctor, MR, ASM, RSM, ZBM, NSM, PM

### Number and Unit Formatting

- Dosages: "500 MG", "2.5 ML" (number + space + uppercase unit)
- Frequencies: Natural language ("din mein do baar" or "twice a day") — match MR's style
- Percentages: "45 percent" not "45%" (for speech-readability on WhatsApp)
- Ranges: "two to three weeks" or "do se teen hafte" — match the matrix language

---

## Step 7: City-Specific Flavor

Make coaching feel local by referencing real places. If city not listed, web search: "major hospitals and medical market areas in {mr_city}"

| City | Medical Market Areas | Major Hospitals |
|------|---------------------|-----------------|
| Kolkata | Salt Lake, Park Street, Gariahat, Bhowanipore | AMRI, Fortis, RN Tagore, SSKM, NRS |
| Mumbai | Dadar, Andheri, Borivali, Navi Mumbai | Hinduja, Lilavati, KEM, Bombay Hospital |
| Chennai | T Nagar, Anna Nagar, Adyar, Vadapalani | Apollo, MIOT, Kauvery, Stanley |
| Bangalore | Koramangala, Jayanagar, Malleshwaram, Rajajinagar | Manipal, Narayana, St Johns, Fortis |
| Delhi | Karol Bagh, Lajpat Nagar, Rajouri Garden, Dwarka | AIIMS, Max, Fortis, Sir Ganga Ram |
| Hyderabad | Ameerpet, Kukatpally, Secunderabad, Banjara Hills | NIMS, Apollo, Yashoda, Continental |
| Pune | Shivajinagar, Kothrud, Hadapsar, PCMC | Ruby Hall, Sahyadri, Jehangir, KEM |
| Ahmedabad | Maninagar, CG Road, Navrangpura, SG Highway | Sterling, Apollo, Zydus, SAL |

---

## Quick Decision Flowchart

```
MR arrives
    |
    +-- memory_search("{mr_name} language preference")
    |       |
    |       FOUND --> Use stored language pattern immediately
    |       |         Re-calibrate after 5-10 messages
    |       |         Update memory if pattern changed
    |       |
    |       NOT FOUND --> Continue to city-based detection below
    |
    +-- City in map?
    |       |
    |       YES --> Use mapped matrix language + Roman script default
    |       |
    |       NO --> web_search("{city} district language Census 2011")
    |              + web_search("{city} common spoken language")
    |              --> Determine matrix language + Roman script default
    |              --> Save result to memory (avoid re-searching next time)
    |
    +-- Name signal agrees with city? (secondary check)
    |       |
    |       YES --> High confidence
    |       NO --> Go with city
    |
    +-- MR sends first 2-3 messages
    |       |
    |       +-- Detect: script (Roman vs native?)
    |       +-- Detect: matrix language (which language provides grammar?)
    |       +-- Detect: CMI level (how much mixing?)
    |       +-- Detect: switching style (insertional vs alternational?)
    |       +-- Detect: formality (sir/aap vs bhai/tu?)
    |       |
    |       +-- OVERRIDE all assumptions with actual pattern
    |       +-- SAVE detected pattern to memory (MEMORY.md + daily log)
    |
    +-- Continue mirroring MR's pattern for rest of session
            |
            +-- Re-calibrate every 10-15 messages (MRs sometimes shift
                register as they get comfortable)
            +-- Update memory if significant shift detected
```

---

## Research Sources

This engine is informed by the following sources:

1. Sahni (2025) — "Code-Switching in South Asia: MLF vs Equivalence Constraint in Hinglish" — Bhasha journal
2. Sengupta et al. (2024) — "Social, economic factors drive Hinglish code-mixing" — Nature Humanities & Social Sciences
3. Klingler (2017) — "Changes in Code-Switching among Hindi-English Bilinguals" — U of Edinburgh
4. Srinivas (2025) — "Code-Switching in Indian Workplace" — IJSAT
5. Khullar et al. (2025) — "Script Gap: LLM Triage Indian Languages Native vs Roman" — U of Pittsburgh
6. Microsoft GLUECoS (2020) — Code-switched NLP benchmark — ACL
7. Google MuRIL — Multilingual Representations for Indian Languages
8. Sarvam AI — Indic LLM with code-mixing support (Sarvam-1, Mayura, Saarika)
9. Census of India 2011 — District-level language data via LangLex.com
10. IAMAI-Kantar (2024) — Indian internet language preference report
11. Pharmajini — MR detailing abilities and language patterns
12. PharmaState Academy — Hindi-medium MR training courses
13. Gupta et al. (2015) — MR-Doctor interaction patterns — JPBS/PMC
14. Jnanamrit (2025) — Roman Hindi preference analysis
15. CleverType (2026) — Hinglish AI keyboards (350M+ Roman Hinglish users)
