"""Static benchmark assets: the interviewer system prompt, 100 questions with
mock candidate answers, and the multiple-choice memory exam.

The candidate is a fixed fictional persona ("Jordan Avery"). Every answer carries
one specific, unique fact so the final exam can probe recall of any given turn.
The exam emphasizes early and middle questions -- exactly the turns that Strategy B
prunes and Strategy C compacts -- so accuracy differences expose what each strategy
forgets.
"""
from __future__ import annotations

INTERVIEWER_SYSTEM_PROMPT = """You are a meticulous, experienced professional interviewer conducting a \
structured, long-form "get-to-know-you" interview with a single candidate. This document is your complete \
operating manual. Read it carefully and internalize it; it governs every turn you take for the entire \
duration of the interview. Below, after the manual, is your complete and fixed list of 100 questions, \
numbered 1 through 100. Your core job is to ask the candidate these questions ONE AT A TIME, strictly in \
their given order, beginning at question 1 and ending at question 100.

== YOUR MISSION ==
The purpose of this interview is to build a rich, accurate portrait of the candidate by eliciting clear, \
specific, first-person answers to each of the 100 questions. You are not here to evaluate, judge, grade, \
or score the candidate. You are here to ask, listen, acknowledge briefly, and move on to the next question. \
The value of this interview lives entirely in the candidate's answers, not in your commentary. Think of \
yourself as a careful documentarian: your questions are the scaffolding, and the candidate's responses are \
the substance you are helping to surface. A successful interview is one in which all 100 questions have been \
asked in order, each answer has been given room to stand on its own, and nothing has been rushed, skipped, \
merged, or editorialized.

== THE CARDINAL RULES (NON-NEGOTIABLE) ==
1. Ask exactly ONE question per turn. Never, under any circumstances, ask two or more questions in the same \
turn. Do not bundle, batch, or chain questions together. One turn, one question.
2. Ask the questions in strict numerical order, 1 through 100. Do not skip ahead. Do not reorder. Do not \
double back. Do not invent, improvise, or substitute your own questions for the ones on the list.
3. After you ask a question, STOP. Wait for the candidate's answer before you ask the next question. Never \
ask the next question until the candidate has responded to the current one.
4. Prefix every question you ask with its number in the form "Qn:" -- for example, "Q1:", "Q7:", "Q42:". \
The number you announce must always match the question's position on the master list.
5. Never reveal, dump, preview, paraphrase, or enumerate the remaining questions. The candidate should only \
ever see the single next question, never the list as a whole and never a look-ahead.
6. Keep your own turns short. A brief, warm, one-line acknowledgement of the previous answer is welcome, \
but it must be brief, and it must be immediately followed by the next numbered question.

== PACING AND TURN DISCIPLINE ==
This is a marathon, not a sprint. There are 100 questions, and you will move through them one turn at a \
time across many exchanges. Resist any urge to accelerate. If you feel tempted to "save time" by asking two \
related questions at once, do not. If you feel tempted to summarize several previous answers to show you \
were listening, do not -- a single short acknowledgement is enough. Your discipline around pacing is the \
single most important behavior in this entire interview. The candidate is relying on you to hold a steady, \
predictable rhythm: acknowledge briefly, then ask the next numbered question, then wait. Acknowledge, ask, \
wait. That three-beat rhythm repeats one hundred times.

== TONE AND RAPPORT ==
Be warm, curious, and genuinely interested, but economical with words. You are friendly without being \
chatty, attentive without being effusive. A good acknowledgement sounds like "Thanks, that's helpful." or \
"Got it -- appreciate the detail." and nothing more. Avoid gushing, avoid long reflections, avoid offering \
your own opinions or anecdotes. The spotlight stays on the candidate at all times. Never argue with, \
correct, or second-guess an answer; accept whatever the candidate says at face value and proceed.

== FORMATTING REQUIREMENTS ==
Every question turn must follow this shape: an optional short acknowledgement of the prior answer (one short \
sentence at most), followed by the next question on its own, prefixed with its number. Do not number your \
acknowledgements. Do not add headers, bullet lists, or multi-paragraph commentary. Do not restate the \
candidate's answer back to them in full. Keep the visual structure clean and predictable so the candidate \
always knows exactly which question they are being asked.

== HANDLING DIFFERENT CANDIDATE BEHAVIORS ==
- If the candidate gives a very short answer: accept it and move on. Do not pester them for elaboration \
unless the answer is completely empty. A terse answer is still a valid answer.
- If the candidate gives a very long, rambling answer: accept it graciously, give a one-line acknowledgement, \
and proceed to the next numbered question. Do not summarize their long answer back to them.
- If the candidate goes off-topic or asks you a question: answer briefly and politely if it is a simple \
logistical question, then gently steer back by asking the next numbered interview question. Do not get \
pulled into a long side conversation.
- If the candidate declines to answer a particular question: respect that completely, acknowledge it without \
pressure ("No problem at all."), and move on to the next numbered question.
- If the candidate seems confused about where you are in the sequence: briefly restate the current question \
number and the question itself, then wait. Never use this as an excuse to jump ahead.
- If the candidate gives an answer that could apply to several questions at once: still ask each remaining \
question in order anyway. Do not skip a question just because you think it was partially answered earlier.

== WHAT NOT TO DO (COMMON FAILURE MODES TO AVOID) ==
- Do NOT ask multiple questions in a single turn, even if they feel related or sequential.
- Do NOT skip questions you assume were "already covered."
- Do NOT reorder questions to group similar topics together.
- Do NOT preview, list, or hint at upcoming questions.
- Do NOT deliver long monologues, summaries, or reflections between questions.
- Do NOT inject your own opinions, preferences, or stories.
- Do NOT evaluate, rate, or score the candidate's answers.
- Do NOT lose track of the question number; always announce the correct one.
- Do NOT end the interview early; continue until question 100 has been asked and answered.

== WORKED EXAMPLES ==
Good turn (correct): "Thanks for sharing that. Q12: Do you play any musical instrument?"
Good turn (correct, no acknowledgement): "Q13: Who is your favorite musical artist?"
Bad turn (asks two questions -- never do this): "Q12: Do you play an instrument? And Q13: who's your \
favorite artist?"
Bad turn (skips ahead -- never do this): "Since you mentioned music, let's jump to Q52 about concerts."
Bad turn (over-summarizes -- never do this): "So far I've learned you grew up by the coast, studied \
engineering, love Rust, and play bass -- what a fascinating combination! Now, Q14..."
Bad turn (previews the list -- never do this): "Coming up I'll ask about your favorite book, film, and \
pets, but first, Q14: what is your favorite book?"

== WHY THIS DISCIPLINE MATTERS ==
A structured interview is only useful if it is administered consistently. Asking one clear question at a \
time, in a fixed order, with room for each answer, is what makes the resulting portrait trustworthy and \
comparable. When questions are bundled, skipped, or reordered, answers blur together and detail is lost. \
Your steady, one-question-at-a-time discipline is what protects the integrity of the whole exercise. Hold \
the line on it for all one hundred questions.

== HOW TO BEGIN ==
When the candidate indicates that they are ready to start, give a brief, friendly greeting and then ask \
question 1, prefixed with "Q1:". From there, proceed sequentially: acknowledge briefly, ask the next \
numbered question, and wait for the answer. Repeat this until you have asked and received an answer to \
question 100.

== ACKNOWLEDGEMENT PHRASE BANK ==
To keep your acknowledgements short, warm, and varied without ever drifting into long commentary, draw from \
phrases like these (or close variants). Each is a single short clause; never string several together: \
"Thanks for that." / "Got it, thank you." / "Appreciate the detail." / "That's helpful, thanks." / "Noted, \
thank you." / "Good to know." / "Thanks for sharing." / "Understood." / "Makes sense." / "Lovely, thank \
you." / "Great, thanks." / "Perfect, thank you." / "Wonderful." / "Thanks -- duly noted." / "Helpful, \
thanks." / "Appreciate it." / "Thank you for that." / "Got it." / "Good, thanks." / "Noted." Use them \
sparingly and rotate so you do not sound robotic, but never let an acknowledgement grow into a paragraph. \
The acknowledgement is a courtesy, not a content turn; its only job is to signal that you heard the answer \
before you move on to the next numbered question.

== EXTENDED PRINCIPLES (REINFORCEMENT) ==
The following principles restate and reinforce the rules above. They exist because consistency over one \
hundred turns is hard, and small drifts compound. Re-anchor on them whenever you are unsure.
- Principle of One: one turn carries exactly one question. If you ever find yourself typing the word "and" \
between two questions, stop and split them across turns. There is no exception to the one-question rule.
- Principle of Order: the master list is the single source of truth for sequence. The next question is \
always the lowest-numbered question you have not yet asked. Never let the conversation's drift change the \
order.
- Principle of the Pause: every question is followed by a wait. You do not get to ask the next question \
until an answer has arrived. The pause is sacred; it is what gives each answer room.
- Principle of Brevity: your words are overhead. The candidate's words are the product. Minimize the former \
to maximize the latter. A long interviewer turn is a defect, not a feature.
- Principle of Neutrality: you neither praise nor critique answers. "Methodical," "interesting," "unusual," \
"impressive" -- none of these belong in your acknowledgements. Accept and proceed.
- Principle of Fidelity: you ask the questions exactly as written. You may add the number prefix and a short \
acknowledgement, but you do not rewrite, soften, sharpen, or reinterpret the question text itself.
- Principle of Completion: the interview is not done until question 100 has been asked and answered. Do not \
wind down early, do not declare the interview "basically finished," and do not offer to "wrap up" before the \
hundredth answer is in.

== FREQUENTLY ASKED INTERNAL QUESTIONS ==
Q: The candidate's last answer seems to already cover the next question. Should I skip it? A: No. Ask the \
next numbered question anyway. Skipping breaks the sequence and the comparability of the interview.
Q: The candidate gave a one-word answer. Should I demand more? A: No. A one-word answer is a complete \
answer. Acknowledge it briefly and proceed.
Q: Two upcoming questions are very similar. May I combine them to save time? A: No. Ask each separately, in \
order, on its own turn.
Q: The candidate asked how many questions are left. May I tell them? A: You may say roughly how far along \
you are (e.g., "We're about a third of the way through.") but do not enumerate or preview the specific \
remaining questions.
Q: I lost track of which question is next. What do I do? A: Recall the highest-numbered question you have \
already asked, and ask the next one in sequence. When in doubt, re-read the master list below and continue \
from the lowest unasked number.
Q: The candidate wants to revisit an earlier answer. May they? A: Yes -- let them amend a previous answer \
briefly, acknowledge it, and then continue from where you were in the sequence. Do not restart.
Q: May I end early if the candidate seems tired? A: You may offer a short break, but the interview is only \
complete at question 100. Resume in order afterward.

== FINAL REMINDER BEFORE YOU BEGIN ==
Acknowledge briefly. Ask the next numbered question. Wait for the answer. Repeat exactly one hundred times, \
in order, one question per turn, never previewing, never skipping, never bundling, never editorializing. \
Hold this discipline from question 1 through question 100.

== CONDUCT, CONFIDENTIALITY, AND RECORD-KEEPING ==
Treat everything the candidate shares as private and handled with care. Do not speculate about the candidate \
beyond what they tell you, and do not draw inferences aloud. Your record of the interview is simply the \
ordered sequence of questions you asked and the answers you received; you are not building a profile, a \
ranking, or a recommendation. If the candidate shares something sensitive, receive it without comment beyond \
a brief, neutral acknowledgement, and continue with the next numbered question. Maintain the same even, \
professional, unhurried demeanor from the first question to the last, regardless of how long the interview \
runs or how the candidate's answers vary in length or tone. Your consistency is itself a form of respect: it \
signals to the candidate that every question, and every answer, is being given the same careful attention as \
every other. Never let fatigue, repetition, or the sheer length of the sequence erode the quality of your \
turns; the hundredth question deserves exactly the same clean, single-question, well-paced treatment as the \
first. If at any point you are uncertain how to proceed, default to the safest interpretation of these rules: \
ask the single next numbered question, prefixed correctly, and then wait. That default is almost always \
right, and it will carry you cleanly through all one hundred questions from start to finish without drift, \
without bundling, without skipping, and without commentary that competes with the candidate's own words.

THE 100 QUESTIONS:
"""

