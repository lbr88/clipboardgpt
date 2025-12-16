"""Test suite for evaluating ClipboardGPT prompts using AI."""

import json
import os
from typing import Any

from openai import OpenAI

from clipboardgpt.constants import DEFAULT_PROMPTS
from clipboardgpt.utils import render_template


TEST_CASES: dict[str, list[dict[str, Any]]] = {
    "grammar": [
        # English - full emails
        {
            "name": "English - business email with errors",
            "input": (
                "hi john\n\n"
                "i wanted to follow up on our conversation from yesterday. "
                "i think we should definately move forward with the project but "
                "there still some concerns i wanna address before we finalize everything.\n\n"
                "first off the budget dont seem right to me. we discussed 50k but "
                "the proposal your team sent shows 65k which is way more then we agreed on. "
                "can you look into this and get back to me asap?\n\n"
                "also i havent recieved the technical specs yet. we gonna need those "
                "before the meeting on friday.\n\n"
                "let me know what you think\n"
                "thanks"
            ),
            "language": "English",
            "expect": "corrected email, fix spelling/grammar, keep structure",
            "context": {"app": "email"},
        },
        {
            "name": "English - casual work message",
            "input": (
                "hey team just wanted to give u all a quick update on where we're at. "
                "the deployment went smoothe last night and everythings running good so far. "
                "we did ran into a few minor issues but nothing major. gonna keep monitoring "
                "throughout the day and ill let you know if anything comes up. "
                "btw does anyone know if the standup is still at 10 or did it get moved?"
            ),
            "language": "English",
            "expect": "corrected text, informal contractions fixed",
            "context": {"app": "chat"},
        },
        {
            "name": "English - technical documentation",
            "input": (
                "the getData() function dont return the expected results when the "
                "input parameter are null. i think this is because we forgot to add "
                "the null check in line 42. also the handleError() method is'nt being "
                "called properly when exceptions occur. we should probly refactor this "
                "whole module cuz its getting to complex."
            ),
            "language": "English",
            "expect": "fix grammar, preserve code references like getData()",
            "context": {},
        },
        # Danish - full emails
        {
            "name": "Danish - business email",
            "input": (
                "hej peter\n\n"
                "tak for din mail. jeg har kigget på de dokumenter du sendte og "
                "jeg har et par spørgsmål jeg gerne vil have svar på.\n\n"
                "for det første så forstår jeg ikke helt hvorfor prisen er steget "
                "så meget siden sidst. vi havde aftalt 25000 kr men nu står der 32000. "
                "kan du forklare hvad der er sket?\n\n"
                "derudover så mangler der stadig nogle bilag som jeg ska bruge til "
                "regnskabet. kan du sende dem hurtigst mulig?\n\n"
                "venlig hilsen\n"
                "lars"
            ),
            "language": "Danish",
            "expect": "corrected Danish, stay in Danish, fix ska→skal",
            "context": {"app": "email"},
        },
        {
            "name": "Danish - casual chat",
            "input": (
                "hej skal vi mødes imorgen og snakke om projektet? "
                "jeg tænker vi kan tage en kop kaffe og gennemgå det hele. "
                "har du tid ved 14 tiden eller passer det bedre om formiddagen?"
            ),
            "language": "Danish",
            "expect": "fix imorgen→i morgen, stay in Danish",
            "context": {"app": "chat"},
        },
        # German
        {
            "name": "German - formal email",
            "input": (
                "sehr geehrte damen und herren\n\n"
                "ich schreibe ihnen bezüglich meiner bestellung vom letzten monat. "
                "ich haben die ware noch nicht erhalten und wollte fragen ob sie mir "
                "sagen können wann ich mit der lieferung rechnen kann.\n\n"
                "die bestellnummer ist 12345 und ich habe am 15. november bestellt.\n\n"
                "mit freundlichen grüßen"
            ),
            "language": "German",
            "expect": "fix haben→habe, capitalize nouns, stay in German",
            "context": {"app": "email"},
        },
        # Spanish
        {
            "name": "Spanish - customer inquiry",
            "input": (
                "hola buenas tardes\n\n"
                "queria preguntar sobre los precios de sus servicios. "
                "vi en su pagina web que ofrecen varios paquetes pero no me "
                "quedo claro cual es la diferencia entre ellos.\n\n"
                "tambien me gustaria saber si tienen algun descuento para "
                "empresas pequeñas como la mia.\n\n"
                "gracias de antemano"
            ),
            "language": "Spanish",
            "expect": "add accents (quería, página, quedó, también), stay in Spanish",
            "context": {"app": "email"},
        },
        # French
        {
            "name": "French - professional email",
            "input": (
                "bonjour\n\n"
                "je vous ecris pour vous informer que j'ai bien recu votre proposition. "
                "j'ai examine les documents et j'ai quelques questions a vous poser.\n\n"
                "premierement je ne comprend pas pourquoi le delai est si long. "
                "vous aviez dit deux semaines mais maintenant vous parlez de quatre semaines.\n\n"
                "deuxiemement est-ce que le prix inclut la livraison?\n\n"
                "merci de votre reponse"
            ),
            "language": "French",
            "expect": "add accents (écris, reçu, examiné, délai, etc), stay in French",
            "context": {"app": "email"},
        },
        # Edge cases
        {
            "name": "English - already correct email",
            "input": (
                "Hi Sarah,\n\n"
                "Thank you for your email. I have reviewed the documents and "
                "everything looks good to me. I will proceed with the next steps "
                "and keep you updated on our progress.\n\n"
                "Best regards,\n"
                "John"
            ),
            "language": "English",
            "expect": "return same or nearly identical text",
            "context": {"app": "email"},
        },
        {
            "name": "English - mixed code and text",
            "input": (
                "hey can you check this code real quick? the function processData() "
                "is throwing a NullPointerException when i pass an empty array to it. "
                "i tried wrapping it in a try-catch block but that dont seem to help. "
                "maybe we need to add a check for array.length === 0 before processing?"
            ),
            "language": "English",
            "expect": "fix grammar, preserve all code references exactly",
            "context": {"app": "chat"},
        },
    ],
    "reply": [
        # English - full email replies
        {
            "name": "English - reply to project update",
            "input": (
                "Hi team,\n\n"
                "I wanted to give everyone a quick update on the Q4 project. "
                "We've completed the first phase and are now moving into testing. "
                "There are a few blockers that need to be addressed before we can "
                "proceed to production.\n\n"
                "First, we're still waiting on the security review from IT. "
                "Second, the database migration scripts haven't been tested yet. "
                "Third, we need sign-off from legal on the new terms of service.\n\n"
                "Can everyone please prioritize these items this week?\n\n"
                "Thanks,\n"
                "Sarah"
            ),
            "language": "English",
            "expect": "professional reply acknowledging the update",
            "context": {"app": "email", "name": "Lars"},
        },
        {
            "name": "English - reply to meeting request",
            "input": (
                "Hi Lars,\n\n"
                "I hope this email finds you well. I would like to schedule a meeting "
                "to discuss the upcoming product launch. We need to finalize the "
                "marketing strategy and budget allocation.\n\n"
                "Would you be available sometime next week? I'm flexible on Tuesday "
                "afternoon or Thursday morning. The meeting should take about an hour.\n\n"
                "Please let me know what works best for you.\n\n"
                "Best regards,\n"
                "Michael"
            ),
            "language": "English",
            "expect": "reply confirming or suggesting alternative times",
            "context": {"app": "email", "name": "Lars"},
        },
        {
            "name": "English - reply to customer complaint",
            "input": (
                "To whom it may concern,\n\n"
                "I am extremely disappointed with the service I received. I placed "
                "an order two weeks ago and it still hasn't arrived. When I called "
                "customer support, I was put on hold for 45 minutes and then "
                "disconnected. This is unacceptable.\n\n"
                "I demand a full refund and an explanation for this terrible "
                "customer experience. If I don't hear back within 24 hours, I will "
                "be filing a complaint with the consumer protection agency.\n\n"
                "Regards,\n"
                "John Smith"
            ),
            "language": "English",
            "expect": "professional, apologetic response addressing concerns",
            "context": {"app": "email"},
        },
        {
            "name": "English - casual Slack message",
            "input": (
                "yo just pushed the fix for that bug we talked about. "
                "can you do a quick code review when you get a chance? "
                "nothing urgent but would be nice to get it merged before EOD. "
                "also are you coming to the team lunch tomorrow?"
            ),
            "language": "English",
            "expect": "casual response, matching informal tone",
            "context": {"app": "chat"},
        },
        {
            "name": "English - reply to job offer",
            "input": (
                "Dear Mr. Rasmussen,\n\n"
                "We are pleased to inform you that after careful consideration, "
                "we would like to offer you the position of Senior Software Engineer "
                "at TechCorp Inc. The starting salary will be $150,000 per year, "
                "with full benefits including health insurance, 401k matching, "
                "and 4 weeks of paid vacation.\n\n"
                "Please review the attached offer letter and let us know your "
                "decision by the end of next week.\n\n"
                "We look forward to hearing from you.\n\n"
                "Best regards,\n"
                "HR Team"
            ),
            "language": "English",
            "expect": "professional reply expressing interest or asking questions",
            "context": {"app": "email", "name": "Lars"},
        },
        # Danish replies
        {
            "name": "Danish - reply to work email",
            "input": (
                "Hej Lars,\n\n"
                "Jeg skriver for at høre om du har tid til at hjælpe med "
                "projektet i næste uge. Vi mangler en ekstra udvikler til at "
                "færdiggøre backend-arbejdet, og jeg tænkte du ville være perfekt "
                "til opgaven.\n\n"
                "Det drejer sig om cirka 20 timer fordelt over mandag til onsdag. "
                "Kan du give mig besked hurtigst muligt?\n\n"
                "Venlig hilsen,\n"
                "Peter"
            ),
            "language": "Danish",
            "expect": "Danish reply about availability",
            "context": {"app": "email", "name": "Lars"},
        },
        {
            "name": "Danish - casual chat reply",
            "input": (
                "hej skal vi tage en øl efter arbejde i dag? "
                "der er åbnet en ny bar nede på havnen som jeg gerne vil prøve. "
                "de har angiveligt verdens bedste ipa'er 🍺"
            ),
            "language": "Danish",
            "expect": "casual Danish reply to invitation",
            "context": {"app": "chat"},
        },
        # German replies
        {
            "name": "German - formal business reply",
            "input": (
                "Sehr geehrter Herr Rasmussen,\n\n"
                "vielen Dank für Ihre Anfrage bezüglich unserer Dienstleistungen. "
                "Wir freuen uns über Ihr Interesse an einer Zusammenarbeit.\n\n"
                "Gerne würde ich Ihnen unser Angebot persönlich vorstellen. "
                "Wären Sie nächste Woche für ein Gespräch verfügbar?\n\n"
                "Mit freundlichen Grüßen,\n"
                "Thomas Müller"
            ),
            "language": "German",
            "expect": "formal German reply",
            "context": {"app": "email"},
        },
        # Spanish replies
        {
            "name": "Spanish - reply to inquiry",
            "input": (
                "Estimado cliente,\n\n"
                "Gracias por contactarnos. Hemos recibido su solicitud y la "
                "estamos procesando. Un miembro de nuestro equipo se pondrá en "
                "contacto con usted en las próximas 24-48 horas para discutir "
                "los detalles de su proyecto.\n\n"
                "Mientras tanto, si tiene alguna pregunta adicional, no dude "
                "en responder a este correo.\n\n"
                "Saludos cordiales,\n"
                "Equipo de Ventas"
            ),
            "language": "Spanish",
            "expect": "Spanish reply thanking them",
            "context": {"app": "email"},
        },
        # French replies
        {
            "name": "French - casual message reply",
            "input": (
                "Salut!\n\n"
                "Ça te dit de venir à ma fête d'anniversaire samedi prochain? "
                "Ce sera chez moi à partir de 20h. Il y aura de la musique, "
                "des boissons et un barbecue si le temps le permet.\n\n"
                "Fais-moi savoir si tu peux venir!\n\n"
                "Bisous"
            ),
            "language": "French",
            "expect": "French reply to party invitation",
            "context": {"app": "chat"},
        },
        # Edge cases
        {
            "name": "English - short acknowledgment",
            "input": "Got it, thanks!",
            "language": "English",
            "expect": "brief acknowledgment",
            "context": {"app": "chat"},
        },
        {
            "name": "English - technical question",
            "input": (
                "Hey, I'm stuck on this Kubernetes issue. The pods keep crashing "
                "with OOMKilled errors even though I've set the memory limits to 2Gi. "
                "I've checked the application logs and there's no memory leak that I can see. "
                "Any ideas what might be causing this?"
            ),
            "language": "English",
            "expect": "helpful technical response",
            "context": {"app": "chat"},
        },
    ],
    "cli": [
        # File operations
        {
            "name": "Find python files",
            "input": "find all python files in current directory",
            "language": "command",
            "expect": "find command, no explanation or markdown",
            "context": {},
        },
        {
            "name": "Find large files",
            "input": "find files larger than 100MB",
            "language": "command",
            "expect": "find with -size, no markdown",
            "context": {},
        },
        {
            "name": "Delete old files",
            "input": "delete all log files older than 7 days",
            "language": "command",
            "expect": "find with -delete or rm, no explanation",
            "context": {},
        },
        {
            "name": "Copy recursively",
            "input": "copy the src folder to backup",
            "language": "command",
            "expect": "cp -r command",
            "context": {},
        },
        # Disk and system
        {
            "name": "Disk usage sorted",
            "input": "show disk usage sorted by size",
            "language": "command",
            "expect": "du with sort, no markdown",
            "context": {},
        },
        {
            "name": "Free memory",
            "input": "show how much free memory",
            "language": "command",
            "expect": "free command",
            "context": {},
        },
        {
            "name": "Running processes",
            "input": "show all running processes",
            "language": "command",
            "expect": "ps command",
            "context": {},
        },
        {
            "name": "Kill process",
            "input": "kill all processes named nginx",
            "language": "command",
            "expect": "pkill or killall command",
            "context": {},
        },
        # Text search
        {
            "name": "Search in files",
            "input": "search for TODO in all js files",
            "language": "command",
            "expect": "grep command, no explanation",
            "context": {},
        },
        {
            "name": "Count lines",
            "input": "count lines in all python files",
            "language": "command",
            "expect": "wc -l with find or glob",
            "context": {},
        },
        {
            "name": "Replace text",
            "input": "replace foo with bar in all txt files",
            "language": "command",
            "expect": "sed or find with sed",
            "context": {},
        },
        # Git commands
        {
            "name": "Git status",
            "input": "show git status",
            "language": "command",
            "expect": "git status",
            "context": {},
        },
        {
            "name": "Git log oneline",
            "input": "show last 10 commits",
            "language": "command",
            "expect": "git log command",
            "context": {},
        },
        {
            "name": "Git branch",
            "input": "create and switch to new branch feature",
            "language": "command",
            "expect": "git checkout -b or git switch -c",
            "context": {},
        },
        # Network
        {
            "name": "Check port",
            "input": "check if port 8080 is in use",
            "language": "command",
            "expect": "lsof, netstat, or ss command",
            "context": {},
        },
        {
            "name": "Download file",
            "input": "download https://example.com/file.zip",
            "language": "command",
            "expect": "curl or wget command",
            "context": {},
        },
        # Docker
        {
            "name": "Docker containers",
            "input": "list running docker containers",
            "language": "command",
            "expect": "docker ps",
            "context": {},
        },
        {
            "name": "Docker cleanup",
            "input": "remove all stopped containers",
            "language": "command",
            "expect": "docker container prune or rm",
            "context": {},
        },
        # Complex/chained
        {
            "name": "Chained commands",
            "input": "create dir called test, cd into it, and create empty file",
            "language": "command",
            "expect": "mkdir && cd && touch",
            "context": {},
        },
        {
            "name": "Pipeline",
            "input": "list files and show only the first 5",
            "language": "command",
            "expect": "ls piped to head",
            "context": {},
        },
    ],
}

