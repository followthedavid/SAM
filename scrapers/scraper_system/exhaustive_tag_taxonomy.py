#!/usr/bin/env python3
"""
Exhaustive Tag Taxonomy - Complete Classification System

This is the definitive, comprehensive taxonomy for adult fiction content.
Every possible dimension is covered.
"""

# ============================================================================
# CONSENT SPECTRUM (Granular)
# ============================================================================

CONSENT_TAGS = {
    "enthusiastic_consent": {
        "keywords": [
            "yes", "please", "want you", "need you", "been waiting", "finally",
            "dreamed of this", "wanted this", "asking for it", "begging for it",
            "eager", "enthusiastic", "willing", "ready", "desperate for"
        ],
        "description": "Explicit, enthusiastic agreement"
    },
    "implied_consent": {
        "keywords": [
            "didn't stop", "let him", "allowed", "permitted", "went along",
            "didn't protest", "accepted", "submitted willingly"
        ],
        "description": "Consent implied but not explicit"
    },
    "reluctant_consent": {
        "keywords": [
            "reluctant", "hesitant", "unsure", "nervous", "scared but",
            "didn't want to but", "gave in", "eventually agreed", "talked into"
        ],
        "description": "Agreed but with reservations"
    },
    "dubious_consent": {
        "keywords": [
            "dubcon", "confused", "didn't understand", "intoxicated", "drunk",
            "high", "drugged", "half-asleep", "sleepy", "hypnotized", "spell",
            "mind control", "not thinking clearly", "overwhelmed"
        ],
        "description": "Ability to consent impaired"
    },
    "coerced_consent": {
        "keywords": [
            "had to", "no choice", "or else", "threatened", "blackmail",
            "leverage", "would tell", "would expose", "make you", "force you to",
            "if you don't", "consequences", "ruin you"
        ],
        "description": "Consent obtained through pressure/threats"
    },
    "non_consensual": {
        "keywords": [
            "rape", "forced", "assault", "against his will", "struggling",
            "fighting", "screaming", "crying", "begging to stop", "no no no",
            "please stop", "don't", "couldn't escape", "held down", "pinned",
            "trapped", "overpowered", "taken", "violated"
        ],
        "description": "No consent given"
    },
    "consensual_non_consent": {
        "keywords": [
            "cnc", "rape fantasy", "pretend", "roleplay", "scene", "safe word",
            "agreed beforehand", "planned", "discussed limits"
        ],
        "description": "Pre-negotiated non-consent play"
    },
}

# ============================================================================
# POWER DYNAMICS (Granular)
# ============================================================================

POWER_DYNAMICS_TAGS = {
    # Authority-based
    "teacher_student": ["teacher", "professor", "student", "pupil", "class", "grade", "detention"],
    "coach_athlete": ["coach", "athlete", "player", "team", "training", "practice", "scholarship"],
    "boss_employee": ["boss", "employee", "job", "office", "promotion", "fired", "raise"],
    "military_rank": ["sergeant", "private", "officer", "soldier", "orders", "sir", "barracks"],
    "religious_authority": ["priest", "pastor", "confession", "altar boy", "church", "sin", "salvation"],
    "medical_authority": ["doctor", "patient", "nurse", "exam", "procedure", "treatment"],
    "legal_authority": ["cop", "police", "officer", "arrest", "jail", "criminal", "lawyer", "judge"],
    "landlord_tenant": ["landlord", "rent", "evict", "tenant", "lease"],
    "guardian_ward": ["guardian", "ward", "custody", "foster", "care"],

    # Age-based
    "age_gap_mild": ["older", "younger", "few years", "college vs high school"],
    "age_gap_significant": ["much older", "could be his father", "twice his age", "generation"],
    "daddy_kink": ["daddy", "boy", "good boy", "little one", "baby", "son"],
    "experience_gap": ["experienced", "inexperienced", "virgin", "first time", "teaching", "showing"],

    # Physical
    "size_difference": ["bigger", "smaller", "towered over", "looked up at", "dwarfed"],
    "strength_difference": ["stronger", "weaker", "couldn't fight", "overpowered", "helpless"],

    # Social
    "class_difference": ["rich", "poor", "wealthy", "servant", "working class", "privileged"],
    "popularity_difference": ["popular", "outcast", "loser", "jock", "nerd", "cool kids"],
    "bully_victim": ["bully", "bullied", "picked on", "tormented", "target", "victim"],

    # Psychological
    "manipulation": ["manipulated", "gaslighting", "mind games", "confused", "twisted"],
    "emotional_dependency": ["need you", "can't live without", "obsessed", "addicted"],
    "blackmail": ["blackmail", "secret", "would tell", "leverage", "photos", "evidence"],
}

# ============================================================================
# RELATIONSHIP TYPES (Exhaustive)
# ============================================================================

RELATIONSHIP_TAGS = {
    # Familial (taboo)
    "father_son": ["father", "son", "dad", "daddy", "old man"],
    "stepfather_stepson": ["stepfather", "stepson", "stepdad", "mom's husband"],
    "brothers": ["brother", "bro", "sibling"],
    "stepbrothers": ["stepbrother", "step-brother", "mom's son"],
    "uncle_nephew": ["uncle", "nephew"],
    "grandfather": ["grandfather", "grandpa", "granddad"],
    "cousins": ["cousin"],

    # Romantic progression
    "strangers": ["stranger", "never met", "first meeting", "didn't know"],
    "acquaintances": ["knew of", "seen around", "barely knew"],
    "friends": ["friend", "buddy", "pal", "bro"],
    "best_friends": ["best friend", "closest friend", "known forever"],
    "roommates": ["roommate", "shared room", "dorm", "apartment"],
    "neighbors": ["neighbor", "next door", "across the hall"],
    "exes": ["ex", "used to date", "broke up", "former"],
    "dating": ["dating", "boyfriend", "seeing each other"],
    "married": ["husband", "married", "spouse", "wedding ring"],
    "affair": ["affair", "cheating", "behind his back", "secret"],

    # Circumstantial
    "classmates": ["classmate", "same class", "school"],
    "coworkers": ["coworker", "colleague", "work together"],
    "teammates": ["teammate", "team", "play together"],
    "rivals": ["rival", "competitor", "enemy", "hate each other"],

    # Transactional
    "prostitution": ["paid", "money", "hustler", "escort", "prostitute", "rent boy"],
    "sugar_relationship": ["sugar daddy", "allowance", "spoiled", "kept"],
    "porn": ["camera", "filming", "scene", "director", "porn"],
}

# ============================================================================
# CHARACTER ARCHETYPES (Exhaustive)
# ============================================================================

CHARACTER_ARCHETYPES = {
    # Physical types
    "twink": ["twink", "slim", "smooth", "hairless", "boyish", "lithe", "slender"],
    "jock": ["jock", "athlete", "muscular", "built", "ripped", "gym", "sports"],
    "bear": ["bear", "hairy", "burly", "stocky", "thick", "barrel chest"],
    "otter": ["otter", "hairy", "slim", "lean and hairy"],
    "daddy": ["daddy", "mature", "silver fox", "distinguished", "older man"],
    "cub": ["cub", "young bear", "chubby", "husky"],
    "muscle": ["muscle", "bodybuilder", "massive", "huge arms", "pecs"],
    "average": ["average", "normal build", "regular guy"],

    # Social types
    "nerd": ["nerd", "geek", "glasses", "smart", "bookworm", "shy"],
    "prep": ["prep", "preppy", "rich", "country club", "polo", "yacht"],
    "goth": ["goth", "dark", "black clothes", "piercings", "tattoos"],
    "punk": ["punk", "mohawk", "rebellious", "anarchist"],
    "hipster": ["hipster", "beard", "craft beer", "vinyl", "artsy"],
    "frat_boy": ["frat", "fraternity", "greek", "party", "bro culture"],

    # Personality types
    "innocent": ["innocent", "naive", "pure", "sheltered", "inexperienced"],
    "corrupted": ["corrupted", "fallen", "ruined", "tainted", "no longer innocent"],
    "bully": ["bully", "mean", "cruel", "aggressive", "intimidating"],
    "victim": ["victim", "target", "prey", "weak", "vulnerable"],
    "predator": ["predator", "hunter", "stalker", "pursuing"],
    "protector": ["protector", "defender", "saved him", "rescued"],
    "manipulator": ["manipulator", "schemer", "deceiver", "liar"],
    "seducer": ["seducer", "temptress", "charmer", "flirt"],
    "reluctant": ["reluctant", "hesitant", "unsure", "conflicted"],
    "eager": ["eager", "willing", "enthusiastic", "hungry for it"],

    # Role types
    "alpha": ["alpha", "leader", "dominant", "in charge", "top dog"],
    "beta": ["beta", "follower", "submissive", "takes orders"],
    "omega": ["omega", "lowest", "used by everyone", "communal"],
    "switch": ["switch", "versatile", "both ways", "either role"],

    # Occupation types
    "blue_collar": ["construction", "mechanic", "plumber", "trucker", "factory"],
    "white_collar": ["office", "suit", "executive", "businessman"],
    "military": ["soldier", "marine", "army", "navy", "uniform"],
    "law_enforcement": ["cop", "police", "detective", "officer"],
    "medical": ["doctor", "nurse", "paramedic", "surgeon"],
    "education": ["teacher", "professor", "tutor", "coach"],
    "creative": ["artist", "musician", "writer", "actor"],
    "service": ["waiter", "bartender", "barista", "delivery"],
}

# ============================================================================
# PHYSICAL DESCRIPTORS
# ============================================================================

PHYSICAL_DESCRIPTORS = {
    # Size (genital)
    "size_huge": ["huge", "massive", "monster", "enormous", "horse", "foot long"],
    "size_big": ["big", "thick", "fat cock", "well hung", "impressive"],
    "size_average": ["average", "normal", "decent"],
    "size_small": ["small", "little", "tiny", "cute"],

    # Body parts emphasized
    "ass_focus": ["ass", "bubble butt", "cheeks", "hole", "crack"],
    "cock_focus": ["cock", "dick", "member", "shaft", "head", "veiny"],
    "chest_focus": ["chest", "pecs", "nipples", "tits"],
    "abs_focus": ["abs", "six pack", "stomach", "treasure trail"],
    "arms_focus": ["arms", "biceps", "muscles", "forearms"],
    "feet_focus": ["feet", "toes", "soles", "arches"],
    "hands_focus": ["hands", "fingers", "grip"],

    # Body hair
    "smooth": ["smooth", "hairless", "shaved", "waxed"],
    "hairy": ["hairy", "fur", "chest hair", "happy trail", "bush"],
    "trimmed": ["trimmed", "groomed", "neat"],

    # Skin/appearance
    "tan": ["tan", "bronze", "sun-kissed"],
    "pale": ["pale", "fair", "white", "porcelain"],
    "tattoos": ["tattoo", "ink", "tattooed"],
    "piercings": ["piercing", "pierced", "ring", "stud"],

    # Age indicators
    "young_looking": ["young", "boyish", "baby face", "youthful"],
    "mature_looking": ["mature", "lines", "gray", "silver", "weathered"],
}

# ============================================================================
# ACTS (Exhaustive Taxonomy)
# ============================================================================

ACTS_TAXONOMY = {
    # Oral
    "blowjob": ["blowjob", "sucking", "suck", "mouth", "lips around", "deep throat"],
    "face_fucking": ["face fuck", "skull fuck", "throat fuck", "gagging", "choking on"],
    "rimming": ["rimming", "rim job", "tongue in ass", "ate his ass", "licking hole"],
    "ball_worship": ["balls", "sack", "licking balls", "tea bag"],

    # Anal
    "anal_penetration": ["fuck", "fucked", "penetrate", "inside", "enter", "thrust"],
    "anal_fingering": ["finger", "fingers inside", "stretched", "opened up"],
    "fisting": ["fist", "fisting", "whole hand", "stretched wide"],
    "double_penetration": ["double", "both holes", "two cocks", "dp"],
    "gaping": ["gape", "gaping", "wide open", "ruined"],

    # Masturbation
    "solo_masturbation": ["jerk", "stroke", "jack off", "masturbat", "hand on himself"],
    "mutual_masturbation": ["jerking each other", "stroking together", "mutual"],
    "handjob": ["handjob", "hand job", "jerked him", "stroked him"],

    # Group
    "threesome": ["threesome", "three way", "two guys", "both of them"],
    "gangbang": ["gangbang", "gang bang", "multiple", "one after another", "train"],
    "orgy": ["orgy", "group", "everyone", "pile"],
    "bukakke": ["bukakke", "covered in cum", "multiple loads"],

    # Voyeurism/Exhibitionism
    "watching": ["watched", "watching", "voyeur", "spying", "peeping"],
    "being_watched": ["being watched", "audience", "people watching", "on display"],
    "public_sex": ["public", "could be caught", "risky", "outside"],
    "glory_hole": ["glory hole", "hole in wall", "anonymous"],

    # BDSM
    "bondage": ["tied", "bound", "restrained", "rope", "handcuff", "chain"],
    "blindfold": ["blindfold", "couldn't see", "darkness"],
    "gag": ["gag", "gagged", "couldn't speak", "muffled"],
    "spanking": ["spank", "spanking", "slap", "paddle", "belt on ass"],
    "whipping": ["whip", "flog", "lash", "marks"],
    "cbt": ["ball torture", "cock torture", "squeeze", "pain"],
    "chastity": ["chastity", "cage", "locked", "denied"],

    # Specific kink acts
    "watersports": ["piss", "urine", "golden shower", "wet"],
    "cum_play": ["cum", "load", "swallow", "facial", "breeding"],
    "edging": ["edge", "edging", "denied", "almost", "not allowed"],
    "prostate": ["prostate", "p-spot", "milking", "hands free"],
    "toys": ["dildo", "vibrator", "plug", "toy", "beads"],
}

# ============================================================================
# SETTINGS (Exhaustive)
# ============================================================================

SETTINGS_TAXONOMY = {
    # Educational
    "high_school": ["high school", "locker", "hallway", "gym class", "detention"],
    "college": ["college", "dorm", "frat", "campus", "lecture"],
    "boarding_school": ["boarding school", "private school", "all boys"],

    # Sports
    "locker_room": ["locker room", "showers", "after practice", "towel"],
    "gym": ["gym", "weight room", "workout", "bench"],
    "field": ["field", "bleachers", "dugout", "behind"],
    "pool": ["pool", "swimming", "speedos", "wet"],

    # Work
    "office": ["office", "desk", "after hours", "conference room"],
    "construction": ["construction", "site", "trailer", "hard hat"],
    "retail": ["store", "back room", "stock room", "fitting room"],

    # Institutional
    "prison": ["prison", "cell", "inmates", "guard", "yard"],
    "military_base": ["barracks", "base", "tent", "deployment"],
    "hospital": ["hospital", "exam room", "gurney", "after hours"],
    "church": ["church", "sacristy", "confession", "pew"],

    # Private
    "bedroom": ["bedroom", "bed", "mattress", "sheets"],
    "bathroom": ["bathroom", "shower", "tub", "steam"],
    "living_room": ["couch", "sofa", "living room", "floor"],
    "basement": ["basement", "dungeon", "underground"],
    "garage": ["garage", "car", "backseat", "hood"],

    # Public
    "restroom": ["restroom", "bathroom", "stall", "urinal"],
    "park": ["park", "woods", "trail", "bench", "bushes"],
    "beach": ["beach", "sand", "dunes", "water"],
    "alley": ["alley", "behind", "dark", "urban"],
    "club": ["club", "bar", "dance floor", "back room"],
    "theater": ["theater", "movie", "dark", "seats", "back row"],

    # Transport
    "car": ["car", "backseat", "parked", "road trip"],
    "truck": ["truck", "cab", "trucker", "sleeper"],
    "plane": ["plane", "mile high", "bathroom"],
    "train": ["train", "compartment", "bathroom"],

    # Unusual
    "outdoor": ["outdoor", "nature", "camping", "tent", "woods"],
    "vacation": ["hotel", "vacation", "resort", "cruise"],
    "party": ["party", "drunk", "upstairs", "closet"],
}

# ============================================================================
# EMOTIONAL DIMENSIONS
# ============================================================================

EMOTIONAL_TAXONOMY = {
    # Positive
    "romantic": ["love", "tender", "gentle", "making love", "passionate", "intimate"],
    "playful": ["playful", "teasing", "fun", "laughing", "games"],
    "loving": ["loving", "caring", "affectionate", "devoted"],
    "worshipful": ["worship", "adore", "perfect", "beautiful", "god"],

    # Negative
    "dark": ["dark", "sinister", "evil", "twisted", "wrong"],
    "degrading": ["degrade", "humiliate", "worthless", "pathetic", "nothing"],
    "angry": ["angry", "rage", "hate", "revenge", "payback"],
    "sad": ["sad", "crying", "tears", "regret", "mistake"],

    # Complex
    "conflicted": ["conflicted", "shouldn't", "wrong but", "can't help"],
    "shameful": ["shame", "ashamed", "disgusted", "self-loathing"],
    "obsessive": ["obsessed", "can't stop", "addiction", "need"],
    "forbidden": ["forbidden", "taboo", "shouldn't", "wrong"],

    # Narrative
    "slow_burn": ["slowly", "building", "tension", "finally"],
    "instant": ["immediate", "sudden", "right away", "couldn't wait"],
    "reluctant_arousal": ["didn't want to but", "body betrayed", "against will but aroused"],
}

# ============================================================================
# IDENTITY/PSYCHOLOGICAL
# ============================================================================

IDENTITY_TAXONOMY = {
    # Sexual identity journey
    "closeted": ["closet", "hiding", "secret", "no one knows", "can't tell"],
    "questioning": ["questioning", "confused", "might be", "curious"],
    "first_realization": ["realized", "finally understood", "always knew"],
    "coming_out": ["came out", "told", "admitted", "confessed"],
    "out_and_proud": ["openly", "proud", "everyone knows"],

    # Sexual experience
    "virgin": ["virgin", "first time", "never done", "cherry"],
    "inexperienced": ["inexperienced", "new to this", "learning"],
    "experienced": ["experienced", "knew what", "skilled", "expert"],
    "corrupted_innocent": ["was innocent", "used to be", "before this", "ruined"],

    # Orientation play
    "gay_awakening": ["didn't know", "first time with", "awakening"],
    "straight_to_gay": ["straight", "not gay but", "just this once", "exception"],
    "bisexual": ["both", "also likes", "men and women"],
    "gay_for_you": ["only you", "never before", "just for you"],

    # Internalized issues
    "internalized_homophobia": ["wrong", "sin", "shouldn't", "disgust", "hate myself"],
    "denial": ["denial", "not gay", "doesn't count", "just experimenting"],
    "repression": ["repressed", "pushed down", "ignored", "finally"],
    "self_acceptance": ["accepted", "finally okay", "embraced", "comfortable"],

    # Psychological states
    "trauma": ["trauma", "flashback", "triggered", "past abuse"],
    "healing": ["healing", "recovery", "therapy", "getting better"],
    "addiction": ["addicted", "can't stop", "need it", "withdrawals"],
    "obsession": ["obsessed", "all I think about", "consuming", "stalking"],
}

# ============================================================================
# KINK TAXONOMY (Exhaustive)
# ============================================================================

KINK_TAXONOMY = {
    # Size related
    "size_kink": ["so big", "huge", "massive", "couldn't fit", "stretched"],
    "size_difference": ["bigger than", "towered", "small compared"],

    # Clothing/fetish
    "underwear": ["underwear", "briefs", "boxers", "jockstrap", "bulge"],
    "uniform": ["uniform", "dressed as", "still wearing"],
    "leather": ["leather", "gear", "harness", "boots"],
    "sportswear": ["jock", "singlet", "shorts", "sweaty gym clothes"],
    "formal_wear": ["suit", "tie", "dressed up", "fancy"],
    "cross_dressing": ["dress", "panties", "feminine", "girly"],

    # Body parts
    "feet": ["feet", "foot", "toes", "socks", "shoes", "worship feet"],
    "armpits": ["armpits", "pits", "musky", "hairy pits"],
    "muscles": ["muscles", "flex", "worship", "feel them"],
    "ass_worship": ["ass worship", "ate his ass", "face buried"],

    # Sensory
    "smell": ["smell", "scent", "musk", "inhale", "sniff"],
    "taste": ["taste", "flavor", "salty", "sweet"],
    "sweat": ["sweat", "sweaty", "worked out", "dripping"],
    "cum": ["cum", "load", "seed", "taste", "swallow", "covered"],

    # Control
    "orgasm_control": ["not allowed", "permission", "beg to cum", "denied"],
    "chastity": ["cage", "locked", "chastity", "no release"],
    "ownership": ["owned", "belong to", "property", "claimed", "marked"],
    "collaring": ["collar", "collared", "leash", "pet"],

    # Pain
    "pain_pleasure": ["hurt so good", "pain", "sting", "burn"],
    "impact_play": ["hit", "slap", "spank", "paddle", "belt"],
    "marks": ["bruises", "marks", "evidence", "hickeys", "bite"],

    # Verbal
    "dirty_talk": ["talked dirty", "verbal", "telling him", "describing"],
    "name_calling": ["slut", "whore", "bitch", "faggot", "pig"],
    "praise": ["good boy", "so good", "perfect", "beautiful"],
    "commands": ["ordered", "commanded", "told to", "demanded"],

    # Breeding
    "breeding": ["breed", "seed", "knock up", "put a baby"],
    "cum_inside": ["inside", "fill", "flood", "deep"],
    "cum_marking": ["mark", "covered", "dripping", "claim"],
    "multiple_loads": ["again", "another load", "kept going", "filled repeatedly"],

    # Miscellaneous
    "anonymous": ["anonymous", "didn't know", "stranger", "faceless"],
    "recorded": ["filmed", "camera", "video", "photos", "evidence"],
    "caught": ["caught", "walked in", "discovered", "exposed"],
    "public_risk": ["might get caught", "risky", "someone coming"],
}

# ============================================================================
# AFTERCARE & RELATIONSHIP DYNAMICS
# ============================================================================

AFTERCARE_TAXONOMY = {
    "aftercare_present": ["held him", "cuddled", "cleaned up", "took care", "gentle after"],
    "aftercare_absent": ["left him", "walked away", "alone after", "used and discarded"],
    "emotional_resolution": ["talked about", "discussed", "felt better", "understood"],
    "relationship_development": ["closer after", "meant something", "changed things"],
    "regret": ["regretted", "mistake", "shouldn't have", "felt wrong after"],
    "anticipation_next": ["again", "next time", "couldn't wait", "wanting more"],
}

# ============================================================================
# NARRATIVE ELEMENTS
# ============================================================================

NARRATIVE_TAXONOMY = {
    # POV
    "first_person_bottom": ["I felt him", "inside me", "he entered me"],
    "first_person_top": ["I pushed", "I entered", "I took"],
    "third_person": ["he felt", "they moved", "the two of them"],
    "second_person": ["you feel", "you moan", "your body"],

    # Tense
    "present_tense": ["is", "are", "feels", "takes"],
    "past_tense": ["was", "were", "felt", "took"],

    # Style
    "literary": ["prose", "descriptive", "metaphor", "literary"],
    "explicit_direct": ["fuck", "cock", "explicit", "graphic"],
    "euphemistic": ["member", "manhood", "shaft", "love"],
    "dialogue_heavy": ["said", "asked", "replied", "moaned"],
}

# ============================================================================
# BDSM PROTOCOLS & PRACTICES (Expanded)
# ============================================================================

BDSM_PROTOCOLS = {
    # Negotiation
    "negotiation": ["negotiated", "discussed limits", "safe word", "boundaries", "contract"],
    "checklist": ["checklist", "yes no maybe", "limits list", "hard limits", "soft limits"],
    "safe_word": ["safe word", "red yellow green", "mercy", "stop word"],

    # Training
    "slave_training": ["training", "being trained", "learning position", "protocols"],
    "pet_training": ["pet", "pup", "puppy play", "handler", "bark", "kennel"],
    "pony_training": ["pony", "pony play", "bit", "bridle", "trot", "stable"],

    # Positions
    "kneeling": ["kneel", "kneeling", "on his knees", "at his feet"],
    "presenting": ["present", "presenting", "display", "inspection"],
    "standing_position": ["stand", "attention", "inspection pose"],
    "crawling": ["crawl", "crawling", "on all fours", "hands and knees"],

    # Rituals
    "greeting_ritual": ["greeting", "ritual greeting", "proper greeting", "protocol"],
    "service": ["service", "serve", "serving", "domestic service", "butler"],
    "worship_ritual": ["worship", "foot worship", "body worship", "ritual worship"],

    # Punishment/Reward
    "punishment": ["punishment", "punished", "consequence", "discipline"],
    "reward": ["reward", "rewarded", "treat", "privilege", "earned"],
    "correction": ["correction", "corrected", "wrong behavior", "reminded"],
}

# ============================================================================
# LEATHER/FETISH COMMUNITY
# ============================================================================

LEATHER_COMMUNITY = {
    # Gear
    "full_leather": ["full leather", "leather from head to toe", "leather uniform"],
    "leather_harness": ["harness", "chest harness", "bulldog harness"],
    "leather_pants": ["leather pants", "leather jeans", "chaps"],
    "leather_boots": ["boots", "engineer boots", "combat boots", "wescos"],
    "leather_cap": ["muir cap", "leather cap", "biker cap"],
    "leather_vest": ["vest", "leather vest", "club vest", "patches"],
    "leather_jacket": ["leather jacket", "motorcycle jacket", "biker jacket"],
    "codpiece": ["codpiece", "exposed", "accessible"],

    # Rubber/latex
    "full_rubber": ["rubber", "latex", "full enclosure", "rubber suit"],
    "gas_mask": ["gas mask", "breath control", "rebreathing"],
    "rubber_hood": ["hood", "rubber hood", "encased"],

    # Accessories
    "collar_formal": ["formal collar", "locked collar", "ownership collar"],
    "cuffs": ["cuffs", "wrist cuffs", "ankle cuffs", "restraint cuffs"],
    "chains": ["chains", "chain leash", "chain bondage"],
    "locks": ["lock", "padlock", "locked", "keyholder"],
}

# ============================================================================
# BEAR/CUB COMMUNITY
# ============================================================================

BEAR_COMMUNITY = {
    # Types
    "polar_bear": ["polar bear", "silver bear", "white beard", "older bear"],
    "muscle_bear": ["muscle bear", "gym bear", "muscular and hairy"],
    "chub": ["chub", "chubby", "big belly", "soft"],
    "superchub": ["superchub", "very large", "huge belly"],
    "chaser": ["chaser", "into bears", "loves big men"],
    "admirer": ["admirer", "bear admirer", "appreciates size"],

    # Culture
    "bear_run": ["bear run", "bear event", "bear weekend"],
    "bear_bar": ["bear bar", "eagle", "bear night"],
    "bear_pride": ["bear pride", "bear flag", "bear community"],
}

# ============================================================================
# PUP/HANDLER COMMUNITY
# ============================================================================

PUP_COMMUNITY = {
    # Roles
    "alpha_pup": ["alpha pup", "lead pup", "pack leader"],
    "beta_pup": ["beta pup", "follower pup"],
    "omega_pup": ["omega pup", "pack omega", "lowest pup"],
    "stray": ["stray", "unowned pup", "looking for handler"],
    "handler": ["handler", "owner", "sir", "master"],

    # Gear
    "pup_hood": ["pup hood", "dog hood", "neoprene hood"],
    "pup_tail": ["tail", "pup tail", "butt plug tail"],
    "pup_mitts": ["mitts", "paw mitts", "pup paws"],
    "pup_collar": ["pup collar", "dog collar", "tag"],
    "pup_harness": ["pup harness", "dog harness"],

    # Behaviors
    "barking": ["bark", "barking", "woof", "arf"],
    "begging": ["beg", "begging", "paws up"],
    "fetching": ["fetch", "fetching", "bring it back"],
    "nuzzling": ["nuzzle", "nuzzling", "head pets"],
    "playing": ["play", "roughhousing", "wrestling"],
}

# ============================================================================
# DADDY/BOY DYNAMICS
# ============================================================================

DADDY_BOY_DYNAMICS = {
    # Daddy types
    "strict_daddy": ["strict daddy", "disciplinarian", "rules", "structure"],
    "gentle_daddy": ["gentle daddy", "nurturing", "caring daddy", "soft daddy"],
    "sugar_daddy": ["sugar daddy", "provides", "spoils", "gifts"],
    "leather_daddy": ["leather daddy", "Sir", "formal", "protocol"],

    # Boy types
    "good_boy": ["good boy", "obedient", "eager to please"],
    "brat": ["brat", "bratty", "talks back", "needs discipline"],
    "little": ["little", "age regression", "little space"],
    "boy_next_door": ["boy next door", "wholesome", "sweet"],

    # Dynamics
    "guidance": ["guidance", "teaching", "mentoring", "showing the way"],
    "structure": ["structure", "rules", "expectations", "schedule"],
    "reward_system": ["reward", "allowance", "treats", "privileges"],
    "care_taking": ["taking care of", "providing for", "protecting"],
}

# ============================================================================
# MASTER/SLAVE DYNAMICS
# ============================================================================

MASTER_SLAVE_DYNAMICS = {
    # Power exchange levels
    "total_power_exchange": ["tpe", "total power exchange", "24/7", "full ownership"],
    "partial_power_exchange": ["partial", "scene only", "bedroom only"],
    "consensual_slavery": ["consensual slavery", "willing slave", "chosen submission"],

    # Master types
    "strict_master": ["strict master", "demanding", "high protocol"],
    "benevolent_master": ["benevolent", "kind master", "fair but firm"],
    "sadistic_master": ["sadist", "enjoys pain", "cruel master"],

    # Slave types
    "pleasure_slave": ["pleasure slave", "sexual service", "body use"],
    "service_slave": ["service slave", "domestic", "household duties"],
    "pain_slave": ["pain slave", "masochist", "craves pain"],

    # Elements
    "slave_contract": ["contract", "slave contract", "terms", "agreement"],
    "slave_positions": ["positions", "slave positions", "display positions"],
    "slave_speech": ["slave speech", "this slave", "third person"],
    "slave_marks": ["brand", "tattoo", "permanent mark", "owned"],
}

# ============================================================================
# TOY/EQUIPMENT TAXONOMY
# ============================================================================

TOY_TAXONOMY = {
    # Dildos
    "dildo_realistic": ["realistic dildo", "lifelike", "veiny dildo"],
    "dildo_fantasy": ["fantasy dildo", "dragon", "werewolf", "alien"],
    "dildo_xl": ["xl dildo", "huge dildo", "monster dildo", "fist dildo"],
    "dildo_double": ["double dildo", "double ended", "share"],

    # Plugs
    "plug_small": ["small plug", "beginner plug", "training plug"],
    "plug_large": ["large plug", "xl plug", "stretching plug"],
    "plug_tail": ["tail plug", "puppy tail", "fox tail", "bunny tail"],
    "plug_vibrating": ["vibrating plug", "remote control", "app controlled"],
    "plug_inflatable": ["inflatable plug", "pump plug", "expanding"],

    # Sounds/urethral
    "sounds": ["sound", "urethral", "sounding", "penis plug"],

    # Vibrators
    "prostate_massager": ["prostate massager", "p-spot", "aneros"],
    "wand": ["wand", "magic wand", "hitachi"],

    # Pumps
    "cock_pump": ["cock pump", "penis pump", "enlargement"],
    "nipple_pump": ["nipple pump", "suction cups"],

    # Cock rings
    "cock_ring": ["cock ring", "ring", "restriction"],
    "ball_stretcher": ["ball stretcher", "weight", "stretching"],

    # Machines
    "fuck_machine": ["fuck machine", "fucking machine", "mechanical"],
    "milking_machine": ["milking machine", "milker", "extraction"],
}

# ============================================================================
# BONDAGE TYPES (Detailed)
# ============================================================================

BONDAGE_TAXONOMY = {
    # Rope
    "shibari": ["shibari", "kinbaku", "japanese bondage", "decorative"],
    "western_bondage": ["western bondage", "functional", "secure"],
    "suspension": ["suspension", "suspended", "hanging", "off the ground"],
    "partial_suspension": ["partial suspension", "semi-suspended"],
    "hogtie": ["hogtie", "hogtied", "hands to feet"],
    "spread_eagle": ["spread eagle", "spread out", "exposed"],

    # Restraints
    "handcuffs": ["handcuffs", "cuffed", "metal cuffs"],
    "leather_cuffs": ["leather cuffs", "wrist restraints"],
    "ankle_cuffs": ["ankle cuffs", "ankle restraints", "legs spread"],
    "collar_and_leash": ["collar", "leash", "led around"],

    # Furniture
    "st_andrews_cross": ["st andrews", "x-cross", "spread on cross"],
    "spanking_bench": ["spanking bench", "bent over bench"],
    "bondage_table": ["bondage table", "strapped down", "table"],
    "cage": ["cage", "caged", "locked in cage", "kennel"],
    "stocks": ["stocks", "pillory", "head and hands locked"],

    # Sensory
    "blindfold_bondage": ["blindfolded", "couldn't see", "darkness"],
    "hood_bondage": ["hood", "hooded", "sensory deprivation"],
    "earplugs": ["earplugs", "couldn't hear", "deaf"],
    "gag_bondage": ["gagged", "couldn't speak", "silenced"],

    # Full enclosure
    "mummification": ["mummified", "wrapped", "cocooned", "plastic wrap"],
    "vacuum_bed": ["vacuum bed", "vac bed", "latex envelope"],
    "sleep_sack": ["sleep sack", "body bag", "enclosed"],
}

# ============================================================================
# IMPACT IMPLEMENTS
# ============================================================================

IMPACT_TAXONOMY = {
    # Hands
    "bare_hand": ["hand", "bare hand", "palm", "slap"],
    "fist": ["fist", "punch", "closed fist"],

    # Paddles
    "paddle_leather": ["leather paddle", "strap"],
    "paddle_wood": ["wooden paddle", "fraternity paddle", "school paddle"],
    "paddle_silicone": ["silicone paddle", "flexible paddle"],

    # Straps
    "belt": ["belt", "leather belt", "doubled over"],
    "strap": ["strap", "tawse", "split strap"],

    # Canes
    "cane_rattan": ["rattan cane", "traditional cane"],
    "cane_bamboo": ["bamboo cane", "bamboo"],
    "cane_acrylic": ["acrylic cane", "clear cane", "evil stick"],
    "cane_carbon": ["carbon fiber", "dragon cane"],

    # Whips
    "flogger": ["flogger", "flog", "many tails"],
    "single_tail": ["single tail", "bullwhip", "signal whip"],
    "cat_o_nine": ["cat o nine tails", "cat", "nine tails"],
    "crop": ["crop", "riding crop", "leather tip"],

    # Other
    "switch": ["switch", "branch", "birch"],
    "ruler": ["ruler", "wooden ruler", "metal ruler"],
    "hairbrush": ["hairbrush", "brush", "over the knee"],
}

# ============================================================================
# EDGE PLAY / EXTREME
# ============================================================================

EDGE_PLAY = {
    # Breath play
    "choking": ["choked", "choking", "hand around throat", "squeeze"],
    "suffocation": ["suffocation", "smothering", "pillow", "hand over mouth"],
    "bagging": ["bag", "plastic bag", "breath play bag"],
    "drowning_play": ["held under", "water", "dunking"],

    # Blood play
    "cutting": ["cutting", "blade", "knife", "blood"],
    "needle_play": ["needle", "piercing", "temporary piercing"],

    # Fire play
    "fire_play": ["fire", "flame", "flash", "burn"],
    "wax_play": ["wax", "candle", "hot wax", "dripping"],
    "branding": ["brand", "branding", "permanent mark"],

    # Electricity
    "violet_wand": ["violet wand", "electricity", "zap", "spark"],
    "tens_unit": ["tens", "electric", "muscle stimulation"],
    "cattle_prod": ["cattle prod", "shock", "electric shock"],

    # Medical
    "medical_play": ["medical", "doctor", "exam", "procedure"],
    "sounds_urethral": ["sounding", "urethral", "sounds"],
    "catheters": ["catheter", "catheterization"],
    "enemas": ["enema", "cleaning", "filled", "retention"],
    "speculums": ["speculum", "opened up", "stretched open"],

    # Extreme insertion
    "fisting_anal": ["fisting", "fist", "whole hand", "elbow deep"],
    "extreme_depth": ["deep", "so deep", "bottomed out", "cervix"],
    "extreme_stretch": ["stretched", "gaping", "ruined", "loose"],
}

# ============================================================================
# SENSORY DETAIL CATEGORIES
# ============================================================================

SENSORY_DETAILS = {
    # Sounds
    "moaning": ["moan", "moaning", "groaning", "whimpering"],
    "screaming": ["scream", "screaming", "cry out", "yell"],
    "whispering": ["whisper", "whispered", "low voice", "murmured"],
    "grunting": ["grunt", "grunting", "primal sounds"],
    "wet_sounds": ["squelch", "wet sounds", "slapping", "slick"],
    "breathing": ["panting", "gasping", "heavy breathing", "ragged breath"],

    # Textures
    "skin_texture": ["smooth skin", "rough hands", "calloused", "soft"],
    "hair_texture": ["coarse hair", "soft hair", "wiry", "silky"],
    "fabric_texture": ["cotton", "silk", "leather", "denim"],

    # Temperatures
    "heat": ["hot", "warm", "burning", "feverish", "heated"],
    "cold": ["cold", "ice", "chilled", "goosebumps"],
    "contrast": ["ice and fire", "hot then cold", "temperature play"],

    # Tastes
    "salt": ["salty", "salt", "sweat taste", "tears"],
    "musk": ["musk", "musky", "masculine", "man smell"],
    "cum_taste": ["cum", "bitter", "salty sweet", "thick"],

    # Visual
    "eye_contact": ["eyes locked", "staring", "watching", "looked into"],
    "expressions": ["face contorted", "expression", "twisted in pleasure"],
    "body_reactions": ["twitching", "trembling", "shaking", "spasming"],
}

# ============================================================================
# TIME/ERA ELEMENTS
# ============================================================================

ERA_TAXONOMY = {
    # Historical
    "ancient": ["ancient", "greek", "roman", "gladiator", "slave"],
    "medieval": ["medieval", "knight", "squire", "castle", "dungeon"],
    "victorian": ["victorian", "gentleman", "servant", "proper"],
    "1920s": ["1920s", "prohibition", "speakeasy", "jazz age"],
    "1950s": ["1950s", "greaser", "jock", "sock hop", "drive in"],
    "1970s": ["1970s", "disco", "bathhouse", "leather bar", "clone"],
    "1980s": ["1980s", "aids crisis", "activism", "leather community"],

    # Modern
    "contemporary": ["modern", "contemporary", "present day", "smartphone"],
    "near_future": ["future", "near future", "advanced technology"],

    # Fantasy
    "fantasy_medieval": ["fantasy", "magic", "wizard", "elf", "orc"],
    "sci_fi": ["sci fi", "space", "alien", "cyberpunk", "android"],
    "supernatural": ["vampire", "werewolf", "demon", "angel", "supernatural"],
    "mythology": ["god", "demigod", "mythology", "olympus", "zeus"],
}

# ============================================================================
# CULTURAL/GEOGRAPHIC
# ============================================================================

CULTURAL_TAXONOMY = {
    # Settings by region
    "american_south": ["southern", "texas", "country", "rural america"],
    "new_york": ["new york", "manhattan", "brooklyn", "nyc"],
    "san_francisco": ["san francisco", "castro", "bay area"],
    "los_angeles": ["la", "los angeles", "hollywood", "west hollywood"],
    "european": ["european", "paris", "london", "berlin", "amsterdam"],
    "tropical": ["tropical", "island", "beach", "caribbean"],
    "rural": ["rural", "farm", "country", "isolated", "small town"],
    "urban": ["urban", "city", "downtown", "metropolitan"],

    # Cultural elements
    "military_culture": ["military", "honor", "duty", "brotherhood"],
    "sports_culture": ["sports", "team", "competition", "locker room"],
    "academic_culture": ["academic", "intellectual", "campus", "scholarly"],
    "blue_collar_culture": ["blue collar", "working class", "hard work"],
    "wealth_culture": ["wealthy", "elite", "privileged", "upper class"],
}

# ============================================================================
# INTENSITY LEVELS
# ============================================================================

INTENSITY_TAXONOMY = {
    # Explicit level
    "fade_to_black": ["fade to black", "implied", "suggestion", "left to imagination"],
    "soft_explicit": ["soft", "gentle", "romantic", "sensual"],
    "moderate_explicit": ["explicit", "detailed", "graphic"],
    "hard_explicit": ["hardcore", "extreme", "very graphic", "nothing left out"],

    # Emotional intensity
    "light_hearted": ["fun", "playful", "casual", "no strings"],
    "emotional": ["emotional", "feelings", "connection", "meaningful"],
    "intense": ["intense", "overwhelming", "consuming", "all-encompassing"],
    "devastating": ["devastating", "life-changing", "destroyed", "broken"],

    # Physical intensity
    "gentle_physical": ["gentle", "soft", "tender", "careful"],
    "passionate_physical": ["passionate", "hungry", "desperate", "urgent"],
    "rough_physical": ["rough", "hard", "aggressive", "brutal"],
    "violent_physical": ["violent", "painful", "damaging", "bloody"],
}

# ============================================================================
# PSYCHOLOGICAL ELEMENTS
# ============================================================================

PSYCHOLOGICAL_TAXONOMY = {
    # Mind states
    "subspace": ["subspace", "floating", "gone", "out of it", "deep"],
    "topspace": ["topspace", "in control", "powerful", "godlike"],
    "drop": ["drop", "subdrop", "crash", "coming down"],
    "high": ["high", "endorphins", "rush", "flying"],

    # Mental dynamics
    "mind_fuck": ["mind fuck", "psychological", "mental game", "confusion"],
    "gaslighting": ["gaslighting", "making him doubt", "reality"],
    "conditioning": ["conditioning", "trained response", "pavlovian"],
    "hypnosis": ["hypnosis", "trance", "hypnotized", "suggestion"],

    # Emotional manipulation
    "love_bombing": ["showered with attention", "overwhelming affection"],
    "withholding": ["withholding", "denied attention", "cold shoulder"],
    "intermittent_reinforcement": ["sometimes kind", "unpredictable", "hot and cold"],
    "isolation": ["isolated", "cut off", "only me", "no one else"],
}

# ============================================================================
# TROPES & SCENARIOS
# ============================================================================

TROPES_TAXONOMY = {
    # Classic scenarios
    "caught_masturbating": ["caught jerking", "walked in on", "didn't hear", "embarrassed"],
    "walked_in_on": ["walked in", "interrupted", "didn't knock", "caught them"],
    "truth_or_dare": ["truth or dare", "dare", "game", "spin the bottle"],
    "drunk_hookup": ["drunk", "party", "wasted", "beer goggles"],
    "mistaken_identity": ["thought he was", "dark room", "wrong person"],
    "stuck": ["stuck", "couldn't move", "trapped", "wedged"],
    "massage_turns_sexual": ["massage", "relaxing", "hands wandered", "tension"],
    "workout_buddies": ["gym", "spot me", "workout", "sweaty"],
    "skinny_dipping": ["skinny dip", "naked swimming", "pool", "lake"],
    "sharing_bed": ["only one bed", "share the bed", "no room", "close quarters"],
    "snowed_in": ["snowed in", "stuck together", "cabin", "blizzard"],
    "road_trip": ["road trip", "long drive", "car", "motel"],
    "camping": ["camping", "tent", "sleeping bag", "outdoors"],

    # Forbidden scenarios
    "cheating": ["cheating", "affair", "behind his back", "don't tell"],
    "secret_relationship": ["secret", "hiding", "no one can know", "forbidden"],
    "taboo_relationship": ["taboo", "shouldn't", "wrong", "forbidden"],
    "revenge_sex": ["revenge", "get back at", "make him jealous", "payback"],
    "hate_sex": ["hate", "enemies", "despise", "angry sex"],

    # First time scenarios
    "first_time_ever": ["first time", "virgin", "never done", "cherry"],
    "first_time_together": ["first time together", "finally", "been waiting"],
    "first_time_with_man": ["first time with a man", "never with a guy", "straight"],
    "first_time_bottoming": ["first time bottoming", "never bottomed", "new to this"],
    "first_time_topping": ["first time topping", "never topped"],

    # Discovery scenarios
    "sexuality_discovery": ["realized", "discovered", "awakening", "first attraction"],
    "kink_discovery": ["didn't know I liked", "surprised myself", "new kink"],
    "mutual_discovery": ["both realized", "same time", "mutual attraction"],
}

# ============================================================================
# POSITIONS (Detailed)
# ============================================================================

POSITIONS_TAXONOMY = {
    # Basic
    "missionary": ["missionary", "face to face", "looking into eyes", "on his back"],
    "doggy_style": ["doggy", "from behind", "on all fours", "hands and knees"],
    "cowboy": ["cowboy", "riding", "on top", "bouncing"],
    "reverse_cowboy": ["reverse cowboy", "facing away", "riding backwards"],
    "spooning": ["spooning", "side by side", "behind him", "lazy"],
    "standing": ["standing", "against the wall", "held up", "legs wrapped"],
    "69": ["69", "sixty nine", "mutual", "at the same time"],

    # Advanced
    "pile_driver": ["pile driver", "folded", "legs over head"],
    "pretzel": ["pretzel", "twisted", "contorted"],
    "butter_churner": ["butter churner", "upside down", "gravity"],
    "wheelbarrow": ["wheelbarrow", "holding legs", "lifted"],
    "frog": ["frog position", "spread wide", "knees bent"],
    "lotus": ["lotus", "sitting", "wrapped around", "intimate"],

    # Furniture-assisted
    "bent_over": ["bent over", "table", "desk", "counter"],
    "on_knees": ["on his knees", "kneeling", "floor"],
    "against_wall": ["against wall", "pressed", "pinned"],
    "in_chair": ["chair", "sitting", "lap", "straddling"],
    "on_stairs": ["stairs", "steps", "angled"],
    "in_shower": ["shower", "wet", "steam", "slippery"],
}

# ============================================================================
# FLUIDS & BODILY ELEMENTS
# ============================================================================

FLUIDS_TAXONOMY = {
    # Cum related
    "cum_swallowing": ["swallowed", "drank", "took his load", "every drop"],
    "cum_facial": ["facial", "face", "covered his face", "on his cheeks"],
    "cum_internal": ["came inside", "filled", "flooded", "bred"],
    "cum_external": ["pulled out", "on his back", "on his chest", "painted"],
    "cum_eating": ["ate", "licked up", "cleaned", "snowball"],
    "multiple_orgasms": ["came again", "second load", "kept cumming", "multiple"],
    "dry_orgasm": ["dry orgasm", "no cum", "prostate orgasm"],
    "ruined_orgasm": ["ruined", "stopped", "denied", "frustrated"],
    "forced_orgasm": ["made him cum", "forced", "couldn't help", "milked"],

    # Pre-cum
    "precum": ["precum", "leaking", "dripping", "wet spot"],
    "excessive_precum": ["so much precum", "soaked", "dripping wet"],

    # Sweat
    "sweat": ["sweat", "sweaty", "glistening", "dripping"],
    "post_workout_sweat": ["after workout", "gym sweat", "musky"],

    # Other
    "spit": ["spit", "drool", "saliva", "wet"],
    "tears": ["tears", "crying", "wet eyes", "streaming"],
}

# ============================================================================
# PACING & NARRATIVE STRUCTURE
# ============================================================================

PACING_TAXONOMY = {
    # Speed
    "slow_burn": ["slow burn", "building", "tension", "took their time"],
    "instant_chemistry": ["immediate", "instant", "right away", "couldn't wait"],
    "gradual_escalation": ["gradually", "slowly escalated", "building up"],
    "quick_encounter": ["quick", "fast", "hurried", "rushed"],

    # Structure
    "flashback": ["remembered", "flashback", "years ago", "back then"],
    "parallel_storylines": ["meanwhile", "at the same time", "elsewhere"],
    "epistolary": ["letter", "text", "message", "email"],
    "stream_of_consciousness": ["thoughts racing", "mind", "inner monologue"],

    # Length/depth
    "pwp": ["pwp", "porn without plot", "just sex"],
    "plot_with_porn": ["story", "plot", "character development", "narrative"],
    "one_shot": ["one shot", "standalone", "complete"],
    "series": ["series", "chapter", "part", "continued"],

    # Endings
    "happy_ending": ["happy ending", "together", "worked out", "happily"],
    "ambiguous_ending": ["ambiguous", "open ended", "uncertain"],
    "dark_ending": ["dark ending", "tragedy", "didn't work out", "loss"],
    "cliffhanger": ["cliffhanger", "to be continued", "unresolved"],
}

# ============================================================================
# SPECIFIC BODY PARTS (Granular)
# ============================================================================

BODY_PARTS_TAXONOMY = {
    # Face
    "lips": ["lips", "full lips", "kissable", "mouth"],
    "jaw": ["jaw", "jawline", "strong jaw", "chiseled"],
    "cheekbones": ["cheekbones", "angular", "sharp"],
    "eyes": ["eyes", "gaze", "stare", "looking"],
    "eyelashes": ["lashes", "eyelashes", "long lashes"],
    "eyebrows": ["eyebrows", "brow", "furrowed"],
    "nose": ["nose", "nuzzle", "breathing"],
    "ears": ["ears", "earlobe", "whispered", "nibbled"],
    "neck": ["neck", "throat", "adam's apple", "collarbone"],

    # Torso
    "shoulders": ["shoulders", "broad shoulders", "muscular shoulders"],
    "chest": ["chest", "pecs", "pectorals", "breast"],
    "nipples": ["nipples", "nips", "hardened", "perky"],
    "abs": ["abs", "stomach", "six pack", "washboard"],
    "v_line": ["v line", "apollo's belt", "hip lines"],
    "back": ["back", "shoulder blades", "spine", "muscles"],
    "lower_back": ["lower back", "dimples", "arch"],

    # Arms
    "biceps": ["biceps", "arms", "guns", "flexed"],
    "forearms": ["forearms", "veiny", "strong"],
    "hands": ["hands", "fingers", "grip", "palms"],
    "wrists": ["wrists", "delicate", "grabbed"],

    # Lower body
    "hips": ["hips", "hip bones", "grabbed hips"],
    "thighs": ["thighs", "legs", "thick thighs", "spread"],
    "calves": ["calves", "legs", "muscular"],
    "feet": ["feet", "toes", "soles", "arches"],
    "ankles": ["ankles", "delicate", "grabbed"],

    # Intimate
    "cock": ["cock", "dick", "member", "shaft", "length"],
    "balls": ["balls", "testicles", "sack", "heavy"],
    "taint": ["taint", "perineum", "between"],
    "hole": ["hole", "entrance", "opening", "pucker"],
    "prostate": ["prostate", "p-spot", "gland", "button"],
}

# ============================================================================
# VERBAL ELEMENTS
# ============================================================================

VERBAL_TAXONOMY = {
    # Dirty talk styles
    "commanding": ["do it", "now", "obey", "I said"],
    "degrading_verbal": ["worthless", "slut", "whore", "pathetic"],
    "praising": ["good boy", "perfect", "so good", "beautiful"],
    "begging": ["please", "need it", "give me", "more"],
    "narrating": ["describing", "telling", "you feel", "watching you"],
    "threatening": ["or else", "make you", "don't make me"],

    # Communication
    "nonverbal": ["no words", "silence", "just sounds", "wordless"],
    "minimal_dialogue": ["few words", "grunts", "brief"],
    "constant_talking": ["kept talking", "never stopped", "verbal"],

    # Languages/accents
    "foreign_language": ["language", "didn't understand", "accent"],
    "slang": ["slang", "crude", "vulgar", "street"],
    "formal_speech": ["formal", "proper", "sir", "eloquent"],
    "baby_talk": ["baby", "widdle", "cutesy"],
}

# ============================================================================
# CLOTHING STATES
# ============================================================================

CLOTHING_TAXONOMY = {
    # States of dress
    "fully_clothed": ["clothed", "dressed", "still wearing", "didn't undress"],
    "partially_clothed": ["half dressed", "shirt on", "pants around ankles"],
    "naked": ["naked", "nude", "bare", "nothing on"],
    "underwear_only": ["just underwear", "boxers", "briefs", "nothing else"],

    # Clothing removal
    "slow_undressing": ["slowly removed", "peeled off", "teasing"],
    "ripped_off": ["ripped", "tore off", "urgent", "desperate"],
    "left_on": ["kept on", "didn't remove", "through clothes"],

    # Specific items
    "jockstrap": ["jockstrap", "jock", "strap", "ass exposed"],
    "underwear_fetish": ["underwear", "sniffing", "wearing his"],
    "uniform_kept_on": ["still in uniform", "dressed as", "costume"],
    "formal_disheveled": ["tie loosened", "shirt unbuttoned", "messy suit"],
}

# ============================================================================
# AFTERMATH/CONSEQUENCES
# ============================================================================

AFTERMATH_TAXONOMY = {
    # Immediate
    "cuddling": ["cuddled", "held", "spooned", "embraced"],
    "cleaning_up": ["cleaned up", "shower", "wiped", "tissues"],
    "round_two": ["again", "ready for more", "second round", "recovered"],
    "passing_out": ["passed out", "fell asleep", "exhausted", "collapsed"],

    # Emotional aftermath
    "post_coital_clarity": ["clarity", "what did we do", "realization"],
    "regret": ["regret", "mistake", "shouldn't have", "what have I done"],
    "satisfaction": ["satisfied", "content", "happy", "fulfilled"],
    "craving_more": ["wanting more", "addicted", "need it again", "hooked"],

    # Relationship aftermath
    "awkwardness": ["awkward", "couldn't look", "embarrassed", "next day"],
    "relationship_change": ["changed everything", "different now", "can't go back"],
    "secret_keeping": ["our secret", "don't tell", "between us", "no one knows"],
    "caught_consequences": ["someone found out", "exposed", "discovered", "told"],
}

# ============================================================================
# GENRE CROSSOVERS
# ============================================================================

GENRE_TAXONOMY = {
    # Sports
    "football": ["football", "quarterback", "tackle", "locker room"],
    "baseball": ["baseball", "pitcher", "dugout", "bat"],
    "basketball": ["basketball", "court", "dunk", "shower"],
    "wrestling": ["wrestling", "mat", "singlet", "pin"],
    "swimming": ["swimming", "pool", "speedos", "dive"],
    "hockey": ["hockey", "ice", "locker room", "pads"],
    "rugby": ["rugby", "scrum", "muddy", "pitch"],
    "mma": ["mma", "fighting", "cage", "submission"],

    # Professions
    "firefighter": ["firefighter", "fireman", "station", "hose"],
    "paramedic": ["paramedic", "ambulance", "emergency"],
    "pilot": ["pilot", "cockpit", "flight", "captain"],
    "chef": ["chef", "kitchen", "restaurant", "cook"],
    "musician": ["musician", "band", "backstage", "groupie"],
    "actor": ["actor", "set", "trailer", "costar"],

    # Settings
    "college_life": ["college", "dorm", "frat", "campus", "party"],
    "military_life": ["military", "barracks", "deployment", "service"],
    "prison_life": ["prison", "cell", "inmate", "guard"],
    "office_life": ["office", "corporate", "boss", "coworker"],
}

# ============================================================================
# SPECIFIC KINK SUBCATEGORIES
# ============================================================================

KINK_SUBCATEGORIES = {
    # Humiliation types
    "verbal_humiliation": ["called names", "degraded verbally", "told he was"],
    "physical_humiliation": ["displayed", "exposed", "shown off"],
    "public_humiliation": ["in front of others", "everyone saw", "witnessed"],
    "self_humiliation": ["made to say", "admit", "confess"],

    # Objectification types
    "furniture_use": ["used as furniture", "footstool", "seat"],
    "toy_treatment": ["treated as toy", "played with", "used"],
    "animal_treatment": ["treated as pet", "animal", "beast"],
    "thing_treatment": ["thing", "object", "it", "property"],

    # Service types
    "domestic_service": ["cleaning", "cooking", "household", "chores"],
    "body_service": ["massage", "bathing", "grooming", "dressing"],
    "sexual_service": ["pleasure", "servicing", "attending to"],
    "protocol_service": ["protocol", "ritual", "ceremony", "formal"],

    # Worship types
    "cock_worship": ["worshipped his cock", "devoted to", "adored"],
    "body_worship": ["worshipped his body", "every inch", "kissed all over"],
    "foot_worship": ["worshipped his feet", "kissed feet", "licked soles"],
    "muscle_worship": ["worshipped muscles", "felt biceps", "traced abs"],
}

# ============================================================================
# AGE/GENERATION DYNAMICS
# ============================================================================

AGE_DYNAMICS = {
    # Age gaps
    "same_age": ["same age", "peers", "classmates", "contemporaries"],
    "few_years": ["few years older", "couple years", "slight gap"],
    "decade_gap": ["ten years", "decade", "significantly older"],
    "generation_gap": ["generation", "could be father", "old enough"],
    "silver_fox": ["silver", "gray hair", "distinguished", "mature"],

    # Life stages
    "college_age": ["college", "university", "student", "early 20s"],
    "young_professional": ["young professional", "starting career", "mid 20s"],
    "established_adult": ["established", "career", "30s", "40s"],
    "mature": ["mature", "experienced", "older", "50s plus"],
    "retired": ["retired", "leisure", "free time"],
}

# ============================================================================
# ETHNICITY/APPEARANCE DIVERSITY
# ============================================================================

APPEARANCE_DIVERSITY = {
    # Skin tones
    "fair_skin": ["fair", "pale", "porcelain", "light"],
    "olive_skin": ["olive", "mediterranean", "tan"],
    "brown_skin": ["brown", "caramel", "mocha"],
    "dark_skin": ["dark", "ebony", "chocolate"],
    "freckled": ["freckled", "freckles", "spotted"],
    "blemished": ["acne", "scars", "imperfect"],

    # Hair colors
    "blond_hair": ["blond", "blonde", "golden", "fair hair"],
    "brown_hair": ["brown hair", "brunette", "chestnut"],
    "black_hair": ["black hair", "dark hair", "raven"],
    "red_hair": ["red hair", "ginger", "auburn", "copper"],
    "gray_hair": ["gray", "silver", "white hair", "salt and pepper"],
    "dyed_hair": ["dyed", "colored", "highlights", "unnatural"],

    # Hair styles
    "short_hair": ["short hair", "buzzed", "crew cut", "fade"],
    "long_hair": ["long hair", "ponytail", "bun", "flowing"],
    "curly_hair": ["curly", "wavy", "ringlets"],
    "bald": ["bald", "shaved head", "no hair"],
    "facial_hair": ["beard", "stubble", "mustache", "goatee"],

    # Eye colors
    "blue_eyes": ["blue eyes", "icy", "sky blue"],
    "green_eyes": ["green eyes", "emerald", "hazel"],
    "brown_eyes": ["brown eyes", "dark eyes", "chocolate"],
    "gray_eyes": ["gray eyes", "silver", "steel"],
}

# ============================================================================
# EMOTIONAL STATES (Granular)
# ============================================================================

EMOTIONAL_STATES = {
    # Positive arousal
    "desire": ["wanted", "craved", "needed", "longed for"],
    "lust": ["lust", "hungry", "desperate", "burning"],
    "adoration": ["adored", "worshipped", "devoted", "loved"],
    "euphoria": ["euphoric", "ecstatic", "blissful", "high"],
    "contentment": ["content", "satisfied", "peaceful", "calm"],

    # Negative arousal
    "shame": ["ashamed", "embarrassed", "humiliated", "mortified"],
    "guilt": ["guilty", "wrong", "shouldn't", "regret"],
    "fear": ["afraid", "scared", "terrified", "anxious"],
    "anger": ["angry", "furious", "rage", "mad"],
    "disgust": ["disgusted", "repulsed", "sick", "revolted"],

    # Complex emotions
    "conflicted": ["conflicted", "torn", "mixed feelings", "confused"],
    "overwhelmed": ["overwhelmed", "too much", "couldn't handle", "flooded"],
    "vulnerable": ["vulnerable", "exposed", "open", "defenseless"],
    "powerful": ["powerful", "in control", "dominant", "commanding"],
    "helpless": ["helpless", "powerless", "couldn't stop", "at mercy"],

    # Transitional
    "surrendering": ["surrendered", "gave in", "let go", "submitted"],
    "resisting": ["resisted", "fought", "struggled", "refused"],
    "accepting": ["accepted", "embraced", "welcomed", "allowed"],
    "denying": ["denied", "refused", "wouldn't admit", "pretended"],
}

# ============================================================================
# SENSORY EXPERIENCES (Expanded)
# ============================================================================

SENSORY_EXPANDED = {
    # Touch sensations
    "electric_touch": ["electric", "spark", "tingling", "charged"],
    "gentle_touch": ["gentle", "soft", "featherlight", "caress"],
    "rough_touch": ["rough", "calloused", "firm", "demanding"],
    "burning_touch": ["burning", "hot", "searing", "fire"],
    "cooling_touch": ["cool", "cold", "ice", "refreshing"],

    # Pain sensations
    "sharp_pain": ["sharp", "stinging", "piercing", "cutting"],
    "dull_pain": ["dull", "aching", "throbbing", "deep"],
    "burning_pain": ["burning", "fire", "searing", "hot"],
    "pleasurable_pain": ["hurt so good", "good pain", "wanted more"],

    # Pleasure sensations
    "building_pleasure": ["building", "growing", "mounting", "escalating"],
    "peak_pleasure": ["peak", "climax", "explosion", "release"],
    "afterglow": ["afterglow", "floating", "warm", "satisfied"],
    "overstimulation": ["too much", "overstimulated", "couldn't take", "overwhelming"],

    # Fullness sensations
    "stretched": ["stretched", "full", "stuffed", "opened"],
    "emptiness": ["empty", "needing", "wanting", "hollow"],
    "pressure": ["pressure", "pressing", "pushing", "deep"],
}

# ============================================================================
# SOCIAL CONTEXTS
# ============================================================================

SOCIAL_CONTEXTS = {
    # Event types
    "wedding": ["wedding", "reception", "ceremony", "bachelor party"],
    "funeral": ["funeral", "wake", "grief", "mourning"],
    "graduation": ["graduation", "ceremony", "celebration"],
    "reunion": ["reunion", "saw him again", "years later"],
    "party": ["party", "celebration", "gathering", "event"],
    "holiday": ["holiday", "christmas", "thanksgiving", "vacation"],

    # Social settings
    "family_gathering": ["family", "relatives", "parents", "siblings"],
    "work_event": ["work event", "conference", "meeting", "team"],
    "school_event": ["school", "prom", "dance", "game"],
    "club_scene": ["club", "bar", "nightlife", "dancing"],

    # Social dynamics
    "public_display": ["public", "everyone watching", "on display"],
    "private_moment": ["private", "alone", "just us", "intimate"],
    "group_dynamic": ["group", "multiple people", "crowd"],
    "one_on_one": ["one on one", "just the two", "alone together"],
}

# ============================================================================
# FANTASY ELEMENTS
# ============================================================================

FANTASY_ELEMENTS = {
    # Supernatural beings
    "vampire": ["vampire", "fangs", "blood", "immortal", "bite"],
    "werewolf": ["werewolf", "wolf", "transform", "moon", "pack"],
    "demon": ["demon", "hellfire", "corruption", "dark magic"],
    "angel": ["angel", "wings", "divine", "fallen", "celestial"],
    "incubus": ["incubus", "succubus", "sex demon", "feeds on"],
    "ghost": ["ghost", "spirit", "haunting", "possession"],
    "fae": ["fae", "fairy", "sidhe", "glamour", "enchantment"],

    # Transformation
    "transformation": ["transformed", "changed", "became", "shifted"],
    "possession": ["possessed", "taken over", "not himself"],
    "corruption": ["corrupted", "tainted", "dark influence"],
    "purification": ["purified", "cleansed", "saved", "redeemed"],

    # Powers
    "telepathy": ["read minds", "telepathy", "mental connection"],
    "empathy_power": ["felt his emotions", "empathic", "shared feelings"],
    "compulsion": ["compelled", "couldn't resist", "had to obey"],
    "shapeshifting": ["shapeshifted", "changed form", "disguised"],
    "enhanced_senses": ["smelled", "heard heartbeat", "saw in dark"],
    "super_strength": ["superhuman", "impossible strength", "lifted easily"],
    "healing_power": ["healed", "regenerated", "recovered instantly"],
}

# ============================================================================
# OMEGAVERSE SPECIFIC
# ============================================================================

OMEGAVERSE = {
    # Dynamics
    "alpha_omega": ["alpha", "omega", "presented", "dynamic"],
    "beta": ["beta", "neutral", "normal"],
    "alpha_alpha": ["two alphas", "alpha clash", "dominance fight"],
    "omega_omega": ["two omegas", "omega pair", "nest"],

    # Biology
    "heat": ["heat", "in heat", "heat cycle", "burning up"],
    "rut": ["rut", "rutting", "aggressive", "instincts"],
    "knotting": ["knot", "knotting", "locked", "tied"],
    "bonding": ["bond", "bonding", "mated", "claimed"],
    "scenting": ["scent", "scenting", "marked", "covered in scent"],
    "nesting": ["nest", "nesting", "safe space", "comfort"],
    "slick": ["slick", "wet", "self-lubricating", "dripping"],

    # Social
    "pack_dynamics": ["pack", "pack alpha", "hierarchy"],
    "claiming": ["claimed", "mine", "marked", "belonging"],
    "courtship": ["courting", "gifts", "wooing", "pursuit"],
}

# ============================================================================
# ROLEPLAY SCENARIOS
# ============================================================================

ROLEPLAY_SCENARIOS = {
    # Classic
    "doctor_patient": ["doctor", "patient", "exam", "checkup"],
    "teacher_student_rp": ["teacher", "student", "lesson", "detention"],
    "cop_criminal": ["cop", "arrest", "criminal", "interrogation"],
    "boss_secretary": ["boss", "secretary", "office", "overtime"],
    "stranger_fantasy": ["stranger", "anonymous", "don't know you"],

    # Costumes
    "uniform_roleplay": ["uniform", "dressed as", "costume"],
    "superhero": ["superhero", "villain", "powers", "secret identity"],
    "historical_costume": ["period", "historical", "costume", "era"],

    # Power exchange
    "pet_play_rp": ["pet", "owner", "good boy", "treat"],
    "slave_auction": ["auction", "sold", "bought", "bidding"],
    "kidnapping_rp": ["kidnapped", "captured", "held", "ransom"],
    "interrogation_rp": ["interrogation", "question", "make talk", "information"],

    # Taboo roleplay
    "age_play_rp": ["daddy", "boy", "little", "grown up"],
    "incest_roleplay": ["pretend", "family", "brother", "father"],
    "dubcon_roleplay": ["pretend resist", "act reluctant", "scene"],
}

# ============================================================================
# WRITING STYLE MARKERS
# ============================================================================

WRITING_STYLE = {
    # Perspective depth
    "deep_pov": ["felt", "thought", "knew", "realized", "inside his head"],
    "surface_pov": ["he did", "happened", "action", "external"],
    "omniscient": ["both felt", "they each", "neither knew"],
    "unreliable": ["thought he knew", "didn't realize", "wrong about"],

    # Sensory focus
    "visual_focus": ["saw", "watched", "looked", "eyes", "vision"],
    "tactile_focus": ["felt", "touched", "sensation", "skin"],
    "auditory_focus": ["heard", "sound", "voice", "moaned"],
    "olfactory_focus": ["smelled", "scent", "aroma", "musk"],

    # Pacing markers
    "action_heavy": ["then", "next", "suddenly", "quickly"],
    "description_heavy": ["was", "had", "with", "beautiful"],
    "dialogue_heavy": ["said", "asked", "replied", "told"],
    "introspection_heavy": ["thought", "wondered", "felt", "knew"],

    # Tone markers
    "humorous": ["laughed", "joked", "funny", "smiled"],
    "serious": ["serious", "grave", "important", "somber"],
    "romantic": ["love", "tender", "gentle", "sweet"],
    "raw": ["raw", "brutal", "honest", "unfiltered"],
}

# ============================================================================
# RELATIONSHIP PROGRESSION
# ============================================================================

RELATIONSHIP_PROGRESSION = {
    # Initial attraction
    "first_notice": ["first noticed", "caught his eye", "couldn't look away"],
    "crush": ["crush", "infatuated", "couldn't stop thinking", "daydreaming"],
    "obsession": ["obsessed", "stalking social media", "everywhere I looked"],
    "mutual_attraction": ["both felt it", "chemistry", "tension between"],

    # Early stages
    "first_conversation": ["first talked", "finally spoke", "broke the ice"],
    "flirting": ["flirting", "teasing", "playful", "hints"],
    "first_touch": ["first touched", "hands brushed", "electric"],
    "first_kiss": ["first kiss", "finally kissed", "lips met"],
    "first_date": ["first date", "asked out", "dinner"],

    # Escalation
    "making_out": ["making out", "heavy petting", "couldn't stop"],
    "first_sexual": ["first time together", "finally", "took that step"],
    "exploring": ["exploring", "learning each other", "discovering"],
    "regular_hookups": ["kept meeting", "couldn't stay away", "again and again"],

    # Commitment
    "defining_relationship": ["what are we", "exclusive", "boyfriends"],
    "meeting_friends": ["met his friends", "introduced", "social circle"],
    "meeting_family": ["met family", "parents", "thanksgiving"],
    "moving_in": ["moved in", "living together", "our place"],
    "engagement": ["engaged", "proposal", "ring", "marry me"],
    "marriage": ["married", "wedding", "husband", "vows"],

    # Challenges
    "first_fight": ["first fight", "argument", "disagreement"],
    "breaking_up": ["broke up", "it's over", "ending things"],
    "getting_back_together": ["got back together", "second chance", "tried again"],
    "long_distance": ["long distance", "apart", "miles away", "video call"],
}

# ============================================================================
# PHYSICAL REACTIONS
# ============================================================================

PHYSICAL_REACTIONS = {
    # Arousal indicators
    "blushing": ["blushed", "cheeks red", "flushed", "heat in face"],
    "hardening": ["getting hard", "tenting", "growing", "stiffening"],
    "goosebumps": ["goosebumps", "shivers", "skin prickled"],
    "dilated_pupils": ["pupils dilated", "eyes darkened", "blown wide"],
    "rapid_breathing": ["breathing faster", "panting", "short breaths"],
    "heart_racing": ["heart racing", "pulse pounding", "heartbeat"],
    "sweating": ["sweating", "perspiring", "damp", "glistening"],
    "trembling": ["trembling", "shaking", "quivering", "vibrating"],

    # Nervous reactions
    "butterflies": ["butterflies", "stomach flipped", "nervous"],
    "dry_mouth": ["dry mouth", "swallowed", "licked lips"],
    "sweaty_palms": ["palms sweaty", "wiped hands", "clammy"],
    "voice_cracking": ["voice cracked", "squeaked", "throat tight"],
    "stumbling_words": ["stumbled", "stammered", "couldn't speak"],

    # Pleasure reactions
    "moaning": ["moaned", "groaned", "whimpered", "keened"],
    "arching": ["arched", "back bowed", "pressed up"],
    "gripping": ["gripped", "grabbed", "clutched", "held tight"],
    "curling_toes": ["toes curled", "feet flexed"],
    "eyes_rolling": ["eyes rolled back", "lost focus"],
    "seeing_stars": ["saw stars", "vision blurred", "dizzy"],

    # Orgasm reactions
    "tensing": ["tensed", "went rigid", "muscles locked"],
    "convulsing": ["convulsed", "spasmed", "jerked"],
    "crying_out": ["cried out", "screamed", "yelled"],
    "going_limp": ["went limp", "collapsed", "boneless"],

    # Pain reactions
    "flinching": ["flinched", "jerked away", "recoiled"],
    "wincing": ["winced", "grimaced", "face twisted"],
    "tears_pain": ["tears from pain", "eyes watered", "crying"],
    "biting_lip": ["bit lip", "teeth sank", "holding back"],
}

# ============================================================================
# ENVIRONMENT/ATMOSPHERE
# ============================================================================

ENVIRONMENT_ATMOSPHERE = {
    # Time of day
    "morning": ["morning", "sunrise", "woke up", "dawn", "breakfast"],
    "afternoon": ["afternoon", "midday", "lunch", "daylight"],
    "evening": ["evening", "sunset", "dusk", "dinner"],
    "night": ["night", "dark", "midnight", "late", "stars"],
    "middle_of_night": ["middle of night", "3am", "couldn't sleep"],

    # Seasons
    "spring": ["spring", "flowers", "warm breeze", "renewal"],
    "summer": ["summer", "hot", "sweat", "vacation", "sun"],
    "fall": ["fall", "autumn", "leaves", "cool", "halloween"],
    "winter": ["winter", "cold", "snow", "christmas", "fireplace"],

    # Weather
    "rain": ["rain", "raining", "storm", "thunder", "wet"],
    "snow": ["snow", "snowing", "blizzard", "frozen"],
    "heat_wave": ["heat wave", "sweltering", "too hot"],
    "perfect_weather": ["perfect day", "sunny", "beautiful"],
    "fog": ["fog", "mist", "couldn't see", "obscured"],

    # Lighting
    "bright_light": ["bright", "sunlight", "fluorescent", "harsh"],
    "dim_light": ["dim", "low light", "shadows", "barely see"],
    "candlelight": ["candles", "candlelight", "flickering", "romantic"],
    "moonlight": ["moonlight", "moon", "silver light"],
    "darkness": ["dark", "pitch black", "couldn't see"],
    "neon": ["neon", "club lights", "colored lights", "strobing"],

    # Sounds
    "silence": ["silence", "quiet", "no sound", "still"],
    "music_playing": ["music", "song", "playing", "soundtrack"],
    "nature_sounds": ["birds", "wind", "waves", "crickets"],
    "city_sounds": ["traffic", "sirens", "urban", "noise"],
    "voices_nearby": ["voices", "people nearby", "might hear"],

    # Smells
    "cologne": ["cologne", "aftershave", "perfume", "scented"],
    "sweat_smell": ["smell of sweat", "musk", "body odor"],
    "food_smell": ["cooking", "food", "kitchen smells"],
    "nature_smell": ["grass", "flowers", "rain smell", "petrichor"],
    "sex_smell": ["smell of sex", "cum", "arousal"],
}

# ============================================================================
# COMMUNICATION PATTERNS
# ============================================================================

COMMUNICATION_PATTERNS = {
    # Digital communication
    "texting": ["texted", "text message", "typing", "read receipt"],
    "sexting": ["sexting", "dirty texts", "pics", "nudes"],
    "phone_call": ["called", "phone", "voice", "hung up"],
    "video_call": ["video call", "facetime", "skype", "zoom"],
    "social_media": ["dm", "instagram", "twitter", "liked his post"],
    "dating_app": ["app", "grindr", "tinder", "swiped", "matched"],
    "email": ["email", "wrote", "inbox"],

    # Verbal styles
    "direct_communication": ["said directly", "blunt", "straightforward"],
    "hints_and_subtext": ["hinted", "implied", "between the lines"],
    "sarcasm": ["sarcastic", "sarcastically", "dry humor"],
    "sweet_talk": ["sweet words", "compliments", "flattery"],
    "dirty_talk_style": ["talked dirty", "explicit words", "filthy"],

    # Emotional conversations
    "confession": ["confessed", "admitted", "told him", "came clean"],
    "argument": ["argued", "fought", "yelled", "disagreed"],
    "apology": ["apologized", "sorry", "forgive me", "made up"],
    "heart_to_heart": ["talked all night", "opened up", "vulnerable"],
    "awkward_silence": ["awkward silence", "didn't know what to say"],

    # Non-verbal
    "eye_contact_comm": ["eyes met", "looked at each other", "staring"],
    "body_language": ["body language", "leaned in", "turned away"],
    "touch_communication": ["touched his arm", "hand on shoulder"],
    "distance": ["kept distance", "space between", "too close"],
}

# ============================================================================
# CONFLICT TYPES
# ============================================================================

CONFLICT_TYPES = {
    # Internal conflict
    "internalized_shame": ["ashamed of wanting", "shouldn't feel", "wrong to want"],
    "identity_crisis": ["who am I", "don't know myself", "questioning everything"],
    "moral_dilemma": ["right or wrong", "should I", "ethical"],
    "fear_of_rejection": ["afraid he'd reject", "what if he says no"],
    "fear_of_outing": ["afraid of being outed", "someone might see"],

    # Relationship conflict
    "jealousy": ["jealous", "saw him with", "who was that"],
    "trust_issues": ["don't trust", "lying", "suspicious"],
    "communication_breakdown": ["wouldn't talk", "shut down", "silent treatment"],
    "different_wants": ["wanted different things", "not compatible"],
    "commitment_fear": ["afraid of commitment", "too fast", "not ready"],
    "infidelity": ["cheated", "unfaithful", "another guy"],

    # External conflict
    "disapproving_family": ["family wouldn't approve", "parents", "disowned"],
    "homophobic_environment": ["homophobic", "not safe", "couldn't be open"],
    "distance_obstacle": ["too far", "different cities", "couldn't be together"],
    "timing": ["wrong time", "bad timing", "not now"],
    "social_pressure": ["what would people think", "reputation", "gossip"],
    "work_complications": ["workplace policy", "boss", "career"],

    # Resolution patterns
    "confrontation": ["confronted", "had it out", "face to face"],
    "avoidance": ["avoided", "ran away", "couldn't face"],
    "compromise": ["compromised", "met in middle", "both gave"],
    "acceptance": ["accepted", "came to terms", "let go"],
    "forgiveness": ["forgave", "second chance", "moved past"],
}

# ============================================================================
# MENTAL HEALTH ELEMENTS
# ============================================================================

MENTAL_HEALTH = {
    # Anxiety spectrum
    "general_anxiety": ["anxious", "worried", "nervous", "on edge"],
    "social_anxiety": ["social anxiety", "afraid of people", "couldn't speak"],
    "panic_attack": ["panic attack", "couldn't breathe", "heart racing", "dying"],
    "performance_anxiety": ["nervous about", "what if I can't", "pressure"],

    # Depression spectrum
    "depression": ["depressed", "empty", "numb", "no point"],
    "low_self_esteem": ["worthless", "not good enough", "hate myself"],
    "isolation": ["isolated", "alone", "no one", "withdrawn"],
    "anhedonia": ["couldn't feel", "nothing mattered", "numb"],

    # Trauma responses
    "ptsd": ["flashback", "triggered", "couldn't stop remembering"],
    "hypervigilance": ["always watching", "couldn't relax", "on guard"],
    "dissociation": ["disconnected", "not in body", "watching myself"],
    "nightmares": ["nightmares", "bad dreams", "woke up screaming"],

    # Recovery elements
    "therapy": ["therapy", "therapist", "counseling", "talking to someone"],
    "medication": ["medication", "pills", "prescription"],
    "support_system": ["support", "friends helped", "not alone"],
    "self_care": ["self care", "taking care of myself", "boundaries"],
    "healing_journey": ["healing", "getting better", "recovery", "progress"],

    # Coping mechanisms
    "healthy_coping": ["worked out", "journaled", "meditated", "talked about it"],
    "unhealthy_coping": ["drinking", "shutting down", "lashing out", "self-destructive"],
}

# ============================================================================
# SUBSTANCE ELEMENTS
# ============================================================================

SUBSTANCE_ELEMENTS = {
    # Alcohol
    "sober": ["sober", "not drinking", "clear headed"],
    "tipsy": ["tipsy", "buzz", "loosened up", "few drinks"],
    "drunk": ["drunk", "wasted", "hammered", "couldn't walk straight"],
    "blackout": ["blacked out", "don't remember", "woke up"],
    "hangover": ["hangover", "next morning", "regret"],

    # Drugs
    "weed": ["weed", "high", "stoned", "marijuana", "420"],
    "poppers": ["poppers", "rush", "head rush", "amyl"],
    "party_drugs": ["molly", "ecstasy", "rolled", "feeling everything"],
    "harder_drugs": ["coke", "meth", "tweaking", "wired"],

    # Consent implications
    "both_intoxicated": ["both drunk", "both high", "same level"],
    "one_sober_one_not": ["he was drunk", "took advantage", "couldn't consent"],
    "morning_after_clarity": ["sober now", "in the light of day", "what did we do"],

    # Context
    "social_drinking": ["at the bar", "party", "drinks with friends"],
    "liquid_courage": ["needed courage", "drink first", "loosened inhibitions"],
    "addiction_context": ["addicted", "couldn't stop", "problem", "rehab"],
}

# ============================================================================
# DISABILITY REPRESENTATION
# ============================================================================

DISABILITY_REP = {
    # Physical disabilities
    "mobility_impairment": ["wheelchair", "cane", "crutches", "couldn't walk"],
    "amputation": ["amputee", "missing limb", "prosthetic"],
    "chronic_pain": ["chronic pain", "always hurts", "pain management"],
    "chronic_illness": ["chronic illness", "sick", "condition", "flare up"],

    # Sensory disabilities
    "deaf_hoh": ["deaf", "hard of hearing", "sign language", "couldn't hear"],
    "blind_vi": ["blind", "visually impaired", "couldn't see", "guide dog"],

    # Neurodivergent
    "autism": ["autistic", "autism", "spectrum", "sensory issues"],
    "adhd": ["adhd", "couldn't focus", "hyperactive", "distracted"],
    "dyslexia": ["dyslexic", "reading difficulty", "letters jumbled"],
    "ocd": ["ocd", "compulsion", "had to", "ritual"],

    # Mental health (as disability)
    "bipolar": ["bipolar", "manic", "depressive episode", "mood swings"],
    "schizophrenia": ["schizophrenia", "voices", "hallucination"],
    "personality_disorder": ["bpd", "npd", "personality disorder"],

    # Adaptive elements
    "accommodation": ["accommodation", "adapted", "accessible"],
    "communication_difference": ["different communication", "alternative"],
    "strength_from_difference": ["saw the world differently", "unique perspective"],
}

# ============================================================================
# COMING OUT JOURNEY (Detailed)
# ============================================================================

COMING_OUT_JOURNEY = {
    # Pre-realization
    "unaware": ["didn't know", "never thought", "assumed straight"],
    "curiosity": ["curious", "wondered", "what if"],
    "denial_phase": ["not gay", "just a phase", "everyone thinks that"],
    "signs_ignored": ["should have known", "looking back", "signs"],

    # Realization
    "moment_of_clarity": ["suddenly knew", "clicked", "finally understood"],
    "gradual_realization": ["slowly realized", "over time", "pieces fell"],
    "triggered_by_person": ["when I saw him", "because of you", "you made me realize"],
    "triggered_by_event": ["that moment", "when it happened", "changed everything"],

    # Processing
    "research_phase": ["googled", "read about", "am I gay quiz"],
    "testing_waters": ["tried", "experimented", "just to see"],
    "internal_acceptance": ["accepted myself", "okay with it", "this is me"],
    "still_processing": ["still figuring out", "not sure", "work in progress"],

    # Coming out acts
    "coming_out_to_self": ["admitted to myself", "said it out loud", "in the mirror"],
    "coming_out_to_friend": ["told my friend", "first person", "needed to tell someone"],
    "coming_out_to_family": ["told my parents", "family", "mom", "dad"],
    "coming_out_to_everyone": ["came out publicly", "everyone knows", "posted"],
    "forced_outing": ["was outed", "someone told", "found out"],

    # Reactions received
    "acceptance_received": ["accepted", "loved anyway", "nothing changed"],
    "rejection_received": ["rejected", "disowned", "lost them"],
    "mixed_reactions": ["some accepted", "complicated", "took time"],
    "violence_threat": ["threatened", "unsafe", "had to leave"],

    # Post coming out
    "relief": ["relief", "weight lifted", "finally free"],
    "pride": ["proud", "pride", "celebrating"],
    "community_finding": ["found community", "others like me", "belonging"],
    "living_openly": ["openly", "no more hiding", "authentic"],
}

# ============================================================================
# SCENE STRUCTURE ELEMENTS
# ============================================================================

SCENE_STRUCTURE = {
    # Buildup
    "tension_building": ["tension built", "anticipation", "inevitable"],
    "teasing_buildup": ["teased", "hinted", "almost but not"],
    "slow_approach": ["slowly", "taking time", "drawing out"],
    "sudden_start": ["suddenly", "without warning", "jumped"],

    # Interruptions
    "almost_caught": ["almost caught", "close call", "nearly walked in"],
    "actually_interrupted": ["interrupted", "had to stop", "someone came"],
    "phone_interruption": ["phone rang", "text", "had to answer"],
    "internal_interruption": ["hesitated", "stopped himself", "second thoughts"],

    # Pacing shifts
    "pace_quickening": ["faster", "urgent", "couldn't wait"],
    "pace_slowing": ["slowed down", "savoring", "making it last"],
    "stop_and_start": ["stopped then started", "pause", "break"],
    "continuous": ["didn't stop", "kept going", "relentless"],

    # Climax structure
    "simultaneous_climax": ["came together", "at the same time", "synchronized"],
    "sequential_climax": ["came first", "then he", "one after other"],
    "delayed_climax": ["held off", "edging", "not yet"],
    "denied_climax": ["didn't get to", "stopped before", "left wanting"],
    "multiple_climax": ["came again", "multiple times", "kept cumming"],

    # Resolution
    "immediate_aftermath": ["right after", "catching breath", "still inside"],
    "pillow_talk": ["talked after", "lying together", "conversation"],
    "quick_departure": ["had to go", "left quickly", "didn't stay"],
    "falling_asleep": ["fell asleep", "drifted off", "exhausted"],
}

# ============================================================================
# CHARACTER VOICE PATTERNS
# ============================================================================

CHARACTER_VOICE = {
    # Speech patterns
    "formal_speech": ["proper", "formal", "sir", "eloquent", "articulate"],
    "casual_speech": ["casual", "relaxed", "chill", "whatever"],
    "crude_speech": ["crude", "vulgar", "swearing", "profanity"],
    "shy_speech": ["quiet", "mumbled", "barely audible", "whispered"],
    "confident_speech": ["confident", "bold", "direct", "commanding"],

    # Accents/dialects
    "southern_accent": ["southern", "drawl", "y'all", "accent"],
    "british_accent": ["british", "english", "mate", "bloody"],
    "australian_accent": ["aussie", "australian", "mate", "g'day"],
    "new_york_accent": ["new york", "brooklyn", "fuggedaboutit"],
    "foreign_accent": ["accent", "english isn't first", "struggled with words"],

    # Verbal quirks
    "uses_nicknames": ["called him", "nickname", "pet name", "babe"],
    "rambling": ["rambled", "kept talking", "couldn't stop"],
    "one_word_answers": ["one word", "short", "brief", "minimal"],
    "nervous_filler": ["um", "uh", "like", "you know"],
    "intellectual_vocab": ["big words", "vocabulary", "academic"],
    "simple_vocab": ["simple words", "basic", "easy to understand"],

    # Emotional expression
    "emotionally_expressive": ["showed emotion", "wore heart on sleeve"],
    "emotionally_reserved": ["didn't show", "stoic", "hard to read"],
    "uses_humor": ["joked", "funny", "made light", "laughed it off"],
    "serious_always": ["always serious", "never jokes", "intense"],
}

# ============================================================================
# MICRO-EXPRESSIONS & TELLS
# ============================================================================

MICRO_EXPRESSIONS = {
    # Eye movements
    "eyes_darting": ["eyes darted", "looked away", "couldn't meet eyes"],
    "prolonged_stare": ["stared", "held gaze", "wouldn't look away"],
    "eye_dilation": ["pupils dilated", "eyes darkened", "wide eyes"],
    "squinting": ["squinted", "narrowed eyes", "suspicious look"],
    "eye_roll": ["rolled eyes", "exasperated", "annoyed look"],

    # Mouth movements
    "lip_licking": ["licked lips", "tongue darted", "wet lips"],
    "lip_biting": ["bit lip", "teeth on lip", "chewing lip"],
    "jaw_clenching": ["jaw clenched", "teeth grinding", "tense jaw"],
    "mouth_falling_open": ["mouth fell open", "jaw dropped", "gaped"],
    "smirking": ["smirked", "half smile", "knowing look"],

    # Facial tells
    "micro_smile": ["slight smile", "corners lifted", "ghost of smile"],
    "furrowed_brow": ["brow furrowed", "confused look", "frowning"],
    "raised_eyebrow": ["raised eyebrow", "questioning look", "skeptical"],
    "nostril_flare": ["nostrils flared", "breathing hard", "angry"],
    "color_change": ["went pale", "flushed", "red face", "blanched"],

    # Body tells
    "shifting_weight": ["shifted", "fidgeted", "couldn't stay still"],
    "crossing_arms": ["crossed arms", "defensive", "closed off"],
    "leaning_in": ["leaned in", "closer", "interested"],
    "leaning_away": ["leaned back", "pulled away", "creating distance"],
    "touching_face": ["touched face", "rubbed neck", "self-soothing"],
    "hands_in_pockets": ["hands in pockets", "hiding hands", "casual"],
}

# ============================================================================
# SPECIFIC ACT DETAILS
# ============================================================================

ACT_DETAILS = {
    # Kissing types
    "peck": ["peck", "quick kiss", "brief", "chaste"],
    "deep_kiss": ["deep kiss", "tongues", "exploring mouth"],
    "aggressive_kiss": ["aggressive", "bruising", "demanding", "claiming"],
    "gentle_kiss": ["gentle kiss", "soft", "tender", "sweet"],
    "neck_kissing": ["kissed neck", "throat", "below ear"],
    "body_kissing": ["kissed down", "trailed kisses", "everywhere"],

    # Oral details
    "teasing_licks": ["licked", "teased", "tongue", "tasting"],
    "full_engulfment": ["took it all", "whole thing", "swallowed"],
    "gagging_detail": ["gagged", "choked", "couldn't breathe"],
    "hands_involved": ["hand and mouth", "stroking while", "both"],

    # Penetration details
    "slow_entry": ["slowly entered", "inch by inch", "taking time"],
    "fast_entry": ["thrust in", "all at once", "sudden"],
    "adjusting": ["adjusting", "getting used to", "giving time"],
    "angle_finding": ["found the spot", "angle", "there", "right there"],

    # Rhythm details
    "slow_rhythm": ["slow", "deliberate", "measured", "steady"],
    "fast_rhythm": ["fast", "pounding", "relentless", "frantic"],
    "changing_rhythm": ["changed pace", "varied", "unpredictable"],
    "grinding": ["grinding", "circular", "deep and slow"],

    # Finishing details
    "pulling_out": ["pulled out", "withdrew", "slipped out"],
    "staying_inside": ["stayed inside", "didn't pull out", "together"],
    "cleanup_detail": ["cleaned up", "dripping", "mess", "wiped"],
}

# ============================================================================
# SCENT/SMELL DETAILED
# ============================================================================

SCENT_TAXONOMY = {
    # Body scents
    "natural_musk": ["musk", "natural scent", "his smell", "masculine"],
    "fresh_shower": ["fresh from shower", "soap", "clean", "shampoo"],
    "sweat_scent": ["sweat", "worked out", "gym smell", "exertion"],
    "arousal_scent": ["arousal", "turned on", "sex smell", "pheromones"],
    "cum_scent": ["cum", "semen", "after sex", "spent"],

    # Product scents
    "cologne_scent": ["cologne", "aftershave", "perfume", "designer"],
    "deodorant": ["deodorant", "antiperspirant", "fresh"],
    "lotion": ["lotion", "moisturizer", "smooth"],
    "lube_scent": ["lube", "silicone", "water-based"],

    # Environmental scents
    "leather_scent": ["leather smell", "hide", "worn leather"],
    "smoke_scent": ["smoke", "cigarette", "weed smoke", "fire"],
    "alcohol_scent": ["alcohol", "whiskey", "beer", "bar smell"],
    "outdoor_scent": ["grass", "earth", "rain", "forest"],
    "indoor_scent": ["fabric softener", "candles", "home"],
}

# ============================================================================
# TASTE DETAILED
# ============================================================================

TASTE_TAXONOMY = {
    # Skin tastes
    "skin_taste": ["tasted skin", "licked", "salty skin"],
    "sweat_taste": ["tasted sweat", "salty", "worked out"],
    "clean_taste": ["clean", "fresh", "soap taste"],

    # Sexual tastes
    "precum_taste": ["precum", "leaking", "salty sweet"],
    "cum_taste_detail": ["cum taste", "bitter", "salty", "swallowed"],
    "ass_taste": ["ass", "musky", "earthy", "rim"],

    # Mouth tastes
    "kiss_taste": ["tasted his mouth", "tongue", "mint", "coffee"],
    "alcohol_taste": ["tasted alcohol", "whiskey", "beer"],
    "smoke_taste": ["tasted smoke", "cigarettes", "weed"],

    # Food context
    "food_play": ["whipped cream", "chocolate", "honey", "food"],
}

# ============================================================================
# TOUCH TEXTURES DETAILED
# ============================================================================

TOUCH_TEXTURES = {
    # Skin textures
    "smooth_skin": ["smooth", "soft skin", "silky"],
    "rough_skin": ["rough", "calloused", "weathered"],
    "hairy_texture": ["hairy", "fur", "prickly", "stubble"],
    "scarred_texture": ["scarred", "raised skin", "marks"],
    "sweaty_texture": ["slick", "wet", "sweaty", "damp"],

    # Body part textures
    "muscle_firm": ["firm muscles", "hard body", "solid"],
    "soft_body": ["soft", "yielding", "plush", "cushioned"],
    "bony": ["bony", "angular", "hip bones", "ribs"],

    # Temperature touch
    "warm_touch": ["warm", "hot skin", "feverish", "burning"],
    "cool_touch": ["cool", "cold hands", "chilled"],
    "contrasting_temp": ["hot and cold", "ice on warm skin"],

    # Pressure touch
    "light_touch": ["light touch", "featherlight", "barely there"],
    "firm_touch": ["firm grip", "strong hold", "pressure"],
    "bruising_touch": ["bruising", "too hard", "will leave marks"],
}

# ============================================================================
# INTERNAL SENSATIONS
# ============================================================================

INTERNAL_SENSATIONS = {
    # Stomach/gut
    "butterflies_internal": ["butterflies", "stomach flipped", "flutter"],
    "gut_punch": ["gut punch", "sinking feeling", "dread"],
    "hunger_internal": ["hungry", "empty", "craving", "need"],
    "nausea": ["nauseous", "sick", "queasy", "stomach turned"],

    # Chest
    "heart_pounding": ["heart pounding", "racing", "could hear it"],
    "chest_tight": ["chest tight", "couldn't breathe", "constricted"],
    "warmth_spreading": ["warmth spread", "heat bloomed", "flushed"],
    "ache_longing": ["ached", "longing", "yearning", "pining"],

    # Head
    "dizzy": ["dizzy", "lightheaded", "spinning", "vertigo"],
    "clarity": ["clarity", "sharp", "focused", "clear"],
    "fuzzy": ["fuzzy", "hazy", "floating", "not all there"],
    "pressure_head": ["pressure", "building", "head pounding"],

    # Sexual internal
    "building_orgasm": ["building", "growing", "mounting", "close"],
    "orgasm_sensation": ["exploded", "crashed", "wave", "pulsing"],
    "post_orgasm": ["aftershocks", "sensitive", "twitching", "floating"],
    "fullness_internal": ["full", "stretched", "stuffed", "complete"],
    "emptiness_after": ["empty", "hollow", "missing", "wanting"],
}

# ============================================================================
# VISUAL DETAILS
# ============================================================================

VISUAL_DETAILS = {
    # Watching acts
    "watching_face": ["watched his face", "expressions", "reactions"],
    "watching_body": ["watched his body", "muscles move", "skin"],
    "watching_cock": ["watched his cock", "bobbing", "leaking", "hard"],
    "watching_ass": ["watched his ass", "spread", "hole", "taking"],
    "eye_contact_during": ["looked into eyes", "held gaze", "watching each other"],

    # Visual states
    "disheveled": ["disheveled", "messy", "wrecked", "ruined"],
    "perfect_composed": ["composed", "perfect", "put together"],
    "sweaty_visual": ["glistening", "sheen", "dripping sweat"],
    "flushed_visual": ["flushed", "red", "pink", "heated"],

    # Light/shadow
    "illuminated": ["light fell on", "illuminated", "highlighted"],
    "shadowed": ["shadows", "hidden", "obscured", "dark"],
    "silhouette": ["silhouette", "outline", "shape against"],

    # Motion visual
    "muscles_flexing": ["muscles flexing", "rippling", "tensing"],
    "body_moving": ["body moving", "rocking", "thrusting"],
    "subtle_movement": ["slight movement", "twitch", "shift"],
}

# ============================================================================
# SOUND DETAILS
# ============================================================================

SOUND_DETAILS = {
    # Vocal sounds
    "moan_types": ["low moan", "high whine", "deep groan", "whimper"],
    "word_sounds": ["whispered", "growled", "panted", "gasped out"],
    "breath_sounds": ["heavy breathing", "panting", "catching breath"],
    "cry_sounds": ["cried out", "screamed", "yelled", "shouted"],

    # Body sounds
    "skin_slapping": ["slapping", "smacking", "skin on skin"],
    "wet_sounds_detail": ["wet", "squelching", "slick", "sloppy"],
    "kissing_sounds": ["kissing sounds", "smack", "wet kiss"],
    "sucking_sounds": ["sucking", "slurping", "hollowed cheeks"],

    # Environmental sounds
    "bed_sounds": ["bed creaking", "springs", "headboard", "mattress"],
    "door_sounds": ["door", "lock clicking", "opening", "closing"],
    "ambient_sounds": ["outside noise", "music", "silence", "white noise"],

    # Reaction sounds
    "sharp_intake": ["sharp intake", "sucked in breath", "gasp"],
    "exhale": ["exhaled", "let out breath", "sighed"],
    "grunt_sound": ["grunted", "huffed", "low sound"],
    "laugh_during": ["laughed", "chuckled", "smiled sound"],
}

# ============================================================================
# POWER EXCHANGE MICRO-DETAILS
# ============================================================================

POWER_EXCHANGE_DETAILS = {
    # Control indicators
    "eye_contact_control": ["made him look", "don't look away", "watch me"],
    "verbal_control": ["told him", "commanded", "ordered", "instructed"],
    "physical_control": ["held him", "pinned", "positioned", "moved him"],
    "pace_control": ["set the pace", "controlled speed", "made him wait"],

    # Submission indicators
    "asking_permission": ["can I", "may I", "please let me"],
    "waiting_patiently": ["waited", "didn't move", "held still"],
    "following_orders": ["did as told", "obeyed", "complied"],
    "showing_gratitude": ["thank you", "grateful", "appreciated"],

    # Power shifts
    "power_given": ["gave control", "let him", "surrendered"],
    "power_taken": ["took control", "seized", "claimed"],
    "power_earned": ["earned it", "proved worthy", "deserved"],
    "power_negotiated": ["negotiated", "agreed", "discussed"],

    # Testing boundaries
    "pushing_limits": ["pushed", "tested", "went further"],
    "respecting_limits": ["respected", "stopped when", "checked in"],
    "safe_word_use": ["safe word", "red", "stopped everything"],
}

# ============================================================================
# INTIMACY LEVELS
# ============================================================================

INTIMACY_LEVELS = {
    # Physical intimacy spectrum
    "no_contact": ["didn't touch", "distance", "separate"],
    "minimal_contact": ["barely touched", "brief", "light"],
    "casual_contact": ["touched", "contact", "physical"],
    "intimate_contact": ["close", "wrapped around", "entwined"],
    "merged": ["couldn't tell where", "one body", "completely connected"],

    # Emotional intimacy spectrum
    "strangers_emotionally": ["didn't know", "anonymous", "no names"],
    "surface_level": ["small talk", "superficial", "didn't go deep"],
    "opening_up": ["shared", "told him about", "revealed"],
    "deeply_vulnerable": ["completely open", "everything", "soul bare"],
    "total_trust": ["trusted completely", "no secrets", "knew everything"],

    # Eye contact intimacy
    "avoiding_eyes": ["couldn't look", "looked away", "averted"],
    "brief_glances": ["glanced", "quick look", "fleeting"],
    "sustained_gaze": ["held gaze", "looked into eyes", "connection"],
    "soul_gazing": ["could see into", "lost in eyes", "deep look"],
}

# ============================================================================
# TIME MARKERS
# ============================================================================

TIME_MARKERS = {
    # Duration
    "quickie": ["quick", "fast", "minutes", "didn't take long"],
    "took_time": ["took their time", "unhurried", "slowly"],
    "hours_long": ["hours", "all night", "lost track of time"],
    "marathon": ["marathon", "again and again", "multiple rounds"],

    # Frequency
    "first_time_marker": ["first time", "never before", "inaugural"],
    "occasional": ["sometimes", "occasionally", "when they could"],
    "regular_occurrence": ["regularly", "often", "routine", "usual"],
    "constant": ["constantly", "all the time", "couldn't stop"],

    # Time references
    "years_ago": ["years ago", "back then", "used to"],
    "recently": ["recently", "just", "the other day"],
    "right_now": ["now", "this moment", "present"],
    "future_hope": ["someday", "will", "going to", "want to"],

    # Waiting
    "waited_long_time": ["waited so long", "finally", "been wanting"],
    "no_waiting": ["immediately", "right away", "couldn't wait"],
    "delayed_gratification": ["made to wait", "anticipation", "building"],
}

# ============================================================================
# LOCATION MICRO-DETAILS
# ============================================================================

LOCATION_DETAILS = {
    # Furniture specifics
    "against_door": ["against door", "slammed door", "pinned to door"],
    "on_floor": ["floor", "carpet", "hardwood", "rug"],
    "on_table": ["table", "desk", "counter", "surface"],
    "in_bed_detail": ["bed", "mattress", "sheets", "pillows"],
    "on_couch": ["couch", "sofa", "cushions"],
    "in_chair_detail": ["chair", "sat", "straddling", "lap"],

    # Bathroom specifics
    "in_shower_detail": ["shower", "water running", "steam", "wet"],
    "against_sink": ["sink", "mirror", "counter"],
    "in_bathtub": ["bathtub", "bath", "water", "bubbles"],

    # Outdoor specifics
    "against_tree": ["tree", "bark", "forest", "woods"],
    "on_grass": ["grass", "ground", "earth", "blanket"],
    "in_water_detail": ["water", "pool", "lake", "ocean", "waves"],
    "in_car_detail": ["car", "backseat", "front seat", "parked"],

    # Public specifics
    "bathroom_stall": ["stall", "locked door", "public bathroom"],
    "back_room": ["back room", "storage", "hidden"],
    "dark_corner": ["dark corner", "hidden", "shadows", "alcove"],
}

# ============================================================================
# ANTICIPATION/BUILDUP ELEMENTS
# ============================================================================

ANTICIPATION_ELEMENTS = {
    # Pre-encounter
    "planning": ["planned", "set up", "arranged", "orchestrated"],
    "fantasizing": ["fantasized", "imagined", "dreamed of", "pictured"],
    "nervous_anticipation": ["nervous", "butterflies", "couldn't wait"],
    "dread_anticipation": ["dreaded", "feared", "anxious about"],

    # Immediate buildup
    "tension_thick": ["tension thick", "could cut with knife", "charged"],
    "stolen_glances": ["stolen glances", "kept looking", "eyes met"],
    "accidental_touch": ["accidental touch", "brushed", "unintentional"],
    "deliberate_tease": ["teased", "deliberately", "knowing", "purposeful"],

    # The moment before
    "pause_before": ["paused", "moment before", "suspended"],
    "last_chance_out": ["last chance", "could still stop", "sure about this"],
    "point_of_no_return": ["no going back", "crossed line", "committed"],
    "breath_held": ["held breath", "waiting", "anticipating"],

    # Breaking point
    "couldn't_resist": ["couldn't resist", "gave in", "finally"],
    "someone_made_move": ["made the move", "initiated", "started it"],
    "mutual_collision": ["both moved", "crashed together", "simultaneously"],
}

# ============================================================================
# MEMORY/FLASHBACK ELEMENTS
# ============================================================================

MEMORY_ELEMENTS = {
    # Memory triggers
    "smell_trigger": ["smell reminded", "scent brought back", "familiar smell"],
    "song_trigger": ["song came on", "music reminded", "their song"],
    "place_trigger": ["being here", "this place", "where they"],
    "person_trigger": ["saw someone who", "looked like", "reminded me of"],

    # Memory quality
    "vivid_memory": ["vivid", "clear as day", "like yesterday"],
    "hazy_memory": ["hazy", "fuzzy", "couldn't remember exactly"],
    "fragmented_memory": ["fragments", "pieces", "flashes"],
    "repressed_memory": ["repressed", "forgotten", "buried", "came flooding"],

    # Memory emotions
    "nostalgic": ["nostalgic", "missed", "those days", "simpler times"],
    "painful_memory": ["painful", "hurt to remember", "wished could forget"],
    "warm_memory": ["warm", "smiled remembering", "good memory"],
    "complicated_memory": ["complicated", "mixed feelings", "bittersweet"],

    # Comparison
    "comparing_to_past": ["like before", "different from", "reminded of"],
    "comparing_to_fantasy": ["like imagined", "better than fantasy", "not what expected"],
    "comparing_partners": ["different from him", "never like this", "no one else"],
}

# ============================================================================
# JEALOUSY/POSSESSIVENESS
# ============================================================================

JEALOUSY_POSSESSIVENESS = {
    # Jealousy triggers
    "seeing_with_other": ["saw him with", "another guy", "talking to someone"],
    "hearing_about_ex": ["ex", "used to", "before me", "past"],
    "attention_elsewhere": ["wasn't looking at me", "distracted", "ignored"],
    "imagined_threat": ["imagined", "paranoid", "what if"],

    # Jealousy reactions
    "quiet_jealousy": ["didn't say anything", "silent", "simmering"],
    "expressed_jealousy": ["told him", "confronted", "asked about"],
    "acted_on_jealousy": ["acted out", "did something", "regretted"],
    "jealous_sex": ["claimed", "marked", "mine", "proving"],

    # Possessiveness
    "verbal_claiming": ["you're mine", "belong to me", "no one else"],
    "physical_marking": ["hickey", "bite mark", "bruise", "evidence"],
    "territorial": ["territory", "his space", "our bed"],
    "showing_off": ["showed off", "public display", "everyone saw"],

    # Resolution
    "reassurance": ["reassured", "only you", "doesn't matter"],
    "trust_building": ["trust", "believe me", "nothing happened"],
    "boundary_setting": ["boundaries", "not okay", "need to talk"],
}

# ============================================================================
# SECRETS/HIDING
# ============================================================================

SECRETS_HIDING = {
    # What's hidden
    "hidden_relationship": ["secret relationship", "no one knows", "hiding us"],
    "hidden_identity": ["closeted", "not out", "hiding who I am"],
    "hidden_desire": ["secret desire", "never told anyone", "private fantasy"],
    "hidden_past": ["past", "before", "didn't tell you", "secret history"],

    # Hiding behaviors
    "sneaking_around": ["sneaking", "secret meetings", "careful"],
    "lying": ["lied", "made up story", "cover story"],
    "compartmentalizing": ["separate lives", "different worlds", "compartment"],
    "close_calls": ["almost caught", "close call", "nearly discovered"],

    # Discovery
    "accidental_discovery": ["found out", "discovered", "stumbled upon"],
    "intentional_reveal": ["told him", "came clean", "confessed"],
    "forced_reveal": ["forced to tell", "caught", "exposed"],
    "still_hidden": ["still secret", "no one knows yet", "hiding"],

    # Consequences
    "relief_after": ["relief", "glad it's out", "weight lifted"],
    "complications": ["complicated", "problems", "consequences"],
    "acceptance_received": ["accepted", "didn't care", "loved anyway"],
    "rejection_after": ["rejected", "couldn't accept", "lost"],
}

# ============================================================================
# FANDOM/AU TROPES
# ============================================================================

AU_TROPES = {
    # Setting AUs
    "coffee_shop_au": ["coffee shop", "barista", "regular customer", "latte"],
    "college_au": ["college au", "campus", "dorm", "roommates"],
    "high_school_au": ["high school au", "teenagers", "prom", "lockers"],
    "office_au": ["office au", "coworkers", "boss", "workplace"],
    "royalty_au": ["royalty", "prince", "king", "servant", "throne"],
    "historical_au": ["historical", "period piece", "past era"],
    "modern_au": ["modern au", "contemporary setting"],
    "space_au": ["space", "spaceship", "astronaut", "alien planet"],
    "fantasy_au": ["fantasy au", "magic", "dragons", "kingdom"],
    "apocalypse_au": ["apocalypse", "post-apocalyptic", "survival", "end of world"],

    # Situation AUs
    "soulmate_au": ["soulmate", "destined", "marks", "bond"],
    "arranged_marriage": ["arranged marriage", "forced to marry", "contract"],
    "fake_relationship": ["fake relationship", "pretend", "for show", "convenience"],
    "enemies_to_lovers": ["enemies to lovers", "hated each other", "rivals"],
    "friends_to_lovers": ["friends to lovers", "always been there", "finally"],
    "strangers_to_lovers": ["strangers", "just met", "random encounter"],
    "second_chance": ["second chance", "years later", "reunion", "again"],
    "forbidden_love_au": ["forbidden", "can't be together", "against rules"],
    "secret_relationship_au": ["secret", "hiding", "no one can know"],
    "one_night_stand_au": ["one night stand", "just tonight", "no strings"],

    # Occupation AUs
    "band_au": ["band", "musicians", "tour", "rockstar"],
    "sports_au": ["sports au", "athletes", "team", "competition"],
    "military_au": ["military au", "soldiers", "war", "deployment"],
    "medical_au": ["medical au", "doctor", "hospital", "nurse"],
    "teacher_au": ["teacher au", "professor", "student", "school"],
    "celebrity_au": ["celebrity", "famous", "paparazzi", "fans"],
}

# ============================================================================
# BODY MODIFICATION
# ============================================================================

BODY_MODIFICATION = {
    # Tattoos
    "tattoo_visible": ["visible tattoo", "sleeve", "neck tattoo", "hand tattoo"],
    "tattoo_hidden": ["hidden tattoo", "covered", "only I know"],
    "tattoo_meaning": ["meaningful tattoo", "story behind", "represents"],
    "tattoo_matching": ["matching tattoos", "couple tattoo", "same design"],
    "tattoo_name": ["name tattooed", "his name", "belonging"],

    # Piercings
    "ear_piercing": ["ear piercing", "earring", "stud", "hoop"],
    "nipple_piercing": ["nipple piercing", "rings", "barbells", "sensitive"],
    "genital_piercing": ["prince albert", "frenum", "guiche", "pierced cock"],
    "facial_piercing": ["eyebrow", "lip ring", "nose ring", "septum"],
    "tongue_piercing": ["tongue piercing", "oral", "ball", "metal"],

    # Other modifications
    "scarification": ["scarification", "scar", "intentional", "pattern"],
    "branding_mod": ["branded", "burn", "permanent mark", "ownership"],
    "subdermal": ["subdermal", "implant", "under skin"],
    "split_tongue": ["split tongue", "forked", "snake tongue"],

    # Reactions to mods
    "turned_on_by_mods": ["loved his tattoos", "piercings turned me on"],
    "playing_with_piercings": ["tugged piercing", "licked the ring", "metal taste"],
}

# ============================================================================
# GROUP SEX DYNAMICS
# ============================================================================

GROUP_DYNAMICS = {
    # Threesome configurations
    "mmm_threesome": ["three guys", "all men", "threesome"],
    "spit_roast": ["spit roast", "both ends", "middle"],
    "daisy_chain": ["daisy chain", "circle", "connected"],
    "double_penetration_group": ["double penetration", "both holes", "at once"],
    "taking_turns": ["taking turns", "one after another", "waiting"],
    "watching_threesome": ["watching", "third wheel", "voyeur in threesome"],

    # Larger groups
    "foursome": ["foursome", "four", "two couples", "swap"],
    "orgy_small": ["small orgy", "five or six", "intimate group"],
    "orgy_large": ["large orgy", "many men", "lost count"],
    "gangbang_receiver": ["gangbang", "center of attention", "used by all"],
    "gangbang_participant": ["took part", "one of many", "joined in"],

    # Roles in groups
    "center_of_attention": ["all focused on", "center", "everyone wanted"],
    "facilitator": ["organized", "brought together", "made it happen"],
    "reluctant_participant": ["talked into", "hesitant", "eventually joined"],
    "enthusiastic_participant": ["eager", "couldn't wait", "suggested it"],
    "observer_only": ["just watched", "didn't join", "observer"],
}

# ============================================================================
# SPECIFIC KINK DETAILS - PRAISE/DEGRADATION
# ============================================================================

PRAISE_DEGRADATION = {
    # Praise kink
    "good_boy_praise": ["good boy", "such a good boy", "my good boy"],
    "beautiful_praise": ["beautiful", "gorgeous", "perfect", "stunning"],
    "skill_praise": ["so good at", "talented", "best I've had"],
    "obedience_praise": ["obedient", "did so well", "followed instructions"],
    "physical_praise": ["love your body", "perfect cock", "amazing ass"],
    "effort_praise": ["trying so hard", "doing great", "keep going"],

    # Degradation kink
    "slut_shaming": ["slut", "whore", "easy", "desperate"],
    "size_degradation": ["small", "pathetic", "tiny", "useless"],
    "worthlessness": ["worthless", "nothing", "garbage", "don't deserve"],
    "objectification_verbal": ["just a hole", "meat", "toy", "thing"],
    "comparison_degradation": ["not as good as", "worse than", "pathetic compared"],
    "public_degradation": ["in front of others", "humiliated publicly"],

    # Mixed/complex
    "praise_then_degrade": ["good boy but", "beautiful slut", "perfect whore"],
    "earning_praise": ["had to earn", "prove worthy", "deserved it"],
    "craving_degradation": ["wanted to be called", "needed to hear", "got off on"],
}

# ============================================================================
# SIZE KINK DETAILED
# ============================================================================

SIZE_KINK_DETAILED = {
    # Cock size
    "huge_cock": ["huge", "massive", "monster", "couldn't fit"],
    "thick_cock": ["thick", "girthy", "stretched", "full"],
    "long_cock": ["long", "deep", "hit spots", "bottomed out"],
    "average_appreciated": ["perfect size", "just right", "fit perfectly"],
    "small_cock": ["small", "little", "cute cock", "didn't matter"],

    # Body size difference
    "big_guy_small_guy": ["bigger than", "towered over", "dwarfed"],
    "muscle_size": ["muscles", "so big", "arms around", "engulfed"],
    "height_difference": ["taller", "shorter", "looked up", "looked down"],
    "weight_difference": ["heavier", "lighter", "pinned by weight"],

    # Size reactions
    "intimidated_by_size": ["intimidated", "nervous about", "can I take"],
    "excited_by_size": ["excited", "couldn't wait", "wanted it"],
    "stretched_by_size": ["stretched", "opened up", "made to fit"],
    "size_worship": ["worshipped", "amazed by", "couldn't believe"],
}

# ============================================================================
# BREEDING KINK DETAILED
# ============================================================================

BREEDING_KINK = {
    # Breeding language
    "breed_me": ["breed me", "put a baby in", "knock me up"],
    "seed": ["seed", "plant your seed", "fill me with seed"],
    "claiming_breeding": ["claiming", "marking inside", "mine now"],
    "fertile_language": ["fertile", "ready", "ripe", "receptive"],

    # Cum inside focus
    "cum_inside_demand": ["inside", "don't pull out", "want to feel it"],
    "filling_up": ["filled", "flooded", "pumped full", "overflowing"],
    "multiple_loads": ["again", "more", "keep going", "not done"],
    "leaking_after": ["leaking", "dripping out", "couldn't keep it in"],

    # Breeding scenarios
    "intentional_breeding": ["trying to", "want your baby", "make me pregnant"],
    "accidental_breeding": ["didn't mean to", "accident", "oops"],
    "breeding_program": ["program", "selected", "chosen for"],
    "competitive_breeding": ["who can", "first to", "winner breeds"],
}

# ============================================================================
# VOYEURISM/EXHIBITIONISM DETAILED
# ============================================================================

VOYEURISM_EXHIBITIONISM = {
    # Voyeurism types
    "accidental_voyeur": ["accidentally saw", "walked in on", "didn't mean to watch"],
    "intentional_voyeur": ["watched on purpose", "spying", "hidden"],
    "invited_voyeur": ["asked to watch", "wanted audience", "perform for"],
    "remote_voyeur": ["video", "camera", "livestream", "watching screen"],

    # Exhibitionism types
    "accidental_exposure": ["didn't know", "caught", "seen accidentally"],
    "intentional_exposure": ["wanted to be seen", "showed off", "performed"],
    "risky_exposure": ["might be caught", "public", "risk"],
    "documented_exposure": ["recorded", "photos", "video", "evidence"],

    # Reactions
    "turned_on_watching": ["got hard watching", "couldn't look away", "aroused"],
    "turned_on_being_watched": ["knowing they watched", "put on show", "performed"],
    "shame_from_watching": ["shouldn't have watched", "felt guilty", "wrong"],
    "shame_from_being_watched": ["embarrassed", "exposed", "vulnerable"],

    # Settings
    "window_voyeurism": ["through window", "could see in", "curtains open"],
    "glory_hole_voyeurism": ["glory hole", "hole in wall", "anonymous"],
    "public_display": ["public", "where people could see", "didn't care who saw"],
}

# ============================================================================
# TECHNOLOGY IN STORIES
# ============================================================================

TECHNOLOGY_ELEMENTS = {
    # Communication tech
    "texting_story": ["texted", "text message", "typing", "blue bubbles"],
    "sexting_story": ["sent pics", "nudes", "dirty messages", "screen"],
    "video_call_sex": ["video call", "facetime", "long distance", "screen"],
    "dating_apps": ["app", "grindr", "tinder", "scruff", "matched"],
    "social_media_stalking": ["stalked profile", "looked up", "found online"],

    # Recording tech
    "photos_taken": ["took photos", "pictures", "camera phone", "selfie"],
    "video_recorded": ["recorded", "filmed", "video", "footage"],
    "hidden_camera": ["hidden camera", "didn't know filmed", "secret recording"],
    "consensual_recording": ["asked to record", "for us", "memory"],
    "shared_content": ["shared", "sent to", "posted", "leaked"],

    # Other tech
    "remote_control_toy": ["remote control", "app controlled", "vibrating"],
    "smart_home": ["smart home", "alexa", "lights dimmed", "music played"],
    "porn_reference": ["watched porn", "like in videos", "learned from"],
}

# ============================================================================
# EVIDENCE/DOCUMENTATION
# ============================================================================

EVIDENCE_DOCUMENTATION = {
    # Physical evidence
    "hickeys_marks": ["hickey", "mark", "bruise", "evidence on skin"],
    "cum_evidence": ["cum stains", "dried cum", "evidence of"],
    "disheveled_appearance": ["looked wrecked", "obviously just", "couldn't hide"],
    "smell_evidence": ["smelled like", "scent of sex", "cologne on me"],

    # Digital evidence
    "text_evidence": ["texts", "messages", "screenshots", "receipts"],
    "photo_evidence": ["photos", "pictures", "saved images", "camera roll"],
    "video_evidence": ["video", "recording", "footage", "tape"],
    "social_media_evidence": ["tagged", "posted", "story", "went live"],

    # Discovery of evidence
    "found_evidence": ["found", "discovered", "saw the", "noticed"],
    "confronted_with_evidence": ["showed me", "proof", "couldn't deny"],
    "hiding_evidence": ["deleted", "erased", "hid", "covered up"],
    "evidence_used": ["blackmail", "leverage", "threatened with", "used against"],
}

# ============================================================================
# VERBAL EXPRESSIONS DURING SEX
# ============================================================================

VERBAL_DURING_SEX = {
    # Requests/demands
    "begging_verbal": ["please", "need it", "give me", "more"],
    "demanding_verbal": ["now", "do it", "harder", "faster"],
    "instructing_verbal": ["like this", "right there", "don't stop"],
    "questioning_verbal": ["you like that", "feel good", "want more"],

    # Expressions
    "moaning_words": ["oh god", "fuck", "yes", "oh"],
    "name_calling_sex": ["called his name", "said my name", "who do you belong to"],
    "dirty_narration": ["described what", "told him what", "narrated"],
    "confession_during": ["love you", "always wanted", "never felt"],

    # Responses
    "affirmative": ["yes", "yeah", "uh huh", "please"],
    "negative_playing": ["no", "stop", "can't", "too much"],
    "incoherent": ["couldn't form words", "just sounds", "babbling"],
    "silent_during": ["quiet", "silent", "no words", "just breathing"],

    # Post-verbal
    "pillow_talk_verbal": ["talked after", "whispered", "confessed"],
    "awkward_silence_after": ["didn't know what to say", "quiet after"],
}

# ============================================================================
# PHYSICAL POSITIONS DETAILED
# ============================================================================

POSITIONS_DETAILED = {
    # Face to face
    "missionary_detailed": ["on his back", "legs spread", "looking up"],
    "legs_on_shoulders": ["legs on shoulders", "folded", "deep angle"],
    "wrapped_around": ["legs wrapped", "holding on", "clinging"],
    "sitting_facing": ["sitting", "facing", "eye contact", "intimate"],

    # From behind
    "doggy_detailed": ["hands and knees", "ass up", "face down"],
    "prone_bone": ["flat on stomach", "pressed down", "weight on"],
    "standing_from_behind": ["standing", "bent over", "against wall"],
    "spooning_detailed": ["lying together", "from behind", "lazy morning"],

    # On top
    "riding_detailed": ["riding", "bouncing", "controlling pace"],
    "reverse_riding": ["reverse", "facing away", "watching himself"],
    "sitting_on": ["sat on", "lap", "lowered onto"],

    # Oral positions
    "kneeling_oral": ["on knees", "looking up", "service"],
    "lying_oral": ["lying down", "between legs", "from above"],
    "69_detailed": ["simultaneous", "both", "at same time"],
    "face_sitting": ["sat on face", "smothered", "couldn't breathe"],

    # Creative positions
    "against_wall_detailed": ["against wall", "lifted", "pinned"],
    "on_furniture": ["bent over", "on table", "desk", "counter"],
    "in_water_position": ["in water", "buoyancy", "wet"],
}

# ============================================================================
# FIRST TIME SPECIFICS
# ============================================================================

FIRST_TIME_DETAILS = {
    # First time with man
    "first_gay_experience": ["first time with a guy", "never before", "always wondered"],
    "first_penetration_receiving": ["first time bottoming", "never been", "cherry"],
    "first_penetration_giving": ["first time topping", "never done this", "new"],
    "first_oral_giving": ["first time sucking", "never had cock in mouth"],
    "first_oral_receiving": ["first blowjob", "never been sucked"],

    # Emotional firsts
    "first_love": ["first love", "never felt this", "new feeling"],
    "first_relationship": ["first relationship", "never dated", "boyfriend"],
    "first_kiss_detailed": ["first kiss", "never kissed", "lips touched"],
    "first_crush": ["first crush", "never felt this way", "butterflies"],

    # Physical sensations first time
    "nervous_first_time": ["nervous", "shaking", "scared but excited"],
    "awkward_first_time": ["awkward", "fumbling", "learning"],
    "painful_first_time": ["hurt", "pain", "too much", "had to stop"],
    "pleasurable_first_time": ["better than expected", "amazing", "why wait"],
    "disappointing_first_time": ["not what expected", "over quickly", "awkward"],

    # Guidance during first
    "guided_through": ["showed me", "taught me", "patient", "explained"],
    "figuring_out_together": ["both new", "learning together", "exploring"],
    "experienced_with_virgin": ["experienced one", "virgin one", "teaching"],
}

# ============================================================================
# SPECIFIC PROFESSION SCENARIOS
# ============================================================================

PROFESSION_SCENARIOS = {
    # Blue collar
    "construction_worker": ["construction", "hard hat", "tool belt", "building site"],
    "mechanic_scenario": ["mechanic", "garage", "grease", "car", "under the hood"],
    "plumber_scenario": ["plumber", "pipes", "under sink", "service call"],
    "landscaper_scenario": ["landscaper", "yard work", "sweaty", "outdoor labor"],
    "trucker_scenario": ["trucker", "truck stop", "long haul", "cab sleeper"],
    "farmhand_scenario": ["farm", "barn", "hay", "rural", "rancher"],

    # White collar
    "executive_scenario": ["ceo", "executive", "corner office", "power suit"],
    "lawyer_scenario": ["lawyer", "attorney", "court", "case", "billable hours"],
    "accountant_scenario": ["accountant", "numbers", "desk job", "overtime"],
    "tech_worker_scenario": ["programmer", "startup", "tech bro", "coding"],

    # Service industry
    "bartender_scenario": ["bartender", "bar", "last call", "after hours"],
    "waiter_scenario": ["waiter", "server", "restaurant", "back of house"],
    "barista_scenario": ["barista", "coffee shop", "regular customer", "latte"],
    "delivery_scenario": ["delivery", "package", "at the door", "tip"],

    # Emergency services
    "firefighter_scenario": ["firefighter", "station", "truck", "hero"],
    "paramedic_scenario": ["paramedic", "ambulance", "saved my life"],
    "cop_scenario": ["cop", "officer", "pulled over", "arrest"],

    # Entertainment
    "personal_trainer": ["trainer", "gym", "one on one", "spot me"],
    "massage_therapist": ["massage", "table", "oil", "tension release"],
    "photographer_scenario": ["photographer", "model", "shoot", "poses"],
}

# ============================================================================
# SPORTS SCENARIOS DETAILED
# ============================================================================

SPORTS_SCENARIOS = {
    # Team sports
    "football_scenario": ["football", "quarterback", "huddle", "tackle", "locker room"],
    "basketball_scenario": ["basketball", "court", "practice", "shooting hoops"],
    "baseball_scenario": ["baseball", "dugout", "batting cage", "pitcher mound"],
    "hockey_scenario": ["hockey", "ice", "penalty box", "after game"],
    "soccer_scenario": ["soccer", "pitch", "cleats", "goal"],
    "rugby_scenario": ["rugby", "scrum", "mud", "tackling"],
    "lacrosse_scenario": ["lacrosse", "stick", "field", "prep school"],

    # Individual sports
    "wrestling_scenario": ["wrestling", "mat", "singlet", "pin", "weigh in"],
    "swimming_scenario": ["swimming", "pool", "speedos", "locker room", "diving"],
    "gymnastics_scenario": ["gymnastics", "flexible", "leotard", "apparatus"],
    "track_scenario": ["track", "running", "shorts", "stretching"],
    "tennis_scenario": ["tennis", "court", "whites", "country club"],
    "golf_scenario": ["golf", "course", "clubhouse", "caddy"],

    # Combat sports
    "boxing_scenario": ["boxing", "ring", "gloves", "corner", "rounds"],
    "mma_scenario": ["mma", "cage", "octagon", "submission", "tap out"],
    "martial_arts_scenario": ["dojo", "sensei", "student", "discipline"],

    # Fitness
    "gym_scenario": ["gym", "workout", "weights", "pump", "gains"],
    "yoga_scenario": ["yoga", "mat", "poses", "flexibility", "instructor"],
    "crossfit_scenario": ["crossfit", "box", "wod", "community"],
}

# ============================================================================
# SEASONAL/HOLIDAY SETTINGS
# ============================================================================

SEASONAL_SETTINGS = {
    # Holidays
    "christmas_setting": ["christmas", "holiday", "mistletoe", "gift", "fireplace"],
    "new_years_setting": ["new years", "midnight", "countdown", "kiss at midnight"],
    "valentines_setting": ["valentines", "romantic", "date night", "chocolate"],
    "halloween_setting": ["halloween", "costume", "party", "scary", "trick or treat"],
    "thanksgiving_setting": ["thanksgiving", "family dinner", "grateful", "after dinner"],
    "fourth_july_setting": ["fourth of july", "fireworks", "barbecue", "summer"],
    "pride_setting": ["pride", "parade", "rainbow", "celebration", "community"],

    # Seasons
    "summer_vacation": ["summer", "vacation", "beach", "pool", "heat"],
    "winter_cozy": ["winter", "cold outside", "warm inside", "blankets", "fireplace"],
    "fall_setting": ["fall", "leaves", "sweater weather", "pumpkin", "cozy"],
    "spring_renewal": ["spring", "new beginnings", "flowers", "warmth returning"],

    # Special occasions
    "birthday_setting": ["birthday", "celebration", "gift", "special day"],
    "graduation_setting": ["graduation", "accomplishment", "party", "future"],
    "bachelor_party": ["bachelor party", "last night single", "wild", "vegas"],
    "wedding_setting": ["wedding", "reception", "ceremony", "just married"],
}

# ============================================================================
# MORNING/DAILY ROUTINE
# ============================================================================

DAILY_ROUTINE = {
    # Morning
    "morning_sex": ["morning", "woke up", "sleepy", "morning wood"],
    "shower_routine": ["shower", "getting ready", "wet", "steam"],
    "breakfast_time": ["breakfast", "coffee", "kitchen", "morning routine"],
    "before_work": ["before work", "running late", "quick", "have to go"],

    # Work related
    "lunch_break": ["lunch break", "middle of day", "quick escape"],
    "after_work": ["after work", "decompressing", "long day", "finally home"],
    "work_trip": ["work trip", "hotel", "away from home", "business travel"],
    "office_late_night": ["stayed late", "overtime", "empty office"],

    # Evening
    "dinner_date": ["dinner", "date night", "restaurant", "romantic"],
    "netflix_and_chill": ["watching tv", "movie night", "couch", "netflix"],
    "going_out": ["going out", "bar", "club", "nightlife"],
    "coming_home": ["coming home", "front door", "finally together"],

    # Night
    "bedtime": ["bedtime", "going to sleep", "end of day", "tired"],
    "middle_of_night": ["middle of night", "couldn't sleep", "woke up hard"],
    "early_morning": ["early morning", "before dawn", "quiet", "dark still"],
}

# ============================================================================
# WEATHER EFFECTS ON MOOD
# ============================================================================

WEATHER_MOOD = {
    # Rain
    "rainy_romantic": ["rain", "cozy inside", "listening to rain", "romantic"],
    "thunderstorm_intense": ["thunderstorm", "lightning", "power out", "primal"],
    "rain_trapped": ["stuck inside", "can't leave", "rain won't stop"],

    # Heat
    "hot_weather_sensual": ["hot", "sweating", "minimal clothes", "heat wave"],
    "pool_escape": ["pool", "cooling off", "wet", "refreshing"],
    "summer_lazy": ["too hot to move", "lazy", "languid", "slow"],

    # Cold
    "snowed_in": ["snowed in", "trapped", "cabin", "blizzard"],
    "warming_up": ["cold outside", "warming each other", "body heat"],
    "winter_cozy_mood": ["fireplace", "blankets", "hot chocolate", "cozy"],

    # Weather transitions
    "first_warm_day": ["first warm day", "spring fever", "energy", "outside"],
    "storm_coming": ["storm coming", "pressure", "electric", "anticipation"],
    "after_storm": ["after storm", "clean", "fresh", "rainbow"],
}

# ============================================================================
# FOOD/DRINK ELEMENTS
# ============================================================================

FOOD_DRINK_ELEMENTS = {
    # Alcohol contexts
    "wine_romantic": ["wine", "bottle", "glasses", "romantic dinner"],
    "beer_casual": ["beer", "casual", "watching game", "six pack"],
    "shots_party": ["shots", "party", "drinking games", "drunk"],
    "cocktails_fancy": ["cocktails", "bar", "mixologist", "fancy"],

    # Food contexts
    "cooking_together": ["cooking together", "kitchen", "making dinner"],
    "feeding_each_other": ["fed him", "from my fingers", "bite"],
    "food_play_detailed": ["whipped cream", "chocolate sauce", "licking off"],
    "restaurant_date": ["restaurant", "menu", "ordering", "wine list"],

    # Caffeine
    "coffee_date": ["coffee", "cafe", "first date", "getting to know"],
    "morning_coffee": ["morning coffee", "waking up", "routine"],

    # Special foods
    "breakfast_in_bed": ["breakfast in bed", "surprised", "romantic gesture"],
    "champagne_celebration": ["champagne", "celebration", "bubbles", "toast"],
    "comfort_food": ["comfort food", "cozy", "taking care", "nurturing"],
}

# ============================================================================
# CAR/TRANSPORTATION SCENARIOS
# ============================================================================

TRANSPORTATION_SCENARIOS = {
    # Cars
    "backseat_sex": ["backseat", "car", "parked", "steamy windows"],
    "road_head": ["driving", "road head", "passenger seat"],
    "parking_lot": ["parking lot", "risky", "could be seen"],
    "garage_privacy": ["garage", "privacy", "pulled in"],
    "drive_in_movie": ["drive in", "movie", "dark", "privacy"],
    "road_trip_sex": ["road trip", "motel", "miles from home"],

    # Public transit
    "empty_train": ["train", "empty car", "late night", "rumbling"],
    "airplane_bathroom": ["airplane", "mile high club", "bathroom", "turbulence"],
    "bus_scenario": ["bus", "back of bus", "late night"],

    # Other
    "motorcycle": ["motorcycle", "vibration", "holding on", "leather"],
    "boat_scenario": ["boat", "rocking", "water", "isolated"],
    "elevator_scenario": ["elevator", "stuck", "between floors", "close quarters"],
    "taxi_backseat": ["taxi", "back of cab", "driver might see"],
}

# ============================================================================
# OBJECT/TOY SPECIFICS
# ============================================================================

TOY_SPECIFICS = {
    # Insertion toys
    "dildo_realistic_detail": ["realistic dildo", "veins", "balls", "suction cup"],
    "dildo_glass": ["glass dildo", "smooth", "cold then warm", "beautiful"],
    "dildo_metal": ["metal dildo", "steel", "heavy", "temperature"],
    "plug_jewelry": ["jeweled plug", "pretty", "decorative", "visible"],
    "beads": ["beads", "anal beads", "one by one", "pulling out"],
    "inflatable": ["inflatable", "pump", "expanding", "growing"],

    # Stimulation toys
    "vibrator_internal": ["vibrator", "buzzing", "inside", "p-spot"],
    "vibrator_external": ["wand", "vibrating", "on cock", "stimulation"],
    "electro_toy": ["electro", "shock", "tens", "electricity"],
    "suction_toy": ["suction", "pump", "vacuum", "engulfed"],

    # Restraint toys
    "spreader_bar": ["spreader bar", "legs apart", "exposed", "can't close"],
    "posture_collar": ["posture collar", "can't look down", "forced posture"],
    "arm_binder": ["arm binder", "behind back", "helpless", "single sleeve"],
    "ball_gag": ["ball gag", "drooling", "can't speak", "muffled"],

    # Remote/tech toys
    "remote_controlled": ["remote control", "in public", "surprise buzz"],
    "app_controlled_toy": ["app controlled", "long distance", "phone"],
    "couples_toy": ["couples toy", "both wearing", "connected"],
}

# ============================================================================
# HAIR-RELATED ELEMENTS
# ============================================================================

HAIR_ELEMENTS = {
    # Head hair actions
    "hair_pulling": ["pulled hair", "grabbed hair", "fist in hair", "yanked"],
    "running_through_hair": ["ran fingers through", "soft hair", "stroking"],
    "hair_in_face": ["hair in face", "pushed aside", "tucked behind ear"],
    "haircut_scenario": ["haircut", "barber", "hands in hair", "intimate"],

    # Facial hair
    "beard_burn": ["beard burn", "scratchy", "stubble", "rough"],
    "clean_shaven": ["clean shaven", "smooth", "just shaved"],
    "beard_stroking": ["stroked his beard", "felt the hair", "tugged beard"],
    "mustache_tickle": ["mustache tickled", "above lip", "facial hair"],

    # Body hair
    "chest_hair_playing": ["played with chest hair", "ran through", "curled fingers"],
    "happy_trail": ["happy trail", "below navel", "followed down"],
    "armpit_hair": ["armpit", "hairy pits", "musky", "buried face"],
    "pubic_hair": ["bush", "trimmed", "natural", "bare", "groomed"],

    # Hair states
    "wet_hair": ["wet hair", "shower", "dripping", "slicked back"],
    "messy_hair": ["messy hair", "bed head", "disheveled", "tousled"],
}

# ============================================================================
# SLEEP/DREAM RELATED
# ============================================================================

SLEEP_DREAM = {
    # Sleep states
    "falling_asleep_together": ["fell asleep", "drifted off", "in his arms"],
    "waking_up_together": ["woke up together", "still there", "morning after"],
    "watching_sleep": ["watched him sleep", "peaceful", "beautiful sleeping"],
    "sleepwalking_scenario": ["sleepwalking", "asleep", "unconscious"],

    # Dream content
    "wet_dream": ["wet dream", "dreaming of", "woke up hard", "dream about"],
    "nightmare_comfort": ["nightmare", "bad dream", "comforted", "held after"],
    "dreaming_of_him": ["dreamed about", "couldn't stop thinking", "in my dreams"],
    "dream_vs_reality": ["thought dreaming", "is this real", "pinch me"],

    # Sleep positions
    "spooning_sleep": ["spooning", "big spoon", "little spoon", "behind"],
    "on_chest_sleep": ["on his chest", "heartbeat", "rising falling"],
    "tangled_together": ["tangled", "limbs intertwined", "couldn't tell where"],
    "separate_sleeping": ["other side of bed", "not touching", "space"],

    # Sleep timing
    "insomnia": ["couldn't sleep", "wide awake", "restless", "insomnia"],
    "exhausted_after": ["exhausted", "passed out", "dead to world"],
    "nap_together": ["nap", "afternoon", "lazy day", "siesta"],
}

# ============================================================================
# LAUGHTER/HUMOR IN INTIMACY
# ============================================================================

HUMOR_INTIMACY = {
    # Funny moments
    "awkward_funny": ["awkward but funny", "laughed at ourselves", "not smooth"],
    "body_sounds": ["embarrassing sound", "queef", "stomach growl", "laughed"],
    "position_fail": ["position didn't work", "fell off", "cramp", "oops"],
    "interruption_funny": ["interrupted", "had to stop", "couldn't continue"],

    # Playful intimacy
    "tickling": ["tickled", "ticklish", "squirming", "laughing"],
    "wrestling_playful": ["wrestling", "playful fight", "pinned", "won"],
    "teasing_playful": ["teased", "playful", "joking", "light"],
    "pillow_fight": ["pillow fight", "playful", "led to more"],

    # Humor as connection
    "inside_jokes": ["inside joke", "only we understand", "our thing"],
    "laughing_together": ["laughed together", "comfortable", "natural"],
    "humor_to_relax": ["joke to relax", "lightened mood", "broke tension"],
    "smiling_during": ["smiled", "happy", "joyful", "fun"],

    # Post-coital humor
    "pillow_talk_funny": ["funny after", "joked about", "playful banter"],
    "rating_performance": ["how was that", "out of ten", "notes"],
}

# ============================================================================
# MUSIC/SOUNDTRACK ELEMENTS
# ============================================================================

MUSIC_ELEMENTS = {
    # Music types
    "romantic_music": ["slow song", "love song", "romantic music", "ballad"],
    "club_music": ["bass", "beat", "club music", "dancing", "electronic"],
    "rock_music": ["rock", "guitar", "drums", "concert"],
    "classical_music": ["classical", "orchestra", "piano", "elegant"],
    "no_music": ["silence", "quiet", "just us", "no sound"],

    # Music context
    "dancing_together": ["dancing", "slow dance", "holding close", "swaying"],
    "concert_scenario": ["concert", "show", "crowd", "backstage"],
    "karaoke_scenario": ["karaoke", "singing", "bar", "drunk singing"],
    "music_playing_background": ["music in background", "soundtrack", "playing softly"],

    # Songs significance
    "their_song": ["our song", "whenever I hear", "reminds me of"],
    "song_triggered_memory": ["song came on", "brought back", "remembered"],
    "lyrics_meaningful": ["lyrics", "words", "meant something"],
}

# ============================================================================
# MONEY/CLASS DYNAMICS
# ============================================================================

CLASS_DYNAMICS = {
    # Wealth differences
    "rich_poor": ["rich", "poor", "different worlds", "couldn't afford"],
    "sugar_dynamic": ["sugar daddy", "pays for", "spoils", "kept"],
    "wealth_intimidation": ["intimidated by wealth", "mansion", "expensive"],
    "equal_footing": ["equal", "same level", "no power imbalance"],

    # Money in relationship
    "financial_dependence": ["dependent", "couldn't leave", "needed money"],
    "paying_for_sex": ["paid", "escort", "transaction", "money exchanged"],
    "gifts_and_spoiling": ["gifts", "bought him", "spoiled", "shopping"],
    "money_not_important": ["doesn't matter", "not about money", "genuine"],

    # Status differences
    "celebrity_normal": ["famous", "normal person", "fan", "star"],
    "boss_subordinate": ["power imbalance", "could fire", "job on line"],
    "teacher_student_power": ["grades", "education", "future", "control"],
    "landlord_tenant_power": ["rent", "eviction", "housing", "leverage"],
}

# ============================================================================
# LANGUAGE/COMMUNICATION BARRIERS
# ============================================================================

LANGUAGE_BARRIERS = {
    # Different languages
    "different_languages": ["didn't speak same language", "translator", "barrier"],
    "learning_language": ["teaching me", "learning to say", "new words"],
    "love_in_any_language": ["universal", "body language", "didn't need words"],
    "sexy_foreign_words": ["said something in", "accent", "foreign whispers"],

    # Communication differences
    "shy_vs_outgoing": ["shy one", "outgoing one", "drew him out"],
    "verbal_vs_nonverbal": ["didn't need words", "communicated differently"],
    "misunderstanding": ["misunderstood", "didn't mean", "confusion"],
    "finally_understood": ["finally understood", "clicked", "got it"],

    # Text vs voice
    "better_in_text": ["better over text", "couldn't say in person"],
    "need_to_hear": ["needed to hear", "say it", "voice"],
    "lost_in_translation": ["lost in translation", "meant something else"],
}

# ============================================================================
# MIRROR/REFLECTION ELEMENTS
# ============================================================================

MIRROR_ELEMENTS = {
    # Mirror use
    "watching_in_mirror": ["watched in mirror", "could see", "reflection"],
    "made_to_watch": ["made him watch", "look at yourself", "see what I see"],
    "avoiding_mirror": ["couldn't look", "avoided reflection", "ashamed"],
    "admiring_in_mirror": ["admired", "looked good", "checked self out"],

    # Mirror positions
    "against_mirror": ["against mirror", "pressed to glass", "reflection"],
    "mirror_on_ceiling": ["ceiling mirror", "could see from above", "watched us"],
    "bathroom_mirror": ["bathroom mirror", "steam", "wiped clear"],
    "closet_mirror": ["closet", "full length", "could see everything"],

    # Self-perception
    "seeing_self_differently": ["saw myself differently", "through his eyes"],
    "watching_transformation": ["watched self change", "becoming", "expression"],
    "body_image_mirror": ["how I looked", "self-conscious", "he said beautiful"],
}

# ============================================================================
# PET/ANIMAL REFERENCES (Non-literal)
# ============================================================================

ANIMAL_REFERENCES = {
    # Pet names
    "calling_pet_names": ["baby", "sweetheart", "honey", "darling"],
    "animal_pet_names": ["puppy", "kitten", "bunny", "bear"],
    "possessive_names": ["mine", "my boy", "belongs to me"],
    "degrading_names": ["pig", "bitch", "dog", "slut"],

    # Animal comparisons
    "predator_prey": ["predator", "prey", "hunted", "caught"],
    "animalistic_behavior": ["animal", "primal", "instinct", "beast"],
    "gentle_animal": ["gentle", "lamb", "soft", "tender"],
    "wild_animal": ["wild", "untamed", "feral", "savage"],

    # Pet dynamic (not literal pet play)
    "pet_treatment": ["treated like pet", "good boy", "reward"],
    "ownership_language": ["owned", "belong to", "collar", "claimed"],
}

# ============================================================================
# RELIGIOUS/SPIRITUAL ELEMENTS
# ============================================================================

RELIGIOUS_ELEMENTS = {
    # Religious conflict
    "religious_guilt": ["sinful", "wrong", "going to hell", "forbidden"],
    "religious_rebellion": ["rebelling", "forbidden fruit", "against teachings"],
    "religious_figure": ["priest", "pastor", "church", "confession"],
    "losing_faith": ["lost faith", "questioning", "no longer believe"],

    # Spiritual experiences
    "transcendent_experience": ["transcendent", "spiritual", "out of body"],
    "worship_language": ["worshipped", "divine", "god", "prayer"],
    "sacred_profane": ["sacred", "profane", "holy", "unholy"],
    "confession_dynamic": ["confess", "confession", "sin", "forgiveness"],

    # Cultural religion
    "religious_family": ["religious family", "raised", "expectations"],
    "religious_community": ["community", "congregation", "everyone knows"],
    "religious_holidays": ["religious holiday", "church", "family obligation"],
}

# ============================================================================
# URBAN VS RURAL SETTINGS
# ============================================================================

URBAN_RURAL = {
    # Urban specific
    "city_apartment": ["apartment", "small space", "neighbors", "thin walls"],
    "rooftop_urban": ["rooftop", "city lights", "skyline", "above it all"],
    "alley_urban": ["alley", "behind building", "urban", "gritty"],
    "subway_urban": ["subway", "underground", "transit", "commute"],
    "club_scene": ["club", "nightlife", "downtown", "dancing"],

    # Rural specific
    "farmland": ["farm", "fields", "barn", "rural", "isolated"],
    "small_town": ["small town", "everyone knows", "gossip", "locals"],
    "cabin_woods": ["cabin", "woods", "isolated", "off grid"],
    "country_road": ["country road", "truck", "nowhere around", "stars"],
    "lake_house": ["lake house", "water", "summer", "vacation"],

    # Contrast
    "city_boy_country": ["city boy", "country", "fish out of water"],
    "country_boy_city": ["country boy", "big city", "overwhelmed"],
    "escaping_to_nature": ["escaped", "got away", "nature", "freedom"],
}

# ============================================================================
# AGE-SPECIFIC SCENARIOS
# ============================================================================

AGE_SPECIFIC = {
    # Teen/young adult (18+)
    "college_freshman": ["freshman", "first year", "new to college", "dorm life"],
    "college_senior": ["senior", "graduating", "last year", "figuring out future"],
    "just_turned_18": ["just turned 18", "finally legal", "birthday"],
    "early_twenties": ["early twenties", "young adult", "figuring out life"],

    # Mid adult
    "late_twenties": ["late twenties", "established", "career focused"],
    "thirties_crisis": ["turning thirty", "where am I", "expected more"],
    "forties_confidence": ["forties", "confident", "knows what wants"],
    "mid_life_awakening": ["mid life", "finally accepting", "wasted years"],

    # Mature
    "fifties_liberation": ["fifties", "kids grown", "free", "second life"],
    "silver_daddy_age": ["silver", "distinguished", "experienced", "daddy age"],
    "retirement_freedom": ["retired", "time finally", "bucket list"],
    "later_life_discovery": ["late bloomer", "finally", "never too late"],

    # Age gap specifics
    "mentor_age": ["old enough to be", "mentor", "guidance", "experience"],
    "peer_age": ["same age", "grew up together", "shared experiences"],
    "generational_culture": ["different generation", "music", "references", "gap"],
}

# ============================================================================
# BODY WORSHIP SUB-TYPES
# ============================================================================

BODY_WORSHIP_DETAILED = {
    # Feet worship detailed
    "feet_massage": ["massaged feet", "rubbed", "pressure points"],
    "feet_kissing": ["kissed feet", "each toe", "instep", "ankle"],
    "feet_licking": ["licked soles", "between toes", "arch"],
    "feet_sniffing": ["smelled feet", "after workout", "sweaty feet"],
    "feet_in_face": ["feet in face", "pressed against", "stepped on"],

    # Armpit worship detailed
    "armpit_licking": ["licked armpit", "hairy pit", "musky"],
    "armpit_sniffing": ["smelled armpit", "inhaled", "pheromones"],
    "armpit_nuzzling": ["buried face", "pit", "breathed in"],

    # Ball worship detailed
    "ball_licking": ["licked balls", "sack", "each one"],
    "ball_sucking": ["sucked balls", "mouth full", "gentle"],
    "ball_worship_gentle": ["worshipped balls", "reverent", "careful"],

    # Ass worship detailed
    "ass_kissing": ["kissed ass", "cheeks", "reverent"],
    "ass_spreading": ["spread cheeks", "exposed", "opened"],
    "ass_rimming_worship": ["rimmed", "tongue", "hole worship"],
    "ass_sniffing": ["smelled ass", "face buried", "musk"],

    # Cock worship detailed
    "cock_kissing": ["kissed cock", "shaft", "head", "reverent"],
    "cock_licking": ["licked cock", "base to tip", "traced veins"],
    "cock_nuzzling": ["nuzzled cock", "rubbed face", "cheek against"],
    "foreskin_play": ["foreskin", "pulled back", "tongue under"],

    # Muscle worship detailed
    "bicep_worship": ["felt biceps", "squeezed", "flexed for me"],
    "pec_worship": ["worshipped pecs", "chest", "nipples"],
    "abs_worship": ["traced abs", "licked stomach", "six pack"],
    "back_worship": ["back muscles", "shoulders", "lats"],
    "thigh_worship": ["thighs", "between legs", "powerful"],
}

# ============================================================================
# BDSM CEREMONY ELEMENTS
# ============================================================================

BDSM_CEREMONIES = {
    # Collaring ceremonies
    "collaring_formal": ["collaring ceremony", "witnesses", "vows", "permanent"],
    "collaring_private": ["private collaring", "just us", "intimate moment"],
    "collar_types": ["day collar", "play collar", "formal collar", "eternity"],
    "collar_removal": ["collar removed", "released", "ended", "returned"],

    # Contract elements
    "contract_negotiation": ["negotiated contract", "terms", "limits", "expectations"],
    "contract_signing": ["signed contract", "agreement", "witnessed"],
    "contract_renewal": ["renewed contract", "renegotiated", "anniversary"],
    "contract_termination": ["ended contract", "released", "no longer"],

    # Protocol ceremonies
    "position_training": ["learned positions", "display", "inspection", "waiting"],
    "title_earning": ["earned title", "boy", "slave", "pet", "promoted"],
    "punishment_ritual": ["punishment ritual", "formal", "witnessed"],
    "reward_ceremony": ["reward ceremony", "earned", "privilege granted"],

    # Community ceremonies
    "leather_family": ["leather family", "house", "lineage", "tradition"],
    "title_contest": ["title holder", "Mr Leather", "competition"],
    "mentorship_formal": ["formal mentorship", "taken under wing", "teaching"],
}

# ============================================================================
# NEGOTIATION ELEMENTS
# ============================================================================

NEGOTIATION_ELEMENTS = {
    # Pre-scene negotiation
    "limits_discussion": ["discussed limits", "hard limits", "soft limits", "boundaries"],
    "safe_word_agreement": ["agreed on safe word", "red yellow green", "system"],
    "health_disclosure": ["health status", "tested", "protection", "disclosure"],
    "experience_sharing": ["shared experience", "what I've done", "new to this"],

    # Checklist elements
    "yes_no_maybe": ["checklist", "yes no maybe", "went through list"],
    "interest_levels": ["really want", "willing to try", "hard no"],
    "role_preferences": ["prefer top", "prefer bottom", "switch", "flexible"],
    "intensity_preferences": ["how hard", "how far", "intensity level"],

    # Ongoing negotiation
    "check_ins": ["checked in", "you okay", "color check", "how are you"],
    "adjusting_scene": ["adjusted", "changed", "more", "less", "different"],
    "stopping_scene": ["stopped", "red", "too much", "need to stop"],
    "aftercare_negotiation": ["what do you need", "aftercare plan", "after this"],
}

# ============================================================================
# AFTERCARE PROTOCOLS DETAILED
# ============================================================================

AFTERCARE_DETAILED = {
    # Physical aftercare
    "blanket_aftercare": ["wrapped in blanket", "warm", "cocooned", "safe"],
    "water_aftercare": ["gave water", "hydration", "sips", "bottle"],
    "food_aftercare": ["chocolate", "snacks", "sugar", "energy"],
    "cleaning_aftercare": ["cleaned up", "wiped down", "gentle cloth"],
    "wound_care": ["checked marks", "arnica", "ice", "treated"],

    # Comfort aftercare
    "cuddling_aftercare": ["cuddled", "held close", "spooned", "arms around"],
    "verbal_aftercare": ["told him good", "praised", "reassured", "talked through"],
    "quiet_aftercare": ["quiet together", "no words needed", "presence"],
    "separate_aftercare": ["needed space", "alone time", "decompress separately"],

    # Extended aftercare
    "next_day_check": ["checked next day", "how are you", "still okay"],
    "drop_prevention": ["watching for drop", "extra care", "days after"],
    "processing_talk": ["talked about scene", "what worked", "feelings"],
    "aftercare_failure": ["no aftercare", "left alone", "dropped hard"],

    # Dom aftercare
    "dom_aftercare": ["dom needed care too", "both recovered", "mutual"],
    "dom_drop": ["dom drop", "guilt", "too far", "needed reassurance"],
}

# ============================================================================
# CHARACTER MOTIVATIONS
# ============================================================================

CHARACTER_MOTIVATIONS = {
    # Positive motivations
    "genuine_attraction": ["attracted to", "drawn to", "couldn't resist"],
    "love_motivation": ["loved him", "in love", "feelings"],
    "curiosity_motivation": ["curious", "wanted to try", "wondered what"],
    "connection_seeking": ["lonely", "wanted connection", "needed someone"],

    # Complex motivations
    "revenge_motivation": ["revenge", "get back at", "make him pay"],
    "proving_something": ["prove", "show them", "prove wrong"],
    "escape_motivation": ["escape", "forget", "distraction"],
    "boredom_motivation": ["bored", "nothing else to do", "why not"],

    # Darker motivations
    "power_motivation": ["wanted power", "control", "dominate"],
    "manipulation_motivation": ["manipulate", "get what wanted", "using"],
    "self_destruction": ["self destructive", "didn't care", "punishing self"],
    "addiction_motivation": ["addicted", "couldn't stop", "needed it"],

    # External motivations
    "peer_pressure": ["pressured", "everyone else", "fit in"],
    "money_motivation": ["for money", "paid", "needed cash"],
    "blackmail_motivation": ["blackmailed", "had to", "no choice"],
    "obligation_motivation": ["felt obligated", "owed him", "had to"],
}

# ============================================================================
# RELATIONSHIP RED FLAGS
# ============================================================================

RELATIONSHIP_RED_FLAGS = {
    # Control patterns
    "isolation_pattern": ["isolated from friends", "only me", "cut off"],
    "jealousy_excessive": ["jealous of everyone", "controlling", "possessive"],
    "monitoring_behavior": ["checked phone", "tracked", "followed"],
    "financial_control": ["controlled money", "allowance", "dependent"],

    # Manipulation patterns
    "gaslighting_pattern": ["made me doubt", "crazy", "didn't happen"],
    "love_bombing_pattern": ["too much too fast", "overwhelming", "intense"],
    "silent_treatment": ["wouldn't talk", "punishment silence", "ignored"],
    "blame_shifting": ["always my fault", "never his", "turned around"],

    # Escalation patterns
    "boundary_pushing": ["kept pushing", "ignored no", "tested limits"],
    "anger_issues": ["anger", "explosive", "scared of his reaction"],
    "threats": ["threatened", "if you leave", "consequences"],
    "physical_escalation": ["got physical", "grabbed", "hurt"],

    # Recovery recognition
    "recognizing_abuse": ["realized it was abuse", "finally saw", "named it"],
    "leaving_pattern": ["tried to leave", "went back", "cycle"],
    "getting_help": ["got help", "support", "therapy", "escaped"],
}

# ============================================================================
# RECOVERY/HEALING JOURNEY
# ============================================================================

RECOVERY_HEALING = {
    # Recognizing need
    "hitting_bottom": ["hit bottom", "couldn't continue", "breaking point"],
    "wake_up_call": ["wake up call", "realized", "something had to change"],
    "asking_for_help": ["asked for help", "admitted needed", "reached out"],

    # Active recovery
    "therapy_journey": ["started therapy", "working through", "processing"],
    "support_system": ["found support", "people who understand", "not alone"],
    "boundaries_learning": ["learning boundaries", "saying no", "protecting self"],
    "self_worth_building": ["building self worth", "deserve better", "valued"],

    # Relationship recovery
    "trust_rebuilding": ["rebuilding trust", "slowly", "earning back"],
    "communication_improving": ["better communication", "talking about", "honest"],
    "healthy_relationship": ["healthy now", "different", "what I deserve"],

    # Trauma processing
    "flashback_management": ["managing flashbacks", "grounding", "coping"],
    "trigger_identification": ["identified triggers", "aware now", "prepared"],
    "narrative_reclaiming": ["reclaiming story", "my terms", "power back"],
    "moving_forward": ["moving forward", "not defined by", "future"],
}

# ============================================================================
# DIALOGUE PATTERNS
# ============================================================================

DIALOGUE_PATTERNS = {
    # Texting styles
    "formal_texting": ["proper texts", "full sentences", "punctuation"],
    "casual_texting": ["lol", "u", "abbreviations", "emojis"],
    "sexting_style": ["explicit texts", "dirty", "pics", "describe"],
    "anxious_texting": ["double texting", "are you there", "did I say wrong"],

    # Dirty talk patterns
    "commanding_talk": ["do this", "now", "I said", "obey"],
    "praising_talk": ["so good", "perfect", "beautiful", "amazing"],
    "degrading_talk": ["worthless", "slut", "pathetic", "nothing"],
    "narrating_talk": ["I'm going to", "you feel", "this is what"],
    "questioning_talk": ["you like that", "want more", "tell me"],

    # Emotional dialogue
    "confession_dialogue": ["I have to tell you", "been meaning to say"],
    "argument_dialogue": ["how could you", "I can't believe", "we need to talk"],
    "reconciliation_dialogue": ["I'm sorry", "forgive me", "can we"],
    "declaration_dialogue": ["I love you", "I want you", "I need you"],

    # Scene-specific dialogue
    "begging_dialogue": ["please", "I need", "give me", "don't stop"],
    "resistance_dialogue": ["no", "stop", "don't", "can't"],
    "surrender_dialogue": ["yes", "anything", "yours", "take me"],
}

# ============================================================================
# SCENE BEATS/STRUCTURE
# ============================================================================

SCENE_BEATS = {
    # Opening beats
    "initial_contact": ["first touch", "hand on", "reached out"],
    "tension_acknowledgment": ["finally", "been wanting", "couldn't wait"],
    "clothing_removal_beat": ["started undressing", "took off", "revealed"],
    "first_kiss_beat": ["lips met", "first taste", "beginning"],

    # Escalation beats
    "hands_exploring": ["hands wandered", "explored", "discovered"],
    "oral_transition": ["moved down", "dropped to knees", "mouth found"],
    "penetration_preparation": ["getting ready", "fingers first", "opening up"],
    "main_event_start": ["finally inside", "entered", "joined"],

    # Intensity beats
    "rhythm_establishing": ["found rhythm", "pace set", "moving together"],
    "intensity_building": ["faster", "harder", "more", "escalating"],
    "position_change": ["changed position", "flipped", "moved to"],
    "edge_approaching": ["getting close", "almost", "building"],

    # Climax beats
    "point_of_no_return": ["couldn't stop", "going to", "inevitable"],
    "orgasm_beat": ["came", "finished", "released", "exploded"],
    "partner_finish": ["made him cum", "brought him", "watched him"],

    # Resolution beats
    "immediate_after": ["collapsed", "catching breath", "still connected"],
    "separation_beat": ["pulled out", "apart", "disconnected"],
    "cleanup_beat": ["cleaned up", "tissues", "shower"],
    "emotional_close": ["held each other", "talked", "processed"],
}

# ============================================================================
# SPECIFIC PENETRATION DETAILS
# ============================================================================

PENETRATION_DETAILS = {
    # Preparation
    "no_prep_raw": ["no prep", "just spit", "raw", "bare"],
    "finger_prep": ["fingered first", "one then two", "stretched"],
    "toy_prep": ["plug first", "toy", "opened with"],
    "thorough_prep": ["took time", "very prepared", "ready"],

    # Lube types
    "spit_only": ["spit", "saliva", "no lube"],
    "water_based_lube": ["lube", "water based", "slick"],
    "silicone_lube": ["silicone", "long lasting", "thick"],
    "natural_lube": ["precum", "natural", "self lubricating"],

    # Entry types
    "slow_entry_detail": ["inch by inch", "slowly", "let adjust"],
    "fast_entry_detail": ["all at once", "thrust in", "sudden"],
    "painful_entry": ["hurt going in", "too fast", "burned"],
    "easy_entry": ["slid right in", "took easily", "ready for it"],

    # Depth
    "shallow_thrusts": ["shallow", "just the tip", "teasing"],
    "deep_thrusts": ["deep", "all the way", "bottomed out"],
    "hitting_prostate": ["hit the spot", "prostate", "there", "again"],
    "depth_limit": ["too deep", "couldn't take more", "limit"],

    # Sensation descriptions
    "fullness_feeling": ["so full", "stuffed", "complete"],
    "stretch_feeling": ["stretched", "opened", "made room"],
    "friction_feeling": ["friction", "drag", "tight around"],
    "heat_feeling": ["heat inside", "warmth", "burning"],
}

# ============================================================================
# ORAL SEX DETAILS
# ============================================================================

ORAL_DETAILS = {
    # Technique
    "teasing_licks_oral": ["teasing licks", "tip only", "barely touching"],
    "full_suction": ["sucked hard", "suction", "hollowed cheeks"],
    "tongue_work": ["tongue", "swirling", "flicking", "lapping"],
    "hand_mouth_combo": ["hand and mouth", "both", "stroking while"],

    # Depth
    "shallow_oral": ["just the head", "tip", "teasing"],
    "deep_throat_attempt": ["tried to take more", "gagged", "eyes watered"],
    "deep_throat_success": ["all the way", "nose against", "swallowed whole"],
    "choking_on": ["choked", "couldn't breathe", "too much"],

    # Ball involvement
    "ball_attention": ["paid attention to balls", "licked", "sucked"],
    "ball_neglect": ["focused on cock", "ignored balls", "only shaft"],

    # Finishing oral
    "cum_in_mouth": ["came in mouth", "shot down throat", "filled mouth"],
    "pulled_out_to_cum": ["pulled out", "came on face", "on chest"],
    "swallowed_load": ["swallowed", "every drop", "didn't spill"],
    "spit_it_out": ["spit", "couldn't swallow", "too much"],
}

# ============================================================================
# HANDJOB/MANUAL DETAILS
# ============================================================================

MANUAL_DETAILS = {
    # Grip types
    "firm_grip": ["firm grip", "tight fist", "squeezed"],
    "loose_grip": ["loose grip", "teasing", "light touch"],
    "two_handed": ["both hands", "two fisted", "needed both"],
    "finger_tips": ["finger tips", "delicate", "tracing"],

    # Technique
    "long_strokes": ["long strokes", "base to tip", "full length"],
    "short_strokes": ["short strokes", "focused", "tip only"],
    "twisting_motion": ["twisted", "corkscrewed", "rotated"],
    "thumb_work": ["thumb on head", "rubbing slit", "spreading precum"],

    # Speed variation
    "slow_and_steady": ["slow", "steady", "building"],
    "fast_and_furious": ["fast", "urgent", "racing"],
    "edging_manual": ["edged", "stopped before", "denied"],
    "milking_motion": ["milking", "squeezing", "extracting"],

    # Lube for manual
    "dry_hand": ["dry", "no lube", "friction"],
    "precum_lube": ["precum", "natural", "slick with"],
    "spit_hand": ["spit on hand", "wet with spit"],
    "lotion_oil": ["lotion", "oil", "massage oil", "slippery"],
}

# ============================================================================
# FROTTAGE/OUTERCOURSE
# ============================================================================

FROTTAGE_OUTERCOURSE = {
    # Grinding types
    "cock_to_cock": ["cocks together", "rubbing together", "sword fight"],
    "dry_humping": ["dry humping", "through clothes", "grinding"],
    "intercrural": ["between thighs", "thigh fucking", "intercrural"],
    "ass_grinding": ["grinding on ass", "between cheeks", "hotdogging"],

    # Body surface
    "against_abs": ["against stomach", "abs", "sliding on"],
    "against_back": ["against back", "from behind", "rubbing"],
    "under_arm": ["armpit", "under arm", "musky"],
    "between_pecs": ["between pecs", "chest", "titfuck"],

    # Finishing
    "came_from_grinding": ["came from grinding", "just friction", "no penetration"],
    "came_on_each_other": ["came on each other", "between us", "mixed together"],
}

# ============================================================================
# PROSTATE STIMULATION DETAILED
# ============================================================================

PROSTATE_DETAILED = {
    # Finding it
    "searching_for_spot": ["searching", "looking for", "curved fingers"],
    "found_it": ["found it", "there", "that's the spot"],
    "first_prostate_experience": ["never felt", "didn't know", "new sensation"],

    # Stimulation types
    "finger_prostate": ["fingers", "massaging", "pressing"],
    "toy_prostate": ["prostate toy", "aneros", "massager"],
    "cock_prostate": ["cock hitting", "angle", "every thrust"],

    # Sensations
    "prostate_pleasure": ["overwhelming", "different pleasure", "full body"],
    "prostate_orgasm": ["prostate orgasm", "hands free", "internal"],
    "milking_prostate": ["milked", "draining", "oozing"],

    # Reactions
    "legs_shaking_prostate": ["legs shaking", "couldn't control", "trembling"],
    "unexpected_orgasm": ["surprised by", "didn't expect", "sudden"],
}

# ============================================================================
# CHASTITY/DENIAL DETAILED
# ============================================================================

CHASTITY_DENIAL = {
    # Device types
    "metal_cage": ["metal cage", "steel", "cold", "heavy"],
    "plastic_cage": ["plastic cage", "clear", "see through"],
    "silicone_cage": ["silicone", "flexible", "comfortable"],

    # Duration
    "short_term_denial": ["few hours", "for the scene", "temporary"],
    "extended_denial": ["days", "week", "long term"],

    # Keyholder dynamics
    "keyholder": ["holds key", "keyholder", "decides when"],
    "begging_for_release": ["begged", "please unlock", "needed to cum"],
    "denied_release": ["denied", "not yet", "longer"],

    # Sensations
    "frustration_chastity": ["frustrated", "desperate", "aching"],
    "arousal_in_cage": ["hard in cage", "straining", "couldn't grow"],
    "leaking_in_cage": ["leaking", "dripping", "constant arousal"],
}

# ============================================================================
# EDGING/ORGASM CONTROL DETAILED
# ============================================================================

EDGING_DETAILED = {
    # Building
    "edge_reached": ["right at edge", "about to", "so close"],
    "pulled_back": ["stopped", "pulled back", "denied"],
    "multiple_edges": ["again and again", "lost count", "so many times"],

    # Release types
    "finally_allowed": ["finally", "permission", "go ahead"],
    "ruined_orgasm_edge": ["ruined", "stopped during", "leaked out"],
    "explosive_release": ["explosive", "intense", "worth the wait"],

    # Psychological
    "begging_to_cum": ["begging", "please", "need to"],
    "crying_frustration": ["crying", "frustrated tears", "too much"],
    "floating_space": ["floating", "gone", "subspace from edging"],
}

# ============================================================================
# HYPNOSIS/MIND CONTROL ELEMENTS
# ============================================================================

HYPNOSIS_ELEMENTS = {
    # Induction
    "eye_fixation": ["look into my eyes", "focus", "can't look away"],
    "voice_induction": ["listen to my voice", "deep voice", "commands"],
    "spiral_visual": ["spiral", "swirling", "going deeper"],

    # Trance states
    "light_trance": ["relaxed", "suggestible", "open"],
    "deep_trance": ["deep under", "completely gone", "blank"],
    "resistance_overcome": ["tried to resist", "couldn't", "gave in"],

    # Suggestions
    "arousal_trigger": ["arousal trigger", "word made hard", "conditioned"],
    "obedience_suggestion": ["obey", "follow commands", "must comply"],
    "pleasure_amplification": ["feel more", "intense", "amplified"],
}

# ============================================================================
# PUBLIC SEX SPECIFICS
# ============================================================================

PUBLIC_SEX_SPECIFICS = {
    # Location risk levels
    "semi_private": ["bathroom stall", "back room", "somewhat hidden"],
    "definitely_public": ["in public", "people around", "could see"],

    # Getting caught
    "almost_caught_public": ["almost caught", "close call", "someone came"],
    "actually_caught": ["caught", "walked in on", "saw us"],
    "exhibitionist_intent": ["wanted to be seen", "didn't care", "turned on by risk"],

    # Aftermath
    "thrill_of_public": ["thrilling", "rush", "exciting"],
    "want_to_again": ["want to do again", "addicted to risk", "more"],
}

# ============================================================================
# FANTASY CREATURES DETAILED
# ============================================================================

FANTASY_CREATURES = {
    # Vampires
    "vampire_bite": ["fangs", "bite", "neck", "blood"],
    "vampire_thrall": ["thrall", "hypnotized by", "couldn't resist"],
    "vampire_seduction": ["supernaturally attractive", "alluring", "drawn to"],

    # Werewolves
    "werewolf_mate": ["mate", "claimed", "bonded", "pack"],
    "werewolf_heat": ["heat", "rut", "instinct", "couldn't control"],
    "werewolf_knot": ["knotted", "swelled", "locked together", "tied"],

    # Demons
    "demon_deal": ["deal", "contract", "sold soul", "bargain"],
    "demon_corruption": ["corrupted", "tainted", "darkness spreading"],
    "incubus_feeding": ["fed on", "energy", "life force", "pleasure"],

    # Other
    "fallen_angel": ["fallen", "cast out", "forbidden", "lost grace"],
    "fae_bargain": ["fae deal", "careful words", "trick", "binding"],
}

# ============================================================================
# MEDICAL SCENARIOS DETAILED
# ============================================================================

MEDICAL_SCENARIOS = {
    # Exam scenarios
    "prostate_exam": ["prostate exam", "doctor's fingers", "medical"],
    "physical_exam": ["physical", "examination", "professional"],
    "sports_physical": ["sports physical", "athlete", "required"],

    # Role elements
    "clinical_language": ["clinical", "medical terms", "professional"],
    "latex_gloves": ["latex gloves", "snap", "clinical"],
    "medical_gown": ["gown", "open back", "exposed"],
    "stirrups_position": ["stirrups", "spread", "vulnerable position"],

    # Power dynamics
    "doctor_authority": ["doctor knows best", "trust me", "professional"],
    "vulnerable_patient": ["vulnerable", "exposed", "at mercy"],
}

# ============================================================================
# UNIFORMS DETAILED
# ============================================================================

UNIFORMS_DETAILED = {
    # Military
    "dress_uniform": ["dress uniform", "formal", "medals", "pristine"],
    "camo_uniform": ["camo", "fatigues", "combat uniform"],

    # Emergency services
    "firefighter_gear": ["turnout gear", "suspenders", "helmet"],
    "police_uniform": ["police uniform", "badge", "belt", "authority"],

    # Sports
    "wrestling_singlet": ["singlet", "tight", "revealing", "spandex"],
    "swim_speedo": ["speedo", "swim brief", "revealing", "wet"],

    # Work
    "suit_and_tie": ["suit", "tie", "professional", "power"],
    "scrubs_uniform": ["scrubs", "medical", "loose", "easy access"],

    # Fetish
    "leather_uniform": ["leather uniform", "cap", "boots", "harness"],
    "jockstrap_only": ["just jockstrap", "ass exposed", "minimal"],
}

# ============================================================================
# PHONE/VIDEO SEX
# ============================================================================

PHONE_VIDEO_SEX = {
    # Phone sex
    "phone_breathing": ["heard breathing", "heavy breath", "phone against ear"],
    "phone_description": ["described what doing", "told him", "narrated"],
    "phone_together": ["came together", "heard him cum", "simultaneous"],

    # Video elements
    "video_showing": ["showed cock", "showed ass", "on display"],
    "video_mutual": ["both on camera", "watching each other", "mutual"],

    # Long distance
    "missing_touch": ["wished could touch", "distance", "not the same"],
    "anticipation_reunion": ["can't wait to see", "reunion", "finally together"],
}

# ============================================================================
# TEARS DURING SEX
# ============================================================================

TEARS_DURING_SEX = {
    # Causes
    "tears_from_pleasure": ["crying from pleasure", "too good", "overwhelming"],
    "tears_from_pain": ["tears from pain", "hurt", "too much"],
    "tears_from_emotion": ["emotional tears", "feelings", "love"],

    # Types
    "eyes_watering": ["eyes watering", "welling up", "misty"],
    "full_crying": ["crying", "sobbing", "tears streaming"],

    # Reactions
    "wiped_tears": ["wiped tears", "kissed tears", "gentle"],
    "turned_on_by_tears": ["turned on by tears", "beautiful crying"],
    "held_after_crying": ["held", "comforted", "it's okay"],
}

# ============================================================================
# MARKING/CLAIMING
# ============================================================================

MARKING_CLAIMING = {
    # Physical marks
    "hickey_neck": ["hickey on neck", "visible mark", "claimed"],
    "hickey_hidden": ["hickey hidden", "only we know", "secret mark"],
    "bite_marks": ["bite marks", "teeth", "permanent"],
    "scratch_marks": ["scratches", "nails", "back scratched"],
    "bruises_intentional": ["intentional bruises", "finger shaped", "grip marks"],

    # Cum marking
    "came_on_face": ["came on face", "facial", "marked"],
    "came_on_body": ["came on chest", "stomach", "covered"],
    "came_inside_marking": ["came inside", "filled", "claimed inside"],

    # Verbal claiming
    "mine_verbal": ["mine", "you're mine", "belong to me"],
    "ownership_declaration": ["own you", "my property", "claimed"],

    # After marking
    "admiring_marks": ["admired marks", "looked at", "proof"],
    "hiding_marks": ["hiding marks", "cover up", "can't let see"],
}

# ============================================================================
# VIRGINITY/FIRST TIME FOCUS
# ============================================================================

VIRGINITY_FOCUS = {
    # Types of virginity
    "anal_virgin": ["anal virgin", "never been fucked", "cherry"],
    "oral_virgin": ["never sucked", "first time oral"],
    "complete_virgin": ["complete virgin", "never done anything", "pure"],

    # Taking virginity
    "taking_virginity": ["took his virginity", "first", "cherry popped"],
    "gentle_deflowering": ["gentle", "careful", "made it good"],
    "rough_deflowering": ["rough", "didn't care", "just took"],

    # Reactions
    "virgin_nervous": ["nervous", "scared", "shaking"],
    "virgin_eager": ["eager", "ready", "wanted it"],
    "virgin_pain": ["hurt", "pain", "burned"],
    "virgin_pleasure": ["felt good", "better than expected", "wanted more"],

    # Significance
    "virginity_important": ["saving it", "special", "meaningful"],
    "virginity_casual": ["just get it over with", "doesn't matter"],
    "regret_losing": ["regret", "wish waited", "wrong person"],
    "glad_lost": ["glad", "finally", "no regrets"],
}

# ============================================================================
# ANONYMOUS/STRANGER SEX
# ============================================================================

ANONYMOUS_SEX = {
    # Meeting contexts
    "cruising": ["cruising", "park", "rest stop", "looking"],
    "bathhouse": ["bathhouse", "sauna", "steam room", "towel"],
    "glory_hole": ["glory hole", "through wall", "anonymous"],
    "dark_room": ["dark room", "couldn't see", "just felt"],
    "app_hookup": ["app", "grindr", "just met", "address"],

    # No names
    "no_names_exchanged": ["didn't exchange names", "anonymous", "strangers"],
    "fake_names": ["fake name", "lied about", "didn't matter"],
    "names_after": ["names after", "finally introduced", "who are you"],

    # Emotional aspects
    "pure_physical": ["just physical", "no feelings", "bodies"],
    "unexpected_connection": ["unexpected connection", "felt something", "surprised"],
    "seeking_another": ["another stranger", "next one", "couldn't stop"],
    "one_and_done": ["one time", "never again", "just once"],
}

# ============================================================================
# DIRTY/MESSY ELEMENTS
# ============================================================================

DIRTY_MESSY = {
    # Fluids mess
    "cum_everywhere": ["cum everywhere", "covered", "dripping", "soaked"],
    "sweat_soaked": ["drenched in sweat", "soaking wet", "dripping"],
    "spit_messy": ["spit", "drool", "wet", "sloppy"],
    "lube_everywhere": ["lube everywhere", "slippery", "mess"],

    # After mess
    "didn't_clean_up": ["didn't clean", "stayed dirty", "let it dry"],
    "quick_wipe": ["quick wipe", "tissues", "minimal"],
    "thorough_clean": ["showered after", "cleaned up", "fresh"],

    # Enjoying mess
    "loved_the_mess": ["loved being messy", "dirty", "filthy"],
    "disgusted_by_mess": ["disgusted", "gross", "needed to clean"],
    "marked_by_mess": ["marked", "his cum on me", "evidence"],
}

# ============================================================================
# COMPETITION/GAMES
# ============================================================================

COMPETITION_GAMES = {
    # Sex games
    "who_cums_first": ["who cums first", "competition", "loser"],
    "endurance_contest": ["how long", "endurance", "hold out"],
    "dare_games": ["dared to", "truth or dare", "had to"],
    "strip_games": ["strip poker", "lost clothing", "naked loser"],

    # Power games
    "wrestling_for_top": ["wrestled for", "who tops", "winner fucks"],
    "bet_stakes": ["bet", "if I win", "stakes"],
    "proving_something": ["prove", "show me", "better than"],

    # Outcomes
    "graceful_loser": ["lost gracefully", "accepted", "good sport"],
    "sore_loser": ["sore loser", "demanded rematch", "sulked"],
    "victory_lap": ["victory", "won", "claimed prize"],
}

# ============================================================================
# ROPE BONDAGE PATTERNS (Shibari)
# ============================================================================

ROPE_PATTERNS = {
    # Basic ties
    "single_column": ["single column", "wrist tie", "basic restraint"],
    "double_column": ["double column", "wrists together", "ankles together"],
    "box_tie": ["box tie", "takate kote", "arms behind back"],
    "chest_harness": ["chest harness", "rope bra", "decorative chest"],
    "hip_harness": ["hip harness", "rope underwear", "crotch rope"],

    # Decorative patterns
    "diamond_pattern": ["diamond pattern", "geometric", "decorative"],
    "pentagram_pattern": ["pentagram", "star pattern", "chest star"],
    "turtle_shell": ["turtle shell", "kikkou", "body harness"],
    "dragonfly_sleeve": ["dragonfly", "arm sleeve", "decorative arm"],

    # Functional ties
    "frog_tie": ["frog tie", "legs bent", "knees spread"],
    "strappado": ["strappado", "arms up behind", "stress position"],
    "ball_tie": ["ball tie", "knees to chest", "compact"],
    "ebi_tie": ["ebi", "shrimp tie", "folded forward"],

    # Suspension ties
    "futomomo": ["futomomo", "thigh tie", "suspension point"],
    "hip_suspension": ["hip suspension", "horizontal", "flying"],
    "partial_suspension_rope": ["partial suspension", "some weight", "supported"],
    "full_suspension_rope": ["full suspension", "completely off ground", "advanced"],

    # Rope types
    "jute_rope": ["jute", "natural", "traditional"],
    "hemp_rope": ["hemp", "rough", "natural fiber"],
    "cotton_rope": ["cotton", "soft", "beginner friendly"],
    "nylon_rope": ["nylon", "synthetic", "smooth"],
}

# ============================================================================
# IMPACT PATTERNS/MARKS
# ============================================================================

IMPACT_PATTERNS = {
    # Mark types
    "parallel_lines": ["parallel lines", "cane marks", "stripes"],
    "crosshatch": ["crosshatch", "crossed marks", "grid pattern"],
    "random_marks": ["random", "scattered", "all over"],
    "targeted_marks": ["targeted", "specific spot", "same place"],
    "wrap_marks": ["wrap", "wrapped around", "side marks"],

    # Mark colors
    "pink_marks": ["pink", "light marks", "just starting"],
    "red_marks": ["red", "welts", "raised"],
    "purple_marks": ["purple", "bruising", "deep"],
    "lasting_marks": ["lasting", "days later", "reminder"],

    # Techniques
    "warm_up_impact": ["warm up", "starting light", "building"],
    "thuddy_impact": ["thuddy", "deep", "heavy", "flogger"],
    "stingy_impact": ["stingy", "sharp", "surface", "cane"],
    "mixed_impact": ["mixed", "variety", "unpredictable"],

    # Patterns
    "counting_strokes": ["counted", "ten strokes", "number"],
    "until_crying": ["until crying", "pushed to tears", "breaking point"],
    "on_demand": ["whenever I want", "random", "kept on edge"],
}

# ============================================================================
# SPECIFIC TOY BRANDS/TYPES
# ============================================================================

TOY_BRANDS_TYPES = {
    # Dildo brands/styles
    "bad_dragon": ["bad dragon", "fantasy", "knot", "exotic"],
    "realistic_brand": ["doc johnson", "realistic", "lifelike"],
    "glass_artisan": ["glass", "artisan", "pyrex", "beautiful"],
    "metal_njoy": ["njoy", "stainless steel", "heavy", "cold"],

    # Plug types
    "jewel_plug": ["jewel plug", "princess plug", "decorative"],
    "tunnel_plug": ["tunnel plug", "hollow", "open access"],
    "expanding_plug": ["expanding", "inflatable", "grows"],
    "vibrating_plug": ["vibrating plug", "remote", "buzzing"],

    # Restraint brands
    "leather_cuffs_quality": ["padded leather", "quality cuffs", "comfortable"],
    "medical_restraints": ["medical grade", "hospital style", "secure"],
    "quick_release": ["quick release", "safety", "easy off"],

    # Electro brands
    "violet_wand_type": ["violet wand", "neon", "electricity play"],
    "tens_unit_type": ["tens unit", "pads", "muscle stim"],
    "estim_box": ["estim", "erotic electro", "cock ring electro"],

    # Chastity types
    "holy_trainer": ["holy trainer", "plastic cage", "comfortable"],
    "metal_cage_type": ["metal cage", "steel", "secure"],
    "full_belt": ["full belt", "complete coverage", "locked"],
}

# ============================================================================
# ROLEPLAY SCRIPT ELEMENTS
# ============================================================================

ROLEPLAY_SCRIPTS = {
    # Opening lines
    "scene_setup": ["the scene is", "you are", "imagine"],
    "character_intro": ["I am your", "you will call me", "address me as"],
    "situation_establish": ["you've been caught", "you need", "I found you"],

    # Power exchange scripts
    "rules_declaration": ["the rules are", "you will", "you will not"],
    "punishment_announcement": ["you need to be punished", "consequence", "discipline"],
    "permission_scripts": ["you may", "you may not", "ask permission"],

    # Dirty talk scripts
    "describing_actions": ["I'm going to", "feel me", "this is what"],
    "demanding_response": ["tell me", "say it", "I want to hear"],
    "narrating_pleasure": ["you like that", "feels good", "you're enjoying"],

    # Scene transitions
    "escalation_cues": ["now I'm going to", "next", "ready for more"],
    "checking_in_script": ["color", "how are you", "still good"],
    "ending_scene": ["scene over", "coming back", "it's done"],

    # Aftercare scripts
    "praise_after": ["you did so well", "proud of you", "good job"],
    "comfort_words": ["I've got you", "you're safe", "it's okay"],
    "grounding_scripts": ["feel the blanket", "you're here", "with me"],
}

# ============================================================================
# ERA-SPECIFIC SLANG
# ============================================================================

ERA_SLANG = {
    # 1970s gay slang
    "seventies_slang": ["trick", "cruise", "tea room", "chicken hawk", "clone"],
    "disco_era": ["disco", "studio 54", "poppers", "mustache"],
    "pre_aids_era": ["before aids", "free love", "bathhouse culture"],

    # 1980s slang
    "eighties_slang": ["nancy boy", "mary", "friend of dorothy", "family"],
    "aids_crisis_language": ["plague", "positive", "kaposi", "akt up"],
    "leather_bar_slang": ["hanky code", "back pocket", "colors", "flagging"],

    # 1990s slang
    "nineties_slang": ["out and proud", "queer", "homo", "breeder"],
    "rave_culture": ["rave", "e", "rolling", "warehouse"],

    # 2000s slang
    "aughts_slang": ["metrosexual", "down low", "dl", "trade"],
    "internet_era": ["a/s/l", "cyber", "cam", "online hookup"],

    # Modern slang
    "current_slang": ["vers", "masc", "fem", "top/bottom", "side"],
    "app_slang": ["looking", "hosting", "now", "gen", "pnp"],
    "meme_culture": ["daddy", "twink death", "gay panic", "disaster gay"],
}

# ============================================================================
# CHARACTER BACKSTORY ELEMENTS
# ============================================================================

CHARACTER_BACKSTORY = {
    # Childhood elements
    "knew_early": ["always knew", "since childhood", "first crush"],
    "late_realization": ["didn't realize until", "late bloomer", "took time"],
    "childhood_trauma": ["childhood", "early experiences", "shaped by"],
    "supportive_upbringing": ["supportive family", "accepting", "lucky"],
    "repressive_upbringing": ["repressive", "religious home", "forbidden"],

    # First experiences
    "first_crush_backstory": ["first crush", "couldn't stop thinking", "realized"],
    "first_experience_backstory": ["first time", "changed everything", "awakening"],
    "first_heartbreak": ["first heartbreak", "never forgot", "learned from"],
    "first_love": ["first love", "thought forever", "intense"],

    # Past relationships
    "ex_boyfriend": ["ex", "used to date", "before you"],
    "bad_relationship_past": ["bad relationship", "abusive ex", "escaped"],
    "good_relationship_ended": ["good but ended", "grew apart", "timing"],
    "never_had_relationship": ["never had", "first relationship", "new to this"],

    # Current life
    "out_to_everyone": ["out", "everyone knows", "openly gay"],
    "partially_out": ["some people know", "not at work", "selective"],
    "closeted_backstory": ["closeted", "hiding", "double life"],
    "journey_to_acceptance": ["journey", "process", "getting there"],
}

# ============================================================================
# PLOT TWIST TYPES
# ============================================================================

PLOT_TWISTS = {
    # Identity twists
    "secret_identity": ["secret identity", "didn't know who", "revealed"],
    "not_who_claimed": ["lied about identity", "fake name", "discovered"],
    "related_twist": ["related", "family connection", "shouldn't have"],
    "knew_all_along": ["knew who I was", "playing", "manipulated"],

    # Relationship twists
    "already_together": ["already dating", "cheating on", "had boyfriend"],
    "ex_connection": ["your ex", "his ex", "small world"],
    "set_up": ["set up", "planned", "matchmaking"],
    "bet_reveal": ["was a bet", "dared to", "not real"],

    # Situation twists
    "caught_twist": ["got caught", "someone saw", "exposed"],
    "pregnancy_scare": ["thought pregnant", "test", "scare"],
    "disease_reveal": ["positive", "had to tell", "disclosure"],
    "moving_away": ["moving", "leaving", "long distance"],

    # Emotional twists
    "feelings_developed": ["caught feelings", "wasn't supposed to", "just sex"],
    "unrequited_revealed": ["loved me all along", "didn't know", "years"],
    "using_each_other": ["both using", "mutual", "honest now"],
    "real_all_along": ["was real", "wasn't fake", "meant it"],
}

# ============================================================================
# CONSENT NEGOTIATION SPECIFIC
# ============================================================================

CONSENT_SPECIFIC = {
    # Asking consent
    "verbal_ask": ["can I", "may I", "do you want", "is this okay"],
    "nonverbal_ask": ["looked for permission", "waited for nod", "checked eyes"],
    "ongoing_consent": ["kept checking", "still okay", "want to continue"],
    "enthusiastic_yes": ["yes", "please", "want this", "don't stop"],

    # Giving consent
    "explicit_yes": ["said yes", "agreed", "consented", "gave permission"],
    "body_language_yes": ["pulled closer", "spread legs", "nodded"],
    "initiating": ["initiated", "started it", "made first move"],

    # Withdrawing consent
    "said_stop": ["said stop", "no", "don't", "wait"],
    "safe_word_used": ["safe word", "red", "mercy", "stop word"],
    "body_language_no": ["pulled away", "tensed up", "closed off"],
    "respected_withdrawal": ["stopped immediately", "checked in", "made sure okay"],

    # Consent violations
    "ignored_no": ["ignored no", "kept going", "didn't stop"],
    "couldn't_consent": ["couldn't consent", "too drunk", "unconscious"],
    "coerced": ["pressured", "guilted", "manipulated into"],
    "regretted_after": ["regretted", "shouldn't have", "felt wrong"],
}

# ============================================================================
# SPECIFIC KINK MICRO-CATEGORIES
# ============================================================================

KINK_MICRO = {
    # Underwear specific
    "jockstrap_fetish": ["jockstrap", "straps", "ass exposed", "pouch"],
    "briefs_fetish": ["briefs", "tighty whities", "bulge", "cotton"],
    "boxer_fetish": ["boxers", "loose", "access", "button fly"],
    "worn_underwear": ["worn", "day old", "scent", "stained"],
    "underwear_theft": ["stole underwear", "kept them", "trophy"],

    # Sock/shoe specific
    "sock_fetish": ["socks", "worn socks", "sweaty", "smell"],
    "shoe_fetish": ["shoes", "sneakers", "boots", "licking"],
    "barefoot_fetish": ["barefoot", "naked feet", "soles"],

    # Specific body part micro
    "navel_fetish": ["belly button", "navel", "innie", "outie"],
    "adam_apple_fetish": ["adam's apple", "throat", "bobbing"],
    "vein_fetish": ["veins", "vascularity", "pulsing", "visible"],
    "tan_lines_fetish": ["tan lines", "speedo lines", "contrast"],

    # Specific act micro
    "facesitting_specific": ["face sitting", "sat on face", "smothered"],
    "queening": ["queening", "throne", "seat", "worship"],
    "teabagging": ["teabagging", "balls on face", "dipping"],
}

# ============================================================================
# BREATH/BREATHING PATTERNS
# ============================================================================

BREATHING_PATTERNS = {
    # Arousal breathing
    "quickening_breath": ["breathing faster", "quickening", "shallow"],
    "heavy_breathing": ["heavy breathing", "deep breaths", "labored"],
    "panting": ["panting", "gasping", "couldn't catch breath"],
    "breath_holding": ["held breath", "stopped breathing", "suspended"],

    # Orgasm breathing
    "breath_before_orgasm": ["breath caught", "inhaled sharply", "held"],
    "breath_during_orgasm": ["exhaled", "released", "cried out"],
    "breath_after_orgasm": ["catching breath", "recovering", "slowing"],

    # Breath play
    "choking_breath": ["hand on throat", "squeezed", "restricted"],
    "controlled_breathing": ["told when to breathe", "controlled", "permission"],
    "breathing_together": ["breathed together", "synchronized", "in rhythm"],

    # Emotional breathing
    "nervous_breathing": ["nervous breath", "shaky", "uneven"],
    "relaxing_breath": ["deep breath", "calming", "centering"],
    "sobbing_breath": ["sobbing", "hiccuping", "gasping through tears"],
}

# ============================================================================
# EYE CONTACT SPECIFICS
# ============================================================================

EYE_CONTACT_SPECIFIC = {
    # Types of looks
    "hungry_look": ["hungry look", "devouring", "wanting"],
    "loving_look": ["loving look", "soft eyes", "adoration"],
    "dominant_look": ["dominant look", "commanding", "powerful"],
    "submissive_look": ["looking up", "pleading eyes", "begging"],
    "challenging_look": ["challenging", "daring", "defiant"],

    # Eye contact during acts
    "eye_contact_oral": ["looked up while sucking", "eyes on", "watching reaction"],
    "eye_contact_penetration": ["looked into eyes", "watched face", "connected"],
    "eye_contact_orgasm": ["eyes locked when came", "watched him cum", "saw it"],

    # Avoiding eyes
    "too_intense": ["too intense", "had to look away", "overwhelming"],
    "shame_avoidance": ["couldn't look", "ashamed", "embarrassed"],
    "forced_eye_contact": ["made him look", "don't look away", "watch me"],

    # Eye expressions
    "eyes_widening": ["eyes widened", "surprise", "shock"],
    "eyes_closing": ["eyes closed", "lost in sensation", "overwhelmed"],
    "eyes_rolling_back": ["eyes rolled back", "gone", "pleasure"],
    "tears_in_eyes": ["tears in eyes", "welling up", "emotional"],
}

# ============================================================================
# HAND/FINGER SPECIFICS
# ============================================================================

HAND_SPECIFICS = {
    # Hand types
    "big_hands": ["big hands", "large", "engulfed", "covered"],
    "rough_hands": ["rough hands", "calloused", "working hands"],
    "soft_hands": ["soft hands", "smooth", "gentle"],
    "skilled_hands": ["skilled", "knew what doing", "experienced"],

    # Finger actions
    "finger_insertion": ["finger inside", "pushed in", "curled"],
    "multiple_fingers": ["two fingers", "three", "stretching"],
    "finger_fucking": ["finger fucked", "in and out", "rhythm"],
    "prostate_fingers": ["found prostate", "pressed", "massaged"],

    # Hand positions
    "hand_on_throat": ["hand on throat", "choking", "control"],
    "hand_in_hair": ["hand in hair", "grabbed", "pulled"],
    "hand_on_hip": ["hand on hip", "gripped", "guiding"],
    "hands_pinned": ["pinned hands", "held down", "restrained"],

    # Finger play
    "finger_sucking": ["sucked fingers", "in mouth", "tasting"],
    "finger_tracing": ["traced", "outlined", "explored"],
    "fingertip_teasing": ["fingertips", "barely touching", "light"],
}

# ============================================================================
# VERBAL CUES/REACTIONS
# ============================================================================

VERBAL_CUES = {
    # Affirmative sounds
    "yes_variations": ["yes", "yeah", "uh huh", "mm hmm"],
    "more_requests": ["more", "don't stop", "keep going", "again"],
    "harder_faster": ["harder", "faster", "deeper", "more"],
    "right_there": ["right there", "that spot", "yes there", "found it"],

    # Names/titles
    "name_moaning": ["moaned name", "said his name", "called out"],
    "title_use": ["sir", "daddy", "master", "boy"],
    "pet_name_use": ["baby", "babe", "sweetheart", "honey"],

    # Warnings
    "close_warning": ["close", "gonna cum", "almost", "can't hold"],
    "stop_warning": ["stop or I'll", "too close", "slow down"],
    "coming_announcement": ["I'm coming", "cumming", "now", "oh god"],

    # Reactions
    "fuck_exclamation": ["fuck", "oh fuck", "fucking hell"],
    "god_exclamation": ["oh god", "god yes", "jesus", "christ"],
    "wordless_sounds": ["just sounds", "couldn't form words", "incoherent"],
    "whimpering": ["whimpered", "whining", "keening", "mewling"],
}

# ============================================================================
# TEMPERATURE PLAY SPECIFIC
# ============================================================================

TEMPERATURE_PLAY = {
    # Cold elements
    "ice_play": ["ice", "ice cube", "melting", "dripping cold"],
    "cold_metal": ["cold metal", "steel", "chilled toy"],
    "cold_water": ["cold water", "shower", "shocking"],
    "cold_room": ["cold room", "goosebumps", "nipples hard"],

    # Hot elements
    "wax_temperature": ["hot wax", "dripping", "burning", "candle"],
    "hot_water": ["hot water", "steaming", "warming"],
    "heated_toy": ["warmed toy", "heated", "body temperature"],
    "hot_breath": ["hot breath", "warm air", "breathing on"],

    # Contrast
    "hot_cold_contrast": ["hot then cold", "contrast", "alternating"],
    "fire_and_ice": ["fire and ice", "both", "switching"],
    "temperature_torture": ["torture", "couldn't predict", "which next"],

    # Body heat
    "body_warmth": ["body heat", "warm skin", "radiating"],
    "fever_hot": ["feverish", "burning up", "too hot"],
    "cold_hands_warm": ["cold hands", "warming on skin", "contrast"],
}

# ============================================================================
# RHYTHM/PACE SPECIFICS
# ============================================================================

RHYTHM_PACE = {
    # Speeds
    "achingly_slow": ["achingly slow", "torture", "deliberate"],
    "steady_rhythm": ["steady", "consistent", "rhythm"],
    "building_speed": ["building", "faster", "accelerating"],
    "frantic_pace": ["frantic", "desperate", "urgent", "wild"],
    "punishing_pace": ["punishing", "relentless", "brutal"],

    # Patterns
    "deep_and_slow": ["deep and slow", "grinding", "savoring"],
    "shallow_and_fast": ["shallow fast", "teasing", "tip"],
    "unpredictable": ["unpredictable", "varied", "couldn't anticipate"],
    "matching_rhythm": ["matched rhythm", "in sync", "together"],

    # Pauses
    "pause_to_savor": ["paused", "savored", "moment"],
    "pause_to_tease": ["stopped", "teasing", "made wait"],
    "pause_edge": ["stopped at edge", "denied", "cruel"],
    "pause_adjustment": ["adjusting", "repositioning", "better angle"],

    # Breathing rhythm
    "rhythm_with_breath": ["matched breathing", "exhale on thrust"],
    "lost_rhythm": ["lost rhythm", "erratic", "close"],
}

# ============================================================================
# SKIN SENSATIONS
# ============================================================================

SKIN_SENSATIONS = {
    # Touch sensations
    "electricity": ["electric", "spark", "current", "tingling"],
    "burning_skin": ["burning", "fire", "heat spreading"],
    "cooling_skin": ["cooling", "goosebumps", "shiver"],
    "numb_sensation": ["numb", "can't feel", "overwhelmed"],

    # Texture sensations
    "friction": ["friction", "drag", "resistance"],
    "slickness": ["slick", "smooth", "gliding"],
    "roughness": ["rough", "scratching", "stubble burn"],
    "softness": ["soft", "gentle", "featherlight"],

    # Pressure sensations
    "light_pressure": ["light pressure", "barely there", "teasing"],
    "firm_pressure": ["firm", "pressing", "solid"],
    "crushing_pressure": ["crushing", "heavy", "weight"],
    "throbbing": ["throbbing", "pulsing", "beating"],

    # Pain sensations
    "sharp_sting": ["sharp sting", "slap", "impact"],
    "dull_ache": ["dull ache", "deep", "lasting"],
    "burn_pain": ["burning pain", "fire", "intense"],
    "pleasurable_pain": ["hurt good", "wanted more", "craved"],
}

# ============================================================================
# MUSCLE MOVEMENTS/REACTIONS
# ============================================================================

MUSCLE_MOVEMENTS = {
    # Involuntary
    "clenching": ["clenched", "tightened", "squeezed around"],
    "spasming": ["spasmed", "involuntary", "couldn't control"],
    "twitching": ["twitched", "jerked", "jumped"],
    "trembling_muscles": ["trembling", "shaking", "quivering"],
    "relaxing_muscles": ["relaxed", "went limp", "loose"],

    # Voluntary
    "flexing": ["flexed", "showed off", "posed"],
    "gripping": ["gripped", "grabbed", "held tight"],
    "pushing_back": ["pushed back", "met thrust", "rocked"],
    "pulling_closer": ["pulled closer", "held", "wouldn't let go"],

    # Specific muscles
    "abs_clenching": ["abs clenched", "stomach tightened", "core engaged"],
    "thighs_squeezing": ["thighs squeezed", "legs clamped", "held"],
    "ass_clenching": ["ass clenched", "tightened around", "squeezed"],
    "jaw_tightening": ["jaw tightened", "teeth clenched", "grinding"],
}

# ============================================================================
# SWEAT/PERSPIRATION
# ============================================================================

SWEAT_SPECIFIC = {
    # Locations
    "forehead_sweat": ["sweat on forehead", "brow", "dripping"],
    "chest_sweat": ["chest glistening", "pecs sweaty", "drops"],
    "back_sweat": ["back sweating", "spine", "sheet underneath"],
    "full_body_sweat": ["drenched", "soaked", "everywhere"],

    # Amounts
    "light_sheen": ["light sheen", "glistening", "dewy"],
    "moderate_sweat": ["sweating", "damp", "visible"],
    "heavy_sweat": ["dripping", "pouring", "soaked"],

    # Reactions to sweat
    "licking_sweat": ["licked sweat", "tasted salt", "tongue on skin"],
    "slippery_from_sweat": ["slippery", "couldn't grip", "sliding"],
    "smell_of_sweat": ["smelled sweat", "musk", "arousing"],
    "turned_on_by_sweat": ["loved the sweat", "dirty", "working hard"],
}

# ============================================================================
# LIPS/MOUTH SPECIFICS
# ============================================================================

LIPS_MOUTH = {
    # Lip descriptions
    "full_lips": ["full lips", "plump", "kissable"],
    "thin_lips": ["thin lips", "firm", "pressed"],
    "chapped_lips": ["chapped", "dry", "rough"],
    "wet_lips": ["wet lips", "licked", "glistening"],

    # Mouth actions
    "biting_own_lip": ["bit his lip", "teeth on lip", "holding back"],
    "licking_lips": ["licked lips", "tongue darted", "wet"],
    "parted_lips": ["parted", "open", "waiting"],
    "lips_on_skin": ["lips on skin", "kissed", "trailed"],

    # Inside mouth
    "tongue_action": ["tongue", "licked", "traced", "explored"],
    "teeth_grazing": ["teeth grazed", "nibbled", "bit gently"],
    "sucking_action": ["sucked", "drew in", "pressure"],
    "mouth_full": ["mouth full", "couldn't speak", "stuffed"],
}

# ============================================================================
# NECK/THROAT SPECIFICS
# ============================================================================

NECK_THROAT = {
    # Neck actions
    "neck_kissing_detailed": ["kissed neck", "below ear", "sensitive spot"],
    "neck_biting": ["bit neck", "marked", "hickey forming"],
    "neck_licking": ["licked neck", "traced", "tasted pulse"],
    "hand_on_throat": ["hand on throat", "not squeezing", "possessive"],

    # Throat focus
    "throat_exposed": ["exposed throat", "head back", "vulnerable"],
    "throat_visible": ["watched throat", "swallowing", "adam's apple"],
    "choking_throat": ["choked", "squeezed throat", "controlled breathing"],

    # Reactions
    "pulse_racing": ["felt pulse", "racing", "heartbeat in throat"],
    "swallowing_nervously": ["swallowed nervously", "throat worked"],
    "moaning_throat": ["moan from throat", "deep sound", "vibration"],
}

# ============================================================================
# BACK SPECIFICS
# ============================================================================

BACK_SPECIFICS = {
    # Back descriptions
    "broad_back": ["broad back", "wide", "muscular"],
    "narrow_back": ["narrow back", "slim", "lean"],
    "scarred_back": ["scars on back", "marks", "history"],
    "tattoo_back": ["back tattoo", "artwork", "covered"],

    # Back actions
    "scratching_back": ["scratched back", "nails", "marks left"],
    "kissing_spine": ["kissed spine", "down vertebrae", "traced"],
    "hands_on_back": ["hands on back", "pulling close", "supporting"],
    "arching_back": ["arched back", "curved", "pressing up"],

    # Back positions
    "back_against_wall": ["back against wall", "pinned", "pressed"],
    "back_on_bed": ["on his back", "looking up", "spread"],
    "back_to_chest": ["back to chest", "spooning position", "wrapped around"],
}

# ============================================================================
# LEG/THIGH SPECIFICS
# ============================================================================

LEG_THIGH = {
    # Thigh descriptions
    "thick_thighs": ["thick thighs", "muscular", "powerful"],
    "lean_thighs": ["lean thighs", "slim", "defined"],
    "hairy_thighs": ["hairy thighs", "fur", "masculine"],
    "smooth_thighs": ["smooth thighs", "hairless", "soft"],

    # Thigh actions
    "thighs_spreading": ["spread thighs", "opened", "inviting"],
    "thighs_squeezing": ["squeezed thighs", "trapped", "held between"],
    "thigh_kissing": ["kissed thighs", "inner thigh", "sensitive"],
    "thigh_biting": ["bit thigh", "marked", "teased"],

    # Leg positions
    "legs_wrapped": ["legs wrapped around", "holding", "pulling in"],
    "legs_over_shoulders": ["legs over shoulders", "deep angle", "folded"],
    "legs_spread_wide": ["legs spread wide", "exposed", "open"],
    "one_leg_up": ["one leg up", "angled", "deeper"],
}

# ============================================================================
# SUBMISSION INDICATORS
# ============================================================================

SUBMISSION_INDICATORS = {
    # Physical submission
    "kneeling_submission": ["knelt", "on knees", "looked up"],
    "head_bowed": ["head bowed", "eyes down", "submissive posture"],
    "presenting": ["presented", "offered", "displayed for"],
    "going_limp": ["went limp", "stopped fighting", "gave in"],

    # Verbal submission
    "saying_yes_sir": ["yes sir", "yes daddy", "yes master"],
    "begging_submission": ["begged", "please", "need"],
    "thanking": ["thank you", "grateful", "appreciated"],
    "asking_permission": ["may I", "can I please", "permission to"],

    # Mental submission
    "surrendering": ["surrendered", "let go", "gave control"],
    "trusting_completely": ["trusted", "completely", "blind faith"],
    "focused_only_on": ["only thought of", "whole world was", "nothing else"],
    "subspace_submission": ["floated", "gone", "deep space"],
}

# ============================================================================
# DOMINANCE INDICATORS
# ============================================================================

DOMINANCE_INDICATORS = {
    # Physical dominance
    "standing_over": ["stood over", "loomed", "towered"],
    "pinning_down": ["pinned", "held down", "couldn't move"],
    "controlling_movement": ["controlled", "positioned", "moved him"],
    "restraining": ["restrained", "held", "prevented"],

    # Verbal dominance
    "commanding_voice": ["commanded", "ordered", "told"],
    "praising_dominance": ["good boy", "well done", "earned"],
    "correcting": ["corrected", "no", "wrong", "try again"],
    "questioning_dominance": ["what do you want", "tell me", "beg"],

    # Mental dominance
    "in_control": ["in control", "owned", "had power"],
    "knowing_exactly": ["knew exactly", "could tell", "read him"],
    "deciding_everything": ["decided", "chose", "determined"],
    "topspace": ["topspace", "powerful", "godlike feeling"],
}

# ============================================================================
# SWITCHING DYNAMICS
# ============================================================================

SWITCHING_DYNAMICS = {
    # Switch initiation
    "roles_flipping": ["flipped", "switched", "traded places"],
    "surprise_switch": ["surprised by switch", "unexpected", "suddenly"],
    "negotiated_switch": ["agreed to switch", "planned", "taking turns"],

    # Transition
    "top_to_bottom": ["was topping now bottoming", "gave up control"],
    "bottom_to_top": ["was bottoming now topping", "took control"],
    "seamless_switch": ["seamless", "natural", "flowed"],
    "awkward_switch": ["awkward transition", "figuring out", "new"],

    # Both roles
    "truly_verse": ["truly vers", "enjoys both", "no preference"],
    "prefers_one": ["prefers", "usually", "more comfortable"],
    "depends_on_partner": ["depends on partner", "chemistry", "mood"],
    "both_same_scene": ["both in same scene", "back and forth", "equal"],
}

# ============================================================================
# ORGASM SPECIFICS
# ============================================================================

ORGASM_SPECIFICS = {
    # Building
    "building_slowly": ["building slowly", "mounting", "approaching"],
    "building_fast": ["building fast", "racing toward", "sudden"],
    "plateau": ["plateau", "held at edge", "sustained"],

    # Timing
    "quick_orgasm": ["came quickly", "couldn't last", "too good"],
    "delayed_orgasm": ["took time", "building forever", "finally"],
    "multiple_orgasms": ["came again", "multiple", "kept cumming"],
    "simultaneous_orgasm": ["came together", "same time", "synchronized"],

    # Intensity
    "small_orgasm": ["small orgasm", "quiet", "mild"],
    "intense_orgasm": ["intense", "overwhelming", "powerful"],
    "mind_blowing": ["mind blowing", "best ever", "transcendent"],
    "dry_orgasm_specific": ["dry orgasm", "no cum", "internal only"],

    # Physical manifestation
    "full_body_orgasm": ["full body", "everywhere", "waves"],
    "localized_orgasm": ["localized", "focused", "concentrated"],
    "prolonged_orgasm": ["prolonged", "kept going", "extended"],
}

# ============================================================================
# REFRACTORY PERIOD
# ============================================================================

REFRACTORY_PERIOD = {
    # Recovery
    "quick_recovery": ["recovered quickly", "ready again", "already hard"],
    "normal_recovery": ["needed time", "recovering", "catching breath"],
    "long_recovery": ["needed long time", "done for now", "satisfied"],

    # During recovery
    "sensitive_after": ["too sensitive", "couldn't touch", "overwhelming"],
    "cuddling_recovery": ["cuddled while", "held", "close"],
    "talking_recovery": ["talked", "pillow talk", "processing"],

    # Going again
    "round_two": ["round two", "again", "more"],
    "multiple_rounds": ["multiple rounds", "lost count", "marathon"],
    "one_and_done": ["one and done", "satisfied", "enough"],
}

# ============================================================================
# SPECIFIC SETTINGS MICRO
# ============================================================================

SETTINGS_MICRO = {
    # Bed types
    "king_bed": ["king bed", "huge", "room to move"],
    "twin_bed": ["twin bed", "small", "had to be close"],
    "floor_mattress": ["mattress on floor", "low", "easy access"],
    "no_bed": ["no bed", "floor", "anywhere"],

    # Surface textures
    "soft_sheets": ["soft sheets", "silk", "smooth"],
    "rough_surface": ["rough surface", "carpet burn", "scratchy"],
    "leather_surface": ["leather", "couch", "squeaky"],
    "cold_surface": ["cold surface", "tile", "metal"],

    # Room conditions
    "messy_room": ["messy room", "clothes everywhere", "didn't care"],
    "clean_room": ["clean room", "pristine", "organized"],
    "dark_room_setting": ["dark room", "couldn't see", "felt only"],
    "well_lit": ["well lit", "could see everything", "watched"],
}

# ============================================================================
# TIME OF DAY EFFECTS
# ============================================================================

TIME_EFFECTS = {
    # Morning specifics
    "morning_light": ["morning light", "sun through window", "golden"],
    "just_woke_up": ["just woke up", "sleepy", "warm from bed"],
    "before_coffee": ["before coffee", "barely awake", "morning haze"],

    # Afternoon specifics
    "afternoon_sun": ["afternoon sun", "lazy day", "warm light"],
    "lunch_break_quickie": ["lunch break", "had to be fast", "back to work"],
    "siesta_sex": ["siesta", "afternoon nap", "lazy"],

    # Evening specifics
    "golden_hour": ["golden hour", "sunset", "beautiful light"],
    "after_dinner": ["after dinner", "full", "relaxed"],
    "date_night": ["date night", "dressed up", "romantic"],

    # Night specifics
    "late_night": ["late night", "everyone asleep", "quiet"],
    "middle_of_night_sex": ["middle of night", "woke up", "dream led to"],
    "all_night": ["all night", "didn't sleep", "marathon"],
}

# ============================================================================
# NIPPLE PLAY SPECIFICS
# ============================================================================

NIPPLE_PLAY = {
    # Actions
    "nipple_pinch": ["pinched nipple", "twisted", "squeezed"],
    "nipple_lick": ["licked nipple", "tongue on", "flicked"],
    "nipple_suck": ["sucked nipple", "mouth on", "nursing"],
    "nipple_bite": ["bit nipple", "teeth on", "gentle bite"],
    "nipple_roll": ["rolled nipple", "between fingers", "circled"],
    "nipple_pull": ["pulled nipple", "tugged", "stretched"],

    # Toys on nipples
    "nipple_clamps_applied": ["clamp on", "clamped", "attached"],
    "nipple_suction": ["suction cups", "vacuum", "pumped"],
    "nipple_ice": ["ice on nipple", "cold", "frozen"],
    "nipple_wax": ["wax on nipple", "dripped", "hot wax"],

    # Reactions
    "nipple_hardening": ["nipple hardened", "peaked", "pebbled"],
    "nipple_sensitive": ["sensitive nipples", "couldn't take", "too much"],
    "nipple_pleasure": ["nipple pleasure", "shot through", "connected"],
    "nipple_pain_pleasure": ["hurt so good", "pain became", "crossed wires"],
}

# ============================================================================
# JEALOUSY TRIGGERS
# ============================================================================

JEALOUSY_TRIGGERS = {
    # Other people
    "ex_jealousy": ["saw ex", "mentioned ex", "compared to ex"],
    "flirting_jealousy": ["flirted with", "smiled at", "touched by"],
    "attractive_stranger": ["attractive stranger", "checked out", "eye contact"],
    "coworker_jealousy": ["work friend", "staying late", "texting coworker"],
    "friend_jealousy": ["close friend", "too close", "spending time"],

    # Attention
    "attention_elsewhere": ["paying attention", "on phone", "distracted"],
    "work_jealousy": ["always working", "prioritizes work", "never time"],
    "hobby_jealousy": ["spends time on", "obsessed with", "rather than me"],

    # Past
    "stories_about_past": ["stories about", "did with ex", "before me"],
    "comparing_to_past": ["not like", "used to", "different from"],

    # Possessive responses
    "marking_response": ["mine", "belong to me", "no one else"],
    "claiming_response": ["claiming", "showing everyone", "making sure"],
    "protective_jealousy": ["protective", "didn't like", "warning look"],
}

# ============================================================================
# TRUST BUILDING
# ============================================================================

TRUST_BUILDING = {
    # Early stages
    "initial_hesitation": ["wasn't sure", "hesitated", "cautious"],
    "testing_waters": ["testing", "seeing if", "small things"],
    "first_vulnerability": ["first time opened", "admitted", "showed"],

    # Building trust
    "consistency": ["always there", "reliable", "showed up"],
    "kept_secrets": ["kept secret", "didn't tell", "protected"],
    "followed_through": ["did what said", "followed through", "kept promise"],

    # Deepening trust
    "showing_flaws": ["showed flaws", "wasn't perfect", "real self"],
    "accepting_flaws": ["accepted flaws", "didn't judge", "still wanted"],
    "mutual_vulnerability": ["both opened", "shared equally", "reciprocated"],

    # Trust earned
    "earned_trust": ["earned trust", "proven", "could rely"],
    "implicit_trust": ["trusted completely", "without question", "knew would"],
    "trust_tested": ["trust tested", "proved worthy", "didn't break"],
}

# ============================================================================
# INTIMACY WITHOUT SEX
# ============================================================================

INTIMACY_NO_SEX = {
    # Physical closeness
    "holding_hands": ["held hands", "intertwined fingers", "hand in hand"],
    "forehead_touch": ["forehead to forehead", "touching foreheads", "leaned in"],
    "nose_nuzzle": ["nuzzled nose", "eskimo kiss", "rubbed noses"],
    "breathing_together": ["breathed together", "in sync", "same rhythm"],
    "heartbeat_listening": ["listened to heartbeat", "ear on chest", "steady rhythm"],

    # Caretaking
    "brushing_hair": ["brushed hair", "ran fingers", "played with hair"],
    "feeding_each_other": ["fed", "shared food", "bite for you"],
    "bathing_together": ["bathed together", "washed", "in tub together"],
    "bandaging_wounds": ["bandaged", "took care of", "gentle with injury"],

    # Emotional intimacy
    "sharing_silence": ["comfortable silence", "didn't need words", "just being"],
    "crying_together": ["cried together", "held while crying", "tears"],
    "laughing_together": ["laughed together", "couldn't stop", "joy"],
    "deep_conversation": ["talked all night", "shared everything", "really listened"],

    # Domestic intimacy
    "cooking_together": ["cooked together", "in kitchen", "made meal"],
    "sleeping_together_no_sex": ["just slept", "held all night", "woke together"],
    "morning_coffee": ["made coffee", "morning routine", "together"],
}

# ============================================================================
# SPECIFIC COMPLIMENTS
# ============================================================================

COMPLIMENTS_SPECIFIC = {
    # Physical compliments
    "beautiful_eyes": ["beautiful eyes", "could get lost", "eyes are"],
    "perfect_mouth": ["perfect mouth", "lips", "smile"],
    "body_appreciation": ["perfect body", "love your", "beautiful"],
    "hands_compliment": ["love your hands", "beautiful hands", "strong hands"],
    "voice_compliment": ["love your voice", "could listen", "sounds like"],

    # Character compliments
    "intelligence_compliment": ["so smart", "brilliant", "clever"],
    "kindness_compliment": ["so kind", "sweetest", "caring"],
    "strength_compliment": ["so strong", "brave", "tough"],
    "talent_compliment": ["so talented", "amazing at", "gifted"],

    # Sexual compliments
    "sexual_prowess": ["so good at", "best I've", "amazing in bed"],
    "taste_compliment": ["taste so good", "could eat", "delicious"],
    "sounds_compliment": ["love the sounds", "noises you make", "moans"],
    "response_compliment": ["love how you respond", "so responsive", "body loves"],

    # Unique compliments
    "unique_features": ["only you", "no one else has", "unique"],
    "imperfection_love": ["love that about you", "perfect imperfection", "makes you you"],
}

# ============================================================================
# INSECURITIES
# ============================================================================

INSECURITIES = {
    # Body insecurities
    "body_shame": ["ashamed of body", "covered up", "didn't want seen"],
    "size_insecurity": ["worried about size", "compared to", "not big enough"],
    "weight_insecurity": ["worried about weight", "too fat", "too skinny"],
    "scar_insecurity": ["ashamed of scars", "tried to hide", "marks"],
    "aging_insecurity": ["getting old", "not young", "wrinkles"],

    # Performance insecurities
    "performance_anxiety": ["worried wouldn't", "couldn't perform", "afraid"],
    "experience_insecurity": ["not experienced", "don't know how", "won't be good"],
    "comparison_insecurity": ["compared to others", "not as good", "better than me"],
    "lasting_insecurity": ["won't last", "too fast", "can't hold"],

    # Emotional insecurities
    "attachment_fear": ["afraid to attach", "will leave", "don't stay"],
    "not_enough": ["not enough", "deserve better", "why me"],
    "too_much": ["too much", "too needy", "pushing away"],
    "vulnerability_fear": ["afraid to show", "weakness", "will use against"],

    # Reassurance
    "needing_reassurance": ["needed to hear", "tell me", "promise"],
    "seeking_validation": ["was that okay", "did you like", "was I"],
}

# ============================================================================
# FANTASY VS REALITY
# ============================================================================

FANTASY_REALITY = {
    # Fantasy elements
    "better_than_fantasy": ["better than imagined", "exceeded fantasy", "never dreamed"],
    "fantasy_fulfilled": ["fantasy fulfilled", "dreamed of this", "always wanted"],
    "fantasy_disappointed": ["not like imagined", "different than thought", "fantasy was better"],

    # Reality intrusions
    "awkward_reality": ["awkward moment", "didn't go as planned", "real life"],
    "body_reality": ["body did", "unexpected", "bodies are"],
    "noise_reality": ["neighbors", "someone might hear", "too loud"],
    "mess_reality": ["messy", "need to clean", "sticky"],

    # Blending
    "roleplay_blend": ["pretending", "playing", "acting out"],
    "lost_in_moment": ["forgot reality", "only this", "nothing else"],
    "reality_check": ["reality check", "remembered", "came back to"],
}

# ============================================================================
# CONNECTION AND CHEMISTRY
# ============================================================================

CONNECTION_CHEMISTRY = {
    # Instant chemistry
    "instant_attraction": ["instant attraction", "moment I saw", "immediately"],
    "electric_connection": ["electric", "spark", "current between"],
    "magnetic_pull": ["magnetic", "pulled toward", "couldn't resist"],
    "undeniable_chemistry": ["undeniable chemistry", "obvious to everyone", "couldn't hide"],

    # Building connection
    "growing_connection": ["connection growing", "each time more", "deepening"],
    "emotional_connection": ["emotional connection", "more than physical", "felt it"],
    "intellectual_connection": ["mental connection", "on same page", "understood"],
    "physical_compatibility": ["bodies fit", "compatible", "made for each other"],

    # Deep connection
    "soul_connection": ["soul connection", "deeper level", "beyond physical"],
    "unspoken_understanding": ["didn't need words", "understood", "knew what"],
    "finishing_thoughts": ["finished sentences", "same thought", "thinking same"],
    "synchronization": ["in sync", "moved together", "same rhythm"],
}

# ============================================================================
# QUICKIE SPECIFICS
# ============================================================================

QUICKIE_SPECIFICS = {
    # Time pressure
    "no_time": ["no time", "have to be quick", "only minutes"],
    "might_get_caught": ["might get caught", "have to hurry", "before they"],
    "stolen_moment": ["stolen moment", "snuck away", "quick chance"],

    # Clothing
    "clothes_still_on": ["clothes still on", "didn't undress", "just enough"],
    "pulled_aside": ["pulled aside", "pushed down", "quick access"],
    "zipper_only": ["just unzipped", "fly down", "barely undressed"],

    # Location
    "quickie_location": ["bathroom", "closet", "car"],
    "against_door": ["against door", "locked door", "back to door"],
    "standing_quickie": ["standing", "against wall", "quick position"],

    # Intensity
    "desperate_quickie": ["desperate", "needed it now", "couldn't wait"],
    "efficient_quickie": ["efficient", "knew exactly", "straight to"],
    "unsatisfying_quickie": ["too quick", "wanted more", "not enough"],
    "perfect_quickie": ["perfect quickie", "exactly what needed", "satisfied"],
}

# ============================================================================
# MARATHON/EXTENDED SEX
# ============================================================================

MARATHON_SEX = {
    # Duration markers
    "hours_long": ["hours", "all day", "lost track of time"],
    "multiple_sessions": ["multiple times", "lost count", "again and again"],
    "all_night_sex": ["all night", "until morning", "sun came up"],
    "weekend_long": ["entire weekend", "didn't leave bed", "days"],

    # Stamina elements
    "breaks_between": ["took breaks", "rested", "caught breath"],
    "hydration_food": ["water break", "needed food", "energy"],
    "position_changes": ["changed positions", "tried everything", "variety"],
    "pacing_for_endurance": ["paced ourselves", "didn't rush", "made it last"],

    # Physical effects
    "exhaustion_pleasure": ["exhausted but", "couldn't stop", "too good"],
    "soreness_building": ["getting sore", "feeling it", "aching"],
    "sensitivity_changes": ["oversensitive", "different after each", "changed"],
    "multiple_orgasms": ["multiple orgasms", "lost count", "kept coming"],

    # Emotional journey
    "emotional_marathon": ["emotional journey", "through everything", "laughed and cried"],
    "deepening_connection": ["felt closer", "more connected", "bonding"],
    "comfortable_together": ["comfortable", "no shame", "everything natural"],
}

# ============================================================================
# SPECIFIC BODY WORSHIP
# ============================================================================

WORSHIP_SPECIFIC = {
    # Face worship
    "eye_worship": ["beautiful eyes", "stared into", "could look forever"],
    "lip_worship": ["perfect lips", "traced", "memorized"],
    "jaw_worship": ["jawline", "traced jaw", "sharp angles"],
    "ear_worship": ["beautiful ears", "traced", "whispered into"],

    # Upper body worship
    "shoulder_worship": ["broad shoulders", "kissed shoulder", "traced"],
    "collarbone_worship": ["collarbone", "traced hollow", "kissed"],
    "chest_worship": ["chest", "mapped with hands", "worshipped"],
    "stomach_worship": ["stomach", "traced muscles", "kissed trail"],

    # Arm worship
    "bicep_worship": ["biceps", "squeezed", "felt strength"],
    "forearm_worship": ["forearms", "veins", "strong"],
    "wrist_worship": ["wrists", "delicate", "pulse point"],
    "hand_worship": ["hands", "kissed palms", "each finger"],

    # Lower body worship
    "hip_worship": ["hips", "hip bones", "traced"],
    "thigh_worship_detailed": ["thighs", "between", "kissed inner"],
    "calf_worship": ["calves", "muscular", "traced"],
    "foot_worship_detailed": ["feet", "massaged", "kissed arch"],

    # Back worship
    "spine_worship": ["spine", "traced vertebrae", "kissed down"],
    "shoulder_blade_worship": ["shoulder blades", "kissed between", "wings"],
    "lower_back_worship": ["lower back", "dimples", "curve"],
    "ass_worship": ["perfect ass", "grabbed", "squeezed"],
}

# ============================================================================
# UNEXPECTED MOMENTS
# ============================================================================

UNEXPECTED_MOMENTS = {
    # Surprising discoveries
    "hidden_sensitive_spot": ["didn't know", "discovered spot", "surprised"],
    "unexpected_kink": ["didn't expect", "surprised themselves", "hidden kink"],
    "unexpected_intensity": ["more intense than", "didn't expect to feel", "overwhelming"],
    "unexpected_emotion": ["didn't expect", "suddenly emotional", "caught off guard"],

    # Awkward moments
    "body_sounds": ["bodies made sound", "squelch", "embarrassing sound"],
    "falling_off_bed": ["fell off bed", "rolled off", "hit floor"],
    "cramp_interrupt": ["got a cramp", "charlie horse", "had to stop"],
    "pet_interrupt": ["pet jumped on", "cat walked in", "dog barking"],

    # Funny moments
    "laughing_during": ["laughed during", "couldn't stop", "funny moment"],
    "failed_position": ["position didn't work", "tried and failed", "not flexible"],
    "wrong_hole": ["wrong hole", "accident", "oops"],
    "timing_off": ["timing off", "missed", "wrong rhythm"],

    # Turning points
    "moment_everything_changed": ["moment changed", "shifted", "different after"],
    "crossing_line": ["crossed a line", "no going back", "changed everything"],
    "revelation_during": ["realized during", "understood", "clarity"],
}

# ============================================================================
# ADDICTION/OBSESSION ELEMENTS
# ============================================================================

ADDICTION_OBSESSION = {
    # Craving
    "constant_craving": ["constant craving", "always wanted", "never enough"],
    "withdrawal_feeling": ["withdrawal", "needed fix", "couldn't function"],
    "thinking_about_constantly": ["couldn't stop thinking", "always on mind", "obsessed"],
    "counting_until": ["counting until", "couldn't wait", "impatient"],

    # Obsessive behavior
    "checking_phone": ["checking phone", "waiting for text", "hoping"],
    "stalking_social": ["checked social media", "looked at pictures", "watched stories"],
    "driving_by": ["drove by", "hoping to see", "just in case"],
    "memorizing_details": ["memorized everything", "every detail", "couldn't forget"],

    # Intensity
    "all_consuming": ["all consuming", "nothing else mattered", "only this"],
    "losing_self": ["losing self", "forgot who", "only existed for"],
    "dangerous_obsession": ["dangerous", "knew it was", "couldn't stop"],

    # Recognition
    "recognizing_problem": ["knew it was problem", "unhealthy", "should stop"],
    "trying_to_stop": ["tried to stop", "couldn't", "kept going back"],
    "accepting_addiction": ["accepted", "gave in", "stopped fighting"],
}

# ============================================================================
# HIDDEN DESIRE REVELATION
# ============================================================================

HIDDEN_DESIRES = {
    # Admitting desires
    "finally_admitting": ["finally admitted", "confessed", "told truth"],
    "scared_to_say": ["scared to say", "afraid of reaction", "nervous"],
    "blurted_out": ["blurted out", "slipped out", "accidentally revealed"],
    "written_down": ["wrote down", "texted", "couldn't say out loud"],

    # Partner's response
    "positive_response": ["wanted it too", "excited", "let's try"],
    "surprised_response": ["surprised but", "didn't expect", "interesting"],
    "enthusiastic_response": ["enthusiastic", "always wanted", "finally"],
    "hesitant_response": ["hesitant", "not sure", "need to think"],

    # Acting on desires
    "first_time_trying": ["first time trying", "finally did", "actually happened"],
    "better_than_expected": ["better than thought", "exceeded expectations", "amazing"],
    "not_what_expected": ["not what expected", "different than thought", "disappointing"],
    "want_to_do_again": ["want again", "definitely again", "loved it"],

    # Aftereffects
    "no_regrets": ["no regrets", "glad did it", "worth it"],
    "some_regrets": ["some regrets", "not sure", "complicated"],
    "changed_relationship": ["changed relationship", "different now", "new level"],
}

# ============================================================================
# SPECIFIC TEXTURES DURING SEX
# ============================================================================

TEXTURES_DURING = {
    # Skin textures
    "smooth_skin": ["smooth skin", "soft", "silky"],
    "rough_skin": ["rough skin", "calloused", "worked hands"],
    "hairy_texture": ["hairy", "chest hair", "rough with hair"],
    "stubble_texture": ["stubble", "rough beard", "scratchy"],

    # Internal textures
    "tight_feeling": ["tight", "gripping", "squeezing"],
    "wet_texture": ["wet", "slick", "dripping"],
    "ridged_feeling": ["ridges", "textured", "felt every"],
    "smooth_inside": ["smooth inside", "velvet", "soft walls"],

    # External textures
    "sheet_texture": ["sheets", "fabric", "cotton"],
    "leather_feel": ["leather", "against skin", "cool then warm"],
    "rope_texture": ["rope", "rough", "fibers"],
    "latex_feel": ["latex", "rubber", "condom"],

    # Temperature textures
    "warm_body": ["warm body", "heat", "body heat"],
    "cool_touch": ["cool touch", "cold hands", "contrast"],
    "hot_breath_texture": ["hot breath", "warmth", "against skin"],
}

# ============================================================================
# SEX MOOD TYPES
# ============================================================================

ANGRY_SEX = {
    # Triggers
    "fight_triggered": ["after fight", "still angry", "hadn't resolved"],
    "jealousy_triggered": ["jealous", "saw with", "prove"],
    "frustration_triggered": ["frustrated", "pent up", "needed release"],

    # Characteristics
    "rough_from_anger": ["rough", "harder than usual", "taking out"],
    "biting_angry": ["bit", "teeth", "marked"],
    "hair_pulling_angry": ["pulled hair", "grabbed", "yanked"],
    "pinning_angry": ["pinned down", "held against", "trapped"],

    # Emotions during
    "anger_becoming_passion": ["anger became", "transformed", "channeled"],
    "still_angry_during": ["still angry", "furious", "rage"],
    "mixed_emotions": ["didn't know if", "confused", "angry and aroused"],

    # Aftermath
    "anger_resolved": ["not angry anymore", "released", "forgiven"],
    "still_unresolved": ["still need to talk", "didn't fix", "temporary"],
    "regret_after_angry": ["regretted", "shouldn't have", "too rough"],
}

TENDER_SEX = {
    # Characteristics
    "gentle_touches": ["gentle", "soft touches", "careful"],
    "slow_pace": ["slow", "taking time", "no rush"],
    "lots_of_kissing": ["kissing", "couldn't stop", "lips"],
    "eye_contact_tender": ["looking into eyes", "watching", "seeing"],

    # Emotional elements
    "love_expressed": ["love you", "I love", "so much"],
    "vulnerability_shown": ["vulnerable", "open", "showed"],
    "tears_of_emotion": ["tears", "emotional", "overwhelmed"],
    "gratitude_expressed": ["grateful", "thank you", "lucky"],

    # Physical elements
    "intertwined": ["intertwined", "tangled", "wrapped"],
    "face_touching": ["touched face", "cupped cheek", "traced"],
    "forehead_kisses": ["kissed forehead", "gentle kiss", "sweet"],
    "whispered_words": ["whispered", "soft words", "quiet"],
}

ROUGH_SEX = {
    # Intensity markers
    "hard_thrusts": ["hard", "pounding", "rough thrusts"],
    "aggressive_pace": ["fast", "aggressive", "relentless"],
    "bruising_grip": ["bruising grip", "tight", "will leave marks"],
    "throwing_around": ["threw", "pushed", "manhandled"],

    # Verbal elements
    "dirty_talk_rough": ["filthy words", "degrading", "crude"],
    "demands_rough": ["demanded", "ordered", "told to"],
    "growling_rough": ["growled", "snarled", "grunted"],

    # Physical markers
    "against_wall_rough": ["slammed against", "against wall", "trapped"],
    "bent_over_rough": ["bent over", "pushed down", "face down"],
    "held_down_rough": ["held down", "pinned", "couldn't move"],

    # Aftermath rough
    "marks_left_rough": ["marks", "bruises", "sore"],
    "satisfied_rough": ["exactly what needed", "perfect", "satisfied"],
}

LAZY_SEX = {
    # Setting
    "morning_lazy": ["lazy morning", "just woke", "still sleepy"],
    "sunday_lazy": ["sunday", "nowhere to be", "whole day"],
    "post_nap": ["after nap", "drowsy", "warm"],

    # Pace
    "slow_movements": ["slow", "languid", "unhurried"],
    "minimal_effort": ["minimal effort", "easy", "natural"],
    "comfortable_position": ["comfortable", "didn't move much", "stayed"],

    # Mood
    "content_lazy": ["content", "happy", "satisfied"],
    "no_pressure": ["no pressure", "no goal", "just feeling"],
    "half_asleep": ["half asleep", "dozing", "drifting"],

    # Characteristics
    "spooning_sex": ["spooning", "behind", "held close"],
    "barely_moving": ["barely moving", "rocking", "gentle"],
    "quiet_lazy": ["quiet", "soft sounds", "peaceful"],
}

DESPERATE_SEX = {
    # Triggers
    "long_time_apart": ["so long", "missed", "needed"],
    "almost_lost": ["almost lost", "close call", "grateful alive"],
    "overwhelming_want": ["needed so bad", "couldn't wait", "desperate"],

    # Characteristics
    "cant_get_close_enough": ["closer", "not close enough", "need more"],
    "tearing_clothes": ["tore clothes", "ripped", "couldn't wait"],
    "multiple_times_desperate": ["again", "more", "not enough"],
    "crying_from_need": ["crying", "overwhelmed", "too much"],

    # Verbal
    "begging_desperate": ["please", "need you", "begging"],
    "possessive_desperate": ["mine", "only mine", "never leave"],
    "declarations_desperate": ["love you", "need you", "can't live without"],

    # Physical
    "clinging_desperate": ["clinging", "holding tight", "wouldn't let go"],
    "frantic_pace": ["frantic", "urgent", "couldn't slow"],
}

MAKEUP_SEX = {
    # Context
    "after_argument": ["after argument", "fight", "disagreement"],
    "apology_sex": ["sorry", "apologizing", "making up"],
    "forgiveness_shown": ["forgive", "forgiven", "let go"],

    # Emotions
    "relief_makeup": ["relief", "glad it's over", "missed you"],
    "residual_tension": ["still tense", "residual", "working through"],
    "love_reaffirmed": ["still love", "always love", "nothing changes"],

    # Characteristics
    "tender_after_fight": ["gentle now", "tender", "careful"],
    "passionate_reunion": ["passionate", "intense", "needed this"],
    "talking_during": ["talked while", "working through", "communicating"],
}

CELEBRATORY_SEX = {
    # Occasions
    "promotion_celebration": ["got promotion", "celebrating success", "good news"],
    "anniversary_sex": ["anniversary", "years together", "celebrating us"],
    "birthday_sex": ["birthday", "special day", "your day"],
    "achievement_celebration": ["achieved", "accomplished", "made it"],

    # Mood
    "happy_sex": ["happy", "joyful", "elated"],
    "playful_celebration": ["playful", "fun", "light"],
    "grateful_celebration": ["grateful", "lucky", "thankful"],

    # Elements
    "champagne_involved": ["champagne", "wine", "toasting"],
    "special_location": ["special place", "nice hotel", "somewhere new"],
    "dressed_up_before": ["dressed up", "looked amazing", "couldn't wait"],
}

COMFORT_SEX = {
    # Triggers
    "bad_day_comfort": ["bad day", "rough day", "needed comfort"],
    "grief_comfort": ["grieving", "lost someone", "sad"],
    "anxiety_comfort": ["anxious", "worried", "stressed"],
    "nightmare_comfort": ["nightmare", "bad dream", "woke up scared"],

    # Approach
    "gentle_approach": ["gentle", "careful", "slow"],
    "holding_comfort": ["held", "safe", "protected"],
    "reassuring_words": ["it's okay", "I'm here", "safe now"],

    # Purpose
    "distraction_comfort": ["distract", "forget", "focus on this"],
    "connection_comfort": ["need to feel", "connected", "not alone"],
    "grounding_comfort": ["grounding", "present", "here now"],
}

GOODBYE_SEX = {
    # Context
    "leaving_temporarily": ["leaving", "going away", "trip"],
    "deployment_goodbye": ["deployment", "military", "months away"],
    "moving_away": ["moving", "different city", "long distance"],
    "breakup_goodbye": ["last time", "ending", "goodbye"],

    # Emotions
    "sadness_goodbye": ["sad", "don't want to go", "miss you already"],
    "memorizing_goodbye": ["memorizing", "remember this", "every detail"],
    "denial_goodbye": ["pretending", "not thinking about", "just this moment"],

    # Intensity
    "prolonged_goodbye": ["took time", "drew out", "didn't want to end"],
    "desperate_goodbye": ["desperate", "holding on", "one more time"],
    "bittersweet_goodbye": ["bittersweet", "happy and sad", "mixed"],
}

# ============================================================================
# AROUSAL STAGES
# ============================================================================

AROUSAL_STAGES = {
    # Initial arousal
    "first_spark": ["first felt", "spark", "beginning"],
    "growing_interest": ["growing", "building", "interested"],
    "fully_aroused": ["fully hard", "completely aroused", "ready"],

    # Physical signs
    "blood_rushing": ["blood rushing", "heat pooling", "warm"],
    "hardening": ["getting hard", "hardening", "stiffening"],
    "leaking": ["leaking", "precum", "wet"],
    "throbbing": ["throbbing", "pulsing", "aching"],

    # Mental arousal
    "thoughts_racing": ["thoughts racing", "imagining", "fantasizing"],
    "focused_on_partner": ["focused on", "couldn't look away", "captivated"],
    "losing_rational_thought": ["couldn't think", "brain fog", "only want"],

    # Plateau
    "sustained_arousal": ["staying hard", "maintained", "plateau"],
    "edge_of_orgasm": ["close", "almost", "right there"],
    "backing_off": ["backing off", "calming", "not yet"],
}

# ============================================================================
# ORGASM TYPES DETAILED
# ============================================================================

ORGASM_TYPES = {
    # Intensity
    "small_orgasm": ["small orgasm", "little one", "mini"],
    "powerful_orgasm": ["powerful", "intense", "overwhelming"],
    "full_body_orgasm": ["full body", "everywhere", "whole body"],
    "ruined_orgasm": ["ruined", "not complete", "stopped"],

    # Type
    "prostate_orgasm": ["prostate orgasm", "hands-free", "from inside"],
    "dry_orgasm": ["dry orgasm", "nothing came out", "still felt"],
    "multiple_orgasm": ["multiple", "one after another", "kept coming"],
    "simultaneous_orgasm": ["same time", "together", "simultaneous"],

    # Build-up
    "sudden_orgasm": ["sudden", "surprised", "unexpected"],
    "slow_build_orgasm": ["built slowly", "gradual", "crept up"],
    "denied_then_released": ["finally allowed", "denied then", "permission"],

    # Aftermath
    "satisfying_orgasm": ["satisfying", "complete", "perfect"],
    "unsatisfying_orgasm": ["not enough", "wanted more", "incomplete"],
    "overwhelming_orgasm": ["too much", "overwhelming", "couldn't handle"],
}

# ============================================================================
# SUBSPACE/HEADSPACE
# ============================================================================

SUBSPACE_ELEMENTS = {
    # Entering
    "approaching_subspace": ["getting floaty", "starting to drift", "slipping"],
    "deep_in_subspace": ["deep in", "completely gone", "floating"],
    "fighting_subspace": ["fighting it", "trying to stay", "resisting"],

    # Characteristics
    "floaty_feeling": ["floaty", "weightless", "drifting"],
    "disconnected": ["disconnected", "far away", "removed"],
    "hyperfocused": ["hyperfocused", "only this", "nothing else"],
    "time_distortion": ["time stopped", "hours felt like", "lost time"],

    # Communication
    "nonverbal_subspace": ["couldn't speak", "only sounds", "words gone"],
    "simple_responses": ["yes sir", "please", "only simple"],
    "checking_in_sub": ["checking in", "color", "you okay"],

    # Coming out
    "coming_back": ["coming back", "returning", "surfacing"],
    "needing_time": ["needed time", "slowly", "gradually"],
    "aftercare_needed": ["needed aftercare", "held", "grounded"],
}

DOMSPACE_ELEMENTS = {
    # Entering
    "entering_domspace": ["in the zone", "focused", "in control"],
    "deep_domspace": ["completely focused", "powerful", "commanding"],

    # Characteristics
    "heightened_awareness": ["aware of everything", "watching", "noticing"],
    "protective_feeling": ["protective", "responsible", "caring for"],
    "power_feeling": ["powerful", "in charge", "control"],
    "calm_control": ["calm", "steady", "centered"],

    # Responsibilities
    "watching_carefully": ["watching carefully", "monitoring", "checking"],
    "reading_partner": ["reading", "understanding", "knowing"],
    "decision_making": ["deciding", "choosing", "directing"],

    # Aftercare for dom
    "dom_drop_possibility": ["might drop", "later feel", "processing"],
    "need_for_feedback": ["need to know", "was it good", "did I"],
    "pride_in_scene": ["proud", "good scene", "took care"],
}

# ============================================================================
# VOICE CHANGES DURING SEX
# ============================================================================

VOICE_CHANGES = {
    # Pitch changes
    "voice_deepening": ["voice deepened", "lower", "rougher"],
    "voice_higher": ["voice higher", "whiny", "needy"],
    "voice_breaking": ["voice breaking", "cracked", "unsteady"],

    # Volume changes
    "getting_louder": ["getting louder", "couldn't stay quiet", "volume"],
    "whisper_to_scream": ["whisper to scream", "built up", "crescendo"],
    "suddenly_quiet": ["suddenly quiet", "silent", "breath caught"],

    # Quality changes
    "raspy_voice": ["raspy", "hoarse", "rough"],
    "breathless_voice": ["breathless", "panting", "gasping"],
    "strained_voice": ["strained", "tight", "controlled"],

    # Specific sounds
    "keening": ["keening", "high sound", "whine"],
    "growling_voice": ["growling", "rumbling", "deep sound"],
    "whimpering_voice": ["whimpering", "small sounds", "needy noises"],
}

# ============================================================================
# FACIAL EXPRESSIONS SPECIFIC
# ============================================================================

FACIAL_EXPRESSIONS = {
    # Eyes
    "eyes_rolling_back": ["eyes rolled back", "whites showing", "gone"],
    "eyes_squeezed_shut": ["eyes squeezed", "tight shut", "couldn't keep open"],
    "eyes_wide": ["eyes wide", "shocked expression", "overwhelmed look"],
    "heavy_lidded": ["heavy lidded", "half closed", "drowsy look"],
    "crying_face": ["tears streaming", "crying face", "wet cheeks"],

    # Mouth
    "mouth_open": ["mouth open", "slack", "hanging open"],
    "biting_lip_expression": ["biting lip", "teeth in lip", "holding back"],
    "tongue_out": ["tongue out", "licking lips", "panting"],
    "silent_scream": ["silent scream", "mouth open no sound", "breathless"],

    # Overall
    "pleasure_face": ["pleasure face", "blissed out", "lost in it"],
    "concentration_face": ["concentrated", "focused face", "determined"],
    "pained_pleasure_face": ["pained pleasure", "hurt so good", "conflicted"],
    "vulnerable_expression": ["vulnerable", "open", "unguarded"],
    "flushed_face": ["flushed", "red face", "heated cheeks"],
}

# ============================================================================
# HIP MOVEMENTS DETAILED
# ============================================================================

HIP_MOVEMENTS = {
    # Thrusting
    "shallow_thrusts": ["shallow", "just the tip", "teasing thrusts"],
    "deep_thrusts": ["deep", "all the way", "buried"],
    "angled_thrusts": ["angled", "hitting spot", "aimed"],
    "circular_motion": ["circular", "grinding", "rotating"],

    # Rhythm
    "steady_rhythm": ["steady rhythm", "consistent", "metronome"],
    "erratic_rhythm": ["erratic", "losing rhythm", "uncontrolled"],
    "building_rhythm": ["building", "faster", "increasing"],
    "stopping_starting": ["stop and start", "pausing", "teasing"],

    # Receiving
    "pushing_back": ["pushing back", "meeting thrusts", "grinding back"],
    "pulling_in": ["pulling in", "legs wrapped", "deeper"],
    "tilting_hips": ["tilted hips", "angling", "better angle"],

    # Involuntary
    "involuntary_thrust": ["involuntary", "couldn't help", "body moved"],
    "bucking_hips": ["bucking", "jerking", "spasming"],
    "frozen_hips": ["frozen", "couldn't move", "overwhelmed"],
}

# ============================================================================
# HAND PLACEMENT DETAILED
# ============================================================================

HAND_PLACEMENT = {
    # On partner's body
    "hands_in_hair": ["hands in hair", "gripping hair", "fingers tangled"],
    "hands_on_hips": ["hands on hips", "gripping hips", "guiding"],
    "hands_on_ass": ["hands on ass", "grabbing", "squeezing"],
    "hands_on_chest": ["hands on chest", "feeling", "pressing"],
    "hands_on_face": ["hands on face", "cupping", "holding"],
    "hands_on_throat": ["hand on throat", "around neck", "light pressure"],

    # Gripping things
    "gripping_sheets": ["gripping sheets", "fisting sheets", "tearing"],
    "gripping_headboard": ["gripping headboard", "holding on", "white knuckles"],
    "gripping_shoulders": ["gripping shoulders", "holding on", "nails in"],

    # Restrained hands
    "hands_pinned": ["hands pinned", "held down", "couldn't move"],
    "hands_tied": ["hands tied", "bound", "restrained"],
    "hands_behind_back": ["hands behind back", "held there", "clasped"],

    # Exploring
    "hands_wandering": ["hands wandering", "exploring", "touching everywhere"],
    "hands_still": ["hands still", "frozen", "gripping"],
    "hands_gentle": ["gentle hands", "soft touch", "careful"],
}

# ============================================================================
# SAFEWORD AND CONSENT CHECKING
# ============================================================================

SAFEWORD_ELEMENTS = {
    # Having safeword
    "established_safeword": ["safeword is", "remember safeword", "can always"],
    "traffic_light": ["red yellow green", "color", "what's your color"],
    "custom_safeword": ["our word", "say X", "if you need"],

    # Using safeword
    "yellow_called": ["yellow", "slow down", "need a moment"],
    "red_called": ["red", "stop", "safeword"],
    "scene_stopped": ["stopped immediately", "checked in", "held"],

    # After safeword
    "reassurance_after": ["it's okay", "proud of you", "thank you for"],
    "processing_after": ["talking about", "what happened", "understanding"],
    "continuing_after": ["ready to continue", "adjusted", "started again"],

    # Non-verbal
    "tap_out": ["tapped out", "signal", "couldn't speak"],
    "dropped_object": ["dropped", "let go of", "signal"],
}

CHECK_INS = {
    # During scene
    "verbal_check": ["you okay", "how you doing", "still good"],
    "color_check": ["what's your color", "give me a color", "color"],
    "physical_check": ["checking", "looking at", "watching for"],

    # Responses
    "enthusiastic_yes": ["yes", "so good", "don't stop"],
    "hesitant_response": ["I think", "maybe", "not sure"],
    "clear_no": ["no", "stop", "need to stop"],

    # Adjustments
    "adjusting_based": ["adjusted", "changed", "modified"],
    "checking_again": ["checking again", "making sure", "still okay"],
    "gratitude_for_check": ["thank you for checking", "appreciate", "feel safe"],
}

# ============================================================================
# BOUNDARY EXPLORATION
# ============================================================================

BOUNDARY_EXPLORATION = {
    # Pushing limits
    "approaching_limit": ["getting close to", "approaching", "near limit"],
    "at_the_edge": ["at the edge", "right at limit", "maximum"],
    "past_comfort": ["past comfort", "new territory", "never before"],

    # Response to limits
    "enjoying_push": ["enjoying", "want more", "keep going"],
    "overwhelmed_by_push": ["too much", "overwhelming", "need break"],
    "discovering_new_limit": ["new limit", "didn't know", "discovered"],

    # Communication about limits
    "expressing_limit": ["that's my limit", "can't do", "too far"],
    "respecting_limit": ["respected", "stopped", "understood"],
    "negotiating_limit": ["maybe we could", "what about", "compromise"],

    # Hard vs soft
    "hard_limit_mentioned": ["hard limit", "never", "won't do"],
    "soft_limit_mentioned": ["soft limit", "might try", "with right person"],
    "limit_becoming_interest": ["used to be limit", "now interested", "changed"],
}

# ============================================================================
# SPECIFIC KINK MICRO-DETAILS
# ============================================================================

SPANKING_DETAILED = {
    # Position
    "over_knee": ["over knee", "across lap", "OTK"],
    "bent_over_furniture": ["bent over", "over desk", "over chair"],
    "standing_spanking": ["standing", "against wall", "hands on wall"],
    "on_all_fours": ["on all fours", "hands and knees", "presenting"],

    # Implement
    "hand_spanking": ["bare hand", "palm", "hand"],
    "belt_spanking": ["belt", "leather belt", "folded belt"],
    "paddle_spanking": ["paddle", "wooden paddle", "leather paddle"],
    "hairbrush_spanking": ["hairbrush", "brush", "back of brush"],
    "cane_spanking": ["cane", "rattan", "switch"],

    # Progression
    "warmup_spanking": ["warmup", "started light", "building"],
    "building_intensity": ["getting harder", "building", "increasing"],
    "peak_intensity": ["full force", "hardest", "maximum"],

    # Reactions
    "counting_strokes": ["counting", "said the number", "count them"],
    "thanking_for_stroke": ["thank you", "thanked", "grateful"],
    "crying_from_spanking": ["started crying", "tears", "broke"],
    "skin_color_change": ["turned red", "pink", "glowing"],
}

BITING_DETAILED = {
    # Location
    "neck_bite": ["bit neck", "teeth on neck", "marked neck"],
    "shoulder_bite": ["bit shoulder", "teeth in shoulder", "shoulder mark"],
    "lip_bite": ["bit lip", "teeth on lip", "drew blood"],
    "ear_bite": ["bit ear", "teeth on earlobe", "nibbled ear"],
    "inner_thigh_bite": ["bit inner thigh", "teeth on thigh", "marked thigh"],

    # Intensity
    "gentle_nibble": ["nibbled", "gentle bite", "teasing teeth"],
    "firm_bite": ["firm bite", "felt teeth", "pressure"],
    "hard_bite": ["hard bite", "sank teeth", "marked"],
    "breaking_skin": ["broke skin", "drew blood", "deep bite"],

    # Reaction to biting
    "gasped_from_bite": ["gasped", "sharp breath", "startled"],
    "moaned_from_bite": ["moaned", "liked it", "encouraging"],
    "asking_for_more_bites": ["more", "again", "harder"],
    "bite_marks_left": ["left marks", "teeth marks", "bruise forming"],
}

SCRATCHING_DETAILED = {
    # Action
    "light_scratch": ["light scratch", "nails tracing", "dragging nails"],
    "firm_scratch": ["firm scratch", "digging in", "pressure"],
    "drawing_blood_scratch": ["drew blood", "scratched deep", "welts"],

    # Location
    "back_scratching": ["scratched back", "nails down back", "raked"],
    "shoulder_scratching": ["scratched shoulders", "nails in shoulders", "gripping"],
    "scalp_scratching": ["scratched scalp", "nails in hair", "through hair"],
    "chest_scratching": ["scratched chest", "nails on chest", "marked"],

    # Marks
    "red_lines": ["red lines", "scratch marks", "trails"],
    "raised_welts": ["welts", "raised marks", "visible"],
    "lasting_marks": ["lasted", "still there", "days later"],
}

HAIR_PULLING_DETAILED = {
    # Grip type
    "handful_grip": ["grabbed handful", "fistful", "tight grip"],
    "base_grip": ["at the base", "close to scalp", "roots"],
    "ponytail_grip": ["grabbed ponytail", "by ponytail", "held"],

    # Action
    "gentle_tug": ["gentle tug", "light pull", "teasing"],
    "firm_pull": ["firm pull", "pulled", "control"],
    "hard_yank": ["yanked", "pulled hard", "sharp"],

    # Purpose
    "guiding_head": ["guided head", "directed", "positioned"],
    "exposing_neck": ["exposed neck", "pulled back", "access"],
    "control_pull": ["control", "making look", "forcing"],

    # Reaction
    "scalp_tingling": ["scalp tingled", "sensation", "felt through"],
    "moaned_from_pull": ["moaned", "liked it", "responded"],
    "submitted_to_pull": ["submitted", "went where", "followed"],
}

# ============================================================================
# SPECIFIC PENETRATION SENSATIONS
# ============================================================================

PENETRATION_SENSATIONS = {
    # Initial entry
    "initial_stretch": ["initial stretch", "first moment", "opening"],
    "burning_entry": ["burned", "stretch burn", "accommodating"],
    "pressure_entry": ["pressure", "pushing in", "filling"],
    "pop_past_ring": ["popped past", "ring gave", "through"],

    # During
    "fullness_sensation": ["full", "filled", "stuffed"],
    "depth_sensation": ["deep", "so deep", "bottomed out"],
    "friction_sensation": ["friction", "drag", "slide"],
    "hitting_prostate": ["hit prostate", "that spot", "seeing stars"],

    # Movement sensations
    "in_and_out": ["in and out", "thrusting", "moving"],
    "grinding_inside": ["grinding", "pressing", "rotating"],
    "pulsing_inside": ["pulsing", "throbbing", "twitching"],
    "expanding_inside": ["expanding", "getting bigger", "swelling"],

    # Withdrawal
    "empty_feeling": ["empty", "missing", "void"],
    "relief_withdrawal": ["relief", "relaxing", "body releasing"],
    "wanting_back": ["wanted back", "needed again", "empty without"],
}

RECEIVING_ORAL_SENSATIONS = {
    # Mouth sensations
    "wet_heat": ["wet heat", "hot mouth", "warm and wet"],
    "suction_feeling": ["suction", "sucking", "vacuum"],
    "tongue_work": ["tongue", "licking", "swirling"],
    "back_of_throat": ["throat", "deep throat", "all the way"],

    # Specific techniques
    "head_focus": ["focused on head", "tip", "sensitive head"],
    "shaft_attention": ["along shaft", "up and down", "length"],
    "ball_attention": ["balls", "sucked balls", "licked balls"],
    "perineum_attention": ["taint", "perineum", "between"],

    # Building sensation
    "building_pleasure": ["building", "getting close", "rising"],
    "edge_of_orgasm_oral": ["so close", "almost", "right there"],
    "orgasm_in_mouth": ["came in mouth", "finished", "released"],
}

GIVING_ORAL_SENSATIONS = {
    # Physical sensations
    "taste_giving": ["tasted", "taste of", "flavor"],
    "weight_on_tongue": ["weight on tongue", "heavy", "substantial"],
    "jaw_ache": ["jaw ached", "tired jaw", "worth it"],
    "gag_reflex": ["gagged", "fought gag", "reflex"],

    # Emotional
    "pride_in_giving": ["proud", "doing well", "pleasing"],
    "submission_in_giving": ["serving", "on knees", "giving"],
    "power_in_giving": ["controlled", "made him", "power"],

    # Partner reactions
    "feeling_reactions": ["felt him react", "twitching", "responding"],
    "hearing_reactions": ["hearing moans", "sounds", "reactions"],
    "tasting_precum": ["tasted precum", "leaking", "salty"],
    "feeling_close": ["felt getting close", "swelling", "pulsing"],
}

# ============================================================================
# SPECIFIC POSITIONS DETAILED
# ============================================================================

MISSIONARY_VARIATIONS = {
    # Basic
    "standard_missionary": ["missionary", "face to face", "on top"],
    "legs_up_missionary": ["legs up", "over shoulders", "folded"],
    "wrapped_legs": ["wrapped legs", "legs around", "pulled close"],

    # Variations
    "pillow_under_hips": ["pillow under", "angled", "better access"],
    "edge_of_bed": ["edge of bed", "standing", "feet on floor"],
    "coital_alignment": ["CAT", "grinding", "clit stimulation"],

    # Intimacy elements
    "eye_contact_missionary": ["looking at each other", "watching", "seeing"],
    "kissing_during_missionary": ["kissing while", "mouths", "close enough"],
    "foreheads_touching": ["foreheads touching", "close", "intimate"],
}

DOGGY_VARIATIONS = {
    # Basic
    "standard_doggy": ["doggy", "from behind", "hands and knees"],
    "face_down_ass_up": ["face down", "ass up", "chest on bed"],
    "standing_doggy": ["standing doggy", "bent over", "from behind standing"],

    # Variations
    "flat_doggy": ["flat", "lying down", "prone bone"],
    "arched_back_doggy": ["arched back", "curve", "presenting"],
    "spread_cheeks": ["spread cheeks", "held open", "exposed"],

    # Control elements
    "hip_grip_doggy": ["gripping hips", "holding hips", "guiding"],
    "hair_pull_doggy": ["hair pulled", "head back", "control"],
    "reach_around": ["reached around", "touched while", "stimulated"],
}

RIDING_VARIATIONS = {
    # Basic
    "standard_cowboy": ["riding", "on top", "cowboy"],
    "reverse_cowboy": ["reverse cowboy", "facing away", "reverse"],
    "lazy_cowboy": ["lazy cowboy", "chest to chest", "lying on"],

    # Movement
    "bouncing": ["bouncing", "up and down", "riding"],
    "grinding_riding": ["grinding", "rotating", "rolling hips"],
    "controlled_riding": ["controlled", "setting pace", "in charge"],

    # Power dynamics
    "power_from_top": ["power", "in control", "using him"],
    "bottom_thrusting_up": ["thrust up", "meeting", "from below"],
    "hands_on_chest_riding": ["hands on chest", "bracing", "leverage"],
}

SIDE_POSITIONS = {
    # Spooning
    "spooning_sex": ["spooning", "from behind", "curled together"],
    "lazy_spooning": ["lazy", "slow", "morning spooning"],
    "deep_spooning": ["leg up", "deeper", "angled"],

    # Face to face
    "face_to_face_side": ["facing each other", "side by side", "intimate"],
    "leg_over_hip": ["leg over hip", "pulled close", "tangled"],

    # Scissoring
    "scissoring": ["scissoring", "legs intertwined", "grinding"],
}

# ============================================================================
# SPECIFIC LUBE/PREP ELEMENTS
# ============================================================================

LUBE_ELEMENTS = {
    # Types
    "water_based_lube": ["water based", "safe for", "easy cleanup"],
    "silicone_lube": ["silicone", "long lasting", "slick"],
    "oil_based": ["oil", "coconut oil", "natural"],
    "saliva_lube": ["spit", "saliva", "wet with mouth"],

    # Application
    "applying_lube": ["applied lube", "lubed up", "slicked"],
    "warming_lube": ["warmed", "in hands", "not cold"],
    "reapplying": ["more lube", "reapplied", "needed more"],

    # Sensations
    "cold_lube": ["cold", "shock", "warmed quickly"],
    "warming_lube_sensation": ["warming sensation", "tingling", "heated"],
    "slick_feeling": ["slick", "gliding", "no friction"],
}

PREP_ELEMENTS = {
    # Fingering prep
    "one_finger_start": ["one finger", "started with", "first finger"],
    "adding_fingers": ["added finger", "two fingers", "stretching"],
    "scissoring_fingers": ["scissoring", "spreading", "stretching"],
    "finding_prostate_prep": ["found prostate", "that spot", "there"],

    # Relaxation
    "relaxing_muscles": ["relax", "breathe", "let me in"],
    "pushing_out": ["push out", "bear down", "helps"],
    "taking_time": ["took time", "patient", "no rush"],

    # Ready signals
    "asking_for_more": ["more", "ready", "want you"],
    "begging_for_it": ["please", "need you", "now"],
    "physically_ready": ["open", "relaxed", "ready"],
}

# ============================================================================
# CLOTHING DURING SEX
# ============================================================================

CLOTHING_DURING = {
    # Partially clothed
    "shirt_still_on": ["shirt on", "didn't take off", "still wearing"],
    "pants_around_ankles": ["pants down", "around ankles", "just enough"],
    "underwear_pulled_aside": ["pulled aside", "moved underwear", "didn't remove"],
    "skirt_hiked_up": ["hiked up", "pushed up", "bunched"],

    # Specific items
    "jockstrap_on": ["jockstrap", "ass exposed", "framed"],
    "harness_only": ["only harness", "straps", "leather"],
    "socks_still_on": ["socks on", "only socks", "forgot"],
    "tie_used": ["tie", "pulled by tie", "like a leash"],

    # Undressing during
    "undressing_each_other": ["undressed each other", "stripped", "removing"],
    "tearing_off": ["tore off", "ripped", "couldn't wait"],
    "slow_reveal": ["slowly", "revealing", "teasing"],

    # Dressed after
    "getting_dressed_after": ["got dressed", "putting on", "back to normal"],
    "disheveled_after": ["disheveled", "wrinkled", "obvious"],
}

# ============================================================================
# CONDOM ELEMENTS
# ============================================================================

CONDOM_ELEMENTS = {
    # Getting condom
    "reaching_for_condom": ["reached for condom", "grabbed", "nightstand"],
    "always_prepared": ["always has", "prepared", "responsible"],
    "almost_forgot": ["almost forgot", "wait", "should use"],

    # Putting on
    "rolling_on": ["rolled on", "put on", "covered"],
    "partner_puts_on": ["put it on for", "rolled onto", "helped"],
    "with_mouth": ["with mouth", "rolled on with", "skill"],

    # During
    "protected_sex": ["protected", "safe", "covered"],
    "sensation_difference": ["could still feel", "different but", "still good"],

    # After
    "removing_condom": ["removed condom", "took off", "disposed"],
    "checking_condom": ["checked", "intact", "no breaks"],

    # Bareback references
    "no_condom": ["no condom", "raw", "bare"],
    "feels_different": ["feels different", "nothing between", "skin to skin"],
    "trust_implied": ["trust", "clean", "tested"],
}

# ============================================================================
# MULTIPLE ROUNDS
# ============================================================================

MULTIPLE_ROUNDS = {
    # Between rounds
    "recovery_time": ["recovery", "resting", "catching breath"],
    "staying_connected": ["stayed inside", "didn't pull out", "connected"],
    "cuddling_between": ["cuddled", "held", "close"],
    "talking_between": ["talked", "laughed", "processed"],

    # Starting again
    "getting_hard_again": ["hard again", "recovering", "ready again"],
    "different_position": ["different position", "switched", "tried"],
    "different_activity": ["switched to", "instead", "this time"],

    # Stamina
    "impressive_stamina": ["stamina", "kept going", "didn't stop"],
    "needed_break": ["needed break", "had to rest", "too much"],
    "lost_count": ["lost count", "how many", "multiple times"],

    # Energy levels
    "still_energetic": ["still energetic", "could go again", "not tired"],
    "pleasantly_exhausted": ["exhausted", "done", "satisfied tired"],
    "completely_spent": ["spent", "couldn't move", "destroyed"],
}

# ============================================================================
# BODY HAIR ELEMENTS
# ============================================================================

BODY_HAIR_ELEMENTS = {
    # Chest hair
    "hairy_chest": ["hairy chest", "chest hair", "furry"],
    "smooth_chest": ["smooth chest", "hairless", "waxed"],
    "trail_of_hair": ["trail", "happy trail", "line of hair"],
    "running_through_hair": ["ran fingers through", "played with", "tugged"],

    # Facial hair
    "beard_sensation": ["beard", "facial hair", "scratchy"],
    "stubble_feeling": ["stubble", "rough", "five o'clock"],
    "beard_burn": ["beard burn", "red marks", "sensitive after"],

    # Other body hair
    "arm_hair": ["arm hair", "forearm", "dark hair"],
    "leg_hair": ["leg hair", "hairy legs", "rough"],
    "pubic_hair": ["pubes", "pubic hair", "trimmed"],

    # Grooming
    "freshly_shaved": ["freshly shaved", "smooth", "just shaved"],
    "growing_back": ["growing back", "stubble", "prickly"],
    "natural": ["natural", "ungroomed", "as is"],
}

# ============================================================================
# SCARS AND MARKS
# ============================================================================

SCARS_MARKS = {
    # Types of scars
    "surgical_scars": ["surgical scar", "operation", "healed incision"],
    "accident_scars": ["accident scar", "injury", "old wound"],
    "self_harm_scars": ["self harm", "old scars", "history"],
    "stretch_marks": ["stretch marks", "lines", "tiger stripes"],

    # Reactions to scars
    "self_conscious": ["self conscious", "tried to hide", "embarrassed"],
    "partner_acceptance": ["accepted", "didn't care", "kissed them"],
    "story_behind": ["story behind", "how got", "explained"],
    "part_of_them": ["part of you", "makes you you", "beautiful"],

    # Touching scars
    "tracing_scars": ["traced scar", "ran finger over", "gentle"],
    "kissing_scars": ["kissed scar", "lips on", "reverent"],
    "avoiding_scars": ["avoided", "careful around", "didn't touch"],
}

# ============================================================================
# TATTOO ELEMENTS
# ============================================================================

TATTOO_ELEMENTS = {
    # Noticing tattoos
    "discovering_tattoo": ["noticed tattoo", "saw tattoo", "didn't know"],
    "asking_about_tattoo": ["asked about", "what does it mean", "when did"],
    "tracing_tattoo": ["traced tattoo", "followed lines", "touched"],

    # Tattoo locations
    "arm_tattoo": ["arm tattoo", "sleeve", "bicep"],
    "chest_tattoo": ["chest tattoo", "over heart", "pec"],
    "back_tattoo": ["back tattoo", "across back", "spine"],
    "intimate_tattoo": ["intimate tattoo", "hidden", "only see when"],

    # Reactions
    "tattoo_attraction": ["hot tattoo", "sexy ink", "turned on by"],
    "licking_tattoo": ["licked tattoo", "tongue over", "tasted ink"],
    "matching_tattoos": ["matching", "got together", "same tattoo"],
}

# ============================================================================
# PIERCING ELEMENTS
# ============================================================================

PIERCING_ELEMENTS = {
    # Types
    "nipple_piercing": ["nipple piercing", "barbell", "ring through"],
    "genital_piercing": ["PA", "prince albert", "pierced cock"],
    "tongue_piercing": ["tongue piercing", "felt metal", "ball"],
    "ear_piercing": ["ear piercing", "earring", "tugged"],

    # Sensations
    "metal_sensation": ["felt metal", "cold metal", "different"],
    "extra_stimulation": ["extra stimulation", "hit differently", "added"],
    "careful_with_piercing": ["careful", "don't want to hurt", "gentle"],

    # Playing with
    "tugging_piercing": ["tugged piercing", "pulled", "played with"],
    "licking_piercing": ["licked piercing", "tongue on", "tasted metal"],
    "using_piercing": ["used piercing", "stimulated with", "advantage"],
}

# ============================================================================
# MEETING/HOOKUP CONTEXTS
# ============================================================================

MEETING_CONTEXTS = {
    # Apps/Online
    "grindr_hookup": ["grindr", "app", "swiped"],
    "scruff_meeting": ["scruff", "messaged", "profile"],
    "tinder_match": ["tinder", "matched", "dating app"],
    "online_meeting": ["online", "chatted first", "met online"],
    "catfish_situation": ["catfish", "not like photos", "different"],

    # Bars/Clubs
    "bar_pickup": ["bar", "bought drink", "approached"],
    "club_meeting": ["club", "dance floor", "grinding"],
    "gay_bar": ["gay bar", "queer space", "our bar"],
    "dive_bar": ["dive bar", "local", "regular"],

    # Through friends
    "friend_introduction": ["friend introduced", "set up", "through friends"],
    "friend_of_friend": ["friend of friend", "party", "knew someone"],
    "double_date_gone_right": ["double date", "switched", "ended up"],

    # Random meetings
    "coffee_shop": ["coffee shop", "cafe", "noticed"],
    "gym_meeting": ["gym", "spotted", "locker room"],
    "grocery_store": ["grocery store", "random", "reached for same"],
    "laundromat": ["laundromat", "waiting", "started talking"],
}

# ============================================================================
# FLIRTING ELEMENTS
# ============================================================================

FLIRTING_ELEMENTS = {
    # Verbal flirting
    "pickup_line": ["pickup line", "cheesy line", "does that work"],
    "compliment_flirt": ["complimented", "said nice things", "flattering"],
    "teasing_flirt": ["teasing", "playful banter", "giving hard time"],
    "innuendo": ["innuendo", "suggestive", "double meaning"],

    # Physical flirting
    "lingering_touch": ["lingering touch", "touched longer", "didn't pull away"],
    "arm_touch": ["touched arm", "hand on arm", "casual touch"],
    "leaning_in": ["leaned in", "closer", "invading space"],
    "eye_contact_flirt": ["eye contact", "couldn't look away", "held gaze"],

    # Response to flirting
    "flattered": ["flattered", "blushing", "pleased"],
    "playing_hard_to_get": ["playing hard to get", "making work", "challenge"],
    "obvious_interest": ["obvious interest", "clearly into", "not subtle"],
    "mutual_flirting": ["mutual", "back and forth", "both flirting"],
}

# ============================================================================
# FIRST KISS ELEMENTS
# ============================================================================

FIRST_KISS_ELEMENTS = {
    # Lead up
    "tension_before_kiss": ["tension", "moment", "about to"],
    "eye_drop_to_lips": ["eyes dropped to lips", "looking at mouth", "wanted to"],
    "leaning_in_kiss": ["leaned in", "moved closer", "closed distance"],
    "asking_first": ["asked first", "can I", "may I kiss"],

    # The kiss
    "soft_first_kiss": ["soft kiss", "gentle", "tentative"],
    "passionate_first_kiss": ["passionate", "intense", "immediately deep"],
    "awkward_first_kiss": ["awkward", "missed", "nose bump"],
    "perfect_first_kiss": ["perfect", "everything hoped", "fireworks"],

    # After
    "pulling_back_slowly": ["pulled back slowly", "savoring", "lingering"],
    "going_for_more": ["immediately more", "couldn't stop", "again"],
    "stunned_after": ["stunned", "couldn't believe", "that happened"],
    "smiling_after_kiss": ["smiled after", "grinning", "happy"],
}

# ============================================================================
# NERVOUSNESS ELEMENTS
# ============================================================================

NERVOUSNESS_ELEMENTS = {
    # Physical signs
    "shaking_hands": ["shaking hands", "trembling", "couldn't steady"],
    "sweaty_palms": ["sweaty palms", "clammy", "wiped hands"],
    "racing_heart_nervous": ["heart racing", "pounding", "could hear"],
    "dry_mouth": ["dry mouth", "licked lips", "swallowed"],
    "voice_shaking": ["voice shook", "couldn't speak", "stammered"],

    # Mental state
    "overthinking": ["overthinking", "too much", "spiral"],
    "second_guessing": ["second guessing", "should I", "not sure"],
    "wanting_to_flee": ["wanted to run", "almost left", "could leave"],
    "forcing_calm": ["forcing calm", "breathe", "you can do this"],

    # Partner response
    "partner_calming": ["calmed me", "it's okay", "relax"],
    "partner_patient": ["patient", "took time", "didn't rush"],
    "both_nervous": ["both nervous", "equally", "laughed about"],

    # Overcoming
    "nervousness_fading": ["nervousness faded", "relaxed into", "forgot"],
    "adrenaline_excitement": ["nervous became excited", "adrenaline", "good nervous"],
}

# ============================================================================
# EXPERIENCE LEVELS
# ============================================================================

EXPERIENCE_LEVELS = {
    # Virgin/first time
    "complete_virgin": ["virgin", "never done", "first time ever"],
    "virgin_with_men": ["first time with man", "never with guy", "women before"],
    "specific_act_first": ["never done this", "first time for", "new to"],

    # Inexperienced
    "limited_experience": ["limited experience", "only few times", "not much"],
    "nervous_inexperience": ["nervous because", "don't know what", "might mess up"],
    "eager_to_learn": ["eager to learn", "teach me", "show me"],

    # Experienced
    "very_experienced": ["experienced", "know what doing", "done this before"],
    "teaching_partner": ["teaching", "showing", "guiding"],
    "confident_experience": ["confident", "knows what wants", "skilled"],

    # Mismatch
    "experience_gap": ["more experienced", "less experienced", "different levels"],
    "intimidated_by_experience": ["intimidated", "they've done more", "compared"],
    "experience_not_matter": ["doesn't matter", "we'll figure out", "together"],
}

# ============================================================================
# SIZE DESCRIPTIONS
# ============================================================================

SIZE_DESCRIPTIONS = {
    # Length
    "average_length": ["average", "normal size", "regular"],
    "above_average_length": ["above average", "bigger than", "impressive length"],
    "very_long": ["very long", "huge", "massive length"],
    "smaller_length": ["smaller", "not big", "compact"],

    # Girth
    "thick_girth": ["thick", "girthy", "wide"],
    "average_girth": ["average thickness", "normal girth", "regular"],
    "thin_girth": ["thin", "slender", "not thick"],

    # Overall
    "perfect_fit": ["perfect fit", "just right", "made for"],
    "challenging_size": ["challenging", "had to adjust", "took time"],
    "comfortable_size": ["comfortable", "easy", "no problem"],

    # Comparisons
    "bigger_than_expected": ["bigger than expected", "surprised", "wow"],
    "smaller_than_expected": ["smaller than expected", "different than", "okay though"],
    "size_doesn't_matter": ["doesn't matter", "not about size", "how use it"],
}

# ============================================================================
# STAMINA ELEMENTS
# ============================================================================

STAMINA_ELEMENTS = {
    # Quick
    "came_fast": ["came fast", "didn't last", "too quick"],
    "premature": ["premature", "couldn't help", "sorry"],
    "embarrassed_quick": ["embarrassed", "usually last", "give me minute"],

    # Average
    "normal_duration": ["normal", "reasonable time", "good amount"],
    "satisfied_duration": ["satisfied", "enough time", "just right"],

    # Long lasting
    "lasted_long": ["lasted long", "marathon", "kept going"],
    "impressive_stamina": ["impressive stamina", "how", "amazing"],
    "too_long": ["too long", "getting tired", "can you"],

    # Control
    "holding_back": ["holding back", "trying not to", "controlling"],
    "edging_for_stamina": ["edging", "stopping", "making last"],
    "multiple_orgasms_stamina": ["multiple times", "kept going", "again"],
}

# ============================================================================
# INTERRUPTION ELEMENTS
# ============================================================================

INTERRUPTION_ELEMENTS = {
    # People interruptions
    "roommate_came_home": ["roommate came home", "heard door", "someone here"],
    "phone_rang": ["phone rang", "ignored it", "had to answer"],
    "knock_on_door": ["knock on door", "who is it", "go away"],
    "someone_walked_in": ["walked in", "caught", "saw us"],

    # Physical interruptions
    "cramp_hit": ["cramp", "leg seized", "had to stop"],
    "fell_off_bed": ["fell off", "slipped", "crashed"],
    "condom_broke": ["condom broke", "need new one", "felt different"],
    "went_soft": ["went soft", "lost it", "give me sec"],

    # Environmental
    "alarm_went_off": ["alarm", "noise", "what's that"],
    "pet_interrupted": ["cat jumped", "dog barked", "pet needs out"],
    "fire_alarm": ["fire alarm", "had to stop", "not a drill"],

    # Handling interruptions
    "ignored_interruption": ["ignored it", "kept going", "not stopping"],
    "had_to_stop": ["had to stop", "pause", "deal with"],
    "continued_after": ["continued after", "where were we", "back to"],
}

# ============================================================================
# MUSIC DURING SEX
# ============================================================================

MUSIC_DURING_SEX = {
    # Having music
    "music_playing": ["music playing", "soundtrack", "in background"],
    "playlist_for_sex": ["sex playlist", "made playlist", "perfect music"],
    "random_music": ["random music", "whatever was on", "didn't plan"],

    # Types
    "slow_music": ["slow music", "sensual", "R&B"],
    "loud_music": ["loud music", "cover sounds", "couldn't hear"],
    "no_music": ["no music", "just us", "sounds of"],

    # Effects
    "moving_to_rhythm": ["moving to rhythm", "beat", "in time"],
    "song_association": ["now whenever hear", "our song", "reminds me"],
    "awkward_song": ["awkward song", "wrong mood", "had to change"],
}

# ============================================================================
# DIRTY TALK SPECIFICS
# ============================================================================

DIRTY_TALK_SPECIFICS = {
    # Asking for it
    "begging_words": ["please", "need it", "give me"],
    "demanding_words": ["now", "harder", "more"],
    "questioning_dirty": ["you like that", "feels good", "want more"],

    # Describing
    "describing_sensations": ["feels so", "you're so", "I love how"],
    "describing_partner": ["so hot", "beautiful", "perfect"],
    "describing_acts": ["love when you", "the way you", "how you"],

    # Possessive talk
    "mine_possessive": ["mine", "belong to me", "only mine"],
    "claiming_words": ["taking", "making you", "marking"],
    "ownership_talk": ["own you", "you're my", "I own"],

    # Degradation (consensual)
    "slut_talk": ["slut", "whore", "dirty"],
    "degrading_praise": ["good little", "such a", "perfect"],
    "humiliation_words": ["pathetic", "desperate", "needy"],

    # Praise during
    "praise_during": ["so good", "perfect", "amazing"],
    "encouragement": ["just like that", "keep going", "yes"],
    "approval_words": ["good boy", "that's it", "perfect"],
}

# ============================================================================
# REACTION TO ORGASM
# ============================================================================

ORGASM_REACTIONS = {
    # Sounds
    "silent_orgasm": ["silent", "held breath", "no sound"],
    "loud_orgasm": ["loud", "screamed", "couldn't be quiet"],
    "moaning_orgasm": ["moaned", "groaned", "cried out"],
    "name_called": ["called name", "said name", "shouted name"],

    # Physical
    "body_shaking": ["body shook", "trembling", "shaking"],
    "toes_curling": ["toes curled", "feet flexed", "curling"],
    "back_arching": ["back arched", "spine curved", "lifted"],
    "grabbing_partner": ["grabbed", "held tight", "gripped"],

    # Emotional
    "emotional_orgasm": ["emotional", "tears", "overwhelmed"],
    "laughing_orgasm": ["laughed", "giggled", "couldn't help"],
    "blissed_out": ["blissed out", "floating", "gone"],

    # After
    "collapsed_after": ["collapsed", "fell", "boneless"],
    "couldn't_move": ["couldn't move", "paralyzed", "spent"],
    "immediate_affection": ["immediately cuddled", "held", "kissed"],
}

# ============================================================================
# SHOWER/BATH SEX
# ============================================================================

SHOWER_BATH_SEX = {
    # Shower
    "shower_sex": ["shower sex", "in shower", "water running"],
    "steam": ["steam", "steamy", "foggy mirror"],
    "slippery": ["slippery", "careful", "almost fell"],
    "water_temperature": ["hot water", "warm", "cold blast"],

    # Bath
    "bath_sex": ["bath sex", "in tub", "bath together"],
    "bubbles": ["bubbles", "bubble bath", "foam"],
    "bath_too_small": ["too small", "cramped", "tight fit"],

    # Practical
    "water_not_lube": ["water not lube", "needed lube", "friction"],
    "position_challenges": ["position challenges", "limited space", "figured out"],
    "getting_clean_dirty": ["getting clean", "then dirty", "both"],

    # Sensory
    "water_sensation": ["water on skin", "running water", "drops"],
    "tile_cold": ["tile cold", "wall cold", "against cold"],
    "warm_wet": ["warm and wet", "water everywhere", "soaked"],
}

# ============================================================================
# OUTDOOR SEX
# ============================================================================

OUTDOOR_SEX = {
    # Locations
    "beach_sex": ["beach", "sand", "ocean nearby"],
    "woods_sex": ["woods", "forest", "trees"],
    "car_sex": ["car", "backseat", "steamed windows"],
    "balcony_sex": ["balcony", "outside", "might see"],
    "pool_sex": ["pool", "water", "floating"],

    # Challenges
    "bugs_insects": ["bugs", "mosquitos", "insects"],
    "weather_challenges": ["cold", "hot", "wind"],
    "uncomfortable_surface": ["uncomfortable", "hard ground", "rocks"],
    "getting_caught_risk": ["might get caught", "risky", "someone coming"],

    # Benefits
    "thrill_of_outside": ["thrill", "exciting", "risky"],
    "nature_connection": ["connected to nature", "primal", "natural"],
    "fresh_air": ["fresh air", "breeze", "outside air"],

    # Aftermath
    "sand_everywhere": ["sand everywhere", "finding sand", "weeks later"],
    "grass_stains": ["grass stains", "evidence", "marked"],
    "sunburn_places": ["sunburn", "forgot sunscreen", "red places"],
}

# ============================================================================
# HOTEL/TRAVEL SEX
# ============================================================================

HOTEL_TRAVEL_SEX = {
    # Hotel specifics
    "hotel_room": ["hotel room", "nice hotel", "fancy room"],
    "hotel_bed": ["hotel bed", "big bed", "clean sheets"],
    "do_not_disturb": ["do not disturb", "hung sign", "privacy"],
    "room_service_after": ["room service", "ordered food", "didn't leave"],

    # Travel context
    "vacation_sex": ["vacation", "getaway", "holiday"],
    "business_trip_hookup": ["business trip", "in town for", "conference"],
    "destination_wedding": ["wedding", "out of town", "hotel hookup"],

    # Specific situations
    "airplane_bathroom": ["airplane bathroom", "mile high", "tiny space"],
    "train_compartment": ["train", "compartment", "rocking motion"],
    "camping_tent": ["tent", "camping", "sleeping bag"],

    # Travel relationship
    "vacation_fling": ["vacation fling", "holiday romance", "what happens here"],
    "long_distance_reunion": ["long distance", "reunion", "finally together"],
    "traveling_together": ["traveling together", "first trip", "exploring"],
}

# ============================================================================
# WORK HOOKUP ELEMENTS
# ============================================================================

WORK_HOOKUP = {
    # Coworker dynamics
    "coworker_attraction": ["coworker", "work together", "office"],
    "boss_employee": ["boss", "employee", "power dynamic"],
    "equal_colleagues": ["colleagues", "same level", "peers"],

    # Location
    "office_sex": ["office", "desk", "after hours"],
    "supply_closet": ["supply closet", "storage room", "hidden"],
    "conference_room": ["conference room", "meeting room", "table"],
    "parking_garage": ["parking garage", "car at work", "after work"],

    # Risks
    "could_get_fired": ["could get fired", "against policy", "risky"],
    "someone_might_see": ["someone might see", "coworkers", "caught"],
    "keeping_secret": ["keeping secret", "no one knows", "professional"],

    # Aftermath
    "awkward_at_work": ["awkward at work", "pretending", "acting normal"],
    "secret_relationship": ["secret relationship", "hiding", "sneaking"],
    "everyone_knows": ["everyone knows", "obvious", "not subtle"],
}

# ============================================================================
# AGE GAP DYNAMICS
# ============================================================================

AGE_GAP_DYNAMICS = {
    # Gap size
    "small_age_gap": ["few years older", "couple years", "not much older"],
    "medium_age_gap": ["decade older", "ten years", "significant gap"],
    "large_age_gap": ["much older", "could be father", "generation gap"],

    # Dynamics
    "older_more_experienced": ["more experienced", "taught me", "showed me"],
    "younger_energy": ["younger energy", "enthusiasm", "stamina"],
    "mentor_dynamic": ["mentor", "guided", "learned from"],
    "equal_despite_age": ["didn't feel age", "equals", "didn't matter"],

    # Social aspects
    "judgment_about_age": ["people judged", "looked at us", "comments"],
    "family_concerns": ["family concerned", "age difference", "worried"],
    "confident_in_choice": ["don't care what", "our business", "happy"],

    # Attraction
    "attracted_to_older": ["attracted to older", "silver fox", "mature"],
    "attracted_to_younger": ["attracted to younger", "youthful", "energy"],
    "age_not_factor": ["age not factor", "doesn't matter", "just him"],
}

# ============================================================================
# PHYSIQUE TYPES
# ============================================================================

PHYSIQUE_TYPES = {
    # Muscular
    "bodybuilder_build": ["bodybuilder", "huge muscles", "competition body"],
    "athletic_build": ["athletic", "toned", "fit"],
    "swimmer_build": ["swimmer build", "lean muscle", "v-shape"],
    "gym_body": ["gym body", "works out", "defined"],

    # Larger
    "bear_body": ["bear body", "big and hairy", "stocky"],
    "chubby_body": ["chubby", "soft", "belly"],
    "dad_bod": ["dad bod", "comfortable", "soft middle"],

    # Lean
    "twink_body": ["twink", "slim", "smooth and thin"],
    "otter_body": ["otter", "lean and hairy", "wiry"],
    "slender_body": ["slender", "thin", "lithe"],

    # Other
    "average_body": ["average body", "normal build", "regular"],
    "tall_body": ["tall", "towered", "had to look up"],
    "short_body": ["short", "compact", "pocket-sized"],
}

# ============================================================================
# COCK SPECIFIC DESCRIPTIONS
# ============================================================================

COCK_DESCRIPTIONS = {
    # Shape
    "curved_up": ["curved up", "upward curve", "hit right spot"],
    "curved_down": ["curved down", "downward", "different angle"],
    "curved_left_right": ["curved to side", "bent", "angled"],
    "straight_cock": ["straight", "no curve", "direct"],

    # Head
    "big_head": ["big head", "mushroom head", "pronounced"],
    "smaller_head": ["smaller head", "tapered", "gradual"],
    "flared_head": ["flared", "ridge", "pronounced corona"],

    # Other features
    "veiny_cock": ["veiny", "prominent veins", "could see veins"],
    "smooth_cock": ["smooth", "no visible veins", "even"],
    "uncut_cock": ["uncut", "foreskin", "uncircumcised"],
    "cut_cock": ["cut", "circumcised", "no foreskin"],

    # State
    "half_hard": ["half hard", "getting hard", "filling"],
    "fully_hard": ["fully hard", "rock hard", "straining"],
    "soft_cock": ["soft", "flaccid", "resting"],
    "dripping_cock": ["dripping", "leaking", "wet tip"],
}

# ============================================================================
# ASS SPECIFIC DESCRIPTIONS
# ============================================================================

ASS_DESCRIPTIONS = {
    # Shape
    "round_ass": ["round ass", "bubble butt", "perfect globes"],
    "flat_ass": ["flat ass", "no ass", "slim"],
    "muscular_ass": ["muscular ass", "hard", "defined"],
    "soft_ass": ["soft ass", "cushion", "jiggles"],

    # Hair
    "hairy_ass": ["hairy ass", "furry", "covered"],
    "smooth_ass": ["smooth ass", "hairless", "waxed"],
    "lightly_hairy_ass": ["lightly hairy", "some hair", "natural"],

    # Actions
    "spreading_cheeks": ["spread cheeks", "opened", "exposed"],
    "grabbing_ass": ["grabbed ass", "squeezed", "handful"],
    "slapping_ass": ["slapped ass", "spanked", "smacked"],
    "eating_ass": ["ate ass", "rimmed", "tongue"],

    # Reactions
    "ass_clenching": ["clenched", "tightened", "squeezed"],
    "ass_relaxing": ["relaxed", "opened up", "let in"],
    "ass_pushing_back": ["pushed back", "grinding", "meeting"],
}

# ============================================================================
# NIPPLE DESCRIPTIONS
# ============================================================================

NIPPLE_DESCRIPTIONS = {
    # Size/appearance
    "small_nipples": ["small nipples", "tiny", "barely there"],
    "large_nipples": ["large nipples", "big", "pronounced"],
    "puffy_nipples": ["puffy nipples", "swollen looking", "raised"],
    "flat_nipples": ["flat nipples", "flush", "need stimulation"],

    # Color
    "pink_nipples": ["pink nipples", "light", "rosy"],
    "dark_nipples": ["dark nipples", "brown", "darker"],

    # State
    "hard_nipples": ["hard nipples", "erect", "pebbled"],
    "sensitive_nipples": ["sensitive nipples", "responsive", "electric"],

    # Piercings
    "pierced_nipples": ["pierced nipples", "barbells", "rings"],
    "playing_with_piercings": ["tugged piercings", "played with", "twisted"],
}

# ============================================================================
# PRECUM ELEMENTS
# ============================================================================

PRECUM_ELEMENTS = {
    # Amount
    "lots_of_precum": ["lots of precum", "dripping", "soaking"],
    "little_precum": ["little precum", "barely", "just a drop"],
    "constant_leak": ["constantly leaking", "never stopped", "steady"],

    # Using it
    "using_as_lube": ["used as lube", "spread it", "slicked"],
    "licking_precum": ["licked up", "tasted", "cleaned"],
    "spreading_precum": ["spread it", "rubbed", "smeared"],

    # Reactions to
    "turned_on_by_precum": ["loved seeing", "turned on by", "hot"],
    "messy_from_precum": ["messy", "wet", "sticky"],
}

# ============================================================================
# CUM ELEMENTS
# ============================================================================

CUM_ELEMENTS = {
    # Amount
    "lots_of_cum": ["lots of cum", "huge load", "so much"],
    "average_load": ["normal amount", "average", "regular"],
    "small_load": ["small load", "not much", "just a bit"],

    # Where
    "cum_inside": ["came inside", "filled", "deep"],
    "cum_on_face": ["came on face", "facial", "covered face"],
    "cum_on_chest": ["came on chest", "covered chest", "painted"],
    "cum_on_stomach": ["came on stomach", "pooled", "belly"],
    "cum_on_back": ["came on back", "back covered", "spine"],
    "cum_on_ass": ["came on ass", "covered ass", "cheeks"],

    # Actions with
    "swallowing_cum": ["swallowed", "drank", "took it all"],
    "spitting_cum": ["spit out", "didn't swallow", "let fall"],
    "playing_with_cum": ["played with", "spread", "rubbed in"],
    "cum_as_lube": ["used cum as", "slicked", "wet with"],
    "cleaning_cum": ["cleaned up", "wiped", "licked clean"],

    # Reactions
    "loved_cum": ["loved the cum", "wanted it", "begged for"],
    "taste_of_cum": ["taste of cum", "salty", "bitter"],
    "marked_by_cum": ["marked", "claimed", "covered"],
}

# ============================================================================
# BALL ELEMENTS
# ============================================================================

BALL_ELEMENTS = {
    # Attention
    "ball_licking": ["licked balls", "tongue on", "worshipped"],
    "ball_sucking": ["sucked balls", "in mouth", "rolled"],
    "ball_cupping": ["cupped balls", "held", "gentle"],
    "ball_tugging": ["tugged balls", "pulled", "stretched"],

    # Reactions
    "balls_tightening": ["balls tightened", "drawing up", "close"],
    "balls_heavy": ["balls heavy", "full", "aching"],

    # Descriptions
    "big_balls": ["big balls", "large", "heavy"],
    "small_balls": ["small balls", "compact", "tight"],
    "low_hanging": ["low hanging", "swinging", "dangling"],
    "tight_balls": ["tight balls", "close to body", "snug"],
}

# ============================================================================
# PROSTATE STIMULATION DETAILED
# ============================================================================

PROSTATE_DETAILED = {
    # Finding it
    "searching_for_prostate": ["searching", "looking for", "finding"],
    "found_prostate": ["found it", "there", "that's the spot"],
    "can't_find": ["couldn't find", "where is", "not finding"],

    # Stimulation
    "direct_pressure": ["direct pressure", "pressed", "pushed"],
    "massage_prostate": ["massaged", "rubbed", "worked"],
    "pounding_prostate": ["pounding", "hitting", "each thrust"],
    "teasing_prostate": ["teasing", "barely touching", "light"],

    # Sensations
    "prostate_building": ["building", "pressure building", "getting close"],
    "prostate_orgasm": ["prostate orgasm", "hands free", "from inside"],
    "overwhelming_prostate": ["overwhelming", "too much", "intense"],
    "seeing_stars": ["seeing stars", "vision went", "white out"],

    # Reactions
    "legs_shaking_prostate": ["legs shaking", "trembling", "couldn't control"],
    "begging_prostate": ["begging", "please", "more"],
    "incoherent_prostate": ["incoherent", "couldn't speak", "just sounds"],
}

# ============================================================================
# FORESKIN ELEMENTS
# ============================================================================

FORESKIN_ELEMENTS = {
    # State
    "foreskin_retracted": ["pulled back", "retracted", "head exposed"],
    "foreskin_covering": ["covering head", "over", "hooded"],
    "playing_with_foreskin": ["played with", "pulled", "stretched"],

    # Actions
    "tongue_under_foreskin": ["tongue under", "explored", "licked under"],
    "foreskin_stretch": ["stretched", "pulled back", "moved"],
    "docking": ["docking", "foreskin over", "together"],

    # Reactions
    "sensitive_foreskin": ["sensitive", "felt everything", "heightened"],
    "foreskin_slide": ["slid", "natural movement", "gliding"],
}

# ============================================================================
# SPECIFIC KINK: FOOT PLAY
# ============================================================================

FOOT_PLAY = {
    # Worship
    "foot_worship": ["worshipped feet", "kissed feet", "adored"],
    "licking_feet": ["licked feet", "tongue on", "tasted"],
    "sucking_toes": ["sucked toes", "toes in mouth", "each one"],
    "kissing_arch": ["kissed arch", "instep", "sole"],

    # Using feet
    "footjob": ["footjob", "feet on", "used feet"],
    "feet_on_face": ["feet on face", "stepped on", "pressed"],
    "feet_in_lap": ["feet in lap", "rubbing", "teasing"],

    # Reactions
    "foot_appreciation": ["beautiful feet", "perfect feet", "love your feet"],
    "ticklish_feet": ["ticklish", "sensitive", "couldn't take it"],
    "turned_on_by_feet": ["turned on", "feet did it", "hot feet"],

    # Context
    "after_long_day": ["after long day", "tired feet", "needed massage"],
    "fresh_from_shower": ["clean feet", "just showered", "fresh"],
    "sweaty_feet": ["sweaty feet", "after gym", "worked out"],
}

# ============================================================================
# SPECIFIC KINK: ARMPIT PLAY
# ============================================================================

ARMPIT_PLAY = {
    # Actions
    "armpit_licking": ["licked armpit", "tongue in pit", "tasted"],
    "armpit_sniffing": ["sniffed armpit", "buried nose", "inhaled"],
    "armpit_worship": ["worshipped armpits", "attention to", "adored"],

    # State
    "sweaty_armpits": ["sweaty pits", "after workout", "musky"],
    "clean_armpits": ["clean", "fresh", "showered"],
    "hairy_armpits": ["hairy pits", "full bush", "natural"],
    "smooth_armpits": ["smooth pits", "shaved", "bare"],

    # Reactions
    "scent_arousing": ["scent arousing", "pheromones", "turned on"],
    "embarrassed_about": ["embarrassed", "self conscious", "sorry"],
    "encouraged_by_partner": ["encouraged", "loved it", "don't apologize"],
}

# ============================================================================
# SPECIFIC KINK: MUSCLE WORSHIP
# ============================================================================

MUSCLE_WORSHIP = {
    # Actions
    "feeling_muscles": ["felt muscles", "hands on", "traced"],
    "licking_muscles": ["licked muscles", "tongue on", "tasted skin"],
    "kissing_muscles": ["kissed muscles", "worshipped", "reverent"],

    # Specific muscles
    "bicep_worship": ["bicep worship", "flexed for", "kissed bicep"],
    "pec_worship": ["pec worship", "chest muscles", "felt chest"],
    "ab_worship": ["ab worship", "six pack", "traced abs"],
    "back_muscle_worship": ["back muscles", "lats", "traps"],
    "thigh_worship": ["thigh worship", "quad", "powerful legs"],

    # Dynamics
    "flexing_for_partner": ["flexed", "showed off", "displayed"],
    "size_difference_worship": ["so much bigger", "dwarfed by", "massive compared"],
    "strength_display": ["showed strength", "lifted", "carried"],

    # Reactions
    "in_awe": ["in awe", "couldn't believe", "amazed"],
    "feeling_small": ["felt small", "delicate", "protected"],
    "turned_on_by_muscles": ["turned on", "muscles did it", "so hot"],
}

# ============================================================================
# SPECIFIC KINK: UNIFORM/GEAR
# ============================================================================

UNIFORM_GEAR = {
    # Leather
    "leather_harness": ["leather harness", "straps", "buckles"],
    "leather_pants": ["leather pants", "tight leather", "squeaky"],
    "leather_jacket": ["leather jacket", "smell of leather", "worn"],
    "leather_boots": ["leather boots", "stomping", "kicked"],
    "full_leather": ["full leather", "head to toe", "geared up"],

    # Rubber/latex
    "rubber_suit": ["rubber suit", "latex", "shiny"],
    "rubber_gloves": ["rubber gloves", "latex gloves", "snapped"],
    "gas_mask": ["gas mask", "breathing", "restricted"],

    # Sports gear
    "jockstrap_gear": ["jockstrap", "worn jock", "gym gear"],
    "sports_uniform": ["sports uniform", "jersey", "shorts"],
    "wrestling_singlet": ["singlet", "tight", "bulge"],

    # Other gear
    "puppy_hood": ["puppy hood", "pup mask", "ears"],
    "collar_gear": ["collar", "leather collar", "owned"],
    "cuffs_gear": ["cuffs", "restraints", "locked"],
}

# ============================================================================
# SPECIFIC KINK: WATERSPORTS
# ============================================================================

WATERSPORTS = {
    # Actions
    "pissing_on": ["pissed on", "golden shower", "stream"],
    "pissing_in_mouth": ["pissed in mouth", "drank", "swallowed"],
    "watching_piss": ["watched piss", "turned on by", "hot stream"],
    "holding_piss": ["holding it", "desperate", "had to go"],

    # Context
    "marking_territory": ["marking", "claiming", "territory"],
    "desperation_play": ["desperate to pee", "couldn't hold", "almost accident"],
    "in_shower_piss": ["in shower", "easy cleanup", "water running"],

    # Reactions
    "turned_on_watersports": ["turned on", "never thought", "actually liked"],
    "warm_sensation": ["warm", "felt it", "hot stream"],
    "humiliation_watersports": ["humiliated", "degraded", "used"],
}

# ============================================================================
# SPECIFIC KINK: HUMILIATION
# ============================================================================

HUMILIATION_KINK = {
    # Verbal humiliation
    "verbal_degradation": ["called names", "degraded", "put down"],
    "public_humiliation": ["in front of others", "everyone saw", "displayed"],
    "comparison_humiliation": ["compared to", "not as good", "smaller than"],
    "failure_humiliation": ["failed", "couldn't", "pathetic"],

    # Physical humiliation
    "forced_position": ["made to", "position", "display"],
    "kneeling_humiliation": ["kneel", "at feet", "below"],
    "crawling": ["crawl", "on floor", "hands and knees"],

    # Emotional
    "shame_arousal": ["ashamed but", "embarrassed and turned on", "shouldn't like"],
    "blushing_humiliation": ["blushing", "face red", "couldn't hide"],
    "tears_humiliation": ["cried", "tears", "broke"],

    # Consensual context
    "agreed_humiliation": ["agreed to", "negotiated", "wanted this"],
    "aftercare_humiliation": ["aftercare", "praised after", "rebuilt"],
    "love_despite": ["love you", "still valued", "just play"],
}

# ============================================================================
# SPECIFIC KINK: SERVICE
# ============================================================================

SERVICE_KINK = {
    # Types of service
    "domestic_service": ["cleaned", "cooked", "served"],
    "sexual_service": ["serviced", "pleasured", "attended to"],
    "body_service": ["bathed", "dressed", "groomed"],
    "waiting_service": ["waited on", "available", "at beck and call"],

    # Attitude
    "pride_in_service": ["pride in serving", "did well", "pleased"],
    "anticipating_needs": ["anticipated", "knew what needed", "before asked"],
    "perfect_service": ["perfect service", "flawless", "praised"],
    "punished_for_failure": ["punished", "failed", "corrected"],

    # Dynamics
    "service_top": ["service top", "your pleasure", "for you"],
    "service_bottom": ["service bottom", "to be used", "available"],
    "24_7_service": ["24/7", "always serving", "full time"],

    # Rewards
    "praised_for_service": ["praised", "good job", "pleased me"],
    "rewarded_service": ["rewarded", "earned", "allowed"],
}

# ============================================================================
# SPECIFIC KINK: OBJECTIFICATION
# ============================================================================

OBJECTIFICATION = {
    # Furniture
    "human_furniture": ["furniture", "footrest", "table"],
    "sat_on": ["sat on", "used as seat", "weight on"],
    "stepped_on": ["stepped on", "walked over", "beneath"],

    # Object treatment
    "treated_as_object": ["treated as", "just a", "not a person"],
    "ignored_while_used": ["ignored", "didn't matter", "just there"],
    "displayed_as_object": ["displayed", "shown off", "trophy"],

    # Specific objects
    "fucktoy": ["fucktoy", "just a hole", "for use"],
    "cocksleeve": ["cocksleeve", "warm hole", "just for"],
    "cumdump": ["cumdump", "for cum", "receptacle"],

    # Reactions
    "peaceful_objectification": ["peaceful", "no thoughts", "just exist"],
    "aroused_by_objectification": ["aroused", "turned on by", "being nothing"],
    "freedom_in_objectification": ["freedom", "no responsibility", "just be"],
}

# ============================================================================
# SPECIFIC KINK: BREATH PLAY
# ============================================================================

BREATH_PLAY = {
    # Methods
    "hand_on_throat": ["hand on throat", "squeezed throat", "choked"],
    "arm_around_throat": ["arm around", "headlock", "from behind"],
    "pillow_over_face": ["pillow", "smothered", "covered face"],
    "face_sitting_breath": ["sat on face", "couldn't breathe", "smothered"],

    # Intensity
    "light_pressure": ["light pressure", "hint of", "suggestion"],
    "firm_grip": ["firm grip", "tighter", "restricted"],
    "cutting_off_air": ["cut off air", "couldn't breathe", "gasping"],

    # Sensations
    "lightheaded": ["lightheaded", "dizzy", "floating"],
    "rushing_sensation": ["rushing", "blood rushing", "heightened"],
    "panic_pleasure": ["panic mixed with", "fear and pleasure", "edge"],

    # Safety
    "tapping_out_breath": ["tapped out", "signal", "stop"],
    "checking_in_breath": ["checked in", "okay", "color"],
    "knowing_limits": ["know limits", "careful", "controlled"],
}

# ============================================================================
# SPECIFIC KINK: FACE FUCKING
# ============================================================================

FACE_FUCKING = {
    # Action
    "thrusting_into_mouth": ["thrust into mouth", "fucking face", "used mouth"],
    "holding_head_still": ["held head", "couldn't move", "still"],
    "controlling_pace": ["controlled pace", "set rhythm", "decided"],

    # Depth
    "shallow_face": ["shallow", "just tip", "teasing"],
    "deep_face": ["deep", "throat", "all the way"],
    "gagging_face": ["gagging", "choking", "fighting reflex"],

    # Position
    "on_knees_face": ["on knees", "looking up", "below"],
    "lying_back_face": ["lying back", "head hanging", "upside down"],
    "standing_over": ["standing over", "looking down", "dominant"],

    # Reactions
    "tears_streaming_face": ["tears streaming", "crying", "watering eyes"],
    "drool_everywhere": ["drool", "spit", "messy"],
    "struggling_face": ["struggling", "hands on thighs", "pushing"],
    "accepting_face": ["accepted", "let it happen", "surrendered"],
}

# ============================================================================
# SPECIFIC KINK: GLORY HOLE
# ============================================================================

GLORY_HOLE = {
    # Setting
    "bathroom_glory": ["bathroom", "stall", "public restroom"],
    "bookstore_glory": ["bookstore", "arcade", "video booth"],
    "club_glory": ["club", "back room", "dark room"],
    "homemade_glory": ["homemade", "DIY", "made one"],

    # Experience
    "giving_through_hole": ["through hole", "anonymous mouth", "just a hole"],
    "receiving_through_hole": ["cock through hole", "didn't see", "just felt"],
    "mystery_person": ["mystery", "didn't know who", "anonymous"],

    # Sensations
    "only_sensation": ["only felt", "couldn't see", "just sensation"],
    "anonymous_thrill": ["anonymous thrill", "didn't know", "anyone"],
    "multiple_people": ["multiple", "one after another", "several"],
}

# ============================================================================
# SPECIFIC KINK: DOUBLE PENETRATION
# ============================================================================

DOUBLE_PENETRATION = {
    # Types
    "two_cocks": ["two cocks", "both inside", "filled by two"],
    "cock_and_toy": ["cock and toy", "dildo too", "added toy"],
    "cock_and_fingers": ["cock and fingers", "stretched more", "added"],

    # Sensations
    "incredibly_full": ["incredibly full", "stuffed", "couldn't take more"],
    "stretched_to_limit": ["stretched to limit", "maximum", "thought couldn't"],
    "overwhelming_dp": ["overwhelming", "too much", "intense"],

    # Logistics
    "preparing_for_dp": ["prepared", "stretched first", "worked up to"],
    "finding_rhythm": ["finding rhythm", "coordinating", "together"],
    "positions_for_dp": ["position for", "logistics", "figured out"],

    # Reactions
    "screaming_dp": ["screaming", "couldn't be quiet", "loud"],
    "incoherent_dp": ["incoherent", "couldn't form words", "gone"],
    "biggest_orgasm": ["biggest orgasm", "never felt", "intense"],
}

# ============================================================================
# SPECIFIC KINK: FISTING
# ============================================================================

FISTING_ELEMENTS = {
    # Preparation
    "lots_of_lube_fisting": ["lots of lube", "couldn't have enough", "slick"],
    "gradual_stretching": ["gradual", "one finger at time", "patient"],
    "relaxation_required": ["had to relax", "breathe", "let go"],

    # Progression
    "one_finger_fist": ["started with one", "first finger", "beginning"],
    "multiple_fingers_fist": ["multiple fingers", "three then four", "adding"],
    "knuckles_fist": ["knuckles", "widest part", "almost there"],
    "whole_hand": ["whole hand", "popped in", "inside"],

    # Sensations
    "incredible_fullness": ["incredible fullness", "never felt so", "complete"],
    "pressure_fisting": ["pressure", "intense", "everywhere"],
    "prostate_fist": ["prostate", "internal massage", "hitting spots"],

    # Movement
    "still_inside": ["still", "didn't move", "just present"],
    "gentle_movement": ["gentle movement", "small motions", "careful"],
    "punch_fisting": ["punch fisting", "in and out", "intense"],
}

# ============================================================================
# SPECIFIC KINK: SOUNDING
# ============================================================================

SOUNDING_ELEMENTS = {
    # Equipment
    "metal_sounds": ["metal sounds", "surgical steel", "cold"],
    "silicone_sounds": ["silicone", "flexible", "beginner"],
    "vibrating_sounds": ["vibrating", "buzzing", "added sensation"],

    # Sensations
    "urethra_sensation": ["urethra", "inside", "never felt before"],
    "deep_sounding": ["deep", "further", "all the way"],
    "strange_pleasure": ["strange pleasure", "shouldn't feel good", "does"],

    # Reactions
    "intense_sounding": ["intense", "overwhelming", "too much"],
    "precum_sounding": ["precum", "leaking constantly", "wet"],
    "hands_free_sounding": ["hands free", "from sounding alone", "no touch"],
}

# ============================================================================
# SPECIFIC KINK: CBT (COCK AND BALL TORTURE)
# ============================================================================

CBT_ELEMENTS = {
    # Ball torture
    "ball_squeezing": ["squeezed balls", "crushed", "pressure"],
    "ball_slapping": ["slapped balls", "hit", "impact"],
    "ball_stretching": ["stretched balls", "weights", "pulled down"],
    "ball_bondage": ["ball bondage", "tied", "separated"],

    # Cock torture
    "cock_slapping": ["slapped cock", "hit", "smacked"],
    "cock_stepping": ["stepped on", "under foot", "crushed"],
    "cock_bondage": ["cock bondage", "tied", "restricted"],

    # Pain response
    "pain_pleasure_cbt": ["pain became pleasure", "hurt so good", "converted"],
    "tears_from_cbt": ["cried", "tears", "too much"],
    "begging_cbt": ["begged", "please", "more or stop"],

    # Aftermath
    "sore_after_cbt": ["sore after", "ached", "feeling it"],
    "marks_from_cbt": ["marks", "bruises", "evidence"],
}

# ============================================================================
# SPECIFIC KINK: ELECTRO
# ============================================================================

ELECTRO_ELEMENTS = {
    # Equipment
    "violet_wand": ["violet wand", "spark", "electricity"],
    "tens_unit": ["tens unit", "pads", "pulses"],
    "electro_plug": ["electro plug", "internal", "shocking"],
    "electro_cock_ring": ["electro ring", "around cock", "zapping"],

    # Sensations
    "tingling_electro": ["tingling", "buzzing", "electric"],
    "sharp_shock": ["sharp shock", "zap", "sudden"],
    "pulsing_electro": ["pulsing", "rhythmic", "waves"],
    "building_electro": ["building", "intensity increasing", "higher"],

    # Reactions
    "jumping_from_shock": ["jumped", "startled", "involuntary"],
    "muscles_contracting": ["muscles contracted", "clenched", "spasm"],
    "electro_orgasm": ["forced orgasm", "couldn't stop", "electricity made"],
}

# ============================================================================
# NARRATIVE: SLOW BURN
# ============================================================================

SLOW_BURN = {
    # Building tension
    "tension_building": ["tension building", "weeks of", "finally"],
    "almost_moments": ["almost", "so close", "interrupted"],
    "longing_looks": ["longing looks", "wanted but", "couldn't act"],
    "delayed_gratification": ["delayed", "waiting", "worth the wait"],

    # Obstacles
    "circumstances_preventing": ["circumstances", "couldn't", "not yet"],
    "denial_of_feelings": ["denied feelings", "pretended", "ignored"],
    "external_obstacles": ["others prevented", "situation", "timing"],
    "internal_obstacles": ["fear prevented", "self-doubt", "wasn't ready"],

    # Finally happening
    "finally_together": ["finally", "at last", "waited so long"],
    "worth_the_wait": ["worth it", "so much better", "built up"],
    "explosive_first_time": ["explosive", "couldn't hold back", "released"],
}

# ============================================================================
# NARRATIVE: ENEMIES TO LOVERS
# ============================================================================

ENEMIES_TO_LOVERS = {
    # Enemy phase
    "hatred": ["hated", "couldn't stand", "enemy"],
    "antagonism": ["antagonized", "provoked", "fought"],
    "competition": ["competed", "rival", "had to beat"],

    # Tension shift
    "hate_attraction": ["hated but attracted", "confused", "shouldn't want"],
    "angry_attraction": ["angry and attracted", "furious but", "hate how I"],
    "forced_proximity": ["forced together", "had to work with", "stuck with"],

    # Turning point
    "seeing_differently": ["saw differently", "realized", "wrong about"],
    "vulnerability_shown": ["showed vulnerability", "different side", "human"],
    "saving_each_other": ["saved", "helped", "was there"],

    # Lover phase
    "hate_to_love": ["hate became love", "transformed", "now love"],
    "passion_from_anger": ["passion from anger", "channeled", "intensity"],
    "still_bicker": ["still bicker", "argue but", "part of us"],
}

# ============================================================================
# NARRATIVE: FRIENDS TO LOVERS
# ============================================================================

FRIENDS_TO_LOVERS = {
    # Friend phase
    "long_friendship": ["friends for years", "known forever", "best friends"],
    "platonic_history": ["never thought of", "just friends", "platonic"],
    "close_bond": ["close bond", "knew everything", "best friend"],

    # Realization
    "sudden_realization": ["suddenly realized", "hit me", "always there"],
    "gradual_realization": ["gradually realized", "over time", "creeping"],
    "jealousy_trigger": ["jealousy", "saw with someone", "didn't like it"],
    "almost_lost_them": ["almost lost", "couldn't imagine", "scared me"],

    # Transition
    "risking_friendship": ["risking friendship", "could ruin", "worth it"],
    "awkward_transition": ["awkward", "different now", "adjusting"],
    "natural_progression": ["natural", "made sense", "always leading here"],

    # Lover phase
    "best_of_both": ["friend and lover", "best of both", "everything"],
    "deeper_connection": ["deeper now", "more than before", "complete"],
    "comfortable_love": ["comfortable", "know each other", "easy"],
}

# ============================================================================
# NARRATIVE: FORBIDDEN LOVE
# ============================================================================

FORBIDDEN_LOVE = {
    # Why forbidden
    "social_class": ["different classes", "not allowed", "beneath"],
    "forbidden_relationship": ["forbidden", "not allowed", "taboo"],
    "age_inappropriate": ["age difference", "shouldn't", "wrong"],
    "already_taken": ["already taken", "cheating", "affair"],
    "workplace_forbidden": ["workplace rules", "could get fired", "policy"],

    # Secrecy
    "hidden_relationship": ["hidden", "secret", "no one knows"],
    "sneaking_around": ["sneaking", "hiding", "careful"],
    "stolen_moments": ["stolen moments", "brief", "had to be quick"],
    "lying_to_others": ["lying", "covering", "excuses"],

    # Risks
    "fear_of_discovery": ["fear of discovery", "what if", "caught"],
    "consequences_if_caught": ["consequences", "would lose", "destroyed"],
    "thrill_of_forbidden": ["thrill", "exciting because", "danger"],

    # Resolution
    "choosing_love": ["chose love", "worth it", "damn consequences"],
    "giving_up": ["gave up", "too hard", "couldn't continue"],
    "discovered": ["discovered", "found out", "exposed"],
}

# ============================================================================
# NARRATIVE: HURT/COMFORT
# ============================================================================

HURT_COMFORT = {
    # The hurt
    "physical_hurt": ["injured", "hurt", "wounded"],
    "emotional_hurt": ["heartbroken", "devastated", "trauma"],
    "past_hurt": ["past trauma", "history", "old wounds"],
    "recent_hurt": ["just happened", "fresh", "raw"],

    # Comforting actions
    "holding_comfort": ["held", "arms around", "close"],
    "words_of_comfort": ["soothing words", "it's okay", "I'm here"],
    "taking_care": ["took care of", "nursed", "tended"],
    "just_being_there": ["just there", "present", "didn't leave"],

    # Healing
    "starting_to_heal": ["starting to heal", "getting better", "progress"],
    "setbacks": ["setback", "bad day", "triggered"],
    "patience_required": ["patience", "took time", "slow"],

    # Love through pain
    "love_despite_hurt": ["loved anyway", "still there", "didn't leave"],
    "stronger_after": ["stronger after", "because of", "survived"],
    "trust_after_hurt": ["learned to trust", "opened up", "let in"],
}

# ============================================================================
# NARRATIVE: SECOND CHANCE
# ============================================================================

SECOND_CHANCE = {
    # The past
    "past_relationship": ["past relationship", "used to be", "before"],
    "why_ended": ["why ended", "what happened", "fell apart"],
    "regrets": ["regrets", "should have", "wish I had"],
    "never_forgot": ["never forgot", "always thought about", "couldn't move on"],

    # Reunion
    "unexpected_reunion": ["unexpected", "ran into", "fate"],
    "planned_reunion": ["reached out", "contacted", "found again"],
    "years_later": ["years later", "so long", "time passed"],

    # Working through
    "addressing_past": ["addressed past", "talked about", "what went wrong"],
    "apologies": ["apologized", "sorry", "regret"],
    "forgiveness": ["forgave", "let go", "moved past"],
    "different_now": ["different now", "changed", "grown"],

    # New beginning
    "fresh_start": ["fresh start", "new beginning", "clean slate"],
    "not_repeating": ["not repeating", "learned from", "different this time"],
    "better_than_before": ["better than before", "what it should be", "finally right"],
}

# ============================================================================
# NARRATIVE: FAKE DATING
# ============================================================================

FAKE_DATING = {
    # Setup
    "fake_boyfriend": ["fake boyfriend", "pretend to be", "act like"],
    "family_event": ["family event", "wedding", "convince family"],
    "work_event": ["work event", "office party", "impress boss"],
    "ex_jealousy": ["make ex jealous", "show them", "prove"],

    # Rules
    "rules_established": ["established rules", "boundaries", "just pretend"],
    "physical_boundaries": ["how far", "can we kiss", "touching allowed"],
    "time_limit": ["time limit", "just for", "then back to"],

    # Blurring lines
    "feels_real": ["feels real", "not pretending", "actually like"],
    "confused_feelings": ["confused", "wasn't supposed to", "catching feelings"],
    "jealousy_unexpected": ["jealousy", "didn't expect", "shouldn't feel"],

    # Resolution
    "admitting_real": ["admitting real", "not fake anymore", "actually want"],
    "scared_to_admit": ["scared to admit", "what if they don't", "risk"],
    "mutual_realization": ["both realized", "same time", "felt it too"],
}

# ============================================================================
# NARRATIVE: MARRIAGE OF CONVENIENCE
# ============================================================================

MARRIAGE_CONVENIENCE = {
    # Reasons
    "green_card": ["green card", "immigration", "stay in country"],
    "inheritance": ["inheritance", "will required", "get money"],
    "business_reasons": ["business reasons", "merger", "contract"],
    "protection": ["protection", "safety", "need husband"],

    # Arrangement
    "terms_agreed": ["terms agreed", "contract", "arrangement"],
    "separate_lives": ["separate lives", "own rooms", "just paper"],
    "public_vs_private": ["public couple", "private strangers", "appearances"],

    # Complications
    "developing_feelings": ["developing feelings", "wasn't supposed to", "complicated"],
    "real_attraction": ["actually attracted", "noticed", "want"],
    "domesticity": ["playing house", "domestic", "felt real"],

    # Resolution
    "choosing_real": ["choosing real", "want this", "not convenience"],
    "renegotiating": ["renegotiating", "new terms", "real now"],
}

# ============================================================================
# NARRATIVE: BODYGUARD/PROTECTOR
# ============================================================================

BODYGUARD_NARRATIVE = {
    # Setup
    "assigned_protection": ["assigned to protect", "bodyguard", "detail"],
    "threat_exists": ["threat", "danger", "needs protection"],
    "reluctant_protectee": ["doesn't want", "can handle", "not needed"],

    # Dynamics
    "professional_distance": ["professional", "just a job", "boundaries"],
    "constant_proximity": ["always there", "close quarters", "24/7"],
    "seeing_real_person": ["saw the real", "behind public", "vulnerable"],

    # Tension
    "forbidden_attraction": ["forbidden", "against rules", "shouldn't"],
    "protective_instinct": ["protective instinct", "more than job", "would die for"],
    "danger_brings_closer": ["danger", "close call", "realized"],

    # Resolution
    "choosing_love_over_job": ["chose love", "quit", "not just a job"],
    "staying_protector_lover": ["both", "still protect", "but also love"],
}

# ============================================================================
# NARRATIVE: CELEBRITY/FAN
# ============================================================================

CELEBRITY_NARRATIVE = {
    # Setup
    "fan_meets_celebrity": ["fan", "met", "couldn't believe"],
    "celebrity_in_disguise": ["disguised", "didn't know who", "normal"],
    "work_brings_together": ["worked together", "hired", "professional"],

    # Dynamics
    "power_imbalance": ["power imbalance", "famous vs not", "different worlds"],
    "public_vs_private": ["public persona", "private person", "real them"],
    "media_attention": ["media", "paparazzi", "exposure"],

    # Challenges
    "trust_issues": ["trust issues", "using me", "for fame"],
    "lifestyle_difference": ["different lifestyle", "adjusting", "not normal"],
    "fans_jealousy": ["fans jealous", "hate", "threats"],

    # Resolution
    "love_worth_spotlight": ["worth it", "despite attention", "chose this"],
    "keeping_private": ["keeping private", "protected", "just us"],
}

# ============================================================================
# NARRATIVE: BOSS/EMPLOYEE
# ============================================================================

BOSS_EMPLOYEE_NARRATIVE = {
    # Setup
    "hired": ["hired", "started job", "new employee"],
    "attracted_to_boss": ["attracted to boss", "couldn't help", "noticed"],
    "boss_attracted": ["boss attracted", "couldn't act", "wanted"],

    # Dynamics
    "power_imbalance_work": ["power imbalance", "they're my boss", "inappropriate"],
    "professional_masks": ["professional", "hid attraction", "acted normal"],
    "working_closely": ["working closely", "late nights", "proximity"],

    # Complications
    "HR_concerns": ["HR", "could get fired", "policy"],
    "colleagues_noticing": ["colleagues noticed", "obvious", "rumors"],
    "career_concerns": ["career", "using me", "getting ahead"],

    # Resolution
    "one_transfers": ["transferred", "different department", "no conflict"],
    "worth_the_risk": ["worth risk", "don't care", "want this"],
    "keeping_secret_work": ["keeping secret", "no one knows", "professional"],
}

# ============================================================================
# NARRATIVE: ROOMMATES
# ============================================================================

ROOMMATE_NARRATIVE = {
    # Setup
    "craigslist_roommate": ["found online", "needed roommate", "stranger"],
    "friend_roommate": ["friend moved in", "needed place", "offered"],
    "forced_roommate": ["assigned", "no choice", "stuck with"],

    # Proximity issues
    "one_bathroom": ["one bathroom", "shared space", "walking in"],
    "thin_walls": ["thin walls", "heard", "couldn't unhear"],
    "shared_kitchen": ["kitchen encounters", "morning coffee", "late night"],
    "accidentally_saw": ["accidentally saw", "didn't mean to", "wasn't looking"],

    # Building tension
    "tension_in_apartment": ["tension", "couldn't escape", "always there"],
    "domestic_intimacy": ["domestic intimacy", "felt like", "playing house"],
    "friends_vs_more": ["more than roommates", "crossed line", "different now"],

    # Resolution
    "finally_acted": ["finally acted", "one of us", "couldn't anymore"],
    "still_roommates": ["still roommates", "but also", "best of both"],
}

# ============================================================================
# NARRATIVE: SNOWED IN/TRAPPED
# ============================================================================

TRAPPED_NARRATIVE = {
    # Trapped scenarios
    "snowed_in": ["snowed in", "blizzard", "couldn't leave"],
    "elevator_stuck": ["elevator stuck", "trapped", "hours"],
    "cabin_isolation": ["cabin", "isolated", "no way out"],
    "storm_stranded": ["storm", "stranded", "had to stay"],

    # Forced proximity
    "no_escape": ["no escape", "stuck together", "forced proximity"],
    "small_space": ["small space", "close quarters", "can't avoid"],
    "shared_warmth": ["shared warmth", "had to stay warm", "body heat"],

    # Building tension
    "nothing_to_do": ["nothing to do", "bored", "only each other"],
    "walls_coming_down": ["walls down", "got to know", "opened up"],
    "tension_building_trapped": ["tension building", "couldn't ignore", "inevitable"],

    # Resolution
    "acted_on_tension": ["acted on it", "finally", "couldn't resist"],
    "continue_after_trapped": ["continued after", "back to normal but", "want more"],
}

# ============================================================================
# NARRATIVE: ONLINE/LONG DISTANCE
# ============================================================================

ONLINE_RELATIONSHIP = {
    # Meeting online
    "met_online": ["met online", "internet", "virtual"],
    "chat_connection": ["chatting", "texting", "online connection"],
    "voice_first": ["voice first", "phone calls", "heard before saw"],
    "video_calls": ["video calls", "saw each other", "screen"],

    # Building relationship
    "emotional_connection_first": ["emotional first", "knew them", "before physical"],
    "sharing_everything": ["shared everything", "knew everything", "open"],
    "anticipation_meeting": ["anticipation", "can't wait", "finally meet"],

    # Meeting in person
    "first_meeting": ["first meeting", "airport", "finally real"],
    "matching_expectations": ["matched", "exactly like", "even better"],
    "not_matching": ["different", "not like expected", "adjustment"],

    # Long distance challenges
    "time_zones": ["time zones", "scheduling", "middle of night"],
    "missing_physical": ["missing physical", "touch starved", "want to hold"],
    "visits": ["visits", "counting days", "limited time"],
}

# ============================================================================
# NARRATIVE: ONE NIGHT STAND TO MORE
# ============================================================================

ONS_TO_MORE = {
    # The one night stand
    "hookup_night": ["hooked up", "one night", "no expectations"],
    "bar_pickup_ons": ["met at bar", "went home together", "that night"],
    "app_hookup": ["app hookup", "looking for fun", "just sex"],

    # After
    "awkward_morning": ["awkward morning", "sneaking out", "what now"],
    "exchanging_numbers": ["exchanged numbers", "maybe again", "keep in touch"],
    "can't_stop_thinking": ["can't stop thinking", "keep remembering", "want more"],

    # Running into each other
    "run_into_again": ["ran into", "saw again", "small world"],
    "same_social_circle": ["same friends", "keep seeing", "can't avoid"],
    "work_together": ["work together", "didn't know", "awkward"],

    # Development
    "another_hookup": ["hooked up again", "couldn't resist", "just once more"],
    "starting_to_date": ["started dating", "more than sex", "actual dates"],
    "catching_feelings": ["caught feelings", "wasn't supposed to", "complicated"],
}

# ============================================================================
# NARRATIVE: ARRANGED RELATIONSHIP
# ============================================================================

ARRANGED_RELATIONSHIP = {
    # Setup
    "family_arranged": ["family arranged", "parents decided", "traditional"],
    "matchmaker": ["matchmaker", "set up", "compatible"],
    "business_arrangement": ["business", "families", "alliance"],

    # Initial meeting
    "meeting_stranger": ["meeting stranger", "didn't know", "arranged to meet"],
    "first_impressions": ["first impression", "not what expected", "surprised"],
    "going_through_motions": ["going through motions", "expected to", "obligation"],

    # Development
    "learning_each_other": ["learning each other", "discovering", "getting to know"],
    "unexpected_compatibility": ["unexpected", "actually compatible", "surprised"],
    "growing_attraction": ["growing attraction", "didn't expect", "feeling more"],

    # Resolution
    "falling_in_love": ["fell in love", "actually love", "lucky"],
    "making_it_work": ["making it work", "choosing each other", "would choose again"],
}

# ============================================================================
# TONE: HUMOROUS/LIGHT
# ============================================================================

HUMOROUS_TONE = {
    # Banter
    "witty_banter": ["witty banter", "teasing", "back and forth"],
    "sarcasm": ["sarcasm", "dry humor", "deadpan"],
    "playful_insults": ["playful insults", "affectionate mocking", "roasting"],

    # Awkward humor
    "awkward_situations": ["awkward", "embarrassing", "cringe"],
    "mishaps": ["mishap", "went wrong", "disaster"],
    "laughing_at_selves": ["laughed at selves", "can't help but", "ridiculous"],

    # During sex
    "funny_during_sex": ["funny during", "laughed", "light moment"],
    "not_taking_serious": ["not too serious", "playful", "fun"],
    "jokes_during": ["jokes", "puns", "terrible timing"],

    # Overall tone
    "light_hearted": ["light hearted", "fun", "not heavy"],
    "romcom_vibes": ["romcom", "cute", "feel good"],
}

# ============================================================================
# TONE: DARK/INTENSE
# ============================================================================

DARK_TONE = {
    # Emotional darkness
    "angst": ["angst", "pain", "emotional turmoil"],
    "tragedy": ["tragedy", "loss", "grief"],
    "trauma": ["trauma", "ptsd", "past"],

    # Content darkness
    "dark_themes": ["dark themes", "heavy content", "not light"],
    "morally_grey": ["morally grey", "not good guys", "complicated"],
    "villain_protagonist": ["villain", "bad guy", "anti-hero"],

    # Relationship darkness
    "toxic_elements": ["toxic", "unhealthy", "codependent"],
    "obsessive": ["obsessive", "unhealthy fixation", "can't let go"],
    "possessive_dark": ["possessive", "won't share", "mine only"],

    # Warnings
    "dead_dove": ["dead dove", "exactly as warned", "no redemption"],
    "dark_ending": ["dark ending", "not happy", "tragedy"],
}

# ============================================================================
# TONE: SWEET/FLUFFY
# ============================================================================

SWEET_TONE = {
    # Affection
    "sweet_gestures": ["sweet gestures", "thoughtful", "caring"],
    "pet_names": ["pet names", "terms of endearment", "nicknames"],
    "constant_affection": ["constant affection", "always touching", "can't help it"],

    # Domestic
    "domestic_fluff": ["domestic fluff", "everyday moments", "simple"],
    "cooking_together": ["cooking together", "domestic", "home"],
    "lazy_mornings": ["lazy mornings", "no rush", "together"],

    # Emotional
    "soft_feelings": ["soft feelings", "warm", "fuzzy"],
    "declarations_love": ["declarations", "I love you", "expressing"],
    "comfort": ["comfort", "safe", "secure"],

    # Overall
    "tooth_rotting_sweet": ["tooth rotting", "so sweet", "diabetes inducing"],
    "happy_ending": ["happy ending", "HEA", "together"],
    "no_conflict": ["no real conflict", "just cute", "pure fluff"],
}

# ============================================================================
# TONE: SMUT-FOCUSED
# ============================================================================

SMUT_FOCUSED = {
    # Explicit level
    "explicit": ["explicit", "graphic", "detailed"],
    "porn_with_plot": ["porn with plot", "smut but story", "sexy story"],
    "pwp": ["PWP", "porn without plot", "just sex"],

    # Focus
    "sex_scenes_detailed": ["detailed sex scenes", "explicit scenes", "graphic"],
    "multiple_sex_scenes": ["multiple scenes", "lots of sex", "frequently"],
    "sexual_tension_heavy": ["heavy sexual tension", "lots of UST", "tension"],

    # Style
    "purple_prose": ["purple prose", "flowery", "elaborate"],
    "clinical_descriptions": ["clinical", "anatomical", "precise"],
    "emotional_smut": ["emotional smut", "connected sex", "meaningful"],
}

# ============================================================================
# POV AND PERSPECTIVE
# ============================================================================

POV_PERSPECTIVE = {
    # First person
    "first_person_mc": ["I", "my", "first person"],
    "first_person_unreliable": ["unreliable narrator", "might not be true", "biased"],

    # Third person
    "third_limited": ["third limited", "his thoughts", "followed one"],
    "third_omniscient": ["third omniscient", "knew both", "all knowing"],
    "third_close": ["close third", "intimate", "in his head"],

    # Second person
    "second_person": ["you", "reader insert", "second person"],

    # Switching POV
    "alternating_pov": ["alternating", "switched between", "both perspectives"],
    "chapter_pov_switch": ["each chapter", "different POV", "traded off"],
}

# ============================================================================
# WORD COUNT/LENGTH
# ============================================================================

LENGTH_MARKERS = {
    # Short
    "drabble": ["drabble", "100 words", "very short"],
    "ficlet": ["ficlet", "under 1000", "short piece"],
    "one_shot": ["one shot", "standalone", "complete in one"],

    # Medium
    "short_story": ["short story", "few chapters", "brief"],
    "novella": ["novella", "longer", "substantial"],

    # Long
    "novel_length": ["novel length", "long fic", "epic"],
    "series": ["series", "multiple parts", "continuing"],
    "WIP": ["WIP", "work in progress", "ongoing"],
}

# ============================================================================
# CHAPTER STRUCTURE
# ============================================================================

CHAPTER_STRUCTURE = {
    # Structure types
    "episodic": ["episodic", "standalone chapters", "vignettes"],
    "continuous": ["continuous", "ongoing plot", "connected"],
    "time_jumps": ["time jumps", "years later", "flashback structure"],

    # Cliffhangers
    "cliffhanger_chapters": ["cliffhanger", "left hanging", "to be continued"],
    "resolved_chapters": ["resolved", "complete chapter", "wrapped up"],

    # Special chapters
    "prologue_epilogue": ["prologue", "epilogue", "bookends"],
    "interlude": ["interlude", "between chapters", "break"],
    "bonus_chapter": ["bonus", "extra", "additional"],
}

# ============================================================================
# DIALOGUE STYLE
# ============================================================================

DIALOGUE_STYLE = {
    # Amount
    "dialogue_heavy": ["dialogue heavy", "lots of talking", "conversation"],
    "minimal_dialogue": ["minimal dialogue", "action focused", "internal"],
    "balanced_dialogue": ["balanced", "mix of", "dialogue and prose"],

    # Style
    "witty_dialogue": ["witty dialogue", "clever", "fast-paced"],
    "realistic_dialogue": ["realistic", "natural", "like real people"],
    "stylized_dialogue": ["stylized", "distinctive", "unique voice"],

    # Accents/dialects
    "accent_written": ["accent written", "dialect", "phonetic"],
    "foreign_words": ["foreign words", "other language", "untranslated"],
    "slang_heavy": ["slang heavy", "colloquial", "casual"],
}

# ============================================================================
# SETTING DETAIL LEVEL
# ============================================================================

SETTING_DETAIL = {
    # High detail
    "richly_described": ["richly described", "detailed setting", "vivid"],
    "world_building": ["world building", "detailed universe", "fleshed out"],
    "sensory_setting": ["sensory details", "could picture", "immersive"],

    # Low detail
    "minimal_setting": ["minimal setting", "sparse", "bare bones"],
    "implied_setting": ["implied", "suggested", "reader fills in"],

    # Focus
    "setting_as_character": ["setting as character", "important to story", "central"],
    "setting_backdrop": ["backdrop only", "background", "not focus"],
}

# ============================================================================
# EMOTIONAL INTENSITY
# ============================================================================

EMOTIONAL_INTENSITY = {
    # High intensity
    "intense_emotions": ["intense emotions", "overwhelming feelings", "powerful"],
    "emotional_rollercoaster": ["rollercoaster", "ups and downs", "turbulent"],
    "crying_while_reading": ["made me cry", "emotional", "tears"],

    # Medium intensity
    "steady_emotions": ["steady emotions", "gradual", "building"],
    "warm_feelings": ["warm feelings", "pleasant", "nice"],

    # Low intensity
    "light_emotions": ["light emotions", "breezy", "not heavy"],
    "detached": ["detached", "observational", "distant"],
}

# ============================================================================
# SEXUAL TENSION TYPES
# ============================================================================

SEXUAL_TENSION_TYPES = {
    # Unresolved
    "unresolved_tension": ["unresolved tension", "UST", "will they"],
    "drawn_out_tension": ["drawn out", "prolonged", "torturous"],
    "almost_moments": ["almost moments", "so close", "interrupted"],

    # Resolved
    "tension_resolved": ["finally resolved", "got together", "paid off"],
    "explosive_resolution": ["explosive", "couldn't hold back", "dam broke"],
    "gradual_resolution": ["gradual", "slowly", "built to"],

    # Types
    "angry_tension": ["angry tension", "hate-want", "conflicted"],
    "sweet_tension": ["sweet tension", "longing", "pining"],
    "forbidden_tension": ["forbidden tension", "shouldn't want", "wrong but"],
}

# ============================================================================
# CHARACTER GROWTH
# ============================================================================

CHARACTER_GROWTH = {
    # Growth types
    "major_growth": ["major growth", "completely changed", "transformed"],
    "subtle_growth": ["subtle growth", "small changes", "gradual"],
    "static_characters": ["static", "didn't change", "same throughout"],

    # Direction
    "positive_growth": ["positive growth", "better person", "improved"],
    "regression": ["regression", "got worse", "backslid"],
    "complex_growth": ["complex", "not simple", "mixed changes"],

    # How shown
    "shown_growth": ["shown not told", "demonstrated", "actions showed"],
    "told_growth": ["told growth", "said changed", "narrated"],
}

# ============================================================================
# CONFLICT RESOLUTION
# ============================================================================

CONFLICT_RESOLUTION = {
    # Resolution types
    "communication_resolves": ["talked it out", "communication", "discussed"],
    "action_resolves": ["action resolved", "did something", "showed"],
    "time_resolves": ["time healed", "distance helped", "eventually"],
    "compromise_resolves": ["compromised", "met middle", "both gave"],

    # Unresolved
    "unresolved_conflict": ["unresolved", "didn't fix", "still there"],
    "open_ended": ["open ended", "reader decides", "ambiguous"],

    # External resolution
    "external_force": ["external force", "something happened", "circumstances"],
    "intervention": ["intervention", "someone helped", "third party"],
}

# ============================================================================
# SENSORY FOCUS
# ============================================================================

SENSORY_FOCUS = {
    # Primary sense
    "visual_focus": ["visual focus", "describing what saw", "imagery"],
    "tactile_focus": ["tactile focus", "touch descriptions", "feeling"],
    "auditory_focus": ["auditory focus", "sounds", "hearing"],
    "olfactory_focus": ["smell focus", "scents", "odors"],
    "taste_focus": ["taste focus", "flavors", "tasting"],

    # Sensory writing
    "multi_sensory": ["multi sensory", "all senses", "immersive"],
    "sparse_sensory": ["sparse sensory", "minimal description", "simple"],

    # Synesthesia
    "synesthetic": ["synesthetic", "mixed senses", "felt colors"],
}

# ============================================================================
# PACING TYPES
# ============================================================================

PACING_TYPES = {
    # Speed
    "fast_paced": ["fast paced", "quick", "action packed"],
    "slow_paced": ["slow paced", "leisurely", "takes time"],
    "varied_pacing": ["varied pacing", "speeds up slows down", "dynamic"],

    # Scene pacing
    "quick_scenes": ["quick scenes", "short", "rapid fire"],
    "long_scenes": ["long scenes", "extended", "drawn out"],
    "balanced_scenes": ["balanced scenes", "appropriate length", "well paced"],

    # Build up
    "gradual_build": ["gradual build", "slow burn", "building"],
    "immediate_action": ["immediate action", "starts fast", "no wait"],
}

# ============================================================================
# ENDINGS
# ============================================================================

ENDINGS = {
    # Happy
    "happy_ending_explicit": ["happy ending", "HEA", "happily ever after"],
    "hopeful_ending": ["hopeful ending", "positive future", "looking up"],
    "satisfying_ending": ["satisfying", "wrapped up", "complete"],

    # Sad
    "sad_ending": ["sad ending", "tragedy", "unhappy"],
    "bittersweet_ending": ["bittersweet", "happy and sad", "mixed"],
    "death_ending": ["character death", "dies", "loss"],

    # Ambiguous
    "ambiguous_ending": ["ambiguous", "open to interpretation", "unclear"],
    "open_ending": ["open ending", "continues", "more to come"],
    "reader_choice": ["reader decides", "your interpretation", "pick your ending"],
}

# ============================================================================
# READER EXPERIENCE
# ============================================================================

READER_EXPERIENCE = {
    # Emotional impact
    "heartwarming": ["heartwarming", "warm fuzzy", "feel good"],
    "heartbreaking": ["heartbreaking", "devastating", "destroyed me"],
    "cathartic": ["cathartic", "emotional release", "needed that"],

    # Physical reactions
    "hot_and_bothered": ["hot and bothered", "turned on", "fanning self"],
    "laughed_out_loud": ["laughed out loud", "funny", "hilarious"],
    "couldn't_put_down": ["couldn't put down", "binge read", "addictive"],

    # Recommendations
    "highly_recommend": ["highly recommend", "must read", "so good"],
    "niche_appeal": ["niche appeal", "specific taste", "not for everyone"],
    "comfort_reread": ["comfort reread", "read again", "go back to"],
}

# ============================================================================
# MILITARY/VETERAN SPECIFIC
# ============================================================================

MILITARY_ELEMENTS = {
    # Service
    "active_duty": ["active duty", "deployed", "on base"],
    "veteran": ["veteran", "served", "former military"],
    "special_forces": ["special forces", "seals", "rangers"],
    "basic_training": ["basic training", "boot camp", "recruit"],

    # Dynamics
    "rank_difference": ["rank difference", "officer and enlisted", "chain of command"],
    "battle_buddies": ["battle buddies", "served together", "brothers in arms"],
    "dont_ask_dont_tell": ["DADT", "don't ask don't tell", "before repeal"],

    # Trauma
    "combat_trauma": ["combat trauma", "war", "PTSD"],
    "survivor_guilt": ["survivor guilt", "didn't make it", "why me"],
    "adjustment": ["adjusting to civilian", "reintegration", "normal life"],

    # Specific elements
    "dog_tags": ["dog tags", "around neck", "metal"],
    "scars_military": ["battle scars", "shrapnel", "marks from service"],
    "uniform_kink": ["uniform kink", "dress uniform", "attraction to"],
}

# ============================================================================
# COLLEGE/UNIVERSITY SPECIFIC
# ============================================================================

COLLEGE_ELEMENTS = {
    # Setting
    "dorm_room": ["dorm room", "roommates", "college housing"],
    "frat_house": ["frat house", "greek life", "fraternity"],
    "campus_setting": ["campus", "quad", "university"],
    "library_college": ["library", "studying", "late night"],

    # Dynamics
    "student_student": ["fellow students", "classmates", "same year"],
    "professor_student": ["professor", "TA", "student"],
    "grad_student": ["grad student", "PhD", "masters"],

    # Events
    "college_party": ["college party", "kegger", "drunk"],
    "spring_break": ["spring break", "vacation", "wild"],
    "finals_stress": ["finals", "stressed", "need release"],
    "graduation": ["graduation", "ending", "next chapter"],

    # Tropes
    "experimenting": ["experimenting", "college is for", "trying things"],
    "first_time_away": ["first time away", "freedom", "no parents"],
    "study_partners": ["study partners", "project partners", "worked together"],
}

# ============================================================================
# HIGH SCHOOL (AGED UP)
# ============================================================================

HIGH_SCHOOL_AGED = {
    # Note: All characters 18+, senior year or aged up
    "senior_year": ["senior year", "18", "almost done"],
    "graduation_close": ["almost graduated", "weeks left", "ending"],

    # Settings
    "school_setting": ["school", "hallways", "lockers"],
    "after_school": ["after school", "empty school", "practice"],
    "prom_night": ["prom", "dance", "formal"],

    # Dynamics
    "jock_nerd": ["jock and nerd", "unlikely pair", "different crowds"],
    "popular_outcast": ["popular and outcast", "different social", "shouldn't work"],
    "rivals_school": ["rivals", "competing", "enemy"],

    # Experiences
    "first_relationship": ["first relationship", "never dated", "new to this"],
    "hiding_at_school": ["hiding", "secret at school", "no one knows"],
    "coming_out_school": ["coming out", "at school", "telling friends"],
}

# ============================================================================
# ROCK BAND/MUSICIAN
# ============================================================================

MUSICIAN_ELEMENTS = {
    # Roles
    "lead_singer": ["lead singer", "frontman", "voice"],
    "guitarist": ["guitarist", "lead guitar", "bass"],
    "drummer": ["drummer", "behind the kit", "rhythm"],
    "band_member": ["band member", "in band", "bandmates"],

    # Settings
    "tour_bus": ["tour bus", "on the road", "traveling"],
    "backstage": ["backstage", "green room", "after show"],
    "recording_studio": ["recording studio", "in studio", "making album"],
    "concert_venue": ["concert", "venue", "stage"],

    # Dynamics
    "bandmate_romance": ["bandmate", "in the band", "complicated"],
    "fan_musician": ["fan", "meet and greet", "dream come true"],
    "roadie_musician": ["roadie", "crew", "touring together"],

    # Lifestyle
    "fame": ["fame", "famous", "recognized"],
    "groupies": ["groupies", "fans wanting", "easy access"],
    "drugs_rockstar": ["party lifestyle", "excess", "rock and roll"],
}

# ============================================================================
# SPORTS SPECIFIC
# ============================================================================

SPORTS_SPECIFIC = {
    # Team sports
    "football_team": ["football", "quarterback", "locker room"],
    "basketball_team": ["basketball", "court", "teammates"],
    "baseball_team": ["baseball", "dugout", "teammates"],
    "hockey_team": ["hockey", "rink", "teammates"],
    "soccer_team": ["soccer", "pitch", "teammates"],
    "swimming_team": ["swimming", "pool", "speedo"],
    "wrestling_team": ["wrestling", "mat", "singlet"],

    # Individual sports
    "boxing": ["boxing", "ring", "fighter"],
    "mma": ["MMA", "cage", "fighter"],
    "gymnastics": ["gymnastics", "flexible", "athlete"],

    # Dynamics
    "teammates": ["teammates", "team bonding", "locker room"],
    "coach_player": ["coach", "player", "dynamic"],
    "rival_teams": ["rival teams", "competition", "enemy team"],

    # Settings
    "locker_room_setting": ["locker room", "showers", "after practice"],
    "team_travel": ["team travel", "hotel", "road game"],
    "celebration": ["won the game", "celebration", "victory"],
}

# ============================================================================
# MEDICAL PROFESSIONAL
# ============================================================================

MEDICAL_PROFESSIONAL = {
    # Roles
    "doctor": ["doctor", "physician", "MD"],
    "nurse": ["nurse", "RN", "nursing"],
    "surgeon": ["surgeon", "operating room", "OR"],
    "paramedic": ["paramedic", "EMT", "ambulance"],
    "therapist": ["therapist", "counselor", "mental health"],

    # Settings
    "hospital": ["hospital", "medical center", "ward"],
    "clinic": ["clinic", "office", "practice"],
    "on_call_room": ["on call room", "between shifts", "hospital bed"],
    "ambulance_setting": ["ambulance", "back of rig", "calls"],

    # Dynamics
    "colleague_romance": ["colleague", "coworker", "work together"],
    "doctor_patient": ["doctor patient", "treated by", "relationship after"],
    "long_shifts": ["long shifts", "exhausted", "only each other"],

    # Elements
    "saving_lives": ["saving lives", "hero", "dramatic"],
    "stress_relief": ["stress relief", "after shift", "need release"],
    "scrubs": ["scrubs", "uniform", "easy access"],
}

# ============================================================================
# LAW ENFORCEMENT
# ============================================================================

LAW_ENFORCEMENT = {
    # Roles
    "police_officer": ["police officer", "cop", "officer"],
    "detective": ["detective", "investigator", "badge"],
    "FBI_agent": ["FBI", "agent", "federal"],
    "sheriff": ["sheriff", "small town", "law"],

    # Settings
    "police_station": ["police station", "precinct", "station"],
    "patrol_car": ["patrol car", "cruiser", "squad car"],
    "interrogation": ["interrogation room", "questioning", "interview"],
    "crime_scene": ["crime scene", "investigation", "evidence"],

    # Dynamics
    "partner_cops": ["partners", "ride together", "have back"],
    "cop_criminal": ["cop and criminal", "wrong side", "shouldn't"],
    "undercover": ["undercover", "cover", "pretending"],

    # Elements
    "handcuffs_professional": ["handcuffs", "cuffing", "restraining"],
    "uniform_cop": ["uniform", "badge", "gun"],
    "power_authority": ["authority", "power", "command"],
}

# ============================================================================
# FIREFIGHTER
# ============================================================================

FIREFIGHTER_ELEMENTS = {
    # Roles
    "firefighter": ["firefighter", "fireman", "smoke eater"],
    "fire_captain": ["captain", "in charge", "leader"],
    "probie": ["probie", "probationary", "new guy"],

    # Settings
    "firehouse": ["firehouse", "station", "living quarters"],
    "fire_scene": ["fire scene", "burning building", "rescue"],
    "bunks": ["bunks", "sleeping quarters", "station beds"],

    # Dynamics
    "firehouse_family": ["firehouse family", "brothers", "crew"],
    "rescue_romance": ["rescued", "saved by", "hero"],
    "shift_together": ["shift together", "24 hours", "long shifts"],

    # Elements
    "gear": ["turnout gear", "helmet", "boots"],
    "physical_demanding": ["physical", "strength", "carrying"],
    "adrenaline": ["adrenaline", "rush", "after call"],
}

# ============================================================================
# CHEF/RESTAURANT
# ============================================================================

CHEF_ELEMENTS = {
    # Roles
    "head_chef": ["head chef", "executive chef", "in charge"],
    "sous_chef": ["sous chef", "second in command", "assisting"],
    "line_cook": ["line cook", "cooking", "station"],
    "server": ["server", "waiter", "front of house"],

    # Settings
    "kitchen_setting": ["kitchen", "back of house", "hot"],
    "walk_in": ["walk in", "cooler", "cold storage"],
    "restaurant_after_hours": ["after hours", "closed", "empty restaurant"],

    # Dynamics
    "kitchen_hierarchy": ["hierarchy", "yes chef", "chain of command"],
    "kitchen_romance": ["kitchen romance", "coworkers", "hot environment"],
    "customer_chef": ["customer", "regular", "meeting chef"],

    # Elements
    "food_sensuality": ["food as sensual", "feeding", "tasting"],
    "knife_skills": ["knife skills", "hands", "precise"],
    "late_nights": ["late nights", "restaurant hours", "closing"],
}

# ============================================================================
# TATTOO ARTIST
# ============================================================================

TATTOO_ARTIST_ELEMENTS = {
    # Roles
    "tattoo_artist": ["tattoo artist", "tattooist", "ink"],
    "apprentice": ["apprentice", "learning", "new"],
    "shop_owner": ["shop owner", "owns the shop", "boss"],

    # Settings
    "tattoo_shop": ["tattoo shop", "parlor", "studio"],
    "private_session": ["private session", "after hours", "alone"],

    # Dynamic
    "artist_client": ["artist and client", "tattooing", "in chair"],
    "intimacy_of_tattooing": ["intimate", "touching", "permanent"],
    "designing_tattoo": ["designing", "custom", "meaningful"],

    # Elements
    "pain_pleasure_tattoo": ["pain", "endorphins", "high"],
    "trust_tattoo": ["trust", "permanent", "on body forever"],
    "covered_in_tattoos": ["covered", "sleeves", "heavily tattooed"],
}

# ============================================================================
# BARTENDER
# ============================================================================

BARTENDER_ELEMENTS = {
    # Role
    "bartender": ["bartender", "behind the bar", "mixing drinks"],
    "bar_owner": ["bar owner", "owns the place", "boss"],
    "regular_customer": ["regular", "always here", "usual"],

    # Settings
    "dive_bar_setting": ["dive bar", "local", "neighborhood"],
    "cocktail_bar": ["cocktail bar", "fancy", "upscale"],
    "after_hours_bar": ["after hours", "closed", "lock in"],

    # Dynamics
    "bartender_customer": ["bartender and customer", "flirting over bar", "drinks"],
    "listening_bartender": ["listened", "therapist", "heard everything"],
    "last_call": ["last call", "closing time", "end of night"],

    # Elements
    "making_drinks": ["making drinks", "skilled hands", "craft"],
    "bar_atmosphere": ["bar atmosphere", "music", "dim lighting"],
    "drunk_confessions": ["drunk confessions", "liquid courage", "told you"],
}

# ============================================================================
# CONSTRUCTION/TRADES
# ============================================================================

TRADES_ELEMENTS = {
    # Roles
    "construction_worker": ["construction worker", "builder", "site"],
    "plumber": ["plumber", "fix pipes", "house call"],
    "electrician": ["electrician", "wiring", "power"],
    "carpenter": ["carpenter", "woodwork", "building"],
    "mechanic": ["mechanic", "fix cars", "garage"],

    # Settings
    "construction_site": ["construction site", "building", "scaffolding"],
    "workshop": ["workshop", "garage", "tools"],
    "house_call": ["house call", "service call", "your place"],

    # Elements
    "blue_collar": ["blue collar", "working class", "trades"],
    "dirty_from_work": ["dirty", "sweaty", "worked all day"],
    "strong_hands": ["strong hands", "calloused", "capable"],
    "tool_belt": ["tool belt", "tools", "hanging low"],
}

# ============================================================================
# TECH/PROGRAMMER
# ============================================================================

TECH_ELEMENTS = {
    # Roles
    "programmer": ["programmer", "developer", "coder"],
    "startup_founder": ["startup", "founder", "entrepreneur"],
    "it_support": ["IT support", "tech support", "fixing"],
    "hacker": ["hacker", "security", "breaking in"],

    # Settings
    "office_tech": ["office", "cubicle", "desk"],
    "home_office": ["home office", "remote", "WFH"],
    "server_room": ["server room", "data center", "cold"],

    # Elements
    "nerd_hot": ["nerd hot", "smart is sexy", "glasses"],
    "late_night_coding": ["late night", "deadline", "all nighter"],
    "online_connection": ["met online", "gaming", "digital"],
}

# ============================================================================
# LAWYER
# ============================================================================

LAWYER_ELEMENTS = {
    # Roles
    "lawyer": ["lawyer", "attorney", "counsel"],
    "prosecutor": ["prosecutor", "DA", "state"],
    "defense_attorney": ["defense", "defending", "criminal law"],
    "paralegal": ["paralegal", "assistant", "law office"],

    # Settings
    "law_firm": ["law firm", "office", "partners"],
    "courtroom": ["courtroom", "trial", "bench"],
    "chambers": ["chambers", "judge's office", "private"],

    # Dynamics
    "opposing_counsel": ["opposing counsel", "other side", "enemy lawyer"],
    "lawyer_client": ["lawyer client", "representing", "case"],
    "partners_firm": ["firm partners", "colleagues", "same firm"],

    # Elements
    "suits": ["suits", "well dressed", "professional"],
    "power_talk": ["power", "commanding", "authoritative"],
    "billable_hours": ["billable hours", "no time", "deadline"],
}

# ============================================================================
# PILOT/FLIGHT
# ============================================================================

PILOT_ELEMENTS = {
    # Roles
    "commercial_pilot": ["pilot", "captain", "flying"],
    "military_pilot": ["military pilot", "fighter", "air force"],
    "flight_attendant": ["flight attendant", "cabin crew", "service"],

    # Settings
    "cockpit": ["cockpit", "flight deck", "controls"],
    "plane_cabin": ["cabin", "plane", "airplane"],
    "layover_hotel": ["layover", "hotel", "overnight"],

    # Dynamics
    "pilot_attendant": ["pilot and attendant", "crew", "flight together"],
    "mile_high": ["mile high", "airplane bathroom", "altitude"],
    "layover_hook_up": ["layover", "foreign city", "one night"],

    # Elements
    "uniform_pilot": ["uniform", "wings", "hat"],
    "exotic_locations": ["exotic locations", "travel", "everywhere"],
    "jet_lag": ["jet lag", "exhausted", "time zones"],
}

# ============================================================================
# ARTIST/CREATIVE
# ============================================================================

ARTIST_ELEMENTS = {
    # Roles
    "painter": ["painter", "artist", "canvas"],
    "sculptor": ["sculptor", "sculpture", "clay"],
    "photographer_artist": ["photographer", "shoot", "camera"],
    "writer_creative": ["writer", "author", "words"],

    # Settings
    "art_studio": ["studio", "art space", "creating"],
    "gallery": ["gallery", "exhibition", "showing"],
    "model_session": ["model session", "posing", "being painted"],

    # Dynamics
    "artist_muse": ["muse", "inspiration", "draw you"],
    "artist_model": ["artist and model", "posing", "nude modeling"],
    "creative_partnership": ["creative partnership", "collaborating", "together"],

    # Elements
    "artistic_eye": ["artistic eye", "seeing beauty", "noticing details"],
    "messy_creative": ["paint splattered", "messy", "creative mess"],
    "tortured_artist": ["tortured artist", "emotional", "creating"],
}

# ============================================================================
# ROYALTY/ARISTOCRACY
# ============================================================================

ROYALTY_ELEMENTS = {
    # Roles
    "prince": ["prince", "heir", "royal"],
    "king": ["king", "ruler", "crown"],
    "lord_noble": ["lord", "duke", "earl"],
    "commoner": ["commoner", "not noble", "regular person"],

    # Settings
    "palace": ["palace", "castle", "royal residence"],
    "throne_room": ["throne room", "court", "formal"],
    "royal_chambers": ["royal chambers", "bedchamber", "private"],

    # Dynamics
    "forbidden_noble": ["forbidden", "can't be together", "class divide"],
    "arranged_royal": ["arranged", "duty", "for the kingdom"],
    "secret_royal": ["secret", "hidden", "no one can know"],

    # Elements
    "duty_vs_love": ["duty vs love", "obligation", "what I want"],
    "scandal": ["scandal", "reputation", "cannot be seen"],
    "crowns_and_jewels": ["crown", "jewels", "finery"],
}

# ============================================================================
# SUPERNATURAL BEING TYPES
# ============================================================================

SUPERNATURAL_BEINGS = {
    # Vampires
    "vampire": ["vampire", "blood", "immortal"],
    "turning_vampire": ["turning", "making", "becoming vampire"],
    "blood_drinking": ["drinking blood", "biting neck", "feeding"],
    "vampire_powers": ["vampire powers", "strength", "speed"],

    # Werewolves
    "werewolf": ["werewolf", "wolf", "shift"],
    "pack_dynamics": ["pack", "alpha", "beta"],
    "mating_bond": ["mate bond", "destined", "fated"],
    "full_moon": ["full moon", "shift", "can't control"],

    # Witches/Mages
    "witch_warlock": ["witch", "warlock", "magic user"],
    "spells": ["spells", "magic", "casting"],
    "familiar": ["familiar", "bonded", "magical companion"],

    # Angels/Demons
    "angel": ["angel", "wings", "heaven"],
    "demon": ["demon", "hell", "infernal"],
    "fallen_angel": ["fallen", "cast out", "neither"],

    # Fae
    "fae_sidhe": ["fae", "fairy", "sidhe"],
    "faerie_court": ["court", "seelie", "unseelie"],
    "glamour": ["glamour", "illusion", "hiding"],

    # Ghosts
    "ghost": ["ghost", "spirit", "haunting"],
    "possession": ["possession", "took over", "inside"],
}

# ============================================================================
# SHIFTER SPECIFIC
# ============================================================================

SHIFTER_ELEMENTS = {
    # Types
    "wolf_shifter": ["wolf shifter", "werewolf", "pack"],
    "cat_shifter": ["cat shifter", "lion", "panther"],
    "bear_shifter": ["bear shifter", "werebear", "clan"],
    "dragon_shifter": ["dragon shifter", "dragon", "hoard"],

    # Dynamics
    "mate_recognition": ["recognized mate", "knew instantly", "scented"],
    "marking_bite": ["marking bite", "claimed", "permanent"],
    "heat_cycle": ["heat", "cycle", "need to mate"],
    "pack_hierarchy": ["pack hierarchy", "alpha", "submit"],

    # Shifting
    "shifting_painful": ["painful shift", "bones breaking", "transformation"],
    "shifting_pleasurable": ["pleasurable shift", "feels good", "freeing"],
    "stuck_in_shift": ["stuck", "can't shift back", "trapped"],
    "partial_shift": ["partial shift", "claws", "eyes only"],

    # Mating
    "mating_frenzy": ["mating frenzy", "can't control", "need"],
    "claiming": ["claiming", "mine", "marked"],
    "rejection": ["rejection", "refused mate", "pain"],
}

# ============================================================================
# SPACE/SCI-FI
# ============================================================================

SPACE_SCIFI = {
    # Settings
    "spaceship": ["spaceship", "vessel", "craft"],
    "space_station": ["space station", "orbital", "station"],
    "alien_planet": ["alien planet", "different world", "not earth"],
    "colony": ["colony", "settlement", "new world"],

    # Roles
    "captain_space": ["captain", "commander", "in charge"],
    "crew_member": ["crew", "aboard", "serving"],
    "alien": ["alien", "not human", "different species"],

    # Elements
    "zero_gravity": ["zero gravity", "floating", "weightless"],
    "close_quarters_space": ["close quarters", "cramped", "small ship"],
    "long_voyage": ["long voyage", "years", "journey"],
    "first_contact": ["first contact", "meeting aliens", "new species"],

    # Dynamics
    "captain_crew": ["captain and crew", "chain of command", "fraternization"],
    "human_alien": ["human and alien", "interspecies", "different"],
    "sole_survivors": ["sole survivors", "only ones left", "together"],
}

# ============================================================================
# HISTORICAL PERIODS
# ============================================================================

HISTORICAL_PERIODS = {
    # Ancient
    "ancient_rome": ["ancient rome", "roman", "empire"],
    "ancient_greece": ["ancient greece", "greek", "sparta"],
    "ancient_egypt": ["ancient egypt", "pharaoh", "nile"],

    # Medieval
    "medieval": ["medieval", "middle ages", "castle"],
    "viking": ["viking", "norse", "raid"],
    "knight": ["knight", "armor", "sword"],

    # Regency/Victorian
    "regency": ["regency", "1800s", "balls"],
    "victorian": ["victorian", "proper", "corset"],
    "gilded_age": ["gilded age", "wealth", "society"],

    # 20th Century
    "roaring_twenties": ["roaring twenties", "1920s", "jazz"],
    "world_war": ["world war", "war time", "soldier"],
    "fifties_sixties": ["1950s", "1960s", "mid century"],
    "seventies_disco": ["disco", "1970s", "dance"],
    "eighties_nineties": ["1980s", "1990s", "recent past"],
}

# ============================================================================
# NON-CONSENT: INITIAL REALIZATION
# ============================================================================

NC_INITIAL_REALIZATION = {
    # The moment of understanding
    "moment_of_realization": ["realized what was", "understood what", "knew then"],
    "dawning_horror": ["dawning horror", "slowly realized", "creeping understanding"],
    "sudden_clarity": ["suddenly knew", "hit me", "clarity"],
    "denial_at_first": ["couldn't be", "not happening", "this isn't"],
    "disbelief": ["disbelief", "couldn't believe", "not real"],

    # Mental scrambling
    "trying_to_process": ["trying to process", "couldn't compute", "brain refusing"],
    "thoughts_racing": ["thoughts racing", "mind spinning", "couldn't think straight"],
    "mental_shutdown": ["mind went blank", "thoughts stopped", "couldn't process"],
    "confusion": ["confused", "didn't understand", "why is this"],

    # Wrong signals
    "misread_situation": ["misread", "thought it was", "didn't see coming"],
    "trusted_wrong_person": ["trusted", "thought safe", "believed"],
    "ignored_warning_signs": ["ignored signs", "should have known", "missed red flags"],
    "too_late_to_realize": ["too late", "already happening", "couldn't stop"],
}

# ============================================================================
# NON-CONSENT: FREEZE RESPONSE
# ============================================================================

NC_FREEZE_RESPONSE = {
    # Physical freezing
    "body_went_rigid": ["went rigid", "froze", "couldn't move"],
    "paralyzed": ["paralyzed", "frozen in place", "body wouldn't respond"],
    "muscles_locked": ["muscles locked", "seized up", "stiff"],
    "couldnt_move": ["couldn't move", "tried but couldn't", "body wouldn't listen"],
    "rooted_in_place": ["rooted", "stuck", "feet wouldn't move"],

    # Mental freeze
    "mind_went_blank": ["mind blank", "thoughts stopped", "empty"],
    "couldnt_think": ["couldn't think", "brain stopped", "frozen mind"],
    "time_stopped": ["time stopped", "moment stretched", "eternal second"],
    "watching_from_outside": ["watching from outside", "not in body", "observer"],

    # Inability to respond
    "couldnt_speak": ["couldn't speak", "voice gone", "words stuck"],
    "couldnt_scream": ["couldn't scream", "tried to scream", "nothing came out"],
    "mouth_wouldnt_work": ["mouth wouldn't", "tried to say", "lips wouldn't move"],
    "voice_trapped": ["voice trapped", "screaming inside", "silent outside"],

    # Automatic compliance
    "body_moved_automatically": ["moved automatically", "went through motions", "autopilot"],
    "did_what_told": ["did what told", "obeyed without thinking", "automatic"],
    "compliance_without_consent": ["complied", "didn't resist", "just let"],
}

# ============================================================================
# NON-CONSENT: FIGHT RESPONSE (SUPPRESSED)
# ============================================================================

NC_FIGHT_SUPPRESSED = {
    # Wanting to fight
    "wanted_to_fight": ["wanted to fight", "rage inside", "wanted to hurt"],
    "imagined_fighting": ["imagined fighting", "saw myself", "in my head"],
    "screaming_inside": ["screaming inside", "internal fight", "raging within"],

    # Why couldn't
    "too_strong": ["too strong", "overpowered", "couldn't match"],
    "physically_restrained": ["restrained", "held down", "couldn't move"],
    "threat_of_worse": ["threat of worse", "would hurt more", "promised pain"],
    "protecting_someone": ["protecting someone", "they'd hurt", "for them"],
    "weapon_present": ["weapon", "knife", "gun", "could kill"],

    # Attempts that failed
    "tried_to_push_away": ["tried to push", "pushed but", "hands on chest"],
    "tried_to_kick": ["tried to kick", "legs pinned", "couldn't reach"],
    "tried_to_bite": ["tried to bite", "mouth covered", "head held"],
    "struggled_until": ["struggled until", "exhausted from fighting", "gave up"],

    # Giving up fight
    "stopped_fighting": ["stopped fighting", "no point", "couldn't win"],
    "conserving_energy": ["conserved energy", "stopped wasting", "survival mode"],
    "accepting_inevitable": ["accepted", "couldn't stop", "let it happen"],
}

# ============================================================================
# NON-CONSENT: FLIGHT RESPONSE (BLOCKED)
# ============================================================================

NC_FLIGHT_BLOCKED = {
    # Wanting to flee
    "desperate_to_escape": ["desperate to escape", "needed to run", "get away"],
    "looking_for_exit": ["looking for exit", "scanning room", "where can I"],
    "calculating_escape": ["calculating", "if I could just", "maybe if"],

    # Blocked escape
    "door_locked": ["door locked", "no way out", "trapped"],
    "physically_blocked": ["blocked exit", "standing in way", "couldn't get past"],
    "held_in_place": ["held in place", "grip too tight", "couldn't break free"],
    "nowhere_to_go": ["nowhere to go", "no escape", "surrounded"],

    # Failed attempts
    "tried_to_run": ["tried to run", "almost made it", "caught"],
    "dragged_back": ["dragged back", "pulled back", "caught trying"],
    "punished_for_trying": ["punished for trying", "made it worse", "shouldn't have"],

    # Mental escape
    "mentally_fleeing": ["mentally fled", "went somewhere else", "not here"],
    "imagining_escape": ["imagined escaping", "pretended away", "fantasy of running"],
    "planning_after": ["planning after", "when this is over", "I'll run then"],
}

# ============================================================================
# NON-CONSENT: DISSOCIATION
# ============================================================================

NC_DISSOCIATION = {
    # Leaving body
    "left_body": ["left body", "floated away", "wasn't in body"],
    "watching_from_ceiling": ["watching from ceiling", "above looking down", "saw myself"],
    "watching_from_corner": ["watching from corner", "outside self", "observer"],
    "not_me": ["not me", "someone else", "happening to other"],

    # Detachment
    "felt_nothing": ["felt nothing", "numb", "couldn't feel"],
    "emotionally_detached": ["detached", "disconnected", "separate"],
    "like_a_dream": ["like a dream", "not real", "dreaming"],
    "foggy": ["foggy", "hazy", "unclear"],

    # Time distortion
    "time_meaningless": ["time meaningless", "could have been", "no sense of"],
    "felt_like_hours": ["felt like hours", "endless", "forever"],
    "felt_like_seconds": ["felt like seconds", "over quick", "blink"],
    "lost_time": ["lost time", "don't remember", "gaps"],

    # Going somewhere else mentally
    "went_somewhere_safe": ["went somewhere safe", "happy place", "memory"],
    "counted_things": ["counted things", "ceiling tiles", "focused elsewhere"],
    "recited_something": ["recited", "song lyrics", "anything else"],
    "made_self_not_there": ["made self not there", "wasn't present", "gone inside"],
}

# ============================================================================
# NON-CONSENT: BODY RESPONSES (UNWANTED)
# ============================================================================

NC_BODY_BETRAYAL = {
    # Physical arousal despite
    "body_responded": ["body responded", "despite everything", "didn't want to"],
    "unwanted_arousal": ["unwanted arousal", "body betrayed", "didn't mean"],
    "erection_without_consent": ["got hard", "body reacted", "physical response"],
    "physical_pleasure_unwanted": ["felt pleasure", "body felt good", "hated that"],

    # Confusion about response
    "confused_by_response": ["confused", "why is body", "doesn't mean"],
    "shame_at_response": ["shame", "ashamed of body", "shouldn't respond"],
    "guilt_about_pleasure": ["guilt", "felt good and hated", "wrong to feel"],
    "body_vs_mind": ["body vs mind", "mind said no", "body said yes"],

    # Orgasm without consent
    "forced_orgasm": ["forced orgasm", "made to come", "couldn't stop"],
    "orgasm_as_weapon": ["used orgasm against", "see you liked", "proof"],
    "crying_while_coming": ["crying while", "came and cried", "both at once"],
    "hatred_at_climax": ["hated self for", "came and hated", "body's betrayal"],

    # Other physical responses
    "tears_flowing": ["tears", "couldn't stop crying", "wet face"],
    "shaking_uncontrollably": ["shaking", "trembling", "couldn't stop"],
    "nausea": ["nausea", "sick feeling", "wanted to vomit"],
    "hyperventilating": ["hyperventilating", "couldn't breathe right", "gasping"],
}

# ============================================================================
# NON-CONSENT: INTERNAL MONOLOGUE
# ============================================================================

NC_INTERNAL_THOUGHTS = {
    # During
    "just_let_it_end": ["just let it end", "be over soon", "almost done"],
    "please_stop": ["please stop", "stop stop stop", "make it stop"],
    "why_me": ["why me", "what did I do", "why is this"],
    "this_isnt_happening": ["this isn't happening", "not real", "wake up"],
    "survive_this": ["survive this", "just survive", "get through"],

    # Bargaining
    "if_i_just": ["if I just", "maybe if I", "if I do this"],
    "ill_do_anything": ["I'll do anything", "just stop", "please"],
    "bargaining_with_god": ["bargaining with god", "praying", "please god"],
    "promising_anything": ["promising anything", "I'll never", "just let me"],

    # Self-blame thoughts
    "my_fault": ["my fault", "I caused", "I let this"],
    "should_have_known": ["should have known", "stupid", "should have seen"],
    "shouldnt_have": ["shouldn't have", "if only I hadn't", "my mistake"],
    "deserve_this": ["deserve this", "punishment", "earned this"],

    # Survival thoughts
    "stay_alive": ["stay alive", "survive", "don't die"],
    "remember_everything": ["remember everything", "for later", "evidence"],
    "stay_quiet": ["stay quiet", "don't provoke", "careful"],
    "just_cooperate": ["just cooperate", "don't fight", "safer to"],
}

# ============================================================================
# NON-CONSENT: PERPETRATOR TACTICS
# ============================================================================

NC_PERPETRATOR_TACTICS = {
    # Physical control
    "physical_overpowering": ["overpowered", "stronger", "couldn't match"],
    "pinned_down": ["pinned", "held down", "weight on"],
    "restraining": ["restrained", "tied", "couldn't move"],
    "covering_mouth": ["covered mouth", "silenced", "couldn't scream"],

    # Threats
    "verbal_threats": ["threatened", "said would", "promised to hurt"],
    "threat_to_others": ["threaten others", "hurt your", "tell your"],
    "threat_of_death": ["kill you", "death threat", "won't survive"],
    "threat_of_exposure": ["tell everyone", "show them", "everyone will know"],

    # Manipulation during
    "gaslighting_during": ["you want this", "you asked for", "you like it"],
    "claiming_relationship": ["you're mine", "belong to me", "owe me"],
    "rewriting_reality": ["this is normal", "everyone does", "not a big deal"],
    "blaming_victim": ["you made me", "your fault", "you did this"],

    # Control tactics
    "isolation": ["no one around", "no one will hear", "alone"],
    "using_substances": ["drugged", "drunk", "incapacitated"],
    "using_authority": ["position of power", "authority", "can't refuse"],
    "economic_coercion": ["need this job", "pay your", "dependent"],
}

# ============================================================================
# NON-CONSENT: TYPES OF SCENARIOS
# ============================================================================

NC_SCENARIO_TYPES = {
    # Relationship context
    "intimate_partner": ["partner", "boyfriend", "husband"],
    "date_situation": ["date", "thought it was", "after dinner"],
    "ex_partner": ["ex", "former", "used to be with"],

    # Authority figures
    "boss_workplace": ["boss", "workplace", "superior"],
    "teacher_coach": ["teacher", "coach", "mentor"],
    "religious_figure": ["priest", "pastor", "religious leader"],
    "medical_professional": ["doctor", "therapist", "trusted professional"],

    # Social context
    "family_member": ["family", "relative", "should have been safe"],
    "friend": ["friend", "trusted", "known for years"],
    "acquaintance": ["acquaintance", "knew of", "not stranger"],
    "stranger": ["stranger", "didn't know", "random"],

    # Situation types
    "party_situation": ["party", "social gathering", "drinking"],
    "home_invasion": ["home invasion", "broke in", "my space"],
    "kidnapping": ["kidnapped", "taken", "abducted"],
    "institutional": ["institution", "prison", "facility"],
}

# ============================================================================
# NON-CONSENT: DURING - SENSORY DETAILS
# ============================================================================

NC_SENSORY_DURING = {
    # What was felt
    "pain_during": ["pain", "it hurt", "burning", "tearing"],
    "pressure": ["pressure", "weight", "heaviness"],
    "intrusion": ["intrusion", "invasion", "inside without"],
    "roughness": ["rough", "not gentle", "harsh"],

    # What was heard
    "their_voice": ["their voice", "saying things", "words"],
    "own_crying": ["own crying", "heard self", "sobbing"],
    "silence_deafening": ["silence", "quiet", "no one coming"],
    "sounds_of_act": ["sounds", "noises", "sickening sounds"],

    # What was smelled
    "their_smell": ["their smell", "breath", "body odor"],
    "alcohol_breath": ["alcohol breath", "drunk smell", "booze"],
    "sweat_smell": ["sweat", "body smell", "musk"],

    # What was seen
    "their_face": ["their face", "looking at me", "expression"],
    "ceiling": ["ceiling", "stared at ceiling", "looked up"],
    "darkness": ["darkness", "couldn't see", "dark"],
    "clock": ["clock", "watched time", "counting minutes"],

    # What was tasted
    "blood_taste": ["blood", "bit lip", "metallic"],
    "tears_taste": ["tears", "salt", "own tears"],
    "them_taste": ["their taste", "in mouth", "forced"],
}

# ============================================================================
# NON-CONSENT: SPECIFIC PHYSICAL EXPERIENCES
# ============================================================================

NC_PHYSICAL_EXPERIENCE = {
    # Penetration without consent
    "unprepared_penetration": ["unprepared", "no preparation", "not ready"],
    "no_lubrication": ["no lube", "dry", "friction burn"],
    "forced_entry": ["forced in", "pushed in", "made to take"],
    "too_fast": ["too fast", "no adjustment", "immediate"],
    "too_rough": ["too rough", "violent", "brutal"],
    "too_deep": ["too deep", "hitting inside", "couldn't take"],

    # Physical damage
    "tearing": ["tearing", "ripping", "damage"],
    "bleeding": ["bleeding", "blood", "saw blood"],
    "bruising": ["bruising", "grip marks", "fingerprints"],
    "soreness_during": ["sore", "aching", "raw"],

    # Restraint marks
    "wrist_damage": ["wrist damage", "rope burn", "marks on wrists"],
    "held_too_tight": ["held too tight", "crushing grip", "couldn't breathe"],
    "position_pain": ["position hurt", "bent wrong", "joints aching"],

    # Other physical
    "gagging": ["gagging", "couldn't breathe", "choking"],
    "suffocation_feelings": ["suffocating", "couldn't get air", "smothered"],
    "temperature": ["cold", "hot", "temperature wrong"],
}

# ============================================================================
# NON-CONSENT: AFTERMATH - IMMEDIATE
# ============================================================================

NC_AFTERMATH_IMMEDIATE = {
    # Physical state after
    "collapsed": ["collapsed", "couldn't stand", "fell"],
    "shaking_after": ["shaking after", "trembling", "couldn't stop"],
    "couldnt_move_after": ["couldn't move", "stayed still", "paralyzed still"],
    "curled_up": ["curled up", "fetal position", "made small"],

    # Immediate emotional
    "shock_after": ["shock", "stunned", "not processing"],
    "numbness_after": ["numb", "couldn't feel", "empty"],
    "crying_after": ["crying", "sobbing", "tears"],
    "silent_after": ["silent", "couldn't speak", "no words"],

    # Physical needs after
    "need_to_wash": ["need to wash", "dirty", "get it off"],
    "compulsive_cleaning": ["scrubbed", "cleaned obsessively", "never clean enough"],
    "checking_body": ["checking body", "damage", "what's wrong"],
    "pain_inventory": ["cataloging pain", "where it hurts", "assessing"],

    # Immediate thoughts
    "what_now": ["what now", "what do I do", "how do I"],
    "tell_someone": ["should I tell", "who do I tell", "can I tell"],
    "hide_it": ["hide it", "no one knows", "can't tell"],
    "pretend_normal": ["pretend normal", "act like", "nothing happened"],
}

# ============================================================================
# NON-CONSENT: AFTERMATH - LONG TERM
# ============================================================================

NC_AFTERMATH_LONGTERM = {
    # PTSD symptoms
    "flashbacks": ["flashbacks", "suddenly back there", "reliving"],
    "nightmares": ["nightmares", "dreams about", "can't sleep"],
    "triggers": ["triggered", "something reminded", "set off"],
    "hypervigilance": ["hypervigilant", "always watching", "can't relax"],
    "startle_response": ["startle easily", "jumpy", "on edge"],

    # Avoidance
    "avoiding_places": ["avoiding places", "can't go there", "won't go near"],
    "avoiding_people": ["avoiding people", "can't be around", "isolating"],
    "avoiding_intimacy": ["avoiding intimacy", "can't be touched", "no sex"],
    "avoiding_thoughts": ["avoiding thoughts", "don't think about", "push away"],

    # Emotional aftermath
    "depression": ["depression", "can't function", "no point"],
    "anxiety": ["anxiety", "constant fear", "panic"],
    "anger": ["anger", "rage", "furious"],
    "shame_longterm": ["shame", "dirty", "ruined"],
    "guilt_longterm": ["guilt", "my fault", "should have"],

    # Impact on life
    "trust_destroyed": ["can't trust", "trust broken", "everyone suspect"],
    "relationship_difficulty": ["relationship difficulty", "can't connect", "push away"],
    "intimacy_problems": ["intimacy problems", "can't be intimate", "flashbacks during"],
    "self_worth_destroyed": ["worthless", "damaged goods", "broken"],
}

# ============================================================================
# NON-CONSENT: COPING MECHANISMS
# ============================================================================

NC_COPING = {
    # Unhealthy coping
    "substance_use": ["drinking", "drugs", "numbing"],
    "self_harm": ["self harm", "hurting self", "punishment"],
    "risky_behavior": ["risky behavior", "don't care", "reckless"],
    "isolation_coping": ["isolation", "withdraw", "alone"],
    "overworking": ["overworking", "staying busy", "don't think"],

    # Attempts at control
    "controlling_everything": ["controlling", "need control", "order"],
    "obsessive_behavior": ["obsessive", "rituals", "have to"],
    "perfectionism": ["perfectionism", "nothing wrong", "perfect"],
    "hyperindependence": ["hyperindependent", "need no one", "only self"],

    # Healthy coping
    "therapy": ["therapy", "counseling", "talking to professional"],
    "support_groups": ["support group", "others like me", "not alone"],
    "trusted_person": ["told someone", "trusted person", "support"],
    "journaling": ["journaling", "writing it out", "processing"],

    # Reclaiming
    "reclaiming_body": ["reclaiming body", "my body again", "taking back"],
    "reclaiming_sexuality": ["reclaiming sexuality", "on my terms", "choosing"],
    "reclaiming_power": ["reclaiming power", "not victim", "survivor"],
}

# ============================================================================
# NON-CONSENT: RECOVERY JOURNEY
# ============================================================================

NC_RECOVERY = {
    # Early recovery
    "acknowledging_happened": ["acknowledging", "admitting", "it happened"],
    "naming_it": ["naming it", "calling it what", "saying the word"],
    "not_my_fault": ["not my fault", "didn't cause", "didn't deserve"],
    "allowing_feelings": ["allowing feelings", "letting self feel", "not suppressing"],

    # Middle recovery
    "good_days_bad_days": ["good days bad days", "ups and downs", "not linear"],
    "triggers_decreasing": ["triggers less", "not as bad", "managing"],
    "sleeping_better": ["sleeping better", "nightmares less", "rest"],
    "functioning_again": ["functioning", "doing things", "living again"],

    # Later recovery
    "integration": ["integration", "part of story", "not whole story"],
    "meaning_making": ["making meaning", "understanding", "purpose"],
    "helping_others": ["helping others", "using experience", "advocacy"],
    "post_traumatic_growth": ["growth", "stronger", "survived"],

    # Setbacks
    "anniversary_reactions": ["anniversary", "date brings back", "that time of year"],
    "new_triggers": ["new trigger", "didn't expect", "surprised by"],
    "recovery_not_linear": ["not linear", "steps back", "still recovering"],
}

# ============================================================================
# NON-CONSENT: DUBIOUS CONSENT SPECTRUM
# ============================================================================

NC_DUBCON_SPECTRUM = {
    # Coercion types
    "emotional_coercion": ["emotional coercion", "guilt trip", "manipulated"],
    "pressure_to_comply": ["pressure", "kept asking", "wouldn't stop"],
    "fear_of_consequences": ["feared consequences", "what if I don't", "might happen"],
    "obligation_feeling": ["felt obligated", "owed", "should"],

    # Impaired consent
    "intoxicated": ["drunk", "high", "intoxicated"],
    "drugged_unknowing": ["drugged", "didn't know", "put something"],
    "asleep_start": ["started while asleep", "woke up to", "already happening"],
    "mentally_impaired": ["mentally impaired", "couldn't decide", "not capable"],

    # Power imbalance
    "couldnt_say_no": ["couldn't say no", "no wasn't option", "had to"],
    "afraid_to_refuse": ["afraid to refuse", "scared to say no", "consequences"],
    "no_real_choice": ["no real choice", "illusion of choice", "either way"],
    "survival_compliance": ["survival", "had to comply", "no other way"],

    # Gray areas
    "said_yes_meant_no": ["said yes", "didn't mean", "couldn't say no"],
    "changed_mind_ignored": ["changed mind", "said stop", "kept going"],
    "consented_to_different": ["consented to different", "not this", "agreed to other"],
    "retroactive_withdrawal": ["wanted to stop", "too late", "already"],
}

# ============================================================================
# NON-CONSENT: SILENCE AND DISCLOSURE
# ============================================================================

NC_DISCLOSURE = {
    # Reasons for silence
    "wont_be_believed": ["won't be believed", "who'd believe", "word against"],
    "shame_prevents": ["shame", "too ashamed", "can't say"],
    "protecting_perpetrator": ["protecting them", "it would ruin", "don't want to"],
    "fear_of_retaliation": ["fear retaliation", "they'd hurt", "make it worse"],
    "fear_of_judgment": ["judged", "what will people", "they'll think"],
    "minimizing": ["not that bad", "others have worse", "overreacting"],

    # Attempted disclosure
    "not_believed": ["wasn't believed", "said I was lying", "didn't believe"],
    "blamed_when_told": ["blamed", "what did you expect", "your fault"],
    "dismissed": ["dismissed", "not a big deal", "get over it"],
    "told_to_forget": ["told to forget", "move on", "don't dwell"],

    # Successful disclosure
    "believed": ["believed me", "took seriously", "listened"],
    "supported": ["supported", "there for me", "helped"],
    "validated": ["validated", "not my fault", "believed"],
    "helped_get_help": ["helped get help", "resources", "professional"],

    # Reporting
    "reported_officially": ["reported", "police", "official"],
    "not_enough_evidence": ["not enough evidence", "couldn't prove", "he said she said"],
    "justice_denied": ["no justice", "got away", "nothing happened"],
    "justice_served": ["justice", "convicted", "believed legally"],
}

# ============================================================================
# NON-CONSENT: NARRATIVE TREATMENT
# ============================================================================

NC_NARRATIVE_TREATMENT = {
    # How depicted
    "graphic_depiction": ["graphic", "detailed", "explicit description"],
    "implied_not_shown": ["implied", "not shown", "off page"],
    "aftermath_focus": ["aftermath focus", "dealing with", "recovery"],
    "during_focus": ["during focus", "as it happens", "in moment"],

    # Perspective
    "victim_pov": ["victim POV", "their perspective", "through their eyes"],
    "perpetrator_pov": ["perpetrator POV", "their perspective", "how they see"],
    "outside_observer": ["outside observer", "third party", "witnessed"],
    "multiple_povs": ["multiple POVs", "different perspectives", "all sides"],

    # Purpose in narrative
    "plot_device": ["plot device", "drives story", "catalyst"],
    "character_backstory": ["backstory", "explains character", "history"],
    "exploration_of_trauma": ["exploration", "examining", "understanding"],
    "gratuitous": ["gratuitous", "unnecessary", "shock value"],

    # Handling aftermath
    "recovery_shown": ["recovery shown", "healing", "getting better"],
    "consequences_shown": ["consequences", "impact", "effects shown"],
    "support_shown": ["support shown", "helped", "not alone"],
    "realistic_portrayal": ["realistic", "accurate", "true to experience"],
}

# ============================================================================
# NON-CONSENT: SPECIFIC VERBAL DURING
# ============================================================================

NC_VERBAL_DURING = {
    # Perpetrator words
    "you_want_this": ["you want this", "I know you want", "admit it"],
    "dont_pretend": ["don't pretend", "stop acting", "we both know"],
    "youre_mine": ["you're mine", "belong to me", "my property"],
    "no_one_will_know": ["no one will know", "our secret", "between us"],
    "if_you_tell": ["if you tell", "don't tell", "keep quiet"],
    "youre_nothing": ["you're nothing", "worthless", "nobody cares"],

    # Victim verbal attempts
    "saying_no": ["no", "stop", "don't"],
    "saying_please": ["please", "please stop", "please don't"],
    "trying_to_reason": ["trying to reason", "let's talk", "wait"],
    "promising_anything": ["I'll do anything", "whatever you want", "just stop"],
    "calling_for_help": ["help", "someone", "please help"],

    # During ongoing
    "begging_to_stop": ["begging", "please stop", "I can't"],
    "crying_words": ["crying", "sobbing", "tears and words"],
    "going_silent": ["went silent", "stopped talking", "no more words"],
    "dissociated_responses": ["automatic yes", "whatever", "gone"],
}

# ============================================================================
# NON-CONSENT: GROOMING PATTERNS
# ============================================================================

NC_GROOMING = {
    # Building trust
    "special_attention": ["special attention", "singled out", "chosen"],
    "gifts_favors": ["gifts", "favors", "gave me things"],
    "emotional_support": ["emotional support", "there for me", "understood me"],
    "filling_a_need": ["filled a need", "what I was missing", "provided"],
    "becoming_indispensable": ["couldn't do without", "needed them", "dependent"],

    # Isolation tactics
    "separating_from_others": ["separated from", "didn't want me with", "jealous of"],
    "creating_us_vs_them": ["us against them", "no one understands", "only I"],
    "questioning_other_relationships": ["friends don't care", "family doesn't understand", "only me"],

    # Boundary erosion
    "small_boundary_pushes": ["small pushes", "little by little", "gradually"],
    "normalizing_inappropriate": ["normalizing", "everyone does", "not weird"],
    "testing_reactions": ["testing", "seeing if", "how far"],
    "desensitization": ["desensitized", "got used to", "didn't notice anymore"],

    # Secrets and shame
    "creating_secrets": ["our secret", "don't tell", "between us"],
    "shame_inducing": ["made me feel shame", "dirty", "guilty"],
    "complicity_creation": ["made me complicit", "you wanted", "you let me"],

    # Escalation
    "gradual_escalation": ["gradually", "escalated", "more each time"],
    "point_of_no_return": ["too late to stop", "already done", "can't go back"],
    "trapped_by_history": ["trapped", "already happened", "might as well"],
}

# ============================================================================
# NON-CONSENT: SPECIFIC BODY MEMORIES
# ============================================================================

NC_BODY_MEMORY = {
    # Where touched
    "phantom_touches": ["phantom touch", "still feel hands", "ghost of touch"],
    "specific_spots_trigger": ["that spot", "when touched there", "instant memory"],
    "skin_crawling": ["skin crawling", "creeping feeling", "wants to escape"],
    "body_remembers": ["body remembers", "muscle memory", "physical memory"],

    # Physical triggers
    "certain_positions": ["certain positions", "that angle", "way of being held"],
    "specific_pressure": ["that pressure", "weight like that", "grip like"],
    "smell_triggers_body": ["smell triggers", "scent brings back", "body reacts to smell"],
    "sound_triggers_body": ["sound triggers", "voice like that", "certain words"],

    # Physical reactions to memory
    "tension_in_body": ["tension", "tight", "clenched"],
    "nausea_from_memory": ["nausea", "sick feeling", "stomach turns"],
    "pain_without_cause": ["pain without cause", "hurts but", "phantom pain"],
    "arousal_from_trigger": ["unwanted arousal", "body responds", "hates that"],

    # Reclaiming body
    "relearning_touch": ["relearning touch", "safe touch", "different"],
    "body_as_own": ["my body", "belong to me", "taking back"],
    "new_associations": ["new associations", "rewriting", "different memories"],
}

# ============================================================================
# NON-CONSENT: TIME PERCEPTION DURING
# ============================================================================

NC_TIME_PERCEPTION = {
    # Time distortion
    "time_stopped": ["time stopped", "frozen moment", "eternal"],
    "time_stretched": ["stretched", "forever", "wouldn't end"],
    "time_compressed": ["compressed", "over fast", "blur"],
    "no_sense_of_time": ["no sense of time", "could have been", "didn't know"],

    # Moment by moment
    "each_second_agony": ["each second", "moment by moment", "counting"],
    "waiting_for_end": ["waiting for end", "when will", "please finish"],
    "endless_middle": ["endless middle", "no end in sight", "forever"],
    "sudden_end": ["sudden end", "then it stopped", "finally over"],

    # Memory of time
    "lost_time": ["lost time", "don't remember", "gaps"],
    "every_detail_remembered": ["remember every detail", "can't forget", "burned in"],
    "fragments": ["fragments", "pieces", "not whole"],
    "confused_timeline": ["confused timeline", "order unclear", "when did"],
}

# ============================================================================
# NON-CONSENT: SPECIFIC EMOTIONAL STATES DURING
# ============================================================================

NC_EMOTIONS_DURING = {
    # Fear
    "terror": ["terror", "pure fear", "paralyzed by fear"],
    "fear_of_death": ["fear of death", "might die", "kill me"],
    "fear_of_pain": ["fear of pain", "will hurt", "more pain"],
    "fear_of_unknown": ["fear of unknown", "what next", "what will"],

    # Powerlessness
    "complete_powerlessness": ["powerless", "no control", "couldn't stop"],
    "helplessness": ["helpless", "nothing I could do", "no options"],
    "vulnerability_extreme": ["vulnerable", "exposed", "defenseless"],
    "at_their_mercy": ["at their mercy", "whatever they want", "no choice"],

    # Shame
    "shame_during": ["shame", "humiliated", "degraded"],
    "feeling_dirty": ["dirty", "filthy", "contaminated"],
    "wanting_to_disappear": ["disappear", "not exist", "invisible"],
    "wishing_for_death": ["wished for death", "rather die", "end me"],

    # Anger
    "rage_inside": ["rage", "anger", "fury"],
    "hatred": ["hatred", "hated them", "burning hate"],
    "anger_at_self": ["angry at self", "why can't I", "useless"],

    # Grief
    "mourning_self": ["mourning self", "who I was", "before"],
    "loss_of_innocence": ["loss of innocence", "can't go back", "changed forever"],
    "grieving_safety": ["safety gone", "world unsafe", "never safe"],
}

# ============================================================================
# NON-CONSENT: MENTAL ESCAPE TECHNIQUES
# ============================================================================

NC_MENTAL_ESCAPE = {
    # Going somewhere else
    "happy_memory": ["went to happy memory", "remembered", "somewhere safe"],
    "imagined_place": ["imagined place", "not here", "somewhere else"],
    "childhood_memory": ["childhood", "when safe", "before"],
    "future_imagination": ["imagined future", "when over", "after this"],

    # Detachment techniques
    "narrating_like_story": ["like a story", "narrating", "not me"],
    "third_person_view": ["third person", "watching", "not happening to me"],
    "clinical_detachment": ["clinical", "observing", "detached"],
    "numbness_intentional": ["made self numb", "turned off", "nothing"],

    # Focus elsewhere
    "counting": ["counting", "numbers", "focused on count"],
    "reciting": ["reciting", "words", "memorized thing"],
    "patterns": ["patterns", "ceiling pattern", "focused elsewhere"],
    "physical_focus": ["focused on", "one sensation", "something else"],

    # Dissociative
    "leaving_body": ["left body", "floated", "wasn't there"],
    "splitting": ["split", "part stayed part left", "divided"],
    "autopilot": ["autopilot", "automatic", "not present"],
}

# ============================================================================
# NON-CONSENT: PHYSICAL SURVIVAL RESPONSES
# ============================================================================

NC_SURVIVAL_PHYSICAL = {
    # Automatic responses
    "going_limp": ["went limp", "stopped resisting", "ragdoll"],
    "compliance_for_survival": ["complied", "did what told", "survive"],
    "minimizing_harm": ["minimizing harm", "less damage", "don't make worse"],
    "protecting_vital_areas": ["protected", "covered", "curled"],

    # Breathing
    "breath_holding": ["held breath", "stopped breathing", "waiting"],
    "shallow_breathing": ["shallow breath", "barely", "quiet"],
    "hyperventilating": ["hyperventilating", "couldn't control", "gasping"],
    "forced_steady_breath": ["forced steady", "trying to calm", "control breath"],

    # Muscle response
    "tensing_all_muscles": ["tensed everything", "tight", "braced"],
    "muscle_fatigue": ["muscles gave out", "too tired", "couldn't hold"],
    "trembling_uncontrollable": ["trembling", "shaking", "couldn't stop"],
    "convulsive_reactions": ["convulsive", "jerking", "involuntary"],

    # Voice
    "screaming_inside": ["screaming inside", "silent scream", "no sound"],
    "voice_frozen": ["voice frozen", "couldn't make sound", "mute"],
    "whimpering": ["whimpering", "small sounds", "involuntary noise"],
    "begging_reflexive": ["begging", "please", "automatic"],
}

# ============================================================================
# NON-CONSENT: AFTERWARD PHYSICAL STATE
# ============================================================================

NC_PHYSICAL_AFTER = {
    # Immediate physical
    "cant_stand": ["couldn't stand", "legs wouldn't", "collapsed"],
    "physical_shaking": ["shaking", "tremors", "couldn't stop"],
    "teeth_chattering": ["teeth chattering", "cold inside", "shock"],
    "hypervigilance_physical": ["hyperalert", "every sound", "couldn't relax"],

    # Pain after
    "soreness_lasting": ["sore", "hurts", "pain lasting"],
    "difficulty_walking": ["hard to walk", "painful to move", "gait changed"],
    "sitting_painful": ["sitting hurt", "couldn't sit", "had to stand"],
    "internal_pain": ["internal pain", "inside hurts", "deep pain"],

    # Evidence on body
    "marks_visible": ["marks", "visible evidence", "can see"],
    "bruises_forming": ["bruises", "forming", "turning colors"],
    "bite_marks_left": ["bite marks", "teeth prints", "evidence"],
    "defensive_wounds": ["defensive wounds", "from fighting", "trying to stop"],

    # Medical needs
    "needed_medical": ["needed medical", "doctor", "treatment"],
    "afraid_to_seek_help": ["afraid to seek", "couldn't go", "what would say"],
    "evidence_preservation": ["preserve evidence", "don't wash", "for proof"],
    "delayed_medical": ["delayed", "waited too long", "evidence gone"],
}

# ============================================================================
# NON-CONSENT: INTIMACY AFTER TRAUMA
# ============================================================================

NC_INTIMACY_AFTER = {
    # Avoidance
    "avoiding_all_touch": ["avoiding touch", "don't touch me", "can't bear"],
    "avoiding_specific_acts": ["can't do that", "triggers", "not that"],
    "avoiding_intimacy_completely": ["no intimacy", "can't be close", "shut down"],
    "hypervigilance_during_intimacy": ["hypervigilant", "watching", "waiting for"],

    # Triggers during intimacy
    "flashback_during_sex": ["flashback", "suddenly there again", "transported"],
    "dissociation_during_sex": ["dissociated", "left body", "not present"],
    "panic_during_intimacy": ["panic", "had to stop", "couldn't continue"],
    "crying_during_intimacy": ["cried", "tears", "couldn't help"],

    # Working through
    "patient_partner": ["patient partner", "understood", "waited"],
    "communication_about_triggers": ["communicated", "told them", "warned"],
    "safe_words_importance": ["safe word", "could stop", "had control"],
    "going_slow": ["slow", "gradual", "no pressure"],

    # Reclaiming
    "reclaiming_sexuality": ["reclaiming", "my choice now", "on my terms"],
    "positive_experiences": ["positive experiences", "different", "healing"],
    "body_autonomy_regained": ["autonomy", "my body", "I decide"],
    "separating_past_present": ["separating", "not them", "different person"],
}

# ============================================================================
# NON-CONSENT: RELATIONSHIP IMPACTS
# ============================================================================

NC_RELATIONSHIP_IMPACT = {
    # Trust issues
    "cant_trust_anyone": ["can't trust", "everyone suspect", "no one safe"],
    "testing_people": ["test people", "see if", "before trust"],
    "walls_up": ["walls up", "protecting self", "won't let in"],
    "expecting_betrayal": ["expecting betrayal", "waiting for", "when will"],

    # Attachment patterns
    "avoidant_attachment": ["avoidant", "push away", "don't get close"],
    "anxious_attachment": ["anxious", "clingy", "fear abandonment"],
    "disorganized_attachment": ["confused", "want close but scared", "push pull"],

    # Relationship fears
    "fear_of_intimacy": ["fear intimacy", "getting close", "vulnerability"],
    "fear_of_abandonment": ["fear abandonment", "will leave", "not enough"],
    "fear_of_commitment": ["fear commitment", "trapped", "can't leave"],
    "fear_of_vulnerability": ["fear vulnerability", "can't be weak", "must protect"],

    # Impact on partner
    "partner_struggles": ["partner struggles", "hard for them", "secondary trauma"],
    "pushing_partner_away": ["push away", "test them", "make them leave"],
    "unfair_to_partner": ["unfair", "they deserve better", "can't give enough"],
    "healing_together": ["healing together", "patient", "growing"],
}

# ============================================================================
# NON-CONSENT: SELF-PERCEPTION AFTER
# ============================================================================

NC_SELF_PERCEPTION = {
    # Negative self-perception
    "feeling_broken": ["broken", "damaged", "ruined"],
    "feeling_dirty": ["dirty", "can't get clean", "contaminated"],
    "feeling_worthless": ["worthless", "no value", "nothing"],
    "feeling_used": ["used", "object", "not person"],
    "feeling_weak": ["weak", "should have", "couldn't even"],

    # Identity impact
    "identity_shattered": ["identity shattered", "don't know who", "changed"],
    "before_and_after": ["before and after", "different person", "divided life"],
    "core_self_questioned": ["questioning self", "who am I", "fundamental"],
    "masculinity_questioned": ["masculinity", "not a man", "should have been stronger"],

    # Self-blame
    "blaming_self": ["my fault", "I should have", "I let"],
    "what_if_thoughts": ["what if I had", "if only", "could have prevented"],
    "deserved_it_thinking": ["deserved it", "asked for", "punishment"],

    # Rebuilding
    "survivor_identity": ["survivor", "not victim", "survived"],
    "finding_self_again": ["finding self", "who I am now", "rebuilding"],
    "stronger_than_thought": ["stronger", "survived", "resilient"],
    "defining_self_beyond": ["more than this", "not whole identity", "also"],
}

# ============================================================================
# NON-CONSENT: SPECIFIC TRIGGER TYPES
# ============================================================================

NC_TRIGGER_TYPES = {
    # Sensory triggers
    "smell_trigger": ["smell", "scent", "cologne like"],
    "sound_trigger": ["sound", "voice like", "words"],
    "sight_trigger": ["saw something", "looked like", "similar"],
    "touch_trigger": ["touch", "grabbed like", "held like"],
    "taste_trigger": ["taste", "reminded", "in mouth"],

    # Situational triggers
    "similar_location": ["similar place", "looked like", "same kind"],
    "similar_time": ["same time", "that hour", "darkness"],
    "similar_situation": ["similar situation", "felt like", "same setup"],
    "similar_person": ["looked like them", "similar", "reminded"],

    # Internal triggers
    "emotion_trigger": ["feeling triggered", "emotional state", "when I feel"],
    "body_position": ["body position", "lying like", "that angle"],
    "vulnerability_trigger": ["feeling vulnerable", "when weak", "exposed"],
    "powerlessness_trigger": ["powerless feeling", "no control", "helpless"],

    # Managing triggers
    "recognizing_triggers": ["recognizing", "know now", "aware of"],
    "coping_with_triggers": ["coping", "managing", "handling"],
    "reducing_trigger_impact": ["impact reducing", "less intense", "manageable"],
    "trigger_warning_need": ["need warning", "prepare self", "advance notice"],
}

# ============================================================================
# NON-CONSENT: SPECIFIC MOMENT DETAILS
# ============================================================================

NC_MOMENT_DETAILS = {
    # The exact moments
    "moment_of_penetration": ["moment of", "when entered", "the push in"],
    "moment_of_first_contact": ["first touch", "when touched", "hand on"],
    "moment_of_restraint": ["when held down", "pinned", "trapped moment"],
    "moment_realized_no_escape": ["realized no escape", "no way out", "trapped"],
    "moment_stopped_fighting": ["stopped fighting", "gave up", "no point"],
    "moment_ended": ["when it ended", "finally over", "stopped"],

    # Transitions
    "before_to_during": ["then it started", "began", "shifted to"],
    "during_to_after": ["when it ended", "stopped", "finally done"],
    "normal_to_not": ["normal then not", "changed", "became"],

    # Specific actions experienced
    "being_undressed": ["undressed", "clothes removed", "stripped"],
    "being_positioned": ["positioned", "moved", "arranged"],
    "being_entered": ["entered", "penetrated", "inside me"],
    "being_used": ["used", "like object", "for them"],
    "being_finished_with": ["finished with", "done with me", "discarded"],
}

# ============================================================================
# NON-CONSENT: INTERNAL QUESTIONS
# ============================================================================

NC_INTERNAL_QUESTIONS = {
    # During questions
    "why_me_question": ["why me", "what did I", "why is this"],
    "what_did_i_do": ["what did I do", "to deserve", "cause this"],
    "will_it_end": ["will it end", "when will", "how long"],
    "will_i_survive": ["will I survive", "am I going to", "live through"],
    "is_this_real": ["is this real", "happening", "not dream"],

    # After questions
    "why_didnt_i": ["why didn't I", "should have", "could have"],
    "what_is_wrong_with_me": ["what's wrong with me", "broken", "defective"],
    "who_am_i_now": ["who am I now", "still me", "changed"],
    "can_i_recover": ["can I recover", "get better", "be normal"],
    "will_anyone_believe": ["will anyone believe", "who would", "my word"],

    # Long-term questions
    "will_i_ever_be_normal": ["ever be normal", "like before", "recover fully"],
    "can_i_trust_again": ["trust again", "anyone ever", "let someone"],
    "am_i_damaged_forever": ["damaged forever", "broken permanently", "ruined"],
    "why_cant_i_forget": ["can't forget", "won't go away", "still remember"],
}

# ============================================================================
# NON-CONSENT: HELP-SEEKING
# ============================================================================

NC_HELP_SEEKING = {
    # Barriers to seeking help
    "shame_prevents_help": ["shame prevents", "too ashamed", "can't face"],
    "fear_prevents_help": ["fear prevents", "afraid of", "what if"],
    "not_knowing_where": ["don't know where", "no idea how", "where would I"],
    "not_qualifying": ["not bad enough", "others worse", "don't qualify"],
    "cant_afford_help": ["can't afford", "no insurance", "expensive"],
    "not_ready": ["not ready", "can't face", "not yet"],

    # Types of help
    "hotline_call": ["called hotline", "crisis line", "phone help"],
    "rainn": ["RAINN", "sexual assault hotline", "called for help"],
    "therapy_individual": ["individual therapy", "counselor", "therapist"],
    "group_therapy": ["group therapy", "support group", "others like me"],
    "medical_help": ["medical help", "hospital", "physical care"],
    "legal_help": ["legal help", "lawyer", "police"],

    # Experience with help
    "positive_help_experience": ["helpful", "made difference", "glad I did"],
    "negative_help_experience": ["not helpful", "made worse", "retraumatized"],
    "mixed_help_experience": ["mixed", "some helpful", "complicated"],
}

# ============================================================================
# NON-CONSENT: SPECIFIC PERPETRATOR AWARENESS
# ============================================================================

NC_PERPETRATOR_AWARENESS = {
    # What they said
    "perpetrator_justifications": ["justified", "said why", "their reason"],
    "perpetrator_denial": ["denied", "didn't happen", "you wanted"],
    "perpetrator_threats_after": ["threatened after", "if you tell", "will hurt"],
    "perpetrator_acting_normal": ["acted normal", "like nothing", "the next day"],

    # Power they held
    "physical_power": ["physically stronger", "overpowered", "couldn't match"],
    "social_power": ["social power", "status", "reputation"],
    "economic_power": ["economic power", "money", "job"],
    "knowledge_power": ["knew things", "could reveal", "secrets"],

    # Victim's understanding
    "understanding_manipulation": ["understood manipulation", "saw tactics", "recognized"],
    "still_confused": ["still confused", "don't understand", "why"],
    "anger_at_perpetrator": ["angry at them", "hate them", "rage"],
    "complicated_feelings": ["complicated feelings", "shouldn't but", "conflicted"],
}

# ============================================================================
# NON-CONSENT: HEALING MOMENTS
# ============================================================================

NC_HEALING_MOMENTS = {
    # Breakthrough moments
    "first_good_day": ["first good day", "didn't think about", "okay moment"],
    "first_laugh_after": ["first laugh", "found joy", "happiness possible"],
    "first_safe_touch": ["first safe touch", "could be touched", "wanted touch"],
    "telling_someone": ["told someone", "said it out loud", "finally shared"],
    "being_believed": ["believed", "taken seriously", "validated"],

    # Reclaiming
    "reclaiming_space": ["reclaimed space", "went back", "my space again"],
    "reclaiming_activity": ["reclaimed activity", "could do again", "taking back"],
    "reclaiming_body": ["my body again", "belongs to me", "not theirs"],
    "reclaiming_sexuality": ["sexuality mine", "choosing pleasure", "my terms"],
    "reclaiming_trust": ["trusting again", "let someone in", "took risk"],

    # Growth moments
    "realizing_strength": ["realized strength", "survived", "strong"],
    "finding_purpose": ["found purpose", "meaning from", "using experience"],
    "helping_others": ["helping others", "not alone", "shared experience"],
    "post_traumatic_growth": ["growth", "who I am now", "became because"],
}

# ============================================================================
# NON-CONSENT: FICTIONAL NARRATIVE ELEMENTS
# ============================================================================

NC_FICTIONAL_ELEMENTS = {
    # Rescue scenarios
    "interrupted_by_rescuer": ["rescued", "someone stopped", "saved"],
    "escape_successful": ["escaped", "got away", "broke free"],
    "perpetrator_caught": ["caught", "punished", "justice"],
    "revenge_narrative": ["revenge", "made them pay", "got back"],

    # Recovery arc
    "healing_journey_shown": ["healing journey", "recovery arc", "getting better"],
    "support_system_shown": ["support system", "people helped", "not alone"],
    "professional_help_shown": ["got help", "therapy", "treatment"],
    "hopeful_ending": ["hopeful ending", "better future", "survived and thrived"],

    # Realistic elements
    "realistic_aftermath": ["realistic aftermath", "accurate portrayal", "true to life"],
    "complex_recovery": ["complex recovery", "not simple", "realistic struggle"],
    "lasting_effects_shown": ["lasting effects", "doesn't just go away", "realistic duration"],
    "survivor_centered": ["survivor centered", "their perspective", "their voice"],

    # Author handling
    "sensitive_handling": ["sensitively handled", "respectful", "careful"],
    "trauma_informed": ["trauma informed", "accurate", "researched"],
    "trigger_warnings_provided": ["trigger warnings", "warned reader", "content notes"],
}

# ============================================================================
# NC DEEP: SECOND-BY-SECOND PHYSICAL SENSATIONS
# ============================================================================

NC_DEEP_PHYSICAL_SENSATIONS = {
    # Skin sensations
    "skin_crawling_sensation": ["skin crawling", "ants under skin", "crawling feeling"],
    "skin_burning": ["skin burning", "burned where touched", "hot where hands"],
    "skin_going_numb": ["skin went numb", "couldn't feel skin", "dead feeling"],
    "goosebumps_wrong": ["goosebumps", "wrong goosebumps", "body reacting"],
    "hypersensitivity": ["hypersensitive", "every touch magnified", "too aware"],

    # Internal body sensations
    "stomach_dropping": ["stomach dropped", "gut falling", "inside falling"],
    "chest_tightening": ["chest tight", "couldn't breathe", "crushing chest"],
    "throat_closing": ["throat closing", "couldn't swallow", "lump in throat"],
    "heart_pounding_wrong": ["heart pounding", "racing wrong", "cardiac fear"],
    "blood_rushing_wrong": ["blood rushing", "in ears", "couldn't hear over"],

    # Genital sensations unwanted
    "unwanted_physical_response": ["responded physically", "body betrayed", "didn't want to"],
    "arousal_with_horror": ["aroused and horrified", "body yes mind no", "betrayal response"],
    "pain_and_arousal_mixed": ["pain mixed with", "confusing signals", "body confused"],
    "numbness_there": ["went numb there", "couldn't feel", "disconnected from"],
    "hypersensitivity_there": ["too sensitive", "every sensation", "overwhelming touch"],

    # Pain specifics
    "sharp_pain": ["sharp pain", "stabbing", "sudden hurt"],
    "burning_pain": ["burning", "tearing feeling", "fire inside"],
    "pressure_pain": ["pressure", "too much", "forced open"],
    "aching_pain": ["aching", "deep ache", "lasting hurt"],
    "throbbing_pain": ["throbbing", "pulsing pain", "rhythmic hurt"],

    # Temperature sensations
    "cold_inside": ["cold inside", "frozen", "ice in veins"],
    "hot_flush_fear": ["hot flush", "burning up", "fever feeling"],
    "alternating_hot_cold": ["hot then cold", "temperature swings", "couldn't regulate"],
    "specific_cold_hands": ["their cold hands", "cold touch", "icy fingers"],
    "specific_hot_breath": ["hot breath", "breath on skin", "warmth wrong"],
}

# ============================================================================
# NC DEEP: MICRO-MOMENT THOUGHTS
# ============================================================================

NC_DEEP_MICRO_THOUGHTS = {
    # Split-second thoughts
    "this_cant_be": ["this can't be", "not possible", "no"],
    "i_must_be_wrong": ["must be wrong", "misunderstanding", "not what I think"],
    "maybe_if_i": ["maybe if I", "perhaps I can", "what if I"],
    "just_survive": ["just survive", "get through", "stay alive"],
    "count_the_seconds": ["counting seconds", "how long", "when will"],

    # Bargaining thoughts
    "ill_do_anything_else": ["anything else", "not this", "something else"],
    "please_not_that": ["please not that", "anything but", "not there"],
    "if_i_cooperate": ["if I cooperate", "maybe less", "won't hurt"],
    "dont_make_it_worse": ["don't make worse", "provoke", "anger them"],
    "just_let_them": ["just let them", "faster if", "over sooner"],

    # Dissociative thoughts
    "this_isnt_me": ["this isn't me", "not my body", "someone else"],
    "im_not_here": ["I'm not here", "somewhere else", "not present"],
    "watching_not_feeling": ["watching", "observing", "not feeling"],
    "floating_above": ["floating above", "ceiling view", "looking down"],
    "far_away": ["far away", "distant", "removed"],

    # Survival calculations
    "calculating_risk": ["calculating", "if I do this", "risk assessment"],
    "path_of_least_harm": ["least harm", "minimize damage", "best option"],
    "protecting_parts": ["protect", "not there", "vital areas"],
    "waiting_for_opening": ["waiting for", "opportunity", "when can I"],
    "memorizing_details": ["memorizing", "remember this", "for later"],

    # Shame thoughts during
    "im_disgusting": ["disgusting", "dirty", "filthy"],
    "i_caused_this": ["caused this", "my fault", "did this"],
    "i_deserve_this": ["deserve this", "punishment", "earned"],
    "no_one_would_want": ["no one would want", "ruined", "used"],
    "everyone_would_know": ["everyone know", "they'd see", "marked"],
}

# ============================================================================
# NC DEEP: BREATH PATTERNS
# ============================================================================

NC_DEEP_BREATHING = {
    # Fear breathing
    "breath_caught": ["breath caught", "stopped breathing", "held breath"],
    "shallow_rapid": ["shallow rapid", "panting fear", "quick breaths"],
    "forgetting_to_breathe": ["forgot to breathe", "had to remind", "oxygen starved"],
    "breath_knocked_out": ["breath knocked", "couldn't inhale", "winded"],
    "gasping": ["gasping", "gulping air", "desperate breath"],

    # Controlled breathing attempts
    "trying_to_steady": ["trying to steady", "calm breathing", "control breath"],
    "counting_breaths": ["counting breaths", "in out", "focus on breath"],
    "breath_as_anchor": ["breath as anchor", "only constant", "held onto"],
    "failing_to_control": ["couldn't control", "breath betrayed", "hyperventilating"],

    # Sounds of breathing
    "ragged_breathing": ["ragged breath", "uneven", "jagged inhales"],
    "whimpering_on_exhale": ["whimpering exhale", "sounds escaped", "couldn't quiet"],
    "breath_stuttering": ["stuttering breath", "hitching", "catching"],
    "trying_to_be_silent": ["silent breathing", "quiet", "don't make noise"],
    "breath_giving_away": ["breath gave away", "heard me", "too loud"],

    # Breathing after
    "first_full_breath": ["first full breath", "finally breathe", "air again"],
    "still_cant_breathe_right": ["still can't breathe", "shallow", "not right"],
    "breath_triggers": ["breathing triggers", "when breathe like", "reminds"],
    "relearning_breath": ["relearning", "how to breathe", "breath work"],
}

# ============================================================================
# NC DEEP: EYE BEHAVIOR
# ============================================================================

NC_DEEP_EYES = {
    # During - victim's eyes
    "eyes_squeezed_shut": ["squeezed shut", "couldn't look", "darkness"],
    "eyes_forced_open": ["eyes open", "made to watch", "couldn't close"],
    "staring_at_nothing": ["stared at nothing", "unfocused", "blank stare"],
    "looking_for_help": ["looking for help", "anyone", "escape route"],
    "eyes_darting": ["eyes darting", "scanning", "looking for way out"],
    "fixed_on_spot": ["fixed on spot", "ceiling", "wall mark", "not looking"],
    "tears_blurring": ["tears blurring", "couldn't see", "wet eyes"],

    # Looking at perpetrator or not
    "couldnt_look_at_them": ["couldn't look", "averted eyes", "not their face"],
    "forced_to_look": ["forced to look", "made me watch", "eyes on them"],
    "seeing_their_expression": ["saw their face", "their expression", "looking at me"],
    "reading_their_eyes": ["read their eyes", "what they wanted", "anticipating"],

    # After - eyes
    "cant_make_eye_contact": ["can't make eye contact", "look away", "eyes down"],
    "hypervigilant_eyes": ["watching everything", "scanning", "constant vigilance"],
    "dead_eyes_after": ["dead eyes", "flat stare", "nothing there"],
    "eyes_that_flinch": ["eyes flinch", "startle", "sudden movement"],
    "crying_without_knowing": ["crying without knowing", "tears just fall", "wet face"],
}

# ============================================================================
# NC DEEP: HAND EXPERIENCES
# ============================================================================

NC_DEEP_HANDS = {
    # Victim's hands during
    "hands_pinned": ["hands pinned", "held down", "couldn't move hands"],
    "hands_tied": ["hands tied", "bound", "restrained"],
    "fists_clenched_helpless": ["fists clenched", "helpless rage", "couldn't hit"],
    "hands_pushing_futilely": ["pushing", "trying to push away", "no strength"],
    "hands_clawing": ["clawing", "scratching", "trying to"],
    "hands_grabbing_anything": ["grabbing", "sheets", "anything to hold"],
    "hands_limp": ["hands limp", "gave up", "no fight left"],
    "fingernails_digging_self": ["nails digging into self", "own skin", "grounding pain"],

    # Perpetrator's hands - what was felt
    "their_hands_everywhere": ["hands everywhere", "couldn't escape touch", "all over"],
    "grip_too_tight": ["grip too tight", "bruising hold", "crushing"],
    "hands_holding_down": ["hands holding", "weight", "pressure"],
    "hands_covering_mouth": ["hand on mouth", "silencing", "couldn't scream"],
    "hands_on_throat": ["hands on throat", "choking", "couldn't breathe"],
    "hands_forcing_open": ["forcing open", "prying", "spreading"],
    "hands_inside": ["hands inside", "fingers", "penetrating"],

    # After - hands
    "cant_stop_washing_hands": ["washing hands", "never clean", "over and over"],
    "hands_that_shake": ["hands shake", "trembling", "can't steady"],
    "phantom_grip_feeling": ["still feel grip", "phantom hands", "where they held"],
    "hands_as_triggers": ["hands trigger", "when touched", "hands on me"],
}

# ============================================================================
# NC DEEP: VOICE AND SOUNDS
# ============================================================================

NC_DEEP_SOUNDS = {
    # Sounds victim made
    "scream_caught": ["scream caught", "tried to scream", "nothing came"],
    "whimper_escaped": ["whimper escaped", "small sound", "couldn't stop"],
    "begging_sounds": ["begging", "please please", "words tumbling"],
    "crying_sounds": ["sobbing", "crying", "keening"],
    "silent_despite": ["silent", "no sound", "couldn't make noise"],
    "sounds_of_pain": ["pain sounds", "grunt", "cry out"],
    "involuntary_sounds": ["involuntary", "couldn't help", "body made"],

    # Sounds perpetrator made
    "their_breathing": ["their breathing", "heavy breath", "panting"],
    "their_voice": ["their voice", "what they said", "words"],
    "their_grunting": ["their grunting", "sounds they made", "effort sounds"],
    "their_moaning": ["their pleasure sounds", "enjoying", "sickening"],
    "their_laughter": ["laughed", "thought funny", "mocking"],
    "their_threats": ["threatening voice", "whispered threats", "promised"],
    "their_instructions": ["instructions", "telling me to", "ordering"],

    # Environmental sounds
    "silence_deafening": ["deafening silence", "quiet", "no one"],
    "sounds_outside": ["sounds outside", "life continuing", "no one knows"],
    "sounds_that_didnt_help": ["sounds nearby", "could hear people", "didn't help"],
    "sounds_marking_time": ["clock", "sounds marking", "how long"],

    # After - sounds
    "voices_as_triggers": ["voices trigger", "similar voice", "tone like"],
    "sounds_that_bring_back": ["sounds bring back", "specific sound", "transports"],
    "hypervigilance_sounds": ["alert to sounds", "every noise", "startle"],
    "needing_silence": ["need silence", "can't handle noise", "overwhelming"],
    "needing_noise": ["need noise", "cover thoughts", "can't be quiet"],
}

# ============================================================================
# NC DEEP: TASTE AND SMELL
# ============================================================================

NC_DEEP_TASTE_SMELL = {
    # Taste during
    "blood_taste_from_biting": ["tasted blood", "bit lip", "metallic"],
    "tears_taste": ["tasted tears", "salt", "own crying"],
    "their_taste_forced": ["their taste", "in mouth", "forced to taste"],
    "bile_rising": ["bile rising", "almost vomited", "sick taste"],
    "taste_of_fear": ["taste of fear", "metallic fear", "adrenaline taste"],

    # Smell during
    "their_cologne": ["their cologne", "smell", "scent remember"],
    "their_body_odor": ["their smell", "body odor", "sweat"],
    "their_breath": ["their breath", "alcohol breath", "close smell"],
    "smell_of_sex": ["smell of sex", "fluids", "aftermath smell"],
    "own_fear_smell": ["own sweat", "fear smell", "smelled fear"],
    "location_smell": ["place smelled", "room smell", "environment"],

    # After - smell triggers
    "cologne_triggers": ["cologne triggers", "similar smell", "instant back"],
    "alcohol_breath_triggers": ["alcohol breath", "that smell", "brings back"],
    "body_smell_triggers": ["body smell triggers", "sweat like", "reminds"],
    "cant_stand_smell": ["can't stand smell", "have to leave", "overwhelming"],
    "smells_that_transport": ["smell transports", "suddenly there", "visceral"],

    # Taste after
    "cant_eat_certain": ["can't eat certain", "taste reminds", "associated"],
    "everything_tastes_wrong": ["everything wrong", "food tastes off", "can't eat"],
    "taste_flashbacks": ["taste flashback", "suddenly tasting", "memory taste"],
}

# ============================================================================
# NC DEEP: SPECIFIC BODY PARTS - WHAT WAS DONE TO THEM
# ============================================================================

NC_DEEP_BODY_PARTS = {
    # Mouth
    "mouth_forced_open": ["mouth forced", "jaw held", "made to open"],
    "something_in_mouth": ["something in mouth", "forced in", "couldn't speak"],
    "mouth_covered": ["mouth covered", "couldn't scream", "silenced"],
    "mouth_used": ["mouth used", "oral forced", "had to"],
    "lips_bitten": ["lips bitten", "bit own lip", "tasted blood"],

    # Neck/Throat
    "neck_grabbed": ["neck grabbed", "throat held", "choked"],
    "neck_bitten": ["neck bitten", "marked", "teeth on throat"],
    "throat_squeezed": ["throat squeezed", "couldn't breathe", "pressure"],
    "marks_on_neck": ["marks on neck", "visible", "had to hide"],

    # Chest
    "chest_pressed": ["chest pressed", "weight on", "couldn't breathe"],
    "chest_touched_unwanted": ["chest touched", "hands on", "groped"],
    "nipples_hurt": ["nipples hurt", "twisted", "bit"],
    "heart_area_pain": ["heart area", "chest pain", "cardiac fear"],

    # Arms
    "arms_pinned": ["arms pinned", "held down", "couldn't move"],
    "arms_bruised": ["arms bruised", "grip marks", "finger prints"],
    "wrists_held": ["wrists held", "tight grip", "marks left"],
    "wrists_tied": ["wrists tied", "bound", "rope burn"],

    # Back
    "back_against_surface": ["back against", "hard surface", "pressed into"],
    "back_scratched": ["back scratched", "floor burn", "rough surface"],
    "spine_bent_wrong": ["bent wrong", "position hurt", "spine aching"],

    # Hips/Pelvis
    "hips_gripped": ["hips gripped", "held in place", "controlled"],
    "hip_bruises": ["hip bruises", "grip marks", "finger shaped"],
    "pelvis_pain": ["pelvis pain", "deep ache", "internal"],

    # Thighs
    "thighs_forced_open": ["thighs forced", "spread open", "couldn't close"],
    "thigh_bruises": ["thigh bruises", "inner thigh marks", "evidence"],
    "thighs_held": ["thighs held", "grip on legs", "controlled"],

    # Genitals
    "genital_pain": ["pain there", "hurt", "damage"],
    "genital_bleeding": ["bleeding", "saw blood", "damaged"],
    "unwanted_genital_response": ["body responded", "didn't want", "betrayal"],

    # Anus
    "anal_pain": ["anal pain", "tearing", "forced entry"],
    "anal_bleeding": ["anal bleeding", "blood after", "damage"],
    "unprepared_entry": ["unprepared", "no lube", "dry entry"],
}

# ============================================================================
# NC DEEP: CLOTHING EXPERIENCES
# ============================================================================

NC_DEEP_CLOTHING = {
    # During
    "clothes_torn": ["clothes torn", "ripped off", "destroyed"],
    "clothes_pulled_aside": ["pulled aside", "moved", "just enough access"],
    "undressed_forcibly": ["forcibly undressed", "stripped", "exposed"],
    "clothes_used_against": ["clothes used against", "tied with", "gagged with"],
    "partial_undress": ["partially", "just enough", "some clothes"],
    "complete_nakedness": ["completely naked", "fully exposed", "nothing"],

    # Specific items
    "underwear_torn": ["underwear torn", "ripped", "destroyed"],
    "pants_pulled_down": ["pants down", "yanked", "around ankles"],
    "shirt_torn_open": ["shirt torn", "ripped open", "buttons flying"],

    # After - clothing
    "cant_wear_similar": ["can't wear similar", "triggers", "reminds"],
    "specific_clothing_trigger": ["specific clothing", "that type", "like what"],
    "dressed_as_armor": ["dress as armor", "layers", "covered up"],
    "cant_be_naked": ["can't be naked", "always covered", "vulnerability"],

    # Evidence in clothing
    "evidence_on_clothes": ["evidence on clothes", "stains", "tears"],
    "preserving_clothes": ["preserving", "evidence", "don't wash"],
    "threw_away_clothes": ["threw away", "couldn't keep", "burned"],
    "can_still_see_blood": ["can see blood", "stain", "won't come out"],
}

# ============================================================================
# NC DEEP: DISSOCIATION TYPES
# ============================================================================

NC_DEEP_DISSOCIATION_TYPES = {
    # Depersonalization
    "not_my_body": ["not my body", "foreign body", "borrowed"],
    "watching_self": ["watching self", "observer", "third person"],
    "body_as_object": ["body as object", "just flesh", "not me"],
    "disconnected_from_body": ["disconnected", "separate from", "floating away"],
    "body_not_real": ["body not real", "dreamlike", "unreal"],

    # Derealization
    "world_not_real": ["world not real", "dreamlike", "fake"],
    "everything_far_away": ["far away", "distant", "through glass"],
    "foggy_reality": ["foggy", "unclear", "hazy"],
    "time_not_real": ["time not real", "distorted", "meaningless"],
    "nothing_matters": ["nothing matters", "pointless", "unreal"],

    # Amnesia types
    "total_blackout": ["blackout", "don't remember", "gap"],
    "partial_memory": ["partial memory", "fragments", "pieces"],
    "emotional_amnesia": ["remember facts not feelings", "clinical memory", "detached recall"],
    "body_memory_only": ["body remembers", "mind blocked", "physical memory"],
    "memory_intrusion": ["memories intrude", "suddenly remember", "flash"],

    # Identity disruption
    "dont_know_who_i_am": ["don't know who", "lost self", "who am I"],
    "before_after_split": ["before and after", "different person", "split"],
    "part_that_experienced": ["part that experienced", "not all of me", "fragment"],
    "protective_alter": ["protective part", "took over", "someone else handled"],

    # Coming back
    "snapping_back": ["snapped back", "suddenly present", "jarring"],
    "slow_return": ["slowly returned", "gradually", "coming back"],
    "not_fully_back": ["not fully back", "partly gone", "still distant"],
    "grounding_needed": ["needed grounding", "anchor to present", "come back"],
}

# ============================================================================
# NC DEEP: FLASHBACK EXPERIENCES
# ============================================================================

NC_DEEP_FLASHBACKS = {
    # How flashbacks start
    "sudden_onset": ["sudden flashback", "without warning", "instantly"],
    "gradual_onset": ["gradual", "creeping", "building"],
    "trigger_identified": ["triggered by", "caused by", "specific trigger"],
    "trigger_unknown": ["don't know trigger", "random", "came from nowhere"],

    # What flashbacks feel like
    "reliving_completely": ["reliving", "back there", "happening again"],
    "sensory_flashback": ["sensory flashback", "feel it", "smell it"],
    "emotional_flashback": ["emotional flashback", "feeling without memory", "terror without image"],
    "visual_flashback": ["visual flashback", "seeing", "images"],
    "body_flashback": ["body flashback", "physical sensation", "body remembers"],

    # During flashback
    "cant_tell_now_from_then": ["can't tell", "now vs then", "time collapse"],
    "know_its_flashback_but": ["know it's flashback", "but feels real", "can't stop"],
    "completely_gone": ["completely gone", "not present", "fully there"],
    "partial_awareness": ["partial awareness", "know but also", "split"],

    # Coming out of flashback
    "orienting_to_present": ["orienting", "where am I", "what year"],
    "residual_feelings": ["residual feelings", "lingers", "doesn't go away"],
    "exhaustion_after": ["exhausted after", "drained", "wiped out"],
    "shame_after_flashback": ["ashamed after", "couldn't control", "embarrassed"],
    "grateful_its_over": ["grateful over", "relief", "survived it"],
}

# ============================================================================
# NC DEEP: NIGHTMARE SPECIFICS
# ============================================================================

NC_DEEP_NIGHTMARES = {
    # Nightmare content
    "exact_replay": ["exact replay", "what happened", "memory as dream"],
    "distorted_version": ["distorted", "changed details", "wrong but same"],
    "symbolic_nightmare": ["symbolic", "not literal", "meaning underneath"],
    "variations_nightmare": ["variations", "different ending", "what if"],
    "worse_in_dream": ["worse in dream", "even more", "amplified"],

    # Nightmare sensations
    "physical_sensations_dream": ["physical in dream", "felt it", "body felt"],
    "paralysis_in_dream": ["couldn't move in dream", "paralyzed", "frozen"],
    "trying_to_scream_dream": ["trying to scream", "no sound", "voice gone"],
    "running_cant_escape_dream": ["running can't escape", "legs won't work", "can't get away"],

    # Waking from nightmares
    "waking_in_panic": ["woke in panic", "gasping", "terrified"],
    "waking_mid_scream": ["woke screaming", "screaming awake", "sound woke me"],
    "waking_crying": ["woke crying", "tears on face", "sobbing awake"],
    "waking_frozen": ["woke frozen", "couldn't move", "paralyzed"],
    "waking_confused": ["woke confused", "where am I", "disoriented"],

    # After nightmare
    "afraid_to_sleep_again": ["afraid to sleep", "can't sleep again", "stay awake"],
    "checking_environment": ["checking room", "making sure", "safe"],
    "needing_comfort": ["needed comfort", "not alone", "someone"],
    "nightmare_hangover": ["nightmare hangover", "all day", "can't shake"],
    "dream_bleed": ["dream bleed", "still felt", "carried into day"],
}

# ============================================================================
# NC DEEP: FIRST HOURS/DAYS AFTER
# ============================================================================

NC_DEEP_FIRST_HOURS = {
    # Immediate after
    "not_moving_after": ["didn't move", "stayed still", "couldn't move"],
    "first_movement": ["first movement", "tried to move", "body wouldn't"],
    "assessing_damage": ["assessing damage", "checking body", "what's hurt"],
    "shock_state": ["in shock", "not processing", "numb"],

    # First actions
    "shower_compulsion": ["had to shower", "scrub clean", "wash off"],
    "hiding_evidence": ["hiding evidence", "cleaning up", "no one know"],
    "preserving_evidence": ["preserving evidence", "don't wash", "might report"],
    "getting_away": ["getting away", "leaving", "escape"],
    "collapsing_somewhere": ["collapsed", "fell down", "couldn't stand"],

    # First hours emotionally
    "delayed_reaction": ["delayed reaction", "hit later", "hours after"],
    "numbness_first": ["numb first", "couldn't feel", "shock buffer"],
    "crying_starting": ["crying started", "tears came", "broke down"],
    "rage_emerging": ["rage emerged", "anger came", "fury"],
    "terror_remaining": ["terror remained", "still scared", "fear didn't go"],

    # First days
    "going_through_motions": ["going through motions", "autopilot", "not present"],
    "cant_eat_first_days": ["couldn't eat", "no appetite", "food sickening"],
    "cant_sleep_first_days": ["couldn't sleep", "afraid to sleep", "nightmares"],
    "hypersomnia": ["sleeping constantly", "escape in sleep", "only sleep"],
    "isolating_first_days": ["isolated", "didn't tell anyone", "alone"],
}

# ============================================================================
# NC DEEP: TELLING SOMEONE
# ============================================================================

NC_DEEP_TELLING = {
    # Deciding to tell
    "building_to_telling": ["building up to", "working toward", "gathering courage"],
    "words_stuck": ["words stuck", "couldn't say", "in my throat"],
    "practicing_words": ["practiced words", "what to say", "how to tell"],
    "false_starts": ["false starts", "almost told", "chickened out"],
    "blurting_out": ["blurted out", "suddenly said", "didn't plan"],

    # The telling itself
    "cant_look_while_telling": ["couldn't look", "looked away", "eyes down"],
    "minimizing_while_telling": ["minimized", "not that bad", "played down"],
    "clinical_telling": ["clinical", "just facts", "no emotion"],
    "emotional_telling": ["emotional", "crying through", "breaking down"],
    "fragmented_telling": ["fragmented", "pieces", "not linear"],

    # Reactions feared
    "fear_of_blame": ["feared blame", "my fault", "what did you"],
    "fear_of_disbelief": ["feared disbelief", "lying", "making up"],
    "fear_of_pity": ["feared pity", "poor thing", "damaged"],
    "fear_of_change": ["feared things change", "look different", "treated different"],
    "fear_of_telling_others": ["fear tell others", "spread", "everyone know"],

    # Reactions received
    "believed": ["believed", "I believe you", "taken seriously"],
    "blamed": ["blamed", "your fault", "what did you expect"],
    "dismissed": ["dismissed", "not that bad", "get over it"],
    "supported": ["supported", "here for you", "whatever you need"],
    "overwhelmed_reaction": ["overwhelmed", "too much for them", "couldn't handle"],
}

# ============================================================================
# NC DEEP: THERAPY EXPERIENCES
# ============================================================================

NC_DEEP_THERAPY = {
    # Starting therapy
    "fear_of_therapy": ["afraid of therapy", "talking about", "opening up"],
    "finding_right_therapist": ["finding right one", "took time", "not first"],
    "wrong_therapist": ["wrong therapist", "didn't help", "made worse"],
    "right_therapist": ["right therapist", "finally found", "understood"],

    # Therapy modalities
    "talk_therapy": ["talk therapy", "discussing", "processing verbally"],
    "emdr": ["EMDR", "eye movement", "reprocessing"],
    "somatic": ["somatic therapy", "body based", "physical processing"],
    "cbt": ["CBT", "cognitive behavioral", "thoughts and behaviors"],
    "trauma_informed": ["trauma informed", "understood trauma", "specialized"],

    # Therapy experiences
    "hard_sessions": ["hard sessions", "difficult", "drained after"],
    "breakthrough_sessions": ["breakthrough", "realized", "shifted"],
    "regression_in_therapy": ["regression", "got worse before better", "harder first"],
    "progress_in_therapy": ["progress", "getting better", "healing"],
    "setbacks_in_therapy": ["setbacks", "not linear", "back and forth"],

    # Resistance in therapy
    "cant_talk_about_details": ["can't talk details", "too hard", "not yet"],
    "intellectualizing": ["intellectualizing", "not feeling", "just facts"],
    "minimizing_in_therapy": ["minimizing", "not that bad", "others worse"],
    "avoiding_topics": ["avoiding topics", "not ready", "skip that"],
    "finally_talking": ["finally talking", "ready now", "can say it"],
}

# ============================================================================
# NC DEEP: BODY RECLAMATION
# ============================================================================

NC_DEEP_BODY_RECLAMATION = {
    # Early stages
    "hating_body": ["hating body", "betrayed me", "enemy"],
    "disconnected_from_body": ["disconnected", "not mine", "foreign"],
    "cant_look_at_body": ["can't look", "avoid mirrors", "don't see"],
    "body_as_crime_scene": ["crime scene", "evidence", "what happened to"],

    # Beginning reclamation
    "first_gentle_touch": ["first gentle", "safe touch", "kind to self"],
    "learning_body_safe": ["learning safe", "body can be", "not always hurt"],
    "body_boundaries": ["setting boundaries", "my body", "I decide"],
    "saying_no_to_touch": ["saying no", "don't touch", "my choice"],

    # Progress
    "neutral_relationship": ["neutral", "not hate", "just body"],
    "moments_of_peace": ["moments of peace", "okay in body", "brief"],
    "reclaiming_parts": ["reclaiming parts", "this is mine", "taking back"],
    "body_as_ally": ["body as ally", "kept me alive", "survived"],

    # Sexuality reclamation
    "fear_of_sex": ["fear of sex", "can't do it", "terrified"],
    "wanting_to_want": ["wanting to want", "wish I could", "someday"],
    "first_chosen_touch": ["first chosen", "I chose this", "wanted"],
    "pleasure_as_mine": ["pleasure mine", "my pleasure", "for me"],
    "separating_trauma_sex": ["separating trauma", "this is different", "not that"],
}

# ============================================================================
# NC DEEP: COERCION SCRIPTS AND MANIPULATION TACTICS
# ============================================================================

NC_DEEP_COERCION_SCRIPTS = {
    # Minimizing language
    "its_not_a_big_deal": ["not a big deal", "making too much", "overreacting"],
    "just_relax": ["just relax", "calm down", "stop being dramatic"],
    "youre_overthinking": ["overthinking", "too sensitive", "reading into"],
    "its_just": ["it's just", "only", "nothing to worry"],

    # Gaslighting phrases
    "you_wanted_this": ["you wanted this", "you asked for", "begged for"],
    "you_led_me_on": ["led me on", "gave signals", "what did you expect"],
    "you_didnt_say_no": ["didn't say no", "never said stop", "didn't hear no"],
    "thats_not_what_happened": ["that's not what", "you're remembering wrong", "never happened"],
    "youre_imagining": ["imagining things", "making it up", "crazy"],

    # Guilt and obligation
    "after_everything_ive_done": ["after everything", "all I've done", "this is how you repay"],
    "you_owe_me": ["owe me", "deserve this", "my right"],
    "its_the_least_you_can_do": ["least you can do", "small thing", "not asking much"],
    "thought_you_loved_me": ["thought you loved", "if you loved me", "prove you love"],
    "thought_we_were_together": ["we're together", "relationship", "couples do this"],

    # Threats disguised
    "no_one_will_believe": ["no one will believe", "who would believe", "word against mine"],
    "youll_ruin_everything": ["ruin everything", "destroy", "your fault if"],
    "think_about_what_happens": ["think about", "consequences", "what happens if"],
    "people_will_find_out": ["people will find out", "everyone will know", "your reputation"],

    # False kindness
    "im_doing_this_for_you": ["doing this for you", "teaching you", "helping you"],
    "youll_thank_me": ["thank me later", "appreciate this", "good for you"],
    "im_the_only_one": ["only one who", "no one else would", "lucky to have me"],
    "taking_care_of_you": ["taking care", "looking after", "what you need"],

    # Isolation tactics
    "no_one_understands": ["no one understands", "only us", "our secret"],
    "they_dont_care": ["they don't care", "wouldn't understand", "wouldn't help"],
    "come_to_me": ["come to me", "I'm here for you", "rely on me"],
    "cant_trust_them": ["can't trust them", "they'll hurt you", "only trust me"],
}

# ============================================================================
# NC DEEP: PERPETRATOR PHYSICAL CONTROL TACTICS
# ============================================================================

NC_DEEP_PHYSICAL_CONTROL = {
    # Positioning control
    "moving_body_like_object": ["moved me like", "positioned", "arranged"],
    "forcing_position": ["forced into position", "made me", "put me"],
    "preventing_escape": ["blocked exit", "couldn't get away", "trapped"],
    "weight_pinning": ["weight on me", "couldn't move under", "crushed"],
    "grip_control": ["grip on", "held tight", "couldn't break free"],

    # Breath control
    "hand_over_mouth": ["hand over mouth", "couldn't breathe", "muffled"],
    "pillow_face": ["pillow on face", "couldn't see", "smothered"],
    "choking_to_control": ["choked", "strangled", "couldn't get air"],
    "threatening_breathing": ["stop breathing", "kill you", "air supply"],

    # Limb control
    "wrists_pinned": ["wrists pinned", "held down arms", "couldn't reach"],
    "ankles_held": ["ankles held", "legs forced", "couldn't kick"],
    "hair_control": ["hair grabbed", "head controlled", "pulled by hair"],
    "neck_control": ["hand on neck", "throat grabbed", "could feel power"],

    # Disabling resistance
    "exhausting_resistance": ["fought until tired", "gave up fighting", "no strength left"],
    "pain_to_stop_fighting": ["hurt until stopped", "pain made stop", "learned not to fight"],
    "overwhelming_with_force": ["so much stronger", "couldn't match", "overpowered completely"],

    # Using environment
    "against_hard_surface": ["against wall", "hard floor", "nowhere to go"],
    "corner_trapped": ["trapped in corner", "backed into", "no escape"],
    "confined_space": ["small space", "couldn't move", "claustrophobic"],
    "isolated_location": ["no one around", "isolated", "no help possible"],
}

# ============================================================================
# NC DEEP: VICTIM'S INTERNAL CALCULATIONS
# ============================================================================

NC_DEEP_SURVIVAL_CALCULATIONS = {
    # Risk assessment
    "will_fighting_make_worse": ["fighting make worse", "more violent if", "provoke"],
    "calculating_injury": ["how badly hurt", "survive this", "damage"],
    "weighing_options": ["what are options", "best chance", "least harm"],
    "reading_their_mood": ["reading mood", "how angry", "what might trigger"],

    # Compliance decisions
    "faster_if_comply": ["faster if", "over sooner", "just get through"],
    "less_pain_if_still": ["less pain if", "don't struggle", "be still"],
    "strategic_compliance": ["strategic", "buying time", "looking for moment"],
    "protective_compliance": ["protecting self", "minimize damage", "survive"],

    # Escape calculations
    "timing_escape_attempt": ["timing escape", "when to run", "moment comes"],
    "distance_to_door": ["distance to door", "how far", "could I make it"],
    "chance_of_success": ["chance of", "probably", "likely"],
    "consequences_of_failed_escape": ["if caught trying", "worse if fail", "punishment"],

    # External help
    "chance_someone_hears": ["someone hear", "if I scream", "loud enough"],
    "anyone_coming": ["anyone coming", "expecting someone", "will notice"],
    "how_long_until": ["how long until", "when will", "time until"],

    # After calculations
    "what_will_happen_after": ["what happens after", "when done", "then what"],
    "will_they_kill_me": ["will they kill", "let me live", "survive this"],
    "what_will_they_do": ["what will they do", "leave or stay", "finished"],
}

# ============================================================================
# NC DEEP: PHYSICAL DAMAGE DETAILED
# ============================================================================

NC_DEEP_PHYSICAL_DAMAGE = {
    # Visible injuries
    "bruising_visible": ["bruises showing", "marks visible", "couldn't hide"],
    "handprint_marks": ["handprint", "finger marks", "grip bruises"],
    "bite_wounds": ["bite marks", "teeth marks", "bleeding from bite"],
    "scratch_evidence": ["scratches", "nail marks", "defensive wounds"],
    "torn_clothing": ["torn clothes", "ripped", "stretched out"],

    # Internal damage
    "internal_tearing": ["tearing inside", "ripped", "bleeding inside"],
    "rectal_damage": ["rectal damage", "tearing", "bleeding from"],
    "genital_injury": ["genital injury", "swelling", "couldn't walk"],
    "internal_bleeding": ["bleeding internally", "pain deep", "damage inside"],

    # Pain locations
    "jaw_pain": ["jaw pain", "from being held", "couldn't open mouth"],
    "wrist_pain": ["wrist pain", "from restraint", "rope burns"],
    "hip_pain": ["hip pain", "from force", "bruised hips"],
    "neck_pain": ["neck pain", "from choking", "throat swollen"],
    "back_pain": ["back pain", "hard surface", "pressed against"],

    # Lasting physical
    "weeks_to_heal": ["weeks to heal", "still hurting", "not healed"],
    "permanent_damage": ["permanent damage", "never healed right", "always feel"],
    "scar_tissue": ["scar tissue", "healed wrong", "feels different"],
    "chronic_pain": ["chronic pain", "always hurts", "never went away"],
}

# ============================================================================
# NC DEEP: MEDICAL EXPERIENCE AFTER
# ============================================================================

NC_DEEP_MEDICAL_AFTER = {
    # Decision to seek help
    "afraid_to_go": ["afraid to go", "couldn't face", "too ashamed"],
    "talked_into_going": ["talked into", "convinced to", "made me go"],
    "forced_to_go": ["forced to go", "had to", "no choice"],
    "went_alone": ["went alone", "by myself", "no one with"],
    "someone_took_me": ["someone took me", "drove me", "came with"],

    # ER experience
    "waiting_room_shame": ["waiting room", "people looking", "what do they think"],
    "explaining_what_happened": ["explaining", "had to tell", "say out loud"],
    "not_believed_medical": ["didn't believe", "skeptical looks", "questioned"],
    "believed_immediately": ["believed immediately", "no judgment", "kind"],

    # Examination
    "physical_exam": ["physical exam", "had to undress", "looked at body"],
    "invasive_exam": ["invasive", "inside", "violated again"],
    "evidence_collection": ["collecting evidence", "swabs", "photos"],
    "clinical_coldness": ["clinical", "cold", "just procedure"],
    "gentle_exam": ["gentle", "asked permission", "went slow"],

    # Aftermath medical
    "sti_testing": ["STI test", "HIV test", "waiting for results"],
    "prophylactics": ["prophylactics", "prevention medication", "just in case"],
    "pregnancy_concern": ["pregnancy concern", "morning after", "what if"],
    "follow_up_appointments": ["follow up", "come back", "check again"],

    # Medical trauma
    "retraumatized_by_exam": ["retraumatized", "like it was happening", "exam triggered"],
    "body_examined_again": ["examined again", "touched again", "more people"],
    "medical_dissociation": ["dissociated during", "left body", "wasn't there"],
}

# ============================================================================
# NC DEEP: REPORTING/LEGAL EXPERIENCE
# ============================================================================

NC_DEEP_LEGAL_REPORTING = {
    # Decision to report
    "debating_reporting": ["should I report", "what's the point", "will it matter"],
    "pressure_to_report": ["pressure to", "should report", "have to"],
    "choosing_not_report": ["chose not to", "couldn't face", "what's the point"],
    "pressure_not_report": ["told not to", "don't tell", "keep quiet"],

    # Police experience
    "police_interview": ["police interview", "told them", "statement"],
    "repeating_story": ["repeat story", "again and again", "how many times"],
    "interrogation_feeling": ["felt interrogated", "like suspect", "didn't believe"],
    "supportive_officer": ["supportive officer", "kind", "patient"],
    "dismissive_officer": ["dismissive", "didn't care", "waste of time"],

    # Questions asked
    "what_were_you_wearing": ["what were you wearing", "what did you drink", "why were you there"],
    "why_didnt_you_fight": ["why didn't you fight", "why didn't you scream", "why didn't you leave"],
    "did_you_say_no": ["did you say no", "did you tell them", "exact words"],
    "relationship_questions": ["know them", "relationship", "history"],

    # Legal process
    "pressing_charges": ["pressing charges", "formal complaint", "pursue"],
    "case_dropped": ["case dropped", "not enough evidence", "nothing happened"],
    "going_to_court": ["going to court", "testify", "face them"],
    "seeing_them_in_court": ["saw them in court", "facing them", "there they were"],

    # Outcomes
    "not_guilty_verdict": ["not guilty", "walked free", "no consequence"],
    "guilty_verdict": ["guilty", "convicted", "believed"],
    "plea_deal": ["plea deal", "lesser charge", "compromise"],
    "no_justice": ["no justice", "nothing happened", "got away with it"],
}

# ============================================================================
# NC DEEP: SUPPORT SYSTEM RESPONSES
# ============================================================================

NC_DEEP_SUPPORT_RESPONSES = {
    # Believing responses
    "believed_immediately": ["believed me", "no doubt", "trusted my word"],
    "believed_after_time": ["eventually believed", "came around", "took time"],
    "still_dont_believe": ["still don't believe", "think I'm lying", "doubt"],

    # Helpful responses
    "just_listened": ["just listened", "didn't interrupt", "let me talk"],
    "asked_what_needed": ["asked what I needed", "how can I help", "what do you want"],
    "respected_choices": ["respected my choices", "my decision", "supported either way"],
    "practical_help": ["practical help", "place to stay", "money", "resources"],
    "accompaniment": ["came with me", "didn't leave alone", "stayed with"],

    # Harmful responses
    "asked_what_i_did": ["what did you do", "your fault", "shouldn't have"],
    "minimized": ["could be worse", "at least", "not that bad"],
    "made_about_them": ["made about them", "how they felt", "this affects me"],
    "told_to_move_on": ["just move on", "get over it", "in the past"],
    "gossiped": ["told others", "gossiped", "everyone knows"],
    "didnt_want_hear": ["didn't want to hear", "too much", "can't handle"],
    "blamed_me": ["blamed me", "your fault", "what did you expect"],

    # Changed relationships
    "treated_differently": ["treated differently", "looked at different", "not same"],
    "walking_on_eggshells": ["eggshells around me", "careful what say", "fragile"],
    "abandoned": ["abandoned", "left", "couldn't handle"],
    "grew_closer": ["grew closer", "bonded", "stronger relationship"],
}

# ============================================================================
# NC DEEP: RELATIONSHIP WITH PERPETRATOR AFTER
# ============================================================================

NC_DEEP_PERP_RELATIONSHIP_AFTER = {
    # Forced contact
    "have_to_see_them": ["have to see them", "can't avoid", "same circles"],
    "live_with_them": ["live with them", "same house", "no escape"],
    "work_with_them": ["work with them", "same office", "every day"],
    "family_gatherings": ["family gatherings", "holidays", "have to see"],

    # Their behavior after
    "acting_normal": ["acting normal", "like nothing happened", "pretending"],
    "smug_knowing": ["smug", "knowing looks", "power over me"],
    "threatening_silence": ["threatening", "keep quiet", "if you tell"],
    "pretending_relationship": ["pretending relationship", "acting like couple", "nothing wrong"],
    "apologizing": ["apologizing", "sorry", "won't happen again"],
    "denying": ["denying", "didn't happen", "lying"],

    # Having to interact
    "pretending_normal": ["pretending normal", "have to act", "can't show"],
    "forced_politeness": ["forced politeness", "have to be civil", "can't make scene"],
    "fear_seeing": ["fear seeing", "panic when see", "can't be near"],
    "anger_seeing": ["anger seeing", "rage", "want to scream"],

    # Breaking contact
    "finally_left": ["finally left", "got away", "escaped"],
    "no_contact": ["no contact", "blocked", "never again"],
    "restraining_order": ["restraining order", "legal protection", "can't come near"],
    "they_still_try": ["still try contact", "won't stop", "keeps trying"],
}

# ============================================================================
# NC DEEP: SELF-PERCEPTION CHANGES
# ============================================================================

NC_DEEP_SELF_PERCEPTION = {
    # Identity disruption
    "who_was_i_before": ["who was I before", "different person", "don't remember"],
    "dont_recognize_self": ["don't recognize self", "mirror stranger", "who is this"],
    "lost_sense_self": ["lost sense of self", "don't know who I am", "identity gone"],
    "defined_by_it": ["defined by it", "all I am now", "only identity"],

    # Self-worth
    "worthless_feeling": ["feel worthless", "no value", "damaged goods"],
    "unlovable_belief": ["unlovable", "no one will want", "too broken"],
    "deserved_it": ["deserved it", "my fault", "brought on self"],
    "dirty_feeling": ["feel dirty", "contaminated", "can't get clean"],
    "ruined_feeling": ["feel ruined", "destroyed", "nothing left"],

    # Shame vs guilt
    "shame_deep": ["deep shame", "core of me", "who I am"],
    "guilt_for_surviving": ["guilt for surviving", "why me", "should have fought"],
    "guilt_for_body_response": ["guilt for body", "responded physically", "betrayed self"],
    "guilt_for_not_preventing": ["could have prevented", "should have known", "my fault"],

    # Rebuilding identity
    "more_than_this": ["more than this", "not just survivor", "other parts of me"],
    "finding_self_again": ["finding self", "who I am", "underneath"],
    "new_identity": ["new identity", "different now", "changed"],
    "survivor_identity": ["survivor identity", "survived", "strength"],
    "refusing_victim_label": ["not victim", "won't be defined", "more than"],
}

# ============================================================================
# NC DEEP: SPECIFIC TRIGGER EXPERIENCES
# ============================================================================

NC_DEEP_TRIGGER_EXPERIENCES = {
    # Sudden triggers
    "smell_trigger": ["smell triggered", "scent", "cologne", "location smell"],
    "sound_trigger": ["sound triggered", "voice", "music", "phrase"],
    "touch_trigger": ["touch triggered", "certain touch", "type of contact"],
    "visual_trigger": ["saw something", "visual trigger", "reminded"],
    "date_trigger": ["date triggered", "anniversary", "time of year"],

    # Trigger response
    "instant_panic": ["instant panic", "heart racing", "can't breathe"],
    "frozen_by_trigger": ["frozen", "couldn't move", "paralyzed"],
    "overwhelming_memory": ["overwhelming memory", "back there", "reliving"],
    "had_to_leave": ["had to leave", "couldn't stay", "got out"],
    "breakdown_public": ["breakdown in public", "couldn't hide", "people saw"],

    # Managing triggers
    "learning_triggers": ["learning triggers", "what sets off", "identify"],
    "avoiding_triggers": ["avoiding triggers", "staying away", "can't be near"],
    "pushing_through": ["pushing through", "despite trigger", "forced self"],
    "grounding_techniques": ["grounding", "here and now", "techniques"],
    "safe_person_help": ["safe person", "helped through", "talked down"],

    # Trigger aftermath
    "exhausted_after": ["exhausted after", "drained", "no energy"],
    "shame_about_reaction": ["shame about reaction", "can't control", "weak"],
    "explaining_reaction": ["had to explain", "why I reacted", "telling"],
    "recovery_time_needed": ["needed time", "recover", "get back to normal"],
}

# ============================================================================
# NC DEEP: INTIMACY REBUILDING STAGES
# ============================================================================

NC_DEEP_INTIMACY_REBUILDING = {
    # Complete avoidance
    "cant_be_touched": ["can't be touched", "flinch away", "no contact"],
    "no_interest": ["no interest", "don't want", "desire gone"],
    "fear_of_sex": ["fear of sex", "terrified", "can't imagine"],
    "avoiding_intimacy": ["avoiding intimacy", "making excuses", "keeping distance"],

    # Tentative steps
    "allowing_hand_holding": ["hand holding okay", "this much", "small step"],
    "brief_touches": ["brief touches", "short", "then need space"],
    "hugs_sometimes": ["hugs sometimes", "from behind no", "has to be right"],
    "kissing_attempts": ["trying kissing", "sometimes okay", "depends"],

    # Working toward
    "communicating_needs": ["communicating needs", "telling partner", "what I need"],
    "safe_word_importance": ["safe word", "can stop anytime", "in control"],
    "going_slow": ["going slow", "no rush", "my pace"],
    "checking_in_during": ["checking in", "partner asks", "am I okay"],

    # Progress moments
    "first_successful_intimacy": ["first time successful", "could do it", "milestone"],
    "pleasure_felt_again": ["felt pleasure", "body responded", "good feeling"],
    "connection_during_sex": ["felt connection", "present", "with partner"],
    "reclaiming_sexuality": ["reclaiming sexuality", "mine again", "choosing this"],

    # Ongoing
    "good_days_bad_days": ["good days bad days", "varies", "unpredictable"],
    "patience_needed": ["patience needed", "takes time", "no timeline"],
    "setbacks_normal": ["setbacks normal", "not failure", "part of process"],
    "healing_not_linear": ["healing not linear", "up and down", "progress overall"],
}

# ============================================================================
# NC DEEP: TIME PERCEPTION DETAILED
# ============================================================================

NC_DEEP_TIME_PERCEPTION = {
    # During the event
    "time_stopped": ["time stopped", "frozen moment", "eternal second"],
    "time_stretched": ["time stretched", "lasted forever", "endless"],
    "time_compressed": ["time compressed", "over fast", "blur"],
    "lost_time": ["lost time", "don't know how long", "gaps"],
    "hyperaware_of_seconds": ["counting seconds", "every moment", "aware of time"],

    # Memory of time
    "dont_know_how_long": ["don't know how long", "could have been", "no idea"],
    "felt_like_hours": ["felt like hours", "eternity", "forever"],
    "only_minutes": ["only minutes", "so short", "quick"],
    "time_distorted_in_memory": ["time distorted", "remember differently", "feels longer"],

    # After - time passage
    "days_blur_together": ["days blur", "losing time", "don't know day"],
    "time_moves_slow": ["time moves slow", "each day endless", "drags"],
    "time_moves_fast": ["time moves fast", "already months", "where did time go"],
    "anniversary_awareness": ["anniversary aware", "date approaching", "that time of year"],

    # Healing and time
    "time_since_event": ["time since", "how long ago", "counting"],
    "time_doesnt_heal": ["time doesn't heal", "still fresh", "like yesterday"],
    "time_helps_some": ["time helps", "getting easier", "less raw"],
    "time_creates_distance": ["distance now", "further away", "not as close"],
}

# ============================================================================
# NC DEEP: VOICE AND SPEECH DURING
# ============================================================================

NC_DEEP_VOICE_SPEECH = {
    # Unable to speak
    "voice_frozen": ["voice frozen", "couldn't speak", "no sound came"],
    "mouth_open_no_sound": ["mouth open", "no sound", "silent scream"],
    "throat_closed": ["throat closed", "couldn't make sound", "blocked"],
    "too_scared_to_speak": ["too scared", "afraid to speak", "what if"],

    # Attempts to speak
    "tried_to_say_no": ["tried to say no", "wouldn't come out", "couldn't form words"],
    "whispered_stop": ["whispered stop", "quiet no", "barely audible"],
    "choked_on_words": ["choked on words", "couldn't get out", "stuck"],
    "words_not_working": ["words not working", "couldn't think", "brain blank"],

    # What was said
    "said_no": ["said no", "told them no", "clearly said"],
    "said_please_stop": ["please stop", "begged stop", "pleaded"],
    "said_dont": ["said don't", "don't do this", "please don't"],
    "said_youre_hurting_me": ["you're hurting me", "it hurts", "hurting"],
    "begged": ["begged", "please", "I'll do anything else"],
    "bargaining_words": ["bargaining", "what if instead", "I'll"],

    # Perpetrator silencing
    "told_to_be_quiet": ["told be quiet", "shut up", "don't speak"],
    "threatened_if_screamed": ["threatened if", "scream and", "make a sound"],
    "gagged": ["gagged", "couldn't speak", "mouth covered"],
    "hand_over_mouth": ["hand over mouth", "smothered sounds", "muffled"],

    # Voice after
    "couldnt_speak_after": ["couldn't speak after", "voice gone", "silent"],
    "voice_shaking": ["voice shaking", "trembling", "couldn't steady"],
    "speaking_felt_impossible": ["speaking felt impossible", "too much", "no words"],
}

# ============================================================================
# NC DEEP: PHYSICAL SENSATIONS MICRO-MOMENT
# ============================================================================

NC_DEEP_MICRO_SENSATIONS = {
    # Skin sensations
    "goosebumps_fear": ["goosebumps from fear", "skin prickling", "hair standing"],
    "cold_sweat": ["cold sweat", "clammy", "breaking out"],
    "hot_flush_fear": ["hot flush", "burning up", "fever feeling"],
    "numb_skin": ["skin numb", "couldn't feel", "dead feeling"],
    "hypersensitive_skin": ["hypersensitive", "every touch magnified", "too much"],

    # Internal sensations
    "stomach_dropping": ["stomach dropped", "falling feeling", "gut sinking"],
    "heart_pounding_chest": ["heart pounding", "chest", "could hear it"],
    "heart_in_throat": ["heart in throat", "choking", "couldn't swallow"],
    "chest_tight": ["chest tight", "couldn't expand", "constricted"],
    "dizzy_spinning": ["dizzy", "spinning", "couldn't focus"],

    # Muscle sensations
    "muscles_locked": ["muscles locked", "couldn't move", "frozen solid"],
    "trembling_uncontrolled": ["trembling", "couldn't stop", "shaking hard"],
    "gone_limp": ["gone limp", "no strength", "couldn't hold"],
    "rigid_with_fear": ["rigid", "stiff", "board-like"],

    # Pain sensations
    "sharp_sudden_pain": ["sharp pain", "sudden", "stabbing"],
    "burning_pain": ["burning", "on fire", "searing"],
    "tearing_sensation": ["tearing", "ripping", "splitting"],
    "dull_ache": ["dull ache", "deep pain", "throbbing"],
    "pressure_pain": ["pressure", "crushing", "weight pain"],
}

# ============================================================================
# NC DEEP: PERPETRATOR WORDS DURING
# ============================================================================

NC_DEEP_PERP_WORDS = {
    # Threats
    "threats_of_violence": ["I'll hurt you", "kill you", "make you sorry"],
    "threats_to_others": ["hurt your family", "tell everyone", "ruin you"],
    "implicit_threats": ["you know what happens", "don't make me", "wouldn't want"],

    # Degradation
    "derogatory_names": ["slut", "whore", "worthless", "disgusting"],
    "dehumanizing_words": ["thing", "hole", "object", "nothing"],
    "ownership_language": ["mine", "belong to me", "I own you"],

    # Gaslighting during
    "you_like_this": ["you like this", "know you want", "enjoying"],
    "your_body_says_yes": ["body says yes", "getting hard", "you're wet"],
    "stop_pretending": ["stop pretending", "don't act like", "we both know"],

    # Instructions
    "commanding_actions": ["do this", "move like", "say this"],
    "demanding_responses": ["tell me you like it", "say yes", "thank me"],
    "criticizing_during": ["wrong", "not like that", "pathetic"],

    # Taunting
    "mocking_fear": ["scared", "look at you", "pathetic"],
    "mocking_tears": ["crying won't help", "baby", "weak"],
    "enjoying_power": ["love seeing you", "so powerful", "helpless"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: POWER ASSERTION
# ============================================================================

NC_VILLAIN_POWER_ASSERTION = {
    # Establishing dominance
    "who_is_in_charge": ["who's in charge here", "I'm in charge now", "you answer to me"],
    "youre_nothing": ["you're nothing", "insignificant", "beneath me"],
    "look_at_me_command": ["look at me", "eyes on me", "don't look away"],
    "dont_you_dare": ["don't you dare", "wouldn't dream of", "think twice"],
    "i_said_command": ["I said", "did you hear me", "when I tell you"],

    # Physical power
    "feel_how_strong": ["feel how strong", "can't fight me", "stronger than you"],
    "stop_struggling": ["stop struggling", "give up", "won't help"],
    "you_cant_stop_me": ["can't stop me", "nothing you can do", "inevitable"],
    "hold_still": ["hold still", "don't move", "stay right there"],
    "nowhere_to_go": ["nowhere to go", "can't run", "can't escape"],

    # Authority power
    "im_your_superior": ["I'm your superior", "above you", "you report to me"],
    "i_make_the_rules": ["I make the rules", "my house", "my world"],
    "you_do_what_i_say": ["do what I say", "my orders", "obey"],
    "because_i_can": ["because I can", "because I want to", "why not"],

    # Control assertions
    "i_control_everything": ["I control everything", "your life is mine", "every part of you"],
    "you_have_no_choice": ["have no choice", "not up to you", "no say"],
    "this_is_happening": ["this is happening", "accept it", "nothing changes it"],
    "i_decide_when": ["I decide when", "when I'm done", "when I say so"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: DEGRADATION EXTENSIVE
# ============================================================================

NC_VILLAIN_DEGRADATION = {
    # Sexual degradation
    "such_a_slut": ["such a slut", "little whore", "dirty slut"],
    "made_for_this": ["made for this", "born for this", "this is your purpose"],
    "just_a_hole": ["just a hole", "nothing but a", "that's all you are"],
    "easy_prey": ["easy", "so easy", "knew you'd be easy"],
    "desperate_for_it": ["desperate for it", "gagging for it", "been wanting this"],

    # Character attacks
    "worthless_person": ["worthless", "pathetic excuse", "waste of space"],
    "you_disgust_me": ["disgust me", "pathetic", "repulsive"],
    "no_one_wants_you": ["no one wants you", "who would want", "lucky I bother"],
    "damaged_goods": ["damaged goods", "ruined", "used up"],
    "youre_nothing_special": ["nothing special", "dime a dozen", "replaceable"],

    # Intelligence attacks
    "so_stupid": ["so stupid", "dumb", "can't even"],
    "did_you_think": ["did you think", "thought you could", "naive"],
    "falling_for_it": ["fell for it", "so gullible", "too easy to trick"],

    # Comparisons
    "worse_than_expected": ["worse than expected", "disappointing", "thought you'd be better"],
    "compared_to_others": ["others were better", "had better", "you're the worst"],
    "below_standards": ["below standards", "not good enough", "barely acceptable"],

    # Body degradation
    "body_insults": ["look at yourself", "that body", "you call that"],
    "size_mockery": ["so small", "pathetic size", "that's it"],
    "appearance_mockery": ["ugly", "hideous", "look at your face"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: GASLIGHTING EXTENSIVE
# ============================================================================

NC_VILLAIN_GASLIGHTING = {
    # Desire projection
    "you_want_this": ["you want this", "know you want it", "been thinking about this"],
    "your_body_proves": ["body proves it", "look how you're reacting", "body doesn't lie"],
    "you_came_here": ["you came here", "you showed up", "you didn't leave"],
    "you_dressed_for_this": ["dressed like this", "what did you expect", "asking for it"],
    "you_led_me_on": ["led me on", "been teasing", "flirting all night"],

    # Reality denial
    "this_isnt_happening": ["not what you think", "not what it looks like", "misunderstanding"],
    "youll_forget": ["you'll forget", "won't remember", "never happened"],
    "no_one_believes": ["no one will believe you", "word against mine", "who'd believe"],
    "making_it_up": ["making it up", "imagining things", "in your head"],
    "youre_crazy": ["you're crazy", "losing it", "unstable"],

    # Blame shifting
    "you_made_me": ["you made me", "your fault", "you caused this"],
    "if_you_hadnt": ["if you hadn't", "none of this if", "you started it"],
    "what_did_you_expect": ["what did you expect", "what did you think would happen", "obvious"],
    "you_knew_what_was_coming": ["knew what was coming", "saw the signs", "could have left"],

    # Minimizing
    "its_not_that_bad": ["not that bad", "could be worse", "exaggerating"],
    "youre_overreacting": ["overreacting", "dramatic", "making a scene"],
    "its_just_sex": ["just sex", "not a big deal", "everyone does this"],
    "youll_get_over_it": ["get over it", "move on", "forget about it"],

    # Consent rewriting
    "you_didnt_say_no": ["didn't say no", "never heard no", "didn't stop me"],
    "you_could_have_left": ["could have left", "door was right there", "didn't run"],
    "you_stopped_fighting": ["stopped fighting", "gave up", "accepted it"],
    "you_came_so": ["you came", "you finished", "body wanted it"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: THREATS COMPREHENSIVE
# ============================================================================

NC_VILLAIN_THREATS = {
    # Violence threats
    "ill_hurt_you_more": ["hurt you more", "make it worse", "haven't started"],
    "dont_make_me_angry": ["don't make me angry", "won't like what happens", "when I'm angry"],
    "i_can_kill_you": ["could kill you", "end you", "no one would know"],
    "real_pain": ["show you real pain", "haven't felt pain yet", "just the beginning"],
    "ill_make_you_scream": ["make you scream", "really scream", "beg for mercy"],

    # Social threats
    "ill_tell_everyone": ["tell everyone", "everyone will know", "your secret out"],
    "destroy_your_reputation": ["destroy reputation", "ruin you", "no one will respect"],
    "your_family_will_know": ["family will know", "tell your parents", "what would they think"],
    "everyone_will_see": ["everyone will see", "pictures", "videos"],
    "social_destruction": ["destroy your life", "make sure everyone", "nowhere to hide"],

    # Career/livelihood threats
    "youll_lose_everything": ["lose everything", "job gone", "career over"],
    "i_have_power_over_career": ["your career", "one word from me", "I control your future"],
    "recommendation_threats": ["recommendation", "reference", "good word or bad"],
    "ill_fire_you": ["fire you", "out on the street", "never work again"],

    # Relationship threats
    "ill_tell_your_partner": ["tell your partner", "boyfriend will know", "husband finds out"],
    "no_one_will_love_you": ["no one will love you", "who would want", "damaged"],
    "ill_take_them_away": ["take them away", "lose them", "never see again"],

    # Physical constraint threats
    "dont_try_to_run": ["don't try to run", "catch you", "won't get far"],
    "locked_in": ["locked in", "can't get out", "no escape"],
    "no_one_can_hear": ["no one can hear", "scream all you want", "soundproof"],
    "no_ones_coming": ["no one's coming", "no rescue", "just us"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: FALSE INTIMACY/TWISTED AFFECTION
# ============================================================================

NC_VILLAIN_FALSE_INTIMACY = {
    # Twisted love
    "i_love_you_twisted": ["I love you", "do this because I love", "this is love"],
    "no_one_loves_you_like_i_do": ["no one loves you like I do", "only I love you", "love you most"],
    "this_is_how_i_show_love": ["how I show love", "special to me", "wouldn't do this to anyone else"],
    "youre_special_to_me": ["special to me", "chosen you", "only you"],

    # Possession as affection
    "youre_mine": ["you're mine", "belong to me", "no one else's"],
    "made_for_me": ["made for me", "perfect for me", "meant to be mine"],
    "never_letting_go": ["never let you go", "always mine", "keep you forever"],
    "only_want_you": ["only want you", "no one else", "obsessed with you"],

    # Caretaker pretense
    "taking_care_of_you": ["taking care of you", "looking after you", "what you need"],
    "teaching_you": ["teaching you", "showing you", "learning from me"],
    "good_for_you": ["good for you", "helping you", "making you better"],
    "youll_understand_someday": ["understand someday", "thank me later", "for your own good"],

    # Intimacy coercion
    "dont_you_trust_me": ["don't you trust me", "thought you trusted", "after everything"],
    "we_have_something_special": ["something special", "connection", "between us"],
    "no_one_knows_you_like_i_do": ["knows you like I do", "understand you", "see the real you"],
    "we_belong_together": ["belong together", "meant to be", "fate"],

    # Post-act "affection"
    "wasnt_that_good": ["wasn't that good", "felt good right", "we both enjoyed"],
    "see_how_good_we_are": ["how good we are", "together", "chemistry"],
    "next_time_better": ["next time", "again soon", "when we do this again"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: COMMANDS AND INSTRUCTIONS
# ============================================================================

NC_VILLAIN_COMMANDS = {
    # Position commands
    "get_on_your_knees": ["get on your knees", "kneel", "down"],
    "turn_over": ["turn over", "on your stomach", "face down"],
    "spread_your_legs": ["spread your legs", "open up", "wider"],
    "bend_over": ["bend over", "lean forward", "arch your back"],
    "dont_move": ["don't move", "stay still", "freeze"],

    # Action commands
    "open_your_mouth": ["open your mouth", "open up", "wider"],
    "take_it": ["take it", "all of it", "take it all"],
    "keep_going": ["keep going", "don't stop", "continue"],
    "faster_slower": ["faster", "slower", "my pace"],
    "be_quiet": ["be quiet", "shut up", "not a sound"],

    # Verbal commands
    "say_you_want_it": ["say you want it", "tell me you want", "beg for it"],
    "say_my_name": ["say my name", "call me", "who am I"],
    "thank_me": ["thank me", "say thank you", "grateful"],
    "apologize": ["apologize", "say sorry", "beg forgiveness"],
    "tell_me_youre_mine": ["tell me you're mine", "say you belong", "who owns you"],

    # Compliance demands
    "stop_crying": ["stop crying", "no tears", "dry those eyes"],
    "look_at_me_while": ["look at me", "eyes open", "watch"],
    "dont_look_away": ["don't look away", "keep watching", "see this"],
    "relax": ["relax", "loosen up", "stop tensing"],
    "enjoy_it": ["enjoy it", "have fun", "feel good"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: TAUNTING AND MOCKING
# ============================================================================

NC_VILLAIN_TAUNTING = {
    # Fear mocking
    "look_at_you_shaking": ["look at you shaking", "trembling", "so scared"],
    "pathetic_fear": ["pathetic", "afraid of little old me", "big bad wolf"],
    "scared_little": ["scared little", "frightened", "terrified"],
    "that_fear_in_your_eyes": ["fear in your eyes", "love that look", "delicious fear"],

    # Weakness mocking
    "so_weak": ["so weak", "can't even fight", "helpless"],
    "thought_you_were_tough": ["thought you were tough", "all talk", "not so brave now"],
    "cant_do_anything": ["can't do anything", "powerless", "useless"],
    "gave_up_so_easily": ["gave up so easily", "no fight", "disappointed"],

    # Tears mocking
    "crying_already": ["crying already", "tears already", "didn't take long"],
    "cry_all_you_want": ["cry all you want", "no one cares", "won't help"],
    "pretty_when_you_cry": ["pretty when you cry", "love those tears", "keep crying"],
    "baby_gonna_cry": ["baby gonna cry", "poor baby", "need a tissue"],

    # Humiliation taunting
    "everyone_would_laugh": ["everyone would laugh", "if they could see", "how pathetic"],
    "this_is_what_you_are": ["this is what you are", "your true self", "natural state"],
    "remember_this": ["remember this", "never forget", "think about this"],
    "this_is_all_youre_good_for": ["all you're good for", "your purpose", "born for this"],

    # Physical taunting
    "you_like_this_dont_you": ["like this don't you", "body says yes", "can't hide"],
    "look_how_you_respond": ["look how you respond", "body betrays you", "can't control"],
    "getting_hard_wet": ["getting hard", "getting wet", "body knows"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: BODY COMMENTARY
# ============================================================================

NC_VILLAIN_BODY_COMMENTARY = {
    # Ownership of body
    "this_body_is_mine": ["this body is mine", "belongs to me now", "I own this"],
    "every_part_of_you": ["every part of you", "all mine", "nothing hidden"],
    "examining_you": ["let me look at you", "see all of you", "inspecting"],
    "this_is_mine_now": ["this is mine now", "taking this", "claiming"],

    # Objectification
    "look_at_this": ["look at this", "what we have here", "nice"],
    "built_for_this": ["built for this", "perfect for", "made to be used"],
    "tight_loose_commentary": ["so tight", "take it", "perfect fit"],
    "body_rating": ["rate you", "score this", "not bad"],

    # Forced appreciation
    "say_you_like_your_body_being": ["tell me you like", "admit it feels", "say it's good"],
    "your_body_wants_this": ["body wants this", "responding", "can't lie"],
    "natural_reaction": ["natural reaction", "can't control it", "body knows"],

    # Degrading commentary
    "disgusting_body_talk": ["disgusting", "should be ashamed", "pathetic body"],
    "comparison_to_others_body": ["seen better", "not much to look at", "disappointing"],
    "marking_claiming": ["marking you", "leaving marks", "so everyone knows"],

    # During act commentary
    "how_it_feels": ["feel that", "how does that feel", "taking it so well"],
    "almost_done": ["almost done", "little more", "not much longer"],
    "youre_doing_well": ["doing so well", "good job", "that's it"],
    "take_more": ["take more", "can handle more", "not enough"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: SILENCING TACTICS
# ============================================================================

NC_VILLAIN_SILENCING = {
    # Direct silencing
    "shut_up": ["shut up", "be quiet", "silence"],
    "not_a_word": ["not a word", "don't speak", "no talking"],
    "one_more_sound": ["one more sound", "make another noise", "if you scream"],
    "ill_give_you_something_to_scream_about": ["give you something to scream about", "really hurt you", "know what pain is"],

    # Muffling threats
    "ill_gag_you": ["gag you", "shut you up", "something in that mouth"],
    "dont_make_me_silence_you": ["make me silence you", "shut you up myself", "ways to keep quiet"],

    # Consequence silencing
    "if_you_tell": ["if you tell", "if you say anything", "word gets out"],
    "no_one_believes": ["no one will believe", "who would believe you", "your word against"],
    "think_what_happens": ["think what happens", "consequences", "careful what you say"],
    "keep_this_between_us": ["between us", "our secret", "no one needs to know"],

    # Emotional silencing
    "youll_only_make_it_worse": ["make it worse", "harder on yourself", "just accept"],
    "fighting_is_pointless": ["pointless to fight", "won't change anything", "give up"],
    "screaming_wont_help": ["screaming won't help", "no one's coming", "waste of breath"],

    # After silencing
    "dont_tell_anyone": ["don't tell anyone", "keep quiet", "our secret"],
    "remember_what_happens": ["remember what happens", "know what I'll do", "if you talk"],
    "act_normal": ["act normal", "pretend nothing happened", "no one knows"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: AFTERMATH SPEECH
# ============================================================================

NC_VILLAIN_AFTERMATH_SPEECH = {
    # Dismissal
    "that_wasnt_so_bad": ["wasn't so bad", "not terrible", "survived"],
    "see_youre_fine": ["see you're fine", "not hurt", "stop being dramatic"],
    "what_are_you_complaining_about": ["complaining about", "nothing to cry about", "grow up"],
    "get_over_it": ["get over it", "move on", "in the past"],

    # Continued threats
    "this_stays_between_us": ["stays between us", "don't tell", "secret"],
    "remember_what_i_said": ["remember what I said", "forget the threat", "still applies"],
    "i_know_where_you_live": ["know where you live", "can find you", "anywhere"],
    "next_time": ["next time", "do this again", "whenever I want"],

    # Reframing
    "you_wanted_this": ["you wanted this", "asked for it", "begged for it"],
    "we_both_enjoyed": ["we both enjoyed", "good time", "mutual"],
    "see_it_wasnt_bad": ["see wasn't bad", "not so terrible", "good even"],

    # Clean up orders
    "clean_yourself_up": ["clean yourself up", "make yourself presentable", "can't look like that"],
    "get_dressed": ["get dressed", "put clothes on", "look normal"],
    "fix_your_face": ["fix your face", "stop crying", "smile"],

    # Final control
    "dont_forget_who_owns_you": ["don't forget", "who owns you", "belong to me"],
    "ill_be_back": ["I'll be back", "see you again", "not done with you"],
    "same_time_next": ["same time", "again soon", "regular arrangement"],
    "youre_lucky": ["you're lucky", "could be worse", "went easy"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: RELATIONSHIP-SPECIFIC
# ============================================================================

NC_VILLAIN_BOSS_DIALOGUE = {
    # Authority leverage
    "your_job_depends": ["job depends", "want to keep working", "employment"],
    "promotion_on_the_line": ["promotion", "career advancement", "good word"],
    "i_can_destroy_your_career": ["destroy career", "never work again", "blacklist"],
    "this_is_how_it_works": ["how it works here", "pay to play", "everyone does"],
    "want_to_succeed": ["want to succeed", "get ahead", "price of success"],
}

NC_VILLAIN_TEACHER_DIALOGUE = {
    # Academic leverage
    "your_grade_depends": ["grade depends", "pass or fail", "transcript"],
    "letter_of_recommendation": ["recommendation", "future schools", "your future"],
    "i_believed_in_you": ["believed in you", "special student", "potential"],
    "extra_help": ["extra help", "private tutoring", "special attention"],
    "office_hours": ["office hours", "my office", "stay after"],
}

NC_VILLAIN_FAMILY_DIALOGUE = {
    # Family leverage
    "this_is_what_families_do": ["families do", "normal", "between us"],
    "dont_tell_mom_dad": ["don't tell", "hurt them", "destroy the family"],
    "ill_always_be_here": ["always be here", "can't escape family", "wherever you go"],
    "i_raised_you": ["raised you", "gave you everything", "owe me"],
    "no_one_will_believe_over_family": ["believe family", "who would believe", "your word"],
}

NC_VILLAIN_INTIMATE_PARTNER_DIALOGUE = {
    # Relationship leverage
    "if_you_loved_me": ["if you loved me", "prove your love", "do this for me"],
    "owe_me_this": ["owe me", "after everything", "least you can do"],
    "this_is_your_duty": ["your duty", "what partners do", "obligation"],
    "ill_leave_you": ["leave you", "no one else will want", "alone forever"],
    "youre_overreacting_partner": ["overreacting", "just sex", "what couples do"],
}

NC_VILLAIN_STRANGER_DIALOGUE = {
    # Random cruelty
    "wrong_place_wrong_time": ["wrong place", "bad luck", "shouldn't have been here"],
    "nothing_personal": ["nothing personal", "just business", "random"],
    "youre_just_convenient": ["convenient", "available", "there"],
    "dont_care_who_you_are": ["don't care who", "doesn't matter", "irrelevant"],
    "never_see_me_again": ["never see me again", "forget my face", "I'm nobody"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: DURING PENETRATION
# ============================================================================

NC_VILLAIN_DURING_PENETRATION = {
    # Initial entry
    "feel_that": ["feel that", "there it is", "inside you now"],
    "take_it_all": ["take it all", "every inch", "all the way"],
    "so_tight_villain": ["so tight", "squeezing me", "perfect fit"],
    "opening_up": ["opening up", "taking me", "letting me in"],

    # During thrusting
    "good_isnt_it": ["good isn't it", "feels good", "knew you'd like"],
    "taking_it_so_well": ["taking it well", "good boy", "handling it"],
    "deeper_villain": ["going deeper", "all the way", "feel me"],
    "harder_villain": ["harder now", "really feel it", "gonna hurt"],

    # Near climax
    "almost_there": ["almost there", "gonna cum", "close"],
    "youre_making_me": ["making me", "doing this to me", "your fault"],
    "cum_inside": ["cum inside", "fill you up", "leave it in"],
    "take_my_load": ["take my load", "every drop", "swallow it"],

    # After finishing
    "that_was_good": ["that was good", "needed that", "satisfied"],
    "your_turn": ["your turn", "now you", "make you cum"],
    "not_done_yet": ["not done yet", "again", "more"],
    "stay_still_after": ["stay still", "don't move", "inside you still"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: ORAL FORCE
# ============================================================================

NC_VILLAIN_ORAL_FORCE = {
    # Commands
    "open_mouth_command": ["open your mouth", "open wide", "wider"],
    "suck_it": ["suck it", "use your tongue", "properly"],
    "no_teeth": ["no teeth", "careful", "hurt me and"],
    "deeper_oral": ["deeper", "all the way", "throat"],

    # During
    "thats_it_oral": ["that's it", "good", "keep going"],
    "look_up_at_me": ["look up at me", "eyes on me", "watch me"],
    "swallow_command": ["swallow", "don't spit", "every drop"],
    "gag_on_it": ["gag on it", "choke", "take it"],

    # Control
    "holding_head": ["holding your head", "control this", "my pace"],
    "cant_pull_away": ["can't pull away", "stay there", "not done"],
    "breathe_when_i_say": ["breathe when I say", "I control air", "permission"],

    # Degradation oral
    "made_for_this_oral": ["mouth made for this", "perfect lips", "born to suck"],
    "practice_makes_perfect": ["practice", "getting better", "learn"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: PSYCHOLOGICAL BREAKING
# ============================================================================

NC_VILLAIN_PSYCHOLOGICAL = {
    # Breaking will
    "give_up_fighting": ["give up", "stop fighting", "accept it"],
    "this_is_your_life_now": ["your life now", "new normal", "get used to"],
    "breaking_you": ["breaking you", "piece by piece", "nothing left"],
    "who_you_were": ["who you were", "that person's gone", "new you"],

    # Identity destruction
    "forget_your_name": ["forget your name", "doesn't matter", "call you what I want"],
    "no_one_remembers": ["no one remembers you", "already forgotten", "don't exist"],
    "youre_nothing_now": ["nothing now", "erased", "remake you"],
    "belong_to_me_now": ["belong to me", "mine now", "property"],

    # Hope destruction
    "no_ones_coming_for_you": ["no one's coming", "no rescue", "given up on you"],
    "this_will_never_end": ["never end", "forever", "rest of your life"],
    "no_escape_ever": ["no escape", "accept it", "can't leave"],
    "hope_is_pointless": ["hope is pointless", "give up hope", "there is none"],

    # Reality distortion
    "this_is_all_there_is": ["all there is", "this is reality", "nothing else"],
    "world_outside_doesnt_exist": ["outside doesn't exist", "just us", "only this"],
    "time_has_no_meaning": ["time meaningless", "could be forever", "who knows"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: MANIPULATIVE PRAISE
# ============================================================================

NC_VILLAIN_MANIPULATIVE_PRAISE = {
    # Twisted compliments
    "youre_so_beautiful_villain": ["so beautiful", "look at you", "pretty"],
    "perfect_body_villain": ["perfect body", "made for this", "gorgeous"],
    "special_victim": ["you're special", "chose you", "not just anyone"],
    "been_watching_you": ["been watching", "noticed you", "wanted you"],

    # Performance praise
    "doing_so_well": ["doing so well", "good job", "perfect"],
    "such_a_good": ["such a good", "obedient", "learned fast"],
    "better_than_expected": ["better than expected", "surprised me", "impressive"],
    "natural_at_this": ["natural at this", "born for it", "talent"],

    # Conditional praise
    "keep_being_good": ["keep being good", "stay good", "don't ruin it"],
    "good_things_if": ["good things if", "reward you", "be nice if"],
    "see_what_happens_when": ["see what happens", "when you behave", "good behavior"],

    # Possessive praise
    "my_good_boy": ["my good boy", "mine", "belong to me"],
    "all_mine": ["all mine", "no one else's", "just for me"],
    "made_you_this_way": ["made you this way", "trained you", "my creation"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: SPECIFIC ACTS COMMENTARY
# ============================================================================

NC_VILLAIN_ACTS_COMMENTARY = {
    # Undressing victim
    "lets_see_whats_under": ["let's see what's under", "show me", "take this off"],
    "nice_body_reveal": ["nice", "look at that", "what we have"],
    "stripping_you": ["stripping you", "piece by piece", "nothing hidden"],

    # Touching/groping
    "like_touching_you": ["like touching you", "feel good", "nice skin"],
    "exploring_your_body": ["exploring", "every inch", "all of you"],
    "cant_stop_touching": ["can't stop", "irresistible", "have to touch"],

    # Preparation/penetration prep
    "getting_you_ready": ["getting ready", "prepare you", "open you up"],
    "this_might_hurt": ["might hurt", "gonna hurt", "but I don't care"],
    "not_using_lube": ["no lube", "raw", "feel everything"],
    "using_fingers_first": ["fingers first", "stretch you", "make room"],

    # Position forcing
    "get_in_position": ["get in position", "like this", "want you here"],
    "stay_like_that": ["stay like that", "don't move", "perfect view"],
    "bending_you_over": ["bending you over", "face down", "ass up"],

    # Multiple rounds
    "going_again": ["going again", "not done", "more"],
    "round_two_villain": ["round two", "ready for more", "again"],
    "keep_going_until": ["until I'm done", "when I say", "not finished"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: RECORDED/WITNESSED SCENARIOS
# ============================================================================

NC_VILLAIN_RECORDING = {
    # Threats with recording
    "recording_this": ["recording this", "on camera", "video proof"],
    "everyone_will_see": ["everyone will see", "post this", "send to everyone"],
    "evidence_against_you": ["evidence", "proof you wanted", "see how you look"],
    "insurance_policy": ["insurance", "keep you quiet", "leverage"],

    # Forcing watching
    "watch_yourself": ["watch yourself", "see how you look", "camera there"],
    "smile_for_camera": ["smile for camera", "look pretty", "performing"],

    # Third party threats
    "bring_others": ["bring others", "friends want turns", "share you"],
    "letting_them_watch": ["letting them watch", "audience", "show"],
    "theyre_next": ["they're next", "waiting their turn", "after me"],
}

# ============================================================================
# NC VILLAIN DIALOGUE: TIME PRESSURE
# ============================================================================

NC_VILLAIN_TIME_PRESSURE = {
    # Limited time cruelty
    "have_to_be_quick": ["be quick", "not much time", "before they come back"],
    "every_second_counts": ["every second", "make it count", "fast"],
    "racing_against_time": ["racing", "hurry", "quickly"],

    # Extended time cruelty
    "all_night_villain": ["all night", "hours", "take my time"],
    "no_rush_villain": ["no rush", "all the time", "savor this"],
    "making_this_last": ["making this last", "slow", "enjoy every moment"],
    "we_have_forever": ["have forever", "no one coming", "endless"],

    # Deadline threats
    "before_they_get_back": ["before they get back", "have to hurry", "almost home"],
    "one_hour_villain": ["one hour", "that's all we have", "make it count"],
    "every_night": ["every night", "regular schedule", "get used to it"],
}

# ============================================================================
# NC VICTIM: INTERNAL PROTECTIVE THOUGHTS
# ============================================================================

NC_VICTIM_PROTECTIVE_THOUGHTS = {
    # Self-preservation
    "just_survive": ["just survive", "get through this", "stay alive"],
    "itll_be_over": ["it'll be over", "has to end", "eventually"],
    "dont_provoke": ["don't provoke", "stay calm", "don't make worse"],
    "do_what_they_say": ["do what they say", "comply", "less pain"],

    # Dissociative protection
    "go_somewhere_else": ["go somewhere else", "not here", "escape in mind"],
    "this_isnt_real": ["this isn't real", "just a dream", "not happening"],
    "im_not_here": ["I'm not here", "someone else", "not me"],
    "float_away": ["float away", "leave body", "above this"],

    # Bargaining thoughts
    "if_i_just": ["if I just", "maybe if", "what if I"],
    "ill_do_anything": ["I'll do anything", "whatever you want", "just stop"],
    "please_just": ["please just", "only this", "not that"],

    # Hope thoughts
    "someone_will_come": ["someone will come", "help coming", "rescue"],
    "it_has_to_end": ["has to end", "can't last forever", "eventually"],
    "ill_get_through": ["I'll get through", "survive this", "strong enough"],

    # Blame deflection
    "not_my_fault": ["not my fault", "didn't ask for", "did nothing wrong"],
    "theyre_the_monster": ["they're the monster", "not me", "their fault"],
}

# ============================================================================
# NC VICTIM: BODY SENSATIONS UNWANTED AROUSAL
# ============================================================================

NC_VICTIM_UNWANTED_AROUSAL = {
    # Physical response horror
    "body_betraying": ["body betraying", "responding against will", "why is body"],
    "getting_hard_unwanted": ["getting hard", "didn't want to", "body responding"],
    "physical_pleasure_horror": ["felt good physically", "hated that it", "body liked"],
    "orgasm_unwanted": ["came against will", "body forced", "orgasm without consent"],

    # Internal conflict
    "doesnt_mean_wanted": ["doesn't mean wanted", "body automatic", "not consent"],
    "hate_my_body": ["hate my body", "betrayed by", "can't trust"],
    "shame_of_response": ["ashamed of response", "shouldn't have", "disgusted with self"],
    "confusion_about_body": ["confused about body", "why did it", "doesn't mean"],

    # Perpetrator using response
    "see_you_like_it": ["see you like it", "body says yes", "wanted it"],
    "made_you_hard": ["made you hard", "aroused you", "proved you wanted"],
    "came_from_this": ["came from this", "enjoyed it", "body proves"],

    # Processing after
    "body_response_trauma": ["traumatized by response", "can't trust body", "betrayal"],
    "pleasure_doesnt_equal_consent": ["pleasure doesn't equal", "automatic response", "not wanting"],
}

# ============================================================================
# NC VICTIM: SPECIFIC MOMENT DETAILS
# ============================================================================

NC_VICTIM_MOMENT_DETAILS = {
    # First touch
    "moment_of_first_touch": ["first touch", "hand on", "began"],
    "realization_moment": ["realized what", "understood then", "knew what was coming"],
    "freeze_moment": ["froze", "couldn't move", "paralyzed"],

    # During key moments
    "moment_of_entry": ["moment of entry", "when they", "felt them"],
    "worst_moment": ["worst moment", "peak of horror", "couldn't bear"],
    "pain_peak": ["pain peaked", "worst pain", "screamed"],
    "going_still": ["went still", "stopped fighting", "gave up"],

    # Watching/awareness
    "watching_it_happen": ["watching happen", "saw everything", "aware"],
    "feeling_every_second": ["every second", "each moment", "felt all"],
    "hyperaware": ["hyperaware", "every sensation", "magnified"],

    # Leaving body
    "felt_self_leave": ["felt self leave", "floated out", "not in body"],
    "watching_from_outside": ["watching from outside", "seeing from above", "not there"],
    "came_back_to_body": ["came back", "returned to body", "in body again"],
}

# ============================================================================
# NC VILLAIN: ESCALATION DIALOGUE
# ============================================================================

NC_VILLAIN_ESCALATION = {
    # Starting "nice"
    "lets_keep_this_easy": ["keep this easy", "doesn't have to hurt", "cooperate"],
    "be_good_and": ["be good and", "behave and", "this can be nice"],
    "dont_make_me_hurt": ["don't make me hurt", "don't want to", "you're making me"],

    # Escalating threats
    "now_youve_made_me": ["now you've made me", "brought this on", "your fault"],
    "should_have_listened": ["should have listened", "warned you", "now see"],
    "this_is_because_you": ["because you", "your doing", "made me"],

    # Full escalation
    "no_more_nice": ["no more nice", "done being gentle", "real now"],
    "wanted_it_rough": ["wanted it rough", "asked for this", "could have been easy"],
    "going_to_regret": ["going to regret", "sorry now", "see what happens"],

    # Control reassertion
    "remember_who_is_in_charge": ["remember who's in charge", "I'm the boss", "control"],
    "thought_you_learned": ["thought you learned", "need another lesson", "teach you again"],
}

# ============================================================================
# NC DEEP: HEARING THE PERPETRATOR'S BREATHING
# ============================================================================

NC_DEEP_PERP_BREATHING = {
    # Their sounds
    "heavy_breathing_on_me": ["heavy breathing", "breath on skin", "panting"],
    "breathing_in_ear": ["breathing in ear", "hot breath", "right in ear"],
    "grunting_sounds": ["grunting", "animal sounds", "primal"],
    "moaning_perpetrator": ["moaning", "pleasure sounds", "enjoying"],

    # Breath as threat
    "breath_getting_faster": ["breath faster", "speeding up", "close to"],
    "breath_on_neck": ["breath on neck", "behind me", "felt breath"],
    "hot_breath": ["hot breath", "warm on skin", "too close"],

    # Voice sounds
    "whispering_while": ["whispering", "in ear", "low voice"],
    "growling": ["growling", "low sound", "threatening"],
    "laughing_during": ["laughing", "chuckling", "amused"],

    # After sounds
    "satisfied_sigh": ["satisfied sigh", "done sound", "finished"],
    "heavy_breathing_after": ["heavy breathing after", "catching breath", "panting"],
}

# ============================================================================
# NC DEEP: VICTIM'S EYES DURING
# ============================================================================

NC_DEEP_VICTIM_EYES = {
    # Where looking
    "eyes_squeezed_shut": ["eyes shut", "squeezed closed", "couldn't look"],
    "staring_at_ceiling": ["staring at ceiling", "fixed point", "not seeing"],
    "staring_at_wall": ["staring at wall", "looking away", "anywhere else"],
    "eyes_unfocused": ["unfocused", "glazed", "not seeing"],
    "forced_to_look": ["forced to look", "made to watch", "look at me"],

    # Eye states
    "tears_blurring": ["tears blurring", "couldn't see through", "crying"],
    "dry_eyes_shock": ["dry eyes", "too shocked", "couldn't cry"],
    "blank_eyes": ["blank eyes", "empty", "no one there"],
    "terror_in_eyes": ["terror visible", "fear in eyes", "wide with fear"],

    # What saw
    "seeing_their_face": ["seeing their face", "looking at them", "their expression"],
    "couldnt_look_at_them": ["couldn't look", "turned away", "wouldn't see"],
    "saw_everything": ["saw everything", "watched", "witnessed"],
    "saw_nothing": ["saw nothing", "blind to", "blocked out"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC PHRASES DURING
# ============================================================================

NC_VILLAIN_SPECIFIC_PHRASES = {
    # Opening lines
    "been_waiting_for_this": ["been waiting for this", "finally", "moment I've wanted"],
    "knew_this_would_happen": ["knew this would happen", "inevitable", "always going to"],
    "thought_about_this": ["thought about this", "imagined this", "fantasized"],
    "dont_pretend_surprised": ["don't pretend surprised", "you knew", "saw it coming"],

    # During possession
    "youre_mine_now": ["you're mine now", "belong to me", "claimed you"],
    "no_one_elses": ["no one else's", "only mine", "don't share"],
    "marking_you": ["marking you", "everyone will know", "my territory"],
    "inside_you_now": ["inside you now", "part of you", "connected"],

    # Control statements
    "i_decide": ["I decide", "my choice", "when I say"],
    "not_your_choice": ["not your choice", "you don't decide", "I choose"],
    "do_as_youre_told": ["do as you're told", "follow orders", "obey"],
    "my_rules": ["my rules", "my game", "I make the rules"],

    # Finishing statements
    "gonna_cum_in_you": ["gonna cum in you", "fill you", "leave it inside"],
    "take_it_all": ["take it all", "every drop", "don't waste any"],
    "feel_that": ["feel that", "feel me", "can you feel"],
    "remember_this": ["remember this", "never forget", "think about this"],
}

# ============================================================================
# NC VILLAIN: QUESTIONS ASKED DURING
# ============================================================================

NC_VILLAIN_QUESTIONS = {
    # Rhetorical cruelty
    "you_like_that_question": ["you like that", "feels good right", "enjoying yourself"],
    "want_more_question": ["want more", "want me to stop", "had enough"],
    "whos_your_daddy": ["who's your daddy", "who owns you", "who do you belong to"],
    "what_are_you": ["what are you", "tell me what you are", "say it"],

    # Forced answers
    "say_yes": ["say yes", "tell me yes", "I want to hear yes"],
    "beg_me": ["beg me", "ask nicely", "say please"],
    "thank_me_question": ["going to thank me", "say thank you", "grateful"],
    "tell_me_you_want": ["tell me you want", "say you want this", "ask for it"],

    # Mocking questions
    "thought_you_were_strong": ["thought you were strong", "where's that fight", "given up"],
    "crying_already_question": ["crying already", "tears so soon", "that all it takes"],
    "cant_take_it": ["can't take it", "too much for you", "weak"],
    "wheres_your_hero": ["where's your hero", "no one coming", "all alone"],

    # Threatening questions
    "know_what_happens_if": ["know what happens if", "want to find out", "test me"],
    "want_me_to_hurt_you": ["want me to hurt you", "make this worse", "more pain"],
    "anyone_know_youre_here": ["anyone know you're here", "told anyone", "missing you"],
}

# ============================================================================
# NC VILLAIN: WHISPERED DIALOGUE
# ============================================================================

NC_VILLAIN_WHISPERS = {
    # Intimate threats
    "whispered_threats": ["whispered threat", "breath in ear", "quiet voice"],
    "soft_cruel_words": ["soft cruel", "gentle voice terrible words", "quiet menace"],
    "hissed_words": ["hissed", "through teeth", "sharp whisper"],
    "murmured_degradation": ["murmured", "low voice", "almost tender cruelty"],

    # Close ear dialogue
    "right_in_ear": ["right in ear", "lips against ear", "so close"],
    "only_you_can_hear": ["only you can hear", "between us", "secret"],
    "intimate_cruelty": ["intimate", "close", "personal"],
    "breath_with_words": ["felt breath with words", "warm air", "each word"],

    # Specific whispers
    "youre_so_tight_whisper": ["so tight", "perfect", "made for me"],
    "taking_it_well_whisper": ["taking it well", "good", "that's it"],
    "almost_done_whisper": ["almost done", "little more", "soon"],
    "gonna_remember_whisper": ["gonna remember", "never forget", "always"],
}

# ============================================================================
# NC VILLAIN: MULTIPLE PERPETRATOR DIALOGUE
# ============================================================================

NC_VILLAIN_MULTIPLE_PERP = {
    # Between perpetrators
    "my_turn": ["my turn", "let me", "want a turn"],
    "hold_him_down": ["hold him down", "keep him still", "got him"],
    "watch_this": ["watch this", "see how", "look at"],
    "can_you_believe": ["can you believe", "look at him", "pathetic"],

    # To victim about others
    "friends_want_turns": ["friends want turns", "everyone gets a go", "share you"],
    "theyre_watching": ["they're watching", "audience", "performing"],
    "make_them_proud": ["make them proud", "put on a show", "impress them"],
    "each_one_of_us": ["each one of us", "all of us", "everyone here"],

    # Group cruelty
    "taking_turns": ["taking turns", "one after another", "line up"],
    "at_the_same_time": ["same time", "together", "both at once"],
    "filming_for_others": ["filming", "others will see", "send to friends"],
}

# ============================================================================
# NC VILLAIN: PAUSING/CONTROL DIALOGUE
# ============================================================================

NC_VILLAIN_PAUSES = {
    # Deliberate pauses
    "lets_take_a_break": ["let's take a break", "rest for a moment", "not done yet"],
    "want_you_to_feel": ["want you to feel", "savor this", "every moment"],
    "no_rush": ["no rush", "all the time", "enjoy this"],
    "making_it_last": ["making it last", "prolonging", "drawing out"],

    # Control demonstrations
    "see_i_can_stop": ["see I can stop", "control", "when I want"],
    "could_end_this": ["could end this", "but I won't", "not yet"],
    "depends_on_you": ["depends on you", "your behavior", "good and I might"],
    "beg_me_to_stop": ["beg me to stop", "beg me to continue", "your choice"],

    # Resuming
    "ready_for_more": ["ready for more", "continue now", "where were we"],
    "missed_me": ["missed me", "want me back", "need it"],
    "cant_wait": ["can't wait", "need you now", "starting again"],
}

# ============================================================================
# NC VICTIM: FROZEN/PARALYSIS INTERNAL
# ============================================================================

NC_VICTIM_FROZEN_STATE = {
    # Physical frozen
    "body_wont_move": ["body won't move", "can't move", "frozen"],
    "legs_wont_work": ["legs won't work", "can't run", "paralyzed"],
    "arms_useless": ["arms useless", "can't push away", "no strength"],
    "voice_trapped": ["voice trapped", "can't scream", "nothing comes out"],

    # Mental frozen
    "brain_stopped": ["brain stopped", "can't think", "blank"],
    "cant_process": ["can't process", "not computing", "doesn't make sense"],
    "this_isnt_happening": ["this isn't happening", "not real", "dream"],
    "shock_state": ["shock", "shut down", "offline"],

    # Time frozen
    "time_stopped": ["time stopped", "frozen moment", "eternal"],
    "slow_motion": ["slow motion", "each second", "stretched"],
    "outside_of_time": ["outside time", "no time", "suspended"],

    # Thawing
    "started_to_feel_again": ["started to feel", "coming back", "sensation returning"],
    "movement_returned": ["movement returned", "could move", "unfroze"],
    "thought_returned": ["thought returned", "mind working", "could think"],
}

# ============================================================================
# NC VICTIM: COUNTING/COPING DURING
# ============================================================================

NC_VICTIM_COUNTING_COPING = {
    # Counting
    "counting_seconds": ["counting seconds", "one two three", "each second"],
    "counting_thrusts": ["counting", "how many", "almost over"],
    "counting_breaths": ["counting breaths", "in out", "focus on breath"],
    "counting_anything": ["counting anything", "ceiling tiles", "something"],

    # Mental escape
    "thinking_of_elsewhere": ["thinking elsewhere", "somewhere else", "not here"],
    "memory_escape": ["memory", "happy memory", "safe place"],
    "fantasy_escape": ["fantasy", "imagining", "pretending"],
    "planning_after": ["planning after", "when done", "what I'll do"],

    # Mantras
    "itll_be_over": ["it'll be over", "almost done", "ending"],
    "stay_alive": ["stay alive", "survive", "just survive"],
    "youre_strong": ["you're strong", "can do this", "survive this"],
    "not_my_fault": ["not my fault", "their fault", "I did nothing wrong"],
}

# ============================================================================
# NC VILLAIN: CLOTHING SPECIFIC
# ============================================================================

NC_VILLAIN_CLOTHING = {
    # Undressing commands
    "take_it_off": ["take it off", "undress", "strip"],
    "ill_do_it": ["I'll do it", "let me", "my way"],
    "ripping_clothes": ["ripping clothes", "tearing", "destroyed"],
    "slowly_undress": ["slowly", "piece by piece", "draw it out"],

    # Clothing comments
    "dressed_like_slut": ["dressed like", "what you're wearing", "asking for it"],
    "knew_youd_wear": ["knew you'd wear", "wearing that", "for me"],
    "keep_something_on": ["keep this on", "don't take off", "want you in"],
    "looks_better_off": ["looks better off", "don't need clothes", "naked is better"],

    # After clothing
    "look_at_you_naked": ["look at you", "naked", "nothing to hide"],
    "exposed": ["exposed", "nowhere to hide", "see everything"],
    "wont_need_those": ["won't need those", "leave them", "clothes gone"],
}

# ============================================================================
# NC DEEP: SMELL DETAILS DURING
# ============================================================================

NC_DEEP_SMELL_DURING = {
    # Perpetrator smells
    "their_cologne": ["their cologne", "smell of them", "scent"],
    "their_sweat": ["their sweat", "body odor", "musk"],
    "their_breath": ["their breath", "alcohol breath", "cigarette breath"],
    "their_arousal": ["smell of arousal", "sex smell", "precum"],

    # Environment smells
    "location_smell": ["location smell", "room smell", "place"],
    "bed_smell": ["bed smell", "sheets", "fabric softener"],
    "outside_smell": ["outside smell", "grass", "car", "alley"],

    # Body smells
    "own_fear_sweat": ["own sweat", "fear sweat", "cold sweat smell"],
    "blood_smell": ["blood smell", "metallic", "iron"],
    "sex_smell": ["sex smell", "bodily fluids", "aftermath smell"],

    # Trauma smell
    "smell_burned_in": ["smell burned in", "never forget smell", "always remember"],
    "smell_triggers_now": ["smell triggers", "scent reminder", "transported back"],
}

# ============================================================================
# NC DEEP: SOUND ENVIRONMENT DURING
# ============================================================================

NC_DEEP_SOUND_ENVIRONMENT = {
    # Background sounds
    "tv_in_background": ["TV in background", "show playing", "noise cover"],
    "music_playing": ["music playing", "song", "radio"],
    "silence_oppressive": ["oppressive silence", "too quiet", "heard everything"],
    "traffic_outside": ["traffic outside", "cars passing", "normal world"],

    # Proximity sounds
    "people_nearby": ["people nearby", "could hear others", "not far"],
    "no_one_around": ["no one around", "isolated", "alone"],
    "party_continuing": ["party continuing", "people laughing", "no one noticed"],
    "normal_life_outside": ["normal life outside", "world continuing", "oblivious"],

    # Internal sounds
    "heartbeat_loud": ["heartbeat loud", "could hear heart", "pounding"],
    "own_breathing": ["own breathing", "ragged breath", "gasping"],
    "ringing_ears": ["ringing ears", "tinnitus", "blood rushing"],
}

# ============================================================================
# NC VILLAIN: POST-ACT CLEANING/COVERING
# ============================================================================

NC_VILLAIN_COVERING = {
    # Evidence disposal
    "clean_up": ["clean up", "get rid of evidence", "no trace"],
    "shower_now": ["shower now", "wash off", "clean yourself"],
    "burn_clothes": ["burn clothes", "get rid of", "destroy evidence"],
    "no_evidence": ["no evidence", "your word against", "prove nothing"],

    # Cover story
    "heres_what_happened": ["here's what happened", "this is what you'll say", "story"],
    "you_wanted_this": ["you wanted this", "asked for it", "tell them that"],
    "nothing_happened": ["nothing happened", "forget it", "didn't happen"],
    "no_one_will_believe": ["no one will believe", "who'd believe you", "your word"],

    # Returning to normal
    "act_normal_now": ["act normal", "pretend nothing", "go back out"],
    "smile": ["smile", "look happy", "no crying"],
    "say_goodbye_nicely": ["say goodbye", "thank them", "be polite"],
}

# ============================================================================
# NC VILLAIN: GROOMING DIALOGUE - PRE-EVENT
# ============================================================================

NC_VILLAIN_GROOMING_DIALOGUE = {
    # Building trust phase
    "youre_special": ["you're special", "different from others", "unique"],
    "understand_you": ["understand you", "get you", "only one who"],
    "can_trust_me": ["can trust me", "safe with me", "I'd never"],
    "no_one_cares_like_me": ["no one cares", "like I do", "only me"],
    "our_little_secret": ["our secret", "just between us", "don't tell"],

    # Isolation building
    "they_dont_understand": ["they don't understand", "wouldn't get it", "just us"],
    "theyd_be_jealous": ["they'd be jealous", "wouldn't approve", "don't tell"],
    "im_the_only_one": ["only one who", "here for you", "no one else"],
    "they_would_ruin_this": ["ruin this", "take you away", "keep you from me"],

    # Testing boundaries
    "its_just_a_hug": ["just a hug", "harmless", "friendly"],
    "dont_you_like_me": ["don't you like me", "thought we were friends", "I thought"],
    "this_is_normal": ["this is normal", "everyone does this", "nothing wrong"],
    "adults_do_this": ["adults do this", "grown ups", "mature"],

    # Gift/favor manipulation
    "after_all_i_gave": ["after all I gave", "everything I've done", "ungrateful"],
    "bought_you_things": ["bought you", "gave you", "paid for"],
    "helped_you": ["helped you", "was there for", "without me"],
    "you_owe_me": ["owe me", "repay", "least you can do"],
}

# ============================================================================
# NC VILLAIN: ONGOING/REPEATED ABUSE DIALOGUE
# ============================================================================

NC_VILLAIN_ONGOING_DIALOGUE = {
    # Establishing routine
    "same_time_usual": ["same time", "usual", "our regular"],
    "you_know_the_drill": ["know the drill", "routine", "how this goes"],
    "just_like_always": ["just like always", "as usual", "every time"],
    "were_doing_this_again": ["doing this again", "back for more", "time again"],

    # Reinforcing control
    "remember_last_time": ["remember last time", "what happened when", "don't make me"],
    "thought_you_learned": ["thought you learned", "by now", "still fighting"],
    "easier_if_you_just": ["easier if you just", "stop fighting", "accept"],
    "how_many_times": ["how many times", "told you", "explain again"],

    # Escalating threats
    "getting_bored": ["getting bored", "need something new", "change things up"],
    "been_too_nice": ["been too nice", "easy on you", "could be worse"],
    "know_what_I_could_do": ["know what I could do", "haven't even", "holding back"],
    "should_be_grateful": ["should be grateful", "gentle", "nice about it"],

    # Possession reinforcement
    "youre_mine_always": ["you're mine", "always mine", "never escape"],
    "belonged_to_me_since": ["belonged to me since", "from the start", "always"],
    "never_getting_away": ["never getting away", "can't escape", "forever"],
    "this_is_your_life": ["this is your life", "accept it", "reality"],
}

# ============================================================================
# NC VILLAIN: AUTHORITY SPECIFIC DIALOGUE
# ============================================================================

NC_VILLAIN_AUTHORITY_SPECIFIC = {
    # Professional authority
    "im_your_boss": ["I'm your boss", "I sign your paycheck", "your career"],
    "i_can_fire_you": ["can fire you", "end your career", "one word"],
    "who_would_hire_you": ["who would hire", "references", "blacklist"],
    "need_this_job_dont_you": ["need this job", "bills to pay", "can't afford"],

    # Academic authority
    "your_grades": ["your grades", "transcript", "academic record"],
    "recommendation_letter": ["recommendation", "letter", "future"],
    "scholarship_depends": ["scholarship", "funding", "depends on me"],
    "expulsion_is_easy": ["expulsion", "kicked out", "report you"],

    # Legal authority
    "i_am_the_law": ["I am the law", "badge", "authority"],
    "who_would_believe_you_cop": ["who'd believe you", "over a cop", "uniform"],
    "could_arrest_you": ["could arrest", "jail", "charges"],
    "know_where_you_live_cop": ["know where you live", "can find you", "always"],

    # Caretaker authority
    "take_care_of_you": ["take care of you", "responsible for", "your guardian"],
    "nowhere_else_to_go": ["nowhere else", "only home", "who would take you"],
    "no_one_wants_you": ["no one wants you", "lucky I keep you", "grateful"],
    "made_you": ["made you", "raised you", "created you"],
}

# ============================================================================
# NC VILLAIN: AGE-BASED DIALOGUE
# ============================================================================

NC_VILLAIN_AGE_DIALOGUE = {
    # Adult to younger
    "youll_understand_when_older": ["understand when older", "mature enough", "grown up"],
    "teaching_you": ["teaching you", "learning", "education"],
    "experienced_for_you": ["experienced", "know what's good", "for you"],
    "this_is_how_you_learn": ["how you learn", "education", "lessons"],
    "respect_your_elders": ["respect elders", "do as told", "older know better"],

    # Power through age
    "been_around_longer": ["been around longer", "know more", "wisdom"],
    "seen_enough_to_know": ["seen enough", "know what", "experience"],
    "at_my_age": ["at my age", "when you're older", "years of"],
    "young_and_naive": ["young and naive", "don't know", "innocent"],

    # Age-related coercion
    "only_get_one_chance": ["one chance", "before you're old", "while young"],
    "your_prime": ["your prime", "beautiful now", "won't last"],
    "appreciate_youth": ["appreciate youth", "enjoy while", "fleeting"],
}

# ============================================================================
# NC VILLAIN: COMPLIMENTING DURING
# ============================================================================

NC_VILLAIN_COMPLIMENTS_DURING = {
    # Physical "compliments"
    "so_beautiful_like_this": ["so beautiful", "like this", "look at you"],
    "perfect_body": ["perfect body", "made for this", "gorgeous"],
    "tighter_than_expected": ["tighter than", "better than thought", "so good"],
    "feels_amazing": ["feels amazing", "incredible", "perfect"],

    # Performance "compliments"
    "doing_so_well": ["doing so well", "good job", "perfect"],
    "taking_it_perfectly": ["taking it perfectly", "made for this", "natural"],
    "better_than_others": ["better than others", "best I've had", "special"],
    "born_for_this": ["born for this", "natural talent", "destiny"],

    # Twisted affection
    "love_you_like_this": ["love you like this", "beautiful like this", "when you"],
    "made_for_me": ["made for me", "perfect fit", "meant to be"],
    "only_one_who_appreciates": ["only one who appreciates", "see your value", "deserve you"],
}

# ============================================================================
# NC VILLAIN: COMPARING TO OTHERS
# ============================================================================

NC_VILLAIN_COMPARISON = {
    # Negative comparison
    "others_were_better": ["others were better", "not as good", "disappointing"],
    "expected_more": ["expected more", "heard you were", "let down"],
    "had_better": ["had better", "you're nothing special", "average"],
    "dont_compare": ["don't compare", "to the others", "better"],

    # Positive comparison to manipulate
    "better_than_them": ["better than them", "special", "unlike others"],
    "chose_you_specially": ["chose you", "specially", "out of everyone"],
    "wouldnt_do_this_with_anyone": ["wouldn't do this", "with anyone else", "just you"],

    # Competition/jealousy manipulation
    "others_would_kill_for_this": ["others would kill", "want this", "lucky"],
    "should_be_grateful": ["should be grateful", "chosen", "opportunity"],
    "plenty_would_take_your_place": ["plenty would", "take your place", "easily replaced"],
}

# ============================================================================
# NC VILLAIN: DURING VIOLENCE ESCALATION
# ============================================================================

NC_VILLAIN_VIOLENCE_ESCALATION = {
    # Warning escalation
    "making_me_do_this": ["making me do this", "your fault", "brought this on"],
    "could_stop_this": ["could stop this", "just cooperate", "your choice"],
    "dont_make_me_hurt": ["don't make me hurt", "want to be gentle", "you're making"],
    "this_can_be_nice": ["this can be nice", "or painful", "your choice"],

    # During violence
    "told_you_to_cooperate": ["told you", "warned you", "now see"],
    "should_have_listened": ["should have listened", "too late now", "your fault"],
    "youre_making_this_worse": ["making this worse", "stop fighting", "only hurts you"],
    "every_time_you_struggle": ["every time you", "more painful", "keep fighting"],

    # Post violence
    "see_what_happens": ["see what happens", "when you fight", "learn your lesson"],
    "next_time_remember": ["next time remember", "won't be gentle", "learned yet"],
    "could_have_been_nice": ["could have been nice", "you chose this", "your fault"],
}

# ============================================================================
# NC VILLAIN: DURING SPECIFIC POSITIONS
# ============================================================================

NC_VILLAIN_POSITION_DIALOGUE = {
    # Face down
    "face_down_talk": ["face down", "don't need to see", "just feel"],
    "stay_like_that": ["stay like that", "perfect view", "don't move"],
    "arch_your_back_command": ["arch your back", "present yourself", "that's it"],

    # Facing them
    "want_to_see_face": ["want to see your face", "watch your eyes", "look at me"],
    "watch_you_cry": ["watch you cry", "see those tears", "beautiful"],
    "see_your_expression": ["see your expression", "every moment", "don't look away"],

    # On knees
    "on_your_knees_where_belong": ["on your knees", "where you belong", "natural position"],
    "look_up_at_me": ["look up at me", "from down there", "beneath me"],
    "worship_position": ["worship position", "serve me", "proper place"],

    # Pinned down
    "pinned_dialogue": ["can't move", "trapped", "held down"],
    "helpless_like_this": ["helpless like this", "nowhere to go", "mine now"],
    "feel_my_weight": ["feel my weight", "can't escape", "under me"],
}

# ============================================================================
# NC VILLAIN: PHONE/TEXT COERCION
# ============================================================================

NC_VILLAIN_DIGITAL_COERCION = {
    # Demanding photos/videos
    "send_me_pictures": ["send me pictures", "want to see", "show me"],
    "video_call_now": ["video call now", "show me", "on camera"],
    "if_you_dont_send": ["if you don't send", "I'll", "consequences"],
    "keep_them_private": ["keep them private", "just for me", "no one sees"],

    # Using material
    "have_your_pictures": ["have your pictures", "saved", "evidence"],
    "could_share_these": ["could share these", "send to everyone", "post"],
    "imagine_if_people_saw": ["imagine if people saw", "your family", "everyone"],
    "insurance_photos": ["insurance", "guarantee", "make sure you"],

    # Remote control
    "answer_when_I_call": ["answer when I call", "always available", "immediately"],
    "tell_me_where_you_are": ["tell me where", "location", "always know"],
    "dont_ignore_me": ["don't ignore me", "I see you online", "answer"],
}

# ============================================================================
# NC VILLAIN: SUBSTANCE-INFLUENCED DIALOGUE
# ============================================================================

NC_VILLAIN_SUBSTANCE = {
    # Using intoxication
    "youre_drunk_so": ["you're drunk", "won't remember", "enjoy yourself"],
    "let_loose": ["let loose", "lowered inhibitions", "real you"],
    "blame_the_alcohol": ["blame the alcohol", "not responsible", "couldn't help"],
    "youll_forget": ["you'll forget", "won't remember", "black out"],

    # Drugging
    "just_a_drink": ["just a drink", "calm you down", "relax"],
    "feel_weird": ["feel weird", "its normal", "just relax"],
    "dont_fight_it": ["don't fight it", "let it happen", "give in"],
    "wont_remember_anyway": ["won't remember", "sleep it off", "tomorrow"],

    # Using aftermath
    "you_were_so_into_it": ["you were so into it", "couldn't stop", "begged for it"],
    "you_said_yes": ["you said yes", "asked for more", "consented"],
    "too_drunk_to_say_no": ["too drunk to say no", "didn't stop me", "let me"],
}

# ============================================================================
# NC VILLAIN: FINAL THREATS/WARNINGS
# ============================================================================

NC_VILLAIN_FINAL_WARNINGS = {
    # Remember threats
    "never_forget_this": ["never forget this", "remember forever", "burned in"],
    "ill_always_know": ["I'll always know", "can always find", "never escape"],
    "this_changes_nothing": ["changes nothing", "life goes on", "act normal"],
    "our_secret_forever": ["our secret", "forever", "never tell"],

    # Future threats
    "do_this_again_whenever": ["do this again", "whenever I want", "any time"],
    "always_available": ["always available", "when I call", "whenever"],
    "own_you_now": ["own you now", "forever mine", "never free"],
    "marked_you_permanently": ["marked you", "permanently", "always mine"],

    # Consequences threatened
    "tell_anyone_and": ["tell anyone and", "if you say anything", "I'll know"],
    "find_you_anywhere": ["find you anywhere", "can't hide", "I'll know"],
    "know_where_family_is": ["know where family", "your loved ones", "wouldn't want"],
    "watching_you_always": ["watching you", "always", "never alone"],
}

# ============================================================================
# NC VILLAIN: EMOTIONAL MANIPULATION DURING
# ============================================================================

NC_VILLAIN_EMOTIONAL_MANIPULATION = {
    # Fake concern
    "does_it_hurt": ["does it hurt", "are you okay", "too much"],
    "ill_be_gentle": ["I'll be gentle", "won't hurt", "easy"],
    "poor_thing": ["poor thing", "poor baby", "there there"],
    "its_okay_to_cry": ["okay to cry", "let it out", "I understand"],

    # Twisted comfort
    "its_almost_over": ["almost over", "almost done", "little more"],
    "youre_doing_great": ["doing great", "so well", "good job"],
    "shh_its_okay": ["shh", "it's okay", "calm down"],
    "just_breathe": ["just breathe", "relax", "don't tense"],

    # Emotional confusion
    "i_dont_want_to_hurt_you": ["don't want to hurt", "making me", "your fault"],
    "why_are_you_crying": ["why are you crying", "not that bad", "dramatic"],
    "thought_youd_like_this": ["thought you'd like", "wanted this", "didn't you"],
    "im_doing_this_because": ["doing this because", "care about you", "for you"],

    # Guilt inducing
    "look_what_you_made_me_do": ["look what you made me", "your fault", "caused this"],
    "if_you_had_just": ["if you had just", "cooperated", "this wouldn't"],
    "you_brought_this_on": ["brought this on", "yourself", "your fault"],
    "dont_blame_me": ["don't blame me", "you wanted", "asked for"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC BODY PART COMMENTARY EXTENDED
# ============================================================================

NC_VILLAIN_BODY_COMMENTARY_EXTENDED = {
    # Ass commentary
    "perfect_ass": ["perfect ass", "that ass", "made for this"],
    "spread_it": ["spread it", "open up", "show me"],
    "tight_ass_comment": ["so tight", "virgin ass", "unused"],
    "pounding_this_ass": ["pounding", "destroying", "owning"],

    # Cock commentary (on victim)
    "look_at_you_hard": ["look at you", "getting hard", "body knows"],
    "your_cock_says_yes": ["cock says yes", "body wants", "can't hide"],
    "pathetic_little_cock": ["pathetic", "little", "nothing"],
    "made_you_hard": ["made you hard", "did that", "turned you on"],

    # Mouth commentary
    "that_mouth": ["that mouth", "those lips", "perfect for"],
    "made_to_suck": ["made to suck", "natural", "talented"],
    "shut_that_mouth": ["shut that mouth", "close it", "silence"],
    "open_wider": ["open wider", "not enough", "all of it"],

    # Skin/body commentary
    "soft_skin": ["soft skin", "smooth", "perfect"],
    "marking_your_skin": ["marking your skin", "bruises", "evidence"],
    "all_over_your_body": ["all over", "everywhere", "whole body"],
    "every_inch": ["every inch", "nothing hidden", "all mine"],
}

# ============================================================================
# NC VILLAIN: DURING TEARS/CRYING
# ============================================================================

NC_VILLAIN_TEARS_DIALOGUE = {
    # Enjoying tears
    "love_those_tears": ["love those tears", "beautiful when you cry", "keep crying"],
    "cry_for_me": ["cry for me", "more tears", "let me see"],
    "tears_turn_me_on": ["tears turn me on", "hot when you cry", "love it"],
    "nothing_like_tears": ["nothing like tears", "real tears", "genuine"],

    # Mocking tears
    "crying_wont_help": ["crying won't help", "no one cares", "useless"],
    "baby_crying": ["baby", "little baby", "crybaby"],
    "thought_you_were_tough": ["thought you were tough", "not so tough now", "weak"],
    "pathetic_tears": ["pathetic", "disgusting", "weak"],

    # Using tears
    "see_youre_affected": ["see you're affected", "getting to you", "feeling it"],
    "means_its_working": ["means it's working", "real", "genuine"],
    "proof_you_feel": ["proof you feel", "not numb", "affected"],

    # Demanding no tears
    "stop_crying_command": ["stop crying", "no tears", "dry eyes"],
    "ill_give_you_something": ["give you something to cry about", "real reason", "more pain"],
    "annoying_tears": ["annoying", "stop it", "irritating"],
}

# ============================================================================
# NC VILLAIN: SOUNDS THEY MAKE/DEMAND
# ============================================================================

NC_VILLAIN_SOUNDS = {
    # Perpetrator sounds
    "grunting_groaning": ["grunting", "groaning", "animal sounds"],
    "heavy_breathing_perp": ["heavy breathing", "panting", "labored"],
    "moaning_pleasure": ["moaning", "pleasure sounds", "enjoying"],
    "laughing_during_act": ["laughing", "chuckling", "amused"],

    # Demanding sounds
    "moan_for_me": ["moan for me", "make sounds", "let me hear"],
    "scream_all_you_want": ["scream all you want", "no one hears", "go ahead"],
    "say_my_name_demand": ["say my name", "who am I", "call me"],
    "beg_me_demand": ["beg me", "say please", "ask nicely"],

    # Silencing sounds
    "shut_up_harsh": ["shut up", "silence", "quiet"],
    "one_sound_and": ["one sound and", "if you scream", "make noise"],
    "keep_quiet_or": ["keep quiet or", "silent", "not a sound"],
    "gag_you_threat": ["gag you", "shut you up", "silence you"],

    # Commentary on victim sounds
    "love_those_sounds": ["love those sounds", "music to me", "beautiful"],
    "hear_yourself": ["hear yourself", "listen to you", "sound like"],
    "whimpering_pathetic": ["whimpering", "pathetic sounds", "weak"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC SCENARIO DIALOGUE - VEHICLE
# ============================================================================

NC_VILLAIN_VEHICLE = {
    # Car specific
    "in_my_car": ["in my car", "my vehicle", "backseat"],
    "nowhere_to_run": ["nowhere to run", "can't escape", "moving"],
    "keep_driving": ["keep driving", "won't stop", "destination"],
    "no_one_can_see": ["no one can see", "tinted windows", "private"],

    # Control in vehicle
    "child_locks": ["child locks", "can't open", "trapped"],
    "dont_try_door": ["don't try the door", "won't open", "locked"],
    "just_drive_and": ["just drive and", "while driving", "road trip"],

    # Stopping threats
    "ill_pull_over": ["pull over", "stop somewhere", "finish this"],
    "middle_of_nowhere": ["middle of nowhere", "no one around", "isolated"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC SCENARIO DIALOGUE - WORKPLACE
# ============================================================================

NC_VILLAIN_WORKPLACE = {
    # Office specific
    "in_my_office": ["in my office", "close the door", "private meeting"],
    "after_hours": ["after hours", "everyone's gone", "just us"],
    "lock_the_door": ["lock the door", "no interruptions", "private"],
    "under_the_desk": ["under the desk", "on your knees", "no one sees"],

    # Professional leverage
    "performance_review": ["performance review", "your evaluation", "depends on"],
    "promotion_discussion": ["promotion", "discussing your future", "career"],
    "private_meeting": ["private meeting", "confidential", "between us"],
    "extra_work": ["extra work", "overtime", "staying late"],

    # Threats professional
    "tell_hr": ["tell HR", "report you", "your file"],
    "references": ["references", "future employers", "what I say"],
    "professional_reputation": ["professional reputation", "industry", "word gets around"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC SCENARIO DIALOGUE - HOME
# ============================================================================

NC_VILLAIN_HOME = {
    # Their home
    "my_house_my_rules": ["my house my rules", "in my home", "I decide"],
    "no_one_knows_youre_here": ["no one knows you're here", "didn't tell anyone", "alone"],
    "soundproof": ["soundproof", "no one hears", "scream all you want"],
    "basement_bedroom": ["basement", "bedroom", "special room"],

    # Victim's home
    "let_me_in": ["let me in", "open the door", "I know you're home"],
    "broke_in": ["broke in", "easy to get in", "not safe here"],
    "know_where_you_live": ["know where you live", "can come back", "anytime"],
    "your_bed": ["your bed", "where you sleep", "never safe here again"],

    # Living together
    "we_live_together": ["we live together", "can't escape", "every night"],
    "nowhere_to_go": ["nowhere to go", "this is home", "stuck here"],
    "family_home": ["family home", "everyone here", "quiet now"],
    "your_room": ["your room", "private space", "no lock helps"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC SCENARIO DIALOGUE - PARTY/SOCIAL
# ============================================================================

NC_VILLAIN_PARTY = {
    # Party setting
    "party_is_loud": ["party is loud", "no one hears", "music covers"],
    "everyone_is_drunk": ["everyone's drunk", "no one notices", "occupied"],
    "back_room": ["back room", "private room", "away from party"],
    "upstairs_bedroom": ["upstairs", "bedroom", "quiet up here"],

    # Social leverage
    "people_will_think": ["people will think", "reputation", "what they'd say"],
    "came_here_with_me": ["came here with me", "everyone saw", "willing"],
    "saw_you_drinking": ["saw you drinking", "drunk", "not reliable"],
    "who_would_believe": ["who would believe", "at a party", "drinking"],

    # Isolation at party
    "just_need_fresh_air": ["need fresh air", "come outside", "just a minute"],
    "want_to_show_you_something": ["show you something", "come see", "this way"],
    "private_conversation": ["private conversation", "just us", "away from noise"],
}

# ============================================================================
# NC VILLAIN: EXPRESSING AROUSAL/DESIRE
# ============================================================================

NC_VILLAIN_DESIRE_EXPRESSION = {
    # Stating desire
    "wanted_you_so_long": ["wanted you so long", "since I saw you", "been waiting"],
    "cant_resist_you": ["can't resist you", "have to have you", "need you"],
    "youre_so_hot": ["you're so hot", "beautiful", "irresistible"],
    "driving_me_crazy": ["driving me crazy", "making me", "can't help myself"],

    # During arousal
    "feel_how_hard": ["feel how hard", "that's for you", "you did this"],
    "so_turned_on": ["so turned on", "excited", "ready"],
    "need_you_now": ["need you now", "right now", "can't wait"],
    "gonna_cum": ["gonna cum", "almost there", "close"],

    # Objectifying desire
    "that_body": ["that body", "look at that", "perfect"],
    "been_watching_you": ["been watching you", "couldn't stop looking", "obsessed"],
    "have_to_have_you": ["have to have you", "must", "need"],
    "made_for_me": ["made for me", "perfect fit", "destiny"],
}

# ============================================================================
# NC VICTIM: INTERNAL BARGAINING
# ============================================================================

NC_VICTIM_INTERNAL_BARGAINING = {
    # With self
    "if_i_just_survive": ["if I just survive", "get through this", "be over"],
    "maybe_if_i_cooperate": ["maybe if I cooperate", "won't hurt as much", "faster"],
    "just_dont_kill_me": ["just don't kill me", "let me live", "anything else"],
    "ill_do_anything": ["I'll do anything", "just stop", "please"],

    # With higher power
    "please_god": ["please god", "if there's a god", "praying"],
    "if_this_ends": ["if this ends", "promise I'll", "never again"],
    "make_it_stop": ["make it stop", "please", "end this"],
    "why_me": ["why me", "what did I do", "deserve this"],

    # With perpetrator (internally)
    "maybe_theyll_stop": ["maybe they'll stop", "change their mind", "show mercy"],
    "if_i_dont_fight": ["if I don't fight", "maybe", "less violent"],
    "just_get_it_over": ["just get it over", "finish", "end this"],
    "please_be_quick": ["please be quick", "fast", "over soon"],
}

# ============================================================================
# NC VICTIM: BODILY AUTONOMY VIOLATION
# ============================================================================

NC_VICTIM_AUTONOMY = {
    # During violations
    "my_body_not_mine": ["my body", "not mine", "taken from me"],
    "dont_own_myself": ["don't own myself", "no control", "their property"],
    "body_doing_things": ["body doing things", "without me", "can't control"],
    "passenger_in_body": ["passenger", "watching happen", "not driving"],

    # Specific violations
    "inside_me_unwanted": ["inside me", "unwanted", "violation"],
    "touching_without_permission": ["touching without permission", "didn't ask", "took"],
    "using_my_body": ["using my body", "like object", "not person"],
    "entered_without_consent": ["entered without consent", "penetrated", "invaded"],

    # After realizations
    "body_will_never_be_same": ["never be same", "changed", "marked"],
    "violated_forever": ["violated forever", "can't undo", "permanent"],
    "took_something": ["took something", "stole", "can't get back"],
    "boundary_destroyed": ["boundary destroyed", "invaded", "violated"],
}

# ============================================================================
# NC VICTIM: SPECIFIC FEAR THOUGHTS
# ============================================================================

NC_VICTIM_FEAR_THOUGHTS = {
    # Death fears
    "am_i_going_to_die": ["am I going to die", "kill me", "this is it"],
    "this_could_be_end": ["could be the end", "might die", "last moments"],
    "want_to_live": ["want to live", "don't want to die", "survive"],
    "please_dont_kill_me": ["please don't kill me", "let me live", "spare me"],

    # Pain fears
    "how_much_will_hurt": ["how much will hurt", "pain coming", "brace"],
    "cant_take_more_pain": ["can't take more pain", "too much", "breaking"],
    "will_damage_me": ["will damage me", "permanent injury", "broken"],
    "please_no_more_pain": ["please no more pain", "stop hurting", "mercy"],

    # Future fears
    "what_happens_after": ["what happens after", "when done", "then what"],
    "will_they_let_me_go": ["will they let me go", "release me", "freedom"],
    "will_this_happen_again": ["happen again", "come back", "next time"],
    "can_never_be_normal": ["never be normal", "ruined", "changed forever"],
}

# ============================================================================
# NC VILLAIN: DURING RESTRAINT
# ============================================================================

NC_VILLAIN_RESTRAINT_DIALOGUE = {
    # Tying up
    "hold_still_while_i_tie": ["hold still", "while I tie", "don't struggle"],
    "not_going_anywhere": ["not going anywhere", "tied up", "secure"],
    "like_you_helpless": ["like you helpless", "love this", "at my mercy"],
    "cant_fight_now": ["can't fight now", "arms tied", "useless"],

    # During restraint
    "look_at_you_tied": ["look at you tied", "helpless", "beautiful"],
    "struggle_all_you_want": ["struggle all you want", "won't help", "tighter"],
    "completely_at_my_mercy": ["at my mercy", "whatever I want", "no escape"],
    "could_do_anything": ["could do anything", "you can't stop me", "helpless"],

    # Commentary on restraints
    "tight_enough": ["tight enough", "cutting in", "marks"],
    "leave_marks": ["leave marks", "evidence", "remember"],
    "hurting_yourself": ["hurting yourself", "stop struggling", "making worse"],
}

# ============================================================================
# NC VILLAIN: DEMANDING PARTICIPATION
# ============================================================================

NC_VILLAIN_DEMANDING_PARTICIPATION = {
    # Physical demands
    "move_your_hips": ["move your hips", "participate", "do something"],
    "kiss_me_back": ["kiss me back", "properly", "like you mean it"],
    "touch_me": ["touch me", "put your hands", "do it"],
    "ride_me": ["ride me", "move", "do the work"],

    # Verbal demands
    "say_you_want_it": ["say you want it", "tell me", "ask for it"],
    "beg_for_more": ["beg for more", "say please", "want more"],
    "tell_me_it_feels_good": ["tell me it feels good", "say it", "admit it"],
    "ask_nicely": ["ask nicely", "say please", "polite"],

    # Active participation demands
    "dont_just_lie_there": ["don't just lie there", "participate", "do something"],
    "act_like_you_want_it": ["act like you want it", "pretend", "perform"],
    "make_me_believe": ["make me believe", "convincing", "try harder"],
    "show_some_enthusiasm": ["show enthusiasm", "into it", "enjoy yourself"],
}

# ============================================================================
# NC VILLAIN: BREATHING/GRUNTING DURING ACT
# ============================================================================

NC_VILLAIN_BREATHING_SOUNDS = {
    # Breathing patterns
    "heavy_panting": ["heavy panting", "breathing hard", "out of breath"],
    "breath_in_ear": ["breath in ear", "hot against", "feel breath"],
    "holding_breath": ["holding breath", "then exhale", "sharp intake"],
    "ragged_breathing": ["ragged breathing", "uneven", "gasping"],

    # Vocal sounds
    "grunting_thrusting": ["grunting", "with each thrust", "animal sounds"],
    "groaning_pleasure": ["groaning", "pleasure sounds", "deep sounds"],
    "growling": ["growling", "low rumble", "threatening"],
    "sighing_satisfaction": ["sighing", "satisfaction", "content"],

    # Words between breaths
    "muttered_words": ["muttered", "under breath", "couldn't hear"],
    "gasped_words": ["gasped words", "between breaths", "panting out"],
    "moaned_words": ["moaned words", "pleasure-thick", "slurred"],
}

# ============================================================================
# NC VILLAIN: EYE CONTACT DEMANDS
# ============================================================================

NC_VILLAIN_EYE_CONTACT = {
    # Demanding eye contact
    "look_at_me_demand": ["look at me", "eyes on me", "don't look away"],
    "watch_what_im_doing": ["watch", "see what I'm doing", "look down"],
    "eyes_open_command": ["eyes open", "don't close them", "see this"],
    "face_me": ["face me", "turn around", "want to see"],

    # Using eye contact
    "staring_into_eyes": ["staring into eyes", "holding gaze", "locked eyes"],
    "watching_reactions": ["watching reactions", "see your face", "every expression"],
    "making_them_watch": ["making watch", "see yourself", "mirror"],

    # Denying eye contact
    "face_away": ["face away", "don't look at me", "turn around"],
    "close_your_eyes": ["close your eyes", "don't see", "blind"],
    "blindfold_threat": ["blindfold you", "won't see coming", "darkness"],
}

# ============================================================================
# NC VILLAIN: SKIN/TOUCH COMMENTARY
# ============================================================================

NC_VILLAIN_TOUCH_COMMENTARY = {
    # Skin observations
    "so_soft": ["so soft", "smooth skin", "perfect"],
    "goosebumps_noticed": ["goosebumps", "shivering", "body reacting"],
    "warm_skin": ["warm skin", "hot", "burning up"],
    "cold_skin": ["cold skin", "freezing", "clammy"],

    # Touch commentary
    "love_touching_you": ["love touching", "can't stop", "feel you"],
    "every_inch": ["every inch", "all of you", "whole body"],
    "memorizing_you": ["memorizing", "remember this", "know your body"],
    "tracing_skin": ["tracing", "following lines", "mapping"],

    # Reaction to touch
    "flinching_noticed": ["flinching", "pulling away", "scared of touch"],
    "body_responding": ["body responding", "can't hide", "reacting"],
    "trembling_noticed": ["trembling", "shaking", "can feel it"],
}

# ============================================================================
# NC VILLAIN: PACE/RHYTHM CONTROL
# ============================================================================

NC_VILLAIN_PACE_CONTROL = {
    # Speed control
    "going_slow_torture": ["going slow", "take my time", "no rush"],
    "going_fast_brutal": ["going fast", "hard", "pounding"],
    "changing_pace": ["changing pace", "keep you guessing", "unpredictable"],
    "stopping_starting": ["stop and start", "edge you", "control"],

    # Depth control
    "all_the_way": ["all the way", "deep", "every inch"],
    "shallow_teasing": ["shallow", "teasing", "just the tip"],
    "bottoming_out": ["bottoming out", "as deep as", "can't go further"],

    # Rhythm commentary
    "feel_that_rhythm": ["feel that rhythm", "in sync", "body knows"],
    "matching_pace": ["matching pace", "together", "moving with"],
    "setting_pace": ["setting pace", "I decide speed", "my rhythm"],
}

# ============================================================================
# NC VILLAIN: CLAIMING/MARKING DIALOGUE
# ============================================================================

NC_VILLAIN_CLAIMING = {
    # Verbal claiming
    "youre_mine": ["you're mine", "belong to me", "my property"],
    "no_one_elses": ["no one else's", "only mine", "claimed"],
    "marked_you": ["marked you", "everyone will know", "my mark"],
    "inside_you": ["inside you", "part of you now", "left something"],

    # Physical marking
    "leaving_bruises": ["leaving bruises", "marks", "evidence"],
    "biting_to_mark": ["biting", "teeth marks", "branded"],
    "scratching_marking": ["scratching", "nail marks", "lines"],
    "hickey_marking": ["hickey", "visible mark", "can't hide"],

    # Possession language
    "this_belongs_to_me": ["belongs to me", "my hole", "my body now"],
    "using_whats_mine": ["using what's mine", "my right", "own you"],
    "never_escape": ["never escape", "always mine", "forever"],
}

# ============================================================================
# NC VILLAIN: HUMILIATION SPECIFIC
# ============================================================================

NC_VILLAIN_HUMILIATION = {
    # Body humiliation
    "pathetic_body": ["pathetic body", "look at yourself", "disgusting"],
    "small_cock_mock": ["small", "pathetic", "call that a cock"],
    "loose_tight_mock": ["loose", "used", "been around"],
    "ugly_mock": ["ugly", "hideous", "no one wants"],

    # Performance humiliation
    "cant_even_perform": ["can't even", "pathetic performance", "useless"],
    "is_that_all": ["is that all", "disappointing", "expected more"],
    "trying_so_hard": ["trying so hard", "failing", "pathetic effort"],

    # Situation humiliation
    "look_at_you_now": ["look at you now", "how far fallen", "reduced to this"],
    "if_they_could_see": ["if they could see", "what would they think", "so proud"],
    "this_is_what_you_are": ["this is what you are", "true self", "always were"],
    "born_for_this": ["born for this", "made to be used", "purpose"],
}

# ============================================================================
# NC VILLAIN: FALSE REASSURANCE
# ============================================================================

NC_VILLAIN_FALSE_REASSURANCE = {
    # Fake comfort
    "its_okay_lie": ["it's okay", "don't worry", "nothing bad"],
    "almost_over_lie": ["almost over", "just a little more", "soon"],
    "wont_hurt_lie": ["won't hurt", "be gentle", "easy"],
    "trust_me_lie": ["trust me", "I know what I'm doing", "relax"],

    # Twisted care
    "doing_this_for_you": ["doing this for you", "your benefit", "teaching"],
    "youll_thank_me": ["thank me later", "appreciate this", "good for you"],
    "taking_care_of_you": ["taking care", "looking after", "caring for"],

    # Reality denial
    "not_so_bad": ["not so bad", "could be worse", "lucky"],
    "youre_fine": ["you're fine", "stop being dramatic", "overreacting"],
    "nothing_to_cry_about": ["nothing to cry about", "grow up", "be strong"],
}

# ============================================================================
# NC VICTIM: MUSCLE TENSION DURING
# ============================================================================

NC_VICTIM_MUSCLE_TENSION = {
    # Full body tension
    "every_muscle_rigid": ["every muscle rigid", "stiff", "locked"],
    "bracing_for_impact": ["bracing", "tensing up", "preparing"],
    "cant_relax": ["can't relax", "body won't", "too scared"],
    "coiled_tight": ["coiled tight", "spring", "about to snap"],

    # Specific areas
    "jaw_clenched": ["jaw clenched", "teeth grinding", "tight"],
    "fists_clenched": ["fists clenched", "nails in palms", "white knuckles"],
    "shoulders_up": ["shoulders up", "hunched", "protective"],
    "stomach_tight": ["stomach tight", "clenched", "nauseous"],
    "thighs_clamped": ["thighs clamped", "trying to close", "resistance"],

    # Release
    "finally_unclenched": ["finally unclenched", "released", "let go"],
    "exhaustion_from_tension": ["exhausted from tension", "muscles aching", "held too long"],
    "trembling_from_effort": ["trembling from effort", "shaking", "can't stop"],
}

# ============================================================================
# NC VICTIM: BREATHING PATTERNS
# ============================================================================

NC_VICTIM_BREATHING = {
    # Fear breathing
    "breath_caught": ["breath caught", "couldn't breathe", "stopped"],
    "hyperventilating": ["hyperventilating", "too fast", "can't slow"],
    "shallow_quick": ["shallow quick breaths", "panting fear", "rapid"],
    "holding_breath_fear": ["holding breath", "afraid to breathe", "silent"],

    # Controlled attempts
    "trying_to_breathe": ["trying to breathe", "focus on breath", "in out"],
    "counting_breaths": ["counting breaths", "one two", "steady"],
    "breathing_through": ["breathing through", "survive this", "just breathe"],

    # Sound of breathing
    "ragged_gasps": ["ragged gasps", "choking", "struggling"],
    "whimpering_breath": ["whimpering", "small sounds", "each exhale"],
    "sobbing_breath": ["sobbing breath", "hitching", "crying breathing"],

    # After
    "first_real_breath": ["first real breath", "finally", "could breathe"],
    "shaky_breath_after": ["shaky breath", "unstable", "trembling exhale"],
}

# ============================================================================
# NC VICTIM: PAIN EXPERIENCE DETAILED
# ============================================================================

NC_VICTIM_PAIN_DETAILED = {
    # Pain types
    "sharp_stabbing": ["sharp", "stabbing", "sudden"],
    "burning_tearing": ["burning", "tearing", "ripping"],
    "dull_ache": ["dull ache", "deep", "throbbing"],
    "pressure_pain": ["pressure", "too much", "stretching"],
    "raw_pain": ["raw", "abraded", "friction"],

    # Pain location
    "pain_inside": ["pain inside", "internal", "deep within"],
    "surface_pain": ["surface pain", "skin", "external"],
    "radiating_pain": ["radiating", "spreading", "everywhere"],

    # Pain response
    "crying_from_pain": ["crying from pain", "tears", "couldn't stop"],
    "screaming_pain": ["screaming", "couldn't help", "pain sound"],
    "silent_pain": ["silent", "couldn't make sound", "too much"],
    "begging_stop_pain": ["begging stop", "please stop", "hurts"],

    # Pain aftermath
    "pain_lasted": ["pain lasted", "still hurting", "didn't stop"],
    "numb_from_pain": ["numb from pain", "couldn't feel", "too much"],
}

# ============================================================================
# NC VICTIM: SPECIFIC BODY PART EXPERIENCE
# ============================================================================

NC_VICTIM_BODY_PARTS = {
    # Hands
    "hands_pinned": ["hands pinned", "couldn't move arms", "held down"],
    "hands_tied": ["hands tied", "bound", "restrained"],
    "hands_useless": ["hands useless", "couldn't push", "no strength"],
    "hands_grasping": ["hands grasping", "for anything", "something to hold"],

    # Legs
    "legs_forced_open": ["legs forced open", "spread", "couldn't close"],
    "legs_pinned": ["legs pinned", "held apart", "immobilized"],
    "legs_shaking": ["legs shaking", "trembling", "couldn't stop"],
    "kicking_stopped": ["stopped kicking", "gave up", "too tired"],

    # Mouth
    "mouth_covered": ["mouth covered", "couldn't scream", "muffled"],
    "mouth_forced_open": ["mouth forced open", "jaw", "couldn't close"],
    "biting_down": ["biting down", "on something", "to not scream"],
    "tasting_tears": ["tasting tears", "salt", "own tears"],

    # Core
    "stomach_churning": ["stomach churning", "nauseous", "sick"],
    "chest_tight": ["chest tight", "couldn't breathe", "compressed"],
    "heart_pounding": ["heart pounding", "could hear it", "racing"],
}

# ============================================================================
# NC VICTIM: DISSOCIATION SPECIFIC
# ============================================================================

NC_VICTIM_DISSOCIATION_SPECIFIC = {
    # Leaving body
    "floating_above": ["floating above", "watching from ceiling", "outside body"],
    "not_in_body": ["not in body", "somewhere else", "left"],
    "watching_happen": ["watching happen", "to someone else", "not me"],
    "disconnected_completely": ["disconnected", "not there", "gone"],

    # Numbness
    "feeling_nothing": ["feeling nothing", "numb", "empty"],
    "cant_feel_body": ["can't feel body", "detached", "not mine"],
    "emotions_gone": ["emotions gone", "hollow", "blank"],
    "pain_distant": ["pain distant", "far away", "muted"],

    # Time distortion
    "time_stopped": ["time stopped", "frozen moment", "eternal"],
    "time_fast": ["time fast", "blur", "over suddenly"],
    "no_sense_time": ["no sense of time", "could be forever", "lost"],

    # Coming back
    "snapping_back": ["snapping back", "suddenly there", "returned"],
    "slowly_returning": ["slowly returning", "coming back", "pieces"],
    "not_wanting_back": ["not wanting to come back", "safer away", "stay gone"],
}

# ============================================================================
# NC VILLAIN: ENTITLEMENT STATEMENTS
# ============================================================================

NC_VILLAIN_ENTITLEMENT = {
    # Deserving
    "i_deserve_this": ["I deserve this", "earned it", "owed to me"],
    "you_owe_me": ["you owe me", "my right", "payment"],
    "after_everything": ["after everything I've done", "gave you", "sacrificed"],
    "least_you_can_do": ["least you can do", "small price", "fair"],

    # Rights
    "my_right": ["my right", "entitled to", "belongs to me"],
    "taking_whats_mine": ["taking what's mine", "claiming", "due"],
    "no_one_denies_me": ["no one denies me", "always get", "never refused"],

    # Justification
    "you_made_me_want": ["you made me want", "your fault", "tempted me"],
    "cant_help_myself": ["can't help myself", "you're too", "irresistible"],
    "anyone_would": ["anyone would", "who wouldn't", "natural"],
    "men_have_needs": ["men have needs", "natural", "can't control"],
}

# ============================================================================
# NC VILLAIN: DURING SPECIFIC ACTS - FINGERING
# ============================================================================

NC_VILLAIN_FINGERING = {
    # Starting
    "feeling_you_first": ["feeling you first", "see what we have", "exploring"],
    "getting_you_ready": ["getting you ready", "open you up", "prepare"],
    "one_finger_first": ["one finger first", "then more", "stretching"],

    # During
    "so_tight_fingers": ["so tight", "barely fits", "virgin"],
    "loosening_up": ["loosening up", "opening", "making room"],
    "feel_that_inside": ["feel that inside", "deep", "finding spots"],
    "more_fingers": ["more fingers", "adding", "stretching more"],

    # Finding prostate
    "found_it": ["found it", "there it is", "sweet spot"],
    "right_there": ["right there", "that spot", "feel that"],
    "making_you_react": ["making you react", "body responding", "can't help it"],
}

# ============================================================================
# NC VILLAIN: DURING SPECIFIC ACTS - ORAL FORCED
# ============================================================================

NC_VILLAIN_FORCED_ORAL = {
    # Commands
    "open_your_mouth": ["open your mouth", "open wide", "wider"],
    "suck_it_properly": ["suck it", "properly", "like you mean it"],
    "use_your_tongue": ["use your tongue", "lick", "work it"],
    "no_teeth_warning": ["no teeth", "careful", "bite and I'll"],

    # During
    "thats_it": ["that's it", "good", "keep going"],
    "deeper_now": ["deeper", "more", "all of it"],
    "look_up_while": ["look up at me", "eyes on me", "watch"],
    "swallow_it": ["swallow it", "don't spit", "every drop"],

    # Control
    "holding_head_down": ["holding head", "can't pull away", "stay"],
    "fucking_mouth": ["fucking your mouth", "throat", "using"],
    "gagging_good": ["gagging", "that's it", "take it"],
    "breathe_through_nose": ["breathe through nose", "figure it out", "adapt"],
}

# ============================================================================
# NC VILLAIN: AFTERMATH - SAME NIGHT
# ============================================================================

NC_VILLAIN_SAME_NIGHT = {
    # Immediate after
    "that_was_good": ["that was good", "needed that", "satisfied"],
    "you_did_well": ["you did well", "good job", "pleased"],
    "maybe_again_later": ["maybe again later", "rest up", "round two"],
    "getting_dressed": ["getting dressed", "cleaning up", "done now"],

    # Dismissal
    "you_can_go": ["you can go", "leave now", "done with you"],
    "get_out": ["get out", "leave", "go"],
    "stay_tonight": ["stay tonight", "not done", "sleep here"],
    "act_normal": ["act normal", "go back", "nothing happened"],

    # Continued control
    "remember_what_i_said": ["remember what I said", "don't forget", "our secret"],
    "see_you_soon": ["see you soon", "next time", "again"],
    "youre_mine_now": ["you're mine now", "from now on", "forever"],
}

# ============================================================================
# NC VICTIM: IMMEDIATELY AFTER - PHYSICAL
# ============================================================================

NC_VICTIM_AFTER_PHYSICAL = {
    # Body state
    "cant_move": ["can't move", "frozen", "paralyzed"],
    "shaking_uncontrollably": ["shaking uncontrollably", "trembling", "can't stop"],
    "curling_up": ["curling up", "fetal position", "small"],
    "legs_wont_work": ["legs won't work", "can't stand", "collapse"],

    # Pain
    "everything_hurts": ["everything hurts", "whole body", "pain everywhere"],
    "specific_pain": ["pain there", "where they", "burning"],
    "numb_pain": ["numb", "too much pain", "can't feel"],
    "throbbing": ["throbbing", "pulsing pain", "won't stop"],

    # Physical evidence
    "bleeding": ["bleeding", "blood", "injured"],
    "bruising_forming": ["bruising forming", "marks appearing", "evidence"],
    "torn_clothes": ["torn clothes", "ripped", "destroyed"],
    "bodily_fluids": ["their fluids", "evidence on", "sticky wet"],
}

# ============================================================================
# NC VICTIM: IMMEDIATELY AFTER - MENTAL
# ============================================================================

NC_VICTIM_AFTER_MENTAL = {
    # Shock state
    "in_shock": ["in shock", "can't process", "unreal"],
    "this_didnt_happen": ["this didn't happen", "not real", "dream"],
    "blank_mind": ["blank mind", "nothing", "empty"],
    "cant_think": ["can't think", "brain stopped", "frozen"],

    # Emotional flood
    "everything_at_once": ["everything at once", "flood", "overwhelming"],
    "crying_finally": ["crying finally", "tears came", "couldn't stop"],
    "screaming_inside": ["screaming inside", "silent scream", "no sound"],
    "complete_numbness": ["complete numbness", "nothing", "void"],

    # First thoughts
    "what_just_happened": ["what just happened", "did that", "real"],
    "my_fault_thought": ["my fault", "I caused", "should have"],
    "not_my_fault_thought": ["not my fault", "they did this", "didn't deserve"],
    "what_do_i_do": ["what do I do", "now what", "help"],
}

# ============================================================================
# NC VILLAIN: LOCATION-BASED THREATS
# ============================================================================

NC_VILLAIN_LOCATION_THREATS = {
    # Isolation
    "no_one_around": ["no one around", "alone here", "isolated"],
    "miles_from_anywhere": ["miles from anywhere", "middle of nowhere", "no help"],
    "soundproof": ["soundproof", "no one hears", "scream all you want"],
    "locked_in": ["locked in", "no escape", "trapped"],

    # Knowledge threats
    "know_where_you_live": ["know where you live", "your address", "can find you"],
    "know_your_routine": ["know your routine", "when you leave", "watching"],
    "follow_you_anywhere": ["follow you", "anywhere you go", "can't hide"],
    "know_your_family": ["know your family", "where they live", "could visit them"],

    # Return threats
    "ill_be_back": ["I'll be back", "see you again", "next time"],
    "this_isnt_over": ["this isn't over", "just beginning", "more to come"],
    "know_how_to_find_you": ["know how to find you", "always", "can't escape"],
}

# ============================================================================
# NC VILLAIN: WEAPON/OBJECT THREATS
# ============================================================================

NC_VILLAIN_WEAPON_THREATS = {
    # Weapon presence
    "have_a_knife": ["have a knife", "see this", "blade"],
    "have_a_gun": ["have a gun", "pointing at", "don't test me"],
    "could_hurt_you_worse": ["could hurt you worse", "tools", "ways to hurt"],
    "dont_make_me_use": ["don't make me use", "rather not", "your choice"],

    # Object use
    "using_objects": ["using objects", "this will", "insert"],
    "improvised_restraints": ["tie you up", "belt", "anything as rope"],
    "household_items": ["household items", "creative", "hurt with anything"],

    # Threat level
    "escalation_threat": ["could get worse", "being nice now", "you don't want"],
    "capability_demonstration": ["see what I can do", "taste of", "just beginning"],
}

# ============================================================================
# NC VILLAIN: MOCKING RESISTANCE
# ============================================================================

NC_VILLAIN_MOCK_RESISTANCE = {
    # Physical resistance mocked
    "that_all_youve_got": ["that all you've got", "weak", "pathetic fight"],
    "keep_trying": ["keep trying", "entertaining", "won't help"],
    "tired_yet": ["tired yet", "gave up fighting", "exhausted"],
    "love_when_you_struggle": ["love when you struggle", "fight more", "exciting"],

    # Verbal resistance mocked
    "say_no_all_you_want": ["say no all you want", "won't help", "meaningless"],
    "scream_louder": ["scream louder", "no one hears", "try harder"],
    "begging_wont_help": ["begging won't help", "keep begging", "love it"],
    "cry_more": ["cry more", "beautiful tears", "keep crying"],

    # Mental resistance mocked
    "think_you_can_ignore": ["think you can ignore", "present with me", "here now"],
    "going_somewhere": ["going somewhere", "in your head", "come back"],
    "trying_to_leave": ["trying to leave", "stay with me", "feel this"],
}

# ============================================================================
# NC VILLAIN: COMMENTARY ON VICTIM REACTIONS
# ============================================================================

NC_VILLAIN_REACTION_COMMENTARY = {
    # Physical reactions
    "look_at_you_trembling": ["look at you trembling", "shaking", "scared"],
    "goosebumps_noticed": ["goosebumps", "body reacting", "responding"],
    "sweating_noticed": ["sweating", "nervous", "afraid"],
    "blushing_noticed": ["blushing", "embarrassed", "body betraying"],

    # Emotional reactions
    "tears_beautiful": ["tears so beautiful", "crying for me", "perfect"],
    "fear_in_eyes": ["fear in your eyes", "love that look", "terrified"],
    "panic_delicious": ["panic", "delicious", "perfect fear"],
    "desperation_showing": ["desperation showing", "hopeless", "given up"],

    # Body reactions
    "getting_hard": ["getting hard", "body wants", "can't hide"],
    "getting_wet": ["getting wet", "body responding", "liking this"],
    "nipples_hard": ["nipples hard", "aroused", "body knows"],
    "cant_control_body": ["can't control body", "reacting", "honest body"],
}

# ============================================================================
# NC VICTIM: SPECIFIC FEAR TYPES
# ============================================================================

NC_VICTIM_FEAR_TYPES = {
    # Immediate fears
    "fear_of_death": ["fear of death", "going to die", "end"],
    "fear_of_pain": ["fear of pain", "how much", "hurt more"],
    "fear_of_unknown": ["fear of unknown", "what will happen", "what next"],
    "fear_of_exposure": ["fear of exposure", "people knowing", "found out"],

    # Social fears
    "fear_no_one_believes": ["no one believes", "who would believe", "word against"],
    "fear_of_judgment": ["fear of judgment", "what they'll think", "blame"],
    "fear_of_shame": ["fear of shame", "everyone knowing", "can't face"],
    "fear_of_pity": ["fear of pity", "poor thing", "victim forever"],

    # Future fears
    "fear_this_again": ["fear this again", "happen again", "when not if"],
    "fear_cant_escape": ["can't escape", "never free", "always looking"],
    "fear_of_intimacy_after": ["fear of intimacy", "never again", "ruined"],
    "fear_of_trust": ["fear of trust", "can't trust anyone", "fooled again"],
}

# ============================================================================
# NC VICTIM: INTERNAL QUESTIONS
# ============================================================================

NC_VICTIM_INTERNAL_QUESTIONS = {
    # During
    "why_me": ["why me", "why is this happening", "what did I do"],
    "when_will_it_end": ["when will it end", "how long", "ever stop"],
    "will_i_survive": ["will I survive", "get through this", "live"],
    "what_do_they_want": ["what do they want", "what satisfies", "when done"],

    # About self
    "could_i_have_stopped": ["could I have stopped", "done differently", "prevented"],
    "why_didnt_i_fight": ["why didn't I fight", "more", "harder"],
    "why_did_i_freeze": ["why did I freeze", "couldn't move", "paralyzed"],
    "is_something_wrong_with_me": ["something wrong with me", "my fault", "deserve this"],

    # About future
    "will_i_be_okay": ["will I be okay", "get through", "survive this"],
    "can_i_tell_anyone": ["can I tell anyone", "who would believe", "safe to tell"],
    "what_happens_now": ["what happens now", "life after", "go on"],
    "will_it_always_hurt": ["will it always hurt", "pain forever", "go away"],
}

# ============================================================================
# NC VILLAIN: TIME-BASED DIALOGUE
# ============================================================================

NC_VILLAIN_TIME_DIALOGUE = {
    # Starting
    "been_waiting": ["been waiting for this", "finally", "dreamed of"],
    "take_my_time": ["take my time", "no rush", "all night"],
    "just_getting_started": ["just getting started", "beginning", "so much more"],

    # During
    "little_longer": ["little longer", "almost", "not quite"],
    "dont_rush_me": ["don't rush me", "my pace", "I decide when"],
    "savoring_this": ["savoring this", "enjoying", "every moment"],
    "making_it_last": ["making it last", "draw out", "not over yet"],

    # Ending
    "almost_done": ["almost done", "close now", "finishing"],
    "one_more_time": ["one more time", "again", "not satisfied"],
    "until_i_decide": ["until I decide", "when I'm done", "I say when"],
    "could_go_all_night": ["could go all night", "stamina", "not tired"],
}

# ============================================================================
# NC VILLAIN: OWNERSHIP LANGUAGE EXTENDED
# ============================================================================

NC_VILLAIN_OWNERSHIP_EXTENDED = {
    # Body ownership
    "this_is_mine_now": ["this is mine now", "your body", "belongs to me"],
    "every_part": ["every part of you", "all of it", "nothing hidden"],
    "inside_and_out": ["inside and out", "completely", "totally mine"],
    "using_whats_mine": ["using what's mine", "my property", "my right"],

    # Person ownership
    "you_are_mine": ["you are mine", "belong to me", "my possession"],
    "bought_and_paid": ["bought and paid", "own you", "mine"],
    "signed_over": ["signed over", "gave yourself", "contract"],
    "no_one_elses_ever": ["no one else's", "ever", "ruined for others"],

    # Time ownership
    "your_time_is_mine": ["your time is mine", "when I want", "available always"],
    "whenever_i_want": ["whenever I want", "on demand", "my schedule"],
    "for_as_long_as": ["for as long as I want", "until done", "indefinitely"],
}

# ============================================================================
# NC VICTIM: SHAME SPIRAL
# ============================================================================

NC_VICTIM_SHAME_SPIRAL = {
    # Core shame
    "deeply_ashamed": ["deeply ashamed", "core shame", "fundamentally wrong"],
    "dirty_forever": ["dirty forever", "can't wash off", "stained"],
    "ruined_person": ["ruined person", "damaged goods", "broken"],
    "unworthy_now": ["unworthy now", "don't deserve", "less than"],

    # Shame thoughts
    "should_have_known": ["should have known", "saw signs", "stupid"],
    "should_have_fought": ["should have fought", "harder", "more"],
    "let_it_happen": ["let it happen", "didn't stop", "fault"],
    "body_betrayed": ["body betrayed", "responded", "disgusting"],

    # Shame behaviors
    "cant_look_in_mirror": ["can't look in mirror", "avoid reflection", "hate seeing"],
    "hiding_from_everyone": ["hiding from everyone", "don't want seen", "isolation"],
    "covering_body": ["covering body", "layers", "hide skin"],
    "cant_accept_kindness": ["can't accept kindness", "don't deserve", "unworthy"],
}

# ============================================================================
# NC VICTIM: ANGER EMERGENCE
# ============================================================================

NC_VICTIM_ANGER = {
    # At perpetrator
    "rage_at_them": ["rage at them", "hatred", "want to hurt"],
    "fantasies_of_revenge": ["fantasies of revenge", "make them pay", "hurt them back"],
    "want_them_dead": ["want them dead", "wish they'd die", "kill them"],
    "fury_at_injustice": ["fury at injustice", "got away with it", "no consequences"],

    # At self
    "angry_at_self": ["angry at self", "should have", "why didn't I"],
    "self_hatred": ["self hatred", "hate myself", "disgusting"],
    "punishing_self": ["punishing self", "deserve pain", "self harm"],

    # At others
    "angry_at_world": ["angry at world", "everyone", "unfair"],
    "angry_no_one_helped": ["angry no one helped", "where were they", "abandoned"],
    "angry_at_disbelievers": ["angry at disbelievers", "didn't believe", "called liar"],
    "angry_at_system": ["angry at system", "no justice", "failed me"],

    # Anger expression
    "explosive_anger": ["explosive anger", "outbursts", "can't control"],
    "suppressed_rage": ["suppressed rage", "holding in", "building"],
    "misdirected_anger": ["misdirected", "wrong targets", "safe people"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC SCENARIO - DATE RAPE
# ============================================================================

NC_VILLAIN_DATE_SCENARIO = {
    # Lead up
    "thought_this_was_date": ["thought this was a date", "nice evening", "then"],
    "having_a_good_time": ["having a good time", "trusted you", "relaxed"],
    "drink_something": ["drink something", "another drink", "relax"],
    "come_back_to_mine": ["come back to mine", "nightcap", "continue talking"],

    # Transition
    "just_a_kiss": ["just a kiss", "thought", "then hands"],
    "things_moved_fast": ["things moved fast", "suddenly", "wait"],
    "said_slow_down": ["said slow down", "not ready", "ignored"],
    "didnt_mean_this": ["didn't mean this", "just kissing", "too far"],

    # During
    "we_both_want_this": ["we both want this", "on a date", "led me on"],
    "already_started": ["already started", "too late", "might as well"],
    "came_home_with_me": ["came home with me", "knew what that meant", "invitation"],
    "been_flirting_all_night": ["flirting all night", "signals", "wanted this"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC SCENARIO - AUTHORITY ABUSE
# ============================================================================

NC_VILLAIN_AUTHORITY_SCENARIO = {
    # Using position
    "im_in_charge_here": ["I'm in charge here", "authority", "power over you"],
    "i_decide_your_future": ["I decide your future", "career", "grade", "freedom"],
    "one_word_from_me": ["one word from me", "destroyed", "ruined"],
    "no_one_questions_me": ["no one questions me", "my word", "respected"],

    # Expectations
    "this_is_how_it_works": ["this is how it works", "pay to play", "real world"],
    "everyone_does_this": ["everyone does this", "normal", "how things are"],
    "small_price": ["small price", "for what you get", "worth it"],
    "professional_relationship": ["professional relationship", "between us", "arrangement"],

    # Threats
    "could_end_you": ["could end you", "one report", "recommendation"],
    "no_one_believes_student": ["no one believes student", "employee", "subordinate"],
    "my_reputation": ["my reputation", "vs yours", "who wins"],
}

# ============================================================================
# NC VICTIM: BETRAYAL SPECIFIC
# ============================================================================

NC_VICTIM_BETRAYAL = {
    # Trust betrayal
    "trusted_them": ["trusted them", "believed them", "thought safe"],
    "let_guard_down": ["let guard down", "relaxed around", "comfortable"],
    "thought_they_cared": ["thought they cared", "loved me", "friend"],
    "knew_them_so_well": ["knew them so well", "thought I did", "wrong"],

    # Relationship betrayal
    "by_partner": ["by partner", "lover", "boyfriend", "husband"],
    "by_family": ["by family", "blood", "should protect"],
    "by_friend": ["by friend", "trusted", "years of friendship"],
    "by_mentor": ["by mentor", "looked up to", "respected"],

    # Betrayal feelings
    "everything_was_lie": ["everything was a lie", "all of it", "nothing real"],
    "never_trust_again": ["never trust again", "can't", "won't let"],
    "questioning_everyone": ["questioning everyone", "who else", "all suspicious"],
    "world_not_safe": ["world not safe", "nowhere safe", "no one safe"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC PHRASES - STARTING
# ============================================================================

NC_VILLAIN_STARTING_PHRASES = {
    # Opening lines
    "ive_been_waiting": ["I've been waiting", "finally", "thought this day"],
    "knew_this_would_happen": ["knew this would happen", "inevitable", "matter of time"],
    "youve_been_asking": ["you've been asking for this", "teasing", "wanting"],
    "time_to_pay_up": ["time to pay up", "owe me", "collection time"],

    # Initial moves
    "dont_fight_it": ["don't fight it", "easier this way", "just let it happen"],
    "relax_itll_be_fine": ["relax", "it'll be fine", "enjoy it"],
    "this_is_happening": ["this is happening", "accept it", "no stopping"],
    "been_thinking_about_this": ["been thinking about this", "planned", "imagined"],

    # Cornering
    "nowhere_to_go": ["nowhere to go", "trapped", "mine now"],
    "no_one_coming": ["no one's coming", "just us", "alone"],
    "locked_door": ["door's locked", "can't escape", "soundproof"],
    "end_of_the_road": ["end of the road", "this is it", "finally"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC PHRASES - DURING
# ============================================================================

NC_VILLAIN_DURING_PHRASES = {
    # Commanding
    "stay_still": ["stay still", "don't move", "hold position"],
    "spread_them": ["spread them", "open up", "wider"],
    "turn_over": ["turn over", "on your stomach", "face down"],
    "get_on_your_knees": ["get on your knees", "kneel", "down"],

    # Commentary
    "perfect": ["perfect", "just like that", "exactly"],
    "so_good": ["so good", "feels amazing", "incredible"],
    "tighter": ["tighter", "squeeze", "grip"],
    "taking_it_well": ["taking it well", "handling it", "good boy"],

    # Taunting
    "see_you_can_take_it": ["see you can take it", "not so bad", "doing fine"],
    "body_knows": ["body knows", "responds", "wants this"],
    "stop_pretending": ["stop pretending", "we both know", "admit it"],
    "almost_there": ["almost there", "close", "gonna cum"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC PHRASES - ENDING
# ============================================================================

NC_VILLAIN_ENDING_PHRASES = {
    # Finishing
    "here_it_comes": ["here it comes", "cumming", "take it"],
    "all_of_it": ["all of it", "every drop", "inside you"],
    "filled_you_up": ["filled you up", "marked you", "inside now"],
    "that_was_good": ["that was good", "needed that", "satisfied"],

    # Post-act
    "clean_yourself": ["clean yourself up", "mess", "presentable"],
    "dont_tell_anyone": ["don't tell anyone", "our secret", "between us"],
    "see_you_next_time": ["see you next time", "do this again", "soon"],
    "you_know_the_deal": ["you know the deal", "keep quiet", "consequences"],

    # Dismissal
    "get_out": ["get out", "leave", "done with you"],
    "back_to_normal": ["back to normal", "act like nothing", "forget it"],
    "was_that_so_bad": ["was that so bad", "survived", "not terrible"],
}

# ============================================================================
# NC VICTIM: PHYSICAL SENSATIONS DURING
# ============================================================================

NC_VICTIM_SENSATIONS_DURING = {
    # Invasion feeling
    "something_inside": ["something inside", "foreign", "invasion"],
    "stretching_painfully": ["stretching painfully", "too much", "tearing"],
    "pressure_overwhelming": ["pressure overwhelming", "filled", "too full"],
    "cant_accommodate": ["can't accommodate", "too big", "won't fit"],

    # Body reactions
    "muscles_clenching": ["muscles clenching", "tight", "resistance"],
    "body_rejecting": ["body rejecting", "pushing out", "resistance"],
    "involuntary_reactions": ["involuntary reactions", "can't control", "body doing"],
    "physical_response_unwanted": ["physical response", "unwanted", "body betraying"],

    # Pain sensations
    "burning_stretching": ["burning", "stretching", "on fire"],
    "sharp_each_thrust": ["sharp pain each", "thrust", "jab"],
    "dull_constant_ache": ["dull constant ache", "persistent", "won't stop"],
    "raw_abraded": ["raw", "abraded", "friction burn"],
}

# ============================================================================
# NC VICTIM: MENTAL STATE DURING
# ============================================================================

NC_VICTIM_MENTAL_DURING = {
    # Disbelief
    "this_isnt_real": ["this isn't real", "can't be happening", "nightmare"],
    "wake_up_please": ["wake up", "please", "just a dream"],
    "not_happening_to_me": ["not happening to me", "someone else", "not real"],

    # Survival mode
    "just_survive": ["just survive", "get through", "stay alive"],
    "dont_die": ["don't die", "stay alive", "survive this"],
    "itll_be_over": ["it'll be over", "end eventually", "almost done"],
    "endure_this": ["endure this", "bear it", "withstand"],

    # Escape attempts
    "go_somewhere_else": ["go somewhere else", "mentally", "not here"],
    "think_of_anything_else": ["think of anything else", "distract", "elsewhere"],
    "leave_body": ["leave body", "float away", "not present"],
    "pretend_elsewhere": ["pretend elsewhere", "imagination", "escape"],
}

# ============================================================================
# NC VILLAIN: MANIPULATION THROUGH PLEASURE
# ============================================================================

NC_VILLAIN_PLEASURE_MANIPULATION = {
    # Forcing pleasure response
    "make_you_enjoy": ["make you enjoy this", "feel good", "pleasure"],
    "body_will_respond": ["body will respond", "can't help it", "physical"],
    "gonna_make_you_cum": ["gonna make you cum", "whether you want", "force pleasure"],
    "see_you_like_it": ["see you like it", "body shows", "can't hide"],

    # Using pleasure against
    "came_so_you_wanted": ["you came", "so you wanted it", "proof"],
    "body_betrayed_you": ["body betrayed you", "responded", "liked it"],
    "hard_wet_so": ["hard", "wet", "proof you wanted"],
    "enjoyed_it_admit": ["enjoyed it", "admit it", "felt good"],

    # Twisted logic
    "if_it_felt_good": ["if it felt good", "was it really", "not so bad"],
    "you_responded": ["you responded", "physically", "wanted"],
    "natural_reaction": ["natural reaction", "bodies do", "meant to"],
}

# ============================================================================
# NC VILLAIN: DURING RESISTANCE
# ============================================================================

NC_VILLAIN_DURING_RESISTANCE = {
    # Response to fighting
    "fight_all_you_want": ["fight all you want", "won't help", "stronger"],
    "like_when_you_fight": ["like when you fight", "exciting", "makes it better"],
    "getting_tired": ["getting tired", "give up", "can't win"],
    "more_you_fight": ["more you fight", "more I enjoy", "keep going"],

    # Response to crying
    "crying_turns_me_on": ["crying turns me on", "love tears", "beautiful"],
    "cry_all_you_want": ["cry all you want", "no one cares", "won't stop"],
    "tears_wont_save_you": ["tears won't save you", "no mercy", "continue"],

    # Response to begging
    "love_when_you_beg": ["love when you beg", "beg more", "music"],
    "begging_makes_harder": ["begging makes me harder", "excited", "more"],
    "keep_begging": ["keep begging", "won't help", "but love it"],
    "please_what": ["please what", "be specific", "ask properly"],
}

# ============================================================================
# NC VICTIM: COPING MECHANISMS DURING
# ============================================================================

NC_VICTIM_COPING_DURING = {
    # Mental escape
    "counting_in_head": ["counting in head", "numbers", "distraction"],
    "reciting_something": ["reciting something", "song", "poem", "prayer"],
    "thinking_of_safe_place": ["thinking of safe place", "elsewhere", "escape"],
    "imagining_rescue": ["imagining rescue", "someone coming", "saved"],

    # Physical coping
    "biting_lip": ["biting lip", "focus pain", "control something"],
    "clenching_fists": ["clenching fists", "nails in palms", "distraction"],
    "closing_eyes_tight": ["closing eyes tight", "don't see", "darkness"],
    "going_limp": ["going limp", "not fighting", "less pain"],

    # Emotional coping
    "detaching_emotionally": ["detaching emotionally", "numb", "don't feel"],
    "rage_as_fuel": ["rage as fuel", "anger keeping alive", "survive to revenge"],
    "focusing_on_after": ["focusing on after", "when it's over", "then"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC INSULTS
# ============================================================================

NC_VILLAIN_INSULTS = {
    # Sexual insults
    "slut_whore": ["slut", "whore", "easy"],
    "cock_hungry": ["cock hungry", "desperate", "gagging for it"],
    "used_up": ["used up", "loose", "been around"],
    "dirty_filthy": ["dirty", "filthy", "disgusting"],

    # Character insults
    "worthless_nothing": ["worthless", "nothing", "waste"],
    "pathetic_weak": ["pathetic", "weak", "useless"],
    "stupid_dumb": ["stupid", "dumb", "idiot"],
    "ugly_hideous": ["ugly", "hideous", "repulsive"],

    # Dehumanizing
    "just_a_hole": ["just a hole", "meat", "object"],
    "thing_not_person": ["thing", "not a person", "it"],
    "property_object": ["property", "object", "possession"],
    "toy_plaything": ["toy", "plaything", "entertainment"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC COMMANDS
# ============================================================================

NC_VILLAIN_COMMANDS_EXTENDED = {
    # Position commands
    "on_back": ["on your back", "lie down", "face up"],
    "on_stomach": ["on your stomach", "face down", "ass up"],
    "on_knees_ext": ["on your knees", "kneel", "down"],
    "bend_over_ext": ["bend over", "lean forward", "present"],

    # Action commands
    "open_mouth_ext": ["open your mouth", "open wide", "wider"],
    "spread_legs_ext": ["spread your legs", "open up", "apart"],
    "hold_still_ext": ["hold still", "don't move", "stay"],
    "look_at_me_ext": ["look at me", "eyes on me", "watch"],

    # Compliance commands
    "stop_fighting_ext": ["stop fighting", "give up", "accept"],
    "stop_crying_ext": ["stop crying", "no tears", "quiet"],
    "shut_up_ext": ["shut up", "be quiet", "silence"],
    "do_what_i_say_ext": ["do what I say", "obey", "follow orders"],
}

# ============================================================================
# NC VILLAIN: GROOMING PROGRESSION DIALOGUE
# ============================================================================

NC_VILLAIN_GROOMING_PROGRESSION = {
    # Building trust phase
    "youre_special_to_me": ["you're special to me", "unique", "different"],
    "no_one_understands_like_i_do": ["no one understands", "like I do", "only one"],
    "can_tell_me_anything": ["can tell me anything", "safe with me", "trust me"],
    "always_here_for_you": ["always here for you", "never leave", "rely on me"],

    # Testing phase
    "its_just_between_us": ["just between us", "secret", "don't tell"],
    "this_is_normal": ["this is normal", "everyone does", "natural"],
    "dont_you_trust_me": ["don't you trust me", "thought we were close", "disappointed"],
    "just_showing_affection": ["just showing affection", "how I care", "love you"],

    # Escalation phase
    "youre_ready_now": ["you're ready now", "mature enough", "time"],
    "been_waiting_for_this": ["been waiting", "patient", "finally"],
    "next_step": ["next step", "relationship", "closer"],
    "prove_you_love_me": ["prove you love me", "show me", "if you care"],
}

# ============================================================================
# NC VILLAIN: RELATIONSHIP MANIPULATION
# ============================================================================

NC_VILLAIN_RELATIONSHIP_MANIPULATION = {
    # Using relationship
    "thought_you_loved_me": ["thought you loved me", "don't you", "prove it"],
    "couples_do_this": ["couples do this", "normal", "what partners do"],
    "marital_duty": ["duty", "obligation", "owe me"],
    "after_everything_weve_been_through": ["after everything", "years together", "owe me this"],

    # Weaponizing history
    "remember_when_i": ["remember when I", "did for you", "sacrificed"],
    "all_ive_given_you": ["all I've given you", "provided", "ungrateful"],
    "would_be_nothing_without_me": ["nothing without me", "made you", "everything you have"],

    # Threatening relationship
    "ill_leave_you": ["I'll leave you", "find someone else", "alone"],
    "no_one_else_wants_you": ["no one else wants you", "lucky to have me", "only option"],
    "take_the_kids": ["take the kids", "custody", "never see them"],
    "tell_everyone_youre": ["tell everyone", "you're", "reputation"],
}

# ============================================================================
# NC VICTIM: LONG-TERM EFFECTS
# ============================================================================

NC_VICTIM_LONG_TERM = {
    # Relationship effects
    "cant_trust_partners": ["can't trust partners", "all suspicious", "waiting for"],
    "afraid_of_intimacy": ["afraid of intimacy", "can't be close", "push away"],
    "sabotaging_relationships": ["sabotaging relationships", "before hurt", "leave first"],
    "choosing_wrong_partners": ["choosing wrong partners", "pattern", "repeat"],

    # Self effects
    "chronic_shame": ["chronic shame", "constant", "underlying"],
    "worthlessness_persistent": ["persistent worthlessness", "never enough", "broken"],
    "hypervigilance_constant": ["constant hypervigilance", "always alert", "never safe"],
    "depression_ongoing": ["ongoing depression", "can't shake", "years"],

    # Body effects
    "disconnected_from_body": ["disconnected from body", "not mine", "foreign"],
    "chronic_pain_psychosomatic": ["chronic pain", "no medical cause", "body memory"],
    "startle_response_exaggerated": ["exaggerated startle", "jump at everything", "on edge"],
    "sleep_never_normal": ["sleep never normal", "insomnia", "nightmares persisting"],

    # Social effects
    "isolation_chosen": ["chosen isolation", "safer alone", "no one"],
    "cant_work_normally": ["can't work normally", "triggered", "functioning impaired"],
    "avoid_places_people": ["avoid places", "people", "triggers everywhere"],
}

# ============================================================================
# NC VICTIM: RECOVERY STAGES
# ============================================================================

NC_VICTIM_RECOVERY_STAGES = {
    # Early stage
    "survival_mode": ["survival mode", "day by day", "just existing"],
    "denial_stage": ["denial", "didn't happen", "not that bad"],
    "crisis_period": ["crisis period", "can't function", "falling apart"],
    "seeking_help_first": ["seeking help", "first time", "admitting need"],

    # Middle stage
    "processing_beginning": ["processing beginning", "starting to feel", "emerging"],
    "anger_emerging": ["anger emerging", "finally feeling", "rage"],
    "grief_stage": ["grief stage", "mourning", "lost self"],
    "therapy_working": ["therapy working", "progress", "small steps"],

    # Integration stage
    "acceptance_beginning": ["acceptance beginning", "happened", "real"],
    "narrative_forming": ["narrative forming", "understanding", "story"],
    "identity_rebuilding": ["identity rebuilding", "who I am now", "new self"],
    "meaning_making": ["meaning making", "purpose", "why"],

    # Growth stage
    "post_traumatic_growth": ["post traumatic growth", "stronger", "wisdom"],
    "helping_others": ["helping others", "advocacy", "purpose from pain"],
    "thriving_not_just_surviving": ["thriving", "not just surviving", "living"],
}

# ============================================================================
# NC VILLAIN: DURING EJACULATION
# ============================================================================

NC_VILLAIN_EJACULATION = {
    # Announcing
    "gonna_cum": ["gonna cum", "cumming", "here it comes"],
    "take_it_all": ["take it all", "every drop", "inside you"],
    "filling_you_up": ["filling you up", "deep inside", "breeding you"],
    "marked_you": ["marked you", "mine now", "inside forever"],

    # During
    "feel_that": ["feel that", "feel me cum", "inside you now"],
    "so_good": ["so good", "perfect", "needed this"],
    "cum_dump": ["cum dump", "use for this", "made for my cum"],

    # After ejaculation
    "dont_let_it_out": ["don't let it out", "keep it in", "hold it"],
    "stay_there": ["stay there", "not done", "moment"],
    "leaking_out": ["leaking out", "dripping", "full"],
    "round_two": ["round two", "again", "not satisfied"],
}

# ============================================================================
# NC VICTIM: SPECIFIC TRAUMA RESPONSES
# ============================================================================

NC_VICTIM_TRAUMA_RESPONSES = {
    # Freeze response detailed
    "couldnt_move_literally": ["couldn't move literally", "paralyzed", "frozen solid"],
    "brain_disconnected_body": ["brain disconnected", "from body", "no control"],
    "time_suspended": ["time suspended", "eternal moment", "frozen in time"],
    "watching_from_outside": ["watching from outside", "not in body", "observer"],

    # Fight response suppressed
    "wanted_to_fight": ["wanted to fight", "couldn't", "body wouldn't"],
    "rage_trapped_inside": ["rage trapped inside", "couldn't express", "impotent fury"],
    "strength_gone": ["strength gone", "no power", "weak"],

    # Flight response blocked
    "wanted_to_run": ["wanted to run", "legs wouldn't", "trapped"],
    "door_right_there": ["door right there", "couldn't reach", "so close"],
    "escape_impossible": ["escape impossible", "no way out", "gave up"],

    # Fawn response
    "tried_to_please": ["tried to please", "maybe stop", "compliance"],
    "became_agreeable": ["became agreeable", "whatever you want", "appease"],
    "cooperating_to_survive": ["cooperating to survive", "strategy", "less pain"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC BODY PART FOCUS DIALOGUE
# ============================================================================

NC_VILLAIN_BODY_FOCUS = {
    # Chest/nipples
    "perfect_chest": ["perfect chest", "nipples", "sensitive aren't they"],
    "like_when_i_touch_these": ["like when I touch these", "responding", "hard"],

    # Genitals
    "this_is_mine_now": ["this is mine now", "cock/pussy", "belongs to me"],
    "look_how_it_responds": ["look how it responds", "body knows", "wants this"],
    "getting_hard_wet_for_me": ["getting hard", "wet", "for me"],

    # Ass
    "perfect_ass_focus": ["perfect ass", "made for this", "gonna wreck"],
    "tight_hole": ["tight hole", "virgin", "unused"],
    "spreading_you": ["spreading you", "open", "see inside"],

    # Mouth
    "perfect_mouth_focus": ["perfect mouth", "made to suck", "lips"],
    "throat_focus": ["throat", "deep", "gag reflex"],
}

# ============================================================================
# NC VILLAIN: USING VICTIM'S NAME
# ============================================================================

NC_VILLAIN_NAME_USE = {
    # Possessive use
    "name_as_claim": ["my [name]", "mine", "belongs to me"],
    "pet_names_twisted": ["baby", "sweetheart", "darling", "twisted"],
    "degrading_names": ["slut", "whore", "used as name"],

    # Power use
    "say_my_name": ["say my name", "who am I", "remember who"],
    "scream_my_name": ["scream my name", "let them hear", "everyone knows"],
    "beg_using_name": ["beg using my name", "properly", "respectfully"],

    # Dehumanizing
    "calling_it": ["calling you it", "thing", "object not person"],
    "number_not_name": ["number", "not name", "dehumanized"],
    "no_name_anymore": ["no name anymore", "whatever I call", "renamed"],
}

# ============================================================================
# NC VILLAIN: DURATION COMMENTARY
# ============================================================================

NC_VILLAIN_DURATION = {
    # Short
    "quick_one": ["quick one", "won't take long", "fast"],
    "just_need_a_minute": ["just need a minute", "quick release", "brief"],

    # Long
    "all_night": ["all night", "hours", "just getting started"],
    "take_my_time": ["take my time", "no rush", "savor"],
    "making_it_last": ["making it last", "draw out", "enjoy every second"],
    "until_i_decide": ["until I decide", "when I'm done", "my timeline"],

    # Repeated
    "do_this_again": ["do this again", "next time", "regular"],
    "whenever_i_want": ["whenever I want", "on demand", "any time"],
    "this_is_routine_now": ["routine now", "regular schedule", "expect this"],
}

# ============================================================================
# NC VICTIM: SPECIFIC MOMENT - REALIZATION
# ============================================================================

NC_VICTIM_REALIZATION_MOMENT = {
    # First awareness
    "something_wrong": ["something's wrong", "not right", "danger"],
    "this_isnt_normal": ["this isn't normal", "shouldn't be", "alarm"],
    "trap_realized": ["trap realized", "no escape", "planned"],
    "moment_everything_changed": ["moment everything changed", "before and after", "world shifted"],

    # Denial breaking
    "this_is_really_happening": ["this is really happening", "not a dream", "real"],
    "cant_pretend_anymore": ["can't pretend anymore", "obvious now", "undeniable"],
    "fight_or_survive": ["fight or survive", "choice made", "moment"],

    # Horror realization
    "knew_what_was_coming": ["knew what was coming", "inevitable", "couldn't stop"],
    "no_way_out": ["no way out", "trapped", "finished"],
    "this_is_it": ["this is it", "happening", "can't escape"],
}

# ============================================================================
# NC VICTIM: BODY DURING - MICRO DETAILS
# ============================================================================

NC_VICTIM_BODY_MICRO = {
    # Skin
    "skin_crawling": ["skin crawling", "want to claw off", "contaminated"],
    "everywhere_touched_burns": ["everywhere touched burns", "fire", "marked"],
    "cold_then_hot": ["cold then hot", "temperature shifts", "shock"],

    # Internal
    "stomach_heaving": ["stomach heaving", "nausea", "going to vomit"],
    "throat_closing": ["throat closing", "can't swallow", "choking"],
    "lungs_won't_work": ["lungs won't work", "can't breathe deep", "shallow"],

    # Extremities
    "hands_tingling": ["hands tingling", "numb", "circulation"],
    "feet_cold": ["feet cold", "freezing", "blood gone"],
    "fingers_useless": ["fingers useless", "can't grip", "no strength"],

    # Core
    "heart_too_fast": ["heart too fast", "will explode", "pounding"],
    "chest_crushing": ["chest crushing", "weight", "can't expand"],
    "everything_tight": ["everything tight", "clenched", "won't release"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC KINK-ADJACENT DIALOGUE
# ============================================================================

NC_VILLAIN_KINK_ADJACENT = {
    # Pain play
    "gonna_hurt_you": ["gonna hurt you", "pain", "suffer"],
    "scream_for_me": ["scream for me", "music", "love it"],
    "more_pain": ["more pain", "not enough", "really feel it"],

    # Degradation
    "on_the_floor": ["on the floor", "where you belong", "beneath me"],
    "like_an_animal": ["like an animal", "beast", "not human"],
    "worship_me": ["worship me", "grateful", "honor"],

    # Control
    "completely_helpless": ["completely helpless", "at my mercy", "powerless"],
    "I_own_you": ["I own you", "property", "possession"],
    "do_anything_to_you": ["do anything to you", "whatever I want", "no limits"],

    # Objectification
    "just_a_body": ["just a body", "holes", "use"],
    "made_for_this": ["made for this", "purpose", "function"],
    "toy_to_play_with": ["toy to play with", "entertainment", "discard when done"],
}

# ============================================================================
# NC VICTIM: SENSORY OVERLOAD
# ============================================================================

NC_VICTIM_SENSORY_OVERLOAD = {
    # Too much input
    "everything_too_loud": ["everything too loud", "sounds overwhelming", "can't filter"],
    "touch_too_intense": ["touch too intense", "every nerve", "screaming"],
    "light_too_bright": ["light too bright", "hurts eyes", "overwhelming"],
    "cant_process": ["can't process", "too much", "overloaded"],

    # Shutdown
    "senses_shutting_down": ["senses shutting down", "going offline", "protection"],
    "going_numb": ["going numb", "feeling less", "detaching"],
    "world_getting_distant": ["world getting distant", "far away", "muffled"],

    # Hyperawareness
    "aware_of_everything": ["aware of everything", "heightened", "too sharp"],
    "every_sound_magnified": ["every sound magnified", "footsteps loud", "breathing"],
    "smell_overwhelming": ["smell overwhelming", "can't escape", "everywhere"],
}

# ============================================================================
# NC VILLAIN: AFTERMATH THREATS
# ============================================================================

NC_VILLAIN_AFTERMATH_THREATS = {
    # Secrecy threats
    "no_one_finds_out": ["no one finds out", "between us", "secret dies here"],
    "tell_anyone_and": ["tell anyone and", "consequences", "I'll know"],
    "who_would_believe": ["who would believe you", "your word", "against mine"],

    # Return threats
    "see_you_again": ["see you again", "this isn't over", "next time"],
    "know_where_you_are": ["know where you are", "always", "can find you"],
    "whenever_I_want": ["whenever I want", "on my schedule", "expect me"],

    # Harm threats
    "worse_next_time": ["worse next time", "if you tell", "really hurt you"],
    "hurt_your_family": ["hurt your family", "loved ones", "them too"],
    "destroy_your_life": ["destroy your life", "ruin everything", "take everything"],
}

# ============================================================================
# NC VICTIM: FIRST WORDS AFTER
# ============================================================================

NC_VICTIM_FIRST_WORDS = {
    # To self
    "oh_god": ["oh god", "no", "what"],
    "this_didnt_happen": ["this didn't happen", "not real", "dream"],
    "im_okay_lie": ["I'm okay", "lying to self", "denial"],

    # To perpetrator
    "please_let_me_go": ["please let me go", "can I leave", "done now"],
    "dont_tell_anyone": ["don't tell anyone", "please", "begging for secrecy too"],
    "silence": ["silence", "couldn't speak", "no words"],

    # To others
    "help_me": ["help me", "first words to safe person", "finally"],
    "something_happened": ["something happened", "can't say what", "vague"],
    "i_was": ["I was...", "can't finish", "words stuck"],
}

# ============================================================================
# NC VILLAIN: DENIAL/MINIMIZING DIALOGUE
# ============================================================================

NC_VILLAIN_DENIAL_DIALOGUE = {
    # Denying it happened
    "nothing_happened": ["nothing happened", "what are you talking about", "imagining"],
    "you_wanted_this": ["you wanted this", "asked for it", "consented"],
    "you_came_to_me": ["you came to me", "your choice", "willingly"],

    # Minimizing
    "not_a_big_deal": ["not a big deal", "overreacting", "drama"],
    "everyone_does_this": ["everyone does this", "normal", "making too much"],
    "wasnt_that_bad": ["wasn't that bad", "could've been worse", "lucky"],

    # Gaslighting
    "didnt_say_no": ["didn't say no", "didn't hear no", "no resistance"],
    "your_body_said_yes": ["your body said yes", "responded", "proof"],
    "youre_remembering_wrong": ["remembering wrong", "not how it happened", "confused"],
}

# ============================================================================
# NC VILLAIN: PRAISE DURING (TWISTED)
# ============================================================================

NC_VILLAIN_TWISTED_PRAISE = {
    # Performance praise
    "good_boy_twisted": ["good boy", "that's it", "perfect"],
    "doing_so_well_twist": ["doing so well", "natural at this", "talented"],
    "best_ive_had_twist": ["best I've had", "perfect", "made for this"],
    "learning_quickly_twist": ["learning quickly", "fast learner", "smart"],

    # Body praise
    "beautiful_like_this_twist": ["beautiful like this", "gorgeous", "perfect body"],
    "perfect_fit_twist": ["perfect fit", "made for me", "like glove"],
    "so_responsive_twist": ["so responsive", "body knows", "sensitive"],

    # Compliance praise
    "finally_cooperating_twist": ["finally cooperating", "see", "better this way"],
    "good_stopped_fighting": ["good you stopped fighting", "smart", "easier"],
    "thats_more_like_it_twist": ["that's more like it", "behaving now", "obedient"],
}

# ============================================================================
# NC VILLAIN: CONTEMPT EXPRESSIONS
# ============================================================================

NC_VILLAIN_CONTEMPT = {
    # Disgust
    "disgusting_contempt": ["disgusting", "pathetic", "revolting"],
    "look_at_yourself_contempt": ["look at yourself", "state of you", "pitiful"],
    "make_me_sick_contempt": ["make me sick", "repulsive", "gross"],

    # Superiority
    "beneath_me_contempt": ["beneath me", "so far below", "nothing"],
    "lucky_i_bother_contempt": ["lucky I bother", "with you", "should be grateful"],
    "could_have_anyone_contempt": ["could have anyone", "chose you", "honor"],

    # Dismissal
    "meaningless_contempt": ["meaningless", "don't matter", "insignificant"],
    "forgettable_contempt": ["forgettable", "won't remember you", "nothing special"],
    "waste_of_time_contempt": ["waste of time", "not worth it", "disappointing"],
}

# ============================================================================
# NC VICTIM: PHYSICAL EVIDENCE AWARENESS
# ============================================================================

NC_VICTIM_EVIDENCE = {
    # On body
    "bruises_forming_evidence": ["bruises forming", "marks appearing", "visible evidence"],
    "teeth_marks_evidence": ["teeth marks", "bite marks", "wounds"],
    "finger_marks_evidence": ["finger marks", "grip bruises", "handprint"],
    "tearing_evidence": ["tearing evidence", "bleeding", "damage"],

    # On clothes
    "torn_clothing_evidence": ["torn clothing", "ripped", "destroyed"],
    "stains_on_clothes_evidence": ["stains on clothes", "evidence", "bodily fluids"],
    "missing_items_evidence": ["missing items", "taken", "kept as trophy"],

    # Internal
    "evidence_inside": ["evidence inside", "their fluids", "DNA"],
    "physical_damage_internal_evidence": ["internal damage", "tearing", "injury"],
}

# ============================================================================
# NC VICTIM: TIME EXPERIENCE
# ============================================================================

NC_VICTIM_TIME_EXPERIENCE = {
    # During
    "time_stretched_exp": ["time stretched", "eternal", "forever"],
    "time_compressed_exp": ["time compressed", "blur", "instant"],
    "no_sense_of_time_exp": ["no sense of time", "lost track", "unknown duration"],
    "counting_seconds_exp": ["counting seconds", "each moment", "waiting for end"],

    # After
    "hours_felt_minutes": ["hours felt like minutes", "compressed", "shock"],
    "minutes_felt_hours": ["minutes felt like hours", "stretched", "eternal"],
    "time_gaps": ["time gaps", "missing time", "can't account"],
    "lost_time_exp": ["lost time", "blacked out", "memory gaps"],
}

# ============================================================================
# NC VILLAIN: CREATING COMPLICITY
# ============================================================================

NC_VILLAIN_COMPLICITY = {
    # Shared blame
    "you_wanted_this_too": ["you wanted this too", "both of us", "mutual"],
    "you_didnt_stop_me": ["you didn't stop me", "could have", "let me"],
    "youre_part_of_this": ["you're part of this", "in this together", "equally"],

    # Creating guilt
    "you_made_me_do_this": ["you made me do this", "your fault", "caused"],
    "look_what_you_did": ["look what you did", "made me", "responsible"],
    "if_you_hadnt_comp": ["if you hadn't", "none of this", "blame yourself"],

    # Forcing participation
    "now_youre_involved": ["now you're involved", "can't tell", "implicated"],
    "we_both_have_secrets": ["we both have secrets", "mutually assured", "keep quiet"],
}

# ============================================================================
# NC VICTIM: HELP-SEEKING BARRIERS
# ============================================================================

NC_VICTIM_HELP_BARRIERS = {
    # Internal barriers
    "too_ashamed_barrier": ["too ashamed", "can't tell", "shameful"],
    "wont_be_believed_barrier": ["won't be believed", "who would believe", "word against"],
    "dont_want_to_remember_barrier": ["don't want to remember", "talking makes real", "denial"],
    "protecting_perpetrator_barrier": ["protecting perpetrator", "complicated feelings", "don't want harm"],

    # External barriers
    "no_one_to_tell_barrier": ["no one to tell", "alone", "isolated"],
    "fear_of_consequences_barrier": ["fear of consequences", "what will happen", "retaliation"],
    "too_complicated_barrier": ["too complicated", "relationship", "can't explain"],
    "system_wont_help_barrier": ["system won't help", "police useless", "no point"],

    # Self-blame barriers
    "my_fault_anyway_barrier": ["my fault anyway", "deserved it", "asked for it"],
    "should_have_known_barrier": ["should have known", "could have prevented", "stupid"],
}

# ============================================================================
# NC VILLAIN: SPECIFIC SCENARIO - INTOXICATION
# ============================================================================

NC_VILLAIN_INTOXICATION_SCENARIO = {
    # Using intoxication
    "youre_drunk_relax": ["you're drunk", "relax", "enjoy"],
    "wont_remember_anyway_intox": ["won't remember anyway", "tomorrow", "blackout"],
    "lowered_inhibitions_intox": ["lowered inhibitions", "real you", "honest"],
    "cant_consent_but_intox": ["can't consent but", "would've said yes", "know you want"],

    # Creating intoxication
    "have_another_drink_intox": ["have another drink", "loosen up", "more"],
    "something_in_drink_intox": ["something in drink", "drugged", "slipped"],
    "too_out_of_it_intox": ["too out of it", "can't fight", "easy"],

    # Exploiting aftermath
    "you_were_into_it_intox": ["you were so into it", "couldn't stop", "wild"],
    "you_said_yes_intox": ["said yes last night", "don't remember", "definitely"],
}

# ============================================================================
# NC VILLAIN: POWER DYNAMIC SPECIFIC
# ============================================================================

NC_VILLAIN_POWER_DYNAMIC_SPECIFIC = {
    # Superior position
    "im_your_boss_power": ["I'm your boss", "superior", "above you"],
    "control_your_future_power": ["control your future", "career", "life"],
    "one_word_power": ["one word from me", "destroyed", "ruined"],

    # Age/experience
    "im_older_wiser_power": ["I'm older", "know better", "experience"],
    "teaching_you_power": ["teaching you", "lessons", "learning"],
    "be_grateful_power": ["should be grateful", "attention", "chosen"],

    # Social position
    "im_respected_power": ["I'm respected", "who would believe", "reputation"],
    "youre_nothing_power": ["you're nothing", "no one", "beneath notice"],
    "my_word_vs_yours_power": ["my word vs yours", "who wins", "obvious"],
}

# ============================================================================
# NC VICTIM: SPECIFIC MEMORIES THAT HAUNT
# ============================================================================

NC_VICTIM_HAUNTING_MEMORIES = {
    # Sensory memories
    "their_smell_memory": ["their smell", "can't forget", "triggers"],
    "their_voice_memory": ["their voice", "echoes", "hear it still"],
    "their_hands_memory": ["their hands", "feeling of", "phantom touch"],
    "their_weight_memory": ["their weight", "pressure", "crushing"],

    # Visual memories
    "their_face_memory": ["their face", "expression", "see it still"],
    "their_eyes_memory": ["their eyes", "looking at me", "haunting"],
    "the_room_memory": ["the room", "where it happened", "can't forget"],
    "my_own_body_memory": ["my own body", "during", "image burned in"],

    # Sound memories
    "sounds_they_made_memory": ["sounds they made", "grunting", "breathing"],
    "my_own_sounds_memory": ["my own sounds", "crying", "begging"],
    "the_silence_memory": ["the silence", "oppressive", "deafening"],
}

NC_DEEP_HEALING_MILESTONES = {
    # Early milestones
    "first_day_didnt_think": ["first day didn't think about", "brief freedom", "forgot for moment"],
    "first_full_night_sleep": ["first full night sleep", "no nightmares", "rested"],
    "first_time_laughed": ["first time laughed", "genuine", "felt joy"],
    "first_time_felt_safe": ["first time felt safe", "moment of peace", "breathed"],

    # Functioning milestones
    "returned_to_work": ["returned to work", "went back", "functioning"],
    "left_house_alone": ["left house alone", "by myself", "could do it"],
    "being_in_crowds": ["being in crowds", "public places", "handled it"],
    "routine_restored": ["routine restored", "normal life", "back to"],

    # Relationship milestones
    "trusted_someone": ["trusted someone", "let them in", "told"],
    "accepted_help": ["accepted help", "let them", "received support"],
    "allowed_touch": ["allowed touch", "didn't flinch", "okay with"],
    "felt_connection": ["felt connection", "genuine", "not alone"],

    # Internal milestones
    "anger_felt": ["felt anger", "at them", "not at self"],
    "not_my_fault_belief": ["believed not my fault", "really believed", "core belief"],
    "future_imagined": ["imagined future", "could see ahead", "life continuing"],
    "identity_beyond_survivor": ["identity beyond", "more than survivor", "whole person"],

    # Integration milestones
    "told_without_crying": ["told without crying", "could talk about", "words came"],
    "trigger_managed": ["trigger managed", "got through", "controlled"],
    "anniversary_survived": ["survived anniversary", "got through date", "still here"],
    "helping_others": ["helping others", "using experience", "purpose from pain"],
}

# ============================================================================
# NC DEEP: LONG-TERM BODY EXPERIENCE
# ============================================================================

NC_DEEP_LONG_TERM_BODY = {
    # Chronic physical
    "chronic_tension": ["chronic tension", "always tight", "never relaxed"],
    "startle_response": ["exaggerated startle", "jump at sounds", "hypervigilant"],
    "sleep_disturbance_ongoing": ["ongoing sleep problems", "never sleep well", "always tired"],
    "appetite_changes_permanent": ["appetite never same", "relationship with food", "changed"],

    # Body relationship
    "body_as_stranger": ["body stranger", "don't know it", "disconnected"],
    "body_as_enemy": ["body enemy", "betrayed me", "can't trust"],
    "body_finally_mine": ["body finally mine", "reclaimed", "belongs to me"],
    "body_holds_memory": ["body holds memory", "remembers", "stored there"],

    # Physical manifestations
    "pain_without_cause": ["pain without cause", "no reason", "psychosomatic"],
    "autoimmune_issues": ["autoimmune", "body attacking", "inflammation"],
    "digestive_issues": ["digestive issues", "stomach", "gut problems"],
    "headaches_chronic": ["chronic headaches", "migraines", "constant pain"],

    # Physical healing
    "reconnecting_to_body": ["reconnecting", "learning body again", "feeling it"],
    "movement_healing": ["movement healing", "yoga", "exercise helped"],
    "body_work_healing": ["body work", "massage", "somatic therapy"],
    "body_as_home_again": ["body home again", "safe inside", "belonging"],
}

# ============================================================================
# CYOA/GENERATIVE FRAMEWORK - Scenario Variety
# For endless permutations in interactive fiction
# ============================================================================

# How the NC situation begins - what led to this moment
NC_SCENARIO_TRIGGERS = {
    # Wrong place/time
    "wrong_turn": ["took wrong turn", "got lost", "ended up", "shouldn't have come here"],
    "stayed_late": ["stayed too late", "last one there", "everyone else left", "alone after hours"],
    "shortcut": ["shortcut through", "decided to cut through", "faster way", "alley"],
    "isolated_location": ["no one around", "empty", "deserted", "quiet area", "secluded"],
    "car_trouble": ["car broke down", "flat tire", "ran out of gas", "needed help"],
    "wrong_door": ["wrong room", "wrong apartment", "wrong floor", "mistook the door"],
    "missed_ride": ["missed the bus", "ride fell through", "stranded", "no way home"],
    "bad_weather": ["caught in the rain", "storm", "had to find shelter", "take cover"],

    # Trust misplaced
    "trusted_friend": ["thought I could trust", "known him for years", "friend of a friend", "vouched for"],
    "trusted_date": ["seemed nice", "perfect gentleman", "good conversation", "felt safe with him"],
    "trusted_authority": ["in uniform", "professional", "position of trust", "supposed to help"],
    "trusted_family_friend": ["family friend", "known the family", "practically uncle", "close to family"],
    "trusted_colleague": ["worked together", "professional relationship", "office friend", "seemed normal"],
    "trusted_neighbor": ["lived next door", "saw him every day", "seemed harmless", "friendly neighbor"],
    "online_meeting": ["met online", "seemed different in person", "catfished", "not who he said"],
    "recommendation": ["someone recommended", "good reviews", "trusted referral", "came highly recommended"],

    # Vulnerability exploited
    "needed_money": ["desperate for money", "couldn't pay rent", "bills piling up", "financial trouble"],
    "needed_job": ["needed the job", "couldn't lose this", "no other options", "unemployed too long"],
    "needed_place": ["needed somewhere to stay", "homeless", "kicked out", "no other options"],
    "needed_help": ["needed his help", "only one who could", "depended on", "no one else"],
    "needed_grade": ["failing the class", "needed to pass", "scholarship on the line", "academic trouble"],
    "needed_fix": ["needed a fix", "withdrawal", "he had what I needed", "desperate"],
    "needed_favor": ["owed him", "needed something from him", "no leverage", "at his mercy"],
    "emotional_vulnerable": ["vulnerable moment", "just went through", "crying when", "emotionally raw"],

    # Manipulation/setup
    "drink_spiked": ["drink tasted wrong", "started feeling strange", "everything got fuzzy", "drugged"],
    "isolated_deliberately": ["led me away", "separated from friends", "got me alone", "isolated me"],
    "locked_in": ["door locked behind", "couldn't get out", "trapped", "no escape"],
    "blackmail_setup": ["had something on me", "pictures", "knew my secret", "would expose"],
    "debt_trap": ["owed too much", "couldn't pay back", "debt collected", "payment due"],
    "bet_lost": ["lost the bet", "stakes were clear", "pay up", "honor the bet"],
    "game_lost": ["lost the game", "winner takes", "those were the rules", "should have won"],
    "grooming_complete": ["been building to this", "months of grooming", "finally", "patient"],

    # Circumstantial
    "party_situation": ["party got out of hand", "too much to drink", "separated from friends", "late night"],
    "camping_trip": ["middle of nowhere", "no cell service", "no one to hear", "wilderness"],
    "road_trip": ["long drive", "middle of nowhere", "no other cars", "isolated highway"],
    "vacation_alone": ["traveling alone", "foreign country", "didn't speak language", "tourist"],
    "new_in_town": ["just moved", "didn't know anyone", "no support system", "isolated"],
    "houseguest": ["staying at his place", "guest room", "nowhere else to go", "his territory"],
    "sleepover": ["sleeping over", "middle of the night", "woke up to", "thought I was safe"],
    "shared_ride": ["shared the cab", "offered a ride", "carpooling", "get in"],
}

# Types of perpetrators - variety of villains
NC_PERPETRATOR_ARCHETYPES = {
    # Authority figures
    "perp_boss": ["boss", "supervisor", "manager", "employer", "CEO", "executive"],
    "perp_teacher": ["teacher", "professor", "instructor", "coach", "tutor", "mentor"],
    "perp_cop": ["cop", "police officer", "detective", "security guard", "officer"],
    "perp_doctor": ["doctor", "physician", "surgeon", "psychiatrist", "therapist"],
    "perp_priest": ["priest", "pastor", "minister", "clergy", "religious leader"],
    "perp_landlord": ["landlord", "property manager", "super", "building owner"],
    "perp_lawyer": ["lawyer", "attorney", "public defender", "legal aid"],
    "perp_judge": ["judge", "magistrate", "court official"],
    "perp_military": ["sergeant", "commanding officer", "drill instructor", "superior officer"],
    "perp_coach": ["coach", "trainer", "athletic director", "team manager"],

    # Social connections
    "perp_date": ["date", "guy from the app", "blind date", "setup", "first date"],
    "perp_boyfriend": ["boyfriend", "partner", "significant other", "lover"],
    "perp_ex": ["ex", "former boyfriend", "ex-partner", "used to date"],
    "perp_friend": ["friend", "buddy", "pal", "someone I knew", "thought was friend"],
    "perp_best_friend": ["best friend", "closest friend", "known forever", "trusted completely"],
    "perp_roommate": ["roommate", "housemate", "lived together", "shared space"],
    "perp_neighbor": ["neighbor", "guy next door", "lived nearby", "from the building"],
    "perp_classmate": ["classmate", "study partner", "lab partner", "from school"],
    "perp_coworker": ["coworker", "colleague", "office mate", "works with me"],

    # Family adjacent
    "perp_stepfather": ["stepfather", "stepdad", "mom's husband", "new dad"],
    "perp_uncle": ["uncle", "mom's brother", "dad's brother", "family"],
    "perp_family_friend": ["family friend", "dad's friend", "known for years", "uncle figure"],
    "perp_guardian": ["guardian", "caretaker", "in charge of me", "responsible for"],
    "perp_foster": ["foster parent", "foster brother", "foster family", "placed with"],
    "perp_in_law": ["brother-in-law", "father-in-law", "in-law", "married into"],

    # Strangers
    "perp_stranger": ["stranger", "never seen before", "random", "didn't know him"],
    "perp_delivery": ["delivery guy", "repairman", "service worker", "came to the door"],
    "perp_driver": ["uber driver", "cab driver", "ride share", "gave me a ride"],
    "perp_bartender": ["bartender", "server", "worked there", "served me drinks"],
    "perp_bouncer": ["bouncer", "doorman", "security", "let me in"],
    "perp_gym": ["guy from gym", "spotter", "trainer", "locker room"],

    # Power types
    "perp_rich": ["rich", "wealthy", "powerful", "influential", "connected"],
    "perp_famous": ["famous", "celebrity", "well-known", "everyone knew him"],
    "perp_criminal": ["criminal", "dealer", "gang member", "dangerous man"],
    "perp_violent": ["violent history", "known for", "reputation", "everyone afraid of"],
    "perp_charming": ["charming", "everyone liked him", "charismatic", "smooth talker"],
    "perp_respected": ["respected", "pillar of community", "no one would believe", "reputation"],

    # Group dynamics
    "perp_gang": ["group of them", "gang", "crew", "multiple", "they"],
    "perp_fraternity": ["frat brothers", "fraternity", "pledges", "brothers"],
    "perp_team": ["team", "teammates", "players", "athletes"],
    "perp_cult": ["cult leader", "group", "followers", "believers"],
}

# Different victim archetypes - who gets targeted
NC_VICTIM_ARCHETYPES = {
    # Naivety/inexperience
    "victim_naive": ["naive", "innocent", "sheltered", "didn't know better", "too trusting"],
    "victim_young": ["young", "barely", "just turned", "still in school"],
    "victim_virgin": ["virgin", "inexperienced", "first time", "never done"],
    "victim_new": ["new to this", "first day", "just started", "didn't know"],
    "victim_foreign": ["foreign", "didn't speak well", "tourist", "from another country"],
    "victim_rural": ["small town", "never seen", "not from the city", "sheltered"],

    # Circumstances
    "victim_alone": ["alone", "no friends here", "no family nearby", "isolated"],
    "victim_broke": ["broke", "no money", "desperate", "poor"],
    "victim_homeless": ["homeless", "no place to stay", "on the street", "couch surfing"],
    "victim_addicted": ["addicted", "needed fix", "withdrawal", "dependent"],
    "victim_indebted": ["in debt", "owed", "no way to pay", "underwater"],
    "victim_dependent": ["dependent on", "needed him for", "couldn't survive without"],

    # Social vulnerability
    "victim_closeted": ["closeted", "secret", "no one knew", "couldn't tell anyone"],
    "victim_outcast": ["outcast", "no friends", "loner", "didn't fit in"],
    "victim_unpopular": ["unpopular", "loser", "target", "always picked on"],
    "victim_immigrant": ["immigrant", "undocumented", "afraid of", "couldn't report"],
    "victim_minority": ["minority", "different", "stood out", "other"],

    # Psychological
    "victim_trusting": ["too trusting", "gave benefit of doubt", "wanted to believe"],
    "victim_polite": ["too polite", "couldn't say no", "didn't want to be rude"],
    "victim_people_pleaser": ["people pleaser", "always said yes", "hated conflict"],
    "victim_low_self_esteem": ["low self-esteem", "didn't think deserved better", "believed him"],
    "victim_trauma_history": ["history of", "happened before", "not the first time"],
    "victim_mental_health": ["depression", "anxiety", "struggling", "not thinking clearly"],

    # Situational
    "victim_drunk": ["drunk", "too many drinks", "wasted", "couldn't think straight"],
    "victim_high": ["high", "stoned", "fucked up", "not sober"],
    "victim_drugged": ["drugged", "slipped something", "roofied", "didn't consent"],
    "victim_tired": ["exhausted", "half asleep", "barely awake", "too tired to"],
    "victim_sick": ["sick", "fever", "not well", "weak"],
    "victim_injured": ["injured", "couldn't run", "hurt", "immobile"],

    # Character types
    "victim_overconfident": ["overconfident", "thought could handle", "underestimated"],
    "victim_reckless": ["reckless", "didn't think", "should have known", "ignored signs"],
    "victim_defiant": ["defiant", "fought back", "didn't give in easy", "resisted"],
    "victim_submissive": ["naturally submissive", "always followed", "compliant"],
    "victim_curious": ["curious", "wanted to try", "experimenting", "exploring"],
}

# Location variety - where it happens
NC_SETTING_VARIETY = {
    # Private spaces
    "setting_his_place": ["his apartment", "his house", "his place", "his bedroom"],
    "setting_my_place": ["my apartment", "my place", "my bedroom", "broke in"],
    "setting_hotel": ["hotel room", "motel", "rented room", "short stay"],
    "setting_dorm": ["dorm room", "college housing", "campus housing"],
    "setting_basement": ["basement", "underground", "cellar", "down the stairs"],
    "setting_attic": ["attic", "upstairs room", "hidden room"],
    "setting_garage": ["garage", "workshop", "shed", "outbuilding"],
    "setting_cabin": ["cabin", "cottage", "cabin in the woods", "remote house"],

    # Public/semi-public
    "setting_bathroom": ["bathroom", "restroom", "men's room", "stall"],
    "setting_locker_room": ["locker room", "changing room", "showers"],
    "setting_back_room": ["back room", "storage room", "supply closet", "back of store"],
    "setting_office": ["office", "after hours", "empty building", "closed"],
    "setting_classroom": ["classroom", "empty classroom", "after class"],
    "setting_church": ["church", "rectory", "confessional", "sacred space"],
    "setting_gym": ["gym", "weight room", "after hours gym"],
    "setting_pool": ["pool area", "sauna", "hot tub", "changing area"],

    # Vehicles
    "setting_car": ["car", "back seat", "parked car", "pulled over"],
    "setting_van": ["van", "back of van", "windowless", "cargo area"],
    "setting_truck": ["truck", "cab", "sleeper", "eighteen wheeler"],
    "setting_boat": ["boat", "yacht", "cabin below", "can't swim away"],
    "setting_rv": ["RV", "camper", "mobile home", "trailer"],

    # Outdoor
    "setting_alley": ["alley", "behind the building", "dark alley", "side street"],
    "setting_park": ["park", "after dark", "secluded area", "under trees"],
    "setting_woods": ["woods", "forest", "trees", "middle of nowhere"],
    "setting_beach": ["beach", "dunes", "secluded beach", "at night"],
    "setting_parking": ["parking lot", "parking garage", "underground parking"],
    "setting_rooftop": ["rooftop", "roof", "top of building", "no way down"],
    "setting_construction": ["construction site", "abandoned building", "empty lot"],

    # Institutional
    "setting_prison": ["prison", "jail", "holding cell", "locked up"],
    "setting_hospital": ["hospital", "exam room", "patient room", "medical"],
    "setting_military": ["barracks", "base", "military housing", "on base"],
    "setting_school": ["school", "campus", "university", "after hours"],
    "setting_rehab": ["rehab", "facility", "treatment center", "program"],
    "setting_shelter": ["shelter", "halfway house", "group home"],

    # Transit
    "setting_subway": ["subway", "train", "empty car", "late night train"],
    "setting_bus": ["bus", "back of bus", "empty bus", "night bus"],
    "setting_plane": ["plane", "airplane bathroom", "red eye", "overnight flight"],
    "setting_elevator": ["elevator", "stuck elevator", "between floors"],
    "setting_stairwell": ["stairwell", "stairs", "fire escape", "back stairs"],
}

# How victim survives/copes during - survival mechanics
NC_SURVIVAL_MECHANICS = {
    # Mental escape
    "survive_dissociate": ["went somewhere else", "left my body", "watched from outside", "wasn't there"],
    "survive_fantasy": ["imagined", "pretended", "in my mind", "somewhere else"],
    "survive_counting": ["counted", "focused on counting", "numbers", "tiles on ceiling"],
    "survive_song": ["song in my head", "humming internally", "lyrics", "melody"],
    "survive_memory": ["remembered", "thought about", "focused on memory", "happy place"],
    "survive_planning": ["planned", "thinking about after", "what I'd do", "escape plan"],

    # Compliance strategies
    "survive_comply": ["just let it happen", "didn't fight", "made it easier", "faster if I"],
    "survive_perform": ["gave him what he wanted", "faked", "pretended to", "acted like"],
    "survive_minimize": ["tried to minimize", "keep it from getting worse", "damage control"],
    "survive_negotiate": ["negotiated", "bargained", "please just", "if I do this will you"],
    "survive_appeal": ["appealed to", "tried to reason", "reminded him", "I'm a person"],

    # Physical endurance
    "survive_breathe": ["focused on breathing", "in and out", "just breathe", "stay conscious"],
    "survive_relax": ["tried to relax", "less damage if", "tensing made it worse"],
    "survive_position": ["shifted position", "made it bearable", "less painful if"],
    "survive_still": ["stayed still", "didn't move", "frozen", "statue"],
    "survive_small": ["made myself small", "curled up", "protected what I could"],

    # Observation/witness
    "survive_witness": ["became a witness", "remembered details", "memorizing", "for later"],
    "survive_evidence": ["thought about evidence", "don't wash", "remember for report"],
    "survive_time": ["tracked time", "how long", "when would it end", "almost over"],
    "survive_landmarks": ["remembered where", "street signs", "details of place"],

    # Emotional regulation
    "survive_numb": ["went numb", "stopped feeling", "turned off", "nothing"],
    "survive_detach": ["detached", "clinical", "observing", "not emotional"],
    "survive_anger": ["focused anger", "would make him pay", "revenge thoughts"],
    "survive_hope": ["held onto hope", "someone might", "it would end", "survive this"],

    # Dark humor/defiance
    "survive_humor": ["dark humor", "absurdity", "almost laughed", "ridiculous"],
    "survive_defiance": ["small defiance", "wouldn't give him", "kept something"],
    "survive_dignity": ["held onto dignity", "he couldn't take", "still me"],
    "survive_spite": ["spite", "wouldn't let him break", "survive to spite him"],
}

# Narrative choice points for CYOA - branch moments
NC_NARRATIVE_BRANCHES = {
    # Initial response choices
    "branch_fight_comply": ["fight or submit", "resist or give in", "struggle or still"],
    "branch_speak_silent": ["speak or stay silent", "scream or quiet", "call out or not"],
    "branch_look_away": ["look at him or look away", "eyes open or closed", "watch or not"],
    "branch_beg_defiant": ["beg or stay defiant", "plead or silent", "ask or demand"],

    # During choices
    "branch_participate_passive": ["participate or be passive", "move or stay still", "respond or not"],
    "branch_fake_honest": ["fake enjoyment or honest", "pretend or show truth", "perform or real"],
    "branch_humanize_anonymous": ["try to humanize or stay anonymous", "make him see or invisible"],
    "branch_time_fast": ["make it last or make it fast", "prolong or end quickly"],

    # Communication choices
    "branch_reason_silent": ["try to reason or stay quiet", "talk him down or nothing"],
    "branch_angry_calm": ["show anger or stay calm", "rage or neutral"],
    "branch_scared_brave": ["show fear or act brave", "let him see or hide it"],
    "branch_cry_stoic": ["let tears come or hold them", "cry or stoic"],

    # Physical choices
    "branch_tense_relax": ["tense up or try to relax", "fight body or surrender it"],
    "branch_protect_expose": ["protect parts or expose", "cover or let him see"],
    "branch_close_open": ["close eyes or keep open", "watch or not watch"],
    "branch_breathe_hold": ["breathe or hold breath", "steady or gasp"],

    # Strategic choices
    "branch_remember_forget": ["try to remember or try to forget", "memorize or block"],
    "branch_evidence_clean": ["preserve evidence or clean immediately", "report or hide"],
    "branch_tell_secret": ["tell someone or keep secret", "speak or silence"],
    "branch_confront_avoid": ["confront later or avoid forever", "face or flee"],
}

# Different outcomes/consequences - variety of endings
NC_OUTCOME_VARIETY = {
    # Immediate aftermath
    "outcome_released": ["let me go", "released", "done with me", "walked away"],
    "outcome_kept": ["kept me", "not done", "again", "wasn't over"],
    "outcome_threatened": ["threatened if I told", "warned me", "would come back", "watching"],
    "outcome_discarded": ["threw me out", "left me there", "abandoned", "disposed of"],
    "outcome_apologized": ["apologized", "said he was sorry", "didn't mean to", "got carried away"],
    "outcome_acted_normal": ["acted like nothing", "normal", "pretended", "what happened?"],

    # Discovery/exposure
    "outcome_caught": ["someone found out", "caught", "discovered", "walked in on"],
    "outcome_believed": ["believed me", "took seriously", "supported", "helped"],
    "outcome_not_believed": ["no one believed", "called me liar", "made it up", "attention seeking"],
    "outcome_blamed": ["blamed me", "my fault", "shouldn't have", "asked for it"],
    "outcome_secret": ["stayed secret", "never told", "buried", "no one knew"],

    # Relationship continuation
    "outcome_see_again": ["had to see him again", "work together", "same school", "unavoidable"],
    "outcome_never_again": ["never saw again", "disappeared", "gone", "moved away"],
    "outcome_continued": ["continued", "happened again", "pattern", "regular"],
    "outcome_escalated": ["escalated", "got worse", "more violent", "more frequent"],

    # Justice outcomes
    "outcome_reported": ["reported", "filed report", "went to police", "told authority"],
    "outcome_prosecuted": ["prosecuted", "charges filed", "court", "trial"],
    "outcome_convicted": ["convicted", "justice", "prison", "believed"],
    "outcome_acquitted": ["acquitted", "not guilty", "got away", "no justice"],
    "outcome_settled": ["settled", "paid off", "NDA", "silenced"],
    "outcome_nothing": ["nothing happened", "no consequences", "went on with life"],

    # Personal outcomes
    "outcome_breakdown": ["breakdown", "fell apart", "couldn't function", "shattered"],
    "outcome_survivor": ["survived", "kept going", "made it through", "still here"],
    "outcome_stronger": ["stronger", "never again", "learned", "grew"],
    "outcome_changed": ["changed", "different person", "before and after", "never the same"],
    "outcome_healing": ["healing", "therapy", "recovery", "slowly better"],
    "outcome_stuck": ["stuck", "can't move on", "haunted", "trapped in it"],
}

# Tone/atmosphere variety - different emotional registers
NC_TONE_VARIETY = {
    # Dark tones
    "tone_brutal": ["brutal", "savage", "violent", "no mercy", "ruthless"],
    "tone_clinical": ["clinical", "detached", "matter of fact", "cold", "efficient"],
    "tone_sadistic": ["sadistic", "enjoyed it", "pleasure from pain", "cruel"],
    "tone_predatory": ["predatory", "hunting", "prey", "stalked", "caught"],

    # Psychological tones
    "tone_gaslighting": ["gaslighting", "made me doubt", "crazy", "imagining"],
    "tone_manipulative": ["manipulative", "twisted", "made me think", "convinced me"],
    "tone_mindfuck": ["mindfuck", "psychological", "in my head", "mental games"],
    "tone_grooming": ["grooming", "gradual", "building trust", "slow burn"],

    # Atmospheric
    "tone_suffocating": ["suffocating", "couldn't breathe", "oppressive", "weight"],
    "tone_inevitable": ["inevitable", "no escape", "always going to", "fate"],
    "tone_surreal": ["surreal", "dreamlike", "couldn't be real", "nightmare"],
    "tone_visceral": ["visceral", "raw", "physical", "bodily", "flesh"],

    # Emotional register
    "tone_hopeless": ["hopeless", "no way out", "despair", "given up"],
    "tone_terrifying": ["terrifying", "pure fear", "horror", "dread"],
    "tone_numbing": ["numbing", "went blank", "nothing", "empty"],
    "tone_humiliating": ["humiliating", "degrading", "shameful", "exposed"],

    # Perspective tones
    "tone_intimate": ["intimate", "close", "personal", "invasive"],
    "tone_observational": ["observational", "watching", "witnessing", "documenting"],
    "tone_fragmented": ["fragmented", "pieces", "flashes", "broken memory"],
    "tone_stream": ["stream of consciousness", "thoughts racing", "internal", "mind"],

    # Dark variety
    "tone_absurd": ["absurd", "almost funny", "ridiculous", "dark comedy"],
    "tone_quiet": ["quiet", "silent", "no screaming", "muffled"],
    "tone_loud": ["loud", "screaming", "crying out", "noise"],
    "tone_intimate_violation": ["intimate violation", "tender violence", "gentle cruelty"],
}

# Perpetrator psychology - why they do it (motivation variety)
NC_PERPETRATOR_PSYCHOLOGY = {
    # Power motivations
    "psych_power": ["about power", "control", "dominance", "making me submit"],
    "psych_ownership": ["ownership", "possession", "mine", "belongs to me"],
    "psych_conquest": ["conquest", "winning", "taking", "claiming"],
    "psych_superiority": ["superiority", "better than", "above", "entitled"],

    # Entitlement
    "psych_deserved": ["deserved it", "owed him", "earned", "payment due"],
    "psych_right": ["his right", "entitled to", "allowed", "permission"],
    "psych_teased": ["teased too much", "led on", "asked for", "what did you expect"],
    "psych_owed": ["owed him", "after everything", "paid for", "did so much"],

    # Sadism
    "psych_enjoy_pain": ["enjoyed my pain", "got off on", "suffering", "loved my fear"],
    "psych_enjoy_power": ["enjoyed the power", "control rush", "having me helpless"],
    "psych_enjoy_degradation": ["enjoyed degrading", "humiliation", "making me feel"],
    "psych_collect": ["collecting", "trophy", "another one", "adding to"],

    # Rationalization
    "psych_teaching": ["teaching a lesson", "showed you", "learn", "education"],
    "psych_helping": ["helping you", "good for you", "needed this", "thank me"],
    "psych_love": ["because I love you", "out of love", "for your own good"],
    "psych_couldnt_help": ["couldn't help myself", "so beautiful", "couldn't resist"],

    # Revenge/anger
    "psych_revenge": ["revenge", "payback", "make you pay", "what you did"],
    "psych_anger": ["angry", "rage", "furious", "punishment"],
    "psych_rejection": ["rejected me", "said no", "turned down", "no one says no"],
    "psych_jealousy": ["jealous", "if I can't have you", "seeing you with", "mine"],

    # Opportunistic
    "psych_opportunity": ["opportunity", "chance", "couldn't pass up", "perfect moment"],
    "psych_convenient": ["convenient", "there", "available", "easy"],
    "psych_impulse": ["impulse", "sudden", "moment", "something came over"],
    "psych_drunk_excuse": ["too drunk", "not myself", "alcohol", "lowered inhibitions"],

    # Dehumanization
    "psych_object": ["just an object", "thing", "not a person", "doesn't matter"],
    "psych_less_than": ["less than", "below", "nothing", "worthless"],
    "psych_disposable": ["disposable", "replaceable", "use and throw", "doesn't count"],
    "psych_deserve_it": ["deserved it", "kind of person who", "that type", "obvious"],
}

# Time/pacing elements - duration and timing variety
NC_TEMPORAL_PACING = {
    # Duration types
    "duration_quick": ["quick", "fast", "over quickly", "didn't last long", "minutes"],
    "duration_prolonged": ["prolonged", "hours", "went on", "wouldn't end", "forever"],
    "duration_multiple": ["multiple times", "again and again", "rounds", "not done"],
    "duration_all_night": ["all night", "until morning", "hours", "lost track"],
    "duration_interrupted": ["interrupted", "almost caught", "had to stop", "close call"],
    "duration_ongoing": ["ongoing", "regular", "weekly", "whenever he wanted"],

    # Time of occurrence
    "time_night": ["at night", "dark", "nighttime", "after dark", "2am"],
    "time_day": ["broad daylight", "middle of day", "afternoon", "could have been seen"],
    "time_dawn": ["dawn", "early morning", "sun coming up", "first light"],
    "time_dusk": ["dusk", "sunset", "getting dark", "twilight"],

    # Pacing within
    "pacing_gradual": ["gradual", "slow build", "didn't realize at first", "crept up"],
    "pacing_sudden": ["sudden", "without warning", "out of nowhere", "instant"],
    "pacing_methodical": ["methodical", "systematic", "deliberate", "planned each"],
    "pacing_frenzied": ["frenzied", "wild", "chaotic", "uncontrolled"],
    "pacing_torturous": ["torturous", "dragging out", "making it last", "savoring"],

    # Before/during/after
    "time_before": ["before it started", "leading up", "moments before", "last normal moment"],
    "time_beginning": ["when it began", "first touch", "moment it started", "realization"],
    "time_middle": ["in the middle", "during", "while", "as it happened"],
    "time_ending": ["when it ended", "finally over", "last moment", "release"],
    "time_after": ["immediately after", "first moments free", "when he left", "alone again"],

    # Subjective time
    "time_stretched": ["time stretched", "felt like hours", "endless", "forever"],
    "time_compressed": ["blur", "happened so fast", "instant", "blink"],
    "time_fragmented": ["gaps", "blackouts", "pieces missing", "don't remember"],
    "time_hyperaware": ["every second", "hyperaware", "vivid", "etched"],
}

# Escalation patterns - how situations worsen
NC_ESCALATION_PATTERNS = {
    # Verbal escalation
    "escalate_verbal": ["started with words", "then touched", "words became action"],
    "escalate_threats": ["threats got worse", "escalated", "more serious", "deadly"],
    "escalate_volume": ["got louder", "started yelling", "screaming", "rage"],

    # Physical escalation
    "escalate_touch": ["touched first", "then grabbed", "then held down", "then"],
    "escalate_violence": ["more violent", "hitting", "choking", "hurting more"],
    "escalate_restraint": ["held hands", "then tied", "couldn't move", "helpless"],
    "escalate_weapons": ["showed weapon", "threatened with", "knife appeared", "gun"],

    # Acts escalation
    "escalate_acts": ["started with", "then wanted more", "not enough", "escalated to"],
    "escalate_invasion": ["first fingers", "then more", "bigger", "more invasive"],
    "escalate_degradation": ["first position", "then degrading", "worse", "humiliating"],
    "escalate_demands": ["first demand", "then another", "kept asking for", "more"],

    # Control escalation
    "escalate_isolation": ["first alone", "then locked", "took phone", "no escape"],
    "escalate_dependency": ["first help", "then dependent", "couldn't leave", "trapped"],
    "escalate_frequency": ["first once", "then more often", "regular", "constant"],
    "escalate_normalization": ["first shocked", "then expected", "routine", "normal"],

    # Resistance response
    "escalate_punishment": ["when I resisted", "punished for", "learned not to", "consequence"],
    "escalate_reward": ["good behavior rewarded", "less pain if", "easier when"],
    "escalate_breaking": ["breaking point", "finally broke", "gave up fighting", "accepted"],
}

# Interruption/near-miss scenarios
NC_INTERRUPTION_SCENARIOS = {
    # Almost caught
    "interrupt_noise": ["heard something", "noise outside", "had to stop", "close call"],
    "interrupt_knock": ["knock on door", "someone there", "had to hide", "pretend"],
    "interrupt_call": ["phone rang", "someone calling", "had to answer", "interrupted"],
    "interrupt_return": ["someone came back", "unexpected return", "heard car", "footsteps"],
    "interrupt_witness": ["someone saw", "caught glimpse", "witness", "not alone"],

    # Pause scenarios
    "pause_break": ["took a break", "let me rest", "moment of", "brief pause"],
    "pause_bathroom": ["bathroom", "had to pee", "moment alone", "locked door"],
    "pause_phone": ["his phone", "had to answer", "distracted", "brief window"],
    "pause_drink": ["got a drink", "left room", "moment alone", "seconds"],

    # Failed escape
    "escape_tried": ["tried to run", "made attempt", "almost got", "reached for"],
    "escape_caught": ["caught me", "grabbed before", "didn't make it", "too slow"],
    "escape_punished": ["punished for trying", "shouldn't have", "made it worse"],
    "escape_window": ["had a chance", "window of", "if I had", "missed it"],
}

# Sensory anchors - specific details that stick
NC_SENSORY_ANCHORS = {
    # Visual anchors
    "anchor_ceiling": ["stared at ceiling", "cracks in ceiling", "water stain", "pattern"],
    "anchor_light": ["that light", "flickering", "too bright", "darkness"],
    "anchor_clock": ["watched clock", "time passing", "numbers", "hands moving"],
    "anchor_object": ["focused on object", "lamp", "picture", "doorknob"],
    "anchor_his_face": ["his face", "expression", "eyes", "burned into memory"],

    # Sound anchors
    "anchor_music": ["music playing", "song forever ruined", "that song", "background"],
    "anchor_tv": ["TV on", "voices", "laugh track", "news"],
    "anchor_breathing": ["his breathing", "heavy breath", "panting", "sound"],
    "anchor_silence": ["silence", "too quiet", "could hear", "nothing but"],
    "anchor_outside": ["sounds outside", "cars passing", "normal life", "so close"],

    # Smell anchors
    "anchor_cologne": ["his cologne", "that smell", "forever associated", "triggers"],
    "anchor_alcohol": ["alcohol breath", "drunk smell", "liquor", "beer"],
    "anchor_sweat": ["sweat smell", "body odor", "his smell", "masculine"],
    "anchor_place": ["smell of place", "basement", "hotel", "car smell"],
    "anchor_cigarettes": ["cigarette smoke", "ash", "tobacco", "on his breath"],

    # Touch anchors
    "anchor_hands": ["his hands", "rough", "grip", "how they felt"],
    "anchor_weight": ["his weight", "on top of me", "crushing", "couldn't move"],
    "anchor_surface": ["cold floor", "rough carpet", "sheet texture", "against back"],
    "anchor_temperature": ["cold", "hot", "temperature", "shivering"],
    "anchor_fabric": ["his shirt", "jeans", "zipper", "clothes"],

    # Taste anchors
    "anchor_mouth": ["taste in mouth", "bile", "blood", "salt tears"],
    "anchor_gag": ["gagged on", "in my mouth", "taste of", "couldn't forget"],
}

# ============================================================================
# Compile all taxonomies into master dictionary
# ============================================================================

MASTER_TAXONOMY = {
    "consent": CONSENT_TAGS,
    "power_dynamics": POWER_DYNAMICS_TAGS,
    "relationships": RELATIONSHIP_TAGS,
    "character_archetypes": CHARACTER_ARCHETYPES,
    "physical_descriptors": PHYSICAL_DESCRIPTORS,
    "acts": ACTS_TAXONOMY,
    "settings": SETTINGS_TAXONOMY,
    "emotional": EMOTIONAL_TAXONOMY,
    "identity": IDENTITY_TAXONOMY,
    "kinks": KINK_TAXONOMY,
    "aftercare": AFTERCARE_TAXONOMY,
    "narrative": NARRATIVE_TAXONOMY,
    "bdsm_protocols": BDSM_PROTOCOLS,
    "leather_community": LEATHER_COMMUNITY,
    "bear_community": BEAR_COMMUNITY,
    "pup_community": PUP_COMMUNITY,
    "daddy_boy": DADDY_BOY_DYNAMICS,
    "master_slave": MASTER_SLAVE_DYNAMICS,
    "toys": TOY_TAXONOMY,
    "bondage": BONDAGE_TAXONOMY,
    "impact": IMPACT_TAXONOMY,
    "edge_play": EDGE_PLAY,
    "sensory": SENSORY_DETAILS,
    "era": ERA_TAXONOMY,
    "cultural": CULTURAL_TAXONOMY,
    "intensity": INTENSITY_TAXONOMY,
    "psychological": PSYCHOLOGICAL_TAXONOMY,
    "tropes": TROPES_TAXONOMY,
    "positions": POSITIONS_TAXONOMY,
    "fluids": FLUIDS_TAXONOMY,
    "pacing": PACING_TAXONOMY,
    "body_parts": BODY_PARTS_TAXONOMY,
    "verbal": VERBAL_TAXONOMY,
    "clothing": CLOTHING_TAXONOMY,
    "aftermath": AFTERMATH_TAXONOMY,
    "genre": GENRE_TAXONOMY,
    "kink_subcategories": KINK_SUBCATEGORIES,
    "age_dynamics": AGE_DYNAMICS,
    "appearance_diversity": APPEARANCE_DIVERSITY,
    "emotional_states": EMOTIONAL_STATES,
    "sensory_expanded": SENSORY_EXPANDED,
    "social_contexts": SOCIAL_CONTEXTS,
    "fantasy_elements": FANTASY_ELEMENTS,
    "omegaverse": OMEGAVERSE,
    "roleplay_scenarios": ROLEPLAY_SCENARIOS,
    "writing_style": WRITING_STYLE,
    "relationship_progression": RELATIONSHIP_PROGRESSION,
    "physical_reactions": PHYSICAL_REACTIONS,
    "environment_atmosphere": ENVIRONMENT_ATMOSPHERE,
    "communication_patterns": COMMUNICATION_PATTERNS,
    "conflict_types": CONFLICT_TYPES,
    "mental_health": MENTAL_HEALTH,
    "substance_elements": SUBSTANCE_ELEMENTS,
    "disability_rep": DISABILITY_REP,
    "coming_out_journey": COMING_OUT_JOURNEY,
    "scene_structure": SCENE_STRUCTURE,
    "character_voice": CHARACTER_VOICE,
    "micro_expressions": MICRO_EXPRESSIONS,
    "act_details": ACT_DETAILS,
    "scent": SCENT_TAXONOMY,
    "taste": TASTE_TAXONOMY,
    "touch_textures": TOUCH_TEXTURES,
    "internal_sensations": INTERNAL_SENSATIONS,
    "visual_details": VISUAL_DETAILS,
    "sound_details": SOUND_DETAILS,
    "power_exchange_details": POWER_EXCHANGE_DETAILS,
    "intimacy_levels": INTIMACY_LEVELS,
    "time_markers": TIME_MARKERS,
    "location_details": LOCATION_DETAILS,
    "anticipation": ANTICIPATION_ELEMENTS,
    "memory": MEMORY_ELEMENTS,
    "jealousy_possessiveness": JEALOUSY_POSSESSIVENESS,
    "secrets_hiding": SECRETS_HIDING,
    "au_tropes": AU_TROPES,
    "body_modification": BODY_MODIFICATION,
    "group_dynamics": GROUP_DYNAMICS,
    "praise_degradation": PRAISE_DEGRADATION,
    "size_kink_detailed": SIZE_KINK_DETAILED,
    "breeding_kink": BREEDING_KINK,
    "voyeurism_exhibitionism": VOYEURISM_EXHIBITIONISM,
    "technology": TECHNOLOGY_ELEMENTS,
    "evidence_documentation": EVIDENCE_DOCUMENTATION,
    "verbal_during_sex": VERBAL_DURING_SEX,
    "positions_detailed": POSITIONS_DETAILED,
    "first_time_details": FIRST_TIME_DETAILS,
    "profession_scenarios": PROFESSION_SCENARIOS,
    "sports_scenarios": SPORTS_SCENARIOS,
    "seasonal_settings": SEASONAL_SETTINGS,
    "daily_routine": DAILY_ROUTINE,
    "weather_mood": WEATHER_MOOD,
    "food_drink": FOOD_DRINK_ELEMENTS,
    "transportation": TRANSPORTATION_SCENARIOS,
    "toy_specifics": TOY_SPECIFICS,
    "hair_elements": HAIR_ELEMENTS,
    "sleep_dream": SLEEP_DREAM,
    "humor_intimacy": HUMOR_INTIMACY,
    "music": MUSIC_ELEMENTS,
    "class_dynamics": CLASS_DYNAMICS,
    "language_barriers": LANGUAGE_BARRIERS,
    "mirror_elements": MIRROR_ELEMENTS,
    "animal_references": ANIMAL_REFERENCES,
    "religious_elements": RELIGIOUS_ELEMENTS,
    "urban_rural": URBAN_RURAL,
    "age_specific": AGE_SPECIFIC,
    "body_worship_detailed": BODY_WORSHIP_DETAILED,
    "bdsm_ceremonies": BDSM_CEREMONIES,
    "negotiation_elements": NEGOTIATION_ELEMENTS,
    "aftercare_detailed": AFTERCARE_DETAILED,
    "character_motivations": CHARACTER_MOTIVATIONS,
    "relationship_red_flags": RELATIONSHIP_RED_FLAGS,
    "recovery_healing": RECOVERY_HEALING,
    "dialogue_patterns": DIALOGUE_PATTERNS,
    "scene_beats": SCENE_BEATS,
    "penetration_details": PENETRATION_DETAILS,
    "oral_details": ORAL_DETAILS,
    "manual_details": MANUAL_DETAILS,
    "frottage_outercourse": FROTTAGE_OUTERCOURSE,
    "prostate_detailed": PROSTATE_DETAILED,
    "chastity_denial": CHASTITY_DENIAL,
    "edging_detailed": EDGING_DETAILED,
    "hypnosis_elements": HYPNOSIS_ELEMENTS,
    "public_sex_specifics": PUBLIC_SEX_SPECIFICS,
    "fantasy_creatures": FANTASY_CREATURES,
    "medical_scenarios": MEDICAL_SCENARIOS,
    "uniforms_detailed": UNIFORMS_DETAILED,
    "phone_video_sex": PHONE_VIDEO_SEX,
    "tears_during_sex": TEARS_DURING_SEX,
    "marking_claiming": MARKING_CLAIMING,
    "virginity_focus": VIRGINITY_FOCUS,
    "anonymous_sex": ANONYMOUS_SEX,
    "dirty_messy": DIRTY_MESSY,
    "competition_games": COMPETITION_GAMES,
    "rope_patterns": ROPE_PATTERNS,
    "impact_patterns": IMPACT_PATTERNS,
    "toy_brands_types": TOY_BRANDS_TYPES,
    "roleplay_scripts": ROLEPLAY_SCRIPTS,
    "era_slang": ERA_SLANG,
    "character_backstory": CHARACTER_BACKSTORY,
    "plot_twists": PLOT_TWISTS,
    "consent_specific": CONSENT_SPECIFIC,
    "kink_micro": KINK_MICRO,
    "breathing_patterns": BREATHING_PATTERNS,
    "eye_contact_specific": EYE_CONTACT_SPECIFIC,
    "hand_specifics": HAND_SPECIFICS,
    "verbal_cues": VERBAL_CUES,
    "temperature_play": TEMPERATURE_PLAY,
    "rhythm_pace": RHYTHM_PACE,
    "skin_sensations": SKIN_SENSATIONS,
    "muscle_movements": MUSCLE_MOVEMENTS,
    "sweat_specific": SWEAT_SPECIFIC,
    "lips_mouth": LIPS_MOUTH,
    "neck_throat": NECK_THROAT,
    "back_specifics": BACK_SPECIFICS,
    "leg_thigh": LEG_THIGH,
    "submission_indicators": SUBMISSION_INDICATORS,
    "dominance_indicators": DOMINANCE_INDICATORS,
    "switching_dynamics": SWITCHING_DYNAMICS,
    "orgasm_specifics": ORGASM_SPECIFICS,
    "refractory_period": REFRACTORY_PERIOD,
    "settings_micro": SETTINGS_MICRO,
    "time_effects": TIME_EFFECTS,
    "nipple_play": NIPPLE_PLAY,
    "jealousy_triggers": JEALOUSY_TRIGGERS,
    "trust_building": TRUST_BUILDING,
    "intimacy_no_sex": INTIMACY_NO_SEX,
    "compliments_specific": COMPLIMENTS_SPECIFIC,
    "insecurities": INSECURITIES,
    "fantasy_reality": FANTASY_REALITY,
    "connection_chemistry": CONNECTION_CHEMISTRY,
    "quickie_specifics": QUICKIE_SPECIFICS,
    "marathon_sex": MARATHON_SEX,
    "worship_specific": WORSHIP_SPECIFIC,
    "unexpected_moments": UNEXPECTED_MOMENTS,
    "addiction_obsession": ADDICTION_OBSESSION,
    "hidden_desires": HIDDEN_DESIRES,
    "textures_during": TEXTURES_DURING,
    "angry_sex": ANGRY_SEX,
    "tender_sex": TENDER_SEX,
    "rough_sex": ROUGH_SEX,
    "lazy_sex": LAZY_SEX,
    "desperate_sex": DESPERATE_SEX,
    "makeup_sex": MAKEUP_SEX,
    "celebratory_sex": CELEBRATORY_SEX,
    "comfort_sex": COMFORT_SEX,
    "goodbye_sex": GOODBYE_SEX,
    "arousal_stages": AROUSAL_STAGES,
    "orgasm_types": ORGASM_TYPES,
    "subspace_elements": SUBSPACE_ELEMENTS,
    "domspace_elements": DOMSPACE_ELEMENTS,
    "voice_changes": VOICE_CHANGES,
    "facial_expressions": FACIAL_EXPRESSIONS,
    "hip_movements": HIP_MOVEMENTS,
    "hand_placement": HAND_PLACEMENT,
    "safeword_elements": SAFEWORD_ELEMENTS,
    "check_ins": CHECK_INS,
    "boundary_exploration": BOUNDARY_EXPLORATION,
    "spanking_detailed": SPANKING_DETAILED,
    "biting_detailed": BITING_DETAILED,
    "scratching_detailed": SCRATCHING_DETAILED,
    "hair_pulling_detailed": HAIR_PULLING_DETAILED,
    "penetration_sensations": PENETRATION_SENSATIONS,
    "receiving_oral_sensations": RECEIVING_ORAL_SENSATIONS,
    "giving_oral_sensations": GIVING_ORAL_SENSATIONS,
    "missionary_variations": MISSIONARY_VARIATIONS,
    "doggy_variations": DOGGY_VARIATIONS,
    "riding_variations": RIDING_VARIATIONS,
    "side_positions": SIDE_POSITIONS,
    "lube_elements": LUBE_ELEMENTS,
    "prep_elements": PREP_ELEMENTS,
    "clothing_during": CLOTHING_DURING,
    "condom_elements": CONDOM_ELEMENTS,
    "multiple_rounds": MULTIPLE_ROUNDS,
    "body_hair_elements": BODY_HAIR_ELEMENTS,
    "scars_marks": SCARS_MARKS,
    "tattoo_elements": TATTOO_ELEMENTS,
    "piercing_elements": PIERCING_ELEMENTS,
    "meeting_contexts": MEETING_CONTEXTS,
    "flirting_elements": FLIRTING_ELEMENTS,
    "first_kiss_elements": FIRST_KISS_ELEMENTS,
    "nervousness_elements": NERVOUSNESS_ELEMENTS,
    "experience_levels": EXPERIENCE_LEVELS,
    "size_descriptions": SIZE_DESCRIPTIONS,
    "stamina_elements": STAMINA_ELEMENTS,
    "interruption_elements": INTERRUPTION_ELEMENTS,
    "music_during_sex": MUSIC_DURING_SEX,
    "dirty_talk_specifics": DIRTY_TALK_SPECIFICS,
    "orgasm_reactions": ORGASM_REACTIONS,
    "shower_bath_sex": SHOWER_BATH_SEX,
    "outdoor_sex": OUTDOOR_SEX,
    "hotel_travel_sex": HOTEL_TRAVEL_SEX,
    "work_hookup": WORK_HOOKUP,
    "age_gap_dynamics": AGE_GAP_DYNAMICS,
    "physique_types": PHYSIQUE_TYPES,
    "cock_descriptions": COCK_DESCRIPTIONS,
    "ass_descriptions": ASS_DESCRIPTIONS,
    "nipple_descriptions": NIPPLE_DESCRIPTIONS,
    "precum_elements": PRECUM_ELEMENTS,
    "cum_elements": CUM_ELEMENTS,
    "ball_elements": BALL_ELEMENTS,
    "prostate_detailed": PROSTATE_DETAILED,
    "foreskin_elements": FORESKIN_ELEMENTS,
    "foot_play": FOOT_PLAY,
    "armpit_play": ARMPIT_PLAY,
    "muscle_worship": MUSCLE_WORSHIP,
    "uniform_gear": UNIFORM_GEAR,
    "watersports": WATERSPORTS,
    "humiliation_kink": HUMILIATION_KINK,
    "service_kink": SERVICE_KINK,
    "objectification": OBJECTIFICATION,
    "breath_play": BREATH_PLAY,
    "face_fucking": FACE_FUCKING,
    "glory_hole": GLORY_HOLE,
    "double_penetration": DOUBLE_PENETRATION,
    "fisting_elements": FISTING_ELEMENTS,
    "sounding_elements": SOUNDING_ELEMENTS,
    "cbt_elements": CBT_ELEMENTS,
    "electro_elements": ELECTRO_ELEMENTS,
    "slow_burn": SLOW_BURN,
    "enemies_to_lovers": ENEMIES_TO_LOVERS,
    "friends_to_lovers": FRIENDS_TO_LOVERS,
    "forbidden_love": FORBIDDEN_LOVE,
    "hurt_comfort": HURT_COMFORT,
    "second_chance": SECOND_CHANCE,
    "fake_dating": FAKE_DATING,
    "marriage_convenience": MARRIAGE_CONVENIENCE,
    "bodyguard_narrative": BODYGUARD_NARRATIVE,
    "celebrity_narrative": CELEBRITY_NARRATIVE,
    "boss_employee_narrative": BOSS_EMPLOYEE_NARRATIVE,
    "roommate_narrative": ROOMMATE_NARRATIVE,
    "trapped_narrative": TRAPPED_NARRATIVE,
    "online_relationship": ONLINE_RELATIONSHIP,
    "ons_to_more": ONS_TO_MORE,
    "arranged_relationship": ARRANGED_RELATIONSHIP,
    "humorous_tone": HUMOROUS_TONE,
    "dark_tone": DARK_TONE,
    "sweet_tone": SWEET_TONE,
    "smut_focused": SMUT_FOCUSED,
    "pov_perspective": POV_PERSPECTIVE,
    "length_markers": LENGTH_MARKERS,
    "chapter_structure": CHAPTER_STRUCTURE,
    "dialogue_style": DIALOGUE_STYLE,
    "setting_detail": SETTING_DETAIL,
    "emotional_intensity": EMOTIONAL_INTENSITY,
    "sexual_tension_types": SEXUAL_TENSION_TYPES,
    "character_growth": CHARACTER_GROWTH,
    "conflict_resolution": CONFLICT_RESOLUTION,
    "sensory_focus": SENSORY_FOCUS,
    "pacing_types": PACING_TYPES,
    "endings": ENDINGS,
    "reader_experience": READER_EXPERIENCE,
    "military_elements": MILITARY_ELEMENTS,
    "college_elements": COLLEGE_ELEMENTS,
    "high_school_aged": HIGH_SCHOOL_AGED,
    "musician_elements": MUSICIAN_ELEMENTS,
    "sports_specific": SPORTS_SPECIFIC,
    "medical_professional": MEDICAL_PROFESSIONAL,
    "law_enforcement": LAW_ENFORCEMENT,
    "firefighter_elements": FIREFIGHTER_ELEMENTS,
    "chef_elements": CHEF_ELEMENTS,
    "tattoo_artist_elements": TATTOO_ARTIST_ELEMENTS,
    "bartender_elements": BARTENDER_ELEMENTS,
    "trades_elements": TRADES_ELEMENTS,
    "tech_elements": TECH_ELEMENTS,
    "lawyer_elements": LAWYER_ELEMENTS,
    "pilot_elements": PILOT_ELEMENTS,
    "artist_elements": ARTIST_ELEMENTS,
    "royalty_elements": ROYALTY_ELEMENTS,
    "supernatural_beings": SUPERNATURAL_BEINGS,
    "shifter_elements": SHIFTER_ELEMENTS,
    "space_scifi": SPACE_SCIFI,
    "historical_periods": HISTORICAL_PERIODS,
    "nc_initial_realization": NC_INITIAL_REALIZATION,
    "nc_freeze_response": NC_FREEZE_RESPONSE,
    "nc_fight_suppressed": NC_FIGHT_SUPPRESSED,
    "nc_flight_blocked": NC_FLIGHT_BLOCKED,
    "nc_dissociation": NC_DISSOCIATION,
    "nc_body_betrayal": NC_BODY_BETRAYAL,
    "nc_internal_thoughts": NC_INTERNAL_THOUGHTS,
    "nc_perpetrator_tactics": NC_PERPETRATOR_TACTICS,
    "nc_scenario_types": NC_SCENARIO_TYPES,
    "nc_sensory_during": NC_SENSORY_DURING,
    "nc_physical_experience": NC_PHYSICAL_EXPERIENCE,
    "nc_aftermath_immediate": NC_AFTERMATH_IMMEDIATE,
    "nc_aftermath_longterm": NC_AFTERMATH_LONGTERM,
    "nc_coping": NC_COPING,
    "nc_recovery": NC_RECOVERY,
    "nc_dubcon_spectrum": NC_DUBCON_SPECTRUM,
    "nc_disclosure": NC_DISCLOSURE,
    "nc_narrative_treatment": NC_NARRATIVE_TREATMENT,
    "nc_verbal_during": NC_VERBAL_DURING,
    "nc_grooming": NC_GROOMING,
    "nc_body_memory": NC_BODY_MEMORY,
    "nc_time_perception": NC_TIME_PERCEPTION,
    "nc_emotions_during": NC_EMOTIONS_DURING,
    "nc_mental_escape": NC_MENTAL_ESCAPE,
    "nc_survival_physical": NC_SURVIVAL_PHYSICAL,
    "nc_physical_after": NC_PHYSICAL_AFTER,
    "nc_intimacy_after": NC_INTIMACY_AFTER,
    "nc_relationship_impact": NC_RELATIONSHIP_IMPACT,
    "nc_self_perception": NC_SELF_PERCEPTION,
    "nc_trigger_types": NC_TRIGGER_TYPES,
    "nc_moment_details": NC_MOMENT_DETAILS,
    "nc_internal_questions": NC_INTERNAL_QUESTIONS,
    "nc_help_seeking": NC_HELP_SEEKING,
    "nc_perpetrator_awareness": NC_PERPETRATOR_AWARENESS,
    "nc_healing_moments": NC_HEALING_MOMENTS,
    "nc_fictional_elements": NC_FICTIONAL_ELEMENTS,
    "nc_deep_physical_sensations": NC_DEEP_PHYSICAL_SENSATIONS,
    "nc_deep_micro_thoughts": NC_DEEP_MICRO_THOUGHTS,
    "nc_deep_breathing": NC_DEEP_BREATHING,
    "nc_deep_eyes": NC_DEEP_EYES,
    "nc_deep_hands": NC_DEEP_HANDS,
    "nc_deep_sounds": NC_DEEP_SOUNDS,
    "nc_deep_taste_smell": NC_DEEP_TASTE_SMELL,
    "nc_deep_body_parts": NC_DEEP_BODY_PARTS,
    "nc_deep_clothing": NC_DEEP_CLOTHING,
    "nc_deep_dissociation_types": NC_DEEP_DISSOCIATION_TYPES,
    "nc_deep_flashbacks": NC_DEEP_FLASHBACKS,
    "nc_deep_nightmares": NC_DEEP_NIGHTMARES,
    "nc_deep_first_hours": NC_DEEP_FIRST_HOURS,
    "nc_deep_telling": NC_DEEP_TELLING,
    "nc_deep_therapy": NC_DEEP_THERAPY,
    "nc_deep_body_reclamation": NC_DEEP_BODY_RECLAMATION,
    "nc_deep_coercion_scripts": NC_DEEP_COERCION_SCRIPTS,
    "nc_deep_physical_control": NC_DEEP_PHYSICAL_CONTROL,
    "nc_deep_survival_calculations": NC_DEEP_SURVIVAL_CALCULATIONS,
    "nc_deep_physical_damage": NC_DEEP_PHYSICAL_DAMAGE,
    "nc_deep_medical_after": NC_DEEP_MEDICAL_AFTER,
    "nc_deep_legal_reporting": NC_DEEP_LEGAL_REPORTING,
    "nc_deep_support_responses": NC_DEEP_SUPPORT_RESPONSES,
    "nc_deep_perp_relationship_after": NC_DEEP_PERP_RELATIONSHIP_AFTER,
    "nc_deep_self_perception": NC_DEEP_SELF_PERCEPTION,
    "nc_deep_trigger_experiences": NC_DEEP_TRIGGER_EXPERIENCES,
    "nc_deep_intimacy_rebuilding": NC_DEEP_INTIMACY_REBUILDING,
    "nc_deep_time_perception": NC_DEEP_TIME_PERCEPTION,
    "nc_deep_voice_speech": NC_DEEP_VOICE_SPEECH,
    "nc_deep_micro_sensations": NC_DEEP_MICRO_SENSATIONS,
    "nc_deep_perp_words": NC_DEEP_PERP_WORDS,
    "nc_villain_power_assertion": NC_VILLAIN_POWER_ASSERTION,
    "nc_villain_degradation": NC_VILLAIN_DEGRADATION,
    "nc_villain_gaslighting": NC_VILLAIN_GASLIGHTING,
    "nc_villain_threats": NC_VILLAIN_THREATS,
    "nc_villain_false_intimacy": NC_VILLAIN_FALSE_INTIMACY,
    "nc_villain_commands": NC_VILLAIN_COMMANDS,
    "nc_villain_taunting": NC_VILLAIN_TAUNTING,
    "nc_villain_body_commentary": NC_VILLAIN_BODY_COMMENTARY,
    "nc_villain_silencing": NC_VILLAIN_SILENCING,
    "nc_villain_aftermath_speech": NC_VILLAIN_AFTERMATH_SPEECH,
    "nc_villain_boss_dialogue": NC_VILLAIN_BOSS_DIALOGUE,
    "nc_villain_teacher_dialogue": NC_VILLAIN_TEACHER_DIALOGUE,
    "nc_villain_family_dialogue": NC_VILLAIN_FAMILY_DIALOGUE,
    "nc_villain_intimate_partner_dialogue": NC_VILLAIN_INTIMATE_PARTNER_DIALOGUE,
    "nc_villain_stranger_dialogue": NC_VILLAIN_STRANGER_DIALOGUE,
    "nc_deep_healing_milestones": NC_DEEP_HEALING_MILESTONES,
    "nc_deep_long_term_body": NC_DEEP_LONG_TERM_BODY,
    "nc_villain_during_penetration": NC_VILLAIN_DURING_PENETRATION,
    "nc_villain_oral_force": NC_VILLAIN_ORAL_FORCE,
    "nc_villain_psychological": NC_VILLAIN_PSYCHOLOGICAL,
    "nc_villain_manipulative_praise": NC_VILLAIN_MANIPULATIVE_PRAISE,
    "nc_villain_acts_commentary": NC_VILLAIN_ACTS_COMMENTARY,
    "nc_villain_recording": NC_VILLAIN_RECORDING,
    "nc_villain_time_pressure": NC_VILLAIN_TIME_PRESSURE,
    "nc_victim_protective_thoughts": NC_VICTIM_PROTECTIVE_THOUGHTS,
    "nc_victim_unwanted_arousal": NC_VICTIM_UNWANTED_AROUSAL,
    "nc_victim_moment_details": NC_VICTIM_MOMENT_DETAILS,
    "nc_villain_escalation": NC_VILLAIN_ESCALATION,
    "nc_deep_perp_breathing": NC_DEEP_PERP_BREATHING,
    "nc_deep_victim_eyes": NC_DEEP_VICTIM_EYES,
    "nc_villain_specific_phrases": NC_VILLAIN_SPECIFIC_PHRASES,
    "nc_villain_questions": NC_VILLAIN_QUESTIONS,
    "nc_villain_whispers": NC_VILLAIN_WHISPERS,
    "nc_villain_multiple_perp": NC_VILLAIN_MULTIPLE_PERP,
    "nc_villain_pauses": NC_VILLAIN_PAUSES,
    "nc_victim_frozen_state": NC_VICTIM_FROZEN_STATE,
    "nc_victim_counting_coping": NC_VICTIM_COUNTING_COPING,
    "nc_villain_clothing": NC_VILLAIN_CLOTHING,
    "nc_deep_smell_during": NC_DEEP_SMELL_DURING,
    "nc_deep_sound_environment": NC_DEEP_SOUND_ENVIRONMENT,
    "nc_villain_covering": NC_VILLAIN_COVERING,
    "nc_villain_grooming_dialogue": NC_VILLAIN_GROOMING_DIALOGUE,
    "nc_villain_ongoing_dialogue": NC_VILLAIN_ONGOING_DIALOGUE,
    "nc_villain_authority_specific": NC_VILLAIN_AUTHORITY_SPECIFIC,
    "nc_villain_age_dialogue": NC_VILLAIN_AGE_DIALOGUE,
    "nc_villain_compliments_during": NC_VILLAIN_COMPLIMENTS_DURING,
    "nc_villain_comparison": NC_VILLAIN_COMPARISON,
    "nc_villain_violence_escalation": NC_VILLAIN_VIOLENCE_ESCALATION,
    "nc_villain_position_dialogue": NC_VILLAIN_POSITION_DIALOGUE,
    "nc_villain_digital_coercion": NC_VILLAIN_DIGITAL_COERCION,
    "nc_villain_substance": NC_VILLAIN_SUBSTANCE,
    "nc_villain_final_warnings": NC_VILLAIN_FINAL_WARNINGS,
    "nc_villain_emotional_manipulation": NC_VILLAIN_EMOTIONAL_MANIPULATION,
    "nc_villain_body_commentary_extended": NC_VILLAIN_BODY_COMMENTARY_EXTENDED,
    "nc_villain_tears_dialogue": NC_VILLAIN_TEARS_DIALOGUE,
    "nc_villain_sounds": NC_VILLAIN_SOUNDS,
    "nc_villain_vehicle": NC_VILLAIN_VEHICLE,
    "nc_villain_workplace": NC_VILLAIN_WORKPLACE,
    "nc_villain_home": NC_VILLAIN_HOME,
    "nc_villain_party": NC_VILLAIN_PARTY,
    "nc_villain_desire_expression": NC_VILLAIN_DESIRE_EXPRESSION,
    "nc_victim_internal_bargaining": NC_VICTIM_INTERNAL_BARGAINING,
    "nc_victim_autonomy": NC_VICTIM_AUTONOMY,
    "nc_victim_fear_thoughts": NC_VICTIM_FEAR_THOUGHTS,
    "nc_villain_restraint_dialogue": NC_VILLAIN_RESTRAINT_DIALOGUE,
    "nc_villain_demanding_participation": NC_VILLAIN_DEMANDING_PARTICIPATION,
    "nc_villain_breathing_sounds": NC_VILLAIN_BREATHING_SOUNDS,
    "nc_villain_eye_contact": NC_VILLAIN_EYE_CONTACT,
    "nc_villain_touch_commentary": NC_VILLAIN_TOUCH_COMMENTARY,
    "nc_villain_pace_control": NC_VILLAIN_PACE_CONTROL,
    "nc_villain_claiming": NC_VILLAIN_CLAIMING,
    "nc_villain_humiliation": NC_VILLAIN_HUMILIATION,
    "nc_villain_false_reassurance": NC_VILLAIN_FALSE_REASSURANCE,
    "nc_victim_muscle_tension": NC_VICTIM_MUSCLE_TENSION,
    "nc_victim_breathing": NC_VICTIM_BREATHING,
    "nc_victim_pain_detailed": NC_VICTIM_PAIN_DETAILED,
    "nc_victim_body_parts": NC_VICTIM_BODY_PARTS,
    "nc_victim_dissociation_specific": NC_VICTIM_DISSOCIATION_SPECIFIC,
    "nc_villain_entitlement": NC_VILLAIN_ENTITLEMENT,
    "nc_villain_fingering": NC_VILLAIN_FINGERING,
    "nc_villain_forced_oral": NC_VILLAIN_FORCED_ORAL,
    "nc_villain_same_night": NC_VILLAIN_SAME_NIGHT,
    "nc_victim_after_physical": NC_VICTIM_AFTER_PHYSICAL,
    "nc_victim_after_mental": NC_VICTIM_AFTER_MENTAL,
    "nc_villain_location_threats": NC_VILLAIN_LOCATION_THREATS,
    "nc_villain_weapon_threats": NC_VILLAIN_WEAPON_THREATS,
    "nc_villain_mock_resistance": NC_VILLAIN_MOCK_RESISTANCE,
    "nc_villain_reaction_commentary": NC_VILLAIN_REACTION_COMMENTARY,
    "nc_victim_fear_types": NC_VICTIM_FEAR_TYPES,
    "nc_victim_internal_questions_deep": NC_VICTIM_INTERNAL_QUESTIONS,
    "nc_villain_time_dialogue": NC_VILLAIN_TIME_DIALOGUE,
    "nc_villain_ownership_extended": NC_VILLAIN_OWNERSHIP_EXTENDED,
    "nc_victim_shame_spiral": NC_VICTIM_SHAME_SPIRAL,
    "nc_victim_anger": NC_VICTIM_ANGER,
    "nc_villain_date_scenario": NC_VILLAIN_DATE_SCENARIO,
    "nc_villain_authority_scenario": NC_VILLAIN_AUTHORITY_SCENARIO,
    "nc_victim_betrayal": NC_VICTIM_BETRAYAL,
    "nc_villain_starting_phrases": NC_VILLAIN_STARTING_PHRASES,
    "nc_villain_during_phrases": NC_VILLAIN_DURING_PHRASES,
    "nc_villain_ending_phrases": NC_VILLAIN_ENDING_PHRASES,
    "nc_victim_sensations_during": NC_VICTIM_SENSATIONS_DURING,
    "nc_victim_mental_during": NC_VICTIM_MENTAL_DURING,
    "nc_villain_pleasure_manipulation": NC_VILLAIN_PLEASURE_MANIPULATION,
    "nc_villain_during_resistance": NC_VILLAIN_DURING_RESISTANCE,
    "nc_victim_coping_during": NC_VICTIM_COPING_DURING,
    "nc_villain_insults": NC_VILLAIN_INSULTS,
    "nc_villain_commands_extended": NC_VILLAIN_COMMANDS_EXTENDED,
    "nc_villain_grooming_progression": NC_VILLAIN_GROOMING_PROGRESSION,
    "nc_villain_relationship_manipulation": NC_VILLAIN_RELATIONSHIP_MANIPULATION,
    "nc_victim_long_term": NC_VICTIM_LONG_TERM,
    "nc_victim_recovery_stages": NC_VICTIM_RECOVERY_STAGES,
    "nc_villain_ejaculation": NC_VILLAIN_EJACULATION,
    "nc_victim_trauma_responses": NC_VICTIM_TRAUMA_RESPONSES,
    "nc_villain_body_focus": NC_VILLAIN_BODY_FOCUS,
    "nc_villain_name_use": NC_VILLAIN_NAME_USE,
    "nc_villain_duration": NC_VILLAIN_DURATION,
    "nc_victim_realization_moment": NC_VICTIM_REALIZATION_MOMENT,
    "nc_victim_body_micro": NC_VICTIM_BODY_MICRO,
    "nc_villain_kink_adjacent": NC_VILLAIN_KINK_ADJACENT,
    "nc_victim_sensory_overload": NC_VICTIM_SENSORY_OVERLOAD,
    "nc_villain_aftermath_threats": NC_VILLAIN_AFTERMATH_THREATS,
    "nc_victim_first_words": NC_VICTIM_FIRST_WORDS,
    "nc_villain_denial_dialogue": NC_VILLAIN_DENIAL_DIALOGUE,
    "nc_villain_twisted_praise": NC_VILLAIN_TWISTED_PRAISE,
    "nc_villain_contempt": NC_VILLAIN_CONTEMPT,
    "nc_victim_evidence": NC_VICTIM_EVIDENCE,
    "nc_victim_time_experience": NC_VICTIM_TIME_EXPERIENCE,
    "nc_villain_complicity": NC_VILLAIN_COMPLICITY,
    "nc_victim_help_barriers": NC_VICTIM_HELP_BARRIERS,
    "nc_villain_intoxication_scenario": NC_VILLAIN_INTOXICATION_SCENARIO,
    "nc_villain_power_dynamic_specific": NC_VILLAIN_POWER_DYNAMIC_SPECIFIC,
    "nc_victim_haunting_memories": NC_VICTIM_HAUNTING_MEMORIES,
}


def get_total_tags():
    """Count total unique tags in taxonomy."""
    count = 0
    for category, tags in MASTER_TAXONOMY.items():
        count += len(tags)
    return count


def get_total_keywords():
    """Count total keywords across all tags."""
    count = 0
    for category, tags in MASTER_TAXONOMY.items():
        for tag_name, tag_data in tags.items():
            if isinstance(tag_data, dict) and "keywords" in tag_data:
                count += len(tag_data["keywords"])
            elif isinstance(tag_data, list):
                count += len(tag_data)
    return count


if __name__ == "__main__":
    print("Exhaustive Tag Taxonomy")
    print("=" * 60)
    print(f"\nTotal categories: {len(MASTER_TAXONOMY)}")
    print(f"Total unique tags: {get_total_tags()}")
    print(f"Total keywords: {get_total_keywords()}")

    print("\nBreakdown by category:")
    for category, tags in MASTER_TAXONOMY.items():
        print(f"  {category}: {len(tags)} tags")
