"""Computational Tool for Complex Mathematical and Analytical Problems.

This tool uses DSPy's built-in ProgramOfThought module with an interpreter
to solve complex problems through programmatic computation including statistical
analysis, financial calculations, engineering computations, and advanced
mathematical operations (summations, infinite series, calculus, etc.).

Async Support:
- When used with dspy.Tool wrapper, supports async execution via acall()
- Example: tool = dspy.Tool(compute); await tool.acall(problem="...")
"""

import dspy
import logging

logger = logging.getLogger(__name__)


class ComputationSignature(dspy.Signature):
    """Signature for computational problem solving through programmatic reasoning.

    This signature defines the input-output structure for solving complex
    computational problems using DSPy's ProgramOfThought with automatic code
    generation and execution. Supports mathematical, statistical, financial,
    and engineering calculations.
    """

    problem: str = dspy.InputField(
        desc="A computational problem (mathematical, statistical, financial, or engineering) that needs to be solved using Python code"
    )
    result: str = dspy.OutputField(
        desc="The computed result from executing the generated Python code"
    )


# Initialize the Python Interpreter for code execution
_interpreter = dspy.PythonInterpreter()

# Initialize the ProgramOfThought module with the interpreter
_pot_module = dspy.ProgramOfThought(ComputationSignature)


def compute(problem: str) -> str:
    """Compute solutions to complex mathematical, statistical, financial, and engineering problems.

    This tool uses DSPy's ProgramOfThought module with an interpreter to solve
    computational problems by automatically generating and executing Python code.

    Use this tool for:
    - Simple calculations (summations, deduction, division, multiplication)
    - Statistical analysis (mean, standard deviation, correlations, distributions)
    - Financial calculations (NPV, IRR, compound interest, portfolio metrics)
    - Engineering computations (physics equations, conversions, optimizations)
    - Advanced mathematics (summations, infinite series, calculus, differential equations)
    - Complex numerical operations requiring programmatic logic

    The module automatically handles code generation and execution internally,
    providing a safe and reliable way to solve computational problems.

    Args:
        problem: A description of the computational problem to solve (mathematical,
                statistical, financial, or engineering)

    Returns:
        String representation of the computed result

    Examples:
        >>> compute("Calculate the mean and standard deviation of [12, 15, 18, 21, 24]")
        "Mean: 18.0, Standard Deviation: 4.24"

        >>> compute("What is the NPV of cash flows [1000, 2000, 3000] with discount rate 0.1?")
        "NPV: 4815.92"

        >>> compute("Calculate the sum of the infinite series 1/2^n for n from 1 to infinity")
        "Sum: 1.0"

        >>> compute("Find the derivative of x^3 + 2x^2 - 5x + 3 at x=2")
        "Derivative at x=2: 15"
    """
    logger.info("Executing computational problem solving")
    logger.debug("Problem: %s", problem)

    try:
        # Use DSPy's ProgramOfThought to solve the problem
        prediction = _pot_module(problem=problem)

        # Extract the result
        result = prediction.result

        logger.info("Computation completed: %s", result)
        return str(result)

    except Exception as e:
        error_msg = f"Error computing solution: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg
