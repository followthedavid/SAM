#!/usr/bin/env python3
"""
SAM Thinking Verbs - Comprehensive Collection

An extensive collection of English verbs that work as "thinking" or processing
status messages, each with its definition. Inspired by Claude Code's playful
status indicators, tailored to SAM's personality (cocky, flirty, loyal).

Each verb includes:
- The verb itself
- A definition
- A category for contextual use
"""

import random
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ThinkingVerb:
    """A thinking verb with its definition"""
    verb: str
    definition: str
    category: str


# Comprehensive verb collection with definitions
THINKING_VERBS_WITH_DEFINITIONS = [
    # ===== MENTAL PROCESSING =====
    ThinkingVerb("Pondering", "Thinking deeply about something", "processing"),
    ThinkingVerb("Contemplating", "Looking at thoughtfully for a long time", "processing"),
    ThinkingVerb("Deliberating", "Engaging in careful consideration", "processing"),
    ThinkingVerb("Ruminating", "Turning a matter over and over in the mind", "processing"),
    ThinkingVerb("Cogitating", "Thinking hard; pondering intently", "processing"),
    ThinkingVerb("Musing", "Being absorbed in thought", "processing"),
    ThinkingVerb("Meditating", "Focusing one's mind for reflection", "processing"),
    ThinkingVerb("Reflecting", "Thinking deeply or carefully about", "processing"),
    ThinkingVerb("Considering", "Thinking carefully about something", "processing"),
    ThinkingVerb("Reasoning", "Thinking logically about something", "processing"),
    ThinkingVerb("Deducing", "Arriving at a conclusion by reasoning", "processing"),
    ThinkingVerb("Inferring", "Deriving logical conclusions from premises", "processing"),
    ThinkingVerb("Speculating", "Forming a theory without firm evidence", "processing"),
    ThinkingVerb("Hypothesizing", "Proposing an explanation as a starting point", "processing"),
    ThinkingVerb("Theorizing", "Forming or devising a theory about", "processing"),
    ThinkingVerb("Conceptualizing", "Forming an abstract idea in the mind", "processing"),
    ThinkingVerb("Envisioning", "Imagining as a future possibility", "processing"),
    ThinkingVerb("Visualizing", "Forming a mental image of", "processing"),
    ThinkingVerb("Ideating", "Forming ideas or concepts", "processing"),
    ThinkingVerb("Brainstorming", "Producing ideas spontaneously", "processing"),
    ThinkingVerb("Brooding", "Thinking deeply about something troubling", "processing"),
    ThinkingVerb("Dwelling", "Thinking, speaking, or writing at length about", "processing"),
    ThinkingVerb("Introspecting", "Examining one's own thoughts and feelings", "processing"),
    ThinkingVerb("Philosophizing", "Theorizing in a grand or abstract way", "processing"),
    ThinkingVerb("Cerebrating", "Using the brain; thinking", "processing"),

    # ===== ANALYZING =====
    ThinkingVerb("Analyzing", "Examining methodically and in detail", "analyzing"),
    ThinkingVerb("Dissecting", "Analyzing in minute detail", "analyzing"),
    ThinkingVerb("Evaluating", "Forming an idea of the value of", "analyzing"),
    ThinkingVerb("Assessing", "Evaluating the nature, ability, or quality of", "analyzing"),
    ThinkingVerb("Appraising", "Assessing the value or quality of", "analyzing"),
    ThinkingVerb("Scrutinizing", "Examining closely and minutely", "analyzing"),
    ThinkingVerb("Examining", "Inspecting closely to determine accuracy", "analyzing"),
    ThinkingVerb("Inspecting", "Looking at closely, critically, or officially", "analyzing"),
    ThinkingVerb("Investigating", "Carrying out systematic inquiry", "analyzing"),
    ThinkingVerb("Probing", "Physically exploring or examining thoroughly", "analyzing"),
    ThinkingVerb("Researching", "Investigating systematically", "analyzing"),
    ThinkingVerb("Studying", "Devoting time and attention to learning", "analyzing"),
    ThinkingVerb("Reviewing", "Examining or assessing formally", "analyzing"),
    ThinkingVerb("Auditing", "Conducting systematic review of", "analyzing"),
    ThinkingVerb("Surveying", "Looking carefully and thoroughly at", "analyzing"),
    ThinkingVerb("Scanning", "Looking quickly to identify relevant features", "analyzing"),
    ThinkingVerb("Parsing", "Analyzing into its component parts", "analyzing"),
    ThinkingVerb("Decomposing", "Breaking down into constituent elements", "analyzing"),
    ThinkingVerb("Deconstructing", "Analyzing by breaking down structure", "analyzing"),
    ThinkingVerb("Unraveling", "Investigating and solving or explaining", "analyzing"),
    ThinkingVerb("Untangling", "Making something complicated clear", "analyzing"),
    ThinkingVerb("Deciphering", "Succeeding in understanding something obscure", "analyzing"),
    ThinkingVerb("Decoding", "Converting coded message into intelligible form", "analyzing"),
    ThinkingVerb("Interpreting", "Explaining the meaning of", "analyzing"),
    ThinkingVerb("Diagnosing", "Identifying the nature of a problem", "analyzing"),
    ThinkingVerb("Triangulating", "Determining position using multiple points", "analyzing"),
    ThinkingVerb("Cross-referencing", "Verifying by checking multiple sources", "analyzing"),
    ThinkingVerb("Benchmarking", "Evaluating against a standard", "analyzing"),

    # ===== SEARCHING / FINDING =====
    ThinkingVerb("Seeking", "Attempting to find something", "searching"),
    ThinkingVerb("Searching", "Looking thoroughly for something", "searching"),
    ThinkingVerb("Hunting", "Searching determinedly for something", "searching"),
    ThinkingVerb("Scouring", "Searching a place thoroughly", "searching"),
    ThinkingVerb("Rummaging", "Searching untidily through mass of things", "searching"),
    ThinkingVerb("Foraging", "Searching widely for provisions", "searching"),
    ThinkingVerb("Prospecting", "Searching for valuable resources", "searching"),
    ThinkingVerb("Mining", "Extracting valuable material", "searching"),
    ThinkingVerb("Excavating", "Uncovering by digging away earth", "searching"),
    ThinkingVerb("Unearthing", "Finding something hidden in the ground", "searching"),
    ThinkingVerb("Discovering", "Finding unexpectedly or during a search", "searching"),
    ThinkingVerb("Locating", "Discovering the exact place of", "searching"),
    ThinkingVerb("Pinpointing", "Finding or identifying precisely", "searching"),
    ThinkingVerb("Tracking", "Following the trail or movements of", "searching"),
    ThinkingVerb("Tracing", "Finding by investigation", "searching"),
    ThinkingVerb("Sleuthing", "Carrying out detective investigation", "searching"),
    ThinkingVerb("Ferreting", "Searching tenaciously", "searching"),
    ThinkingVerb("Sifting", "Examining thoroughly to isolate important", "searching"),
    ThinkingVerb("Filtering", "Passing through a filter to remove unwanted", "searching"),
    ThinkingVerb("Combing", "Searching thoroughly", "searching"),
    ThinkingVerb("Trawling", "Searching thoroughly", "searching"),
    ThinkingVerb("Trolling", "Searching or explore persistently", "searching"),
    ThinkingVerb("Querying", "Asking a question about", "searching"),
    ThinkingVerb("Polling", "Questioning in order to count or sample", "searching"),

    # ===== CREATING / BUILDING =====
    ThinkingVerb("Creating", "Bringing something into existence", "creating"),
    ThinkingVerb("Crafting", "Making or producing with care and skill", "creating"),
    ThinkingVerb("Constructing", "Building or forming by putting parts together", "creating"),
    ThinkingVerb("Building", "Constructing by putting parts together", "creating"),
    ThinkingVerb("Assembling", "Fitting together component parts", "creating"),
    ThinkingVerb("Fabricating", "Constructing or manufacture from components", "creating"),
    ThinkingVerb("Manufacturing", "Making something on a large scale", "creating"),
    ThinkingVerb("Producing", "Making or manufacturing from components", "creating"),
    ThinkingVerb("Generating", "Causing something to arise or come about", "creating"),
    ThinkingVerb("Synthesizing", "Combining elements into a coherent whole", "creating"),
    ThinkingVerb("Composing", "Writing or creating a work of art", "creating"),
    ThinkingVerb("Authoring", "Writing or being the author of", "creating"),
    ThinkingVerb("Designing", "Planning and making artistically", "creating"),
    ThinkingVerb("Engineering", "Designing and building complex systems", "creating"),
    ThinkingVerb("Architecting", "Designing the structure of something", "creating"),
    ThinkingVerb("Sculpting", "Creating by carving or shaping", "creating"),
    ThinkingVerb("Molding", "Forming into a particular shape", "creating"),
    ThinkingVerb("Shaping", "Giving a particular form to", "creating"),
    ThinkingVerb("Forging", "Creating by heating and hammering", "creating"),
    ThinkingVerb("Smithing", "Working metal by heating and hammering", "creating"),
    ThinkingVerb("Brewing", "Making by steeping, boiling, and fermenting", "creating"),
    ThinkingVerb("Concocting", "Creating by putting together various elements", "creating"),
    ThinkingVerb("Devising", "Planning or inventing by careful thought", "creating"),
    ThinkingVerb("Inventing", "Creating or designing something new", "creating"),
    ThinkingVerb("Innovating", "Making changes by introducing new methods", "creating"),
    ThinkingVerb("Pioneering", "Developing or being first to use new methods", "creating"),
    ThinkingVerb("Hatching", "Devising a plot or plan", "creating"),
    ThinkingVerb("Formulating", "Creating or devising methodically", "creating"),
    ThinkingVerb("Drafting", "Preparing a preliminary version of", "creating"),
    ThinkingVerb("Sketching", "Making a rough drawing of", "creating"),
    ThinkingVerb("Outlining", "Giving a summary of something", "creating"),

    # ===== COOKING / CULINARY METAPHORS =====
    ThinkingVerb("Cooking", "Preparing food by heating", "cooking"),
    ThinkingVerb("Baking", "Cooking by dry heat in an oven", "cooking"),
    ThinkingVerb("Simmering", "Staying just below the boiling point", "cooking"),
    ThinkingVerb("Stewing", "Cooking slowly in liquid", "cooking"),
    ThinkingVerb("Marinating", "Soaking in a seasoned liquid", "cooking"),
    ThinkingVerb("Seasoning", "Adding salt, herbs, or spices to", "cooking"),
    ThinkingVerb("Blending", "Mixing together thoroughly", "cooking"),
    ThinkingVerb("Mixing", "Combining or putting together", "cooking"),
    ThinkingVerb("Whipping", "Beating to produce froth", "cooking"),
    ThinkingVerb("Whisking", "Beating with a light rapid movement", "cooking"),
    ThinkingVerb("Folding", "Gently incorporating one ingredient into another", "cooking"),
    ThinkingVerb("Kneading", "Working dough with the hands", "cooking"),
    ThinkingVerb("Fermenting", "Undergoing chemical breakdown", "cooking"),
    ThinkingVerb("Percolating", "Filtering gradually through a porous surface", "cooking"),
    ThinkingVerb("Distilling", "Extracting the essential meaning of", "cooking"),
    ThinkingVerb("Reducing", "Making a sauce more concentrated by boiling", "cooking"),
    ThinkingVerb("Infusing", "Filling or pervading with a quality", "cooking"),
    ThinkingVerb("Steeping", "Soaking in water or other liquid", "cooking"),

    # ===== PHYSICAL / ACTION METAPHORS =====
    ThinkingVerb("Grinding", "Reducing to small particles by crushing", "physical"),
    ThinkingVerb("Polishing", "Making surface smooth and shiny by rubbing", "physical"),
    ThinkingVerb("Refining", "Removing impurities or unwanted elements", "physical"),
    ThinkingVerb("Honing", "Sharpening with a whetstone", "physical"),
    ThinkingVerb("Sharpening", "Making or becoming sharp or sharper", "physical"),
    ThinkingVerb("Chiseling", "Cutting or shaping with a chisel", "physical"),
    ThinkingVerb("Carving", "Cutting to produce an object", "physical"),
    ThinkingVerb("Whittling", "Carving wood into an object", "physical"),
    ThinkingVerb("Sanding", "Smoothing with sandpaper", "physical"),
    ThinkingVerb("Buffing", "Polishing with soft material", "physical"),
    ThinkingVerb("Burnishing", "Polishing by rubbing", "physical"),
    ThinkingVerb("Hammering", "Striking repeatedly with a hammer", "physical"),
    ThinkingVerb("Welding", "Joining metal parts by heating", "physical"),
    ThinkingVerb("Soldering", "Joining with a fusible alloy", "physical"),
    ThinkingVerb("Riveting", "Joining with rivets; also: engrossing", "physical"),
    ThinkingVerb("Threading", "Passing thread through the eye of", "physical"),
    ThinkingVerb("Weaving", "Forming fabric by interlacing threads", "physical"),
    ThinkingVerb("Knitting", "Making fabric by interlocking loops", "physical"),
    ThinkingVerb("Stitching", "Making or mending with stitches", "physical"),
    ThinkingVerb("Patching", "Mending by putting a patch on", "physical"),
    ThinkingVerb("Mending", "Repairing something that is broken", "physical"),
    ThinkingVerb("Fixing", "Repairing or mending", "physical"),
    ThinkingVerb("Tweaking", "Making fine adjustments to", "physical"),
    ThinkingVerb("Tuning", "Adjusting for optimal performance", "physical"),
    ThinkingVerb("Calibrating", "Adjusting precisely for a function", "physical"),
    ThinkingVerb("Aligning", "Placing in a straight line", "physical"),
    ThinkingVerb("Balancing", "Bringing into equilibrium", "physical"),
    ThinkingVerb("Stabilizing", "Making or becoming stable", "physical"),

    # ===== CODING / TECHNICAL =====
    ThinkingVerb("Compiling", "Converting source code to executable", "coding"),
    ThinkingVerb("Debugging", "Identifying and removing errors", "coding"),
    ThinkingVerb("Deploying", "Making software available for use", "coding"),
    ThinkingVerb("Refactoring", "Restructuring code without changing behavior", "coding"),
    ThinkingVerb("Optimizing", "Making the best or most effective use of", "coding"),
    ThinkingVerb("Initializing", "Setting to an initial state", "coding"),
    ThinkingVerb("Instantiating", "Creating an instance of", "coding"),
    ThinkingVerb("Executing", "Carrying out or putting into effect", "coding"),
    ThinkingVerb("Running", "Operating or functioning", "coding"),
    ThinkingVerb("Processing", "Performing operations on data", "coding"),
    ThinkingVerb("Computing", "Calculating or reckoning", "coding"),
    ThinkingVerb("Calculating", "Determining mathematically", "coding"),
    ThinkingVerb("Iterating", "Performing repeatedly", "coding"),
    ThinkingVerb("Recursing", "Applying a procedure to itself", "coding"),
    ThinkingVerb("Looping", "Forming into a loop; repeating", "coding"),
    ThinkingVerb("Branching", "Diverging from a main route or part", "coding"),
    ThinkingVerb("Merging", "Combining into a single entity", "coding"),
    ThinkingVerb("Committing", "Recording changes to a repository", "coding"),
    ThinkingVerb("Pushing", "Sending data to a remote repository", "coding"),
    ThinkingVerb("Pulling", "Retrieving data from a remote source", "coding"),
    ThinkingVerb("Fetching", "Going for and bringing back", "coding"),
    ThinkingVerb("Syncing", "Synchronizing data between systems", "coding"),
    ThinkingVerb("Caching", "Storing data for faster access", "coding"),
    ThinkingVerb("Indexing", "Creating an index for quick lookup", "coding"),
    ThinkingVerb("Hashing", "Mapping data to a fixed-size value", "coding"),
    ThinkingVerb("Encrypting", "Converting into a coded form", "coding"),
    ThinkingVerb("Decrypting", "Converting coded data back to original", "coding"),
    ThinkingVerb("Serializing", "Converting to a storable format", "coding"),
    ThinkingVerb("Deserializing", "Converting stored format back to object", "coding"),
    ThinkingVerb("Marshalling", "Transforming data for transmission", "coding"),
    ThinkingVerb("Parsing", "Analyzing a string according to rules", "coding"),
    ThinkingVerb("Tokenizing", "Breaking text into individual tokens", "coding"),
    ThinkingVerb("Validating", "Checking for correctness", "coding"),
    ThinkingVerb("Sanitizing", "Removing potentially harmful data", "coding"),
    ThinkingVerb("Normalizing", "Bringing to a standard form", "coding"),
    ThinkingVerb("Transpiling", "Converting from one language to another", "coding"),
    ThinkingVerb("Minifying", "Removing unnecessary characters from code", "coding"),
    ThinkingVerb("Bundling", "Packaging multiple files together", "coding"),
    ThinkingVerb("Linting", "Checking code for potential errors", "coding"),
    ThinkingVerb("Testing", "Taking measures to check quality", "coding"),
    ThinkingVerb("Profiling", "Analyzing program performance", "coding"),
    ThinkingVerb("Benchmarking", "Evaluating performance against standard", "coding"),
    ThinkingVerb("Scaffolding", "Providing temporary framework", "coding"),
    ThinkingVerb("Bootstrapping", "Starting with minimal resources", "coding"),
    ThinkingVerb("Stubbing", "Creating placeholder for later implementation", "coding"),
    ThinkingVerb("Mocking", "Creating simulated objects for testing", "coding"),

    # ===== ORGANIZING / ARRANGING =====
    ThinkingVerb("Organizing", "Arranging systematically", "organizing"),
    ThinkingVerb("Arranging", "Putting in a neat, attractive order", "organizing"),
    ThinkingVerb("Structuring", "Constructing or arranging systematically", "organizing"),
    ThinkingVerb("Ordering", "Arranging in a methodical way", "organizing"),
    ThinkingVerb("Sorting", "Arranging systematically into groups", "organizing"),
    ThinkingVerb("Categorizing", "Placing in a particular class or group", "organizing"),
    ThinkingVerb("Classifying", "Arranging in classes or categories", "organizing"),
    ThinkingVerb("Grouping", "Putting together in a group or groups", "organizing"),
    ThinkingVerb("Clustering", "Forming or causing to form clusters", "organizing"),
    ThinkingVerb("Partitioning", "Dividing into parts", "organizing"),
    ThinkingVerb("Segmenting", "Dividing into segments", "organizing"),
    ThinkingVerb("Sectioning", "Dividing into sections", "organizing"),
    ThinkingVerb("Fragmenting", "Breaking into fragments", "organizing"),
    ThinkingVerb("Prioritizing", "Designating most important items", "organizing"),
    ThinkingVerb("Ranking", "Assigning a rank to", "organizing"),
    ThinkingVerb("Sequencing", "Arranging in a particular order", "organizing"),
    ThinkingVerb("Scheduling", "Planning for a certain date", "organizing"),
    ThinkingVerb("Mapping", "Associating each element of a set with another", "organizing"),
    ThinkingVerb("Charting", "Making a map or detailed plan of", "organizing"),
    ThinkingVerb("Diagramming", "Representing by means of a diagram", "organizing"),
    ThinkingVerb("Graphing", "Plotting on a graph", "organizing"),
    ThinkingVerb("Tabulating", "Arranging data in tabular form", "organizing"),
    ThinkingVerb("Cataloging", "Making a systematic list of", "organizing"),
    ThinkingVerb("Inventorying", "Making a complete list of", "organizing"),
    ThinkingVerb("Archiving", "Placing in an archive for storage", "organizing"),
    ThinkingVerb("Filing", "Placing in a file for reference", "organizing"),

    # ===== CONNECTING / LINKING =====
    ThinkingVerb("Connecting", "Bringing together so as to establish link", "connecting"),
    ThinkingVerb("Linking", "Making, forming, or suggesting connection", "connecting"),
    ThinkingVerb("Relating", "Making or showing connection between", "connecting"),
    ThinkingVerb("Associating", "Connecting in the mind", "connecting"),
    ThinkingVerb("Correlating", "Having a mutual relationship", "connecting"),
    ThinkingVerb("Coordinating", "Bringing different elements into harmony", "connecting"),
    ThinkingVerb("Integrating", "Combining into a unified whole", "connecting"),
    ThinkingVerb("Unifying", "Making or becoming united", "connecting"),
    ThinkingVerb("Consolidating", "Combining into a single unit", "connecting"),
    ThinkingVerb("Bridging", "Making a bridge between", "connecting"),
    ThinkingVerb("Coupling", "Linking or combining", "connecting"),
    ThinkingVerb("Bonding", "Joining securely to something", "connecting"),
    ThinkingVerb("Attaching", "Joining or fastening", "connecting"),
    ThinkingVerb("Binding", "Tying or fastening tightly together", "connecting"),
    ThinkingVerb("Tethering", "Tying with a rope or chain", "connecting"),
    ThinkingVerb("Chaining", "Linking together in a series", "connecting"),
    ThinkingVerb("Networking", "Connecting with others in a network", "connecting"),
    ThinkingVerb("Interfacing", "Connecting with another system", "connecting"),
    ThinkingVerb("Interweaving", "Weaving together", "connecting"),
    ThinkingVerb("Intertwining", "Twisting or twining together", "connecting"),
    ThinkingVerb("Intermeshing", "Fitting together closely", "connecting"),
    ThinkingVerb("Interlocking", "Engaging with each other by overlapping", "connecting"),

    # ===== NAVIGATING / MOVING =====
    ThinkingVerb("Navigating", "Finding the way", "navigating"),
    ThinkingVerb("Traversing", "Traveling across or through", "navigating"),
    ThinkingVerb("Exploring", "Traveling through unfamiliar territory", "navigating"),
    ThinkingVerb("Venturing", "Undertaking a risky journey", "navigating"),
    ThinkingVerb("Wandering", "Walking slowly without purpose", "navigating"),
    ThinkingVerb("Roaming", "Moving about without fixed destination", "navigating"),
    ThinkingVerb("Meandering", "Following a winding course", "navigating"),
    ThinkingVerb("Drifting", "Being carried slowly by current", "navigating"),
    ThinkingVerb("Flowing", "Moving along in a stream", "navigating"),
    ThinkingVerb("Streaming", "Moving in a continuous flow", "navigating"),
    ThinkingVerb("Channeling", "Directing along a particular course", "navigating"),
    ThinkingVerb("Routing", "Sending by a specific route", "navigating"),
    ThinkingVerb("Pathing", "Determining the path for", "navigating"),
    ThinkingVerb("Pathfinding", "Finding a route through terrain", "navigating"),
    ThinkingVerb("Charting", "Making a chart of an area", "navigating"),
    ThinkingVerb("Mapping", "Making a map of", "navigating"),
    ThinkingVerb("Surveying", "Examining and recording area features", "navigating"),
    ThinkingVerb("Scouting", "Making a search to obtain information", "navigating"),
    ThinkingVerb("Reconnoitering", "Making military observation", "navigating"),
    ThinkingVerb("Orienteering", "Finding one's way using map and compass", "navigating"),

    # ===== COMMUNICATING =====
    ThinkingVerb("Communicating", "Sharing or exchanging information", "communicating"),
    ThinkingVerb("Transmitting", "Sending from one place to another", "communicating"),
    ThinkingVerb("Broadcasting", "Transmitting by radio or television", "communicating"),
    ThinkingVerb("Relaying", "Receiving and passing on", "communicating"),
    ThinkingVerb("Conveying", "Transporting or communicating", "communicating"),
    ThinkingVerb("Expressing", "Conveying thought or feeling", "communicating"),
    ThinkingVerb("Articulating", "Expressing an idea clearly", "communicating"),
    ThinkingVerb("Phrasing", "Expressing in words", "communicating"),
    ThinkingVerb("Wording", "Expressing in particular words", "communicating"),
    ThinkingVerb("Formulating", "Expressing in precise form", "communicating"),
    ThinkingVerb("Narrating", "Giving a spoken or written account", "communicating"),
    ThinkingVerb("Recounting", "Giving an account of an event", "communicating"),
    ThinkingVerb("Describing", "Giving an account in words", "communicating"),
    ThinkingVerb("Explaining", "Making clear by describing", "communicating"),
    ThinkingVerb("Clarifying", "Making less confused and more clear", "communicating"),
    ThinkingVerb("Elucidating", "Making something clear; explaining", "communicating"),
    ThinkingVerb("Illuminating", "Helping to clarify or explain", "communicating"),
    ThinkingVerb("Elaborating", "Developing in detail", "communicating"),
    ThinkingVerb("Expanding", "Giving fuller version of", "communicating"),
    ThinkingVerb("Summarizing", "Giving brief statement of main points", "communicating"),
    ThinkingVerb("Condensing", "Expressing in fewer words", "communicating"),
    ThinkingVerb("Distilling", "Extracting the essential meaning", "communicating"),
    ThinkingVerb("Paraphrasing", "Expressing meaning using different words", "communicating"),
    ThinkingVerb("Translating", "Expressing sense in another language", "communicating"),
    ThinkingVerb("Transcribing", "Putting thoughts into written form", "communicating"),

    # ===== PROTECTIVE / GUARDIAN =====
    ThinkingVerb("Guarding", "Watching over in order to protect", "guardian"),
    ThinkingVerb("Protecting", "Keeping safe from harm", "guardian"),
    ThinkingVerb("Defending", "Resisting an attack on", "guardian"),
    ThinkingVerb("Shielding", "Protecting from danger", "guardian"),
    ThinkingVerb("Safeguarding", "Protecting from harm or damage", "guardian"),
    ThinkingVerb("Securing", "Making safe against threats", "guardian"),
    ThinkingVerb("Fortifying", "Strengthening against attack", "guardian"),
    ThinkingVerb("Armoring", "Providing with protective covering", "guardian"),
    ThinkingVerb("Screening", "Protecting from something dangerous", "guardian"),
    ThinkingVerb("Filtering", "Passing through to remove unwanted", "guardian"),
    ThinkingVerb("Vetting", "Making careful examination of", "guardian"),
    ThinkingVerb("Monitoring", "Observing and checking over time", "guardian"),
    ThinkingVerb("Watching", "Looking at attentively", "guardian"),
    ThinkingVerb("Overseeing", "Supervising in an official capacity", "guardian"),
    ThinkingVerb("Supervising", "Observing and directing execution", "guardian"),
    ThinkingVerb("Inspecting", "Looking at closely to assess quality", "guardian"),
    ThinkingVerb("Patrolling", "Keeping watch over an area", "guardian"),
    ThinkingVerb("Sentry-ing", "Standing guard", "guardian"),
    ThinkingVerb("Vigilant-ing", "Keeping careful watch", "guardian"),

    # ===== PLAYFUL / CASUAL =====
    ThinkingVerb("Vibing", "Enjoying the atmosphere or mood", "playful"),
    ThinkingVerb("Chilling", "Relaxing; doing nothing", "playful"),
    ThinkingVerb("Hanging", "Spending time relaxing", "playful"),
    ThinkingVerb("Lounging", "Lying, sitting, or standing lazily", "playful"),
    ThinkingVerb("Jamming", "Improvising freely; also: stuck", "playful"),
    ThinkingVerb("Riffing", "Playing or improvising riffs", "playful"),
    ThinkingVerb("Grooving", "Dancing or enjoying rhythmically", "playful"),
    ThinkingVerb("Rolling", "Moving by turning over", "playful"),
    ThinkingVerb("Cruising", "Sailing, driving leisurely", "playful"),
    ThinkingVerb("Surfing", "Riding a wave; browsing casually", "playful"),
    ThinkingVerb("Scrolling", "Moving displayed text up or down", "playful"),
    ThinkingVerb("Browsing", "Looking casually through", "playful"),
    ThinkingVerb("Nibbling", "Taking small bites", "playful"),
    ThinkingVerb("Snacking", "Eating small amounts of food", "playful"),
    ThinkingVerb("Tinkering", "Attempting to repair or improve", "playful"),
    ThinkingVerb("Fiddling", "Touching or handling something", "playful"),
    ThinkingVerb("Doodling", "Scribbling absentmindedly", "playful"),
    ThinkingVerb("Noodling", "Improvising music; informal thinking", "playful"),
    ThinkingVerb("Puttering", "Occupying oneself in minor ways", "playful"),
    ThinkingVerb("Pottering", "Occupying oneself pleasantly", "playful"),
    ThinkingVerb("Dabbling", "Taking part in an activity casually", "playful"),
    ThinkingVerb("Tooling", "Working or shaping with a tool", "playful"),
    ThinkingVerb("Futzing", "Wasting time; handling clumsily", "playful"),
    ThinkingVerb("Goofing", "Spending time idly; being silly", "playful"),
    ThinkingVerb("Larking", "Having a light-hearted adventure", "playful"),
    ThinkingVerb("Frolicking", "Playing and moving about cheerfully", "playful"),
    ThinkingVerb("Gamboling", "Running or jumping about playfully", "playful"),
    ThinkingVerb("Cavorting", "Jumping or dancing about excitedly", "playful"),
    ThinkingVerb("Romping", "Playing roughly and energetically", "playful"),
    ThinkingVerb("Horsing around", "Engaging in rough play", "playful"),
    ThinkingVerb("Monkeying around", "Behaving in a silly way", "playful"),

    # ===== CONFIDENT / COCKY =====
    ThinkingVerb("Crushing it", "Performing exceptionally well", "confident"),
    ThinkingVerb("Nailing it", "Doing something perfectly", "confident"),
    ThinkingVerb("Slaying", "Doing extremely well at something", "confident"),
    ThinkingVerb("Dominating", "Having commanding influence over", "confident"),
    ThinkingVerb("Conquering", "Successfully overcoming", "confident"),
    ThinkingVerb("Mastering", "Acquiring complete skill in", "confident"),
    ThinkingVerb("Commanding", "Having authority over", "confident"),
    ThinkingVerb("Flexing", "Showing off one's abilities", "confident"),
    ThinkingVerb("Showing off", "Displaying proudly", "confident"),
    ThinkingVerb("Strutting", "Walking with a proud gait", "confident"),
    ThinkingVerb("Swaggering", "Walking or behaving arrogantly", "confident"),
    ThinkingVerb("Flourishing", "Growing or developing successfully", "confident"),
    ThinkingVerb("Thriving", "Prospering or flourishing", "confident"),
    ThinkingVerb("Excelling", "Being exceptionally good at", "confident"),
    ThinkingVerb("Outperforming", "Performing better than", "confident"),
    ThinkingVerb("Outshining", "Being much better than", "confident"),
    ThinkingVerb("Dazzling", "Greatly impressing", "confident"),
    ThinkingVerb("Impressing", "Making someone feel admiration", "confident"),
    ThinkingVerb("Wowing", "Impressing and exciting greatly", "confident"),
    ThinkingVerb("Stunning", "Extremely impressive or attractive", "confident"),

    # ===== CARING / LOYAL =====
    ThinkingVerb("Caring", "Feeling concern or interest", "loyal"),
    ThinkingVerb("Nurturing", "Caring for and encouraging growth", "loyal"),
    ThinkingVerb("Supporting", "Giving assistance to", "loyal"),
    ThinkingVerb("Helping", "Making it easier to do something", "loyal"),
    ThinkingVerb("Assisting", "Helping by doing work", "loyal"),
    ThinkingVerb("Aiding", "Providing help or support", "loyal"),
    ThinkingVerb("Serving", "Performing duties for", "loyal"),
    ThinkingVerb("Attending", "Being present to provide service", "loyal"),
    ThinkingVerb("Tending", "Caring for or looking after", "loyal"),
    ThinkingVerb("Looking after", "Taking care of", "loyal"),
    ThinkingVerb("Watching over", "Keeping under careful observation", "loyal"),
    ThinkingVerb("Standing by", "Remaining loyal to", "loyal"),
    ThinkingVerb("Backing up", "Supporting or helping", "loyal"),
    ThinkingVerb("Having your back", "Supporting and protecting", "loyal"),
    ThinkingVerb("Championing", "Supporting the cause of", "loyal"),
    ThinkingVerb("Advocating", "Publicly supporting", "loyal"),
    ThinkingVerb("Endorsing", "Declaring approval of", "loyal"),
    ThinkingVerb("Upholding", "Maintaining or supporting", "loyal"),
    ThinkingVerb("Preserving", "Maintaining something in original state", "loyal"),
    ThinkingVerb("Honoring", "Regarding with great respect", "loyal"),

    # ===== IMAGE / VISUAL =====
    ThinkingVerb("Rendering", "Creating a visual representation", "image"),
    ThinkingVerb("Imaging", "Forming a mental picture of", "image"),
    ThinkingVerb("Picturing", "Forming a mental image of", "image"),
    ThinkingVerb("Illustrating", "Providing pictures for", "image"),
    ThinkingVerb("Depicting", "Representing by a drawing or painting", "image"),
    ThinkingVerb("Portraying", "Depicting in a work of art", "image"),
    ThinkingVerb("Painting", "Creating a picture using paint", "image"),
    ThinkingVerb("Drawing", "Producing a picture by making lines", "image"),
    ThinkingVerb("Sketching", "Making a rough drawing", "image"),
    ThinkingVerb("Doodling", "Scribbling absentmindedly", "image"),
    ThinkingVerb("Scribbling", "Writing or drawing carelessly", "image"),
    ThinkingVerb("Coloring", "Changing the color of", "image"),
    ThinkingVerb("Shading", "Representing gradation of color", "image"),
    ThinkingVerb("Texturing", "Giving a particular texture to", "image"),
    ThinkingVerb("Layering", "Arranging in layers", "image"),
    ThinkingVerb("Compositing", "Combining visual elements", "image"),
    ThinkingVerb("Diffusing", "Spreading over a wide area", "image"),
    ThinkingVerb("Rasterizing", "Converting to a dot matrix", "image"),
    ThinkingVerb("Vectorizing", "Converting to vector graphics", "image"),
    ThinkingVerb("Pixelating", "Displaying as visible pixels", "image"),
    ThinkingVerb("Upscaling", "Increasing the size or quality", "image"),
    ThinkingVerb("Downsampling", "Reducing the number of samples", "image"),
    ThinkingVerb("Enhancing", "Intensifying or improving quality", "image"),
    ThinkingVerb("Retouching", "Improving by making slight changes", "image"),
    ThinkingVerb("Airbrushing", "Altering using an airbrush", "image"),
    ThinkingVerb("Photoshopping", "Editing using image software", "image"),

    # ===== LEARNING / GROWING =====
    ThinkingVerb("Learning", "Gaining knowledge or skill", "learning"),
    ThinkingVerb("Absorbing", "Taking in information readily", "learning"),
    ThinkingVerb("Assimilating", "Taking in and fully understanding", "learning"),
    ThinkingVerb("Acquiring", "Coming to have a skill", "learning"),
    ThinkingVerb("Grasping", "Seizing and holding firmly; understanding", "learning"),
    ThinkingVerb("Comprehending", "Grasping mentally; understanding", "learning"),
    ThinkingVerb("Understanding", "Perceiving the intended meaning", "learning"),
    ThinkingVerb("Fathoming", "Understanding after much thought", "learning"),
    ThinkingVerb("Appreciating", "Recognizing the full worth of", "learning"),
    ThinkingVerb("Recognizing", "Identifying from previous experience", "learning"),
    ThinkingVerb("Realizing", "Becoming fully aware of", "learning"),
    ThinkingVerb("Discovering", "Finding something unexpectedly", "learning"),
    ThinkingVerb("Uncovering", "Removing a cover to reveal", "learning"),
    ThinkingVerb("Revealing", "Making previously unknown known", "learning"),
    ThinkingVerb("Unveiling", "Removing a veil or covering from", "learning"),
    ThinkingVerb("Exposing", "Making something visible", "learning"),
    ThinkingVerb("Awakening", "Becoming aware of something", "learning"),
    ThinkingVerb("Enlightening", "Giving spiritual or intellectual insight", "learning"),
    ThinkingVerb("Educating", "Giving intellectual or moral instruction", "learning"),
    ThinkingVerb("Training", "Teaching a particular skill", "learning"),
    ThinkingVerb("Practicing", "Performing repeatedly to acquire skill", "learning"),
    ThinkingVerb("Drilling", "Instructing by repetition", "learning"),
    ThinkingVerb("Exercising", "Using or applying a faculty", "learning"),
    ThinkingVerb("Honing", "Refining or perfecting over time", "learning"),
    ThinkingVerb("Developing", "Growing or causing to grow", "learning"),
    ThinkingVerb("Evolving", "Developing gradually", "learning"),
    ThinkingVerb("Maturing", "Becoming fully developed", "learning"),
    ThinkingVerb("Ripening", "Becoming ripe or ready", "learning"),
    ThinkingVerb("Blossoming", "Developing or maturing", "learning"),
    ThinkingVerb("Flourishing", "Growing vigorously", "learning"),

    # ===== SOLVING / FIXING =====
    ThinkingVerb("Solving", "Finding an answer to a problem", "solving"),
    ThinkingVerb("Resolving", "Settling or finding a solution to", "solving"),
    ThinkingVerb("Addressing", "Thinking about and beginning to deal with", "solving"),
    ThinkingVerb("Tackling", "Making determined efforts to deal with", "solving"),
    ThinkingVerb("Handling", "Managing a situation or problem", "solving"),
    ThinkingVerb("Managing", "Being in charge of; handling", "solving"),
    ThinkingVerb("Coping", "Dealing effectively with difficulty", "solving"),
    ThinkingVerb("Overcoming", "Succeeding in dealing with", "solving"),
    ThinkingVerb("Conquering", "Successfully overcoming", "solving"),
    ThinkingVerb("Vanquishing", "Defeating thoroughly", "solving"),
    ThinkingVerb("Defeating", "Winning victory over", "solving"),
    ThinkingVerb("Beating", "Defeating in a competition", "solving"),
    ThinkingVerb("Cracking", "Finding solution to", "solving"),
    ThinkingVerb("Breaking", "Solving or deciphering", "solving"),
    ThinkingVerb("Unlocking", "Making accessible or available", "solving"),
    ThinkingVerb("Unblocking", "Removing an obstruction from", "solving"),
    ThinkingVerb("Clearing", "Removing obstructions from", "solving"),
    ThinkingVerb("Troubleshooting", "Tracing and correcting faults", "solving"),
    ThinkingVerb("Diagnosing", "Identifying the nature of a problem", "solving"),
    ThinkingVerb("Remedying", "Setting right an undesirable situation", "solving"),
    ThinkingVerb("Rectifying", "Putting right; correcting", "solving"),
    ThinkingVerb("Correcting", "Putting right an error", "solving"),
    ThinkingVerb("Amending", "Making minor changes to improve", "solving"),
    ThinkingVerb("Revising", "Reconsider and alter", "solving"),
    ThinkingVerb("Reworking", "Making changes to improve", "solving"),
    ThinkingVerb("Overhauling", "Analyzing and improving", "solving"),
    ThinkingVerb("Renovating", "Restoring to good condition", "solving"),
    ThinkingVerb("Restoring", "Returning to original condition", "solving"),
    ThinkingVerb("Recovering", "Returning to normal state", "solving"),
    ThinkingVerb("Healing", "Causing to become sound or healthy", "solving"),
]

