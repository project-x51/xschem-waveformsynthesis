#!/bin/bash

# Path to the Python script
PYTHON_SCRIPT="~/2450_xschem_synthesis.py"

# Create a unique ID for this run
RUN_ID=$(date +%s)
PID_FILE="/tmp/xschem_python_pid_$RUN_ID.txt"
CONTROL_FILE="/tmp/xschem_python_control_$RUN_ID.txt"

# Start the Python script in the background and save its PID
python3 "$PYTHON_SCRIPT" $RUN_ID &
PID=$!

# Save the PID to a file for later termination
echo $PID > "$PID_FILE"

# Create control file for communication
echo "running" > "$CONTROL_FILE"


# Wait for the Python script to finish or be killed
wait $PID

# Clean up temporary files
rm -f "$PID_FILE"
rm -f "$CONTROL_FILE"

echo "Python script terminated"
