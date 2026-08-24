#include "main_window.h"

#include <QDialog>
#include <QStatusBar>

#include "new_scene_dialog.h"
#include "scene_file_commands.h"
#include "scene_presets.h"
#include "simulation_controller.h"

void MainWindow::open_new_scene_dialog()
{
    std::string error_message;

    if (!ensure_can_author_scene("Reset simulation before creating a new scene"))
    {
        return;
    }

    NewSceneDialog dialog(this);
    if (dialog.exec() != QDialog::Accepted)
    {
        return;
    }

    close_scene_dialogs();
    stop_simulation_timer();

    if (!m_simulation->create_scene_from_preset(dialog.selected_preset(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        show_failure(QString("New scene failed: %1").arg(failure_message), "New Scene Failed", failure_message);
        return;
    }

    refresh_after_scene_change(false);
    statusBar()->showMessage(QString("Created new scene: %1").arg(scene_preset_label(dialog.selected_preset())));
}

void MainWindow::load_scene()
{
    SceneFileCommands file_commands(*this, *statusBar(), *m_simulation);
    QString file_path;

    if (!file_commands.begin_load_scene(&file_path))
    {
        return;
    }

    close_scene_dialogs();
    stop_simulation_timer();

    if (!file_commands.finish_load_scene(file_path))
    {
        return;
    }

    refresh_after_scene_change(false);
}

void MainWindow::save_scene()
{
    SceneFileCommands file_commands(*this, *statusBar(), *m_simulation);
    file_commands.save_scene();
}

void MainWindow::open_ragdoll()
{
    SceneFileCommands file_commands(*this, *statusBar(), *m_simulation);
    if (!file_commands.open_ragdoll())
    {
        return;
    }

    refresh_after_scene_change(true);
}

void MainWindow::clear_scene()
{
    close_scene_dialogs();

    stop_simulation_timer();
    m_simulation->clear_scene();
    refresh_after_scene_change(false);
    statusBar()->showMessage("Scene cleared");
}

void MainWindow::import_physics()
{
    SceneFileCommands file_commands(*this, *statusBar(), *m_simulation);
    if (!file_commands.import_physics())
    {
        return;
    }

    reset_elapsed_time();
    refresh_view_state();
}