#include "tool_dialogs.h"

#include "app_theme.h"
#include "dialog_form_utils.h"

#include <QComboBox>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QLabel>
#include <QSlider>
#include <QVBoxLayout>

#include "viewport_widget.h"

AddForceDialog::AddForceDialog(SimulationController* simulation, ViewportWidget* viewport, QWidget* parent)
    : QDialog(parent)
    , m_simulation(simulation)
    , m_viewport(viewport)
    , m_mode_combo(0)
    , m_position_x_slider(0)
    , m_position_y_slider(0)
    , m_position_z_slider(0)
    , m_position_x_value(0)
    , m_position_y_value(0)
    , m_position_z_value(0)
    , m_rotation_x_slider(0)
    , m_rotation_y_slider(0)
    , m_rotation_z_slider(0)
    , m_rotation_x_value(0)
    , m_rotation_y_value(0)
    , m_rotation_z_value(0)
    , m_strength_spin(0)
    , m_is_edit_session(false)
    , m_edit_entity_id(0)
{
    setWindowTitle("Add Force");
    setModal(false);
    resize(620, 340);

    QVBoxLayout* root_layout = new QVBoxLayout(this);
    m_mode_combo = new QComboBox(this);
    m_mode_combo->addItem("Push");
    m_mode_combo->addItem("Pull");
    QGroupBox* position_group = new QGroupBox("Position");
    QGroupBox* rotation_group = new QGroupBox("Orientation");
    QGridLayout* position_layout = new QGridLayout(position_group);
    QGridLayout* rotation_layout = new QGridLayout(rotation_group);
    QFormLayout* form_layout = new QFormLayout();
    QDialogButtonBox* buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, Qt::Horizontal, this);

    const DialogFormUtils::SliderRow position_x = DialogFormUtils::add_slider_row(position_layout, 0, "X", -400, 400, 0, 10);
    const DialogFormUtils::SliderRow position_y = DialogFormUtils::add_slider_row(position_layout, 1, "Y", -400, 400, 80, 10);
    const DialogFormUtils::SliderRow position_z = DialogFormUtils::add_slider_row(position_layout, 2, "Z", -400, 400, 100, 10);
    m_position_x_slider = position_x.slider;
    m_position_y_slider = position_y.slider;
    m_position_z_slider = position_z.slider;
    m_position_x_value = position_x.value_label;
    m_position_y_value = position_y.value_label;
    m_position_z_value = position_z.value_label;

    const DialogFormUtils::SliderRow rotation_x = DialogFormUtils::add_slider_row(rotation_layout, 0, "Pitch X", -3600, 3600, -900, 100);
    const DialogFormUtils::SliderRow rotation_y = DialogFormUtils::add_slider_row(rotation_layout, 1, "Rotate Y", -3600, 3600, 0, 100);
    const DialogFormUtils::SliderRow rotation_z = DialogFormUtils::add_slider_row(rotation_layout, 2, "Rotate Z", -3600, 3600, 0, 100);
    m_rotation_x_slider = rotation_x.slider;
    m_rotation_y_slider = rotation_y.slider;
    m_rotation_z_slider = rotation_z.slider;
    m_rotation_x_value = rotation_x.value_label;
    m_rotation_y_value = rotation_y.value_label;
    m_rotation_z_value = rotation_z.value_label;

    m_strength_spin = new QDoubleSpinBox(this);
    m_strength_spin->setRange(5.0, 100000.0);
    m_strength_spin->setDecimals(1);
    m_strength_spin->setSingleStep(10.0);
    m_strength_spin->setValue(180.0);

    form_layout->addRow("Mode", m_mode_combo);
    form_layout->addRow("Strength", m_strength_spin);

    root_layout->addLayout(form_layout);
    root_layout->addWidget(position_group);
    root_layout->addWidget(rotation_group);
    clear_dialog_button_box_icons(buttons);
    root_layout->addWidget(buttons);

    connect(m_mode_combo, SIGNAL(currentIndexChanged(int)), this, SLOT(update_preview()));
    connect(m_position_x_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_position_y_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_position_z_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_rotation_x_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_rotation_y_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_rotation_z_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_strength_spin, SIGNAL(valueChanged(double)), this, SLOT(update_preview()));
    connect(buttons, SIGNAL(accepted()), this, SLOT(accept()));
    connect(buttons, SIGNAL(rejected()), this, SLOT(reject()));

    refresh_value_labels();
    update_preview();
}

SimulationController::ForceSpec AddForceDialog::spec() const
{
    SimulationController::ForceSpec force_spec;
    DialogFormUtils::assign_user_axes(
        force_spec.position,
        position_value(m_position_x_slider),
        position_value(m_position_y_slider),
        position_value(m_position_z_slider));
    DialogFormUtils::assign_user_axes(
        force_spec.rotation_degrees,
        rotation_value(m_rotation_x_slider),
        rotation_value(m_rotation_y_slider),
        rotation_value(m_rotation_z_slider));
    force_spec.strength = static_cast<float>(m_strength_spin->value());
    force_spec.mode = m_mode_combo ? m_mode_combo->currentIndex() : SimulationController::ForcePush;
    force_spec.active = true;
    return force_spec;
}

