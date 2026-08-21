// Command dispatcher for the headless simulator CLI.
//
// Reads a JSON scenario ({"commands": [ {cmd, ...}, ... ]}) and replays each
// command against a live SimulationController exactly the way the GUI does,
// returning a JSON result array ({"results": [ ... ]}). It adds no simulation
// logic of its own -- every command maps to an existing controller method.
#ifndef HAVOK_SIM_CLI_COMMAND_DISPATCH_H
#define HAVOK_SIM_CLI_COMMAND_DISPATCH_H

#include "json_value.h"

class SimulationController;

// Execute all commands in the scenario against a fresh controller. Returns a
// JSON object {"ok": bool, "results": [...]}. ok is false if any command hard-failed.
JsonValue run_scenario(SimulationController& controller, const JsonValue& scenario);

#endif
