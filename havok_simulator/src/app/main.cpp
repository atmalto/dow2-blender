#include <QApplication>

#include "app_theme.h"
#include "main_window.h"

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    configure_application_theme(app);

    MainWindow window;
    window.show();
    return app.exec();
}