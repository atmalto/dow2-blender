#include "sync_server.h"

#include <QHostAddress>
#include <QTcpServer>
#include <QTcpSocket>

#include <string>

#include "command_dispatch.h"
#include "json_value.h"
#include "simulation_controller.h"
#include "sync_protocol.h"

namespace
{
    // Big-endian uint32 helpers (network byte order), matching the Python client.
    quint32 read_u32_be(const QByteArray& buffer, int offset)
    {
        return (static_cast<quint32>(static_cast<unsigned char>(buffer.at(offset + 0))) << 24)
             | (static_cast<quint32>(static_cast<unsigned char>(buffer.at(offset + 1))) << 16)
             | (static_cast<quint32>(static_cast<unsigned char>(buffer.at(offset + 2))) << 8)
             | (static_cast<quint32>(static_cast<unsigned char>(buffer.at(offset + 3))));
    }

    QByteArray frame_payload(const QByteArray& payload)
    {
        const quint32 length = static_cast<quint32>(payload.size());
        QByteArray out;
        out.reserve(sync_protocol::kLengthPrefixBytes + payload.size());
        out.append(static_cast<char>((length >> 24) & 0xFF));
        out.append(static_cast<char>((length >> 16) & 0xFF));
        out.append(static_cast<char>((length >> 8) & 0xFF));
        out.append(static_cast<char>(length & 0xFF));
        out.append(payload);
        return out;
    }

    QByteArray error_response(const std::string& message)
    {
        JsonValue out = JsonValue::make_object();
        out.set("ok", JsonValue(false));
        out.set("error", JsonValue(message));
        return QByteArray(out.dump().c_str());
    }
}

SyncServer::SyncServer(SimulationController* controller,
                       unsigned short port,
                       const QString& token,
                       QObject* parent)
    : QObject(parent)
    , m_controller(controller)
    , m_port(port)
    , m_token(token)
    , m_server(0)
{
}

SyncServer::~SyncServer()
{
    stop();
}

bool SyncServer::start()
{
    m_last_error.clear();

    if (m_server)
    {
        return m_server->isListening();
    }

    m_server = new QTcpServer(this);
    connect(m_server, SIGNAL(newConnection()), this, SLOT(handle_new_connection()));

    if (!m_server->listen(QHostAddress::LocalHost, m_port))
    {
        m_last_error = m_server->errorString();
        return false;
    }
    return true;
}

void SyncServer::stop()
{
    QMap<QTcpSocket*, QByteArray>::iterator it = m_buffers.begin();
    while (it != m_buffers.end())
    {
        QTcpSocket* socket = it.key();
        if (socket)
        {
            socket->disconnectFromHost();
            socket->deleteLater();
        }
        ++it;
    }
    m_buffers.clear();

    if (m_server)
    {
        if (m_server->isListening())
        {
            m_server->close();
        }
        delete m_server;
        m_server = 0;
    }
}

bool SyncServer::is_listening() const
{
    return m_server != 0 && m_server->isListening();
}

void SyncServer::handle_new_connection()
{
    while (m_server->hasPendingConnections())
    {
        QTcpSocket* socket = m_server->nextPendingConnection();
        m_buffers.insert(socket, QByteArray());
        connect(socket, SIGNAL(readyRead()), this, SLOT(handle_ready_read()));
        connect(socket, SIGNAL(disconnected()), this, SLOT(handle_disconnected()));
    }
}

void SyncServer::handle_ready_read()
{
    QTcpSocket* socket = qobject_cast<QTcpSocket*>(sender());
    if (!socket)
    {
        return;
    }
    m_buffers[socket].append(socket->readAll());
    drain_socket(socket);
}

void SyncServer::handle_disconnected()
{
    QTcpSocket* socket = qobject_cast<QTcpSocket*>(sender());
    if (!socket)
    {
        return;
    }
    m_buffers.remove(socket);
    socket->deleteLater();
}

void SyncServer::drain_socket(QTcpSocket* socket)
{
    QByteArray& buffer = m_buffers[socket];
    for (;;)
    {
        if (buffer.size() < sync_protocol::kLengthPrefixBytes)
        {
            return; // wait for the length prefix
        }

        const quint32 length = read_u32_be(buffer, 0);
        if (length > sync_protocol::kMaxFrameBytes)
        {
            socket->write(frame_payload(error_response("frame too large")));
            socket->flush();
            socket->disconnectFromHost();
            return;
        }

        if (static_cast<quint32>(buffer.size() - sync_protocol::kLengthPrefixBytes) < length)
        {
            return; // wait for the rest of the payload
        }

        const QByteArray request_json = buffer.mid(sync_protocol::kLengthPrefixBytes,
                                                   static_cast<int>(length));
        buffer.remove(0, sync_protocol::kLengthPrefixBytes + static_cast<int>(length));

        bool mutated = false;
        const QByteArray response_json = process_request_json(request_json, &mutated);
        socket->write(frame_payload(response_json));
        socket->flush();

        if (mutated)
        {
            emit scene_changed();
        }
    }
}

QByteArray SyncServer::process_request_json(const QByteArray& request_json, bool* mutated)
{
    if (mutated)
    {
        *mutated = false;
    }

    std::string parse_error;
    JsonValue request = JsonValue::parse(std::string(request_json.constData(), request_json.size()),
                                         &parse_error);
    if (!parse_error.empty())
    {
        return error_response(std::string("JSON parse error: ") + parse_error);
    }

    // Token gate (skipped when the server was started without a token).
    if (!m_token.isEmpty())
    {
        const std::string given = request.member_string("token");
        if (QString::fromUtf8(given.c_str()) != m_token)
        {
            return error_response("unauthorized");
        }
    }

    // Liveness probe -- proves the transport without touching the scene.
    if (request.member_string("op") == "ping")
    {
        JsonValue out = JsonValue::make_object();
        out.set("ok", JsonValue(true));
        out.set("op", JsonValue(std::string("pong")));
        out.set("protocol", JsonValue(std::string(sync_protocol::kProtocolTag)));
        return QByteArray(out.dump().c_str());
    }

    // Everything else is a command scenario: forward to the shared dispatcher.
    if (!m_controller)
    {
        return error_response("no simulation controller");
    }
    JsonValue result = run_scenario(*m_controller, request);
    if (mutated)
    {
        *mutated = true;
    }
    return QByteArray(result.dump().c_str());
}
