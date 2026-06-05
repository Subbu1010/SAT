"""Original exam-style questions modeled on SAT, PSAT, and PSAT 8/9 formats."""

from __future__ import annotations

import random

from app.database.exam_catalog.constants import DIFFICULTY_ORDER, DIFFICULTY_PATTERN

_EXAM_SEED = {"SAT": 0, "PSAT": 50_000, "PSAT 8/9": 100_000}


def _rng(i: int, exam_type: str, salt: int = 0) -> random.Random:
    return random.Random(i + salt + _EXAM_SEED.get(exam_type, 0))


def _difficulty(i: int, exam_type: str) -> str:
    pattern = DIFFICULTY_PATTERN.get(exam_type, DIFFICULTY_ORDER)
    return pattern[i % len(pattern)]


def _row(
    *,
    exam_type: str,
    subject: str,
    topic: str,
    i: int,
    question_text: str,
    options: list[str],
    answer: str,
    explanation: str,
    strategy_tip: str,
    skill_category: str,
    estimated_time: int = 60,
    passage: str | None = None,
) -> dict:
    return {
        "exam_type": exam_type,
        "subject": subject,
        "topic": topic,
        "difficulty": _difficulty(i, exam_type),
        "skill_category": skill_category,
        "question_text": question_text,
        "passage": passage,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "strategy_tip": strategy_tip,
        "estimated_time": estimated_time,
    }


def _math_algebra(i: int, exam_type: str) -> dict:
    if exam_type == "PSAT 8/9":
        m = i % 6 + 2
        b = i % 5 + 1
        c = m + b
        ans = str(m)
        opts = [ans, str(m + 1), str(m - 1), str(m + 2)]
        text = f"A number m satisfies m + {b} = {c}. What is the value of m?"
        expl = f"Subtract {b} from both sides: m = {c} - {b} = {m}."
        skill = "Linear equations in one variable"
    elif exam_type == "PSAT":
        a = i % 4 + 2
        x = i % 7 + 2
        b = i % 5 + 2
        c = a * x + b
        ans = str(x)
        opts = [ans, str(x + 1), str(x - 1), str(x + 2)]
        text = f"If {a}x + {b} = {c}, what is the value of x?"
        expl = f"Subtract {b} to get {a}x = {a*x}, then divide by {a}."
        skill = "Linear equations in one variable"
    else:
        a = i % 5 + 2
        b = i % 7 + 3
        c = i % 4 + 10
        x = (c - b) // a if (c - b) % a == 0 else 4
        c = a * x + b
        ans = str(x)
        opts = [ans, str(x + 1), str(x - 1), str(x + 2)]
        text = (
            f"The equation {a}x + {b} = {c} represents a relationship between two variables. "
            "What is the value of x?"
        )
        expl = f"Subtract {b}: {a}x = {a*x}. Divide by {a}: x = {x}."
        skill = "Heart of Algebra — linear equations"

    _rng(i, exam_type, 1).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Math",
        topic="Algebra",
        i=i,
        question_text=text,
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Isolate the variable using inverse operations.",
        skill_category=skill,
        estimated_time=55 if exam_type == "PSAT 8/9" else 65,
    )


def _math_advanced(i: int, exam_type: str) -> dict:
    if exam_type == "PSAT 8/9":
        n = i % 5 + 2
        ans = str(n * n)
        opts = [ans, str(n * n + 1), str(n + n), str(n * n - 1)]
        text = f"What is the value of {n}²?"
        expl = f"{n}² = {n} × {n} = {n*n}."
        skill = "Exponents and squares"
    elif exam_type == "PSAT":
        r1 = i % 4 + 2
        r2 = i % 3 + 2
        ans = f"x² + {r1 + r2}x + {r1 * r2}"
        opts = [
            ans,
            f"x² + {r1 * r2}x + {r1 + r2}",
            f"x² + {r1}x + {r2}",
            f"x² + {r1 + r2}x + {r1 + r2}",
        ]
        text = f"Which expression is equivalent to (x + {r1})(x + {r2})?"
        expl = f"Multiply binomials: (x + {r1})(x + {r2}) = x² + {r1+r2}x + {r1*r2}."
        skill = "Polynomials"
    else:
        p = i % 5 + 2
        q = (i % 4) + 6
        if p == q:
            q += 1
        roots = sorted((p, q))
        ans = str(roots[1])
        opts = [str(roots[0]), str(roots[1]), str(roots[0] + roots[1]), str(roots[1] + 1)]
        text = f"If x² - {p+q}x + {p*q} = 0, which of the following is a solution?"
        expl = f"Factor: (x - {p})(x - {q}) = 0, so x = {p} or x = {q}."
        skill = "Passport to Advanced Math — quadratics"

    _rng(i, exam_type, 3).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Math",
        topic="Advanced Math",
        i=i,
        question_text=text,
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Try factoring before using the quadratic formula.",
        skill_category=skill,
        estimated_time=70,
    )


