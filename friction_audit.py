from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components
from streamlit.errors import StreamlitSecretNotFoundError

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    Credentials = None


RESULTS_FILE = Path("friction_audit_results.csv")
APP_VERSION = "practice-friction-finder-polish-v1"
LOGGER = logging.getLogger(__name__)
GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CSV_COLUMNS = [
    "timestamp",
    "name_optional",
    "email_optional",
    "practice_name_optional",
    "website_optional",
    "role",
    "practice_stage",
    "answers_json",
    "ai_attitude",
    "primary_friction_area",
    "secondary_friction_area",
    "result_accuracy",
    "hardest_part_free_text",
    "already_tried_free_text",
    "magic_wand_free_text",
    "conversation_opt_in",
    "follow_up_email",
]

PRACTICE_STAGES = [
    "I'm preparing to start or newly getting started",
    "I'm building a solo private practice",
    "I have a steady solo practice",
    "I run or help run a group practice",
    "I'm not sure / other",
]

AI_ATTITUDE_OPTIONS = {
    "I'm excited about it and already experimenting": [],
    "I'm curious, but cautious": ["ai_uncertainty"],
    "I don't know enough yet to have a strong opinion": ["ai_uncertainty"],
    "I'm worried about ethics, privacy, or clinical boundaries": [
        "ai_uncertainty",
        "ai_uncertainty",
    ],
    "I don't think AI belongs in therapy at all": ["ai_uncertainty"],
}

