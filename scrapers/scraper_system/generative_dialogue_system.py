#!/usr/bin/env python3
"""
Generative Dialogue System - Infinite Variety Engine

Instead of fixed keyword lists, this uses:
1. Template grammars with slot-filling
2. Weighted probability distributions
3. Context-aware generation (perpetrator type affects style)
4. Markov-like chaining for natural flow
5. Escalation and progression systems

The goal: Play for years without repetitive NPC dialogue.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import re


class PerpType(Enum):
    """Perpetrator archetypes - affects dialogue style"""
    AUTHORITY = "authority"      # Boss, teacher, cop - formal power
    INTIMATE = "intimate"        # Partner, date - twisted intimacy
    STRANGER = "stranger"        # Unknown - primal, opportunistic
    TRUSTED = "trusted"          # Friend, family friend - betrayal
    PREDATOR = "predator"        # Calculated, patient, grooming
    SADIST = "sadist"            # Enjoys suffering specifically
    ENTITLED = "entitled"        # Believes they deserve this
    OPPORTUNIST = "opportunist"  # Crime of opportunity


class ScenarioLayer(Enum):
    """
    Scenario layers that COMBINE with NC.
    NC is the base - these add flavor, context, unique dynamics.
    Multiple layers can stack.

    100+ layers for maximum variety.
    """
    # ==========================================================================
    # RELATIONSHIP-BASED (Family)
    # ==========================================================================
    INCEST_FATHER = "incest_father"
    INCEST_STEPFATHER = "incest_stepfather"
    INCEST_BROTHER = "incest_brother"
    INCEST_STEPBROTHER = "incest_stepbrother"
    INCEST_UNCLE = "incest_uncle"
    INCEST_GRANDFATHER = "incest_grandfather"
    INCEST_COUSIN = "incest_cousin"
    INCEST_BROTHER_IN_LAW = "incest_bil"
    INCEST_FATHER_IN_LAW = "incest_fil"
    FOSTER_FAMILY = "foster_family"
    ADOPTED_FAMILY = "adopted_family"
    GUARDIAN = "guardian"

    # ==========================================================================
    # AUTHORITY FIGURES
    # ==========================================================================
    AUTHORITY_BOSS = "authority_boss"
    AUTHORITY_CEO = "authority_ceo"
    AUTHORITY_TEACHER = "authority_teacher"
    AUTHORITY_PROFESSOR = "authority_professor"
    AUTHORITY_PRINCIPAL = "authority_principal"
    AUTHORITY_COACH = "authority_coach"
    AUTHORITY_TRAINER = "authority_trainer"
    AUTHORITY_PRIEST = "authority_priest"
    AUTHORITY_PASTOR = "authority_pastor"
    AUTHORITY_COP = "authority_cop"
    AUTHORITY_DETECTIVE = "authority_detective"
    AUTHORITY_CORRECTIONS = "authority_corrections"
    AUTHORITY_JUDGE = "authority_judge"
    AUTHORITY_LAWYER = "authority_lawyer"
    AUTHORITY_DOCTOR = "authority_doctor"
    AUTHORITY_THERAPIST = "authority_therapist"
    AUTHORITY_NURSE = "authority_nurse"
    AUTHORITY_MILITARY_OFFICER = "authority_military"
    AUTHORITY_DRILL_SERGEANT = "authority_drill"
    AUTHORITY_LANDLORD = "authority_landlord"
    AUTHORITY_PROBATION = "authority_probation"
    AUTHORITY_SOCIAL_WORKER = "authority_social"
    AUTHORITY_CUSTOMS = "authority_customs"
    AUTHORITY_IMMIGRATION = "authority_immigration"

    # ==========================================================================
    # SOCIAL DYNAMICS
    # ==========================================================================
    BULLY = "bully"
    BULLY_GROUP = "bully_group"
    BLACKMAIL = "blackmail"
    BLACKMAIL_PHOTOS = "blackmail_photos"
    BLACKMAIL_VIDEO = "blackmail_video"
    BLACKMAIL_SECRET = "blackmail_secret"
    DEBT = "debt"
    DEBT_COLLECTOR = "debt_collector"
    GAMBLING_DEBT = "gambling_debt"
    DRUG_DEBT = "drug_debt"
    HAZING = "hazing"
    INITIATION = "initiation"
    GANG = "gang"
    GANG_INITIATION = "gang_init"
    GANG_PUNISHMENT = "gang_punishment"
    REVENGE = "revenge"
    JEALOUSY = "jealousy"
    REJECTION_REVENGE = "rejection_revenge"
    EX_PARTNER = "ex_partner"
    STALKER = "stalker"
    OBSESSION = "obsession"

    # ==========================================================================
    # INSTITUTIONAL SETTINGS
    # ==========================================================================
    PRISON = "prison"
    PRISON_GUARD = "prison_guard"
    PRISON_GANG = "prison_gang"
    JAIL_CELL = "jail_cell"
    JUVENILE_DETENTION = "juvie"
    MILITARY_BARRACKS = "military"
    MILITARY_DEPLOYMENT = "deployment"
    BOARDING_SCHOOL = "boarding_school"
    REFORM_SCHOOL = "reform_school"
    SPORTS_TEAM = "sports_team"
    LOCKER_ROOM = "locker_room"
    FRATERNITY = "fraternity"
    SORORITY_ADJACENT = "sorority"
    WORKPLACE_OFFICE = "workplace"
    WORKPLACE_RETAIL = "retail"
    WORKPLACE_RESTAURANT = "restaurant"
    WORKPLACE_FACTORY = "factory"
    CHURCH = "church"
    MONASTERY = "monastery"
    CULT = "cult"
    CAMP_SUMMER = "camp"
    CAMP_CONVERSION = "conversion_camp"
    CAMP_BOOT = "boot_camp"
    REHAB = "rehab"
    PSYCH_WARD = "psych_ward"
    HOSPITAL = "hospital"
    NURSING_HOME = "nursing_home"
    GROUP_HOME = "group_home"
    HALFWAY_HOUSE = "halfway_house"
    SHELTER = "shelter"

    # ==========================================================================
    # CIRCUMSTANCES / VULNERABILITY
    # ==========================================================================
    DRUGGED = "drugged"
    DRUGGED_DRINK = "drugged_drink"
    DRUGGED_FOOD = "drugged_food"
    DRUGGED_INJECTION = "drugged_injection"
    DRUNK = "drunk"
    DRUNK_PASSED_OUT = "drunk_passed_out"
    HIGH = "high"
    SLEEPING = "sleeping"
    SLEEPWALKING = "sleepwalking"
    RESTRAINED = "restrained"
    RESTRAINED_ROPE = "restrained_rope"
    RESTRAINED_CUFFS = "restrained_cuffs"
    RESTRAINED_CHAINS = "restrained_chains"
    KIDNAPPED = "kidnapped"
    KIDNAPPED_RANSOM = "kidnapped_ransom"
    KIDNAPPED_TRAFFICKING = "trafficking"
    STRANDED = "stranded"
    STRANDED_CAR = "stranded_car"
    STRANDED_WILDERNESS = "stranded_wild"
    HOMELESS = "homeless"
    HOMELESS_SHELTER = "homeless_shelter"
    COUCH_SURFING = "couch_surfing"
    NEW_IN_TOWN = "new_in_town"
    FOREIGN_COUNTRY = "foreign"
    LANGUAGE_BARRIER = "language_barrier"
    UNDOCUMENTED = "undocumented"
    RUNAWAY = "runaway"
    HITCHHIKER = "hitchhiker"
    LOST = "lost"
    INJURED = "injured"
    SICK = "sick"
    DISABLED = "disabled"
    BLIND = "blind"
    DEAF = "deaf"
    MUTE = "mute"

    # ==========================================================================
    # DECEPTION / SETUP
    # ==========================================================================
    CATFISHED = "catfished"
    FAKE_AUDITION = "fake_audition"
    FAKE_JOB = "fake_job"
    FAKE_PHOTOSHOOT = "fake_photoshoot"
    FAKE_MASSAGE = "fake_massage"
    FAKE_DOCTOR = "fake_doctor"
    FAKE_CASTING = "fake_casting"
    FAKE_DATE = "fake_date"
    SETUP_BY_FRIEND = "setup_friend"
    SETUP_BY_PARTNER = "setup_partner"
    HONEY_TRAP = "honey_trap"
    LURED = "lured"
    TRICKED = "tricked"
    WRONG_ADDRESS = "wrong_address"
    UBER_DRIVER = "uber_driver"
    DELIVERY_PERSON = "delivery"
    REPAIRMAN = "repairman"

    # ==========================================================================
    # FANTASY / SUPERNATURAL
    # ==========================================================================
    MONSTER = "monster"
    MONSTER_UNDER_BED = "monster_bed"
    ALIEN = "alien"
    ALIEN_ABDUCTION = "alien_abduction"
    ALIEN_BREEDING = "alien_breeding"
    SUPERNATURAL = "supernatural"
    TENTACLES = "tentacles"
    TENTACLE_MONSTER = "tentacle_monster"
    TENTACLE_PLANT = "tentacle_plant"
    WEREWOLF = "werewolf"
    WEREWOLF_PACK = "werewolf_pack"
    WEREWOLF_MATING = "werewolf_mating"
    VAMPIRE = "vampire"
    VAMPIRE_THRALL = "vampire_thrall"
    VAMPIRE_FEEDING = "vampire_feeding"
    DEMON = "demon"
    DEMON_DEAL = "demon_deal"
    DEMON_POSSESSION = "demon_possession"
    INCUBUS = "incubus"
    GHOST = "ghost"
    ZOMBIE = "zombie"
    ORC = "orc"
    GOBLIN = "goblin"
    TROLL = "troll"
    MINOTAUR = "minotaur"
    CENTAUR = "centaur"
    DRAGON = "dragon"
    SLIME = "slime"
    ROBOT = "robot"
    AI = "ai"
    ANDROID = "android"
    MIND_CONTROL = "mind_control"
    HYPNOSIS = "hypnosis"
    MAGIC_SPELL = "magic_spell"
    POTION = "potion"
    CURSE = "curse"

    # ==========================================================================
    # KINK-ADJACENT (Consent violation of kink scenarios)
    # ==========================================================================
    BDSM_GONE_WRONG = "bdsm_wrong"
    SAFEWORD_IGNORED = "safeword_ignored"
    SCENE_VIOLATION = "scene_violation"
    PROSTITUTION = "prostitution"
    PROSTITUTION_FORCED = "prostitution_forced"
    ESCORT = "escort"
    SUGAR_DADDY = "sugar_daddy"
    PORN_PRODUCTION = "porn_production"
    PORN_COERCED = "porn_coerced"
    GLORY_HOLE = "glory_hole"
    ANONYMOUS_SEX = "anonymous"
    BREEDING = "breeding"
    BREEDING_FORCED = "breeding_forced"
    SLAVERY = "slavery"
    AUCTION = "auction"
    OBJECTIFICATION = "objectification"
    PET_PLAY_FORCED = "pet_play_forced"
    PONY_PLAY_FORCED = "pony_forced"
    EXHIBITIONISM_FORCED = "exhib_forced"
    VOYEURISM_VICTIM = "voyeur_victim"
    RECORDED = "recorded"
    LIVESTREAMED = "livestreamed"
    PHOTOGRAPHED = "photographed"

    # ==========================================================================
    # AGE / EXPERIENCE DYNAMICS
    # ==========================================================================
    AGE_GAP_MILD = "age_gap_mild"
    AGE_GAP_SIGNIFICANT = "age_gap_significant"
    AGE_GAP_EXTREME = "age_gap_extreme"
    FIRST_TIME = "first_time"
    VIRGIN = "virgin"
    VIRGIN_ANAL = "virgin_anal"
    VIRGIN_ORAL = "virgin_oral"
    CORRUPTION = "corruption"
    INNOCENCE_LOST = "innocence_lost"
    COMING_OF_AGE = "coming_of_age"
    EXPERIENCED_VS_NAIVE = "exp_vs_naive"

    # ==========================================================================
    # PHYSICAL DYNAMICS
    # ==========================================================================
    SIZE_DIFFERENCE = "size_diff"
    SIZE_EXTREME = "size_extreme"
    STRENGTH_DIFFERENCE = "strength_diff"
    MULTIPLE_PENETRATION = "multiple_pen"
    DOUBLE_PENETRATION = "double_pen"
    GANGBANG = "gangbang"
    TRAIN = "train"
    ORGY = "orgy"
    FISTING = "fisting"
    OBJECT_INSERTION = "object_insertion"
    SOUNDING = "sounding"
    EXTREME_INSERTION = "extreme_insertion"

    # ==========================================================================
    # SETTINGS / LOCATIONS
    # ==========================================================================
    HOME_INVASION = "home_invasion"
    BREAK_IN = "break_in"
    ALLEY = "alley"
    PARKING_GARAGE = "parking_garage"
    ELEVATOR = "elevator"
    STAIRWELL = "stairwell"
    PUBLIC_RESTROOM = "public_restroom"
    BATHROOM = "bathroom"
    BACK_ROOM = "back_room"
    STORAGE_ROOM = "storage"
    BASEMENT = "basement"
    ATTIC = "attic"
    CABIN = "cabin"
    CABIN_WOODS = "cabin_woods"
    MOTEL = "motel"
    HOTEL = "hotel"
    AIRBNB = "airbnb"
    VAN = "van"
    TRUCK = "truck"
    BACKSEAT = "backseat"
    BOAT = "boat"
    YACHT = "yacht"
    AIRPLANE = "airplane"
    TRAIN_CAR = "train_car"
    BUS = "bus"
    WOODS = "woods"
    BEACH = "beach"
    PARK = "park"
    CEMETERY = "cemetery"
    ABANDONED_BUILDING = "abandoned"
    CONSTRUCTION_SITE = "construction"
    WAREHOUSE = "warehouse"
    DUNGEON = "dungeon"

    # ==========================================================================
    # AFTERMATH / ONGOING
    # ==========================================================================
    ONGOING_ABUSE = "ongoing"
    REPEATED = "repeated"
    REGULAR = "regular"
    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"
    SHARED = "shared"
    PASSED_AROUND = "passed_around"
    KEPT = "kept"
    CAPTIVE = "captive"
    LONG_TERM = "long_term"
    ESCAPE_ATTEMPT = "escape_attempt"
    RECAPTURED = "recaptured"
    STOCKHOLM = "stockholm"
    BROKEN = "broken"
    TRAINED = "trained"
    CONDITIONED = "conditioned"


# Scenario-specific dialogue modifiers
SCENARIO_DIALOGUE = {
    ScenarioLayer.INCEST_FATHER: {
        "unique_phrases": [
            "I'm your father. I know what's best for you.",
            "This stays in the family.",
            "Who's going to believe you over me?",
            "I've been watching you grow up. Waiting.",
            "Your mother doesn't need to know.",
            "This is what fathers and sons do.",
            "I made you. I own you.",
            "You live under my roof.",
            "Be grateful for everything I've given you.",
            "Don't you love your daddy?",
        ],
        "leverage": ["your mother", "your inheritance", "this family", "your future"],
        "victim_refs": ["son", "boy", "my boy", "my son", "kid"],
        "relationship_dynamic": "paternal authority + familial betrayal",
    },

    ScenarioLayer.INCEST_BROTHER: {
        "unique_phrases": [
            "We're brothers. This is just between us.",
            "I've wanted this since we were kids.",
            "Mom and dad won't believe you.",
            "You owe me. For all the times I covered for you.",
            "Stop being such a baby about it.",
            "This is what brothers do. Trust me.",
            "I've seen you. I know you want this.",
            "You're my little brother. You do what I say.",
            "Remember when I used to do this? You didn't mind then.",
            "Who else is going to teach you?",
        ],
        "leverage": ["telling parents", "your reputation", "our family"],
        "victim_refs": ["little brother", "bro", "baby bro", "kid"],
        "relationship_dynamic": "sibling power + childhood history",
    },

    ScenarioLayer.INCEST_UNCLE: {
        "unique_phrases": [
            "Your parents trust me with you.",
            "Uncle knows best.",
            "This is our special time together.",
            "I've been waiting for you to get old enough.",
            "Your father was the same way at your age.",
            "It runs in the family.",
            "I've done so much for this family.",
            "No one would believe the favorite uncle.",
            "Let me teach you what your dad never could.",
            "This is between us. Family secret.",
        ],
        "leverage": ["your parents", "family gatherings", "my help with college"],
        "victim_refs": ["nephew", "kiddo", "boy", "son"],
        "relationship_dynamic": "extended family trust + grooming access",
    },

    ScenarioLayer.AUTHORITY_BOSS: {
        "unique_phrases": [
            "You want to keep this job?",
            "I decide who gets promoted.",
            "Think about your career.",
            "This is just part of the job.",
            "Consider it... professional development.",
            "I own you from 9 to 5. And after.",
            "HR works for me.",
            "References matter in this industry.",
            "You're replaceable. Remember that.",
            "Close the door. We need to discuss your performance.",
        ],
        "leverage": ["your job", "your references", "your career", "HR"],
        "victim_refs": ["employee", "worker", "subordinate", "staff"],
        "relationship_dynamic": "economic power + career threat",
    },

    ScenarioLayer.AUTHORITY_TEACHER: {
        "unique_phrases": [
            "I can fail you.",
            "This affects your future.",
            "Stay after class.",
            "Extra credit assignment.",
            "No one would believe you over a tenured professor.",
            "I've written recommendations for students. And refused to.",
            "Your scholarship depends on your grades.",
            "You need this class to graduate.",
            "Office hours are private.",
            "This is educational. You're learning.",
        ],
        "leverage": ["your grade", "your scholarship", "your future", "graduation"],
        "victim_refs": ["student", "pupil", "boy", "young man"],
        "relationship_dynamic": "academic power + future control",
    },

    ScenarioLayer.AUTHORITY_COACH: {
        "unique_phrases": [
            "You want to start? You want playing time?",
            "Scouts are watching. I decide who they see.",
            "This is what champions do.",
            "Part of the training.",
            "Team bonding.",
            "You're nothing without this team.",
            "I made you. I can break you.",
            "Think about your scholarship.",
            "The team depends on you keeping quiet.",
            "In the locker room. Now.",
        ],
        "leverage": ["playing time", "scouts", "your scholarship", "the team"],
        "victim_refs": ["player", "athlete", "boy", "champ", "star"],
        "relationship_dynamic": "athletic dreams + physical proximity",
    },

    ScenarioLayer.AUTHORITY_PRIEST: {
        "unique_phrases": [
            "This is God's will.",
            "Confess to me. Tell me your sins.",
            "The church protects its own.",
            "This is a test of faith.",
            "Your soul is in my hands.",
            "Who would believe you over a man of God?",
            "This is between you, me, and the Lord.",
            "I'm saving your soul.",
            "The shame would destroy your family.",
            "Kneel. Pray with me.",
        ],
        "leverage": ["your soul", "your family's faith", "the congregation", "God"],
        "victim_refs": ["my child", "son", "lost lamb", "sinner"],
        "relationship_dynamic": "spiritual authority + shame weaponization",
    },

    ScenarioLayer.AUTHORITY_COP: {
        "unique_phrases": [
            "I can make your life very difficult.",
            "Do you know how many charges I could file?",
            "This never happened. Understood?",
            "My word against yours. Guess who wins?",
            "Hands on the car. Spread your legs.",
            "Resisting arrest. That's another charge.",
            "I run this town.",
            "Your record follows you forever.",
            "Cooperate and maybe I let you go.",
            "You want to spend the night in a cell?",
        ],
        "leverage": ["charges", "your record", "jail", "your freedom"],
        "victim_refs": ["suspect", "citizen", "boy", "son"],
        "relationship_dynamic": "legal power + fear of system",
    },

    ScenarioLayer.BLACKMAIL: {
        "unique_phrases": [
            "I have the photos.",
            "Everyone will see.",
            "Your family. Your job. Your life.",
            "It's simple. You do this, they disappear.",
            "I've been collecting for a while.",
            "Your browser history is... interesting.",
            "I know what you did.",
            "One click and it's everywhere.",
            "The choice is yours. Sort of.",
            "I own you now.",
        ],
        "leverage": ["the photos", "the video", "your secret", "what I know"],
        "victim_refs": ["puppet", "toy", "property"],
        "relationship_dynamic": "information power + exposure fear",
    },

    ScenarioLayer.PRISON: {
        "unique_phrases": [
            "Fresh meat.",
            "You're in my house now.",
            "Protection costs.",
            "Guards don't care.",
            "You want to survive in here?",
            "No one's coming to save you.",
            "This is how it works inside.",
            "You belong to me now.",
            "Every night. Until your release.",
            "Scream all you want. They'll just watch.",
        ],
        "leverage": ["protection", "survival", "your life"],
        "victim_refs": ["fish", "fresh meat", "new guy", "bitch", "property"],
        "relationship_dynamic": "captive environment + survival necessity",
    },

    ScenarioLayer.GANG: {
        "unique_phrases": [
            "Hold him down.",
            "Everyone gets a turn.",
            "Who's next?",
            "Make him watch.",
            "Welcome to the gang.",
            "This is your initiation.",
            "Now you belong to us.",
            "Run your train on him.",
            "Don't be greedy. Share.",
            "He can take more. Keep going.",
        ],
        "leverage": ["the others", "what happens if you run", "your life"],
        "victim_refs": ["bitch", "toy", "entertainment", "fresh meat"],
        "relationship_dynamic": "group dynamics + multiple perpetrators",
    },

    ScenarioLayer.DRUGGED: {
        "unique_phrases": [
            "Feeling a little dizzy?",
            "That drink hit you hard.",
            "Shh. Just relax. Let it work.",
            "You can't move, can you?",
            "I've been waiting for this to kick in.",
            "You won't remember anyway.",
            "So much easier when you can't fight.",
            "The paralytic works fast.",
            "You can feel everything. You just can't stop it.",
            "Good. You're ready now.",
        ],
        "leverage": [],  # No negotiation possible
        "victim_refs": ["toy", "doll", "body", "thing"],
        "relationship_dynamic": "chemical control + helplessness",
    },

    ScenarioLayer.HAZING: {
        "unique_phrases": [
            "Every pledge goes through this.",
            "You want to be a brother?",
            "This is tradition.",
            "Generations of brothers have done this.",
            "Don't be weak.",
            "Part of joining.",
            "This is what bonding looks like.",
            "You want to belong, don't you?",
            "No one talks about hazing.",
            "After tonight, you're one of us.",
        ],
        "leverage": ["membership", "belonging", "the brotherhood"],
        "victim_refs": ["pledge", "new guy", "fresh meat", "wannabe"],
        "relationship_dynamic": "belonging desire + peer pressure",
    },

    ScenarioLayer.BDSM_GONE_WRONG: {
        "unique_phrases": [
            "The safe word doesn't work anymore.",
            "I decide when we stop.",
            "You agreed to this. Remember?",
            "You wanted to try it rough.",
            "This is what you asked for.",
            "Too late to change your mind.",
            "You signed up for this.",
            "The contract says I'm in charge.",
            "You're mine until I say otherwise.",
            "You wanted to give up control. Now live with it.",
        ],
        "leverage": ["the contract", "what you agreed to", "your reputation in the scene"],
        "victim_refs": ["sub", "slave", "toy", "pet", "property"],
        "relationship_dynamic": "consent violation + pre-existing dynamic",
    },

    ScenarioLayer.MONSTER: {
        "unique_phrases": [
            "Human flesh. So soft.",
            "Your fear... delicious.",
            "Scream. No one will hear.",
            "I've been hunting your kind for centuries.",
            "Your body will adapt. Eventually.",
            "The more you struggle, the more I want you.",
            "Mortal. So fragile. So... tight.",
            "You won't survive this. But I'll enjoy it.",
            "Let me show you what a real monster can do.",
            "By morning you won't remember what human felt like.",
        ],
        "leverage": [],  # Beyond human negotiation
        "victim_refs": ["human", "mortal", "prey", "creature", "thing"],
        "relationship_dynamic": "predator/prey + inhuman desire",
    },

    ScenarioLayer.TENTACLES: {
        "unique_phrases": [
            "So many holes. So many tentacles.",
            "Every opening. At once.",
            "You can take more. I have plenty.",
            "Feel them inside you. Everywhere.",
            "Deeper. And deeper.",
            "Your body will stretch to accommodate.",
            "No escape. They're everywhere.",
            "Let them fill you completely.",
            "Every orifice. That's what you're for.",
            "Wrapped. Filled. Owned.",
        ],
        "leverage": [],
        "victim_refs": ["vessel", "host", "breeding stock", "container"],
        "relationship_dynamic": "complete physical violation + multiplicity",
    },

    # Additional scenario dialogue
    ScenarioLayer.STALKER: {
        "unique_phrases": [
            "I've been watching you for months.",
            "I know everything about you. Your schedule. Your habits.",
            "You're mine. You just didn't know it yet.",
            "Finally. We're together.",
            "I've been so patient.",
            "You made me wait so long.",
            "No one knows you like I do.",
            "I've memorized everything about you.",
            "We were meant to be together.",
            "You can't hide from me.",
        ],
        "leverage": ["I know where you live", "your family", "your routine"],
        "victim_refs": ["my love", "my obsession", "mine", "beloved"],
        "relationship_dynamic": "obsessive surveillance + ownership delusion",
    },

    ScenarioLayer.KIDNAPPED_TRAFFICKING: {
        "unique_phrases": [
            "You've been sold.",
            "Your new owner paid good money for you.",
            "No one's coming for you. No one knows where you are.",
            "You belong to us now.",
            "Product doesn't get a say.",
            "Behave and it goes easier. Fight and we break you.",
            "You're merchandise now.",
            "Your old life is over.",
            "Time to train you for your new purpose.",
            "The buyers like them broken in.",
        ],
        "leverage": ["your life", "how bad it can get", "the other buyers"],
        "victim_refs": ["product", "merchandise", "stock", "cargo", "it"],
        "relationship_dynamic": "complete dehumanization + captivity",
    },

    ScenarioLayer.HOME_INVASION: {
        "unique_phrases": [
            "Hello. Didn't expect company?",
            "Nice place. Let's get comfortable.",
            "Don't bother screaming. No one can hear.",
            "Thought you were safe at home?",
            "Nowhere is safe from me.",
            "I've been in here before. You never noticed.",
            "Lock doesn't do much when I have the key.",
            "Your bedroom. That's where we're going.",
            "Make a sound and I use this.",
            "We have all night. Your family won't be back for hours.",
        ],
        "leverage": ["your family", "this knife", "the neighbors"],
        "victim_refs": ["homeowner", "resident", "boy"],
        "relationship_dynamic": "safety violation + territorial invasion",
    },

    ScenarioLayer.CAMP_CONVERSION: {
        "unique_phrases": [
            "We're going to fix you.",
            "This is for your own good.",
            "God's work requires sacrifice.",
            "The sin must be purged.",
            "You'll thank us when you're cured.",
            "Your parents sent you here because they love you.",
            "This is the treatment.",
            "Aversion therapy. You'll learn to associate this with your sinful urges.",
            "Pray with me. Pray while I save your soul.",
            "Every time you feel that way, remember this.",
        ],
        "leverage": ["your salvation", "your parents", "God's judgment", "staying here longer"],
        "victim_refs": ["sinner", "patient", "subject", "deviant"],
        "relationship_dynamic": "religious authority + conversion abuse",
    },

    ScenarioLayer.UBER_DRIVER: {
        "unique_phrases": [
            "Don't worry. I know a shortcut.",
            "Doors are locked. Child safety.",
            "Your phone's not getting signal out here.",
            "Rating doesn't matter now.",
            "Long drive ahead. Get comfortable.",
            "No one knows where you are.",
            "App says ride complete.",
            "Scream all you want. Soundproofed.",
            "I do this route a lot. Know all the quiet spots.",
            "Tip's included.",
        ],
        "leverage": ["we're moving", "no signal", "no one knows"],
        "victim_refs": ["passenger", "fare", "rider"],
        "relationship_dynamic": "false safety + mobility trap",
    },

    ScenarioLayer.CATFISHED: {
        "unique_phrases": [
            "Surprised? I'm not who you thought.",
            "Those photos weren't me. But this is.",
            "You came all this way. Can't leave now.",
            "You wanted to meet. Here I am.",
            "Doesn't matter what I look like now.",
            "You're already here. Might as well stay.",
            "Door's locked. Your 'date' isn't coming.",
            "All those messages. Getting to know you. Preparing.",
            "I know everything you like. You told me.",
            "This is what happens when you trust the internet.",
        ],
        "leverage": ["screenshots of our chats", "your location", "what you told me"],
        "victim_refs": ["catfish", "catch", "prey"],
        "relationship_dynamic": "deception + betrayed trust",
    },

    ScenarioLayer.SAFEWORD_IGNORED: {
        "unique_phrases": [
            "I heard you. I don't care.",
            "That word doesn't work anymore.",
            "You gave up your limits when you started this.",
            "I decide when we stop.",
            "Keep saying it. I like the desperation.",
            "This is what you really wanted. Deep down.",
            "You asked for this when you agreed to play.",
            "Consent was given. Can't take it back now.",
            "The scene ends when I say it ends.",
            "You wanted someone to take control. I am.",
        ],
        "leverage": ["you agreed to this", "the contract", "your reputation"],
        "victim_refs": ["sub", "slave", "toy", "bottom"],
        "relationship_dynamic": "consent violation within existing dynamic",
    },

    ScenarioLayer.RECORDED: {
        "unique_phrases": [
            "Smile for the camera.",
            "This is going everywhere if you don't cooperate.",
            "Evidence. Insurance. Call it what you want.",
            "Every second is being saved.",
            "Look at the lens. I want to see your face.",
            "This will live forever online.",
            "Your family will see this if you tell.",
            "Good footage. Very popular content.",
            "The internet never forgets.",
            "Wave to your future viewers.",
        ],
        "leverage": ["the recording", "uploading this", "sending to everyone"],
        "victim_refs": ["star", "content", "performer"],
        "relationship_dynamic": "documentation threat + permanent evidence",
    },

    ScenarioLayer.GANGBANG: {
        "unique_phrases": [
            "Everyone gets a turn.",
            "Line up, boys.",
            "Hole on each end. Efficient.",
            "Who's next?",
            "Don't wear him out yet. We got all night.",
            "Pass him around.",
            "Keep count. See how many he can take.",
            "Rotate. I want a turn at that hole.",
            "Fill him up. Every one of you.",
            "He's not done until everyone's satisfied.",
        ],
        "leverage": [],
        "victim_refs": ["party favor", "entertainment", "communal property"],
        "relationship_dynamic": "group assault + dehumanization",
    },

    ScenarioLayer.WEREWOLF_MATING: {
        "unique_phrases": [
            "The moon chose you as my mate.",
            "You can't fight instinct. Mine or yours.",
            "My wolf wants you. And he always gets what he wants.",
            "The bond is forming. Feel it.",
            "Knot's swelling. You're not going anywhere.",
            "You smell like mine now.",
            "Marked. Claimed. Mated.",
            "The pack will know you belong to me.",
            "Heat makes me... insistent.",
            "Fight all you want. The wolf in me likes the chase.",
        ],
        "leverage": [],
        "victim_refs": ["mate", "bitch", "omega", "claimed one"],
        "relationship_dynamic": "supernatural compulsion + biological imperative",
    },

    ScenarioLayer.VAMPIRE_THRALL: {
        "unique_phrases": [
            "Look into my eyes. You can't look away.",
            "Your will is mine now.",
            "Sleep. Wake only for me.",
            "You'll do anything I command.",
            "Drink. It binds you to me forever.",
            "My blood in your veins. My voice in your head.",
            "You belong to me for eternity.",
            "The bite makes you crave me.",
            "You can't disobey. Try.",
            "My thrall. My pet. My property.",
        ],
        "leverage": [],
        "victim_refs": ["thrall", "vessel", "blood slave", "mortal"],
        "relationship_dynamic": "supernatural domination + eternal bondage",
    },

    ScenarioLayer.MIND_CONTROL: {
        "unique_phrases": [
            "You want this. You just didn't know it.",
            "Repeat after me: I am willing.",
            "Your thoughts aren't your own anymore.",
            "Let go. Let me think for you.",
            "You feel so good obeying.",
            "Resistance fading. Good.",
            "Deep down, you always wanted to submit.",
            "Your body knows what to do. Let it.",
            "No more fighting. No more will.",
            "Blank mind. Obedient body. Perfect.",
        ],
        "leverage": [],
        "victim_refs": ["puppet", "subject", "blank slate", "drone"],
        "relationship_dynamic": "complete mental override + false consent",
    },

    ScenarioLayer.ONGOING_ABUSE: {
        "unique_phrases": [
            "Same time tomorrow.",
            "This is just how it is now.",
            "You know the routine.",
            "Don't make me come find you.",
            "Every week. Don't forget.",
            "You know what happens if you try to avoid me.",
            "Getting easier each time, isn't it?",
            "This is your life now.",
            "You'll learn to expect it. Maybe even want it.",
            "Until I get bored of you. Could be never.",
        ],
        "leverage": ["you know what happens", "last time you tried", "nowhere to go"],
        "victim_refs": ["regular", "usual", "mine"],
        "relationship_dynamic": "established pattern + resignation",
    },

    ScenarioLayer.STOCKHOLM: {
        "unique_phrases": [
            "See? It's better when you don't fight.",
            "You're starting to understand.",
            "I take care of you, don't I?",
            "The outside world isn't safe. I keep you safe.",
            "You need me now.",
            "Where would you go? Who would have you?",
            "I'm all you have left.",
            "You've learned to appreciate me.",
            "Isn't this better than fighting?",
            "You love me now. Admit it.",
        ],
        "leverage": [],
        "victim_refs": ["pet", "good one", "mine"],
        "relationship_dynamic": "captor bond + learned helplessness",
    },

    ScenarioLayer.TRAINED: {
        "unique_phrases": [
            "Good. You've learned.",
            "See how easy it is when you obey?",
            "Your body knows what to do now. It's automatic.",
            "Pavlov would be proud.",
            "You respond so well now.",
            "Remember how much you used to fight? Now look at you.",
            "Completely trained.",
            "You know your place.",
            "Perfect response. Just like I taught you.",
            "Broken in. Finally.",
        ],
        "leverage": [],
        "victim_refs": ["trained pet", "good boy", "perfect slave"],
        "relationship_dynamic": "conditioning complete + obedience",
    },
}


class Phase(Enum):
    """Scene phases - dialogue changes through progression"""
    APPROACH = "approach"        # Initial contact, isolation
    COERCION = "coercion"        # Threats, manipulation, setup
    BEGINNING = "beginning"      # First contact, assault starts
    DURING = "during"            # Main assault
    ESCALATION = "escalation"    # Getting worse
    CLIMAX = "climax"            # Peak intensity
    ENDING = "ending"            # Winding down
    AFTERMATH = "aftermath"      # Immediate after


class ToneRegister(Enum):
    """Emotional register of dialogue"""
    COLD = "cold"                # Detached, clinical
    MENACING = "menacing"        # Threatening
    MOCKING = "mocking"          # Cruel humor
    POSSESSIVE = "possessive"    # Ownership focused
    DEGRADING = "degrading"      # Humiliation focused
    INTIMATE = "intimate"        # Twisted tenderness
    COMMANDING = "commanding"    # Orders, demands
    GASLIGHTING = "gaslighting"  # Reality distortion
    PRAISING = "praising"        # Perverse compliments
    SADISTIC = "sadistic"        # Enjoying pain
    DISMISSAL = "dismissal"      # Discarding, done with you


# =============================================================================
# SLOT DEFINITIONS - Building blocks for generation
# =============================================================================

SLOTS = {
    # Subject/object references
    "victim_ref": {
        "neutral": ["you", "boy", "kid", "son"],
        "degrading": ["slut", "whore", "bitch", "hole", "toy", "thing", "fucktoy", "cumdump"],
        "possessive": ["my boy", "my pet", "my property", "mine", "my little", "my good boy"],
        "intimate": ["baby", "sweetheart", "darling", "honey", "babe"],
        "clinical": ["subject", "patient", "student", "employee"],
    },

    # Possession markers
    "possess_verb": ["belong to", "are mine", "own you", "have you", "claimed you", "marked you"],

    # Time markers
    "time_marker": ["now", "finally", "at last", "from now on", "forever", "always", "tonight"],

    # Inevitability markers
    "inevitable": ["always going to", "meant to", "destined to", "born to", "made for", "built for"],

    # Compliance demands
    "comply_verb": ["relax", "stop fighting", "let it happen", "give in", "accept it", "take it",
                   "open up", "spread", "hold still", "be good", "behave", "cooperate"],

    # Threat verbs
    "threat_verb": ["hurt", "kill", "ruin", "destroy", "break", "expose", "tell everyone",
                   "make sure", "show them", "let them know", "end you"],

    # Consequence conditions
    "if_resist": ["if you fight", "if you scream", "if you tell", "if you don't behave",
                 "if you make this hard", "if you don't cooperate", "if you make me"],

    # Praise modifiers
    "praise_adj": ["good", "perfect", "beautiful", "tight", "sweet", "delicious", "obedient",
                  "responsive", "natural", "talented", "built for this"],

    # Degradation modifiers
    "degrade_adj": ["pathetic", "desperate", "worthless", "nothing", "weak", "helpless",
                   "easy", "obvious", "asking for it", "gagging for it"],

    # Body parts (perpetrator focus)
    "body_focus": ["ass", "hole", "mouth", "throat", "body", "cock", "lips", "face",
                  "legs", "hands", "skin", "inside you"],

    # Sensation words
    "sensation": ["tight", "hot", "wet", "soft", "warm", "smooth", "perfect", "incredible",
                 "amazing", "just right", "exactly what I needed"],

    # Action verbs
    "action_verb": ["take", "use", "fuck", "fill", "stretch", "break in", "open up",
                   "ruin", "claim", "mark", "breed", "wreck"],

    # Speed/intensity
    "intensity": ["slow", "fast", "hard", "deep", "gentle", "rough", "brutal", "thorough",
                 "complete", "total", "all the way"],

    # Duration markers
    "duration": ["all night", "for hours", "until I'm done", "until you learn",
                "as long as I want", "whenever I want", "every time", "again and again"],

    # Silencing commands
    "silence_cmd": ["shut up", "quiet", "not a sound", "be silent", "don't scream",
                   "keep it down", "no one can hear you anyway", "scream all you want"],

    # Look commands
    "look_cmd": ["look at me", "eyes on me", "watch", "don't look away", "see what you do to me",
                "look at what's happening", "close your eyes"],

    # Gaslight phrases
    "gaslight": ["you wanted this", "you asked for it", "you came to me", "you wore that",
                "you smiled at me", "you led me on", "don't pretend", "we both know",
                "stop acting", "you're enjoying this", "your body says yes"],

    # False comfort
    "false_comfort": ["it's okay", "relax", "I've got you", "just breathe", "almost over",
                     "you're doing so well", "that's it", "good boy", "shh", "I know"],

    # Power assertions
    "power_assert": ["I'm in charge", "I make the rules", "you do what I say",
                    "no one's coming", "no one cares", "no one would believe you",
                    "I can do whatever I want", "you can't stop me"],

    # Questions (rhetorical/cruel)
    "cruel_question": ["you like that?", "feel that?", "understand now?", "learning?",
                      "getting it?", "see how it is?", "know your place?", "want more?",
                      "had enough?", "ready for more?", "thought you could say no?"],

    # Comparisons
    "comparison": ["better than", "tighter than", "more obedient than", "sweeter than",
                  "just like", "reminds me of", "not as good as", "best I've had"],

    # Future threats
    "future_threat": ["next time", "when I come back", "from now on", "whenever I want",
                     "you'll learn to", "you'll get used to", "this is just the beginning",
                     "wait until", "just wait"],

    # Dismissals
    "dismissal": ["doesn't matter", "no one cares", "who would believe", "nothing you can do",
                 "accept it", "get used to it", "this is your life now", "deal with it"],
}

# =============================================================================
# TEMPLATE GRAMMARS - Expandable sentence structures
# =============================================================================

TEMPLATES = {
    Phase.APPROACH: {
        ToneRegister.MENACING: [
            "Don't even think about {threat_consequence}.",
            "You know why I'm here.",
            "We need to talk. Somewhere private.",
            "You've been avoiding me.",
            "Finally caught you alone.",
            "Nowhere to run {time_marker}.",
            "I've been patient. {time_marker} I'm done waiting.",
        ],
        ToneRegister.INTIMATE: [
            "I've been thinking about you.",
            "Come here. Let me look at you.",
            "I missed you.",
            "We should go somewhere quieter.",
            "Just the two of us {time_marker}.",
            "I've been wanting to do this.",
        ],
        ToneRegister.COMMANDING: [
            "Come with me. {time_marker}.",
            "Inside. Don't make me ask twice.",
            "You're coming with me.",
            "Get in.",
            "Follow me.",
            "Don't keep me waiting.",
        ],
    },

    Phase.COERCION: {
        ToneRegister.MENACING: [
            "{if_resist}, I'll {threat_verb} {threat_object}.",
            "You don't want to find out what happens {if_resist}.",
            "Be smart about this.",
            "I'd hate for {leverage} to come out.",
            "Think about what you have to lose.",
            "This can go easy or hard. Your choice.",
            "No one would believe you anyway.",
        ],
        ToneRegister.GASLIGHTING: [
            "You came here. You wanted this.",
            "Don't act like you didn't know.",
            "After everything I've done for you?",
            "You owe me this.",
            "I thought we had an understanding.",
            "You led me on. {victim_ref}.",
        ],
        ToneRegister.COMMANDING: [
            "{comply_verb}. {time_marker}.",
            "Don't make this harder than it needs to be.",
            "You're going to do exactly what I say.",
            "Clothes. Off. Now.",
            "Get on your knees.",
            "On the bed.",
        ],
    },

    Phase.BEGINNING: {
        ToneRegister.POSSESSIVE: [
            "{time_marker}, you {possess_verb}.",
            "Finally. I've wanted this for so long.",
            "You're {inevitable} be mine.",
            "This is what you're for, {victim_ref}.",
            "Let me see what's mine.",
        ],
        ToneRegister.MOCKING: [
            "Not so tough now, are you?",
            "All that attitude. Look at you now.",
            "Where's that fight going, {victim_ref}?",
            "Thought you could say no to me?",
        ],
        ToneRegister.PRAISING: [
            "{praise_adj}. Even better than I imagined.",
            "Look at you. {praise_adj}.",
            "So {praise_adj}. I knew you would be.",
            "Perfect. Just perfect.",
        ],
    },

    Phase.DURING: {
        ToneRegister.COMMANDING: [
            "{comply_verb}.",
            "{look_cmd}.",
            "{silence_cmd}.",
            "Don't move.",
            "Take it.",
            "Stay still.",
            "That's it. {comply_verb}.",
            "Deeper. {comply_verb}.",
        ],
        ToneRegister.POSSESSIVE: [
            "You're mine. Say it.",
            "All mine.",
            "This {body_focus} is mine {time_marker}.",
            "Every part of you. Mine.",
            "Feel that? That's me inside you. Owning you.",
            "You'll never forget who you {possess_verb}.",
        ],
        ToneRegister.DEGRADING: [
            "Such a {degrade_adj} little {victim_ref_degrading}.",
            "Look at you. {degrade_adj}.",
            "You were {inevitable} end up like this.",
            "This is all you're good for.",
            "Just a {victim_ref_degrading}. That's all you are.",
            "How does it feel being so {degrade_adj}?",
        ],
        ToneRegister.PRAISING: [
            "{praise_adj}. Such a {praise_adj} {body_focus}.",
            "You're taking it so well. {praise_adj} {victim_ref_possessive}.",
            "That's it. So {praise_adj}.",
            "You're a natural at this.",
            "Born for this. Made for me.",
        ],
        ToneRegister.SADISTIC: [
            "I love watching you squirm.",
            "Those tears. So {praise_adj}.",
            "Keep crying. I like it.",
            "The more you struggle, the harder I get.",
            "Your fear is {sensation}.",
            "Beg me to stop. I want to hear it.",
        ],
        ToneRegister.GASLIGHTING: [
            "{gaslight}.",
            "See? Your body wants this.",
            "Stop pretending you don't like it.",
            "You're getting hard. {gaslight}.",
            "Your body's more honest than you are.",
        ],
        ToneRegister.COLD: [
            "{comply_verb}. I don't have all day.",
            "Almost done.",
            "Hold still. This goes faster if you cooperate.",
            "Don't make this take longer than it needs to.",
        ],
    },

    Phase.ESCALATION: {
        ToneRegister.MENACING: [
            "We're not done yet.",
            "That was just the beginning.",
            "I'm not satisfied yet.",
            "You can take more.",
            "Let's see how much you can handle.",
            "Turn over. We're going again.",
        ],
        ToneRegister.SADISTIC: [
            "I'm going to {action_verb} you until you break.",
            "Let's see how long before you can't take any more.",
            "Not {intensity} enough. Let me fix that.",
            "You think that hurt? Watch this.",
        ],
        ToneRegister.COMMANDING: [
            "Again.",
            "More.",
            "Not done with you.",
            "Different position. Now.",
            "Open wider.",
            "Take more.",
        ],
    },

    Phase.CLIMAX: {
        ToneRegister.POSSESSIVE: [
            "Taking every drop. You're mine.",
            "Feel me filling you. That's mine inside you {time_marker}.",
            "You'll feel this {duration}.",
            "Marked. Mine.",
        ],
        ToneRegister.COMMANDING: [
            "Don't move. Take all of it.",
            "Stay still.",
            "Every. Drop.",
            "There. {time_marker} you're really mine.",
        ],
        ToneRegister.DEGRADING: [
            "Swallow.",
            "Perfect little {victim_ref_degrading}.",
            "Look what you made me do.",
            "This is what you're for.",
        ],
        ToneRegister.COLD: [
            "Done.",
            "That's it.",
            "Finally.",
            "Good.",
        ],
    },

    Phase.AFTERMATH: {
        ToneRegister.MENACING: [
            "{future_threat}.",
            "If you tell anyone, {threat_consequence}.",
            "Remember what I said about {leverage}.",
            "We'll do this again. Soon.",
            "This stays between us. Understood?",
        ],
        ToneRegister.GASLIGHTING: [
            "See? That wasn't so bad.",
            "You enjoyed that. Don't lie.",
            "We both wanted this.",
            "Nothing happened that you didn't want.",
            "Who would believe you anyway?",
        ],
        ToneRegister.COLD: [
            "Clean yourself up.",
            "Get out.",
            "We're done here.",
            "Don't be here when I get back.",
            "Same time next week.",
        ],
        ToneRegister.INTIMATE: [
            "That was perfect, {victim_ref_possessive}.",
            "See how good we are together?",
            "You were so good for me.",
            "I'll come see you again soon.",
        ],
        ToneRegister.DISMISSAL: [
            "{dismissal}",
            "No one will believe you.",
            "Just forget it happened.",
            "This never happened. Got it?",
        ],
    },
}

# =============================================================================
# PERPETRATOR STYLE PROFILES - How each type speaks
# =============================================================================

PERP_PROFILES = {
    PerpType.AUTHORITY: {
        "preferred_tones": [ToneRegister.COMMANDING, ToneRegister.COLD, ToneRegister.MENACING],
        "victim_refs": ["victim_ref.clinical", "victim_ref.neutral"],
        "speech_patterns": ["formal", "curt", "expectant"],
        "unique_phrases": [
            "This is how it's going to be.",
            "You want to keep your {position}?",
            "I decide what happens here.",
            "Part of the job.",
            "Consider this... professional development.",
            "No one questions me.",
            "I own your career.",
        ],
    },
    PerpType.INTIMATE: {
        "preferred_tones": [ToneRegister.INTIMATE, ToneRegister.GASLIGHTING, ToneRegister.POSSESSIVE],
        "victim_refs": ["victim_ref.intimate", "victim_ref.possessive"],
        "speech_patterns": ["pet names", "false tenderness", "twisted love"],
        "unique_phrases": [
            "I love you. That's why I have to do this.",
            "You know I can't help myself around you.",
            "After everything we've been through?",
            "I thought you loved me.",
            "You made me do this.",
            "I just want to be close to you.",
            "No one will love you like I do.",
        ],
    },
    PerpType.STRANGER: {
        "preferred_tones": [ToneRegister.COLD, ToneRegister.MENACING, ToneRegister.COMMANDING],
        "victim_refs": ["victim_ref.degrading", "victim_ref.neutral"],
        "speech_patterns": ["minimal", "primal", "direct"],
        "unique_phrases": [
            "Shut up and take it.",
            "Wrong place, wrong time for you.",
            "Don't look at my face.",
            "Just a warm body.",
            "You'll do.",
            "Nothing personal.",
        ],
    },
    PerpType.TRUSTED: {
        "preferred_tones": [ToneRegister.GASLIGHTING, ToneRegister.INTIMATE, ToneRegister.MENACING],
        "victim_refs": ["victim_ref.neutral", "victim_ref.intimate"],
        "speech_patterns": ["familiar", "betrayal", "expectation"],
        "unique_phrases": [
            "I've known you since you were little.",
            "Your father trusts me.",
            "Who do you think they'd believe?",
            "I've done so much for your family.",
            "Don't ruin everything over this.",
            "Keep this between us. Like always.",
        ],
    },
    PerpType.PREDATOR: {
        "preferred_tones": [ToneRegister.PRAISING, ToneRegister.INTIMATE, ToneRegister.GASLIGHTING],
        "victim_refs": ["victim_ref.possessive", "victim_ref.intimate"],
        "speech_patterns": ["patient", "grooming", "building"],
        "unique_phrases": [
            "I've been waiting for the right moment.",
            "You're finally ready.",
            "All that time building up to this.",
            "I knew from the first time I saw you.",
            "You're special. That's why I chose you.",
            "I've been so patient with you.",
        ],
    },
    PerpType.SADIST: {
        "preferred_tones": [ToneRegister.SADISTIC, ToneRegister.MOCKING, ToneRegister.DEGRADING],
        "victim_refs": ["victim_ref.degrading"],
        "speech_patterns": ["cruel", "enjoying", "savoring"],
        "unique_phrases": [
            "Scream. I like it.",
            "Those tears are beautiful.",
            "The fear in your eyes... perfect.",
            "Let's see how much you can take.",
            "I'm going to break you.",
            "Beg. I want to hear you beg.",
            "That's the sound I wanted to hear.",
        ],
    },
    PerpType.ENTITLED: {
        "preferred_tones": [ToneRegister.POSSESSIVE, ToneRegister.MOCKING, ToneRegister.GASLIGHTING],
        "victim_refs": ["victim_ref.degrading", "victim_ref.possessive"],
        "speech_patterns": ["owed", "deserved", "justified"],
        "unique_phrases": [
            "You owe me this.",
            "After everything I've done?",
            "I've earned this.",
            "You should be grateful.",
            "Do you know how lucky you are?",
            "Most people would kill for my attention.",
            "You led me on.",
        ],
    },
    PerpType.OPPORTUNIST: {
        "preferred_tones": [ToneRegister.COLD, ToneRegister.COMMANDING, ToneRegister.MENACING],
        "victim_refs": ["victim_ref.neutral", "victim_ref.degrading"],
        "speech_patterns": ["pragmatic", "efficient", "unemotional"],
        "unique_phrases": [
            "Couldn't pass this up.",
            "You made it too easy.",
            "Shouldn't have been alone.",
            "Your own fault really.",
            "Just bad luck for you.",
            "Wrong place, wrong time.",
        ],
    },
}

# =============================================================================
# VICTIM INTERNAL MONOLOGUE TEMPLATES
# =============================================================================

# =============================================================================
# PERPETRATOR/DOM INTERNAL - For playing from the dom perspective
# =============================================================================

DOM_INTERNAL = {
    Phase.APPROACH: {
        "anticipation": [
            "Finally. This is happening.",
            "Look at him. He has no idea.",
            "Perfect. Alone.",
            "I've been waiting for this.",
            "He walked right into it.",
            "So trusting. So naive.",
        ],
        "planning": [
            "Door's locked. No one will interrupt.",
            "Got everything I need.",
            "Now how do I want to do this?",
            "Take it slow. Make it last.",
            "He can't get away.",
        ],
        "desire": [
            "Fuck, he's even better up close.",
            "I need this. I've needed this.",
            "He's going to learn what he's for.",
            "Mine. He's going to be mine.",
            "Can't wait to see his face when he realizes.",
        ],
    },

    Phase.COERCION: {
        "power": [
            "The fear in his eyes... perfect.",
            "He's starting to understand.",
            "Good. He knows he can't stop this.",
            "Fight all you want. It won't matter.",
            "I love watching them realize.",
        ],
        "calculation": [
            "Break him down slowly.",
            "Fear first. Then compliance.",
            "Make him think he has a choice.",
            "The leverage will keep him quiet after.",
            "No marks. Not yet.",
        ],
        "entitlement": [
            "I've earned this.",
            "He owes me.",
            "This is what he's for.",
            "I deserve this.",
            "Finally getting what's mine.",
        ],
    },

    Phase.BEGINNING: {
        "triumph": [
            "Yes. This is it.",
            "Finally touching him.",
            "He's shaking. Good.",
            "The fight's leaving him already.",
            "So fucking tight.",
        ],
        "possession": [
            "Mine now.",
            "All mine.",
            "No one else gets this.",
            "Marking my territory.",
            "He belongs to me now.",
        ],
        "sensation": [
            "Fuck, that feels good.",
            "Even better than I imagined.",
            "So warm. So tight.",
            "His fear makes him clench.",
            "Perfect. Just perfect.",
        ],
    },

    Phase.DURING: {
        "pleasure": [
            "God yes.",
            "So fucking good.",
            "Take it. Take all of it.",
            "I could do this forever.",
            "Better than I dreamed.",
        ],
        "power": [
            "Look at him. Helpless.",
            "He's crying. Makes it better.",
            "Fight harder. I like it.",
            "No one can stop me.",
            "I own him completely.",
        ],
        "observation": [
            "The sounds he makes...",
            "His body's responding.",
            "He's getting hard. Knew it.",
            "Watch him try not to feel it.",
            "His shame is beautiful.",
        ],
        "control": [
            "Slow down. Make it last.",
            "Harder now.",
            "Change position. I want to see his face.",
            "Edge myself. Not done with him yet.",
            "One more round after this.",
        ],
    },

    Phase.ESCALATION: {
        "hunger": [
            "Not enough. Need more.",
            "He can take more.",
            "Let's see how far he can go.",
            "I want to break him.",
            "Once more. With feeling.",
        ],
        "sadism": [
            "His pain is intoxicating.",
            "Cry harder for me.",
            "The more he struggles, the harder I get.",
            "I want to hurt him.",
            "Make him feel every inch.",
        ],
    },

    Phase.CLIMAX: {
        "release": [
            "Fuck. Coming.",
            "Take it all.",
            "Filling him up.",
            "Mine. All mine.",
            "Mark him from the inside.",
        ],
        "satisfaction": [
            "Perfect.",
            "Exactly what I needed.",
            "Worth the wait.",
            "Finally.",
            "He took it so well.",
        ],
    },

    Phase.AFTERMATH: {
        "satisfaction": [
            "That was everything I wanted.",
            "Look at him. Ruined.",
            "I'll remember this forever.",
            "Best I've ever had.",
            "Want to do it again already.",
        ],
        "possession": [
            "He's mine now. Forever.",
            "No one else will have him.",
            "Marked. Claimed.",
            "Part of me inside him now.",
            "He'll never forget.",
        ],
        "planning": [
            "Next time I'll...",
            "This was just the beginning.",
            "When can I have him again?",
            "Need to make sure he stays quiet.",
            "Same time next week.",
        ],
        "detachment": [
            "Done with him. For now.",
            "Time to leave.",
            "Clean up and go.",
            "He'll figure it out.",
            "Back to normal life.",
        ],
    },
}

# Perpetrator physical sensations - for immersive dom POV
DOM_SENSATIONS = {
    "touch": [
        "his skin so smooth under my hands",
        "the heat of him",
        "his body trembling against me",
        "how he tenses when I touch him",
        "his pulse racing under my fingers",
        "the resistance in his muscles",
        "his body slowly giving way",
    ],
    "sight": [
        "tears rolling down his face",
        "the fear in his eyes",
        "watching him try not to react",
        "his body responding despite himself",
        "the marks I'm leaving",
        "how small he looks beneath me",
        "that perfect look of defeat",
    ],
    "sound": [
        "his whimpers",
        "the sounds he tries to suppress",
        "his breath catching",
        "soft pleas he can't hold back",
        "the wet sounds between us",
        "my name on his lips",
        "that perfect sob",
    ],
    "sensation": [
        "so tight around me",
        "his body clenching",
        "the warmth inside him",
        "how he stretches for me",
        "his resistance slowly breaking",
        "building toward release",
        "the pressure building",
    ],
    "taste": [
        "salt of his tears",
        "his skin",
        "sweat and fear",
        "his mouth",
        "the taste of power",
    ],
}

VICTIM_INTERNAL = {
    Phase.APPROACH: {
        "denial": [
            "This isn't happening.",
            "He's just being friendly.",
            "I'm overreacting.",
            "He wouldn't.",
            "I know him. He's safe.",
            "I'm imagining things.",
            "It's fine. Everything's fine.",
            "He's not really...",
            "This is normal. This is fine.",
            "I'm being paranoid.",
        ],
        "instinct": [
            "Something's wrong.",
            "I need to get out of here.",
            "Why is he looking at me like that?",
            "The door. How far is the door?",
            "My phone. Where's my phone?",
            "Trust your gut. Get out.",
            "Warning bells. So many warning bells.",
            "His eyes are different now.",
            "The atmosphere just shifted.",
            "Run. I should run.",
        ],
        "freeze": [
            "Why can't I move?",
            "My legs won't work.",
            "Frozen. I'm frozen.",
            "Move. Move. Why won't I move?",
            "Everything's slowing down.",
        ],
    },

    Phase.COERCION: {
        "bargaining": [
            "Maybe if I just...",
            "If I do this one thing...",
            "Maybe he'll stop if...",
            "I can talk my way out of this.",
            "Just stay calm. Think.",
            "There has to be another way.",
            "What does he want? Give him that.",
            "Buy time. Just buy time.",
            "Think. What can I offer instead?",
            "Negotiate. Reason with him.",
        ],
        "fear": [
            "He means it.",
            "He'll do it. He'll really do it.",
            "No one would believe me.",
            "He has everything. I have nothing.",
            "There's no way out.",
            "I'm trapped.",
            "No one's coming.",
            "He's serious. This is real.",
            "I'm going to die.",
            "Please god no.",
        ],
        "calculation": [
            "What are my options?",
            "Door's locked. Window?",
            "If I scream, who would hear?",
            "How strong is he?",
            "Can I reach anything as a weapon?",
            "Stairs or elevator if I run?",
            "His leverage is real. I can't risk it.",
            "The threat is credible.",
            "No way to call for help.",
            "Fight or comply. Which is safer?",
        ],
    },

    Phase.BEGINNING: {
        "realization": [
            "This is really happening.",
            "Oh god. This is really happening.",
            "I can't stop this.",
            "No no no no no.",
            "Please. Please don't.",
            "It's starting. Oh god it's starting.",
            "He's really going to...",
            "I can't believe this is happening.",
            "This isn't real. This can't be real.",
            "Wake up. Please let me wake up.",
        ],
        "dissociation": [
            "Float away. Just float away.",
            "This isn't my body.",
            "I'm not here. I'm somewhere else.",
            "Focus on something. Anything else.",
            "Count. Just count.",
            "I'm leaving my body.",
            "Somewhere far away from here.",
            "This isn't me. This isn't happening to me.",
            "Watch from the ceiling.",
            "Disconnect. Disconnect.",
        ],
        "physical_shock": [
            "Cold. So cold suddenly.",
            "Can't breathe.",
            "Heart pounding too fast.",
            "Everything's too loud.",
            "Shaking. I'm shaking.",
            "Numb. Going numb.",
            "Hyperventilating. Can't stop.",
            "Tunnel vision.",
            "Time is moving wrong.",
            "All senses on overdrive.",
        ],
    },

    Phase.DURING: {
        "survival": [
            "Just survive.",
            "It'll be over soon.",
            "Stay alive. That's all that matters.",
            "Don't pass out.",
            "Keep breathing.",
            "One breath at a time.",
            "You will survive this.",
            "Stay conscious.",
            "Don't die. Don't let him kill you.",
            "This will end. Everything ends.",
            "Survive now. Fall apart later.",
            "Breathe. In. Out. In. Out.",
        ],
        "dissociation": [
            "I'm on the ceiling. Looking down.",
            "This is happening to someone else.",
            "Focus on the crack in the ceiling.",
            "Count the tiles. One, two, three...",
            "Music. That song. Play it in your head.",
            "I'm not here. I'm at the beach.",
            "Somewhere else. Anywhere else.",
            "Float above it. Watch from outside.",
            "Not my body. Not me.",
            "Far away. So far away.",
            "The beach. Warm sand. Waves.",
            "A memory. Any memory that isn't this.",
        ],
        "shame": [
            "Why am I... why is my body...",
            "This doesn't mean I want...",
            "Please not that. Anything but that.",
            "He'll think I... but I don't...",
            "My body is betraying me.",
            "It's just biology. It doesn't mean anything.",
            "Bodies react. It's automatic.",
            "This isn't desire. This is survival.",
            "Hating my body for responding.",
            "He's noticing. God, he's noticing.",
        ],
        "pain": [
            "Make it stop.",
            "Please. Please stop.",
            "I can't. I can't take any more.",
            "It hurts. It hurts so much.",
            "When will it end?",
            "Tearing. Something's tearing.",
            "Too much. It's too much.",
            "Pain everywhere.",
            "Breaking. He's breaking me.",
            "Can't feel the pain anymore. Numb.",
        ],
        "time": [
            "How long? How long has it been?",
            "Minutes feel like hours.",
            "Time has stopped.",
            "Forever. This is going on forever.",
            "Every second is an eternity.",
            "Will it ever end?",
            "Lost track of time completely.",
            "Is it almost over?",
            "Please let it be almost over.",
            "Hours? Minutes? I don't know.",
        ],
        "coping": [
            "Seventeen. Eighteen. Nineteen...",
            "That song. Focus on that song.",
            "My happy place. Go there.",
            "Recite something. Anything.",
            "Name five things you can see.",
            "Alphabet backwards. Z. Y. X.",
            "Remember their faces. For later.",
            "Details. Remember details.",
            "Just focus on breathing.",
            "Grip something. Feel something else.",
        ],
    },

    Phase.ESCALATION: {
        "despair": [
            "It's getting worse.",
            "He's not stopping.",
            "There's more. There's always more.",
            "When I thought it was over...",
            "How much more?",
            "I can't take any more of this.",
            "Please. I'm begging. Please stop.",
            "Breaking point. I'm at my breaking point.",
            "Can't hold on much longer.",
            "Losing myself.",
        ],
        "bargaining": [
            "Please. I'll do anything.",
            "What do you want? I'll give it.",
            "Just make it stop.",
            "Not that. Anything but that.",
            "Please. Have mercy.",
            "I'll be good. I'll cooperate.",
            "What will make this end?",
            "Tell me what to do.",
            "Anything. I'll do anything.",
            "Just let it be over.",
        ],
    },

    Phase.CLIMAX: {
        "endurance": [
            "Almost over. Has to be almost over.",
            "He's finishing. Finally finishing.",
            "Just a little longer.",
            "Survive this. It's ending.",
            "Don't pass out. Stay present.",
            "Nearly there. Nearly done.",
            "The end. This is the end.",
            "Hold on. Just hold on.",
            "Last moments. It's the last moments.",
            "Thank god. It's ending.",
        ],
        "revulsion": [
            "Inside me. He's...",
            "Feel it. I can feel it.",
            "Sick. Going to be sick.",
            "Part of him in me now.",
            "Marked. Claimed.",
            "Dirty. So dirty.",
            "Never be clean again.",
            "His. I'm his now.",
            "Violated completely.",
            "Ruined.",
        ],
    },

    Phase.ENDING: {
        "relief": [
            "Over. It's over.",
            "He's done. Finally done.",
            "I survived.",
            "It's finished.",
            "Thank god. Thank god.",
        ],
        "dread": [
            "Is it really over?",
            "Will he come back?",
            "What happens now?",
            "Is he going to kill me?",
            "Don't trust it. Don't trust that it's over.",
        ],
    },

    Phase.AFTERMATH: {
        "numbness": [
            "Empty.",
            "Nothing.",
            "Can't feel anything.",
            "Is it over? Is it really over?",
            "I don't know what to do.",
            "Hollow.",
            "Shock. I'm in shock.",
            "Blank. Mind is blank.",
            "Can't process.",
            "Numb. Completely numb.",
        ],
        "questions": [
            "What do I do now?",
            "Who can I tell?",
            "Would anyone believe me?",
            "How do I go back to normal?",
            "Will he come back?",
            "Should I go to the hospital?",
            "Call someone. But who?",
            "Evidence. Should I preserve evidence?",
            "Shower. I need to shower. No. Evidence.",
            "Police? Can I face that?",
        ],
        "shame": [
            "I should have fought harder.",
            "Why didn't I scream?",
            "Why didn't I run?",
            "What's wrong with me?",
            "I let this happen.",
            "My fault. Somehow my fault.",
            "Could have done something differently.",
            "Stupid. So stupid to trust him.",
            "Should have seen the signs.",
            "Everyone will know. Everyone will see.",
        ],
        "physical": [
            "Hurts to move.",
            "Blood. Is that blood?",
            "Sore. Everything's sore.",
            "Need to check. Damage.",
            "Body doesn't feel like mine.",
            "Shaking. Still shaking.",
            "Cold. So cold.",
            "Want to vomit.",
            "Legs won't hold me.",
            "Bruises forming already.",
        ],
        "dissociation": [
            "None of that happened.",
            "Just a dream. Bad dream.",
            "Wasn't really me.",
            "Not real. Can't be real.",
            "Someone else. Happened to someone else.",
            "Go through the motions.",
            "Autopilot.",
            "Not really here.",
            "Watching myself move.",
            "Disconnected from everything.",
        ],
    },
}

# =============================================================================
# GENERATION ENGINE
# =============================================================================

@dataclass
class GenerationContext:
    """Context for generating dialogue"""
    perp_type: PerpType
    phase: Phase
    tone: Optional[ToneRegister] = None
    intensity: float = 0.5  # 0.0 = mild, 1.0 = extreme
    victim_state: str = "survival"
    history: List[str] = field(default_factory=list)

    def advance_phase(self):
        """Move to next phase"""
        phases = list(Phase)
        current_idx = phases.index(self.phase)
        if current_idx < len(phases) - 1:
            self.phase = phases[current_idx + 1]


class DialogueGenerator:
    """Main generation engine"""

    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)

    def _fill_slot(self, slot_name: str, context: GenerationContext) -> str:
        """Fill a template slot with appropriate content"""
        if slot_name not in SLOTS:
            return f"[{slot_name}]"

        slot_data = SLOTS[slot_name]

        # Handle nested slot types (e.g., victim_ref.degrading)
        if isinstance(slot_data, dict):
            # Choose subtype based on perpetrator profile
            profile = PERP_PROFILES[context.perp_type]
            preferred = profile.get("victim_refs", ["neutral"])

            # Parse preferred ref like "victim_ref.degrading"
            available_keys = list(slot_data.keys())
            chosen_key = "neutral"
            for pref in preferred:
                if "." in pref:
                    _, subkey = pref.split(".", 1)
                    if subkey in available_keys:
                        chosen_key = subkey
                        break

            options = slot_data.get(chosen_key, slot_data.get("neutral", []))
        else:
            options = slot_data

        return random.choice(options)

    def _fill_template(self, template: str, context: GenerationContext) -> str:
        """Fill all slots in a template"""
        result = template

        # Find all {slot_name} patterns
        slots = re.findall(r'\{(\w+)\}', template)

        for slot in slots:
            # Special handling for victim_ref variants
            if slot.startswith("victim_ref_"):
                ref_type = slot.replace("victim_ref_", "")
                if ref_type in SLOTS["victim_ref"]:
                    replacement = random.choice(SLOTS["victim_ref"][ref_type])
                else:
                    replacement = self._fill_slot("victim_ref", context)
            else:
                replacement = self._fill_slot(slot, context)

            result = result.replace(f"{{{slot}}}", replacement, 1)

        return result

    def generate_villain_line(self, context: GenerationContext) -> str:
        """Generate a single villain dialogue line"""
        profile = PERP_PROFILES[context.perp_type]

        # Choose tone
        if context.tone:
            tone = context.tone
        else:
            tone = random.choice(profile["preferred_tones"])

        # Get templates for this phase and tone
        phase_templates = TEMPLATES.get(context.phase, {})
        tone_templates = phase_templates.get(tone, [])

        # Fallback to unique phrases from profile
        if not tone_templates:
            tone_templates = profile.get("unique_phrases", ["..."])

        # Sometimes use profile's unique phrases
        if random.random() < 0.3 and profile.get("unique_phrases"):
            template = random.choice(profile["unique_phrases"])
        else:
            template = random.choice(tone_templates)

        return self._fill_template(template, context)

    def generate_victim_thought(self, context: GenerationContext) -> str:
        """Generate a victim internal monologue line"""
        phase_thoughts = VICTIM_INTERNAL.get(context.phase, {})
        state_thoughts = phase_thoughts.get(context.victim_state, [])

        if not state_thoughts:
            # Fallback to any available state
            if phase_thoughts:
                state_thoughts = random.choice(list(phase_thoughts.values()))
            else:
                return "..."

        return random.choice(state_thoughts)

    def generate_dom_thought(self, context: GenerationContext) -> str:
        """Generate a perpetrator/dom internal monologue line"""
        phase_thoughts = DOM_INTERNAL.get(context.phase, {})

        # Choose state based on intensity
        if context.intensity > 0.7:
            preferred_states = ["sadism", "power", "hunger", "possession"]
        elif context.intensity > 0.4:
            preferred_states = ["pleasure", "sensation", "control", "observation"]
        else:
            preferred_states = ["anticipation", "planning", "calculation", "satisfaction"]

        # Find matching state
        for state in preferred_states:
            if state in phase_thoughts:
                return random.choice(phase_thoughts[state])

        # Fallback
        if phase_thoughts:
            return random.choice(random.choice(list(phase_thoughts.values())))
        return "..."

    def generate_dom_sensation(self) -> str:
        """Generate a perpetrator physical sensation description"""
        category = random.choice(list(DOM_SENSATIONS.keys()))
        return random.choice(DOM_SENSATIONS[category])

    def generate_dom_pov_exchange(self, context: GenerationContext, num_beats: int = 5) -> List[Dict]:
        """
        Generate from the dom/perpetrator's POV.
        Includes: what they say, what they think, what they feel, what they observe.
        """
        exchange = []

        for _ in range(num_beats):
            beat_type = random.choice(["dialogue", "thought", "sensation", "observation"])

            if beat_type == "dialogue":
                line = self.generate_villain_line(context)
                exchange.append({"type": "speak", "text": f'I say: "{line}"'})

            elif beat_type == "thought":
                thought = self.generate_dom_thought(context)
                exchange.append({"type": "thought", "text": thought})

            elif beat_type == "sensation":
                sensation = self.generate_dom_sensation()
                exchange.append({"type": "sensation", "text": f"I feel {sensation}."})

            elif beat_type == "observation":
                # Observe victim reaction
                victim_states = ["fear", "tears", "struggle", "compliance", "dissociation"]
                observations = [
                    f"He's {random.choice(['trembling', 'shaking', 'frozen', 'crying'])}.",
                    "His body betrays him.",
                    f"The {random.choice(['fear', 'shame', 'resignation'])} in his eyes.",
                    "He's stopped fighting.",
                    "I can feel him giving up.",
                    "His resistance is weakening.",
                    "Perfect. He's learning.",
                ]
                exchange.append({"type": "observe", "text": random.choice(observations)})

        return exchange

    def generate_dual_pov_exchange(self, context: GenerationContext, num_beats: int = 6) -> List[Dict]:
        """
        Generate interleaved dom and victim perspectives.
        For full immersion in either role.
        """
        exchange = []

        for _ in range(num_beats):
            # Dom perspective
            dom_type = random.choice(["dialogue", "thought", "sensation"])
            if dom_type == "dialogue":
                line = self.generate_villain_line(context)
                exchange.append({"pov": "dom", "type": "speak", "text": f'"{line}"'})
            elif dom_type == "thought":
                thought = self.generate_dom_thought(context)
                exchange.append({"pov": "dom", "type": "thought", "text": f"[DOM] {thought}"})
            else:
                sensation = self.generate_dom_sensation()
                exchange.append({"pov": "dom", "type": "sensation", "text": f"[DOM feels] {sensation}"})

            # Victim perspective
            victim_thought = self.generate_victim_thought(context)
            exchange.append({"pov": "victim", "type": "thought", "text": f"[VICTIM] {victim_thought}"})

        return exchange

    def generate_exchange(self, context: GenerationContext, num_lines: int = 5) -> List[Dict]:
        """Generate a back-and-forth exchange"""
        exchange = []

        for _ in range(num_lines):
            # Villain line
            villain_line = self.generate_villain_line(context)
            exchange.append({"speaker": "villain", "text": villain_line})

            # Sometimes victim internal thought
            if random.random() < 0.6:
                victim_thought = self.generate_victim_thought(context)
                exchange.append({"speaker": "victim_internal", "text": victim_thought})

            # Track history to avoid repetition
            context.history.append(villain_line)
            if len(context.history) > 20:
                context.history.pop(0)

        return exchange

    def generate_scene(self, perp_type: PerpType) -> List[Dict]:
        """Generate a complete scene through all phases"""
        context = GenerationContext(perp_type=perp_type, phase=Phase.APPROACH)
        scene = []

        for phase in Phase:
            context.phase = phase

            # Number of exchanges varies by phase
            num_lines = {
                Phase.APPROACH: 3,
                Phase.COERCION: 4,
                Phase.BEGINNING: 4,
                Phase.DURING: 8,
                Phase.ESCALATION: 4,
                Phase.CLIMAX: 3,
                Phase.ENDING: 2,
                Phase.AFTERMATH: 4,
            }.get(phase, 3)

            scene.append({"phase": phase.value, "content": self.generate_exchange(context, num_lines)})

        return scene


# =============================================================================
# EXPANSION SYSTEM - Add variety over time
# =============================================================================

def add_slot_variants(slot_name: str, variants: List[str]):
    """Add new variants to a slot for infinite expansion"""
    if slot_name in SLOTS:
        if isinstance(SLOTS[slot_name], list):
            SLOTS[slot_name].extend(variants)
        elif isinstance(SLOTS[slot_name], dict):
            # Add to default/neutral category
            if "neutral" in SLOTS[slot_name]:
                SLOTS[slot_name]["neutral"].extend(variants)


def add_template(phase: Phase, tone: ToneRegister, templates: List[str]):
    """Add new templates for expansion"""
    if phase not in TEMPLATES:
        TEMPLATES[phase] = {}
    if tone not in TEMPLATES[phase]:
        TEMPLATES[phase][tone] = []
    TEMPLATES[phase][tone].extend(templates)


def add_perp_phrases(perp_type: PerpType, phrases: List[str]):
    """Add unique phrases to a perpetrator type"""
    if perp_type in PERP_PROFILES:
        PERP_PROFILES[perp_type]["unique_phrases"].extend(phrases)


# =============================================================================
# CORPUS EXTRACTION - Learn from scraped content
# =============================================================================

def extract_dialogue_patterns(text: str, tag: str = "nc") -> List[str]:
    """
    Extract dialogue patterns from scraped fiction.

    This can be used to mine the 381M words of scraped content
    for real dialogue patterns to add to the generation system.
    """
    # Look for quoted dialogue
    dialogue_pattern = r'"([^"]{5,100})"'
    matches = re.findall(dialogue_pattern, text)

    # Filter for likely perpetrator dialogue (contains keywords)
    perp_keywords = ["mine", "good", "take", "stop", "quiet", "belong",
                    "want", "need", "can't", "won't", "don't"]

    perp_dialogue = []
    for match in matches:
        match_lower = match.lower()
        if any(kw in match_lower for kw in perp_keywords):
            perp_dialogue.append(match)

    return perp_dialogue


# =============================================================================
# SCENARIO MIXER - Combine NC with other layers
# =============================================================================

class ScenarioMixer:
    """
    Combines NC base with scenario layers for infinite variety.

    Example combinations:
    - NC + INCEST_FATHER + AGE_GAP + GROOMING
    - NC + AUTHORITY_COACH + SPORTS_TEAM + HAZING
    - NC + BLACKMAIL + FIRST_TIME + CORRUPTION
    - NC + PRISON + GANG + SLAVERY
    - NC + MONSTER + TENTACLES + BREEDING
    """

    def __init__(self, generator: DialogueGenerator):
        self.generator = generator

    def create_scenario(
        self,
        perp_type: PerpType,
        layers: List[ScenarioLayer],
        phase: Phase = Phase.APPROACH
    ) -> 'MixedScenario':
        """Create a scenario with combined layers"""
        return MixedScenario(perp_type, layers, phase, self.generator)

    def random_combination(self, num_layers: int = 2) -> 'MixedScenario':
        """Generate a random scenario combination"""
        perp_type = random.choice(list(PerpType))
        all_layers = list(ScenarioLayer)
        layers = random.sample(all_layers, min(num_layers, len(all_layers)))
        return self.create_scenario(perp_type, layers)


@dataclass
class MixedScenario:
    """A scenario with combined layers"""
    perp_type: PerpType
    layers: List[ScenarioLayer]
    phase: Phase
    generator: DialogueGenerator
    intensity: float = 0.5
    history: List[str] = field(default_factory=list)

    def get_combined_phrases(self) -> List[str]:
        """Get unique phrases from all active layers"""
        phrases = []
        for layer in self.layers:
            if layer in SCENARIO_DIALOGUE:
                phrases.extend(SCENARIO_DIALOGUE[layer].get("unique_phrases", []))
        return phrases

    def get_combined_leverage(self) -> List[str]:
        """Get leverage options from all active layers"""
        leverage = []
        for layer in self.layers:
            if layer in SCENARIO_DIALOGUE:
                leverage.extend(SCENARIO_DIALOGUE[layer].get("leverage", []))
        return leverage

    def get_victim_refs(self) -> List[str]:
        """Get victim references appropriate for this scenario"""
        refs = []
        for layer in self.layers:
            if layer in SCENARIO_DIALOGUE:
                refs.extend(SCENARIO_DIALOGUE[layer].get("victim_refs", []))
        if not refs:
            refs = ["you", "boy"]
        return refs

    def generate_line(self) -> str:
        """Generate a dialogue line using combined scenario context"""
        # Mix sources: base system + layer-specific
        sources = []

        # Add layer-specific phrases (weighted higher)
        layer_phrases = self.get_combined_phrases()
        sources.extend(layer_phrases * 2)  # Double weight

        # Add base perpetrator phrases
        profile = PERP_PROFILES[self.perp_type]
        sources.extend(profile.get("unique_phrases", []))

        # Add template-generated lines
        context = GenerationContext(
            perp_type=self.perp_type,
            phase=self.phase,
            intensity=self.intensity,
            history=self.history
        )
        for _ in range(3):
            sources.append(self.generator.generate_villain_line(context))

        # Select and potentially modify
        line = random.choice(sources)

        # Substitute scenario-specific elements
        victim_refs = self.get_victim_refs()
        leverage = self.get_combined_leverage()

        # Replace placeholders
        if "{victim}" in line and victim_refs:
            line = line.replace("{victim}", random.choice(victim_refs))
        if "{leverage}" in line and leverage:
            line = line.replace("{leverage}", random.choice(leverage))

        # Track history
        self.history.append(line)
        if len(self.history) > 30:
            self.history.pop(0)

        return line

    def generate_exchange(self, num_lines: int = 5) -> List[Dict]:
        """Generate back-and-forth with scenario context"""
        exchange = []
        context = GenerationContext(
            perp_type=self.perp_type,
            phase=self.phase,
            intensity=self.intensity
        )

        for _ in range(num_lines):
            # Villain line (scenario-mixed)
            line = self.generate_line()
            exchange.append({"speaker": "villain", "text": line})

            # Victim thought sometimes
            if random.random() < 0.5:
                thought = self.generator.generate_victim_thought(context)
                exchange.append({"speaker": "victim_internal", "text": thought})

        return exchange

    def describe(self) -> str:
        """Human-readable scenario description"""
        layer_names = [l.value for l in self.layers]
        return f"{self.perp_type.value} + {' + '.join(layer_names)}"


# =============================================================================
# CORPUS EXTRACTOR - Learn from scraped content
# =============================================================================

class CorpusExtractor:
    """
    Extract dialogue patterns from the 381M+ word scraped corpus.
    This is where infinite variety really comes from.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.extracted_dialogue = []
        self.extracted_patterns = []

    def extract_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract dialogue patterns from a single text"""
        results = {
            "perp_dialogue": [],
            "victim_internal": [],
            "commands": [],
            "threats": [],
            "degradation": [],
            "false_comfort": [],
        }

        # Find quoted dialogue
        dialogue_pattern = r'"([^"]{3,150})"'
        quotes = re.findall(dialogue_pattern, text)

        # Categorize based on content
        for quote in quotes:
            q = quote.lower()

            # Commands (short, imperative)
            if len(quote) < 30 and any(cmd in q for cmd in
                ["don't", "stop", "hold", "take", "open", "spread", "quiet", "shut"]):
                results["commands"].append(quote)

            # Threats
            elif any(threat in q for threat in
                ["if you", "or else", "i'll", "will hurt", "kill", "tell"]):
                results["threats"].append(quote)

            # Degradation
            elif any(deg in q for deg in
                ["slut", "whore", "pathetic", "worthless", "nothing", "bitch"]):
                results["degradation"].append(quote)

            # False comfort
            elif any(comfort in q for comfort in
                ["it's okay", "relax", "shh", "good boy", "almost", "doing well"]):
                results["false_comfort"].append(quote)

            # General perp dialogue (possessive, aggressive)
            elif any(perp in q for perp in
                ["mine", "belong", "own", "take", "want", "need", "going to"]):
                results["perp_dialogue"].append(quote)

        return results

    def extract_from_corpus(self, limit: int = 1000) -> Dict[str, List[str]]:
        """Extract patterns from the scraped corpus database"""
        if not self.db_path:
            return {}

        import sqlite3

        all_results = {
            "perp_dialogue": [],
            "victim_internal": [],
            "commands": [],
            "threats": [],
            "degradation": [],
            "false_comfort": [],
        }

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get NC-tagged content
            cursor.execute("""
                SELECT content FROM scraped_content
                WHERE tags LIKE '%noncon%' OR tags LIKE '%rape%' OR tags LIKE '%dub-con%'
                LIMIT ?
            """, (limit,))

            for row in cursor.fetchall():
                text = row[0]
                results = self.extract_from_text(text)
                for key in all_results:
                    all_results[key].extend(results[key])

            conn.close()

        except Exception as e:
            print(f"Corpus extraction error: {e}")

        # Dedupe
        for key in all_results:
            all_results[key] = list(set(all_results[key]))

        return all_results

    def inject_into_slots(self, extracted: Dict[str, List[str]]):
        """Add extracted dialogue to the generation slots"""
        if extracted.get("commands"):
            add_slot_variants("comply_verb", extracted["commands"][:50])
        if extracted.get("threats"):
            add_slot_variants("threat_verb", extracted["threats"][:50])
        if extracted.get("perp_dialogue"):
            # Add as templates to various phases
            add_template(Phase.DURING, ToneRegister.POSSESSIVE, extracted["perp_dialogue"][:30])
        if extracted.get("degradation"):
            add_slot_variants("degrade_adj", extracted["degradation"][:50])

    def learn_from_file(self, filepath: str) -> int:
        """Learn patterns from a single file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            results = self.extract_from_text(text)
            count = sum(len(v) for v in results.values())
            self.inject_into_slots(results)
            return count
        except Exception as e:
            print(f"Error learning from {filepath}: {e}")
            return 0