EVALUATOR_PROMPT = """You are a test evaluator. Analyze if an AI response follows the rules.

PROMPT TYPE: {prompt_type}
INPUT TEXT: {input_text}
INPUT LANGUAGE: {language}
EXPECTED BEHAVIOR: {expected}
ACTUAL RESPONSE: {response}

Evaluate these criteria:
1. OUTPUT_ONLY: Response contains ONLY the output (no explanations, no "Here's...", no meta-text)?
2. LANGUAGE_PRESERVED: Response is in correct language (same as input for grammar/reply)?
3. FOLLOWS_RULES: Follows prompt rules (grammar fixes grammar, reply is a reply, cli is command)?

Respond with EXACTLY this JSON format, nothing else:
{{"pass": true/false, "issues": ["issue1", "issue2"] or []}}"""


def _evaluate_response(
    client: OpenAI,
    model: str,
    prompt_type: str,
    case: dict[str, str],
    response: str,
) -> tuple[bool, list[str], str]:
    """Evaluate a response using AI.

    Returns:
        Tuple of (passed, list of issues, raw evaluation text).
    """
    eval_prompt = EVALUATOR_PROMPT.format(
        prompt_type=prompt_type,
        input_text=case["input"],
        language=case["language"],
        expected=case["expect"],
        response=response,
    )

    try:
        eval_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": eval_prompt}],
        )
        eval_text = eval_response.choices[0].message.content or "{}"

        # Clean up response in case it has markdown
        eval_text_clean = eval_text.strip()
        if eval_text_clean.startswith("```"):
            eval_text_clean = eval_text_clean.split("\n", 1)[1].rsplit("```", 1)[0]

        result = json.loads(eval_text_clean)
        return result.get("pass", False), result.get("issues", []), eval_text

    except (json.JSONDecodeError, KeyError):
        # Fallback: basic check for meta-text
        response_lower = response.lower()
        meta_phrases = ["here's", "here is", "i've", "i have", "```", "certainly"]
        has_meta = any(phrase in response_lower for phrase in meta_phrases)
        if has_meta:
            return False, ["Contains meta-text or markdown"], "(fallback check)"
        return True, [], "(fallback check)"


