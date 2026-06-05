"""Generate practice questions: 100 per exam type + subject + topic."""

from __future__ import annotations

import random

BULK_SOURCE = "bulk_bank"
EXAM_TYPES = ["SAT", "PSAT", "PSAT 8/9"]
SUBJECT_TOPICS: dict[str, list[str]] = {
    "Math": [
        "Algebra",
        "Advanced Math",
        "Problem Solving",
        "Data Analysis",
        "Geometry",
        "Trigonometry",
    ],
    "Reading": ["Reading Comprehension", "Vocabulary"],
    "Writing": ["Grammar", "Writing"],
}
DIFFICULTIES = ["Easy", "Medium", "Hard"]
QUESTIONS_PER_GROUP = 100


def _difficulty(i: int) -> str:
    return DIFFICULTIES[i % len(DIFFICULTIES)]


def _math_algebra(i: int, exam_type: str) -> dict:
    a = i % 9 + 1
    x = i % 11 + 1
    b = 17 - a * x
    correct = str(x)
    opts = [correct, str(x + 1), str(x - 1), str(x + 2)]
    random.Random(i).shuffle(opts)
    return {
        "question_text": f"If {a}x + {b} = 17, what is x?",
        "options": opts,
        "answer": correct,
        "explanation": f"Subtract {b}, then divide by {a} to get x = {x}.",
        "strategy_tip": "Isolate the variable using inverse operations.",
        "estimated_time": 50,
    }


def _math_advanced(i: int, exam_type: str) -> dict:
    n = i % 5 + 2
    correct = str(n * n)
    opts = [correct, str(n * n + 1), str(n * (n + 1)), str(n + n)]
    random.Random(i + 3).shuffle(opts)
    return {
        "question_text": f"What is ({n})²?",
        "options": opts,
        "answer": correct,
        "explanation": f"({n})² = {n} × {n} = {n * n}.",
        "strategy_tip": "Memorize common squares to save time.",
        "estimated_time": 45,
    }


def _math_problem_solving(i: int, exam_type: str) -> dict:
    rate = i % 4 + 2
    hours = i % 3 + 3
    total = rate * hours
    correct = str(total)
    opts = [correct, str(total + rate), str(total - rate), str(rate + hours)]
    random.Random(i + 5).shuffle(opts)
    return {
        "question_text": f"A tutor helps {rate} students per hour for {hours} hours. How many students total?",
        "options": opts,
        "answer": correct,
        "explanation": f"Multiply rate × time: {rate} × {hours} = {total}.",
        "strategy_tip": "Identify rate, quantity, and total in word problems.",
        "estimated_time": 55,
    }


def _math_data(i: int, exam_type: str) -> dict:
    vals = [10 + i % 5, 12 + i % 4, 14 + i % 3, 16 + i % 2]
    mean = sum(vals) // len(vals)
    correct = str(mean)
    opts = [correct, str(mean + 1), str(mean - 1), str(max(vals))]
    random.Random(i + 7).shuffle(opts)
    return {
        "question_text": f"What is the mean of {vals}?",
        "options": opts,
        "answer": correct,
        "explanation": f"Sum = {sum(vals)}, count = 4, mean = {mean}.",
        "strategy_tip": "Check whether the question asks for mean, median, or mode.",
        "estimated_time": 60,
    }


def _math_geometry(i: int, exam_type: str) -> dict:
    base, height = i % 6 + 4, i % 4 + 3
    area = base * height // 2
    correct = str(area)
    opts = [correct, str(base * height), str(base + height), str(area + 2)]
    random.Random(i + 11).shuffle(opts)
    return {
        "question_text": f"A triangle has base {base} and height {height}. What is its area?",
        "options": opts,
        "answer": correct,
        "explanation": f"Area = ½ × base × height = ½ × {base} × {height} = {area}.",
        "strategy_tip": "Write the correct formula before plugging in numbers.",
        "estimated_time": 55,
    }


def _math_trig(i: int, exam_type: str) -> dict:
    # 3-4-5 style scaled
    k = i % 4 + 1
    opp, hyp = 3 * k, 5 * k
    correct = f"{opp}/{hyp}"
    opts = [correct, f"{hyp}/{opp}", f"{4 * k}/{5 * k}", f"{3 * k}/{4 * k}"]
    random.Random(i + 13).shuffle(opts)
    return {
        "question_text": f"In a right triangle with legs {3*k} and {4*k}, what is sin(theta) if opposite = {3*k} and hypotenuse = {5*k}?",
        "options": opts,
        "answer": correct,
        "explanation": f"sin = opposite/hypotenuse = {opp}/{hyp}.",
        "strategy_tip": "Draw and label opposite, adjacent, and hypotenuse.",
        "estimated_time": 65,
    }