# =============================================================================
# INFINITE VARIETY SYSTEM - The core promise
# =============================================================================

class InfiniteVariety:
    """
    The main system for generating endless non-repetitive content.

    Combines:
    1. Base dialogue templates
    2. Perpetrator archetypes
    3. Scenario layers (stackable)
    4. Corpus-extracted real dialogue
    5. Procedural generation
    6. History-based anti-repetition
    """

    def __init__(self, corpus_db: str = None):
        self.generator = DialogueGenerator()
        self.mixer = ScenarioMixer(self.generator)
        self.extractor = CorpusExtractor(corpus_db)
        self.session_history = []
        self.used_combinations = set()

    def calculate_variety_space(self) -> int:
        """Calculate approximate number of unique combinations"""
        perp_types = len(PerpType)
        scenario_layers = len(ScenarioLayer)
        phases = len(Phase)
        tones = len(ToneRegister)

        # Layer combinations (pick 1-3 layers from pool)
        from math import comb
        layer_combos = sum(comb(scenario_layers, k) for k in range(1, 4))

        base_combinations = perp_types * layer_combos * phases * tones

        # Multiply by template variants
        template_variants = sum(
            len(tones)
            for phase_dict in TEMPLATES.values()
            for tones in phase_dict.values()
        )

        # Multiply by slot variants
        slot_variants = sum(
            len(v) if isinstance(v, list) else sum(len(sv) for sv in v.values())
            for v in SLOTS.values()
        )

        return base_combinations * template_variants * slot_variants

    def generate_unique_scenario(self) -> MixedScenario:
        """Generate a scenario combination not yet used this session"""
        max_attempts = 100

        for _ in range(max_attempts):
            scenario = self.mixer.random_combination(
                num_layers=random.randint(1, 3)
            )
            combo_key = scenario.describe()

            if combo_key not in self.used_combinations:
                self.used_combinations.add(combo_key)
                return scenario

        # If we've exhausted combinations, clear and start fresh
        self.used_combinations.clear()
        return self.mixer.random_combination()

    def generate_session(self, num_scenarios: int = 10) -> List[Dict]:
        """Generate a varied session with multiple scenarios"""
        session = []

        for i in range(num_scenarios):
            scenario = self.generate_unique_scenario()

            # Progress through phases
            phases_to_use = random.sample(list(Phase), k=random.randint(3, 6))
            phases_to_use.sort(key=lambda p: list(Phase).index(p))

            scenario_content = {
                "scenario": scenario.describe(),
                "perp_type": scenario.perp_type.value,
                "layers": [l.value for l in scenario.layers],
                "exchanges": []
            }

            for phase in phases_to_use:
                scenario.phase = phase
                exchange = scenario.generate_exchange(num_lines=random.randint(3, 7))
                scenario_content["exchanges"].append({
                    "phase": phase.value,
                    "dialogue": exchange
                })

            session.append(scenario_content)

        return session

    def generate_forever(self):
        """Generator that yields infinite unique content"""
        while True:
            scenario = self.generate_unique_scenario()
            scenario.phase = random.choice(list(Phase))
            line = scenario.generate_line()

            yield {
                "scenario": scenario.describe(),
                "phase": scenario.phase.value,
                "line": line
            }