RESULT_COPY = {
    "client_volume": {
        "title": "Attracting enough clients",
        "pattern_interpretation": [
            "Based on your answers, the biggest strain may be the pressure of not having enough steady inquiries. That can create a very specific kind of background noise: even when you are doing good clinical work, part of your mind is still scanning for where the next client will come from.",
            "For therapists, this often feels especially tender because the work itself is relational and meaningful. You may not want to spend your week chasing visibility, watching numbers, or wondering whether the quiet patches mean something about your skill. Usually, this pattern is less about your ability as a therapist and more about whether enough right people can find and understand you at the right moment.",
            "The useful question may not be, 'How do I market harder?' It may be, 'What would make my practice easier to discover, understand, and take the next step with?'",
        ],
        "what_it_might_cost_you": "This can cost you steadiness, planning energy, and confidence. It can also make every marketing task feel urgent instead of intentional.",
        "low_pressure_actions": [
            "Look at the last 30 days and note where each inquiry came from.",
            "Choose one visibility path to tend gently for two weeks instead of trying five things at once.",
            "Make sure your website or profile has one clear next step for someone who is ready to reach out.",
        ],
        "reassurance": "This does not mean you are doing anything wrong. It may simply mean your path to being found needs more support than it has had.",
    },
    "client_fit": {
        "title": "Attracting better-fit clients",
        "pattern_interpretation": [
            "Your answers suggest that the issue may not only be whether people are reaching out. It may be whether the right people are recognizing themselves in your practice before they contact you.",
            "This can feel confusing because, from the outside, inquiries can look like success. But if too many consults feel mismatched, if people misunderstand your work, or if you keep explaining the same boundaries and fit issues, the practice can start to feel more draining than it should.",
            "Better-fit client attraction usually starts before the consult. It lives in the specificity of your language, the situations you name, the expectations you set, and the quiet signals that help someone think, 'This therapist understands what I am looking for.'",
        ],
        "what_it_might_cost_you": "This can cost you emotional bandwidth, consult time, and the sense of ease that comes from doing the work you are best suited to do.",
        "low_pressure_actions": [
            "Write down the words your best-fit clients use when they describe why they came to therapy.",
            "Review your homepage or directory profile for phrases that could fit almost any therapist.",
            "Name one or two client situations you are especially equipped to support.",
        ],
        "reassurance": "This does not mean you need to become narrow or exclusionary. It means clarity can be a kindness to both you and the people deciding whether to reach out.",
    },
    "messaging_positioning": {
        "title": "Website and messaging clarity",
        "pattern_interpretation": [
            "The pattern here looks like a clarity issue more than a motivation issue. You may know what you do in the room, but translating that into website language, directory copy, or a simple explanation of your practice may feel strangely hard.",
            "A lot of therapists end up with language that is accurate but too broad to be useful. Words like supportive, compassionate, evidence-based, and client-centered may be true, but they do not always help a potential client understand why you are the right person for what they are carrying.",
            "The opportunity is not to sound more polished. It is to sound more recognizable. Clear messaging helps people feel oriented: what you help with, who you are a good fit for, what the process may feel like, and what to do next.",
        ],
        "what_it_might_cost_you": "Unclear messaging can cost you right-fit inquiries, referral confidence, and a lot of time rewriting the same few sentences without ever feeling done.",
        "low_pressure_actions": [
            "Read your homepage out loud and notice where it starts to feel abstract.",
            "Replace one broad sentence with a more specific client-centered one.",
            "Ask a trusted person what they think you help with after reading your site for 60 seconds.",
        ],
        "reassurance": "This does not mean your work is unclear. It may mean the public-facing language has not caught up to the depth and specificity of what you actually do.",
    },
    "marketing_discomfort": {
        "title": "Marketing discomfort",
        "pattern_interpretation": [
            "Your answers point to a very common private practice tension: wanting people to find you without wanting to feel like you are performing, selling, or turning your care into content.",
            "For therapists, marketing can bump into ethics, identity, privacy, humility, and a wish not to make big promises. That discomfort can lead to avoidance, but the avoidance can then create more pressure when the practice needs visibility.",
            "The helpful move may be to stop asking, 'How do I market like everyone else?' and start asking, 'What kind of visibility feels honest enough that I could actually sustain it?'",
        ],
        "what_it_might_cost_you": "This can cost you consistency, visibility, and peace of mind. It can also make every public-facing task feel heavier than the task itself.",
        "low_pressure_actions": [
            "Define what ethical, low-pressure visibility means in your own words.",
            "Pick one marketing task that feels honest enough to repeat.",
            "Create a short list of topics you can speak about without feeling like you are selling.",
        ],
        "reassurance": "This does not mean you are bad at marketing. It may mean you need a way of being visible that does not ask you to betray your own temperament.",
    },
    "admin_burden": {
        "title": "Admin burden",
        "pattern_interpretation": [
            "Based on your answers, it does not sound like therapy itself is the problem. It sounds like your attention is getting pulled into all the small things surrounding the work: messages, forms, follow-ups, billing, scheduling, notes, and decisions that never fully feel done.",
            "A lot of therapists describe this as feeling busy all day without feeling like they actually spent the day doing the work they became a therapist to do. The hard part is that most of these tasks are small enough to seem manageable on their own, but together they take up a surprising amount of mental space.",
            "The pattern to notice is not just how much admin exists. It is whether admin keeps fragmenting your day, interrupting your clinical presence, or making the practice feel harder to hold than it needs to be.",
        ],
        "what_it_might_cost_you": "This can cost you focus, recovery time, and the grounded feeling you need to do good clinical work without carrying the whole practice in your head.",
        "low_pressure_actions": [
            "List the three admin tasks that interrupt your week the most.",
            "Choose one repeated message or process to turn into a simple template.",
            "Block one small admin reset window instead of letting admin scatter across the day.",
        ],
        "reassurance": "This does not mean you are disorganized. It may mean the practice has outgrown the amount of invisible labor you can comfortably absorb.",
    },
    "ai_uncertainty": {
        "title": "AI uncertainty",
        "pattern_interpretation": [
            "Your answers suggest that AI may feel like both a possibility and a question mark. You might see how it could reduce admin or help with blank-page tasks, while also feeling cautious about ethics, privacy, clinical boundaries, accuracy, and what should remain deeply human.",
            "That hesitation makes sense. Therapy is not a generic business context. The stakes are relational, confidential, and clinical. For many therapists, the question is not whether AI is impressive. It is whether there is a bounded, responsible way to use it without compromising care.",
            "A useful starting place may be separating AI for clinical care from AI for practice support. You do not have to decide everything at once. You can begin by naming what is off-limits, what is low-risk, and what would need more guidance.",
        ],
        "what_it_might_cost_you": "Uncertainty can cost you time and clarity. You may either avoid tools that could help with low-risk admin or feel pressured to experiment faster than feels responsible.",
        "low_pressure_actions": [
            "Write down what you would never want AI to touch in your practice.",
            "Choose one low-risk use case, like drafting non-client-facing admin language.",
            "Make a short list of questions you would need answered before using AI more.",
        ],
        "reassurance": "This does not mean you are behind. Caution can be a strength when it helps you define thoughtful boundaries instead of getting swept up in hype.",
    },
    "consultation_conversion": {
        "title": "Intake and consultation conversion",
        "pattern_interpretation": [
            "The pattern we noticed is around the space between someone reaching out and actually becoming a client. That middle step can hold a lot: response timing, consult flow, fee conversations, fit language, forms, scheduling, and the small moments where someone either feels oriented or drifts away.",
            "This can be frustrating because the interest is there, but it does not always turn into a booked session. Sometimes the issue is not demand. It is that the path from inquiry to first appointment asks too much of the potential client or too much improvising from you.",
            "A clearer intake path can make the process feel calmer for both sides. It does not have to be rigid or salesy. It just needs to help people understand what happens next and help you assess fit without reinventing the wheel every time.",
        ],
        "what_it_might_cost_you": "This can cost you good-fit clients, consult energy, and confidence in a part of the practice that should feel supportive instead of leaky.",
        "low_pressure_actions": [
            "Review your last five inquiries and note where each person stopped or booked.",
            "Create a simple consult outline so every call has a clear beginning, middle, and next step.",
            "Clarify what happens after someone submits your contact form.",
        ],
        "reassurance": "This does not mean you need to pressure people. It may mean your process needs to carry more of the orientation so you do not have to.",
    },
    "referral_dependence": {
        "title": "Referral dependence",
        "pattern_interpretation": [
            "Your answers suggest that referrals may be doing a lot of the heavy lifting in your practice. That can be a beautiful thing. Referrals often come from trust, reputation, and relationships you have built over time.",
            "The strain shows up when referrals become the only reliable path. If a key referral source slows down, changes roles, or sends people who are not quite the right fit, the practice can start to feel less steady than it looks from the outside.",
            "The goal is not to abandon referrals. It is to make sure they are part of a healthier mix, so your practice is not dependent on a few people or platforms to keep the right clients coming in.",
        ],
        "what_it_might_cost_you": "Referral dependence can cost you predictability, right-fit control, and the ability to shape your practice intentionally over time.",
        "low_pressure_actions": [
            "Map your current referral sources and mark which ones you can actually influence.",
            "Identify one non-referral path where clients could discover you directly.",
            "Update one public profile so it reflects your current best-fit work.",
        ],
        "reassurance": "This does not mean referrals are a problem. It means your practice may deserve more than one doorway.",
    },
    "group_practice_growth": {
        "title": "Group practice growth and systems",
        "pattern_interpretation": [
            "Your answers point toward the friction that often appears when a practice grows beyond what one person can personally hold. The practice may be working, but too much may still depend on your memory, judgment, availability, or ability to smooth things over.",
            "Group practice growth can bring a strange mix of pride and pressure. You may be supporting clinicians, managing operations, thinking about client flow, trying to protect clinical quality, and still being pulled into decisions that should probably have a clearer home.",
            "This pattern is often less about needing to work harder and more about needing the practice to become more legible: clearer roles, repeated processes, shared language, and systems that reduce the amount of invisible translation you do every day.",
        ],
        "what_it_might_cost_you": "This can cost you leadership energy, consistency, and the ability to think strategically because the day-to-day keeps asking for your direct attention.",
        "low_pressure_actions": [
            "Name the decision or task that still depends too much on you.",
            "Document one repeated process in plain language.",
            "Look for the place where a clearer role, template, or expectation would reduce back-and-forth.",
        ],
        "reassurance": "This does not mean growth was a mistake. It may mean the systems need to mature alongside the care you are trying to provide.",
    },
}

