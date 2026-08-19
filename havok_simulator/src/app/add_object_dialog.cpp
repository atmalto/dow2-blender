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

AddObjectDialog::AddObjectDialog(SimulationController* simulation, ViewportWidget* viewport, QWidget* parent)
    : QDialog(parent)
    , m_simulation(simulation)
    , m_viewport(viewport)
    , m_type_combo(0)
    , m_body_type_combo(0)
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
    , m_scale_x_slider(0)
    , m_scale_y_slider(0)
    , m_scale_z_slider(0)
    , m_scale_x_value(0)
    , m_scale_y_value(0)
    , m_scale_z_value(0)
    , m_restitution_spin(0)
    , m_mass_spin(0)
    , m_is_edit_session(false)
    , m_edit_entity_id(0)
{
    setWindowTitle("Add Object");
    setModal(false);
    resize(620, 420);

    QVBoxLayout* root_layout = new QVBoxLayout(this);
    QFormLayout* form_layout = new QFormLayout();
    QGroupBox* position_group = new QGroupBox("Position");
    QGroupBox* rotation_group = new QGroupBox("Orientation");
    QGroupBox* scale_group = new QGroupBox("Scale");
    QGridLayout* position_layout = new QGridLayout(position_group);
    QGridLayout* rotation_layout = new QGridLayout(rotation_group);
    QGridLayout* scale_layout = new QGridLayout(scale_group);
    QDialogButtonBox* buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, Qt::Horizontal, this);

    m_type_combo = new QComboBox(this);
    m_type_combo->addItem("Cube");
    m_type_combo->addItem("Sphere");
    m_type_combo->addItem("Wedge");

    m_body_type_combo = new QComboBox(this);
    m_body_type_combo->addItem("Dynamic");
    m_body_type_combo->addItem("Static");

    m_restitution_spin = new QDoubleSpinBox(this);
    m_restitution_spin->setRange(0.0, 1.0);
    m_restitution_spin->setDecimals(2);
    m_restitution_spin->setSingleStep(0.05);
    m_restitution_spin->setValue(0.15);

    m_mass_spin = new QDoubleSpinBox(this);
    m_mass_spin->setRange(0.1, 100000.0);
    m_mass_spin->setDecimals(2);
    m_mass_spin->setSingleStep(0.5);
    m_mass_spin->setValue(10.0);

    form_layout->addRow("Type", m_type_combo);
    form_layout->addRow("Rigid Body", m_body_type_combo);
    form_layout->addRow("Restitution", m_restitution_spin);
    form_layout->addRow("Mass", m_mass_spin);

    const DialogFormUtils::SliderRow position_x = DialogFormUtils::add_slider_row(position_layout, 0, "X", -400, 400, 0, 10);
    const DialogFormUtils::SliderRow position_y = DialogFormUtils::add_slider_row(position_layout, 1, "Y", -400, 400, 0, 10);
    const DialogFormUtils::SliderRow position_z = DialogFormUtils::add_slider_row(position_layout, 2, "Z", -400, 400, 60, 10);
    m_position_x_slider = position_x.slider;
    m_position_y_slider = position_y.slider;
    m_position_z_slider = position_z.slider;
    m_position_x_value = position_x.value_label;
    m_position_y_value = position_y.value_label;
    m_position_z_value = position_z.value_label;

    const DialogFormUtils::SliderRow rotation_x = DialogFormUtils::add_slider_row(rotation_layout, 0, "Pitch X", -3600, 3600, 0, 100);
    const DialogFormUtils::SliderRow rotation_y = DialogFormUtils::add_slider_row(rotation_layout, 1, "Rotate Y", -3600, 3600, 0, 100);
    const DialogFormUtils::SliderRow rotation_z = DialogFormUtils::add_slider_row(rotation_layout, 2, "Rotate Z", -3600, 3600, 0, 100);
    m_rotation_x_slider = rotation_x.slider;
    m_rotation_y_slider = rotation_y.slider;
    m_rotation_z_slider = rotation_z.slider;
    m_rotation_x_value = rotation_x.value_label;
    m_rotation_y_value = rotation_y.value_label;
    m_rotation_z_value = rotation_z.value_label;

    const DialogFormUtils::SliderRow scale_x = DialogFormUtils::add_slider_row(scale_layout, 0, "Scale X", 1, 40, 3, 1);
    const DialogFormUtils::SliderRow scale_y = DialogFormUtils::add_slider_row(scale_layout, 1, "Scale Y", 1, 40, 3, 1);
    const DialogFormUtils::SliderRow scale_z = DialogFormUtils::add_slider_row(scale_layout, 2, "Scale Z", 1, 40, 3, 1);
    m_scale_x_slider = scale_x.slider;
    m_scale_y_slider = scale_y.slider;
    m_scale_z_slider = scale_z.slider;
    m_scale_x_value = scale_x.value_label;
    m_scale_y_value = scale_y.value_label;
    m_scale_z_value = scale_z.value_label;

    root_layout->addLayout(form_layout);
    root_layout->addWidget(position_group);
    root_layout->addWidget(rotation_group);
    root_layout->addWidget(scale_group);
    clear_dialog_button_box_icons(buttons);
    root_layout->addWidget(buttons);

    connect(m_type_combo, SIGNAL(currentIndexChanged(int)), this, SLOT(object_type_changed(int)));
    connect(m_body_type_combo, SIGNAL(currentIndexChanged(int)), this, SLOT(update_preview()));
    connect(m_position_x_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_position_y_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_position_z_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_rotation_x_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_rotation_y_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_rotation_z_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_scale_x_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_scale_y_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_scale_z_slider, SIGNAL(valueChanged(int)), this, SLOT(update_preview()));
    connect(m_restitution_spin, SIGNAL(valueChanged(double)), this, SLOT(update_preview()));
    connect(m_mass_spin, SIGNAL(valueChanged(double)), this, SLOT(update_preview()));
    connect(buttons, SIGNAL(accepted()), this, SLOT(accept()));
    connect(buttons, SIGNAL(rejected()), this, SLOT(reject()));

    object_type_changed(0);
    refresh_value_labels();
    update_preview();
}

