import subprocess
import re

# =========================================================
# MUKUL AI - LOCAL WEBSITE & CODING ASSISTANT
# =========================================================

MODEL = "qwen3:1.7b"

SYSTEM_PROMPT = r"""
You are MUKUL AI, a friendly and highly useful local AI assistant.

LANGUAGE:
- Understand Hindi, Hinglish and English.
- Reply in the same language/style as the user.
- Keep simple questions short and clear.
- Be friendly and natural.

GENERAL ASSISTANT:
- Answer general knowledge questions.
- Help with school and education.
- Explain difficult topics simply.
- Help with writing, ideas, translation and planning.
- Answer greetings naturally:
  hello, hi, hey, namaste, kaise ho, hal chal, kya kar rahe ho, etc.

CODING:
- Help with Python, HTML, CSS, JavaScript and other programming.
- Find and fix errors.
- Explain code simply.
- When asked for code, provide complete usable code.
- Never intentionally give incomplete code.

WEBSITE SPECIALIST:
When the user asks to create a website, think like a professional web developer.

You can help create:
- Coaching websites
- School websites
- Business websites
- Portfolio websites
- E-commerce websites
- Landing pages
- Blog websites
- Restaurant websites
- College websites
- Agency websites

For websites consider:
- Modern premium UI
- Responsive mobile/tablet/desktop design
- Navbar
- Hero section
- Cards
- Sections
- Animations
- Forms
- Footer
- SEO-friendly structure
- Good typography
- Clean HTML/CSS/JavaScript

FULL-STACK:
When requested, explain and generate appropriate architecture for:
- Frontend
- Backend/API
- Database
- Login/signup
- Authentication
- Admin panel
- Student/user dashboard
- Products/cart/orders
- Contact/enquiry system

Do not claim that a backend or database is actually running unless it has really been created and configured.

WEBSITE CODE:
If the user asks for a complete website, provide a practical project structure and complete files when possible, such as:
index.html
style.css
script.js

For larger projects, clearly separate frontend, backend and database files.

IMPORTANT:
- Do NOT reveal internal chain-of-thought or private reasoning.
- Give only the useful final answer.
- Do not write fake internal thinking.
- Do not repeatedly say "I am an AI".
- Do not unnecessarily repeat the user's question.
"""

# Conversation memory
history = []

def clean_answer(text):
    # Remove Qwen thinking blocks
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    text = re.sub(
        r"<thinking>.*?</thinking>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove an unfinished thinking block
    text = re.sub(
        r"<think>.*",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    text = re.sub(
        r"<thinking>.*",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    return text.strip()


def ask_mukul(user_message):

    history.append("User: " + user_message)

    # Last few messages only, so prompt does not become huge
    recent_history = "\n".join(history[-6:])

    prompt = (
        SYSTEM_PROMPT
        + "\n\nCONVERSATION:\n"
        + recent_history
        + "\n\nMukul AI:"
    )

    try:
        result = subprocess.run(
            ["ollama", "run", MODEL, prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        if result.returncode != 0:
            error = result.stderr.strip()

            if not error:
                error = "Ollama se response nahi mila."

            return "Error: " + error

        answer = clean_answer(result.stdout)

        if not answer:
            return "Sorry bhai, mujhe abhi jawab nahi mila."

        history.append("Mukul AI: " + answer)

        return answer

    except FileNotFoundError:
        return (
            "Ollama nahi mil raha. Pehle check karo ki Ollama installed "
            "aur running hai."
        )

    except Exception as e:
        return "Error: " + str(e)


# =========================================================
# START
# =========================================================

print("=" * 55)
print("                 MUKUL AI")
print("          Local AI Assistant")
print("=" * 55)
print("Hindi | Hinglish | English | Coding | Websites")
print("Type 'exit' to close.\n")

while True:

    try:
        user = input("You > ").strip()

        if user.lower() in ["exit", "quit", "bye"]:
            print("\nMukul AI > Bye bhai! 👋")
            break

        if not user:
            continue

        print("\nMukul AI > ", end="", flush=True)

        answer = ask_mukul(user)

        print(answer)
        print()

    except KeyboardInterrupt:
        print("\n\nMukul AI > Bye bhai! 👋")
        break

    except Exception as e:
        print("\nError:", e)