QUESTIONS = [
    {
        "prompt": "When you think about your practice lately, what has been taking the most energy?",
        "options": {
            "Finding enough of the right clients": [
                "client_volume",
                "client_fit",
            ],
            "Keeping up with everything outside the therapy room": [
                "admin_burden"
            ],
            "Explaining what I do in a way that feels clear and true": [
                "messaging_positioning",
                "marketing_discomfort",
            ],
            "Creating systems so the practice does not rely on me remembering everything": [
                "group_practice_growth"
            ],
            "I'm not sure yet": [],
        },
    },
    {
        "prompt": "When you think about your website or directory profile, what feels most true?",
        "options": {
            "It exists, but I am not sure it says what I really do": [
                "messaging_positioning"
            ],
            "It brings people in, but not always the right people": [
                "client_fit",
                "messaging_positioning",
            ],
            "I rarely touch it because I never know what to say": [
                "marketing_discomfort",
                "messaging_positioning",
            ],
            "It is not the main issue right now": [],
        },
    },
    {
        "prompt": "Which sentence feels closest to what you've actually thought lately?",
        "options": {
            "I need more people to find me.": ["client_volume"],
            "I need the right people to understand why I'm a fit.": [
                "client_fit",
                "messaging_positioning",
            ],
            "I wish the practice felt less mentally scattered.": ["admin_burden"],
            "I know things are working, but they take more energy than they should.": [
                "admin_burden",
                "group_practice_growth",
            ],
            "I'm not sure yet.": [],
        },
    },
    {
        "prompt": "Where do you lose the most energy outside the therapy room?",
        "options": {
            "Answering messages, scheduling, forms, billing, or follow-up": [
                "admin_burden"
            ],
            "Trying to explain my work clearly": ["messaging_positioning"],
            "Putting myself out there in any public way": ["marketing_discomfort"],
            "Managing people, processes, or handoffs": [
                "group_practice_growth",
                "admin_burden",
            ],
        },
    },
    {
        "prompt": "What tends to happen after someone reaches out?",
        "options": {
            "A lot of people do not respond or do not book": [
                "consultation_conversion"
            ],
            "The consult call sometimes feels awkward or hard to steer": [
                "consultation_conversion",
                "marketing_discomfort",
            ],
            "They book, but I later realize the fit is not ideal": [
                "client_fit",
                "consultation_conversion",
            ],
            "This part feels pretty steady": [],
        },
    },
    {
        "prompt": "How does marketing your practice usually feel?",
        "options": {
            "Exposed, salesy, or just not like me": ["marketing_discomfort"],
            "Fine in theory, but I do not know what to focus on": [
                "marketing_discomfort",
                "client_volume",
            ],
            "I mostly rely on referrals so I do not have to think about it much": [
                "referral_dependence",
                "marketing_discomfort",
            ],
            "Manageable enough right now": [],
        },
    },
    {
        "prompt": "If referrals slowed down for a month or two, what would you feel?",
        "options": {
            "Honestly, nervous": ["referral_dependence", "client_volume"],
            "A little exposed, but I have a few other paths": [
                "referral_dependence"
            ],
            "Mostly okay; clients find me in several ways": [],
            "Not relevant to my current practice stage": [],
        },
    },
    {
        "prompt": "What feels hardest about attracting the right clients?",
        "options": {
            "Knowing how to describe who I help without sounding too narrow": [
                "client_fit",
                "messaging_positioning",
            ],
            "Helping people understand why they should choose me": [
                "messaging_positioning",
                "client_fit",
            ],
            "Getting in front of enough people at all": ["client_volume"],
            "I am not sure fit is the main issue": [],
        },
    },
    {
        "prompt": "If you own or help run a group practice, what feels most strained? If not, choose the closest fit.",
        "options": {
            "Keeping systems clear as more people are involved": [
                "group_practice_growth"
            ],
            "Making sure the practice has a clear shared message": [
                "group_practice_growth",
                "messaging_positioning",
            ],
            "Finding enough right-fit clients for more than just me": [
                "group_practice_growth",
                "client_volume",
                "client_fit",
            ],
            "I am solo and this does not apply much": [],
        },
    },
    {
        "prompt": "What do you most wish felt lighter by this time next month?",
        "options": {
            "The pressure of needing more clients": ["client_volume"],
            "The mental load of admin and follow-through": ["admin_burden"],
            "The uncertainty around what to say publicly": [
                "messaging_positioning",
                "marketing_discomfort",
            ],
            "The worry that growth is making the practice messier": [
                "group_practice_growth"
            ],
        },
    },
    {
        "prompt": "Which sentence sounds most like something you might say privately?",
        "options": {
            "I know I am good at the work, but I do not know how to make the practice easier to find.": [
                "client_volume",
                "marketing_discomfort",
            ],
            "I am tired of explaining what I do in a way that still feels vague.": [
                "messaging_positioning"
            ],
            "I get interest, but the fit or follow-through is inconsistent.": [
                "client_fit",
                "consultation_conversion",
            ],
            "The practice is working, but it takes more energy to run than it should.": [
                "admin_burden",
                "group_practice_growth",
            ],
        },
    },
]


