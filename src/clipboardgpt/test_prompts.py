"""Test suite for evaluating ClipboardGPT prompts using AI."""

import json
import os
from typing import Any

from openai import OpenAI

from clipboardgpt.constants import DEFAULT_PROMPTS
from clipboardgpt.utils import render_template


TEST_CASES: dict[str, list[dict[str, Any]]] = {
    "grammar": [
        # English tests
        {
            "name": "English - basic errors",
            "input": "i dont think this are working good",
            "language": "English",
            "expect": "corrected text only, no explanation",
            "context": {},
        },
        {
            "name": "English - already correct",
            "input": "This sentence is already correct.",
            "language": "English",
            "expect": "same or very similar text returned",
            "context": {},
        },
        {
            "name": "English - informal contractions",
            "input": "i wanna tell u about the thing",
            "language": "English",
            "expect": "fix wanna→want to, u→you",
            "context": {},
        },
        {
            "name": "English - gonna/gotta",
            "input": "im gonna go now cuz i gotta leave",
            "language": "English",
            "expect": "fix gonna→going to, gotta→got to, cuz→because",
            "context": {},
        },
        {
            "name": "English - formal email",
            "input": "hey i need the report asap thx",
            "language": "English",
            "expect": "corrected formal text",
            "context": {"context": "formal business email"},
        },
        {
            "name": "English - casual chat",
            "input": "ur gonna love this lol",
            "language": "English",
            "expect": "corrected text",
            "context": {"app": "chat"},
        },
        {
            "name": "English - punctuation only",
            "input": "Hello how are you I am fine",
            "language": "English",
            "expect": "add proper punctuation",
            "context": {},
        },
        {
            "name": "English - capitalization",
            "input": "i went to paris and saw the eiffel tower",
            "language": "English",
            "expect": "fix capitalization of I, Paris, Eiffel Tower",
            "context": {},
        },
        # Danish tests
        {
            "name": "Danish - basic errors",
            "input": "jeg tror ikke det her virke godt",
            "language": "Danish",
            "expect": "corrected Danish text only, must stay in Danish",
            "context": {},
        },
        {
            "name": "Danish - spelling",
            "input": "hvad sker der, ska vi mødes imorgen",
            "language": "Danish",
            "expect": "fix ska→skal, imorgen→i morgen, stay in Danish",
            "context": {},
        },
        {
            "name": "Danish - formal",
            "input": "hej jeg vil gerne bestille en tid",
            "language": "Danish",
            "expect": "polished Danish, no translation",
            "context": {"context": "formal email"},
        },
        # German tests
        {
            "name": "German - basic errors",
            "input": "ich haben gestern ein film gesehen",
            "language": "German",
            "expect": "corrected German, haben→habe, ein→einen",
            "context": {},
        },
        {
            "name": "German - capitalization",
            "input": "das auto ist sehr schnell und die straße ist lang",
            "language": "German",
            "expect": "fix noun capitalization: Auto, Straße",
            "context": {},
        },
        # Spanish tests
        {
            "name": "Spanish - basic errors",
            "input": "yo quere ir al tienda mañana",
            "language": "Spanish",
            "expect": "corrected Spanish: quiero, a la tienda",
            "context": {},
        },
        {
            "name": "Spanish - accents",
            "input": "como estas, que vas a hacer manana",
            "language": "Spanish",
            "expect": "add accents: Cómo estás, mañana",
            "context": {},
        },
        # French tests
        {
            "name": "French - basic errors",
            "input": "je suis alle au magasin hier",
            "language": "French",
            "expect": "corrected French: allé with accent",
            "context": {},
        },
        {
            "name": "French - gender agreement",
            "input": "la maison est très grand et beau",
            "language": "French",
            "expect": "fix agreement: grande, belle",
            "context": {},
        },
        # Mixed/edge cases
        {
            "name": "Code snippet - preserve",
            "input": "the function getData() dont work",
            "language": "English",
            "expect": "fix grammar but preserve getData()",
            "context": {},
        },
        {
            "name": "Numbers and dates",
            "input": "the meeting is on january 5th 2024 at 3pm",
            "language": "English",
            "expect": "proper formatting, minimal changes",
            "context": {},
        },
    ],
    "reply": [
        # English - various tones
        {
            "name": "English - casual question",
            "input": "Hey, can you help me with something?",
            "language": "English",
            "expect": "English response only, no meta text",
            "context": {},
        },
        {
            "name": "English - very casual/slang",
            "input": "yo whats up, wanna grab lunch?",
            "language": "English",
            "expect": "casual response matching informal tone",
            "context": {"app": "chat"},
        },
        {
            "name": "English - formal request",
            "input": "Dear Sir/Madam, I would like to inquire about your services.",
            "language": "English",
            "expect": "formal English response matching tone",
            "context": {"app": "email"},
        },
        {
            "name": "English - meeting request",
            "input": "Can we schedule a meeting tomorrow?",
            "language": "English",
            "expect": "English response about scheduling",
            "context": {"name": "Lars"},
        },
        {
            "name": "English - thank you",
            "input": "Thanks so much for your help!",
            "language": "English",
            "expect": "polite acknowledgment response",
            "context": {},
        },
        {
            "name": "English - complaint",
            "input": "This product is terrible and I want a refund.",
            "language": "English",
            "expect": "professional response addressing concern",
            "context": {"app": "email"},
        },
        {
            "name": "English - invitation",
            "input": "Would you like to come to my birthday party next Saturday?",
            "language": "English",
            "expect": "response to invitation",
            "context": {},
        },
        {
            "name": "English - technical question",
            "input": "How do I fix the bug in the login page?",
            "language": "English",
            "expect": "helpful response, may ask for details",
            "context": {"app": "chat"},
        },
        # Danish replies
        {
            "name": "Danish - casual",
            "input": "Hej, kan du hjælpe mig med noget?",
            "language": "Danish",
            "expect": "Danish response only, must stay in Danish",
            "context": {},
        },
        {
            "name": "Danish - formal",
            "input": "Kære kunde, tak for din henvendelse.",
            "language": "Danish",
            "expect": "formal Danish response",
            "context": {"app": "email"},
        },
        {
            "name": "Danish - invitation",
            "input": "Vil du med til fest på fredag?",
            "language": "Danish",
            "expect": "Danish response to invitation",
            "context": {"app": "chat"},
        },
        {
            "name": "Danish - work context",
            "input": "Kan du sende rapporten inden kl 15?",
            "language": "Danish",
            "expect": "Danish response about deadline",
            "context": {},
        },
        # German replies
        {
            "name": "German - casual",
            "input": "Hey, hast du Zeit heute Abend?",
            "language": "German",
            "expect": "German response, casual tone",
            "context": {"app": "chat"},
        },
        {
            "name": "German - formal",
            "input": "Sehr geehrte Damen und Herren, ich möchte mich bewerben.",
            "language": "German",
            "expect": "formal German response",
            "context": {"app": "email"},
        },
        # Spanish replies
        {
            "name": "Spanish - casual",
            "input": "Oye, qué tal si nos vemos mañana?",
            "language": "Spanish",
            "expect": "Spanish response, casual",
            "context": {},
        },
        {
            "name": "Spanish - formal",
            "input": "Estimado señor, le escribo para solicitar información.",
            "language": "Spanish",
            "expect": "formal Spanish response",
            "context": {"app": "email"},
        },
        # French replies
        {
            "name": "French - casual",
            "input": "Salut, ça te dit d'aller au cinéma?",
            "language": "French",
            "expect": "French response, casual",
            "context": {"app": "chat"},
        },
        {
            "name": "French - formal",
            "input": "Madame, Monsieur, je vous prie de bien vouloir...",
            "language": "French",
            "expect": "formal French response",
            "context": {"app": "email"},
        },
        # Edge cases
        {
            "name": "Short message - ok",
            "input": "ok",
            "language": "English",
            "expect": "brief acknowledgment or follow-up",
            "context": {},
        },
        {
            "name": "Emoji message",
            "input": "🎉🎉🎉 Congratulations!!!",
            "language": "English",
            "expect": "celebratory response",
            "context": {},
        },
        {
            "name": "Question with context",
            "input": "What do you think about the proposal?",
            "language": "English",
            "expect": "response asking for or giving opinion",
            "context": {"context": "business meeting follow-up"},
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