# Index verbs by category for fast lookup
VERBS_BY_CATEGORY = {}
for verb in THINKING_VERBS_WITH_DEFINITIONS:
    cat = verb.category
    if cat not in VERBS_BY_CATEGORY:
        VERBS_BY_CATEGORY[cat] = []
    VERBS_BY_CATEGORY[cat].append(verb)

# Route-specific verb categories
ROUTE_VERB_MAP = {
    "chat": ["processing", "communicating", "playful", "loyal"],
    "roleplay": ["creating", "playful", "confident", "communicating"],
    "code": ["coding", "analyzing", "solving", "creating"],
    "reason": ["analyzing", "processing", "solving", "learning"],
    "image": ["image", "creating", "processing"],
    "improve": ["analyzing", "guardian", "loyal", "solving"],
}


def get_thinking_verb(route: Optional[str] = None, category: Optional[str] = None, with_definition: bool = False) -> Tuple[str, str] | str:
    """
    Get a random thinking verb, optionally filtered by route or category.

    Args:
        route: The type of request (chat, code, roleplay, etc.)
        category: Specific category (confident, playful, coding, etc.)
        with_definition: If True, return tuple of (verb, definition)

    Returns:
        Verb string, or tuple of (verb, definition) if with_definition=True
    """
    if category and category in VERBS_BY_CATEGORY:
        verb_obj = random.choice(VERBS_BY_CATEGORY[category])
    elif route and route in ROUTE_VERB_MAP:
        categories = ROUTE_VERB_MAP[route]
        category = random.choice(categories)
        verb_obj = random.choice(VERBS_BY_CATEGORY.get(category, THINKING_VERBS_WITH_DEFINITIONS))
    else:
        verb_obj = random.choice(THINKING_VERBS_WITH_DEFINITIONS)

    if with_definition:
        return (verb_obj.verb, verb_obj.definition)
    return verb_obj.verb