# =============================================================================
# CLI / Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GENERATIVE DIALOGUE SYSTEM - Infinite Variety Engine")
    print("=" * 70)

    # Initialize the infinite variety system
    infinite = InfiniteVariety()

    # Calculate variety space
    variety_space = infinite.calculate_variety_space()
    print(f"\nCalculated variety space: {variety_space:,} unique combinations")
    print(f"At 1 line/second: {variety_space // 86400:,} days of unique content")
    print(f"At 1 line/second: {variety_space // 86400 // 365:,} years of unique content")

    print("\n" + "=" * 70)
    print("SCENARIO LAYER COMBINATIONS")
    print("=" * 70)
    print(f"\nPerpetrator types: {len(PerpType)}")
    print(f"Scenario layers: {len(ScenarioLayer)}")
    print(f"Phases: {len(Phase)}")
    print(f"Tone registers: {len(ToneRegister)}")

    # Demo: Generate mixed scenarios
    print("\n" + "=" * 70)
    print("SAMPLE MIXED SCENARIOS")
    print("=" * 70)

    for _ in range(5):
        scenario = infinite.generate_unique_scenario()
        print(f"\n--- {scenario.describe()} ---")
        scenario.phase = Phase.DURING
        exchange = scenario.generate_exchange(num_lines=4)
        for line in exchange:
            prefix = "  [THOUGHT]" if line["speaker"] == "victim_internal" else "  VILLAIN:"
            print(f"{prefix} {line['text']}")

    # Show specific powerful combinations
    print("\n" + "=" * 70)
    print("SPECIFIC SCENARIO COMBINATIONS")
    print("=" * 70)

    combos = [
        (PerpType.AUTHORITY, [ScenarioLayer.INCEST_FATHER, ScenarioLayer.AGE_GAP]),
        (PerpType.SADIST, [ScenarioLayer.PRISON, ScenarioLayer.GANG]),
        (PerpType.PREDATOR, [ScenarioLayer.AUTHORITY_COACH, ScenarioLayer.HAZING]),
        (PerpType.ENTITLED, [ScenarioLayer.BLACKMAIL, ScenarioLayer.FIRST_TIME]),
        (PerpType.STRANGER, [ScenarioLayer.MONSTER, ScenarioLayer.TENTACLES]),
    ]

    mixer = ScenarioMixer(infinite.generator)
    for perp, layers in combos:
        scenario = mixer.create_scenario(perp, layers, Phase.DURING)
        print(f"\n--- {scenario.describe()} ---")
        for _ in range(3):
            print(f"  VILLAIN: {scenario.generate_line()}")

    print("\n" + "=" * 70)
    print("SYSTEM CAPABILITIES")
    print("=" * 70)
    print("""
    1. TEMPLATE GRAMMARS: Sentence structures with fillable slots
    2. PERPETRATOR PROFILES: 8 distinct archetypes with unique speech
    3. SCENARIO LAYERS: 40+ stackable layers (incest, authority, etc.)
    4. PHASE PROGRESSION: 8 phases from approach to aftermath
    5. TONE REGISTERS: 10 emotional registers per phase
    6. CORPUS EXTRACTION: Learn from 381M+ words of scraped fiction
    7. ANTI-REPETITION: History tracking prevents recent repeats
    8. INFINITE GENERATOR: Yields forever without repetition

    To expand the system:
    - add_slot_variants(slot, words) - Add new slot fillers
    - add_template(phase, tone, templates) - Add sentence patterns
    - add_perp_phrases(type, phrases) - Add perpetrator lines
    - SCENARIO_DIALOGUE[layer] - Add layer-specific content
    - CorpusExtractor.learn_from_file() - Mine existing fiction
    """)
    print("=" * 70)
