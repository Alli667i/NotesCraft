# import json
# import re
#
# # from process_to_word_02 import generate_word_file
# from app_version_01 import process_to_word_02
#
#
# def validate_and_fix_json(ai_output: str):
#     """
#     Validates and fixes AI JSON output.
#     Handles:
#     - Proper JSON directly (no regex needed)
#     - Broken JSON with stray characters
#     - Multi-line text fields
#     """
#
#     # Step 1: Try parsing directly
#     try:
#         parsed = json.loads(ai_output)
#         # Ensure it’s always a list of objects
#         if isinstance(parsed, dict):
#             return [parsed]
#         elif isinstance(parsed, list):
#             return parsed
#     except Exception:
#         pass  # fall back to regex repair if json.loads fails
#
#     # Step 2: Cleanup obvious junk
#     cleaned = re.sub(r'[\n\s]*[-]+[\s,]*', '', ai_output)
#
#     # Step 3: Regex to capture "type" and "text"
#     pattern = r'"type"\s*:\s*"([^"]+)"\s*,\s*"text"\s*:\s*"([\s\S]*?)"(?=\s*(?:,\s*"?type"?\s*:|\s*\}))'
#     matches = re.findall(pattern, cleaned)
#
#     if not matches:
#         return {
#             "error": "No valid objects found. AI output too malformed.",
#             "original_output": ai_output
#         }
#
#     # Step 4: Build list of dicts (no manual escaping!)
#     result = []
#     for typ, text in matches:
#         result.append({"type": typ.strip(), "text": text.strip()})
#
#     return result
#
# from process_to_word_02 import generate_word_file
#
# fixed_text = [{'type': 'heading', 'text': 'Ten Principles of Economics'}, {'type': 'subheading', 'text': 'Understanding the Economy: Household vs. Society'}, {'type': 'paragraph', 'text': 'The word "economy" comes from the Greek word "oikonomos," meaning "one who manages a household." This origin highlights a key similarity: both households and societies face the challenge of managing resources.'}, {'type': 'bullet', 'text': 'A **household** must decide who does which tasks (e.g., cooking, laundry) and how its limited resources (e.g., food, TV access) are distributed among members, considering their abilities, efforts, and desires.'}, {'type': 'bullet', 'text': 'Similarly, a **society** must decide what jobs need to be done (e.g., growing food, making clothing, designing software) and who will do them. After resources (like people, land, buildings, machines) are allocated to these jobs, society must also decide how to distribute the goods and services produced (e.g., who consumes luxury items versus basic necessities).'}, {'type': 'subheading', 'text': 'The Fundamental Problem: Scarcity'}, {'type': 'paragraph', 'text': 'The management of societys resources is critically important because these resources are limited. This fundamental limitation is known as scarcity.'}, {'type': 'bullet', 'text': '**Scarcity means** that society has limited resources and, therefore, cannot produce all the goods and services that people wish to have.'}, {'type': 'bullet', 'text': 'Just as an individual household member cannot get everything they want, each person in a society cannot attain the highest standard of living they might desire due to resource limitations.'}, {'type': 'subheading', 'text': 'What Do Economists Study?'}, {'type': 'paragraph', 'text': 'Economics is defined as the study of how society manages its scarce resources. In most societies, resources are not allocated by a single powerful figure but through the combined actions of millions of households and firms.'}, {'type': 'bullet', 'text': '**Individual Decisions:** Economists study how people make choices, such as how much they work, what they buy, how much they save, and how they invest their savings.'}, {'type': 'bullet', 'text': '**Interactions Among People:** They also examine how people interact, for example, how buyers and sellers collectively determine the price and quantity of goods sold in a market.'}, {'type': 'bullet', 'text': '**Economy as a Whole:** Furthermore, economists analyze broader forces and trends that affect the entire economy, including:The growth in average income.The proportion of the population that is unemployed.The rate at which prices are rising (inflation).'}, {'type': 'subheading', 'text': 'About This Chapter'}, {'type': 'paragraph', 'text': 'This chapter introduces Ten Principles of Economics, offering a foundational overview of the subject. These ideas will be explored in greater depth in subsequent chapters.'}, {'type': 'subheading', 'text': 'Key Definitions'}, {'type': 'bullet', 'text': '**Scarcity:** The limited nature of societys resources.'}, {'type': 'bullet', 'text': '**Economics:** The study of how society manages its scarce resources.'}, {'type': 'heading', 'text': 'How People Make Decisions'}, {'type': 'subheading', 'text': 'Introduction to Economic Decision Making'}, {'type': 'paragraph', 'text': 'An economy is essentially a collection of people interacting and making choices in their daily lives. Whether we look at a local city, a country, or the entire world, the way an economy behaves is a direct reflection of the decisions made by the individuals within it. Therefore, to understand how an economy works, we first need to study how individuals make their decisions.'}, {'type': 'subheading', 'text': 'Key Definitions'}, {'type': 'bullet', 'text': 'Economy: A group of people dealing with one another as they go about their lives, whose collective behavior reflects the individual decisions made by its members.'}, {'type': 'heading', 'text': 'Principle 1: People Face Tradeoffs'}, {'type': 'paragraph', 'text': 'The core idea of economics is that to get one thing we like, we usually have to give up something else we also like. This concept is often summarized by the saying, Theres no such thing as a free lunch. Every decision involves choosing one option and letting go of another.'}, {'type': 'subheading', 'text': 'Tradeoffs for Students'}, {'type': 'paragraph', 'text': 'Consider a student deciding how to use their time, which is a valuable and limited resource.'}, {'type': 'bullet', 'text': 'If she studies economics for an hour, she gives up an hour she could have spent studying psychology.'}, {'type': 'bullet', 'text': 'If she spends an hour studying, she gives up an hour she could have used for napping, bike riding, watching TV, or working for extra money.'}, {'type': 'subheading', 'text': 'Tradeoffs for Families'}, {'type': 'paragraph', 'text': 'Families also face tradeoffs when deciding how to spend their income.'}, {'type': 'bullet', 'text': 'They can buy essentials like food and clothing, or luxuries like a family vacation.'}, {'type': 'bullet', 'text': 'They can choose to spend money now or save it for future goals like retirement or their childrens college education.'}, {'type': 'bullet', 'text': 'Every dollar spent on one item means one less dollar available for another item.'}, {'type': 'subheading', 'text': 'Key Definitions'}, {'type': 'bullet', 'text': 'Tradeoff: The act of giving up one thing in order to gain another, often considered as a balance between two desirable but incompatible features.'}]
#
# generate_word_file(fixed_text,"Ch15")
# # process_to_word_02.generate_word_file(fixed_text,"Ch12")
#
#
#

