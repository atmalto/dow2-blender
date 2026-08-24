#include <QApplication>
#include <QByteArray>
#include <QString>
#include <QStringList>

#include <cstdio>

#include "app_theme.h"
#include "main_window.h"
#include "sync_protocol.h"
#include "sync_server.h"

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    configure_application_theme(app);

    MainWindow window;

    // Opt-in Blender sync bridge: `--sync-listen [port]` starts a loopback TCP
    // server that pushes authored physics/ragdoll data into this live session.
    // Add `--headless` to run the event loop without showing the window (Qt4 has
    // no `-platform offscreen`), which is how automated sync tests drive it.
    const QStringList args = app.arguments();
    const bool headless = args.contains(QLatin1String("--headless"));
    if (!headless)
    {
        window.show();
    }

    const int flag_index = args.indexOf(QLatin1String("--sync-listen"));
    if (flag_index >= 0)
    {
        unsigned short port = sync_protocol::kDefaultPort;
        if (flag_index + 1 < args.size())
        {
            bool ok = false;
            const ushort parsed = args.at(flag_index + 1).toUShort(&ok);
            if (ok)
            {
                port = parsed;
            }
        }
        const QString token = QString::fromLocal8Bit(qgetenv(sync_protocol::kTokenEnvVar));
        if (!window.start_sync_listener(port, token))
        {
            std::fprintf(stderr, "sync: failed to listen on 127.0.0.1:%u (%s)\n",
                         static_cast<unsigned>(port),
                         window.sync_listener_last_error().toLocal8Bit().constData());
        }
        else
        {
            std::fprintf(stderr, "sync: listening on 127.0.0.1:%u\n", static_cast<unsigned>(port));
        }
    }

    return app.exec();
}
