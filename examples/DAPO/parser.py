"""Math answer extraction utilities for DAPO reward computation.

This module provides functions to extract answers from model outputs,
specifically for math problems with boxed answers.
"""

import re

from word2number import w2n


def _fix_fracs(string):
    """Fix LaTeX fraction formatting."""
    substrs = string.split("\\frac")
    new_str = substrs[0]
    if len(substrs) > 1:
        substrs = substrs[1:]
        for substr in substrs:
            new_str += "\\frac"
            if len(substr) > 0 and substr[0] == "{":
                new_str += substr
            else:
                try:
                    assert len(substr) >= 2
                except:
                    return string
                a = substr[0]
                b = substr[1]
                if b != "{":
                    if len(substr) > 2:
                        post_substr = substr[2:]
                        new_str += "{" + a + "}{" + b + "}" + post_substr
                    else:
                        new_str += "{" + a + "}{" + b + "}"
                else:
                    if len(substr) > 2:
                        post_substr = substr[2:]
                        new_str += "{" + a + "}" + b + post_substr
                    else:
                        new_str += "{" + a + "}" + b
    string = new_str
    return string


def _fix_a_slash_b(string):
    """Convert a/b format to LaTeX fraction."""
    if len(string.split("/")) != 2:
        return string
    a = string.split("/")[0]
    b = string.split("/")[1]
    try:
        if "sqrt" not in a:
            a = int(a)
        if "sqrt" not in b:
            b = int(b)
        assert string == f"{a}/{b}"
        new_string = "\\frac{" + str(a) + "}{" + str(b) + "}"
        return new_string
    except:
        return string


def _fix_sqrt(string):
    """Fix LaTeX sqrt formatting."""
    _string = re.sub(r"\\sqrt(\w+)", r"\\sqrt{\1}", string)
    return _string


def convert_word_number(text: str) -> str:
    """Convert word numbers to digits."""
    try:
        text = str(w2n.word_to_num(text))
    except:
        pass
    return text


# Units list for stripping from answers
UNIT_TEXTS = [
    "east",
    "degree",
    "mph",
    "kmph",
    "ft",
    "m sqaure",
    " m east",
    "sq m",
    "deg",
    "mile",
    "q .",
    "monkey",
    "prime",
    "ratio",
    "profit of rs",
    "rd",
    "o",
    "gm",
    "p . m",
    "lb",
    "tile",
    "per",
    "dm",
    "lt",
    "gain",
    "ab",
    "way",
    "west",
    "a .",
    "b .",
    "c .",
    "d .",
    "e .",
    "f .",
    "g .",
    "h .",
    "t",
    "a",
    "h",
    "no change",
    "men",
    "soldier",
    "pie",
    "bc",
    "excess",
    "st",
    "inches",
    "noon",
    "percent",
    "by",
    "gal",
    "kmh",
    "c",
    "acre",
    "rise",
    "a . m",
    "th",
    "π r 2",
    "sq",
    "mark",
    "l",
    "toy",
    "coin",
    "sq . m",
    "gallon",
    "° f",
    "profit",
    "minw",
    "yr",
    "women",
    "feet",
    "am",
    "pm",
    "hr",
    "cu cm",
    "square",
    "v â € ™",
    "are",
    "rupee",
    "rounds",
    "cubic",
    "cc",
    "mtr",
    "s",
    "ohm",
    "number",
    "kmph",
    "day",
    "hour",
    "minute",
    "min",
    "second",
    "man",
    "woman",
    "sec",
    "cube",
    "mt",
    "sq inch",
    "mp",
    "∏ cm ³",
    "hectare",
    "more",
    "sec",
    "unit",
    "cu . m",
    "cm 2",
    "rs .",
    "rs",
    "kg",
    "g",
    "month",
    "km",
    "m",
    "cm",
    "mm",
    "apple",
    "liter",
    "loss",
    "yard",
    "pure",
    "year",
    "increase",
    "decrease",
    "d",
    "less",
    "Surface",
    "litre",
    "pi sq m",
    "s .",
    "metre",
    "meter",
    "inch",
]
# Add plural forms
UNIT_TEXTS.extend([t + "s" for t in UNIT_TEXTS])


