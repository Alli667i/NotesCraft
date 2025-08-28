import json
import re

# from process_to_word_02 import generate_word_file
from app_version_01 import process_to_word_02


def validate_and_fix_json(ai_output: str):
    """
    Validates and fixes AI JSON output.
    Handles:
    - Proper JSON directly (no regex needed)
    - Broken JSON with stray characters
    - Multi-line text fields
    """

    # Step 1: Try parsing directly
    try:
        parsed = json.loads(ai_output)
        # Ensure it’s always a list of objects
        if isinstance(parsed, dict):
            return [parsed]
        elif isinstance(parsed, list):
            return parsed
    except Exception:
        pass  # fall back to regex repair if json.loads fails

    # Step 2: Cleanup obvious junk
    cleaned = re.sub(r'[\n\s]*[-]+[\s,]*', '', ai_output)

    # Step 3: Regex to capture "type" and "text"
    pattern = r'"type"\s*:\s*"([^"]+)"\s*,\s*"text"\s*:\s*"([\s\S]*?)"(?=\s*(?:,\s*"?type"?\s*:|\s*\}))'
    matches = re.findall(pattern, cleaned)

    if not matches:
        return {
            "error": "No valid objects found. AI output too malformed.",
            "original_output": ai_output
        }

    # Step 4: Build list of dicts (no manual escaping!)
    result = []
    for typ, text in matches:
        result.append({"type": typ.strip(), "text": text.strip()})

    return result

from process_to_word_02 import generate_word_file

fixed_text = [{'type': 'heading', 'text': 'Ten Principles of Economics'}, {'type': 'subheading', 'text': 'Understanding the Economy: Household vs. Society'}, {'type': 'paragraph', 'text': 'The word "economy" comes from the Greek word "oikonomos," meaning "one who manages a household." This origin highlights a key similarity: both households and societies face the challenge of managing resources.'}, {'type': 'bullet', 'text': 'A **household** must decide who does which tasks (e.g., cooking, laundry) and how its limited resources (e.g., food, TV access) are distributed among members, considering their abilities, efforts, and desires.'}, {'type': 'bullet', 'text': 'Similarly, a **society** must decide what jobs need to be done (e.g., growing food, making clothing, designing software) and who will do them. After resources (like people, land, buildings, machines) are allocated to these jobs, society must also decide how to distribute the goods and services produced (e.g., who consumes luxury items versus basic necessities).'}, {'type': 'subheading', 'text': 'The Fundamental Problem: Scarcity'}, {'type': 'paragraph', 'text': 'The management of societys resources is critically important because these resources are limited. This fundamental limitation is known as scarcity.'}, {'type': 'bullet', 'text': '**Scarcity means** that society has limited resources and, therefore, cannot produce all the goods and services that people wish to have.'}, {'type': 'bullet', 'text': 'Just as an individual household member cannot get everything they want, each person in a society cannot attain the highest standard of living they might desire due to resource limitations.'}, {'type': 'subheading', 'text': 'What Do Economists Study?'}, {'type': 'paragraph', 'text': 'Economics is defined as the study of how society manages its scarce resources. In most societies, resources are not allocated by a single powerful figure but through the combined actions of millions of households and firms.'}, {'type': 'bullet', 'text': '**Individual Decisions:** Economists study how people make choices, such as how much they work, what they buy, how much they save, and how they invest their savings.'}, {'type': 'bullet', 'text': '**Interactions Among People:** They also examine how people interact, for example, how buyers and sellers collectively determine the price and quantity of goods sold in a market.'}, {'type': 'bullet', 'text': '**Economy as a Whole:** Furthermore, economists analyze broader forces and trends that affect the entire economy, including:The growth in average income.The proportion of the population that is unemployed.The rate at which prices are rising (inflation).'}, {'type': 'subheading', 'text': 'About This Chapter'}, {'type': 'paragraph', 'text': 'This chapter introduces Ten Principles of Economics, offering a foundational overview of the subject. These ideas will be explored in greater depth in subsequent chapters.'}, {'type': 'subheading', 'text': 'Key Definitions'}, {'type': 'bullet', 'text': '**Scarcity:** The limited nature of societys resources.'}, {'type': 'bullet', 'text': '**Economics:** The study of how society manages its scarce resources.'}, {'type': 'heading', 'text': 'How People Make Decisions'}, {'type': 'subheading', 'text': 'Introduction to Economic Decision Making'}, {'type': 'paragraph', 'text': 'An economy is essentially a collection of people interacting and making choices in their daily lives. Whether we look at a local city, a country, or the entire world, the way an economy behaves is a direct reflection of the decisions made by the individuals within it. Therefore, to understand how an economy works, we first need to study how individuals make their decisions.'}, {'type': 'subheading', 'text': 'Key Definitions'}, {'type': 'bullet', 'text': 'Economy: A group of people dealing with one another as they go about their lives, whose collective behavior reflects the individual decisions made by its members.'}, {'type': 'heading', 'text': 'Principle 1: People Face Tradeoffs'}, {'type': 'paragraph', 'text': 'The core idea of economics is that to get one thing we like, we usually have to give up something else we also like. This concept is often summarized by the saying, Theres no such thing as a free lunch. Every decision involves choosing one option and letting go of another.'}, {'type': 'subheading', 'text': 'Tradeoffs for Students'}, {'type': 'paragraph', 'text': 'Consider a student deciding how to use their time, which is a valuable and limited resource.'}, {'type': 'bullet', 'text': 'If she studies economics for an hour, she gives up an hour she could have spent studying psychology.'}, {'type': 'bullet', 'text': 'If she spends an hour studying, she gives up an hour she could have used for napping, bike riding, watching TV, or working for extra money.'}, {'type': 'subheading', 'text': 'Tradeoffs for Families'}, {'type': 'paragraph', 'text': 'Families also face tradeoffs when deciding how to spend their income.'}, {'type': 'bullet', 'text': 'They can buy essentials like food and clothing, or luxuries like a family vacation.'}, {'type': 'bullet', 'text': 'They can choose to spend money now or save it for future goals like retirement or their childrens college education.'}, {'type': 'bullet', 'text': 'Every dollar spent on one item means one less dollar available for another item.'}, {'type': 'subheading', 'text': 'Key Definitions'}, {'type': 'bullet', 'text': 'Tradeoff: The act of giving up one thing in order to gain another, often considered as a balance between two desirable but incompatible features.'}]

generate_word_file(fixed_text,"Ch15")
# process_to_word_02.generate_word_file(fixed_text,"Ch12")