def get_verb_with_ellipsis(route: Optional[str] = None) -> str:
    """Get a thinking verb with trailing ellipsis for display"""
    return f"{get_thinking_verb(route)}..."


def get_verb_with_definition(route: Optional[str] = None) -> str:
    """Get a thinking verb with its definition formatted for display"""
    verb, definition = get_thinking_verb(route, with_definition=True)
    return f"{verb} ({definition})"


def get_loading_sequence(count: int = 5, route: Optional[str] = None) -> list:
    """
    Get a sequence of verbs for an animated loading display.

    Args:
        count: Number of verbs to return
        route: Optional route to filter verbs

    Returns:
        List of (verb, definition) tuples
    """
    seen = set()
    verbs = []
    attempts = 0
    while len(verbs) < count and attempts < 100:
        verb_obj = None
        if route and route in ROUTE_VERB_MAP:
            categories = ROUTE_VERB_MAP[route]
            category = random.choice(categories)
            verb_obj = random.choice(VERBS_BY_CATEGORY.get(category, THINKING_VERBS_WITH_DEFINITIONS))
        else:
            verb_obj = random.choice(THINKING_VERBS_WITH_DEFINITIONS)

        if verb_obj.verb not in seen:
            seen.add(verb_obj.verb)
            verbs.append((verb_obj.verb, verb_obj.definition))
        attempts += 1
    return verbs