def _math_problem_solving(i: int, exam_type: str) -> dict:
    if exam_type == "PSAT 8/9":
        packs = i % 3 + 2
        each = i % 4 + 3
        total = packs * each
        ans = str(total)
        opts = [ans, str(total + packs), str(total - each), str(packs + each)]
        text = (
            f"A teacher places {packs} equal stacks of worksheets on a table. "
            f"Each stack has {each} worksheets. How many worksheets are there in all?"
        )
        expl = f"Multiply stacks × worksheets: {packs} × {each} = {total}."
        skill = "Multiplication in context"
    elif exam_type == "PSAT":
        pct = i % 4 + 10
        base = (i % 5 + 4) * 10
        increase = base * pct // 100
        ans = str(base + increase)
        opts = [ans, str(base), str(increase), str(base + pct)]
        text = f"A club has {base} members and grows by {pct}%. How many members does it have now?"
        expl = f"{pct}% of {base} is {increase}. New total = {base + increase}."
        skill = "Percent increase"
    else:
        rate = i % 3 + 4
        hours = i % 4 + 3
        total = rate * hours
        ans = str(total)
        opts = [ans, str(total + rate), str(total - hours), str(rate + hours)]
        text = (
            f"A research assistant processes {rate} samples per hour. "
            f"At that rate, how many samples are processed in {hours} hours?"
        )
        expl = f"Rate × time: {rate} × {hours} = {total}."
        skill = "Problem Solving — rates"

    _rng(i, exam_type, 5).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Math",
        topic="Problem Solving",
        i=i,
        question_text=text,
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Translate the situation into multiplication, ratio, or percent.",
        skill_category=skill,
        estimated_time=65,
    )


