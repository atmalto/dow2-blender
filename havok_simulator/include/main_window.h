#ifndef HAVOK_SCENE_APP_MAIN_WINDOW_H
#define HAVOK_SCENE_APP_MAIN_WINDOW_H

#include <QMainWindow>

class QAction;
class QComboBox;
class QDockWidget;
class QDoubleSpinBox;
class QLabel;
class QMenu;
class QTimer;
class QWidget;
class AddForceDialog;
class AddObjectDialog;
class RagdollPropertiesDialog;
class RagdollPreviewWindow;

class SimulationController;
class ViewportWidget;

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = 0);

private slots:
    void open_new_scene_dialog();
    void load_scene();
    void save_scene();
    void open_ragdoll();
    void import_physics();
    void open_add_object_dialog();
    void open_add_force_dialog();
    void clear_scene();
    void commit_add_object();
    void commit_add_force();
    void commit_edit_object();
    void commit_edit_ragdoll();
    void commit_edit_force();
    void edit_selected_entity();
    void delete_selected_entity();
    void duplicate_selected_entity();
    void deselect_entity();
    void toggle_play_pause();
    void play_simulation();
    void pause_simulation();
    void step_simulation();
    void reset_simulation();
    void open_settings_dialog();
    void ground_mode_changed(int index);
    void entity_selection_changed(int index);
    void duration_limit_changed(int index);
    void ragdoll_start_position_changed();
    void viewport_selection_changed();
    void advance_simulation();

private:
    void create_actions();
    void create_menus();
    void create_toolbar();
    void create_docks();
    void refresh_ui();
    void refresh_ragdoll_preview_window(bool open_for_selected_ragdoll);
    void close_scene_dialogs();

    SimulationController* m_simulation;
    ViewportWidget* m_viewport;
    QAction* m_new_scene_action;
    QAction* m_load_scene_action;
    QAction* m_save_scene_action;
    QAction* m_open_ragdoll_action;
    QAction* m_import_physics_action;
    QAction* m_clear_scene_action;
    QAction* m_add_object_action;
    QAction* m_add_force_action;
    QAction* m_edit_entity_action;
    QAction* m_delete_entity_action;
    QAction* m_duplicate_entity_action;
    QAction* m_play_action;
    QAction* m_pause_action;
    QAction* m_step_action;
    QAction* m_reset_action;
    QAction* m_settings_action;
    QMenu* m_scene_menu;
    QMenu* m_simulation_menu;
    AddObjectDialog* m_add_object_dialog;
    AddObjectDialog* m_edit_object_dialog;
    AddForceDialog* m_add_force_dialog;
    AddForceDialog* m_edit_force_dialog;
    RagdollPropertiesDialog* m_edit_ragdoll_dialog;
    RagdollPreviewWindow* m_ragdoll_preview_window;
    QDockWidget* m_scene_dock;
    QDockWidget* m_simulation_dock;
    QComboBox* m_entity_select_combo;
    QComboBox* m_duration_limit_combo;
    QDoubleSpinBox* m_ragdoll_start_x;
    QDoubleSpinBox* m_ragdoll_start_y;
    QDoubleSpinBox* m_ragdoll_start_z;
    QLabel* m_scene_summary_label;
    QLabel* m_ragdoll_path_label;
    QLabel* m_simulation_summary_label;
    QTimer* m_step_timer;
    float m_elapsed_simulation_time;
    float m_simulation_duration_limit_seconds;
};

#endif