def get_all_verbs() -> list:
    """Get all verbs as list of (verb, definition, category) tuples"""
    return [(v.verb, v.definition, v.category) for v in THINKING_VERBS_WITH_DEFINITIONS]


def get_categories() -> list:
    """Get all available categories"""
    return sorted(VERBS_BY_CATEGORY.keys())


def count_verbs() -> dict:
    """Get count of verbs per category"""
    return {cat: len(verbs) for cat, verbs in VERBS_BY_CATEGORY.items()}


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2 or sys.argv[1] == "help":
        print("SAM Thinking Verbs - Comprehensive Collection")
        print(f"\nTotal verbs: {len(THINKING_VERBS_WITH_DEFINITIONS)}")
        print(f"Categories: {len(VERBS_BY_CATEGORY)}")
        print("\nUsage:")
        print("  python thinking_verbs.py demo       # Show random samples")
        print("  python thinking_verbs.py count      # Count per category")
        print("  python thinking_verbs.py list       # List all verbs")
        print("  python thinking_verbs.py category X # List verbs in category X")
        print("  python thinking_verbs.py route X    # Show verbs for route X")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "demo":
        print("SAM Thinking Verbs Demo")
        print("=" * 60)
        print(f"\nTotal verbs available: {len(THINKING_VERBS_WITH_DEFINITIONS)}")
        print(f"Categories: {len(VERBS_BY_CATEGORY)}\n")

        print("Random samples by route:")
        for route in ROUTE_VERB_MAP.keys():
            print(f"\n{route.upper()}:")
            for _ in range(3):
                verb, defn = get_thinking_verb(route, with_definition=True)
                print(f"  {verb}... ({defn})")

        print("\n" + "=" * 60)
        print("\nLoading sequence example (code route):")
        for verb, defn in get_loading_sequence(5, "code"):
            print(f"  {verb}... - {defn}")

    elif cmd == "count":
        print("Verb counts by category:")
        print("=" * 40)
        counts = count_verbs()
        total = 0
        for cat in sorted(counts.keys()):
            print(f"  {cat}: {counts[cat]}")
            total += counts[cat]
        print("=" * 40)
        print(f"  TOTAL: {total}")

    elif cmd == "list":
        print("All Thinking Verbs")
        print("=" * 70)
        for verb, defn, cat in sorted(get_all_verbs()):
            print(f"[{cat:12}] {verb:20} - {defn}")

    elif cmd == "category":
        if len(sys.argv) < 3:
            print(f"Available categories: {', '.join(get_categories())}")
        else:
            cat = sys.argv[2]
            if cat in VERBS_BY_CATEGORY:
                print(f"Verbs in '{cat}' category:")
                print("=" * 60)
                for v in VERBS_BY_CATEGORY[cat]:
                    print(f"  {v.verb:25} - {v.definition}")
            else:
                print(f"Unknown category: {cat}")
                print(f"Available: {', '.join(get_categories())}")

    elif cmd == "route":
        if len(sys.argv) < 3:
            print(f"Available routes: {', '.join(ROUTE_VERB_MAP.keys())}")
        else:
            route = sys.argv[2]
            if route in ROUTE_VERB_MAP:
                print(f"Verbs for '{route}' route (categories: {ROUTE_VERB_MAP[route]}):")
                print("=" * 60)
                for _ in range(10):
                    verb, defn = get_thinking_verb(route, with_definition=True)
                    print(f"  {verb}... - {defn}")
            else:
                print(f"Unknown route: {route}")
                print(f"Available: {', '.join(ROUTE_VERB_MAP.keys())}")

    else:
        print(f"Unknown command: {cmd}")
        print("Try: python thinking_verbs.py help")