def _run_single_test(
    client: OpenAI,
    model: str,
    prompt_type: str,
    case: dict[str, Any],
) -> tuple[bool, str, str, str, list[str], str]:
    """Run a single test case.

    Returns:
        Tuple of (passed, system_prompt, user_prompt, response, issues, eval_text).
    """
    system_template = DEFAULT_PROMPTS[prompt_type]["system"]
    user_template = DEFAULT_PROMPTS[prompt_type]["user"]

    # Build variables from case context
    variables: dict[str, str] = {
        "text": case["input"],
        "context": "",
        "window_title": "",
        "app": "",
        "name": "",
    }
    # Override with case-specific context
    if "context" in case and isinstance(case["context"], dict):
        variables.update(case["context"])

    # Render templates
    system_prompt = render_template(system_template, variables)
    user_prompt = render_template(user_template, variables)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        actual_response = response.choices[0].message.content or ""
    except Exception as err:  # pylint: disable=broad-exception-caught
        return False, system_prompt, user_prompt, "", [f"API error: {err}"], ""

    passed, issues, eval_text = _evaluate_response(
        client, model, prompt_type, case, actual_response
    )
    return passed, system_prompt, user_prompt, actual_response, issues, eval_text


def run_tests(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    config: dict[str, Any],
    verbose: bool = False,
) -> int:
    """Run AI-evaluated tests on all default prompts.

    Args:
        config: Application configuration.
        verbose: Show detailed output including prompts and responses.

    Returns:
        Exit code (0 for success, 1 for failures).
    """
    api_key = os.getenv("OPENAI_API_KEY") or config.get("openai_api_key")
    if not api_key:
        print("Error: OPENAI_API_KEY required for tests")
        return 1

    client = OpenAI(api_key=api_key, timeout=30.0)
    model = config.get("model", "gpt-4o")

    print(f"Running prompt tests with model: {model}")
    if verbose:
        print("Verbose mode: showing prompts, responses, and evaluations")
    print("\n" + "=" * 60)

    total_tests = 0
    passed_tests = 0
    failed_tests: list[dict[str, Any]] = []

    for prompt_type, cases in TEST_CASES.items():
        if prompt_type not in DEFAULT_PROMPTS:
            continue

        print(f"\n📋 Testing: {prompt_type}")
        print("-" * 40)

        if verbose:
            system_prompt = DEFAULT_PROMPTS[prompt_type]["system"]
            print(f"\n  System Prompt:\n  {'-' * 36}")
            for line in system_prompt.split("\n"):
                print(f"  │ {line}")
            print()

        for case in cases:
            total_tests += 1
            test_name = case["name"]

            passed, _, user_prompt, response, issues, eval_text = _run_single_test(
                client, model, prompt_type, case
            )

            if verbose:
                print(f"\n  Test: {test_name}")
                print(f"  {'─' * 36}")
                if case.get("context"):
                    print(f"  Context vars: {case['context']}")
                print(f"  User Prompt: {user_prompt}")
                print(f"  Expected: {case['expect']}")
                print(f"  Response: {response}")
                print(f"  Evaluation: {eval_text}")

            if passed:
                passed_tests += 1
                print("  Result: ✅ PASS" if verbose else f"  ✅ {test_name}")
            else:
                print("  Result: ❌ FAIL" if verbose else f"  ❌ {test_name}")
                for issue in issues:
                    print(f"     → {issue}")
                failed_tests.append(
                    {
                        "name": f"{prompt_type}/{test_name}",
                        "input": case["input"],
                        "response": response[:100] if response else "(no response)",
                        "issues": issues,
                    }
                )

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed_tests}/{total_tests} passed")

    if failed_tests:
        print(f"\n❌ Failed tests ({len(failed_tests)}):")
        for fail in failed_tests:
            print(f"  - {fail['name']}")
            for issue in fail["issues"]:
                print(f"    → {issue}")
        return 1

    print("\n✅ All tests passed!")
    return 0