def ensure_csv_schema() -> None:
    if not RESULTS_FILE.exists():
        return

    with RESULTS_FILE.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        existing_columns = reader.fieldnames or []

    if existing_columns == CSV_COLUMNS:
        return

    migrated_rows = []
    for row in rows:
        migrated_rows.append(
            {
                "timestamp": row.get("timestamp", ""),
                "name_optional": row.get("name_optional", ""),
                "email_optional": row.get("email_optional", ""),
                "practice_name_optional": row.get("practice_name_optional", ""),
                "website_optional": row.get("website_optional", ""),
                "role": row.get("role", ""),
                "practice_stage": row.get("practice_stage", ""),
                "answers_json": row.get("answers_json", row.get("answers", "")),
                "ai_attitude": row.get("ai_attitude", ""),
                "primary_friction_area": row.get("primary_friction_area", ""),
                "secondary_friction_area": row.get("secondary_friction_area", ""),
                "result_accuracy": row.get("result_accuracy", ""),
                "hardest_part_free_text": row.get("hardest_part_free_text", ""),
                "already_tried_free_text": row.get("already_tried_free_text", ""),
                "magic_wand_free_text": row.get("magic_wand_free_text", ""),
                "conversation_opt_in": row.get("conversation_opt_in", ""),
                "follow_up_email": row.get("follow_up_email", ""),
            }
        )

    with RESULTS_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(migrated_rows)


