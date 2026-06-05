"""Command-line entry point for the Gemini agent project."""

from agent import Agent


def main() -> None:
    """Ask the user for a goal and run the agent."""
    goal = input("What goal should the agent work on? ").strip()
    if not goal:
        print("No goal provided. Exiting.")
        return

    agent = Agent()
    final_answer = agent.run(goal)

    print("\nFinal answer:\n")
    print(final_answer)
    print("\nSaved progress to memory.json")
    print("Saved final report to report.md")


if __name__ == "__main__":
    main()