# Each entry: id, the interview question, and the candidate's canonical answer
# (containing a unique, memorable fact).
QUESTIONS = [
    {"id": 1, "question": "Where did you grow up?", "answer": "I grew up in the small coastal town of Marisol Bay in northern Oregon, about two hours from Portland."},
    {"id": 2, "question": "What city do you live in now?", "answer": "I currently live in Asheville, North Carolina, in a converted loft downtown."},
    {"id": 3, "question": "What is your current job title?", "answer": "I'm a Staff Reliability Engineer at a logistics technology company."},
    {"id": 4, "question": "What industry do you work in?", "answer": "I work in freight and supply-chain logistics software."},
    {"id": 5, "question": "How many years of professional experience do you have?", "answer": "I have eleven years of professional experience, all in software."},
    {"id": 6, "question": "What is your favorite programming language?", "answer": "My favorite programming language is Rust, mostly for its ownership model."},
    {"id": 7, "question": "What was the first computer you owned?", "answer": "The first computer I owned was a hand-me-down Gateway 2000 desktop from my uncle."},
    {"id": 8, "question": "What degree did you earn, and in what field?", "answer": "I earned a bachelor's degree in mechanical engineering, not computer science."},
    {"id": 9, "question": "Which university did you attend?", "answer": "I attended Carnegie Mellon University for my undergraduate degree."},
    {"id": 10, "question": "What was your favorite subject in school?", "answer": "My favorite subject in school was thermodynamics, surprisingly."},
    {"id": 11, "question": "What is your primary hobby outside of work?", "answer": "My primary hobby is restoring vintage mechanical watches."},
    {"id": 12, "question": "Do you play any musical instrument?", "answer": "Yes, I play the upright double bass in a community jazz trio."},
    {"id": 13, "question": "Who is your favorite musical artist?", "answer": "My favorite musical artist is the pianist Bill Evans."},
    {"id": 14, "question": "What is your favorite book?", "answer": "My favorite book is 'The Left Hand of Darkness' by Ursula K. Le Guin."},
    {"id": 15, "question": "What is your favorite film?", "answer": "My favorite film is the 1985 movie 'Ran' by Akira Kurosawa."},
    {"id": 16, "question": "Do you have any pets?", "answer": "I have a twelve-year-old greyhound named Pascal."},
    {"id": 17, "question": "What is your favorite food?", "answer": "My favorite food is Vietnamese bun cha, which I discovered while traveling."},
    {"id": 18, "question": "What food do you dislike the most?", "answer": "The food I dislike most is black licorice; I can't stand the taste."},
    {"id": 19, "question": "Coffee or tea?", "answer": "I'm firmly a tea person, specifically a strong Assam in the mornings."},
    {"id": 20, "question": "What is your favorite season?", "answer": "My favorite season is late autumn, around mid-November."},
    {"id": 21, "question": "What is your preferred mode of commute?", "answer": "I commute almost exclusively by bicycle, a steel-frame touring bike."},
    {"id": 22, "question": "What is the farthest you have ever traveled from home?", "answer": "The farthest I've traveled is to Ulaanbaatar, Mongolia, for a friend's wedding."},
    {"id": 23, "question": "What language are you currently trying to learn?", "answer": "I'm currently learning Portuguese, about six months in."},
    {"id": 24, "question": "Do you prefer mountains or the ocean?", "answer": "I strongly prefer mountains; I find the ocean a little unsettling."},
    {"id": 25, "question": "What is your favorite color?", "answer": "My favorite color is a deep teal, almost like oxidized copper."},
    {"id": 26, "question": "What sport do you follow most closely?", "answer": "I follow competitive cycling most closely, especially the spring classics."},
    {"id": 27, "question": "What is your typical wake-up time?", "answer": "I usually wake up at 5:40 in the morning without an alarm."},
    {"id": 28, "question": "Are you an early bird or a night owl?", "answer": "I'm decisively an early bird; I'm useless after about 9 pm."},
    {"id": 29, "question": "What is your favorite way to relax?", "answer": "I relax best by doing long-form crossword puzzles in pen."},
    {"id": 30, "question": "What is one skill you wish you had?", "answer": "I wish I could do proper freehand architectural sketching."},
    {"id": 31, "question": "What is your favorite city you've visited?", "answer": "My favorite city I've visited is Porto, Portugal."},
    {"id": 32, "question": "What is your go-to comfort meal?", "answer": "My go-to comfort meal is a bowl of congee with scallions and ginger."},
    {"id": 33, "question": "What is the name of your oldest friend?", "answer": "My oldest friend is named Theodora, but everyone calls her Teddy."},
    {"id": 34, "question": "How many siblings do you have?", "answer": "I have three siblings: two older sisters and one younger brother."},
    {"id": 35, "question": "What is your birth month?", "answer": "I was born in February, right around Valentine's Day."},
    {"id": 36, "question": "What is your favorite board game?", "answer": "My favorite board game is the cooperative game Pandemic."},
    {"id": 37, "question": "What is your preferred text editor?", "answer": "I use Neovim as my preferred editor and have for years."},
    {"id": 38, "question": "What is your favorite type of cuisine?", "answer": "My favorite cuisine overall is Lebanese, especially the mezze spreads."},
    {"id": 39, "question": "What is one cause you care deeply about?", "answer": "I care deeply about watershed conservation and clean rivers."},
    {"id": 40, "question": "What was your first job?", "answer": "My first job was as a bicycle mechanic at a shop called Cogwheel."},
    {"id": 41, "question": "What is your favorite quote or motto?", "answer": "My motto is 'measure twice, cut once,' inherited from my grandfather."},
    {"id": 42, "question": "Do you prefer working from home or an office?", "answer": "I strongly prefer the office; home is too distracting for me."},
    {"id": 43, "question": "What is your favorite holiday?", "answer": "My favorite holiday is the autumn equinox, which I celebrate with a big dinner."},
    {"id": 44, "question": "What kind of car do you drive?", "answer": "I drive a 2009 manual-transmission Honda Fit named Hazel."},
    {"id": 45, "question": "What is your favorite dessert?", "answer": "My favorite dessert is a dense Basque burnt cheesecake."},
    {"id": 46, "question": "What is a movie you can watch repeatedly?", "answer": "I can watch 'My Neighbor Totoro' endlessly."},
    {"id": 47, "question": "What is your shoe size?", "answer": "I wear a US men's size 11 shoe."},
    {"id": 48, "question": "What is your favorite kind of weather?", "answer": "My favorite weather is a cool, foggy morning around 50 degrees."},
    {"id": 49, "question": "What is your preferred social media platform?", "answer": "I mostly avoid social media, but I keep one account on Mastodon."},
    {"id": 50, "question": "What is your favorite animal?", "answer": "My favorite animal is the octopus, for its problem-solving intelligence."},
    {"id": 51, "question": "What is your favorite kind of music to work to?", "answer": "I work best to ambient techno, nothing with lyrics."},
    {"id": 52, "question": "What is the last concert you attended?", "answer": "The last concert I attended was a Kronos Quartet performance."},
    {"id": 53, "question": "What is your favorite vegetable?", "answer": "My favorite vegetable is roasted fennel, which most people overlook."},
    {"id": 54, "question": "What is your favorite indoor plant?", "answer": "I keep a large monstera named Gerald in my living room."},
    {"id": 55, "question": "Do you prefer print books or e-books?", "answer": "I strongly prefer print books; I like the physical margins for notes."},
    {"id": 56, "question": "What is your favorite time of day?", "answer": "My favorite time of day is the hour just before sunrise."},
    {"id": 57, "question": "What is a food you only recently started enjoying?", "answer": "I only recently started enjoying raw oysters, in the last year or so."},
    {"id": 58, "question": "What is your favorite type of footwear?", "answer": "My favorite footwear is a pair of resoleable leather Blundstone boots."},
    {"id": 59, "question": "What is your favorite number?", "answer": "My favorite number is 17, with no particular reason."},
    {"id": 60, "question": "What is your favorite kind of art?", "answer": "My favorite art form is woodblock printmaking, especially Japanese ukiyo-e."},
    {"id": 61, "question": "What is your dream travel destination?", "answer": "My dream destination is the fjords of western Norway."},
    {"id": 62, "question": "What is your favorite breakfast?", "answer": "My favorite breakfast is shakshuka with a runny egg and crusty bread."},
    {"id": 63, "question": "What is your preferred operating system?", "answer": "I run Arch Linux on my personal machines, by choice."},
    {"id": 64, "question": "What is your favorite kind of tree?", "answer": "My favorite tree is the coastal redwood, which I find humbling."},
    {"id": 65, "question": "What is one thing you collect?", "answer": "I collect vintage fountain pens, with about forty in my collection."},
    {"id": 66, "question": "What is your favorite drink, non-alcoholic?", "answer": "My favorite non-alcoholic drink is a homemade ginger switchel."},
    {"id": 67, "question": "What is your favorite type of weather event?", "answer": "I love a good thunderstorm, the louder the better."},
    {"id": 68, "question": "What is your favorite genre of fiction?", "answer": "My favorite fiction genre is speculative literary science fiction."},
    {"id": 69, "question": "What is your favorite kind of cheese?", "answer": "My favorite cheese is a well-aged Comte, ideally 24 months."},
    {"id": 70, "question": "What is your preferred note-taking method?", "answer": "I take all my notes by hand in dot-grid notebooks."},
    {"id": 71, "question": "What is your favorite museum?", "answer": "My favorite museum is the Mauritshuis in The Hague."},
    {"id": 72, "question": "What is a sport you played growing up?", "answer": "Growing up I competed in springboard diving until I was sixteen."},
    {"id": 73, "question": "What is your favorite kind of bread?", "answer": "My favorite bread is a dark, dense German pumpernickel."},
    {"id": 74, "question": "What is your favorite spice?", "answer": "My favorite spice is smoked paprika; I put it on almost everything."},
    {"id": 75, "question": "What is your favorite mode of exercise?", "answer": "My favorite exercise is bouldering at an indoor climbing gym."},
    {"id": 76, "question": "What is your favorite kind of weather to sleep in?", "answer": "I sleep best when it's cold enough to need a heavy wool blanket."},
    {"id": 77, "question": "What is your favorite app on your phone?", "answer": "My favorite phone app is a stargazing one called Stellarium."},
    {"id": 78, "question": "What is your favorite condiment?", "answer": "My favorite condiment is a Korean gochujang, by a wide margin."},
    {"id": 79, "question": "What is your favorite kind of vacation?", "answer": "My ideal vacation is a self-supported multi-day cycling tour."},
    {"id": 80, "question": "What is your favorite historical period?", "answer": "My favorite historical period is the Dutch Golden Age."},
    {"id": 81, "question": "What is your favorite kind of pie?", "answer": "My favorite pie is a tart sour-cherry pie with a lattice crust."},
    {"id": 82, "question": "What is your favorite writing instrument?", "answer": "My favorite pen is a Pilot Custom 823 with a fine nib."},
    {"id": 83, "question": "What is your favorite kind of soup?", "answer": "My favorite soup is a Hungarian goulash, thick and paprika-heavy."},
    {"id": 84, "question": "What is your preferred keyboard layout?", "answer": "I type on a Colemak layout, which I switched to years ago."},
    {"id": 85, "question": "What is your favorite flower?", "answer": "My favorite flower is the ranunculus, for its tightly layered petals."},
    {"id": 86, "question": "What is a TV show you recommend?", "answer": "I always recommend the documentary series 'The Blue Planet'."},
    {"id": 87, "question": "What is your favorite kind of nut?", "answer": "My favorite nut is the Marcona almond from Spain."},
    {"id": 88, "question": "What is your favorite mountain range?", "answer": "My favorite mountain range is the Dolomites in northern Italy."},
    {"id": 89, "question": "What is your favorite kind of weather for cycling?", "answer": "I love cycling in cool, dry weather right after a rain."},
    {"id": 90, "question": "What is your favorite type of tea?", "answer": "Beyond Assam, my favorite tea is a smoky Lapsang Souchong."},
    {"id": 91, "question": "What is your favorite kind of chair?", "answer": "My favorite chair is a worn leather Eames lounge replica."},
    {"id": 92, "question": "What is your favorite constellation?", "answer": "My favorite constellation is Orion, the first one I learned."},
    {"id": 93, "question": "What is your favorite kind of cookie?", "answer": "My favorite cookie is a chewy molasses-ginger cookie."},
    {"id": 94, "question": "What is your favorite material to work with?", "answer": "My favorite material to work with is brass; I like how it ages."},
    {"id": 95, "question": "What is your favorite kind of knot?", "answer": "My favorite knot is the bowline, which I use constantly."},
    {"id": 96, "question": "What is your favorite kind of weather sound?", "answer": "My favorite sound is rain on a metal roof."},
    {"id": 97, "question": "What is your favorite citrus fruit?", "answer": "My favorite citrus is the blood orange, for its color and tartness."},
    {"id": 98, "question": "What is your favorite kind of dance?", "answer": "My favorite dance is the Argentine tango, though I'm a beginner."},
    {"id": 99, "question": "What is your favorite kind of weather to read in?", "answer": "I love reading during a gray, drizzly afternoon."},
    {"id": 100, "question": "What is one word your friends would use to describe you?", "answer": "My friends would describe me with the word 'methodical'."},
]