def strip_string(string, skip_unit=False):
    """Clean and normalize a math answer string."""
    string = str(string).strip()
    string = string.replace("\n", "")
    string = string.rstrip(".")
    string = string.replace("\\!", "")

    # Matrix normalization
    string = re.sub(r"\\begin\{array\}\{.*?\}", r"\\begin{pmatrix}", string)
    string = re.sub(r"\\end\{array\}", r"\\end{pmatrix}", string)
    string = string.replace("bmatrix", "pmatrix")

    # LaTeX normalization
    string = string.replace("tfrac", "frac")
    string = string.replace("dfrac", "frac")
    string = string.replace("\\neq", "\\ne").replace("\\leq", "\\le").replace("\\geq", "\\ge")
    string = string.replace("\\left", "")
    string = string.replace("\\right", "")
    string = string.replace("\\{", "{")
    string = string.replace("\\}", "}")

    # Remove text units
    _string = re.sub(r"\\text{.*?}$", "", string).strip()
    if _string != "" and _string != string:
        string = _string

    if not skip_unit:
        for _ in range(2):
            for unit_text in UNIT_TEXTS:
                _string = re.sub(r"(^|\W)" + unit_text + r"($|\W)", r"\1\2", string)
                if _string != "":
                    string = _string

    # Remove degree symbols
    string = string.replace("^{\\circ}", "")
    string = string.replace("^\\circ", "")

    # Remove currency symbols
    string = string.replace("\\$", "")
    string = string.replace("$", "")
    string = string.replace("\\(", "").replace("\\)", "")

    # Convert word numbers
    string = convert_word_number(string)

    # Clean text formatting
    string = re.sub(r"\\text\{(.*?)\}", r"\1", string)
    for key in ["x=", "y=", "z=", "x\\in", "y\\in", "z\\in", "x\\to", "y\\to", "z\\to"]:
        string = string.replace(key, "")
    string = string.replace("\\emptyset", r"{}")
    string = string.replace("(-\\infty,\\infty)", "\\mathbb{R}")

    # Remove percentage
    string = string.replace("\\%", "")
    string = string.replace(r"\%", "")
    string = string.replace("%", "")

    # Decimal normalization
    string = string.replace(" .", " 0.")
    string = string.replace("{.", "{0.")

    # Remove enclosing brackets for simple alphanumeric
    if (
        string.startswith("{")
        and string.endswith("}")
        and string.isalnum()
        or string.startswith("(")
        and string.endswith(")")
        and string.isalnum()
        or string.startswith("[")
        and string.endswith("]")
        and string.isalnum()
    ):
        string = string[1:-1]

    # Infinity normalization
    string = string.replace("infinity", "\\infty")
    if "\\infty" not in string:
        string = string.replace("inf", "\\infty")
    string = string.replace("+\\inity", "\\infty")

    string = string.replace("and", "")
    string = string.replace("\\mathbf", "")
    string = re.sub(r"\\mbox{.*?}", "", string)
    string.replace("'", "")
    string.replace('"', "")

    if "j" in string and "i" not in string:
        string = string.replace("j", "i")

    # Clean trailing zeros
    string = re.sub(r"(\d+)\.0*([^\d])", r"\1\2", string)
    string = re.sub(r"(\d+)\.0*$", r"\1", string)

    if len(string) == 0:
        return string
    if string[0] == ".":
        string = "0" + string

    # Handle simple equations
    if len(string.split("=")) == 2:
        if len(string.split("=")[0]) <= 2:
            string = string.split("=")[1]

    string = _fix_sqrt(string)
    string = string.replace(" ", "")
    string = _fix_fracs(string)
    string = _fix_a_slash_b(string)

    return string


