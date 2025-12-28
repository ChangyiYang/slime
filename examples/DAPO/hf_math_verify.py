# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
from itertools import product

from math_verify import parse
from math_verify.grader import sympy_expr_eq
from sympy import Basic, MatrixBase

from .parser import extract_answer as qwen_extract_answer


def extract_last_boxed(text):
    """Extract the last \\boxed{} content from LaTeX text."""
    pattern = r"\\boxed\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}"
    matches = list(re.finditer(pattern, text))
    if matches:
        return matches[-1].group(0)
    return None


def extract_solution(response):
    """Extract answer from model response."""
    # Remove prompt prefix if present
    model_output = re.sub(r"^.*?<\|im_start\|>assistant", "<|im_start|>assistant", response, flags=re.DOTALL, count=1)

    # Remove stop tokens
    stop_words = ["</s>", "<|im_end|>", "<|endoftext|>", "[END]"]
    for stop_word in stop_words:
        if stop_word in model_output:
            model_output = model_output.split(stop_word)[0].strip()

    # Follow DAPO: only extract the last 300 chars to avoid reward hacking
    model_output = model_output[-300:]
    predict_answer = qwen_extract_answer(model_output, data_name="math", use_last_number=False)

    return predict_answer


def _verify_with_sympy(gold, target, float_rounding=6, numeric_precision=15, strict=True):
    """Compare gold and target using sympy.
    
    Note: Removed timeout decorator because signal.alarm doesn't work in 
    Ray worker threads (non-main thread), causing all comparisons to fail.
    """
    def compare_single(gold, target):
        if isinstance(gold, (Basic, MatrixBase)) and isinstance(target, (Basic, MatrixBase)):
            return sympy_expr_eq(gold, target, float_rounding, numeric_precision, strict)
        elif isinstance(gold, str) and isinstance(target, str):
            gold = gold.strip()
            target = target.strip()
            return len(gold) > 0 and len(target) > 0 and gold == target
        return False

    def safe_compare(g, t):
        try:
            return compare_single(g, t)
        except Exception:
            return False

    if not isinstance(gold, list):
        gold = [gold]
    if not isinstance(target, list):
        target = [target]

    return any(safe_compare(g, t) for g, t in product(gold, target))


def _hf_verify(gold, target):
    """Verify using HuggingFace math_verify library."""
    # Fast path: if strings are identical, return True immediately
    if gold == target:
        return True
    
    try:
        # Disable timeout in parse() because signal.alarm() doesn't work in 
        # Ray worker threads (non-main thread)
        parsed_target = parse(target, parsing_timeout=None)
        parsed_gold = parse(gold, parsing_timeout=None)
        return _verify_with_sympy(gold=parsed_gold, target=parsed_target)
    except Exception:
        return False


def get_dapo_math_reward(response, label):
    """Compute DAPO-style math reward using HuggingFace math_verify.

    This is the slime-style reward function for DAPO math verification.
    Uses symbolic math verification via math_verify + sympy for accurate
    comparison of mathematical expressions.

    Args:
        response: The model response string
        label: The ground truth answer

    Returns:
        1 if correct, 0 if incorrect
    """
    if not label:
        return 0

    label = str(label)

    # Extract answer from response
    extracted_answer = extract_solution(response)
    if not extracted_answer:  # Check for None or empty string
        return 0

    # Wrap answers in boxed format for math_verify
    if "\\boxed" not in extracted_answer:
        boxed_answer = f"\\boxed{{{extracted_answer}}}"
    else:
        boxed_answer = extracted_answer

    if "\\boxed" not in label:
        boxed_label = f"\\boxed{{{label}}}"
    else:
        boxed_label = label

    # Verify using sympy-based comparison
    is_correct = _hf_verify(gold=boxed_label, target=boxed_answer)

    return 1 if is_correct else 0


# Keep compute_score as alias for backward compatibility
compute_score = get_dapo_math_reward


async def get_dapo_math_reward_async(args, sample, **kwargs):
    """Async wrapper for slime custom reward interface.

    This is the entry point for slime's --custom-rm-path option.

    Args:
        args: Training arguments (unused)
        sample: Sample object with response and label attributes
        **kwargs: Additional arguments (unused)

    Returns:
        1 if correct, 0 if incorrect
    """
    response = sample.response
    label = sample.label
    return get_dapo_math_reward(response, label)


if __name__ == "__main__":
    # Test case
    solution_str = """<|im_start|>user
Two circles, one of radius inches, the other of radius inches, are tangent at point P. Two bugs start crawling at the same time from point P, one crawling along the larger circle at $3\\pi$ inches per minute, the other crawling along the smaller circle at $2.5\\pi$ inches per minute. How many minutes is it before their next meeting at point P? Please reason step by step, and put your final answer within \\boxed{}.<|im_end|>
<|im_start|>assistant
Some reasoning... \\boxed{10}"""

    score = get_dapo_math_reward(solution_str, "10")
    print(f"Score: {score}")

    # Additional test cases
    print(f"Fraction test: {get_dapo_math_reward('The answer is \\boxed{1/2}', '0.5')}")
    print(f"Integer test: {get_dapo_math_reward('Result: \\boxed{42}', '42')}")