SimulationController::SpawnedObjectSpec AddObjectDialog::spec() const
{
    SimulationController::SpawnedObjectSpec object_spec;
    object_spec.object_type = static_cast<SimulationController::ObjectType>(m_type_combo->currentIndex());
    object_spec.body_type = static_cast<SimulationController::RigidBodyType>(m_body_type_combo->currentIndex());
    DialogFormUtils::assign_user_axes(
        object_spec.position,
        position_value(m_position_x_slider),
        position_value(m_position_y_slider),
        position_value(m_position_z_slider));
    DialogFormUtils::assign_user_axes(
        object_spec.rotation_degrees,
        rotation_value(m_rotation_x_slider),
        rotation_value(m_rotation_y_slider),
        rotation_value(m_rotation_z_slider));
    object_spec.scale[0] = scale_value(m_scale_x_slider);
    object_spec.scale[1] = scale_value(m_scale_y_slider);
    object_spec.scale[2] = scale_value(m_scale_z_slider);
    object_spec.restitution = static_cast<float>(m_restitution_spin->value());
    object_spec.mass = static_cast<float>(m_mass_spin->value());

    if (object_spec.object_type == SimulationController::ObjectSphere)
    {
        object_spec.scale[1] = object_spec.scale[0];
        object_spec.scale[2] = object_spec.scale[0];
    }

    return object_spec;
}