def _math_data(i: int, exam_type: str) -> dict:
    if exam_type == "PSAT 8/9":
        vals = [6 + i % 3, 8 + i % 2, 10 + i % 2]
        ans = str(sum(vals) // len(vals))
        opts = [ans, str(int(ans) + 1), str(int(ans) - 1), str(max(vals))]
        text = f"The number of books read by three students were {vals[0]}, {vals[1]}, and {vals[2]}. What is the mean?"
        expl = f"Sum = {sum(vals)}. Mean = {sum(vals)} ÷ 3 = {ans}."
        skill = "Mean"
    elif exam_type == "PSAT":
        vals = [12 + i % 4, 15 + i % 3, 18 + i % 2, 21 + i % 2]
        ans = str(sum(vals) // len(vals))
        opts = [ans, str(int(ans) + 2), str(int(ans) - 1), str(max(vals))]
        text = f"Test scores for four students were {vals}. What is the mean score?"
        expl = f"Sum = {sum(vals)}. Mean = {sum(vals)} ÷ 4 = {ans}."
        skill = "Mean and data summaries"
    else:
        vals = [18 + i % 5, 22 + i % 4, 25 + i % 3, 30 + i % 2]
        sorted_vals = sorted(vals)
        med = (sorted_vals[1] + sorted_vals[2]) / 2
        ans = str(int(med)) if med == int(med) else str(med)
        opts = [ans, str(sorted_vals[0]), str(sorted_vals[-1]), str(sum(vals) // 4)]
        text = f"A data set is {vals}. What is the median?"
        expl = f"Ordered values: {sorted_vals}. Median = average of middle two = {ans}."
        skill = "Problem Solving and Data Analysis — median"

    _rng(i, exam_type, 7).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Math",
        topic="Data Analysis",
        i=i,
        question_text=text,
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Sort data before finding median; sum all values for mean.",
        skill_category=skill,
        estimated_time=60,
    )


def _math_geometry(i: int, exam_type: str) -> dict:
    if exam_type == "PSAT 8/9":
        side = i % 5 + 3
        ans = str(side * side)
        opts = [ans, str(side * 2), str(side + side), str(side * side + side)]
        text = f"A square has side length {side} units. What is its area in square units?"
        expl = f"Area of a square = side² = {side}² = {side*side}."
        skill = "Area of squares"
    elif exam_type == "PSAT":
        base = i % 5 + 4
        height = i % 4 + 3
        area = base * height // 2
        ans = str(area)
        opts = [ans, str(base * height), str(base + height), str(area + 2)]
        text = f"A triangle has a base of {base} units and a height of {height} units. What is its area?"
        expl = f"Area = ½ × base × height = ½ × {base} × {height} = {area}."
        skill = "Area of triangles"
    else:
        angle1 = 40 + i % 15
        angle2 = 50 + i % 20
        ans = f"{180 - angle1 - angle2}°"
        opts = [ans, f"{180 - angle1}°", f"{angle1 + angle2}°", "90°"]
        text = (
            f"In triangle ABC, angle A measures {angle1}° and angle B measures {angle2}°. "
            "What is the measure of angle C?"
        )
        expl = f"Triangle angles sum to 180°: C = 180 - {angle1} - {angle2} = {ans[:-1]}°."
        skill = "Additional Topics in Math — angles"

    _rng(i, exam_type, 11).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Math",
        topic="Geometry",
        i=i,
        question_text=text,
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Write the geometry formula before substituting values.",
        skill_category=skill,
        estimated_time=60,
    )


def _math_trig(i: int, exam_type: str) -> dict:
    if exam_type == "PSAT 8/9":
        opp, hyp = 3, 5
        ans = f"{opp}/{hyp}"
        opts = [ans, f"{hyp}/{opp}", "4/5", "3/4"]
        text = (
            "In a right triangle, the side opposite angle θ has length 3 and the hypotenuse has length 5. "
            "What is sin(θ)?"
        )
        expl = "sin(θ) = opposite/hypotenuse = 3/5."
        skill = "Basic right-triangle ratios"
    elif exam_type == "PSAT":
        k = i % 3 + 1
        ans = f"{3*k}/{5*k}"
        opts = [ans, f"{5*k}/{3*k}", f"{4*k}/{5*k}", f"{3*k}/{4*k}"]
        text = (
            f"In a right triangle with side lengths {3*k}, {4*k}, and {5*k}, "
            f"what is sin(θ) for the angle opposite the side of length {3*k}?"
        )
        expl = f"sin(θ) = opposite/hypotenuse = {3*k}/{5*k}."
        skill = "Right-triangle trigonometry"
    else:
        k = i % 4 + 1
        ans = f"{4*k}/{5*k}"
        opts = [ans, f"{3*k}/{5*k}", f"{5*k}/{4*k}", f"{4*k}/{3*k}"]
        text = (
            f"In a right triangle, sin(θ) = {3*k}/{5*k}. What is cos(θ)? "
            "(Use a {3*k}-{4*k}-{5*k} triangle.)"
        )
        expl = f"If opposite = {3*k} and hypotenuse = {5*k}, adjacent = {4*k}. cos(θ) = {4*k}/{5*k}."
        skill = "Additional Topics in Math — trigonometry"

    _rng(i, exam_type, 13).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Math",
        topic="Trigonometry",
        i=i,
        question_text=text,
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Sketch a labeled right triangle before computing ratios.",
        skill_category=skill,
        estimated_time=70,
    )


def _reading_comp(i: int, exam_type: str) -> dict:
    passages = {
        "PSAT 8/9": [
            (
                "Maya tracked her study time for two weeks. On weekdays she reviewed for 25 minutes each day, "
                "but on weekends she skipped review entirely. Her science teacher suggested that short, consistent "
                "practice sessions are more effective than occasional long cramming sessions.",
                "Short, regular practice is more effective than occasional cramming",
                "Informational — study habits",
            ),
            (
                "The town library added a seed exchange next to the gardening books. Patrons can take free packets "
                "and leave extras from their own gardens. Within a month, participation exceeded expectations, "
                "suggesting that low-cost community resources can encourage shared learning.",
                "Low-cost community resources can encourage shared participation",
                "Informational — community programs",
            ),
        ],
        "PSAT": [
            (
                "Urban planners studying commuter patterns found that neighborhoods with protected bike lanes saw "
                "a measurable drop in short car trips under two miles. The change was most pronounced near schools "
                "and transit stations, indicating that safe infrastructure can shift daily transportation choices.",
                "Safe bike infrastructure can reduce short car trips",
                "Social Science — transportation",
            ),
            (
                "Archaeologists reexamined pottery shards using portable spectroscopy tools that identify mineral "
                "content without removing samples from the site. The new method confirmed older theories about trade "
                "routes while reducing damage to fragile artifacts.",
                "New tools can confirm theories while protecting artifacts",
                "Science — archaeology methods",
            ),
        ],
        "SAT": [
            (
                "Economists analyzing remote-work adoption noted that productivity gains were uneven across industries. "
                "Knowledge-based teams reported stable output, while manufacturing supervisors struggled to replicate "
                "in-person quality checks. The findings suggest that workflow design, not location alone, determines "
                "whether distributed work succeeds.",
                "Workflow design largely determines whether remote work succeeds",
                "Social Science — labor trends",
            ),
            (
                "Neuroscience researchers observed that spaced review sessions produced stronger long-term recall than "
                "single intensive study blocks, even when total study time was held constant. Participants who returned "
                "to material across several days retained more detail one month later.",
                "Spaced review improves long-term retention more than cramming",
                "Science — learning and memory",
            ),
        ],
    }
    pool = passages[exam_type]
    passage, answer, skill = pool[i % len(pool)]
    opts = [
        answer,
        "The passage disproves all prior research on the topic",
        "The author argues that technology should be avoided",
        "The text focuses only on a single irrelevant detail",
    ]
    _rng(i, exam_type, 17).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Reading",
        topic="Reading Comprehension",
        i=i,
        question_text="Which choice best states the main idea of the text?",
        passage=passage,
        options=opts,
        answer=answer,
        explanation="The correct option reflects the central claim supported throughout the passage.",
        strategy_tip="Avoid extremes; the main idea should cover the full passage.",
        skill_category=skill,
        estimated_time=75 if exam_type != "PSAT 8/9" else 65,
    )


