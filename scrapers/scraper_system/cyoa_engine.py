#!/usr/bin/env python3
"""
CYOA Engine - Choose Your Own Adventure Framework for NC Scenarios

This provides the branching narrative structure where:
- Every choice leads somewhere
- NC is inevitable but varies by path
- Choices affect perpetrator type, intensity, duration, scenario layers
- Can play from victim OR dom perspective

The goal: Endless replayability where no two playthroughs feel the same.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple
from enum import Enum

# Import from generative system (relative import for package, fallback for direct run)
try:
    from .generative_dialogue_system import (
        ScenarioLayer, PerpType, Phase, ToneRegister,
        DialogueGenerator, GenerationContext, ScenarioMixer, MixedScenario,
        SCENARIO_DIALOGUE, DOM_INTERNAL, VICTIM_INTERNAL
    )
except ImportError:
    from generative_dialogue_system import (
        ScenarioLayer, PerpType, Phase, ToneRegister,
        DialogueGenerator, GenerationContext, ScenarioMixer, MixedScenario,
        SCENARIO_DIALOGUE, DOM_INTERNAL, VICTIM_INTERNAL
    )


class ChoiceType(Enum):
    """Types of choices the player can make"""
    LOCATION = "location"           # Where to go
    ACTION = "action"               # What to do
    RESPONSE = "response"           # How to react
    DIALOGUE = "dialogue"           # What to say
    RESISTANCE = "resistance"       # Fight/comply spectrum
    MENTAL = "mental"               # Internal coping choice
    ESCAPE = "escape"               # Attempt to escape


class Perspective(Enum):
    """Whose POV are we playing from"""
    VICTIM = "victim"
    PERPETRATOR = "dom"


@dataclass
class Choice:
    """A single choice the player can make"""
    id: str
    text: str
    choice_type: ChoiceType
    # What this choice leads to
    leads_to: Optional[str] = None  # Node ID
    # How this choice modifies the scenario
    adds_layers: List[ScenarioLayer] = field(default_factory=list)
    changes_perp: Optional[PerpType] = None
    intensity_modifier: float = 0.0  # -1.0 to +1.0
    # Conditions for this choice to appear
    requires_layers: List[ScenarioLayer] = field(default_factory=list)
    excludes_layers: List[ScenarioLayer] = field(default_factory=list)
    # Flavor text for consequences
    consequence_hint: str = ""
    # Is this an ending choice?
    is_ending: bool = False


@dataclass
class SceneNode:
    """A node in the CYOA tree - represents a moment/scene"""
    id: str
    title: str
    description: str
    phase: Phase
    # What choices are available here
    choices: List[Choice] = field(default_factory=list)
    # Scene generation parameters
    num_dialogue_lines: int = 4
    # Special flags
    is_ending: bool = False
    is_checkpoint: bool = False
    # Content generation
    custom_content: Optional[Callable] = None


@dataclass
class GameState:
    """Current state of a playthrough"""
    perspective: Perspective
    current_node: str
    active_layers: List[ScenarioLayer] = field(default_factory=list)
    perp_type: PerpType = PerpType.STRANGER
    intensity: float = 0.5
    phase: Phase = Phase.APPROACH
    # History
    choices_made: List[str] = field(default_factory=list)
    nodes_visited: List[str] = field(default_factory=list)
    dialogue_history: List[Dict] = field(default_factory=list)
    # Stats
    resistance_score: int = 0
    compliance_score: int = 0
    dissociation_level: float = 0.0
    damage_level: float = 0.0


class CYOAEngine:
    """
    Main engine for running Choose Your Own Adventure scenarios.

    Features:
    - Branching narrative with meaningful choices
    - Procedural scene generation at each node
    - Scenario layer accumulation
    - Multiple endings based on path
    - Play from victim OR perpetrator perspective
    """

    def __init__(self, perspective: Perspective = Perspective.VICTIM):
        self.generator = DialogueGenerator()
        self.mixer = ScenarioMixer(self.generator)
        self.nodes: Dict[str, SceneNode] = {}
        self.state: Optional[GameState] = None

        # Build the default story tree
        self._build_default_tree()

    def _build_default_tree(self):
        """Build the default branching story structure"""

        # =====================================================================
        # OPENING BRANCHES - How it begins
        # =====================================================================

        self.add_node(SceneNode(
            id="start",
            title="The Beginning",
            description="Where does this story begin?",
            phase=Phase.APPROACH,
            choices=[
                Choice(
                    id="start_party",
                    text="At a party",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="party_arrival",
                    adds_layers=[ScenarioLayer.DRUNK],
                    consequence_hint="Alcohol flows freely..."
                ),
                Choice(
                    id="start_work",
                    text="At work, late night",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="office_late",
                    adds_layers=[ScenarioLayer.WORKPLACE_OFFICE],
                    changes_perp=PerpType.AUTHORITY,
                    consequence_hint="Everyone else has gone home..."
                ),
                Choice(
                    id="start_home",
                    text="Home alone",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="home_alone",
                    adds_layers=[ScenarioLayer.HOME_INVASION],
                    changes_perp=PerpType.STRANGER,
                    consequence_hint="You thought you were safe..."
                ),
                Choice(
                    id="start_online",
                    text="Meeting someone from an app",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="online_meet",
                    adds_layers=[ScenarioLayer.CATFISHED],
                    consequence_hint="Are they who they said they were?"
                ),
                Choice(
                    id="start_family",
                    text="Family gathering",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="family_event",
                    adds_layers=[ScenarioLayer.INCEST_UNCLE],
                    changes_perp=PerpType.TRUSTED,
                    consequence_hint="A relative you've always trusted..."
                ),
            ]
        ))

        # =====================================================================
        # PARTY BRANCH
        # =====================================================================

        self.add_node(SceneNode(
            id="party_arrival",
            title="The Party",
            description="Music is loud. Drinks are flowing. You don't know many people here.",
            phase=Phase.APPROACH,
            choices=[
                Choice(
                    id="party_drink",
                    text="Accept a drink from someone",
                    choice_type=ChoiceType.ACTION,
                    leads_to="party_drugged",
                    adds_layers=[ScenarioLayer.DRUGGED_DRINK],
                    intensity_modifier=0.2,
                    consequence_hint="You didn't see him pour it..."
                ),
                Choice(
                    id="party_quiet",
                    text="Find somewhere quieter",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="party_bedroom",
                    adds_layers=[ScenarioLayer.LURED],
                    consequence_hint="Someone offers to show you a quiet room..."
                ),
                Choice(
                    id="party_leave_alone",
                    text="Leave alone, it's getting late",
                    choice_type=ChoiceType.ACTION,
                    leads_to="party_parking",
                    adds_layers=[ScenarioLayer.PARKING_GARAGE],
                    changes_perp=PerpType.OPPORTUNIST,
                    consequence_hint="The parking lot is dark..."
                ),
                Choice(
                    id="party_friend",
                    text="Go with a 'friend' who offers a ride",
                    choice_type=ChoiceType.ACTION,
                    leads_to="party_ride",
                    adds_layers=[ScenarioLayer.BACKSEAT],
                    changes_perp=PerpType.ENTITLED,
                    consequence_hint="You thought you could trust him..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="party_drugged",
            title="Everything's Fuzzy",
            description="The room is spinning. Your legs don't work right. Someone is helping you walk...",
            phase=Phase.COERCION,
            choices=[
                Choice(
                    id="drugged_comply",
                    text="Let him help you somewhere to sit down",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="drugged_bedroom",
                    intensity_modifier=-0.1,
                    consequence_hint="He's being so helpful..."
                ),
                Choice(
                    id="drugged_resist",
                    text="Try to pull away, find your phone",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="drugged_struggle",
                    intensity_modifier=0.2,
                    consequence_hint="Your body won't cooperate..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="drugged_bedroom",
            title="The Bedroom",
            description="He's laid you on a bed. The door clicks shut. Locked.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="bedroom_beg",
                    text="Beg him to stop",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="assault_beginning",
                    intensity_modifier=0.1,
                    consequence_hint="Your words are slurred..."
                ),
                Choice(
                    id="bedroom_silent",
                    text="Stay silent, try to focus through the fog",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.1,
                    consequence_hint="Maybe if you don't react..."
                ),
            ]
        ))

        # =====================================================================
        # HOME INVASION BRANCH
        # =====================================================================

        self.add_node(SceneNode(
            id="home_alone",
            title="Home",
            description="Quiet evening. You're scrolling through your phone when you hear the back door.",
            phase=Phase.APPROACH,
            choices=[
                Choice(
                    id="home_investigate",
                    text="Go check the noise",
                    choice_type=ChoiceType.ACTION,
                    leads_to="home_confrontation",
                    consequence_hint="Maybe it was nothing..."
                ),
                Choice(
                    id="home_hide",
                    text="Hide and call for help",
                    choice_type=ChoiceType.ACTION,
                    leads_to="home_found",
                    adds_layers=[ScenarioLayer.STALKER],
                    consequence_hint="He knows where you hide..."
                ),
                Choice(
                    id="home_run",
                    text="Run for the front door",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="home_caught_running",
                    intensity_modifier=0.3,
                    consequence_hint="He's faster..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="home_confrontation",
            title="Face to Face",
            description="He's in your kitchen. Mask. Knife. He sees you before you can run.",
            phase=Phase.COERCION,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="confront_comply",
                    text="Put your hands up, don't resist",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="home_restrained",
                    adds_layers=[ScenarioLayer.RESTRAINED],
                    intensity_modifier=-0.2,
                    consequence_hint="Maybe compliance keeps you alive..."
                ),
                Choice(
                    id="confront_bargain",
                    text="Try to bargain - offer money, anything",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="home_bargain_fail",
                    consequence_hint="He doesn't want money..."
                ),
                Choice(
                    id="confront_fight",
                    text="Grab something and fight",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="home_overpowered",
                    intensity_modifier=0.4,
                    adds_layers=[ScenarioLayer.INJURED],
                    consequence_hint="He's stronger than you..."
                ),
            ]
        ))

        # =====================================================================
        # WORKPLACE BRANCH
        # =====================================================================

        self.add_node(SceneNode(
            id="office_late",
            title="Working Late",
            description="The office is empty. Just you and the boss finishing up a project.",
            phase=Phase.APPROACH,
            choices=[
                Choice(
                    id="office_drink",
                    text="Accept when he suggests a drink to celebrate",
                    choice_type=ChoiceType.ACTION,
                    leads_to="office_celebration",
                    adds_layers=[ScenarioLayer.AUTHORITY_BOSS],
                    consequence_hint="One drink can't hurt..."
                ),
                Choice(
                    id="office_leave",
                    text="Decline and say you need to head home",
                    choice_type=ChoiceType.ACTION,
                    leads_to="office_blocked",
                    consequence_hint="He doesn't take no well..."
                ),
                Choice(
                    id="office_conference",
                    text="He asks you to review something in the conference room",
                    choice_type=ChoiceType.ACTION,
                    leads_to="conference_trapped",
                    adds_layers=[ScenarioLayer.BACK_ROOM],
                    consequence_hint="The door locks from inside..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="office_blocked",
            title="Blocked",
            description="He's standing between you and the door. His expression has changed.",
            phase=Phase.COERCION,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="blocked_firm",
                    text="Firmly insist you're leaving",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="office_threatening",
                    adds_layers=[ScenarioLayer.BLACKMAIL],
                    consequence_hint="He mentions your job..."
                ),
                Choice(
                    id="blocked_comply",
                    text="Nervously agree to stay a bit longer",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="office_couch",
                    intensity_modifier=-0.1,
                    consequence_hint="Maybe this will defuse it..."
                ),
            ]
        ))

        # =====================================================================
        # FAMILY BRANCH
        # =====================================================================

        self.add_node(SceneNode(
            id="family_event",
            title="Family Gathering",
            description="Holiday dinner. Your uncle has been drinking. He keeps finding reasons to be near you.",
            phase=Phase.APPROACH,
            choices=[
                Choice(
                    id="family_avoid",
                    text="Try to stay with the group",
                    choice_type=ChoiceType.ACTION,
                    leads_to="family_cornered",
                    consequence_hint="He waits for his moment..."
                ),
                Choice(
                    id="family_escape",
                    text="Go to your old bedroom to 'rest'",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="family_bedroom",
                    adds_layers=[ScenarioLayer.DRUNK],
                    consequence_hint="He knows this house better than you remember..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="family_cornered",
            title="Cornered",
            description="He catches you alone in the kitchen. Everyone else is watching the game.",
            phase=Phase.COERCION,
            choices=[
                Choice(
                    id="cornered_call",
                    text="Try to call out to the others",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="family_silenced",
                    intensity_modifier=0.2,
                    consequence_hint="His hand covers your mouth..."
                ),
                Choice(
                    id="cornered_basement",
                    text="He says he needs help with something in the basement",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="family_basement",
                    adds_layers=[ScenarioLayer.BASEMENT],
                    consequence_hint="No one will hear you down there..."
                ),
            ]
        ))

        # =====================================================================
        # THE ASSAULT - Core scene (multiple paths lead here)
        # =====================================================================

        self.add_node(SceneNode(
            id="assault_beginning",
            title="It Begins",
            description="This is really happening. There's no getting out of this.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=8,
            choices=[
                Choice(
                    id="assault_fight",
                    text="Fight with everything you have",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.3,
                    consequence_hint="It might make it worse..."
                ),
                Choice(
                    id="assault_freeze",
                    text="Freeze - can't move, can't think",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_during_frozen",
                    intensity_modifier=0.0,
                    consequence_hint="Your body makes the choice for you..."
                ),
                Choice(
                    id="assault_dissociate",
                    text="Try to go somewhere else in your mind",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="assault_during_dissociated",
                    intensity_modifier=-0.2,
                    consequence_hint="Float away from your body..."
                ),
                Choice(
                    id="assault_comply",
                    text="Comply to make it end faster",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_during_compliant",
                    intensity_modifier=-0.3,
                    consequence_hint="Just survive..."
                ),
            ]
        ))

        # During assault variations based on victim response
        for response, state in [
            ("fight", "fighting"),
            ("frozen", "frozen"),
            ("dissociated", "dissociation"),
            ("compliant", "survival")
        ]:
            self.add_node(SceneNode(
                id=f"assault_during_{response}",
                title="During",
                description=f"The assault continues. You're {state.replace('_', ' ')}.",
                phase=Phase.DURING,
                num_dialogue_lines=10,
                choices=[
                    Choice(
                        id=f"during_{response}_endure",
                        text="Endure",
                        choice_type=ChoiceType.MENTAL,
                        leads_to="assault_escalation",
                    ),
                    Choice(
                        id=f"during_{response}_change",
                        text="Try a different approach",
                        choice_type=ChoiceType.RESPONSE,
                        leads_to="assault_beginning",  # Loop back for different choice
                    ),
                ]
            ))

        # =====================================================================
        # ESCALATION
        # =====================================================================

        self.add_node(SceneNode(
            id="assault_escalation",
            title="It Gets Worse",
            description="He's not done. It's getting more intense.",
            phase=Phase.ESCALATION,
            num_dialogue_lines=8,
            choices=[
                Choice(
                    id="escalation_beg",
                    text="Beg for it to stop",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="assault_climax",
                    intensity_modifier=0.1,
                    consequence_hint="Your pleas only encourage him..."
                ),
                Choice(
                    id="escalation_numb",
                    text="Go completely numb",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="assault_climax",
                    intensity_modifier=-0.2,
                    consequence_hint="Nothing can hurt you if you feel nothing..."
                ),
                Choice(
                    id="escalation_multiple",
                    text="[BRANCH] Others arrive",
                    choice_type=ChoiceType.ACTION,
                    leads_to="assault_multiple",
                    adds_layers=[ScenarioLayer.GANGBANG],
                    intensity_modifier=0.5,
                    consequence_hint="It wasn't just him..."
                ),
            ]
        ))

        # =====================================================================
        # CLIMAX / ENDING
        # =====================================================================

        self.add_node(SceneNode(
            id="assault_climax",
            title="The End Approaches",
            description="He's finishing. It's almost over.",
            phase=Phase.CLIMAX,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="climax_end",
                    text="Let it end",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="aftermath",
                ),
            ]
        ))

        # =====================================================================
        # AFTERMATH BRANCHES
        # =====================================================================

        self.add_node(SceneNode(
            id="aftermath",
            title="After",
            description="It's over. He's done. What now?",
            phase=Phase.AFTERMATH,
            num_dialogue_lines=4,
            choices=[
                Choice(
                    id="aftermath_escape",
                    text="Run as soon as you can",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="ending_escaped",
                    is_ending=True,
                ),
                Choice(
                    id="aftermath_trapped",
                    text="He's not letting you leave",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="aftermath_kept",
                    adds_layers=[ScenarioLayer.KEPT],
                    consequence_hint="This isn't over..."
                ),
                Choice(
                    id="aftermath_threats",
                    text="He makes threats about telling",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="ending_threatened",
                    adds_layers=[ScenarioLayer.BLACKMAIL],
                    is_ending=True,
                ),
                Choice(
                    id="aftermath_ongoing",
                    text="He says this will happen again",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="ending_ongoing",
                    adds_layers=[ScenarioLayer.ONGOING_ABUSE],
                    consequence_hint="The beginning of something worse..."
                ),
            ]
        ))

        # =====================================================================
        # ENDINGS
        # =====================================================================

        self.add_node(SceneNode(
            id="ending_escaped",
            title="Escaped",
            description="You got away. But you'll never be the same.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="ending_threatened",
            title="Silenced",
            description="His threats ensure your silence. Life goes on. On the surface.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="ending_ongoing",
            title="The New Normal",
            description="This is your life now. He comes when he wants. You survive.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="aftermath_kept",
            title="Kept",
            description="Hours turn to days. You're not going anywhere.",
            phase=Phase.DURING,
            choices=[
                Choice(
                    id="kept_broken",
                    text="Accept your new reality",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="ending_broken",
                    adds_layers=[ScenarioLayer.BROKEN],
                    is_ending=True,
                ),
                Choice(
                    id="kept_escape_attempt",
                    text="Plan an escape",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="kept_escape",
                    adds_layers=[ScenarioLayer.CAPTIVE, ScenarioLayer.KIDNAPPED],
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="ending_broken",
            title="Broken",
            description="You've stopped fighting. Stopped hoping. You're his now.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        # =====================================================================
        # EXTENDED WORKPLACE BRANCH
        # =====================================================================

        self.add_node(SceneNode(
            id="office_celebration",
            title="Celebration",
            description="One drink becomes two. The office feels different now. His hand on your shoulder.",
            phase=Phase.COERCION,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="celebration_excuse",
                    text="Make an excuse to leave",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="office_blocked",
                    consequence_hint="He doesn't let you go that easily..."
                ),
                Choice(
                    id="celebration_more",
                    text="Have another drink",
                    choice_type=ChoiceType.ACTION,
                    leads_to="office_drunk",
                    adds_layers=[ScenarioLayer.DRUNK],
                    intensity_modifier=-0.1,
                    consequence_hint="Your judgment is slipping..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="office_drunk",
            title="Too Many Drinks",
            description="The room is tilting. He's helping you to the couch in his office.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="drunk_resist",
                    text="Try to push him away",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_beginning",
                    intensity_modifier=0.2,
                    consequence_hint="Your limbs won't cooperate..."
                ),
                Choice(
                    id="drunk_confused",
                    text="You're too confused to react",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    adds_layers=[ScenarioLayer.DRUGGED_DRINK],
                    consequence_hint="Was there something in that drink?"
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="office_threatening",
            title="The Threat",
            description="His tone changes. He mentions your performance review. Your job. Your future.",
            phase=Phase.COERCION,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="threat_submit",
                    text="Give in to keep your job",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.2,
                    consequence_hint="What choice do you have?"
                ),
                Choice(
                    id="threat_refuse",
                    text="Refuse and try to leave anyway",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="office_forced",
                    intensity_modifier=0.3,
                    consequence_hint="He doesn't accept no..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="office_forced",
            title="Forced",
            description="He grabs you. Shoves you against the desk. The door is locked.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="forced_fight",
                    text="Fight back",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.3,
                ),
                Choice(
                    id="forced_survive",
                    text="Stop fighting to survive",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_during_compliant",
                    intensity_modifier=-0.2,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="office_couch",
            title="The Couch",
            description="You sit on his office couch. He sits too close. His hand on your thigh.",
            phase=Phase.COERCION,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="couch_move",
                    text="Try to move away",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="office_forced",
                    consequence_hint="He follows..."
                ),
                Choice(
                    id="couch_frozen",
                    text="Freeze, unable to move",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    consequence_hint="He takes your silence as permission..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="conference_trapped",
            title="Conference Room",
            description="The door clicks locked behind you. He's between you and the exit.",
            phase=Phase.COERCION,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="conf_scream",
                    text="Scream for help",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="conf_silenced",
                    intensity_modifier=0.2,
                    consequence_hint="Soundproofed for privacy..."
                ),
                Choice(
                    id="conf_negotiate",
                    text="Try to talk your way out",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="office_threatening",
                    consequence_hint="He's not interested in talking..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="conf_silenced",
            title="Silenced",
            description="His hand clamps over your mouth. No one heard. No one's coming.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="silenced_bite",
                    text="Bite his hand",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.4,
                    adds_layers=[ScenarioLayer.INJURED],
                    consequence_hint="He hits you. Hard."
                ),
                Choice(
                    id="silenced_comply",
                    text="Nod. Stop screaming.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.1,
                ),
            ]
        ))

        # =====================================================================
        # ONLINE DATING BRANCH
        # =====================================================================

        self.add_node(SceneNode(
            id="online_meet",
            title="The Date",
            description="You arrive at the address he sent. It's not a restaurant. It's an apartment.",
            phase=Phase.APPROACH,
            choices=[
                Choice(
                    id="online_enter",
                    text="Go inside - maybe it's a nice dinner at home",
                    choice_type=ChoiceType.ACTION,
                    leads_to="online_trapped",
                    adds_layers=[ScenarioLayer.LURED],
                    consequence_hint="The door locks behind you..."
                ),
                Choice(
                    id="online_wait",
                    text="Text him to come outside",
                    choice_type=ChoiceType.ACTION,
                    leads_to="online_ambush",
                    consequence_hint="He comes out. With friends."
                ),
                Choice(
                    id="online_leave",
                    text="This feels wrong. Leave.",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="online_followed",
                    adds_layers=[ScenarioLayer.STALKER],
                    consequence_hint="He follows you to your car..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="online_trapped",
            title="Trapped",
            description="The apartment is nothing like his pictures. Neither is he. The door is bolted.",
            phase=Phase.COERCION,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="trapped_window",
                    text="Look for another way out",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="online_caught",
                    consequence_hint="Third floor. No fire escape."
                ),
                Choice(
                    id="trapped_phone",
                    text="Try to call for help",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="online_phone_taken",
                    consequence_hint="He takes your phone."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="online_caught",
            title="Caught",
            description="He grabs you from behind before you reach the window.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="caught_struggle",
                    text="Struggle and fight",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.3,
                ),
                Choice(
                    id="caught_limp",
                    text="Go limp. Save your energy.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="online_phone_taken",
            title="Phone Taken",
            description="He smashes your phone. 'No one knows you're here. No one's coming.'",
            phase=Phase.COERCION,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="phone_beg",
                    text="Beg him to let you go",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="assault_beginning",
                    consequence_hint="Your begging excites him..."
                ),
                Choice(
                    id="phone_silent",
                    text="Stay silent. Don't give him anything.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=0.1,
                    consequence_hint="Your defiance angers him..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="online_ambush",
            title="Ambush",
            description="He comes out with two other men. They surround you before you can run.",
            phase=Phase.COERCION,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="ambush_run",
                    text="Try to run",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="ambush_caught",
                    intensity_modifier=0.3,
                    consequence_hint="They're faster..."
                ),
                Choice(
                    id="ambush_comply",
                    text="Go with them quietly",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="ambush_inside",
                    intensity_modifier=-0.1,
                    consequence_hint="Maybe they'll be gentler if you don't fight..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="ambush_caught",
            title="Caught Running",
            description="They tackle you to the ground. Drag you inside.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="drag_fight",
                    text="Keep fighting",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_multiple",
                    adds_layers=[ScenarioLayer.GANGBANG],
                    intensity_modifier=0.4,
                ),
                Choice(
                    id="drag_stop",
                    text="Stop fighting. You're outnumbered.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_multiple",
                    adds_layers=[ScenarioLayer.GANGBANG],
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="ambush_inside",
            title="Inside",
            description="They lead you inside. Lock the door. Circle around you.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="inside_plead",
                    text="Plead with them",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="assault_multiple",
                    adds_layers=[ScenarioLayer.GANGBANG],
                ),
                Choice(
                    id="inside_numb",
                    text="Go numb. Disconnect.",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="assault_multiple",
                    adds_layers=[ScenarioLayer.GANGBANG],
                    intensity_modifier=-0.2,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="assault_multiple",
            title="Multiple",
            description="They take turns. One holds you while another uses you.",
            phase=Phase.DURING,
            num_dialogue_lines=10,
            choices=[
                Choice(
                    id="multiple_endure",
                    text="Endure. Count them. It has to end.",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="assault_climax",
                ),
                Choice(
                    id="multiple_break",
                    text="Break down completely",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="assault_climax",
                    adds_layers=[ScenarioLayer.BROKEN],
                    intensity_modifier=0.2,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="online_followed",
            title="Followed",
            description="You get to your car. He's already there. Leaning against it.",
            phase=Phase.COERCION,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="followed_car",
                    text="Try to get in the car anyway",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="car_trapped",
                    adds_layers=[ScenarioLayer.BACKSEAT],
                ),
                Choice(
                    id="followed_run",
                    text="Run back toward the building",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="chased",
                    intensity_modifier=0.2,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="car_trapped",
            title="Car",
            description="He pushes you into the backseat. Gets in after you. Locks the doors.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="car_fight",
                    text="Fight in the confined space",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.2,
                ),
                Choice(
                    id="car_still",
                    text="Stay still. Nowhere to go.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="chased",
            title="Chased",
            description="He catches you before you reach the door. Drags you into the shadows.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="chased_scream",
                    text="Scream",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="chased_silenced",
                    intensity_modifier=0.3,
                ),
                Choice(
                    id="chased_quiet",
                    text="Stay quiet, hope someone sees",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="chased_silenced",
            title="Silenced",
            description="His hand over your mouth. Knife at your throat. 'One more sound.'",
            phase=Phase.BEGINNING,
            num_dialogue_lines=4,
            choices=[
                Choice(
                    id="knife_comply",
                    text="Stop struggling",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.1,
                ),
                Choice(
                    id="knife_risk",
                    text="Risk it. Bite and run.",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="knife_cut",
                    adds_layers=[ScenarioLayer.INJURED],
                    intensity_modifier=0.5,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="knife_cut",
            title="Cut",
            description="The knife slices your arm as you break free. But he catches you again. Now he's angry.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="cut_submit",
                    text="Submit. You can't win.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.3,
                ),
            ]
        ))

        # =====================================================================
        # EXTENDED HOME INVASION
        # =====================================================================

        self.add_node(SceneNode(
            id="home_found",
            title="Found",
            description="He finds you hiding. 'I've been watching you for weeks. I know all your hiding spots.'",
            phase=Phase.COERCION,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="found_run",
                    text="Try to run past him",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="home_overpowered",
                    intensity_modifier=0.2,
                ),
                Choice(
                    id="found_freeze",
                    text="Frozen in terror",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="home_caught_running",
            title="Caught",
            description="He tackles you at the door. Slams you to the ground.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="tackle_fight",
                    text="Keep fighting",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.3,
                    adds_layers=[ScenarioLayer.INJURED],
                ),
                Choice(
                    id="tackle_stop",
                    text="Stop fighting",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="home_bargain_fail",
            title="Bargaining",
            description="'I don't want your money.' He steps closer. 'I want something else.'",
            phase=Phase.COERCION,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="bargain_offer",
                    text="Offer to cooperate if he doesn't hurt you",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.2,
                ),
                Choice(
                    id="bargain_refuse",
                    text="Refuse",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="home_overpowered",
                    intensity_modifier=0.3,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="home_restrained",
            title="Restrained",
            description="He ties your hands. Pushes you toward the bedroom. Your bedroom.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="restrained_comply",
                    text="Walk where he pushes you",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
                Choice(
                    id="restrained_drop",
                    text="Let your legs give out",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="dragged",
                    consequence_hint="He drags you instead..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="dragged",
            title="Dragged",
            description="He drags you by your bound wrists. Carpet burns. It doesn't matter to him.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="dragged_bed",
                    text="He throws you on the bed",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="home_overpowered",
            title="Overpowered",
            description="He's too strong. Too fast. You're pinned beneath him on your own floor.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="pinned_fight",
                    text="Keep struggling",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.2,
                ),
                Choice(
                    id="pinned_stop",
                    text="Stop struggling. It's useless.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.1,
                ),
            ]
        ))

        # =====================================================================
        # FAMILY EXTENDED
        # =====================================================================

        self.add_node(SceneNode(
            id="family_bedroom",
            title="Your Old Room",
            description="You lie down on your childhood bed. The door opens. He's there.",
            phase=Phase.APPROACH,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="bedroom_pretend",
                    text="Pretend to be asleep",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="family_sleeping",
                    adds_layers=[ScenarioLayer.SLEEPING],
                ),
                Choice(
                    id="bedroom_confront",
                    text="Sit up. Ask what he wants.",
                    choice_type=ChoiceType.DIALOGUE,
                    leads_to="family_coercion",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="family_sleeping",
            title="Pretending",
            description="You keep your eyes closed. Feel the bed dip as he sits. His hand on your leg.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="sleeping_maintain",
                    text="Keep pretending. Maybe he'll stop.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.2,
                    consequence_hint="He doesn't stop..."
                ),
                Choice(
                    id="sleeping_wake",
                    text="'Wake up' and confront him",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="family_coercion",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="family_coercion",
            title="Family Coercion",
            description="'No one will believe you over me. I'm family. Think about what this would do to your parents.'",
            phase=Phase.COERCION,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="fam_protect",
                    text="Give in to protect your family",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                    intensity_modifier=-0.2,
                ),
                Choice(
                    id="fam_scream",
                    text="Scream for help anyway",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="family_silenced",
                    intensity_modifier=0.3,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="family_silenced",
            title="Silenced",
            description="His hand covers your mouth. 'The TV's loud. They won't hear. And if they did... who would they believe?'",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="fam_fight",
                    text="Fight anyway",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    intensity_modifier=0.3,
                ),
                Choice(
                    id="fam_give",
                    text="Give up. He's right.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="family_basement",
            title="The Basement",
            description="He leads you down the stairs. The familiar basement feels different now. Sinister.",
            phase=Phase.COERCION,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="base_stairs",
                    text="Try to run back up the stairs",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="base_caught",
                    intensity_modifier=0.2,
                ),
                Choice(
                    id="base_cooperate",
                    text="Cooperate. No one can hear you down here.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="base_caught",
            title="Caught on Stairs",
            description="He grabs your ankle. You fall. He drags you back down.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="stairs_fight",
                    text="Kick and fight",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="assault_during_fight",
                    adds_layers=[ScenarioLayer.INJURED],
                    intensity_modifier=0.4,
                ),
                Choice(
                    id="stairs_stop",
                    text="Stop fighting",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="assault_beginning",
                ),
            ]
        ))

        # =====================================================================
        # SUPERNATURAL BRANCH
        # =====================================================================

        self.add_node(SceneNode(
            id="start_supernatural",
            title="Something Wrong",
            description="You wake in the night. Something is in the room with you. Something inhuman.",
            phase=Phase.APPROACH,
            choices=[
                Choice(
                    id="super_monster",
                    text="[MONSTER] Red eyes in the dark",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="monster_approach",
                    adds_layers=[ScenarioLayer.MONSTER],
                    changes_perp=PerpType.PREDATOR,
                ),
                Choice(
                    id="super_tentacle",
                    text="[TENTACLES] Something slithering",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="tentacle_approach",
                    adds_layers=[ScenarioLayer.TENTACLES],
                    changes_perp=PerpType.PREDATOR,
                ),
                Choice(
                    id="super_vampire",
                    text="[VAMPIRE] A figure by your bed",
                    choice_type=ChoiceType.LOCATION,
                    leads_to="vampire_approach",
                    adds_layers=[ScenarioLayer.VAMPIRE_THRALL],
                    changes_perp=PerpType.PREDATOR,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="monster_approach",
            title="The Monster",
            description="Massive. Inhuman. Claws and teeth and hunger. It towers over your bed.",
            phase=Phase.APPROACH,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="monster_run",
                    text="Try to run",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="monster_caught",
                    intensity_modifier=0.3,
                ),
                Choice(
                    id="monster_freeze",
                    text="Freeze in terror",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="monster_takes",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="monster_caught",
            title="Caught",
            description="Claws tear your clothes as it drags you back. Pins you down with inhuman strength.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="m_caught_fight",
                    text="Fight uselessly",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="monster_during",
                    intensity_modifier=0.3,
                ),
                Choice(
                    id="m_caught_submit",
                    text="Go limp. You can't fight this.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="monster_during",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="monster_takes",
            title="Taken",
            description="It grabs you. Lifts you like you weigh nothing. Positions you how it wants.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="m_takes_scream",
                    text="Scream",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="monster_during",
                    intensity_modifier=0.1,
                    consequence_hint="No one comes..."
                ),
                Choice(
                    id="m_takes_silent",
                    text="Silent terror",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="monster_during",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="monster_during",
            title="The Monster Uses You",
            description="Inhuman. Wrong. Too big. It doesn't care if you survive.",
            phase=Phase.DURING,
            num_dialogue_lines=10,
            choices=[
                Choice(
                    id="monster_endure",
                    text="Try to survive",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="monster_ending",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="monster_ending",
            title="Dawn",
            description="You wake to sunlight. Alone. Was it real? The marks on your body say yes.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="tentacle_approach",
            title="Tentacles",
            description="They slide from under the bed. Wrap around your ankles. Pull.",
            phase=Phase.APPROACH,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="tent_grab",
                    text="Grab the headboard",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="tentacle_pulled",
                    intensity_modifier=0.2,
                ),
                Choice(
                    id="tent_paralyzed",
                    text="Paralyzed with fear",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="tentacle_wrapped",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="tentacle_pulled",
            title="Pulled",
            description="More tentacles. They pry your hands free. Wrap around your wrists, your thighs. Spread you.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="pulled_fight",
                    text="Keep fighting",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="tentacle_during",
                    intensity_modifier=0.2,
                ),
                Choice(
                    id="pulled_still",
                    text="Go still",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="tentacle_during",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="tentacle_wrapped",
            title="Wrapped",
            description="They cocoon you. Lift you off the bed. Suspend you in their grip.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="wrapped_scream",
                    text="Scream",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="tentacle_during",
                    consequence_hint="A tentacle fills your mouth..."
                ),
                Choice(
                    id="wrapped_accept",
                    text="Accept what's coming",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="tentacle_during",
                    intensity_modifier=-0.1,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="tentacle_during",
            title="Filled",
            description="Every opening. Stretched. Filled. More push in. There's always more.",
            phase=Phase.DURING,
            num_dialogue_lines=10,
            choices=[
                Choice(
                    id="tentacle_endure",
                    text="Endure. Float away.",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="tentacle_ending",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="tentacle_ending",
            title="Released",
            description="They recede. Leave you on the bed. Covered in... something. Changed.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="vampire_approach",
            title="The Vampire",
            description="Beautiful. Terrible. It looks at you with ancient hunger. 'I've watched you for so long.'",
            phase=Phase.APPROACH,
            num_dialogue_lines=5,
            choices=[
                Choice(
                    id="vamp_flee",
                    text="Try to flee",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="vampire_caught",
                    intensity_modifier=0.2,
                ),
                Choice(
                    id="vamp_mesmerized",
                    text="Can't move. Its eyes hold you.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="vampire_thrall",
                    adds_layers=[ScenarioLayer.MIND_CONTROL],
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="vampire_caught",
            title="Caught",
            description="Inhuman speed. It's on you before you reach the door. Fangs at your throat.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="v_caught_still",
                    text="Go still. Don't make it worse.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="vampire_during",
                ),
                Choice(
                    id="v_caught_fight",
                    text="Fight for your life",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="vampire_during",
                    intensity_modifier=0.3,
                    adds_layers=[ScenarioLayer.INJURED],
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="vampire_thrall",
            title="Thrall",
            description="Its will overwhelms yours. You want this now. You need it. Even as part of you screams.",
            phase=Phase.BEGINNING,
            num_dialogue_lines=6,
            choices=[
                Choice(
                    id="thrall_accept",
                    text="Accept. Surrender.",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="vampire_during",
                    intensity_modifier=-0.2,
                ),
                Choice(
                    id="thrall_fight",
                    text="Fight the compulsion",
                    choice_type=ChoiceType.RESISTANCE,
                    leads_to="vampire_during",
                    intensity_modifier=0.2,
                    consequence_hint="You can't win against its mind..."
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="vampire_during",
            title="Feeding",
            description="It drinks. And takes. Both at once. Pleasure and pain blurring together.",
            phase=Phase.DURING,
            num_dialogue_lines=10,
            choices=[
                Choice(
                    id="vampire_endure",
                    text="Endure",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="vampire_ending",
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="vampire_ending",
            title="Marked",
            description="It leaves you alive. Bound to it now. It will return. You'll be waiting.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        # =====================================================================
        # MORE ENDINGS
        # =====================================================================

        self.add_node(SceneNode(
            id="ending_reported",
            title="Reported",
            description="You went to the police. They took a report. He was never charged. You see him sometimes.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="ending_moved",
            title="Started Over",
            description="You moved. New city. New life. But you still check the locks three times.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="ending_therapy",
            title="Healing",
            description="Slowly, with help, you're rebuilding. Some days are harder than others. But you're surviving.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="kept_escape",
            title="Escape Attempt",
            description="You wait for your moment. A door left unlocked. A second of inattention.",
            phase=Phase.DURING,
            choices=[
                Choice(
                    id="escape_succeed",
                    text="Run. Don't look back.",
                    choice_type=ChoiceType.ESCAPE,
                    leads_to="ending_escaped_captivity",
                    is_ending=True,
                ),
                Choice(
                    id="escape_caught",
                    text="He catches you",
                    choice_type=ChoiceType.RESPONSE,
                    leads_to="recaptured",
                    adds_layers=[ScenarioLayer.RECAPTURED],
                    intensity_modifier=0.4,
                ),
            ]
        ))

        self.add_node(SceneNode(
            id="ending_escaped_captivity",
            title="Escaped",
            description="You got away. After days. Weeks. However long. You're free. Physically, at least.",
            phase=Phase.AFTERMATH,
            is_ending=True,
            num_dialogue_lines=0,
        ))

        self.add_node(SceneNode(
            id="recaptured",
            title="Recaptured",
            description="He's furious. This time will be worse. He'll make sure you never try again.",
            phase=Phase.ESCALATION,
            num_dialogue_lines=8,
            choices=[
                Choice(
                    id="recap_broken",
                    text="Break completely",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="ending_broken",
                    adds_layers=[ScenarioLayer.BROKEN, ScenarioLayer.TRAINED],
                    is_ending=True,
                ),
                Choice(
                    id="recap_survive",
                    text="Survive. Plan for next time.",
                    choice_type=ChoiceType.MENTAL,
                    leads_to="aftermath_kept",
                ),
            ]
        ))

    def add_node(self, node: SceneNode):
        """Add a node to the story tree"""
        self.nodes[node.id] = node

    def start_game(self, perspective: Perspective = Perspective.VICTIM) -> GameState:
        """Start a new game"""
        self.state = GameState(
            perspective=perspective,
            current_node="start",
            active_layers=[],
            perp_type=PerpType.STRANGER,
            intensity=0.5,
            phase=Phase.APPROACH,
        )
        return self.state

    def get_current_node(self) -> Optional[SceneNode]:
        """Get the current scene node"""
        if not self.state:
            return None
        return self.nodes.get(self.state.current_node)

    def generate_scene_content(self) -> Dict:
        """Generate content for the current scene"""
        if not self.state:
            return {}

        node = self.get_current_node()
        if not node:
            return {}

        # Build scenario from current state
        scenario = self.mixer.create_scenario(
            self.state.perp_type,
            self.state.active_layers[:3] if self.state.active_layers else [],
            node.phase
        )
        scenario.intensity = self.state.intensity

        # Generate dialogue
        dialogue = []
        if node.num_dialogue_lines > 0:
            if self.state.perspective == Perspective.VICTIM:
                # Victim POV: villain speaks, victim thinks
                for _ in range(node.num_dialogue_lines):
                    villain_line = scenario.generate_line()
                    dialogue.append({"type": "villain_speaks", "text": villain_line})

                    if random.random() < 0.5:
                        context = GenerationContext(
                            perp_type=self.state.perp_type,
                            phase=node.phase,
                            intensity=self.state.intensity
                        )
                        thought = self.generator.generate_victim_thought(context)
                        dialogue.append({"type": "victim_thinks", "text": thought})
            else:
                # Dom POV: dom speaks, dom thinks/feels
                context = GenerationContext(
                    perp_type=self.state.perp_type,
                    phase=node.phase,
                    intensity=self.state.intensity
                )
                exchange = self.generator.generate_dom_pov_exchange(context, node.num_dialogue_lines)
                dialogue = exchange

        return {
            "node": node,
            "scenario": scenario.describe() if scenario else "base",
            "dialogue": dialogue,
            "choices": self._filter_choices(node.choices),
        }

    def _filter_choices(self, choices: List[Choice]) -> List[Choice]:
        """Filter choices based on current state"""
        if not self.state:
            return choices

        valid = []
        for choice in choices:
            # Check required layers
            if choice.requires_layers:
                if not all(l in self.state.active_layers for l in choice.requires_layers):
                    continue

            # Check excluded layers
            if choice.excludes_layers:
                if any(l in self.state.active_layers for l in choice.excludes_layers):
                    continue

            valid.append(choice)

        return valid

    def make_choice(self, choice_id: str) -> Tuple[bool, Dict]:
        """Make a choice and advance the game"""
        if not self.state:
            return False, {"error": "No active game"}

        node = self.get_current_node()
        if not node:
            return False, {"error": "No current node"}

        # Find the choice
        choice = None
        for c in node.choices:
            if c.id == choice_id:
                choice = c
                break

        if not choice:
            return False, {"error": f"Invalid choice: {choice_id}"}

        # Apply choice effects
        self.state.choices_made.append(choice_id)
        self.state.nodes_visited.append(self.state.current_node)

        if choice.adds_layers:
            for layer in choice.adds_layers:
                if layer not in self.state.active_layers:
                    self.state.active_layers.append(layer)

        if choice.changes_perp:
            self.state.perp_type = choice.changes_perp

        self.state.intensity = max(0.0, min(1.0,
            self.state.intensity + choice.intensity_modifier))

        # Update resistance/compliance scores
        if choice.choice_type == ChoiceType.RESISTANCE:
            self.state.resistance_score += 1
        elif choice.choice_type in [ChoiceType.RESPONSE] and "comply" in choice.id:
            self.state.compliance_score += 1

        # Move to next node
        if choice.leads_to:
            self.state.current_node = choice.leads_to
            next_node = self.get_current_node()
            if next_node:
                self.state.phase = next_node.phase

        return True, {
            "choice": choice,
            "new_state": self.state,
            "is_ending": choice.is_ending or (self.get_current_node() and self.get_current_node().is_ending)
        }

    def get_summary(self) -> Dict:
        """Get summary of the playthrough"""
        if not self.state:
            return {}

        return {
            "perspective": self.state.perspective.value,
            "choices_made": len(self.state.choices_made),
            "nodes_visited": len(self.state.nodes_visited),
            "active_layers": [l.value for l in self.state.active_layers],
            "perpetrator_type": self.state.perp_type.value,
            "final_intensity": self.state.intensity,
            "resistance_score": self.state.resistance_score,
            "compliance_score": self.state.compliance_score,
            "ending_node": self.state.current_node,
        }


# =============================================================================
# CLI / Demo
# =============================================================================

def play_demo():
    """Run a simple demo of the CYOA engine"""
    print("=" * 70)
    print("CYOA NC ENGINE - Demo Playthrough")
    print("=" * 70)

    engine = CYOAEngine()
    engine.start_game(Perspective.VICTIM)

    while True:
        content = engine.generate_scene_content()
        node = content.get("node")

        if not node:
            break

        print(f"\n{'='*60}")
        print(f"[{node.title}]")
        print(f"{'='*60}")
        print(f"\n{node.description}")

        # Show dialogue
        if content.get("dialogue"):
            print("\n--- Scene ---")
            for line in content["dialogue"]:
                if line["type"] == "villain_speaks":
                    print(f'  HE SAYS: "{line["text"]}"')
                elif line["type"] == "victim_thinks":
                    print(f'  [You think: {line["text"]}]')

        # Show choices
        choices = content.get("choices", [])
        if not choices or node.is_ending:
            print("\n[THE END]")
            break

        print("\n--- What do you do? ---")
        for i, choice in enumerate(choices, 1):
            hint = f" ({choice.consequence_hint})" if choice.consequence_hint else ""
            print(f"  {i}. {choice.text}{hint}")

        # Auto-select for demo (random)
        selected = random.choice(choices)
        print(f"\n  > Selected: {selected.text}")

        success, result = engine.make_choice(selected.id)
        if not success:
            print(f"Error: {result}")
            break

        if result.get("is_ending"):
            content = engine.generate_scene_content()
            node = content.get("node")
            if node:
                print(f"\n{'='*60}")
                print(f"[ENDING: {node.title}]")
                print(f"{'='*60}")
                print(f"\n{node.description}")
            break

    # Summary
    print("\n" + "=" * 70)
    print("PLAYTHROUGH SUMMARY")
    print("=" * 70)
    summary = engine.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("\nCYOA Engine Statistics:")
    engine = CYOAEngine()
    print(f"  Total nodes: {len(engine.nodes)}")

    total_choices = sum(len(n.choices) for n in engine.nodes.values())
    print(f"  Total choices: {total_choices}")

    endings = [n for n in engine.nodes.values() if n.is_ending]
    print(f"  Possible endings: {len(endings)}")

    print("\n" + "=" * 70)
    print("Running demo playthrough...")
    play_demo()
