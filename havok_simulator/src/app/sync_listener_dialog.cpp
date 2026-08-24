#include "sync_listener_dialog.h"

#include <QDialogButtonBox>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QSpinBox>
#include <QVBoxLayout>
#include <QWidget>

SyncListenerDialog::SyncListenerDialog(QWidget* parent)
    : QDialog(parent)
    , m_port_spin(0)
    , m_state_label(0)
    , m_start_button(0)
    , m_restart_button(0)
    , m_stop_button(0)
    , m_is_listening(false)
{
    QVBoxLayout* main_layout = new QVBoxLayout(this);
    QFormLayout* form_layout = new QFormLayout();
    QDialogButtonBox* close_buttons = new QDialogButtonBox(QDialogButtonBox::Close, Qt::Horizontal, this);
    QWidget* button_row = new QWidget(this);
    QHBoxLayout* button_layout = new QHBoxLayout(button_row);

    setWindowTitle("Sync Listener");

    m_port_spin = new QSpinBox(this);
    m_port_spin->setRange(1, 65535);
    m_port_spin->setValue(47800);

    m_state_label = new QLabel("Listener is stopped.", this);
    m_state_label->setWordWrap(true);

    m_start_button = new QPushButton("Start", this);
    m_restart_button = new QPushButton("Restart", this);
    m_stop_button = new QPushButton("Stop", this);

    button_layout->setContentsMargins(0, 0, 0, 0);
    button_layout->addWidget(m_start_button);
    button_layout->addWidget(m_restart_button);
    button_layout->addWidget(m_stop_button);
    button_layout->addStretch(1);

    form_layout->addRow("Port", m_port_spin);
    form_layout->addRow("Status", m_state_label);

    main_layout->addLayout(form_layout);
    main_layout->addWidget(button_row);
    main_layout->addWidget(close_buttons);

    connect(m_start_button, SIGNAL(clicked()), this, SLOT(emit_start_requested()));
    connect(m_restart_button, SIGNAL(clicked()), this, SLOT(emit_restart_requested()));
    connect(m_stop_button, SIGNAL(clicked()), this, SLOT(emit_stop_requested()));
    connect(close_buttons, SIGNAL(rejected()), this, SLOT(reject()));

    refresh_buttons();
}

unsigned short SyncListenerDialog::port() const
{
    return m_port_spin ? static_cast<unsigned short>(m_port_spin->value()) : 47800;
}

void SyncListenerDialog::set_port(unsigned short port)
{
    if (m_port_spin)
    {
        m_port_spin->setValue(static_cast<int>(port));
    }
}

void SyncListenerDialog::set_listener_state(bool listening, unsigned short port, const QString& message)
{
    m_is_listening = listening;
    set_port(port);

    if (m_state_label)
    {
        if (!message.isEmpty())
        {
            m_state_label->setText(message);
        }
        else if (listening)
        {
            m_state_label->setText(QString("Listening on 127.0.0.1:%1").arg(static_cast<unsigned>(port)));
        }
        else
        {
            m_state_label->setText("Listener is stopped.");
        }
    }

    refresh_buttons();
}

void SyncListenerDialog::emit_start_requested()
{
    emit start_requested(port());
}

void SyncListenerDialog::emit_restart_requested()
{
    emit restart_requested(port());
}

void SyncListenerDialog::emit_stop_requested()
{
    emit stop_requested();
}

void SyncListenerDialog::refresh_buttons()
{
    if (m_start_button)
    {
        m_start_button->setEnabled(!m_is_listening);
    }
    if (m_restart_button)
    {
        m_restart_button->setEnabled(true);
    }
    if (m_stop_button)
    {
        m_stop_button->setEnabled(m_is_listening);
    }
}