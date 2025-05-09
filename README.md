Xschem waveform Synthesize
This document provides a guide to synthesize simulated current or voltage waveforms from the
XSCHEM schematic editor using the pyVISA Python library. The waveforms are generated from
data stored in a CSV file and can be synthesized with any compatible current or voltage source
instrument. This guide demonstrates waveform synthesize from xschem using the Keithley 2450
Source Measure Unit (SMU).
~ Use launcher.sym to start the execution of your Python script. Launch the shell script run_python.sh from
launcher.sym to run the Python script in the background, allowing Xschem to remain active during execution. To
terminate or abort the trigger, use the Tcl script stop_script.tcl, which can also be launched via launcher.sym.
This setup provides a convenient way to control both the start and stop of the arbitrary current or voltage wave
generation.


~ Sample NGSpice code to export simulation results to a CSV file is provided below.
name=Stimuli2
only_toplevel=true
value=
"
.lib /home/ihpopenpdk/asic_tools/pdk/IHP-Open-PDK/ihp-sg13g2/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.option savecurrents
.save all
.control
set wr_vecnames *** Ensure ngspice includes vectors such as node voltages and current.
set wr_singlescale *** Ensure that ngspice does not repeat time or frequency values in the output file .
save all
tran 0.05 50
write test_23_csv.raw
wrdata ~/current.csv @n.xm5.nsg13_hv_pmos[ids] ***write drain current (ids) of mosfet 5 to a csv file.
set appendwrite
op
remzerovec
write test_23_csv.raw
save all
.endc”
~On the 2450 SMU, navigate to the Menu Bar and select System Settings. Under the Command Set section,
choose SCPI for Python and pyVISA configuration.
~ Create and store a Source Configuration List that can includes settings such as voltage or current ranges,
maximum limits, specific values and other relevant settings. Current or voltage values stored in a .csv file can be
loaded into a Python array and incorporated into this Source Configuration List. If needed, you can also define a
Measure Configuration List to specify how measurements should be performed. Both configuration lists can
then be used to generate arbitrary current or voltage waveforms
~ Configure Timer 1 on the 2450 SMU to set the required time intervals for your source steps.
~ Build a Trigger Model to invoke the Source Configuration List. This will source the desired current or
voltage values at each defined time step. The trigger model ensures that the SMU automatically applies each
source setting in synchronization with the configured timer steps.
