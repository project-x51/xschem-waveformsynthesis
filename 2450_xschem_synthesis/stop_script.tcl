#!/usr/bin/tclsh

# Find the most recent control file
set control_files [glob -nocomplain /tmp/xschem_python_control_*.txt]

if {[llength $control_files] == 0} {
    puts "No running Python scripts found."
    return
}

# Sort by modification time (newest first)
set sorted_files [lsort -decreasing -command {
    apply {{a b} {
        expr {[file mtime $a] - [file mtime $b]}
    }}
} $control_files]

# Get the most recent file
set control_file [lindex $sorted_files 0]

# Send stop command
if {[catch {
    set fh [open $control_file w]
    puts $fh "stop"
    close $fh
    puts "Stop command sent to $control_file"
} err]} {
    puts "Error sending stop command: $err"
}
