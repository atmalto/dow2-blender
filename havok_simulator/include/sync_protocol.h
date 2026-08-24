// Shared constants + framing for the Blender <-> simulator sync bridge.
//
// The wire format is deliberately tiny and dependency-free so both the Qt4
// simulator and Blender's stdlib-only Python can speak it:
//
//   frame  = <uint32 big-endian length N> <N bytes UTF-8 JSON>
//   request  JSON: {"protocol":"dow2-sync/1","token":"...", ...command fields...}
//   response JSON: {"ok":bool, ...}
//
// A request with {"op":"ping"} is answered with {"ok":true,"op":"pong"} and is
// used purely to prove the transport is alive. Every other request is forwarded
// verbatim to the existing run_scenario() command dispatcher.
#ifndef HAVOK_SYNC_PROTOCOL_H
#define HAVOK_SYNC_PROTOCOL_H

namespace sync_protocol
{
    // Protocol tag echoed by both ends; bump when the envelope changes.
    static const char* const kProtocolTag = "dow2-sync/1";

    // Loopback-only default endpoint. The port can be overridden on the command
    // line (--sync-listen <port>); the token is read from this environment var.
    static const unsigned short kDefaultPort = 47800;
    static const char* const kTokenEnvVar = "DOW2_SYNC_TOKEN";

    // Guard against absurd/hostile frame sizes (64 MiB).
    static const unsigned int kMaxFrameBytes = 64u * 1024u * 1024u;

    // Number of bytes in the length prefix.
    static const int kLengthPrefixBytes = 4;
}

#endif
