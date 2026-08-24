// Loopback TCP front-end that lets the Blender add-on push authored physics /
// ragdoll data into a *running* simulator on demand (user presses "Sync").
//
// It adds no simulation logic: each received frame is a JSON command document
// that is handed straight to run_scenario() against the live SimulationController
// -- the exact same path the headless CLI and the GUI menus already use. The
// server is event-driven (QTcpServer::newConnection / QIODevice::readyRead), so
// nothing polls, and it binds 127.0.0.1 only so no network port is exposed.
#ifndef HAVOK_SYNC_SERVER_H
#define HAVOK_SYNC_SERVER_H

#include <QByteArray>
#include <QMap>
#include <QObject>
#include <QString>

class QTcpServer;
class QTcpSocket;
class SimulationController;

class SyncServer : public QObject
{
    Q_OBJECT

public:
    // The controller must outlive the server (owned by MainWindow / the CLI).
    // An empty token disables the token check (loopback dev convenience).
    SyncServer(SimulationController* controller,
               unsigned short port,
               const QString& token,
               QObject* parent = 0);
    ~SyncServer();

    // Begin listening on 127.0.0.1:port. Returns false (and sets last_error())
    // if the port is unavailable.
    bool start();
    void stop();
    bool is_listening() const;
    unsigned short port() const { return m_port; }
    QString last_error() const { return m_last_error; }

signals:
    // Emitted after a request mutates the scene, so a GUI host can refresh its
    // views. Not emitted for read-only requests (e.g. ping).
    void scene_changed();

private slots:
    void handle_new_connection();
    void handle_ready_read();
    void handle_disconnected();

private:
    // Pull as many complete frames as are buffered for this socket and process
    // each one, writing a framed JSON response back.
    void drain_socket(QTcpSocket* socket);
    QByteArray process_request_json(const QByteArray& request_json, bool* mutated);

    SimulationController* m_controller;
    unsigned short m_port;
    QString m_token;
    QString m_last_error;
    QTcpServer* m_server;
    QMap<QTcpSocket*, QByteArray> m_buffers; // per-connection receive buffer
};

#endif
