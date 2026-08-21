// havok_sim_cli -- headless driver for the Havok ragdoll simulator.
//
// It boots the same SimulationController the GUI uses (constructing it initializes
// the Havok base system) and replays a JSON command scenario against it, printing
// a JSON result document. This lets an automated test suite exercise every
// simulator interaction without a window or OpenGL context.
//
// Usage:
//   havok_sim_cli <scenario.json>     read the scenario from a file
//   havok_sim_cli -                   read the scenario from stdin
//
// Exit code 0 if all commands succeeded, 1 if any command failed, 2 on bad usage
// or unparseable input.

#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "json_value.h"
#include "command_dispatch.h"
#include "simulation_controller.h"

namespace
{
    bool read_all(std::istream& in, std::string* out)
    {
        std::ostringstream buffer;
        buffer << in.rdbuf();
        *out = buffer.str();
        return true;
    }
}

int main(int argc, char** argv)
{
    if (argc < 2)
    {
        std::fprintf(stderr, "Usage: %s <scenario.json>|-\n", argv[0]);
        return 2;
    }

    std::string text;
    const std::string source = argv[1];
    if (source == "-")
    {
        read_all(std::cin, &text);
    }
    else
    {
        std::ifstream file(source.c_str(), std::ios::binary);
        if (!file)
        {
            std::fprintf(stderr, "error: cannot open '%s'\n", source.c_str());
            return 2;
        }
        read_all(file, &text);
    }

    std::string parse_error;
    JsonValue scenario = JsonValue::parse(text, &parse_error);
    if (!parse_error.empty())
    {
        JsonValue out = JsonValue::make_object();
        out.set("ok", JsonValue(false));
        out.set("error", JsonValue(std::string("JSON parse error: ") + parse_error));
        std::printf("%s\n", out.dump().c_str());
        return 2;
    }

    // Constructing the controller initializes the Havok base system (same as GUI).
    SimulationController controller;
    JsonValue result = run_scenario(controller, scenario);

    std::printf("%s\n", result.dump().c_str());
    return result.member_bool("ok", false) ? 0 : 1;
}
