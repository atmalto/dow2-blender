#include "tool_dialogs.h"

#include "app_theme.h"

#include <QDialogButtonBox>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QSlider>
#include <QVBoxLayout>
#include <QWidget>

#include "simulation_settings.h"

namespace
{
    const int kSettingsSliderStepsPerUnit = 20;
}

SimulationSettingsDialog::SimulationSettingsDialog(QWidget* parent)
    : QDialog(parent)
    , m_ragdoll_scale_slider(0)
    , m_gravity_scale_slider(0)
    , m_ragdoll_scale_value(0)
    , m_gravity_scale_value(0)
{
    SimulationSettings& settings = SimulationSettings::instance();
    QVBoxLayout* main_layout = new QVBoxLayout(this);
    QFormLayout* form_layout = new QFormLayout();
    QDialogButtonBox* buttons = new QDialogButtonBox(QDialogButtonBox::Close, Qt::Horizontal, this);
    QWidget* ragdoll_row = new QWidget(this);
    QWidget* gravity_row = new QWidget(this);
    QHBoxLayout* ragdoll_row_layout = new QHBoxLayout(ragdoll_row);
    QHBoxLayout* gravity_row_layout = new QHBoxLayout(gravity_row);

    setWindowTitle("Simulation Settings");

    m_ragdoll_scale_slider = new QSlider(Qt::Horizontal, this);
    m_ragdoll_scale_slider->setRange(1, 20);
    m_ragdoll_scale_slider->setSingleStep(1);
    m_ragdoll_scale_slider->setPageStep(1);
    m_ragdoll_scale_slider->setValue(
        static_cast<int>(settings.ragdoll_mass_scale() * kSettingsSliderStepsPerUnit + 0.5f));
    m_ragdoll_scale_value = new QLabel(this);
    m_ragdoll_scale_value->setMinimumWidth(48);
    ragdoll_row_layout->setContentsMargins(0, 0, 0, 0);
    ragdoll_row_layout->addWidget(m_ragdoll_scale_slider);
    ragdoll_row_layout->addWidget(m_ragdoll_scale_value);

    m_gravity_scale_slider = new QSlider(Qt::Horizontal, this);
    m_gravity_scale_slider->setRange(0, 40);
    m_gravity_scale_slider->setSingleStep(1);
    m_gravity_scale_slider->setPageStep(1);
    m_gravity_scale_slider->setValue(
        static_cast<int>(settings.gravity_scale() * kSettingsSliderStepsPerUnit + 0.5f));
    m_gravity_scale_value = new QLabel(this);
    m_gravity_scale_value->setMinimumWidth(48);
    gravity_row_layout->setContentsMargins(0, 0, 0, 0);
    gravity_row_layout->addWidget(m_gravity_scale_slider);
    gravity_row_layout->addWidget(m_gravity_scale_value);

    form_layout->addRow("Ragdoll Weight Scale", ragdoll_row);
    form_layout->addRow("Gravity Scale", gravity_row);

    main_layout->addLayout(form_layout);
    clear_dialog_button_box_icons(buttons);
    main_layout->addWidget(buttons);

    connect(m_ragdoll_scale_slider, SIGNAL(valueChanged(int)), this, SLOT(ragdoll_scale_changed(int)));
    connect(m_gravity_scale_slider, SIGNAL(valueChanged(int)), this, SLOT(gravity_scale_changed(int)));
    connect(buttons, SIGNAL(rejected()), this, SLOT(reject()));
    connect(buttons, SIGNAL(accepted()), this, SLOT(accept()));

    refresh_labels();
}

void SimulationSettingsDialog::ragdoll_scale_changed(int slider_value)
{
    SimulationSettings::instance().set_ragdoll_mass_scale(
        static_cast<float>(slider_value) / static_cast<float>(kSettingsSliderStepsPerUnit));
    refresh_labels();
}

void SimulationSettingsDialog::gravity_scale_changed(int slider_value)
{
    SimulationSettings::instance().set_gravity_scale(
        static_cast<float>(slider_value) / static_cast<float>(kSettingsSliderStepsPerUnit));
    refresh_labels();
}

void SimulationSettingsDialog::refresh_labels()
{
    SimulationSettings& settings = SimulationSettings::instance();

    if (m_ragdoll_scale_value)
    {
        m_ragdoll_scale_value->setText(QString::number(settings.ragdoll_mass_scale(), 'f', 2));
    }
    if (m_gravity_scale_value)
    {
        m_gravity_scale_value->setText(QString::number(settings.gravity_scale(), 'f', 2));
    }
}