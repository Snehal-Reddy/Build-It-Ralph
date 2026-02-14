import os
import json
import sys

# --- Universal Ralph Loop Bootstrapper ---
# This script initializes the Ralph Wiggum Loop based on `ralph_config.json`.

def init():
    # 1. Load Config
    try:
        with open("ralph_config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("[Ralph Init] Error: 'ralph_config.json' not found. Run '/setup_ralph' first.")
        return

    # 2. Get Initial Phase
    phases = config.get("phases", [])
    if not phases:
        print("[Ralph Init] Error: No phases defined in config.")
        return
    initial_phase = phases[0]

    # 3. Create/Reset State
    state_file = config.get("state_file", ".ralph_state.json")
    
    # Check if existing state exists?
    # Usually, we want to force a restart or ask?
    # For now, we force restart (iteration 1).
    state = {
        "status": "ACTIVE",
        "phase": initial_phase,
        "iteration": 1,
        "history": [], # Basic history
        "metrics": {}  # Generic metrics store
    }
    
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    print(f"[Ralph Init] Loop Initialized. Phase: {initial_phase}")
    print(f"[Ralph Init] State saved to: {state_file}")

    # 4. Optional: Print First-Phase Prompt
    if "--print-prompt" in sys.argv:
        prompt_path = os.path.join(config.get("prompts_dir", "prompts"), f"{initial_phase.lower()}.md")
        try:
            with open(prompt_path, "r") as f:
                print(f"[{initial_phase} PHASE]\n\n{f.read()}")
        except FileNotFoundError:
            print(f"Error: Prompt file '{prompt_path}' not found.")
    else:
        print(f"\n[Ralph Init] Ready to start! The first phase is '{initial_phase}'.")
        print(f"To begin, just say: 'Start the loop' or '/ralph'.")

if __name__ == "__main__":
    init()