def google_sheets_ready() -> bool:
    try:
        service_account = st.secrets.get("gcp_service_account")
        sheet_config = st.secrets.get("google_sheet")
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        message = "Google Sheets is not configured; using local CSV only."
        st.session_state["sheets_status"] = message
        LOGGER.info(message)
        return False

    if not service_account or not sheet_config:
        message = "Google Sheets secrets are incomplete; using local CSV only."
        st.session_state["sheets_status"] = message
        LOGGER.info(message)
        return False

    if not sheet_config.get("spreadsheet_id"):
        message = "Google Sheets spreadsheet_id is missing; using local CSV only."
        st.session_state["sheets_status"] = message
        LOGGER.info(message)
        return False

    st.session_state["sheets_status"] = "Google Sheets is configured."
    return True


def column_letter(column_number: int) -> str:
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


@st.cache_resource(show_spinner=False)
def get_google_worksheet():
    if gspread is None or Credentials is None:
        raise RuntimeError(
            "Google Sheets dependencies are not installed. Run `pip install -r requirements.txt`."
        )

    service_account_info = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=GOOGLE_SHEETS_SCOPES,
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(st.secrets["google_sheet"]["spreadsheet_id"])
    worksheet_name = st.secrets["google_sheet"].get("worksheet_name", "Responses")

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=1000,
            cols=len(CSV_COLUMNS),
        )

    header = worksheet.row_values(1)
    if header != CSV_COLUMNS:
        if not header:
            worksheet.append_row(CSV_COLUMNS)
        else:
            worksheet.update("1:1", [CSV_COLUMNS])

    return worksheet


