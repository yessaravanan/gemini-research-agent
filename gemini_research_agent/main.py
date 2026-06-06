"""Command-line entry point for the Gemini agent project."""

from .agent import Agent


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
    print(f"\nSaved latest progress to {agent.memory_path}")
    print(f"Saved latest report to {agent.report_path}")
    if agent.run_memory_path and agent.run_report_path:
        print(f"Archived run memory to {agent.run_memory_path}")
        print(f"Archived run report to {agent.run_report_path}")
    if agent.run_artifacts_path:
        print(f"Archived run artifacts under {agent.run_artifacts_path}")


if __name__ == "__main__":
    main()