def _reading_comp(i: int, exam_type: str) -> dict:
    passage = (
        f"Passage {i+1}: Students who review missed questions weekly improve retention "
        "more than those who only take full tests."
    )
    correct = "Weekly review of missed questions"
    opts = [
        correct,
        "Taking only full tests",
        "Avoiding timed practice",
        "Skipping error analysis",
    ]
    random.Random(i + 17).shuffle(opts)
    return {
        "question_text": "What is the main idea of the passage?",
        "passage": passage,
        "options": opts,
        "answer": correct,
        "explanation": "The passage contrasts weekly review with test-only practice.",
        "strategy_tip": "Main idea answers should reflect the full passage, not one detail.",
        "estimated_time": 70,
    }


def _reading_vocab(i: int, exam_type: str) -> dict:
    words = [
        ("pragmatic", "practical"),
        ("ambiguous", "unclear"),
        ("concise", "brief"),
        ("diligent", "hardworking"),
        ("candid", "honest"),
    ]
    word, meaning = words[i % len(words)]
    correct = meaning
    opts = [correct, "confused", "angry", "lazy"]
    random.Random(i + 19).shuffle(opts)
    return {
        "question_text": f"The word '{word}' most nearly means:",
        "options": opts,
        "answer": correct,
        "explanation": f"'{word}' means {meaning}.",
        "strategy_tip": "Replace the word in the sentence with each option.",
        "estimated_time": 45,
    }


def _writing_grammar(i: int, exam_type: str) -> dict:
    correct = "The students are ready for the exam."
    opts = [
        correct,
        "The student are ready for the exam.",
        "The students is ready for the exam.",
        "The students ready for the exam.",
    ]
    random.Random(i + 23).shuffle(opts)
    return {
        "question_text": "Which sentence is grammatically correct?",
        "options": opts,
        "answer": correct,
        "explanation": "Plural subject 'students' requires plural verb 'are'.",
        "strategy_tip": "Find the subject first, then match the verb.",
        "estimated_time": 40,
    }


def _writing_writing(i: int, exam_type: str) -> dict:
    correct = "therefore"
    opts = ["therefore", "however", "meanwhile", "for example"]
    random.Random(i + 29).shuffle(opts)
    return {
        "question_text": "The data were inconclusive; ____, the team repeated the trial.",
        "options": opts,
        "answer": correct,
        "explanation": "A conclusion follows inconclusive data, so 'therefore' fits cause-effect.",
        "strategy_tip": "Match transition words to logical relationships between clauses.",
        "estimated_time": 50,
    }


_GENERATORS = {
    ("Math", "Algebra"): _math_algebra,
    ("Math", "Advanced Math"): _math_advanced,
    ("Math", "Problem Solving"): _math_problem_solving,
    ("Math", "Data Analysis"): _math_data,
    ("Math", "Geometry"): _math_geometry,
    ("Math", "Trigonometry"): _math_trig,
    ("Reading", "Reading Comprehension"): _reading_comp,
    ("Reading", "Vocabulary"): _reading_vocab,
    ("Writing", "Grammar"): _writing_grammar,
    ("Writing", "Writing"): _writing_writing,
}


def generate_group(exam_type: str, subject: str, topic: str, count: int = QUESTIONS_PER_GROUP) -> list[dict]:
    gen = _GENERATORS.get((subject, topic))
    if not gen:
        return []

    rows: list[dict] = []
    for i in range(count):
        base = gen(i, exam_type)
        rows.append(
            {
                "exam_type": exam_type,
                "subject": subject,
                "topic": topic,
                "difficulty": _difficulty(i),
                "skill_category": topic,
                "source": BULK_SOURCE,
                **base,
            }
        )
    return rows


def generate_all_questions(count_per_group: int = QUESTIONS_PER_GROUP) -> list[dict]:
    all_rows: list[dict] = []
    for exam_type in EXAM_TYPES:
        for subject, topics in SUBJECT_TOPICS.items():
            for topic in topics:
                all_rows.extend(generate_group(exam_type, subject, topic, count_per_group))
    return all_rows


def group_keys() -> list[tuple[str, str, str]]:
    keys = []
    for exam_type in EXAM_TYPES:
        for subject, topics in SUBJECT_TOPICS.items():
            for topic in topics:
                keys.append((exam_type, subject, topic))
    return keys