def append_to_google_sheet(row: dict[str, str]) -> None:
    if not google_sheets_ready():
        return

    try:
        worksheet = get_google_worksheet()
        worksheet.append_row(
            [row.get(column, "") for column in CSV_COLUMNS],
            value_input_option="USER_ENTERED",
        )
    except Exception as error:
        st.session_state["sheets_error"] = str(error)


def update_google_sheet_row(timestamp: str, updates: dict[str, str]) -> None:
    if not google_sheets_ready():
        return

    try:
        worksheet = get_google_worksheet()
        timestamp_column = CSV_COLUMNS.index("timestamp") + 1
        cell = worksheet.find(timestamp, in_column=timestamp_column)
        if not cell:
            return

        current_values = worksheet.row_values(cell.row)
        current_values += [""] * (len(CSV_COLUMNS) - len(current_values))
        row = dict(zip(CSV_COLUMNS, current_values))
        row.update(updates)

        last_column = column_letter(len(CSV_COLUMNS))
        worksheet.update(
            f"A{cell.row}:{last_column}{cell.row}",
            [[row.get(column, "") for column in CSV_COLUMNS]],
        )
    except Exception as error:
        st.session_state["sheets_error"] = str(error)


def score_answers(
    answers: dict[str, str], ai_attitude: str
) -> Tuple[str, Optional[str], Counter]:
    scores: Counter = Counter()

    for index, selected in answers.items():
        question = QUESTIONS[int(index)]
        for category in question["options"][selected]:
            scores[category] += 1

    for category in AI_ATTITUDE_OPTIONS.get(ai_attitude, []):
        scores[category] += 1

    if not scores:
        return "messaging_positioning", None, scores

    ranked = scores.most_common()
    primary = ranked[0][0]
    secondary = None

    if len(ranked) > 1:
        top_score = ranked[0][1]
        second_score = ranked[1][1]
        if second_score >= max(2, top_score - 1):
            secondary = ranked[1][0]

    return primary, secondary, scores


def save_result(row: dict[str, str]) -> None:
    ensure_csv_schema()
    file_exists = RESULTS_FILE.exists()

    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    append_to_google_sheet(row)


def update_result_fields(timestamp: str, updates: dict[str, str]) -> None:
    if RESULTS_FILE.exists():
        ensure_csv_schema()

        with RESULTS_FILE.open("r", newline="", encoding="utf-8") as csv_file:
            rows = list(csv.DictReader(csv_file))

        for row in reversed(rows):
            if row.get("timestamp") == timestamp:
                row.update(updates)
                break

        with RESULTS_FILE.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    update_google_sheet_row(timestamp, updates)


def render_result(primary: str, secondary: Optional[str], practice_stage: str) -> None:
    primary_copy = RESULT_COPY[primary]

    st.header("Here's the pattern we noticed...")
    st.subheader(primary_copy["title"])

    if practice_stage:
        st.caption(
            f"We read this through the lens of where your practice is right now: {practice_stage}."
        )

    for paragraph in primary_copy["pattern_interpretation"]:
        st.write(paragraph)

    if secondary:
        secondary_copy = RESULT_COPY[secondary]
        st.subheader("A secondary pattern also showed up")
        st.write(
            f"There was also some signal around {secondary_copy['title'].lower()}. "
            f"That may mean this is not one isolated pain point. It may be connected "
            f"to another part of how your practice is being found, understood, or held."
        )

    st.subheader("What this might be costing you")
    st.write(primary_copy["what_it_might_cost_you"])

    st.subheader("A few low-pressure things to try")
    for action in primary_copy["low_pressure_actions"]:
        st.markdown(f"- {action}")

    st.subheader("This does not mean you are doing anything wrong")
    st.write(primary_copy["reassurance"])
    st.caption(
        "This is not a diagnosis or business prescription. It is a reflection tool: a way to notice where the work around the work may be asking for attention."
    )


