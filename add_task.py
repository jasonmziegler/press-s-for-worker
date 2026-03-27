import sys
from taskqueue import add_task

if len(sys.argv) < 2:
    print('Usage: python add_task.py "Your task description here"')
    print('       python add_task.py --fast "Your task description here"')
    sys.exit(1)

think = True
args = sys.argv[1:]
if args[0] == "--fast":
    think = False
    args = args[1:]

task = " ".join(args)
task_id = add_task(task, think=think)
mode = "think" if think else "fast"
print(f"Task #{task_id} [{mode}] queued: {task}")