def choice_answer_clean(pred: str):
    """Clean multiple choice answer."""
    pred = pred.strip("\n")
    direct_answer_trigger = ("choice is", "answer is")

    # Check for ICL pattern
    ICL = False
    for trigger in direct_answer_trigger:
        if pred.count(trigger) > 1:
            ICL = True
    if ICL:
        pred = pred.split("\n\n")[0]

    # Split by trigger
    preds = re.split("|".join(direct_answer_trigger), pred)
    if len(preds) > 1:
        answer_flag = True
        pred = preds[-1]
    else:
        answer_flag = False

    pred = pred.strip("\n").rstrip(".").rstrip("/").strip(" ").lstrip(":")

    # Extract choice letters
    tmp = re.findall(r"\b(A|B|C|D|E)\b", pred.upper())
    if tmp:
        pred = tmp
    else:
        pred = [pred.strip().strip(".")]

    if len(pred) == 0:
        pred = ""
    else:
        if answer_flag:
            pred = pred[0]
        else:
            pred = pred[-1]

    pred = pred.rstrip(".").rstrip("/")
    return pred


def extract_answer(pred_str, data_name, use_last_number=True):
    """Extract the answer from model prediction string.

    Args:
        pred_str: The model's prediction string
        data_name: The dataset name (e.g., 'math', 'gsm8k')
        use_last_number: Whether to use the last number as fallback

    Returns:
        The extracted answer string
    """
    pred_str = pred_str.replace("\u043a\u0438", "")

    # Multiple choice datasets
    if data_name in ["mmlu_stem", "sat_math", "aqua", "gaokao2023"]:
        return choice_answer_clean(pred_str)

    # Try different extraction patterns
    if "final answer is $" in pred_str and "$. I hope" in pred_str:
        # minerva_math format
        tmp = pred_str.split("final answer is $", 1)[1]
        pred = tmp.split("$. I hope", 1)[0].strip()
    elif "boxed" in pred_str:
        # LaTeX boxed format
        ans = pred_str.split("boxed")[-1]
        if len(ans) == 0:
            return ""
        elif ans[0] == "{":
            stack = 1
            a = ""
            for c in ans[1:]:
                if c == "{":
                    stack += 1
                    a += c
                elif c == "}":
                    stack -= 1
                    if stack == 0:
                        break
                    a += c
                else:
                    a += c
        else:
            a = ans.split("$")[0].strip()
        pred = a
    elif "he answer is" in pred_str:
        pred = pred_str.split("he answer is")[-1].strip()
    elif "final answer is" in pred_str:
        pred = pred_str.split("final answer is")[-1].strip()
    elif "答案是" in pred_str:
        pred = pred_str.split("答案是")[1].strip().split("\n\n")[0].strip()
    else:
        # Fallback: use last number
        if use_last_number:
            pattern = r"-?\d*\.?\d+"
            pred = re.findall(pattern, pred_str.replace(",", ""))
            if len(pred) >= 1:
                pred = pred[-1]
            else:
                pred = ""
        else:
            pred = ""

    # Post-process for choice datasets
    if data_name in ["sat_math", "aqua"] or "mmlu" in data_name:
        tmp = re.findall(r"\b(A|B|C|D|E)\b", pred.upper())
        if tmp:
            pred = tmp[-1]
        else:
            pred = pred.strip().strip(".")

    # Clean up
    pred = re.sub(r"\n\s*", "", pred)
    if pred != "" and pred[0] == ":":
        pred = pred[1:]
    if pred != "" and pred[-1] == ".":
        pred = pred[:-1]
    if pred != "" and pred[-1] == "/":
        pred = pred[:-1]

    pred = strip_string(pred, skip_unit=data_name in ["carp_en", "minerva_math"])
    return pred