def _reading_vocab(i: int, exam_type: str) -> dict:
    words = {
        "PSAT 8/9": [
            ("assist", "help", "The tutor will assist students after school."),
            ("rapid", "quick", "There was a rapid change in weather."),
            ("observe", "watch", "Scientists observe bird migration each spring."),
            ("accurate", "correct", "Her summary was accurate and clear."),
        ],
        "PSAT": [
            ("pragmatic", "practical", "The committee took a pragmatic approach to budgeting."),
            ("ambiguous", "unclear", "The ending remained ambiguous."),
            ("concise", "brief", "Please keep your response concise."),
            ("diligent", "hardworking", "A diligent reviewer checked every citation."),
        ],
        "SAT": [
            ("meticulous", "careful", "The editor was meticulous about punctuation."),
            ("tenacious", "persistent", "A tenacious researcher repeated the trial."),
            ("equivocal", "ambiguous", "The spokesperson gave an equivocal answer."),
            ("astute", "perceptive", "An astute reader noticed the contradiction."),
        ],
    }
    word, meaning, sentence = words[exam_type][i % len(words[exam_type])]
    opts = [meaning, "confused", "hostile", "careless"]
    _rng(i, exam_type, 19).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Reading",
        topic="Vocabulary",
        i=i,
        question_text=f"As used in the sentence below, what does '{word}' most nearly mean?\n\n{sentence}",
        options=opts,
        answer=meaning,
        explanation=f"In context, '{word}' means {meaning}.",
        strategy_tip="Replace the word with each answer choice in the sentence.",
        skill_category="Craft and Structure — words in context",
        estimated_time=45,
    )