st.set_page_config(page_title="Practice Friction Finder", page_icon="PF")

st.markdown(
    """
    <style>
    :root {
        --cream: #f7f1e7;
        --paper: #fffaf1;
        --sage: #d9ddcc;
        --ink: #26342f;
        --muted: #6f6a5f;
        --terracotta: #b86f52;
        --terracotta-dark: #8d4f3b;
        --line: #e5d9c9;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(184, 111, 82, 0.14), transparent 32rem),
            linear-gradient(180deg, var(--cream), #f3eadc 100%);
        color: var(--ink);
    }

    .block-container {
        max-width: 880px;
        padding-top: 3.5rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: var(--ink);
        letter-spacing: 0;
    }

    p, li, label, .stMarkdown, .stCaption {
        color: var(--ink);
    }

    div[data-testid="stForm"] {
        background: rgba(255, 250, 241, 0.84);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1.4rem 1.5rem 1.6rem;
        box-shadow: 0 18px 50px rgba(38, 52, 47, 0.08);
    }

    section[data-testid="stSidebar"] {
        background: var(--paper);
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-baseweb="select"] > div {
        background-color: #fffdf8;
        border-color: var(--line);
        color: var(--ink);
        border-radius: 10px;
    }

    div[role="radiogroup"] {
        background: rgba(217, 221, 204, 0.24);
        border: 1px solid rgba(229, 217, 201, 0.8);
        border-radius: 14px;
        padding: 0.65rem 0.8rem;
    }

    .stButton > button,
    div[data-testid="stFormSubmitButton"] button {
        background: var(--terracotta);
        color: #fffaf1;
        border: 1px solid var(--terracotta-dark);
        border-radius: 999px;
        padding: 0.65rem 1.25rem;
        font-weight: 700;
        box-shadow: 0 10px 24px rgba(141, 79, 59, 0.18);
    }

    .stButton > button:hover,
    div[data-testid="stFormSubmitButton"] button:hover {
        background: var(--terracotta-dark);
        color: #fffaf1;
        border-color: var(--terracotta-dark);
    }

    hr {
        border-color: var(--line);
    }

    .hero {
        background: rgba(255, 250, 241, 0.72);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 2rem 2.1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 18px 50px rgba(38, 52, 47, 0.07);
    }

    .eyebrow {
        color: var(--terracotta-dark);
        font-size: 0.82rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }

    .hero h1 {
        font-size: 3rem;
        line-height: 1.04;
        margin: 0 0 0.75rem;
    }

    .subtitle {
        color: var(--muted);
        font-size: 1.15rem;
        line-height: 1.6;
        margin-bottom: 0.75rem;
    }

    .soft-note {
        color: var(--muted);
        font-size: 0.96rem;
        line-height: 1.55;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">For therapists and practice owners</div>
      <h1>Practice Friction Finder</h1>
      <div class="subtitle">A quick 3-minute reflection tool for therapists and practice owners to notice where their practice may be leaking time, energy, or right-fit clients.</div>
      <div class="soft-note">Warm, low-pressure, and built for reflection. Not a diagnosis, not a business prescription.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "audit_submitted" not in st.session_state:
    st.session_state["audit_submitted"] = False
if st.session_state.get("app_version") != APP_VERSION:
    st.session_state["app_version"] = APP_VERSION
    st.session_state["audit_submitted"] = False
    st.session_state.pop("latest_result", None)

with st.form("friction_audit_form"):
    st.subheader("A little context")

    role = st.selectbox(
        "Which best describes you?",
        [
            "Solo therapist",
            "Group practice owner",
            "Practice leader or admin",
            "Pre-launch or early-stage practice",
            "Other",
        ],
    )
    practice_stage = st.selectbox(
        "Which best describes your practice stage right now?",
        PRACTICE_STAGES,
    )

    st.subheader("The audit")
    answers = {}
    for index, question in enumerate(QUESTIONS):
        answers[str(index)] = st.radio(
            question["prompt"],
            list(question["options"].keys()),
            key=f"question_{index}",
        )

    ai_attitude = st.radio(
        "How do you currently feel about AI in private practice?",
        list(AI_ATTITUDE_OPTIONS.keys()),
        key="ai_attitude",
    )

    st.subheader("Your words, not just our categories")
    st.write(
        "These next few are optional, but they help capture the nuance multiple-choice questions can miss."
    )
    hardest_part = st.text_area(
        "If we were having coffee, what's the thing you'd probably vent about first?"
    )
    already_tried = st.text_area(
        "What's something you've already tried that everyone said would work, but didn't?"
    )
    magic_wand = st.text_area(
        "If you woke up tomorrow and one part of your practice no longer drained your energy, what changed?"
    )

    submitted = st.form_submit_button("Show my result")
    st.caption(
        "If you change your answers after seeing a result, click this again to refresh the pattern."
    )

if submitted:
    primary, secondary, scores = score_answers(answers, ai_attitude)
    timestamp = datetime.now().isoformat(timespec="microseconds")

    row = {
        "timestamp": timestamp,
        "name_optional": "",
        "email_optional": "",
        "practice_name_optional": "",
        "website_optional": "",
        "role": role,
        "practice_stage": practice_stage,
        "answers_json": json.dumps(answers, ensure_ascii=False),
        "ai_attitude": ai_attitude,
        "primary_friction_area": primary,
        "secondary_friction_area": secondary or "",
        "result_accuracy": "",
        "hardest_part_free_text": hardest_part,
        "already_tried_free_text": already_tried,
        "magic_wand_free_text": magic_wand,
        "conversation_opt_in": "",
        "follow_up_email": "",
    }
    save_result(row)

    st.session_state["latest_result"] = {
        "timestamp": timestamp,
        "primary": primary,
        "secondary": secondary,
        "scores": dict(scores),
        "practice_stage": practice_stage,
    }
    st.session_state["audit_submitted"] = True

if st.session_state.get("audit_submitted") and "latest_result" in st.session_state:
    latest = st.session_state["latest_result"]

    if submitted:
        st.success("Your reflection is ready — scroll down to see your result.")
        components.html(
            """
            <script>
            const result = window.parent.document.getElementById("audit-result");
            if (result) {
                result.scrollIntoView({ behavior: "smooth", block: "start" });
            }
            </script>
            """,
            height=0,
        )

    st.markdown('<div id="audit-result"></div>', unsafe_allow_html=True)
    st.divider()
    render_result(
        latest["primary"],
        latest["secondary"],
        latest.get("practice_stage", ""),
    )

    st.write(
        "If this brought up something you've been trying to untangle, we're talking with therapists and practice owners as we build this. You're welcome to reach out or leave your email."
    )

    with st.form("result_feedback_form"):
        st.subheader("A quick check")
        result_accuracy = st.radio("Did this feel accurate?", ["Yes", "Somewhat", "No"])
        conversation_opt_in = st.radio(
            "Would you be open to a 20-minute conversation about what this brought up?",
            ["Yes", "Maybe", "Not right now"],
        )

        st.write(
            "If you want us to send your result, follow up, or invite you into the early conversations we're having, you can leave your info below."
        )
        name = st.text_input("Name (optional)")
        email = st.text_input("Email (optional)")
        practice_name = st.text_input("Practice name (optional)")
        website = st.text_input("Website (optional)")
        follow_up_email = email
        if conversation_opt_in in ["Yes", "Maybe"] and not email:
            st.caption(
                "If you are open to talking, an email is the easiest way for us to follow up."
            )

        feedback_submitted = st.form_submit_button("Save my reflections")

    if feedback_submitted:
        update_result_fields(
            latest["timestamp"],
            {
                "name_optional": name,
                "email_optional": email,
                "practice_name_optional": practice_name,
                "website_optional": website,
                "result_accuracy": result_accuracy,
                "conversation_opt_in": conversation_opt_in,
                "follow_up_email": follow_up_email,
            },
        )
        st.success("Thank you. Your reflections were saved locally with this audit.")
