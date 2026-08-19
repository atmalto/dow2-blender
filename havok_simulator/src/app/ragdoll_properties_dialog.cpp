#include "tool_dialogs.h"

#include "app_theme.h"
#include "dialog_form_utils.h"

#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QLabel>
#include <QVBoxLayout>

#include "viewport_widget.h"

RagdollPropertiesDialog::RagdollPropertiesDialog(SimulationController* simulation, ViewportWidget* viewport, QWidget* parent)
	: QDialog(parent)
	, m_simulation(simulation)
	, m_viewport(viewport)
	, m_asset_path_label(0)
	, m_position_x_spin(0)
	, m_position_y_spin(0)
	, m_position_z_spin(0)
	, m_edit_entity_id(0)
{
	setWindowTitle("Edit Ragdoll");
	setModal(false);
	resize(420, 220);

	QVBoxLayout* root_layout = new QVBoxLayout(this);
	QFormLayout* form_layout = new QFormLayout();
	QDialogButtonBox* buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, Qt::Horizontal, this);

	m_asset_path_label = new QLabel(this);
	m_asset_path_label->setWordWrap(true);

	m_position_x_spin = new QDoubleSpinBox(this);
	m_position_y_spin = new QDoubleSpinBox(this);
	m_position_z_spin = new QDoubleSpinBox(this);

	m_position_x_spin->setRange(-500.0, 500.0);
	m_position_y_spin->setRange(-500.0, 500.0);
	m_position_z_spin->setRange(-500.0, 500.0);
	m_position_x_spin->setDecimals(2);
	m_position_y_spin->setDecimals(2);
	m_position_z_spin->setDecimals(2);
	m_position_x_spin->setSingleStep(0.25);
	m_position_y_spin->setSingleStep(0.25);
	m_position_z_spin->setSingleStep(0.25);

	form_layout->addRow("Asset", m_asset_path_label);
	form_layout->addRow("Start X", m_position_x_spin);
	form_layout->addRow("Start Y", m_position_y_spin);
	form_layout->addRow("Start Z", m_position_z_spin);

	root_layout->addLayout(form_layout);
	clear_dialog_button_box_icons(buttons);
	root_layout->addWidget(buttons);

	connect(m_position_x_spin, SIGNAL(valueChanged(double)), this, SLOT(update_preview()));
	connect(m_position_y_spin, SIGNAL(valueChanged(double)), this, SLOT(update_preview()));
	connect(m_position_z_spin, SIGNAL(valueChanged(double)), this, SLOT(update_preview()));
	connect(buttons, SIGNAL(accepted()), this, SLOT(accept()));
	connect(buttons, SIGNAL(rejected()), this, SLOT(reject()));
}

RagdollSceneSpec RagdollPropertiesDialog::spec() const
{
	RagdollSceneSpec ragdoll_spec;
	ragdoll_spec.asset_path = m_asset_path;
	DialogFormUtils::assign_user_axes(
		ragdoll_spec.position,
		static_cast<float>(m_position_x_spin->value()),
		static_cast<float>(m_position_y_spin->value()),
		static_cast<float>(m_position_z_spin->value()));
	return ragdoll_spec;
}

void RagdollPropertiesDialog::set_spec(const RagdollSceneSpec& spec)
{
	float ui_x = 0.0f;
	float ui_y = 0.0f;
	float ui_z = 0.0f;

	m_original_spec = spec;
	m_edit_entity_id = m_simulation ? m_simulation->selected_entity().id : 0;
	m_asset_path = spec.asset_path;
	if (m_asset_path_label)
	{
		m_asset_path_label->setText(QString::fromLocal8Bit(spec.asset_path.c_str()));
	}
	if (m_position_x_spin)
	{
		DialogFormUtils::extract_user_axes(spec.position, &ui_x, &ui_y, &ui_z);
		m_position_x_spin->setValue(ui_x);
		m_position_y_spin->setValue(ui_y);
		m_position_z_spin->setValue(ui_z);
	}
}

SceneEntityId RagdollPropertiesDialog::edit_entity_id() const
{
	return m_edit_entity_id;
}

void RagdollPropertiesDialog::done(int result)
{
	if (result != QDialog::Accepted && m_simulation)
	{
		if (m_edit_entity_id != 0)
		{
			m_simulation->select_entity(m_edit_entity_id, SceneEntityKindRagdoll);
		}
		m_simulation->set_ragdoll_start_position(
			m_original_spec.position[0],
			m_original_spec.position[1],
			m_original_spec.position[2]);
	}

	if (m_viewport)
	{
		m_viewport->updateGL();
	}

	QDialog::done(result);
}

void RagdollPropertiesDialog::update_preview()
{
	if (m_simulation)
	{
		float position[3];

		if (m_edit_entity_id != 0)
		{
			m_simulation->select_entity(m_edit_entity_id, SceneEntityKindRagdoll);
		}

		DialogFormUtils::assign_user_axes(
			position,
			static_cast<float>(m_position_x_spin->value()),
			static_cast<float>(m_position_y_spin->value()),
			static_cast<float>(m_position_z_spin->value()));
		m_simulation->set_ragdoll_start_position(
			position[0],
			position[1],
			position[2]);
	}

	if (m_viewport)
	{
		m_viewport->updateGL();
	}
}