def _writing_grammar(i: int, exam_type: str) -> dict:
    sets = {
        "PSAT 8/9": [
            (
                "Which sentence is grammatically correct?",
                [
                    "The students is ready for class.",
                    "The student are ready for class.",
                    "The students are ready for class.",
                    "The students ready for class.",
                ],
                "The students are ready for class.",
                "Plural subject 'students' requires plural verb 'are'.",
                "Standard English Conventions — agreement",
            ),
            (
                "Which sentence is grammatically correct?",
                [
                    "Each of the players have a jersey.",
                    "Each of the players has a jersey.",
                    "Each of the players having a jersey.",
                    "Each of the players were a jersey.",
                ],
                "Each of the players has a jersey.",
                "'Each' is singular, so the verb must be 'has'.",
                "Standard English Conventions — agreement",
            ),
        ],
        "PSAT": [
            (
                "Which sentence is grammatically correct?",
                [
                    "Neither the coach nor the players was ready.",
                    "Neither the coach nor the players were ready.",
                    "Neither the coach nor the players is ready.",
                    "Neither the coach nor the players being ready.",
                ],
                "Neither the coach nor the players were ready.",
                "With a plural noun nearer the verb, use 'were'.",
                "Standard English Conventions — agreement",
            ),
            (
                "Which sentence is grammatically correct?",
                [
                    "The data shows a clear trend.",
                    "The data show a clear trend.",
                    "The data showing a clear trend.",
                    "The data has show a clear trend.",
                ],
                "The data show a clear trend.",
                "'Data' is plural and takes 'show'.",
                "Standard English Conventions — agreement",
            ),
        ],
        "SAT": [
            (
                "Which sentence is grammatically correct?",
                [
                    "The committee have voted to postpone the event.",
                    "The committee has voted to postpone the event.",
                    "The committee having voted to postpone the event.",
                    "The committee were voted to postpone the event.",
                ],
                "The committee has voted to postpone the event.",
                "Collective noun acting as one unit takes singular verb 'has'.",
                "Standard English Conventions — agreement",
            ),
            (
                "Which sentence is grammatically correct?",
                [
                    "Having finished the experiment, the samples were stored overnight.",
                    "Having finished the experiment, the researchers stored the samples overnight.",
                    "Having finished the experiment, the samples had been stored overnight by them.",
                    "Having finished the experiment, storage of the samples occurred overnight.",
                ],
                "Having finished the experiment, the researchers stored the samples overnight.",
                "Introductory phrase must modify the subject that follows ('researchers').",
                "Standard English Conventions — modifiers",
            ),
        ],
    }
    pool = sets[exam_type]
    text, opts, ans, expl, skill = pool[i % len(pool)]
    _rng(i, exam_type, 23).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Writing",
        topic="Grammar",
        i=i,
        question_text=text,
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Identify the subject and check verb form and modifier placement.",
        skill_category=skill,
        estimated_time=45,
    )


def _writing_writing(i: int, exam_type: str) -> dict:
    sets = {
        "PSAT 8/9": [
            (
                "It started raining during recess; ______, our class stayed inside and read.",
                ["however", "therefore", "for example", "meanwhile"],
                "therefore",
                "Rain caused staying inside, so 'therefore' shows result.",
                "Expression of Ideas — transitions",
            ),
        ],
        "PSAT": [
            (
                "The pilot trial produced inconclusive results; ______, the team redesigned the survey.",
                ["therefore", "however", "for instance", "meanwhile"],
                "therefore",
                "Inconclusive results led to redesign — cause and effect.",
                "Expression of Ideas — transitions",
            ),
            (
                "The museum curator loved historical maps; ______, she collected navigation tools from several centuries.",
                ["for example", "however", "therefore", "nevertheless"],
                "for example",
                "The second clause gives an example of her interest.",
                "Expression of Ideas — transitions",
            ),
        ],
        "SAT": [
            (
                "The initial prototype failed under stress testing; ______, engineers reinforced the frame before launch.",
                ["consequently", "meanwhile", "for example", "nevertheless"],
                "consequently",
                "Failure led to reinforcement — logical consequence.",
                "Expression of Ideas — transitions",
            ),
            (
                "The author admires the scientist's precision; ______, she questions the ethics of the experiment.",
                ["however", "therefore", "for example", "similarly"],
                "however",
                "Second clause contrasts admiration with ethical concern.",
                "Expression of Ideas — transitions",
            ),
        ],
    }
    pool = sets[exam_type]
    text, opts, ans, expl, skill = pool[i % len(pool)]
    _rng(i, exam_type, 29).shuffle(opts)
    return _row(
        exam_type=exam_type,
        subject="Writing",
        topic="Writing",
        i=i,
        question_text=f"Which choice completes the text with the most logical transition?\n\n{text}",
        options=opts,
        answer=ans,
        explanation=expl,
        strategy_tip="Match the transition to the logical relationship between clauses.",
        skill_category=skill,
        estimated_time=50,
    )


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


def generate_group(exam_type: str, subject: str, topic: str, count: int) -> list[dict]:
    gen = _GENERATORS.get((subject, topic))
    if not gen:
        return []
    return [{**gen(i, exam_type), "source": "exam_catalog"} for i in range(count)]
