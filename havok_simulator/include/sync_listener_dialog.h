#ifndef HAVOK_SCENE_APP_SYNC_LISTENER_DIALOG_H
#define HAVOK_SCENE_APP_SYNC_LISTENER_DIALOG_H

#include <QDialog>

class QLabel;
class QPushButton;
class QSpinBox;

class SyncListenerDialog : public QDialog
{
    Q_OBJECT

public:
    explicit SyncListenerDialog(QWidget* parent = 0);

    unsigned short port() const;
    void set_port(unsigned short port);
    void set_listener_state(bool listening, unsigned short port, const QString& message);

signals:
    void start_requested(unsigned short port);
    void restart_requested(unsigned short port);
    void stop_requested();

private slots:
    void emit_start_requested();
    void emit_restart_requested();
    void emit_stop_requested();

private:
    void refresh_buttons();

    QSpinBox* m_port_spin;
    QLabel* m_state_label;
    QPushButton* m_start_button;
    QPushButton* m_restart_button;
    QPushButton* m_stop_button;
    bool m_is_listening;
};

#endif