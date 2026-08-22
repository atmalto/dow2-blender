#ifndef HAVOK_SCENE_APP_TOOL_DIALOGS_H
#define HAVOK_SCENE_APP_TOOL_DIALOGS_H

#include <QDialog>

#include "simulation_controller.h"

class QComboBox;
class QDoubleSpinBox;
class QLabel;
class QSlider;
class ViewportWidget;

class AddObjectDialog : public QDialog
{
    Q_OBJECT

public:
    AddObjectDialog(SimulationController* simulation, ViewportWidget* viewport, QWidget* parent = 0);

    SimulationController::SpawnedObjectSpec spec() const;
    void set_spec(const SimulationController::SpawnedObjectSpec& spec);
    SceneEntityId edit_entity_id() const;

protected:
    virtual void done(int result);

private slots:
    void update_preview();
    void object_type_changed(int index);

private:
    float position_value(const QSlider* slider) const;
    float rotation_value(const QSlider* slider) const;
    float scale_value(const QSlider* slider) const;
    void refresh_value_labels();

    SimulationController* m_simulation;
    ViewportWidget* m_viewport;
    QComboBox* m_type_combo;
    QComboBox* m_body_type_combo;
    QSlider* m_position_x_slider;
    QSlider* m_position_y_slider;
    QSlider* m_position_z_slider;
    QLabel* m_position_x_value;
    QLabel* m_position_y_value;
    QLabel* m_position_z_value;
    QSlider* m_rotation_x_slider;
    QSlider* m_rotation_y_slider;
    QSlider* m_rotation_z_slider;
    QLabel* m_rotation_x_value;
    QLabel* m_rotation_y_value;
    QLabel* m_rotation_z_value;
    QSlider* m_scale_x_slider;
    QSlider* m_scale_y_slider;
    QSlider* m_scale_z_slider;
    QLabel* m_scale_x_value;
    QLabel* m_scale_y_value;
    QLabel* m_scale_z_value;
    QDoubleSpinBox* m_restitution_spin;
    QDoubleSpinBox* m_mass_spin;
    SimulationController::SpawnedObjectSpec m_original_spec;
    bool m_is_edit_session;
    SceneEntityId m_edit_entity_id;
};

class RagdollPropertiesDialog : public QDialog
{
    Q_OBJECT

public:
    RagdollPropertiesDialog(SimulationController* simulation, ViewportWidget* viewport, QWidget* parent = 0);

    RagdollSceneSpec spec() const;
    void set_spec(const RagdollSceneSpec& spec);
    SceneEntityId edit_entity_id() const;

protected:
    virtual void done(int result);

private slots:
    void update_preview();

private:
    SimulationController* m_simulation;
    ViewportWidget* m_viewport;
    QLabel* m_asset_path_label;
    QDoubleSpinBox* m_position_x_spin;
    QDoubleSpinBox* m_position_y_spin;
    QDoubleSpinBox* m_position_z_spin;
    std::string m_asset_path;
    RagdollSceneSpec m_original_spec;
    SceneEntityId m_edit_entity_id;
};

class AddForceDialog : public QDialog
{
    Q_OBJECT

public:
    AddForceDialog(SimulationController* simulation, ViewportWidget* viewport, QWidget* parent = 0);

    SimulationController::ForceSpec spec() const;
    void set_spec(const SimulationController::ForceSpec& spec);
    SceneEntityId edit_entity_id() const;

protected:
    virtual void done(int result);

private slots:
    void update_preview();

private:
    float position_value(const QSlider* slider) const;
    float rotation_value(const QSlider* slider) const;
    void refresh_value_labels();

    SimulationController* m_simulation;
    ViewportWidget* m_viewport;
    QComboBox* m_mode_combo;
    QSlider* m_position_x_slider;
    QSlider* m_position_y_slider;
    QSlider* m_position_z_slider;
    QLabel* m_position_x_value;
    QLabel* m_position_y_value;
    QLabel* m_position_z_value;
    QSlider* m_rotation_x_slider;
    QSlider* m_rotation_y_slider;
    QSlider* m_rotation_z_slider;
    QLabel* m_rotation_x_value;
    QLabel* m_rotation_y_value;
    QLabel* m_rotation_z_value;
    QDoubleSpinBox* m_strength_spin;
    QDoubleSpinBox* m_radius_spin;
    SimulationController::ForceSpec m_original_spec;
    bool m_is_edit_session;
    SceneEntityId m_edit_entity_id;
};

class SimulationSettingsDialog : public QDialog
{
    Q_OBJECT

public:
    SimulationSettingsDialog(QWidget* parent = 0);

private slots:
    void ragdoll_scale_changed(int slider_value);
    void gravity_scale_changed(int slider_value);

private:
    void refresh_labels();

    QSlider* m_ragdoll_scale_slider;
    QSlider* m_gravity_scale_slider;
    QLabel* m_ragdoll_scale_value;
    QLabel* m_gravity_scale_value;
};

#endif
