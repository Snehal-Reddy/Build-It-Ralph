import os
import json
import sys
import subprocess

# --- Universal Ralph Loop Engine ---
# This script manages the state transitions for the Ralph Wiggum Loop.
# It is designed to be a generic harness, driven by `.gemini/ralph/config.json`.

def run_command(command):
    """Executes a shell command and returns True if successful."""
    if not command:
        return True
    print(f"[Ralph Engine] Running: {command}")
    try:
        subprocess.run(command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"[Ralph Engine] Command failed: {command}")
        return False

def main():
    # 1. Load Configuration
    CONFIG_PATH = os.path.join(".gemini", "ralph", "config.json")
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        # Not a Ralph project or not initialized
        return

    # 2. Resolve Paths
    PROJECT_DIR = os.environ.get("GEMINI_PROJECT_DIR", ".")
    STATE_FILE = config.get("state_file", os.path.join(".gemini", "ralph", "state.json"))
    PROMPTS_DIR = config.get("prompts_dir", os.path.join(".gemini", "ralph", "prompts"))

    # 3. Load State
    if not os.path.exists(STATE_FILE):
        return # Loop not active

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except json.JSONDecodeError:
        return # Corrupt state

    # 4. Check Agent Status
    # The hook only acts when the agent marks itself as COMPLETED or FAILED.
    current_status = state.get("status")
    if current_status not in ["COMPLETED", "FAILED"]:
        return

    # 5. Determine Transition
    phases = config.get("phases", [])
    current_phase = state.get("phase")
    
    if not phases:
        print("[Ralph Engine] Error: No phases defined in .gemini/ralph/config.json")
        return

    try:
        current_idx = phases.index(current_phase)
    except ValueError:
        # Unknown phase, reset to start or abort? Let's reset to first phase.
        current_idx = -1

    next_phase = None
    next_prompt_file = None

    if current_status == "FAILED":
        # --- FAILURE RECOVERY ---
        print(f"[Ralph Engine] Phase {current_phase} FAILED. Initiating recovery...")
        
        # 1. Run Cleanup Command (if any)
        cleanup_cmd = config.get("cleanup_command")
        if cleanup_cmd:
            if not run_command(cleanup_cmd):
                print("[Ralph Engine] Cleanup failed. Aborting loop.")
                return 

        # 2. Reset to First Phase
        next_phase = phases[0]
        # Increment iteration on failure reset? Often yes, to track attempts.
        state["iteration"] = state.get("iteration", 1) + 1

    else:
        # --- SUCCESS TRANSITION ---
        # Cyclic transition: A -> B -> C -> A
        next_idx = (current_idx + 1) % len(phases)
        next_phase = phases[next_idx]
        
        # If completing the *last* phase, increment iteration
        if next_idx == 0:
            state["iteration"] = state.get("iteration", 1) + 1

    # 6. Execute Pre-Phase Scripts (Optional)
    # The config can define specific scripts to run *before* entering a phase
    # e.g., "scripts": { "PLAN": "python3 scripts/profile.py" }
    phase_scripts = config.get("phase_scripts", {})
    if next_phase in phase_scripts:
        script = phase_scripts[next_phase]
        if not run_command(script):
             print(f"[Ralph Engine] Pre-phase script for {next_phase} failed.")
             # Decide: Stop or continue? For now, we continue but log it.

    # 7. Update State
    state["phase"] = next_phase
    state["status"] = "ACTIVE"
    # We keep custom fields (like 'current_plan') in state, 
    # but the Agent might want them cleared.
    # The prompt instructions should tell the Agent to overwrite them.
    
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    # 8. Load Next Prompt
    # Construct filename: e.g., ".gemini/ralph/prompts/PLAN.md" or ".gemini/ralph/prompts/plan_phase.md"
    # We assume standard naming convention or config mapping.
    # Simple default: "{phase_name_lowercase}.md"
    prompt_filename = f"{next_phase.lower()}.md"
    prompt_path = os.path.join(PROMPTS_DIR, prompt_filename)
    
    try:
        with open(prompt_path, "r") as f:
            next_prompt_content = f.read()
    except FileNotFoundError:
        next_prompt_content = f"Error: Prompt file '{prompt_path}' not found for phase {next_phase}."

    # 9. Construct "Context Clearing" Response
    # This is the magic. We deny the previous tool output (essentially) 
    # and force a fresh context with the new prompt.
    
    full_prompt = f"[{next_phase} PHASE]\n\n{next_prompt_content}"

    response = {
        "clearContext": True,
        "decision": "deny",
        "reason": full_prompt,
        "systemMessage": f"Transitioning to {next_phase} phase (Iteration {state.get('iteration', 1)})"
    }

    # 10. Output JSON to CLI
    json_output = json.dumps(response)
    sys.stdout.write(json_output)
    sys.stdout.flush()

if __name__ == "__main__":
    main()