notes_gen = [
  {"type": "heading", "text": "Chapter 1: Ten Principles of Economics"},

  {"type": "subheading", "text": "Introduction"},
  {"type": "paragraph", "text": "Economics studies how societies with limited resources decide what to produce, how to produce it, and who consumes what. It is similar to managing a household where choices must be made about work, resources, and rewards."},
  {"type": "bullet", "text": "Scarcity means resources are limited while wants are unlimited."},
  {"type": "bullet", "text": "Economists study decision-making, market interactions, and big trends like growth, unemployment, and inflation."},
  {"type": "bullet", "text": "This chapter introduces 10 key principles of economics."},

  {"type": "subheading", "text": "Principle 1: People Face Trade-offs"},
  {"type": "bullet", "text": "Choosing one thing means giving up another due to limited resources."},
  {"type": "bullet", "text": "Examples: A student dividing time between subjects; a family dividing income between food, clothes, and vacations."},
  {"type": "bullet", "text": "Society faces choices such as 'guns vs. butter' (defense vs. consumer goods)."},
  {"type": "bullet", "text": "Efficiency = getting the most out of resources; Equality = fair distribution. Policies often balance the two."},

  {"type": "subheading", "text": "Principle 2: The Cost of Something Is What You Give Up to Get It"},
  {"type": "bullet", "text": "Opportunity cost = the value of the next best alternative you give up."},
  {"type": "bullet", "text": "Example: The true cost of college includes not just tuition and books but also lost income from not working."},
  {"type": "bullet", "text": "Athletes may skip college because the opportunity cost (forgone millions) is too high."},

  {"type": "subheading", "text": "Principle 3: Rational People Think at the Margin"},
  {"type": "bullet", "text": "Rational people make decisions by comparing marginal benefits and marginal costs."},
  {"type": "bullet", "text": "Marginal change = small, step-by-step adjustment to a plan."},
  {"type": "bullet", "text": "Example: Airlines sell last-minute tickets below average cost because marginal cost is nearly zero."},
  {"type": "bullet", "text": "Water vs. diamonds: Water is essential but plentiful (low marginal benefit). Diamonds are rare (high marginal benefit)."},
  {"type": "bullet", "text": "Decision rule: Take an action if marginal benefit exceeds marginal cost."},

  {"type": "subheading", "text": "Principle 4: People Respond to Incentives"},
  {"type": "bullet", "text": "Incentive = something that motivates people to act (reward or punishment)."},
  {"type": "bullet", "text": "Higher prices → buyers consume less, sellers produce more."},
  {"type": "bullet", "text": "Gasoline tax encourages smaller cars, carpooling, and public transport."},
  {"type": "bullet", "text": "Seat belts improve safety but may lead drivers to drive faster, increasing accidents (unintended consequences)."},
  {"type": "bullet", "text": "Real-world examples: Fuel price increases led to small car sales, higher transit use, and changes in lifestyle."},

  {"type": "subheading", "text": "Principle 5: Trade Can Make Everyone Better Off"},
  {"type": "bullet", "text": "Trade is not win-lose; both sides can benefit."},
  {"type": "bullet", "text": "Families and countries gain by specializing in what they do best and trading for the rest."},
  {"type": "bullet", "text": "Trade allows greater variety and lower costs."},

  {"type": "subheading", "text": "Principle 6: Markets Are Usually a Good Way to Organize Economic Activity"},
  {"type": "bullet", "text": "Market economy = decisions made by households and firms, not central planners."},
  {"type": "bullet", "text": "Adam Smith’s 'invisible hand': prices guide buyers and sellers toward efficient outcomes."},
  {"type": "bullet", "text": "Policies that block prices (e.g., rent control, heavy taxes) disrupt efficiency."},

  {"type": "subheading", "text": "Principle 7: Governments Can Sometimes Improve Market Outcomes"},
  {"type": "bullet", "text": "Governments enforce rules and protect property rights so markets work properly."},
  {"type": "bullet", "text": "They correct market failures such as externalities (e.g., pollution) and monopolies."},
  {"type": "bullet", "text": "They may also act to improve equality, even if it reduces efficiency."},

  {"type": "subheading", "text": "Key Definitions"},
  {"type": "bullet", "text": "Scarcity → limited nature of society’s resources."},
  {"type": "bullet", "text": "Economics → study of how society manages scarce resources."},
  {"type": "bullet", "text": "Efficiency → getting the most from scarce resources."},
  {"type": "bullet", "text": "Equality → fair distribution of resources."},
  {"type": "bullet", "text": "Opportunity cost → what must be given up to obtain something."},
  {"type": "bullet", "text": "Rational people → systematically do the best they can with available opportunities."},
  {"type": "bullet", "text": "Marginal change → small incremental adjustment to a decision."},
  {"type": "bullet", "text": "Incentive → something that motivates behavior."},
  {"type": "bullet", "text": "Market economy → system where households and firms interact through markets."},
  {"type": "bullet", "text": "Property rights → ability to own and control resources."},
  {"type": "bullet", "text": "Market failure → when markets fail to allocate resources efficiently."},
  {"type": "bullet", "text": "Externality → impact of one person’s actions on others."}
]

from process_to_word_02 import generate_word_file

generate_word_file(notes_gen,"Ch_01")