void AddForceDialog::set_spec(const SimulationController::ForceSpec& spec)
{
    float ui_x = 0.0f;
    float ui_y = 0.0f;
    float ui_z = 0.0f;

    m_is_edit_session = true;
    m_original_spec = spec;
    m_edit_entity_id = m_simulation ? m_simulation->selected_entity().id : 0;

    if (m_mode_combo)
    {
        m_mode_combo->blockSignals(true);
        m_mode_combo->setCurrentIndex(spec.mode);
        m_mode_combo->blockSignals(false);
    }
    if (m_position_x_slider)
    {
        DialogFormUtils::extract_user_axes(spec.position, &ui_x, &ui_y, &ui_z);

        m_position_x_slider->blockSignals(true);
        m_position_y_slider->blockSignals(true);
        m_position_z_slider->blockSignals(true);
        m_position_x_slider->setValue(static_cast<int>(ui_x / DialogFormUtils::kPositionSliderScale));
        m_position_y_slider->setValue(static_cast<int>(ui_y / DialogFormUtils::kPositionSliderScale));
        m_position_z_slider->setValue(static_cast<int>(ui_z / DialogFormUtils::kPositionSliderScale));
        m_position_x_slider->blockSignals(false);
        m_position_y_slider->blockSignals(false);
        m_position_z_slider->blockSignals(false);
    }
    if (m_rotation_x_slider)
    {
        DialogFormUtils::extract_user_axes(spec.rotation_degrees, &ui_x, &ui_y, &ui_z);

        m_rotation_x_slider->blockSignals(true);
        m_rotation_y_slider->blockSignals(true);
        m_rotation_z_slider->blockSignals(true);
        m_rotation_x_slider->setValue(static_cast<int>(ui_x / DialogFormUtils::kRotationSliderScale));
        m_rotation_y_slider->setValue(static_cast<int>(ui_y / DialogFormUtils::kRotationSliderScale));
        m_rotation_z_slider->setValue(static_cast<int>(ui_z / DialogFormUtils::kRotationSliderScale));
        m_rotation_x_slider->blockSignals(false);
        m_rotation_y_slider->blockSignals(false);
        m_rotation_z_slider->blockSignals(false);
    }
    if (m_strength_spin)
    {
        m_strength_spin->blockSignals(true);
        m_strength_spin->setValue(spec.strength);
        m_strength_spin->blockSignals(false);
    }

    refresh_value_labels();

    if (m_simulation)
    {
        if (m_edit_entity_id != 0)
        {
            m_simulation->select_entity(m_edit_entity_id, SceneEntityKindForce);
        }
        m_simulation->clear_force_preview();
        m_simulation->set_selected_force_preview(spec, 0);
    }

    if (m_viewport)
    {
        m_viewport->updateGL();
    }
}

SceneEntityId AddForceDialog::edit_entity_id() const
{
    return m_edit_entity_id;
}

void AddForceDialog::done(int result)
{
    if (m_simulation)
    {
        if (m_is_edit_session)
        {
            if (m_edit_entity_id != 0)
            {
                m_simulation->select_entity(m_edit_entity_id, SceneEntityKindForce);
            }

            if (result != QDialog::Accepted)
            {
                m_simulation->set_selected_force_preview(m_original_spec, 0);
            }
        }
        else
        {
            m_simulation->clear_force_preview();
        }
    }
    if (m_viewport)
    {
        m_viewport->updateGL();
    }
    QDialog::done(result);
}

void AddForceDialog::update_preview()
{
    refresh_value_labels();

    if (m_simulation)
    {
        if (m_is_edit_session)
        {
            if (m_edit_entity_id != 0)
            {
                m_simulation->select_entity(m_edit_entity_id, SceneEntityKindForce);
            }
            m_simulation->set_selected_force_preview(spec(), 0);
        }
        else
        {
            m_simulation->set_force_preview(spec());
        }
    }
    if (m_viewport)
    {
        m_viewport->updateGL();
    }
}

float AddForceDialog::position_value(const QSlider* slider) const
{
    return slider ? static_cast<float>(slider->value()) * DialogFormUtils::kPositionSliderScale : 0.0f;
}

float AddForceDialog::rotation_value(const QSlider* slider) const
{
    return slider ? static_cast<float>(slider->value()) * DialogFormUtils::kRotationSliderScale : 0.0f;
}

void AddForceDialog::refresh_value_labels()
{
    if (m_position_x_value)
    {
        m_position_x_value->setText(QString::number(position_value(m_position_x_slider), 'f', 1));
        m_position_y_value->setText(QString::number(position_value(m_position_y_slider), 'f', 1));
        m_position_z_value->setText(QString::number(position_value(m_position_z_slider), 'f', 1));
        m_rotation_x_value->setText(QString::number(rotation_value(m_rotation_x_slider), 'f', 1));
        m_rotation_y_value->setText(QString::number(rotation_value(m_rotation_y_slider), 'f', 1));
        m_rotation_z_value->setText(QString::number(rotation_value(m_rotation_z_slider), 'f', 1));
    }
}