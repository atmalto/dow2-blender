#include "main_window.h"

#include <QStatusBar>

#include "sync_listener_dialog.h"
#include "sync_protocol.h"
#include "sync_server.h"

bool MainWindow::start_sync_listener(unsigned short port, const QString& token)
{
    SyncServer* new_server = 0;

    stop_sync_listener();

    m_sync_listener_port = port;
    m_sync_listener_token = token;
    m_sync_listener_last_error.clear();

    new_server = new SyncServer(m_simulation, port, token, this);
    connect(new_server, SIGNAL(scene_changed()), this, SLOT(sync_listener_scene_changed()));

    if (!new_server->start())
    {
        m_sync_listener_last_error = new_server->last_error();
        delete new_server;
        refresh_sync_listener_dialog();
        return false;
    }

    m_sync_server = new_server;
    refresh_sync_listener_dialog();
    return true;
}

void MainWindow::stop_sync_listener()
{
    if (m_sync_server)
    {
        m_sync_server->stop();
        delete m_sync_server;
        m_sync_server = 0;
    }
    refresh_sync_listener_dialog();
}

bool MainWindow::is_sync_listener_running() const
{
    return m_sync_server != 0 && m_sync_server->is_listening();
}

void MainWindow::open_sync_listener_dialog()
{
    if (!m_sync_listener_dialog)
    {
        m_sync_listener_dialog = new SyncListenerDialog(this);
        m_sync_listener_dialog->setWindowModality(Qt::NonModal);
        connect(m_sync_listener_dialog, SIGNAL(start_requested(unsigned short)),
                this, SLOT(start_sync_listener_from_dialog(unsigned short)));
        connect(m_sync_listener_dialog, SIGNAL(restart_requested(unsigned short)),
                this, SLOT(restart_sync_listener_from_dialog(unsigned short)));
        connect(m_sync_listener_dialog, SIGNAL(stop_requested()),
                this, SLOT(stop_sync_listener_from_dialog()));
    }

    refresh_sync_listener_dialog();
    show_non_modal_dialog(m_sync_listener_dialog);
}

void MainWindow::start_sync_listener_from_dialog(unsigned short port)
{
    const QString token = QString::fromLocal8Bit(qgetenv(sync_protocol::kTokenEnvVar));
    if (start_sync_listener(port, token))
    {
        const QString message = QString("Sync listener started on 127.0.0.1:%1").arg(static_cast<unsigned>(port));
        statusBar()->showMessage(message);
        refresh_sync_listener_dialog();
        return;
    }

    const QString failure = m_sync_listener_last_error.isEmpty()
        ? QString("Could not listen on 127.0.0.1:%1").arg(static_cast<unsigned>(port))
        : QString("Could not listen on 127.0.0.1:%1 (%2)")
            .arg(static_cast<unsigned>(port))
            .arg(m_sync_listener_last_error);
    show_failure(failure, "Sync Listener Failed", failure);
}

void MainWindow::restart_sync_listener_from_dialog(unsigned short port)
{
    start_sync_listener_from_dialog(port);
}

void MainWindow::stop_sync_listener_from_dialog()
{
    stop_sync_listener();
    statusBar()->showMessage("Sync listener stopped");
}

void MainWindow::sync_listener_scene_changed()
{
    refresh_after_scene_change(false);
    statusBar()->showMessage(QString("Applied sync request on 127.0.0.1:%1")
        .arg(static_cast<unsigned>(m_sync_listener_port)));
}

void MainWindow::refresh_sync_listener_dialog()
{
    if (!m_sync_listener_dialog)
    {
        return;
    }

    QString message;
    if (is_sync_listener_running())
    {
        message = QString("Listening on 127.0.0.1:%1")
            .arg(static_cast<unsigned>(m_sync_listener_port));
        if (!m_sync_listener_token.isEmpty())
        {
            message += " (token enabled)";
        }
    }
    else if (!m_sync_listener_last_error.isEmpty())
    {
        message = QString("Stopped. Last error: %1").arg(m_sync_listener_last_error);
    }
    else
    {
        message = "Listener is stopped.";
    }

    m_sync_listener_dialog->set_listener_state(
        is_sync_listener_running(),
        m_sync_listener_port,
        message);
}