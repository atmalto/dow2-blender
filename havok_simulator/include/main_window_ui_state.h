#ifndef HAVOK_SCENE_APP_MAIN_WINDOW_UI_STATE_H
#define HAVOK_SCENE_APP_MAIN_WINDOW_UI_STATE_H

class QAction;
class QComboBox;
class QDoubleSpinBox;
class QLabel;

class SimulationController;

struct MainWindowUiView
{
    QAction* play_action;
    QAction* pause_action;
    QAction* step_action;
    QAction* reset_action;
    QAction* new_scene_action;
    QAction* load_scene_action;
    QAction* save_scene_action;
    QAction* open_ragdoll_action;
    QAction* import_physics_action;
    QAction* add_object_action;
    QAction* edit_entity_action;
    QAction* duplicate_entity_action;
    QAction* delete_entity_action;
    QAction* clear_scene_action;
    QComboBox* entity_select_combo;
    QDoubleSpinBox* ragdoll_start_x;
    QDoubleSpinBox* ragdoll_start_y;
    QDoubleSpinBox* ragdoll_start_z;
    QLabel* scene_summary_label;
    QLabel* ragdoll_path_label;
    QLabel* simulation_summary_label;
};

class MainWindowUiState
{
public:
    static void apply(
        SimulationController& simulation,
        const MainWindowUiView& view,
        float elapsed_simulation_time,
        float simulation_duration_limit_seconds);
};

#endif