#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May  7 13:43:00 2025

@author: ihpopenpdk
"""

import pyvisa
import time
import signal
import sys
import pandas as pd
import os
import numpy as np
import threading

# Check if run ID is provided
if len(sys.argv) > 1:
    run_id = sys.argv[1]
    # Create paths for control files
    pid_file = f"/tmp/xschem_python_pid_{run_id}.txt"
    control_file = f"/tmp/xschem_python_control_{run_id}.txt"
else:
    print("No run ID provided. Using default control files.")
    pid_file = "/tmp/xschem_python_pid_default.txt"
    control_file = "/tmp/xschem_python_control_default.txt"

# Check if the input file exists
input_file = '~/current.csv'
if not os.path.exists(input_file):
    print(f"Error: Input file '{input_file}' not found.")
    exit(1)

#************************************** Read the CSV file and create uniform time-step (1 ms steps) array *******************************************************************
try:
    df = pd.read_csv(input_file, delim_whitespace=True, header=0, 
                     names=['time', 'ids'], dtype={'time': float, 'ids': float})
except ValueError as e:
    print(f"Error reading CSV: {e}")
    print("Ensure all values in 'data.csv' (excluding header) are numeric and properly formatted.")
    exit(1)
except Exception as e:
    print(f"Unexpected error reading CSV: {e}")
    exit(1)

# Check for non-numeric values
if df[['time', 'ids']].isna().any().any():
    print("Warning: Missing or non-numeric values detected. Dropping invalid rows.")
    df = df.dropna()

# Extract time and ids columns
time_values = df['time'].values
ids = df['ids'].values

# Verify that we have enough data
if len(time_values) < 2:
    print("Error: Insufficient data points (need at least 2 rows).")
    exit(1)

# Initialize output arrays
new_time = []
new_ids = []

# Process time steps
i = 0
time_step = 0.001  # 1 ms
while i < len(time_values):
    # Always add the current point (will be modified if time step < 1 ms)
    current_time = time_values[i]
    current_ids = ids[i]
    
    # Check if we're at the last point
    if i == len(time_values) - 1:
        new_time.append(current_time)
        new_ids.append(current_ids)
        break
    
    # Compute time step to next point
    next_time = time_values[i + 1]
    step = next_time - current_time
    
    if step >= time_step - 1e-6:  # Time step ≥ 1 ms (with tolerance)
        new_time.append(current_time)
        new_ids.append(current_ids)
        i += 1
    else:
        # Time step < 1 ms, find n_time where diff from c_time ≥ 1 ms
        c_time = current_time
        j = i + 1
        n_time = None
        while j < len(time_values):
            if time_values[j] - c_time >= time_step - 1e-6:
                n_time = time_values[j]
                n_ids = ids[j]
                break
            j += 1
        
        # If no n_time found, use the last point
        if n_time is None:
            j = len(time_values) - 1
            n_time = time_values[j]
            n_ids = ids[j]
        
        # Find max ids in the interval [c_time, n_time) (exclusive of n_time)
        mask = (time_values >= c_time) & (time_values < n_time)
        max_ids = np.max(ids[mask]) if mask.any() else current_ids
        
        # Add c_time with max_ids
        new_time.append(c_time)
        new_ids.append(max_ids)
        
        # Add n_time with its original ids
        new_time.append(n_time)
        new_ids.append(n_ids)
        
        # Skip to the point after n_time
        i = j + 1

# Create uniform time array starting at 0 with 1 ms steps
num_points = len(new_time)
new_uniform_time = np.arange(0, num_points * time_step, time_step)

# Ensure the uniform time array has the same length as new_ids
if len(new_uniform_time) != len(new_ids):
    print(f"Warning: Adjusting uniform time array length to match {len(new_ids)} points.")
    new_uniform_time = np.arange(0, len(new_ids) * time_step, time_step)

# Create new DataFrame with uniform time
new_df = pd.DataFrame({
    'Time': new_uniform_time,
    'Current': new_ids
})

# Debugging: Print DataFrame
print("Processed DataFrame with uniform 1 ms time steps:")
print(new_df)

# Check if DataFrame has exactly two columns
if new_df.shape[1] != 2:
    print(f"Error: DataFrame must contain exactly two columns (Time, Current). Found {new_df.shape[1]} column(s).")
    sys.exit(1)

# Verify numeric data
try:
    new_df['Time'] = new_df['Time'].astype(float)
    new_df['Current'] = new_df['Current'].astype(float)
except ValueError as e:
    print(f"Error: Non-numeric data found in DataFrame: {e}")
    sys.exit(1)

# Check if DataFrame is empty
if new_df.empty:
    print("Error: No data in processed DataFrame.")
    sys.exit(1)

# Print the DataFrame for verification
print("Processed DataFrame content (two columns):")
print(new_df)

# Extract current values
curr_list = new_df['Current'].tolist()  # List of currents in amperes

# ***********************Function to check control file for stop commands********************************
# Variable to control the main loop
running = True

def check_control_file():
    global running
    while running:
        try:
            if os.path.exists(control_file):
                with open(control_file, 'r') as f:
                    command = f.read().strip()
                    if command == "stop":
                        print("\nStop command received. Terminating...")
                        running = False
                        break
        except Exception as e:
            print(f"Error checking control file: {e}")
        
        time.sleep(0.5)  # Check every 0.5 seconds

# Start the control file monitoring thread
monitor_thread = threading.Thread(target=check_control_file)
monitor_thread.daemon = True
monitor_thread.start()

# Setup signal handler for clean termination
def signal_handler(sig, frame):
    global running
    print('\nCtrl+C detected. Stopping execution...')
    running = False

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

#****************************Configure 2450*********************************************************************
rm = pyvisa.ResourceManager()
resource_name = 'TCPIP0::10.0.0.38::5025::SOCKET'
instrument = None  # Initialize instrument variable

try:
    instrument = rm.open_resource(resource_name)
    instrument.timeout = 10000
    instrument.read_termination = '\n'
    instrument.write_termination = '\n'

    # Initialize instrument
    print(f"Instrument ID: {instrument.query('*IDN?')}")
    instrument.write(':SYST:CLE')  # Clear errors
    instrument.write('*RST')  # Reset instrument
    time.sleep(1)

    # Setup current source
    instrument.write(':SOUR:FUNC CURR')# source current
    instrument.write(':SOUR:CURR:RANG 0.001')  # 1 mA range
    instrument.write(':SOUR:CURR:VLIM 5')      # Voltage limit 5V
    instrument.write(':SENS:FUNC "VOLT"')      # Measure voltage
    
    # Create the current source configuration list
    list_name = "CURR_LIST"
    instrument.write(f':SOUR:CONF:LIST:CRE "{list_name}"')
    
    # Add each current setting to the configuration list
    for current in curr_list:
        # Set the current level
        instrument.write(f':SOUR:CURR {current}')
        # Store current source settings in the list
        instrument.write(f':SOUR:CONF:LIST:STOR "{list_name}"')
    
    # Configure timer for 1ms operation
    instrument.write(':TRIG:TIM1:STAT 0') # Disable timer-1
    instrument.write(':TRIG:TIM1:CLE') # Clear the timer-1
    instrument.write(':TRIG:TIM1:DEL 0.001')  # 1ms delay
    instrument.write(':TRIG:TIM1:COUN 0')  # 0 = infinite count
    instrument.write(':TRIG:TIM1:STAR:STIM NOT1') # Start timer-1 using stimulus notify-1
    
    
    # Build trigger model
    instrument.write(':TRIG:LOAD "Empty"') # Reset the trigger model
    instrument.write(':TRIG:BLOC:SOUR:STAT 1, ON') # Trigger block turn on the source output
    instrument.write(f':TRIG:BLOC:CONF:RECALL 2, "{list_name}", 1') # Recall the index-1 in the configuration list 
    instrument.write(':TRIG:BLOC:NOT 3, 1') # Generate trigger event notify-1 to start the timer
    instrument.write(':TRIG:BLOC:WAIT 4, TIM1') #  Wait for the timer event 
    instrument.write(f':TRIG:BLOC:CONF:NEXT 5, "{list_name}"') # Recall the next index in the configuration list
    instrument.write(':TRIG:BLOC:BRAN:ALW 6, 4') # Infinite loop
    instrument.write(':TRIG:TIM1:STAT 1')# enable timer-1
    
    instrument.write(':OUTP ON')
    instrument.write(':INIT')
    
    
    # Main loop with control file and signal handler termination
    while running:
        time.sleep(0.5)
        
    print("\nExecution stopping...")
    instrument.write(':ABORT')
    print("Trigger model aborted")
    
    print(f"Final error state: {instrument.query(':SYST:ERR?')}")
    print("Script execution complete")

except pyvisa.VisaIOError as e:
    print("VI_ERROR_IO Details:", e)
except Exception as e:
    print("Unexpected Error:", e)
finally:
    # Update control file status
    try:
        with open(control_file, 'w') as f:
            f.write("terminated")
    except:
        pass
        
    if instrument is not None:
        try:
            instrument.write(':ABORT')  # Stop the trigger model
            instrument.write(':OUTP OFF')  # Turn off the output
            instrument.close()
            print("Connection closed")
        except:
            print("Failed to close connection cleanly")