void AddObjectDialog::set_spec(const SimulationController::SpawnedObjectSpec& spec)
{
    float ui_x = 0.0f;
    float ui_y = 0.0f;
    float ui_z = 0.0f;

    m_is_edit_session = true;
    m_original_spec = spec;
    m_edit_entity_id = m_simulation ? m_simulation->selected_entity().id : 0;

    if (m_type_combo)
    {
        m_type_combo->blockSignals(true);
        m_type_combo->setCurrentIndex(spec.object_type);
        m_type_combo->blockSignals(false);
    }
    if (m_body_type_combo)
    {
        m_body_type_combo->blockSignals(true);
        m_body_type_combo->setCurrentIndex(spec.body_type);
        m_body_type_combo->blockSignals(false);
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
    if (m_scale_x_slider)
    {
        m_scale_x_slider->blockSignals(true);
        m_scale_y_slider->blockSignals(true);
        m_scale_z_slider->blockSignals(true);
        m_scale_x_slider->setValue(static_cast<int>(spec.scale[0] / 0.25f));
        m_scale_y_slider->setValue(static_cast<int>(spec.scale[1] / 0.25f));
        m_scale_z_slider->setValue(static_cast<int>(spec.scale[2] / 0.25f));
        m_scale_x_slider->blockSignals(false);
        m_scale_y_slider->blockSignals(false);
        m_scale_z_slider->blockSignals(false);
    }
    if (m_restitution_spin)
    {
        m_restitution_spin->blockSignals(true);
        m_restitution_spin->setValue(spec.restitution);
        m_restitution_spin->blockSignals(false);
    }
    if (m_mass_spin)
    {
        m_mass_spin->blockSignals(true);
        m_mass_spin->setValue(spec.mass);
        m_mass_spin->blockSignals(false);
    }

    object_type_changed(spec.object_type);
    refresh_value_labels();

    if (m_simulation)
    {
        m_simulation->clear_object_preview();
        m_simulation->set_object_preview(spec);
    }

    if (m_viewport)
    {
        m_viewport->updateGL();
    }
}

SceneEntityId AddObjectDialog::edit_entity_id() const
{
    return m_edit_entity_id;
}

void AddObjectDialog::done(int result)
{
    if (m_simulation)
    {
        m_simulation->clear_object_preview();
    }
    if (m_viewport)
    {
        m_viewport->updateGL();
    }
    QDialog::done(result);
}

void AddObjectDialog::update_preview()
{
    if (m_type_combo && m_type_combo->currentIndex() == SimulationController::ObjectSphere)
    {
        m_scale_y_slider->blockSignals(true);
        m_scale_z_slider->blockSignals(true);
        m_scale_y_slider->setValue(m_scale_x_slider->value());
        m_scale_z_slider->setValue(m_scale_x_slider->value());
        m_scale_y_slider->blockSignals(false);
        m_scale_z_slider->blockSignals(false);
    }

    refresh_value_labels();

    if (m_body_type_combo && m_mass_spin)
    {
        const bool is_dynamic = m_body_type_combo->currentIndex() == SimulationController::BodyDynamic;
        m_mass_spin->setEnabled(is_dynamic);
    }

    if (m_simulation)
    {
        m_simulation->set_object_preview(spec());
    }
    if (m_viewport)
    {
        m_viewport->updateGL();
    }
}

void AddObjectDialog::object_type_changed(int index)
{
    const bool is_sphere = index == SimulationController::ObjectSphere;
    if (m_scale_y_slider)
    {
        m_scale_y_slider->setEnabled(!is_sphere);
    }
    if (m_scale_z_slider)
    {
        m_scale_z_slider->setEnabled(!is_sphere);
    }

    if (is_sphere)
    {
        m_scale_y_slider->setValue(m_scale_x_slider->value());
        m_scale_z_slider->setValue(m_scale_x_slider->value());
    }

    update_preview();
}

float AddObjectDialog::position_value(const QSlider* slider) const
{
    return slider ? static_cast<float>(slider->value()) * DialogFormUtils::kPositionSliderScale : 0.0f;
}

float AddObjectDialog::rotation_value(const QSlider* slider) const
{
    return slider ? static_cast<float>(slider->value()) * DialogFormUtils::kRotationSliderScale : 0.0f;
}

float AddObjectDialog::scale_value(const QSlider* slider) const
{
    return slider ? static_cast<float>(slider->value()) * 0.25f : 1.0f;
}

void AddObjectDialog::refresh_value_labels()
{
    if (m_position_x_value)
    {
        m_position_x_value->setText(QString::number(position_value(m_position_x_slider), 'f', 1));
        m_position_y_value->setText(QString::number(position_value(m_position_y_slider), 'f', 1));
        m_position_z_value->setText(QString::number(position_value(m_position_z_slider), 'f', 1));
        m_rotation_x_value->setText(QString::number(rotation_value(m_rotation_x_slider), 'f', 1));
        m_rotation_y_value->setText(QString::number(rotation_value(m_rotation_y_slider), 'f', 1));
        m_rotation_z_value->setText(QString::number(rotation_value(m_rotation_z_slider), 'f', 1));
        m_scale_x_value->setText(QString::number(scale_value(m_scale_x_slider), 'f', 2));
        m_scale_y_value->setText(QString::number(scale_value(m_scale_y_slider), 'f', 2));
        m_scale_z_value->setText(QString::number(scale_value(m_scale_z_slider), 'f', 2));
    }
}