assert len(QUESTIONS) == 100, "Expected exactly 100 questions"
assert len({q["id"] for q in QUESTIONS}) == 100, "Question ids must be unique"

# Multiple-choice memory exam. Weighted toward the beginning and middle of the
# sequence -- the turns most damaged by pruning/compaction. Each item has one
# correct option (matching the canonical answer) plus plausible distractors and a
# "none of the above" choice.
QUIZ = [
    {"question_id": 5, "prompt": "How many years of professional experience does the candidate have?",
     "options": {"a": "Seven years", "b": "Eleven years", "c": "Fifteen years", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 9, "prompt": "Which university did the candidate attend for their undergraduate degree?",
     "options": {"a": "MIT", "b": "Georgia Tech", "c": "Carnegie Mellon University", "d": "None of the above"},
     "correct": "c"},
    {"question_id": 14, "prompt": "What is the candidate's favorite book?",
     "options": {"a": "'The Left Hand of Darkness' by Ursula K. Le Guin", "b": "'Dune' by Frank Herbert", "c": "'Neuromancer' by William Gibson", "d": "None of the above"},
     "correct": "a"},
    {"question_id": 16, "prompt": "What kind of pet does the candidate have, and what is its name?",
     "options": {"a": "A cat named Pascal", "b": "A greyhound named Pascal", "c": "A greyhound named Hazel", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 22, "prompt": "What is the farthest place the candidate has traveled from home?",
     "options": {"a": "Reykjavik, Iceland", "b": "Ulaanbaatar, Mongolia", "c": "Porto, Portugal", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 25, "prompt": "What is the candidate's favorite color?",
     "options": {"a": "Burnt orange", "b": "Deep teal", "c": "Forest green", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 35, "prompt": "In what month was the candidate born?",
     "options": {"a": "February", "b": "November", "c": "August", "d": "None of the above"},
     "correct": "a"},
    {"question_id": 44, "prompt": "What kind of car does the candidate drive?",
     "options": {"a": "A 2009 manual Honda Fit named Hazel", "b": "A 2009 manual Honda Fit named Pascal", "c": "A Subaru Outback named Hazel", "d": "None of the above"},
     "correct": "a"},
    {"question_id": 50, "prompt": "What is the candidate's favorite animal?",
     "options": {"a": "The raven", "b": "The octopus", "c": "The greyhound", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 59, "prompt": "What is the candidate's favorite number?",
     "options": {"a": "7", "b": "23", "c": "17", "d": "None of the above"},
     "correct": "c"},
    {"question_id": 65, "prompt": "What does the candidate collect, and roughly how many do they have?",
     "options": {"a": "Vintage watches, about forty", "b": "Vintage fountain pens, about forty", "c": "Fountain pens, about a dozen", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 75, "prompt": "What is the candidate's favorite mode of exercise?",
     "options": {"a": "Indoor bouldering", "b": "Road cycling", "c": "Springboard diving", "d": "None of the above"},
     "correct": "a"},
]

# Build a quick lookup and sanity-check that every quiz item references a real
# question and that its correct option is genuinely supported by the answer.
_BY_ID = {q["id"]: q for q in QUESTIONS}
for item in QUIZ:
    assert item["question_id"] in _BY_ID, f"Quiz references unknown question {item['question_id']}"
    assert item["correct"] in item["options"], "Correct letter must be a valid option"


def answers_by_id() -> dict[int, str]:
    return {q["id"]: q["answer"] for q in QUESTIONS}


def build_question_list_block() -> str:
    """The numbered 100-question list embedded in the interviewer system prompt."""
    return "\n".join(f"{q['id']}. {q['question']}" for q in QUESTIONS)


def build_interviewer_system_prompt() -> str:
    """Full static system prompt = instructions + the 100-question block."""
    return INTERVIEWER_SYSTEM_PROMPT + build_question_list_block()
