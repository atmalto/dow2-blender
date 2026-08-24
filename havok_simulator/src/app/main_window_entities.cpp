#include "main_window.h"

#include <QStatusBar>

#include "simulation_controller.h"
#include "tool_dialogs.h"
#include "viewport_widget.h"

namespace
{
    template <typename DialogT>
    DialogT* ensure_non_modal_dialog(
        DialogT*& dialog,
        SimulationController* simulation,
        ViewportWidget* viewport,
        MainWindow* window,
        const char* accepted_slot)
    {
        if (!dialog)
        {
            dialog = new DialogT(simulation, viewport, window);
            dialog->setWindowModality(Qt::NonModal);
            window->connect(dialog, SIGNAL(accepted()), window, accepted_slot);
        }

        return dialog;
    }
}

void MainWindow::open_add_object_dialog()
{
    if (!ensure_can_author_scene("Reset simulation before changing scene entities"))
    {
        return;
    }

    ensure_non_modal_dialog(m_add_object_dialog, m_simulation, m_viewport, this, SLOT(commit_add_object()));

    show_non_modal_dialog(m_add_object_dialog);
}

void MainWindow::open_add_force_dialog()
{
    if (!ensure_can_author_scene("Reset simulation before changing scene entities"))
    {
        return;
    }

    ensure_non_modal_dialog(m_add_force_dialog, m_simulation, m_viewport, this, SLOT(commit_add_force()));

    show_non_modal_dialog(m_add_force_dialog);
}

void MainWindow::commit_add_object()
{
    if (!m_add_object_dialog)
    {
        return;
    }

    std::string error_message;
    if (!m_simulation->add_object(m_add_object_dialog->spec(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        show_failure(QString("Object creation failed: %1").arg(failure_message), "Object Creation Failed", failure_message);
        return;
    }

    reset_elapsed_time();
    refresh_view_state();
    statusBar()->showMessage("Added test object");
}

void MainWindow::commit_add_force()
{
    if (!m_add_force_dialog)
    {
        return;
    }

    std::string error_message;
    if (!m_simulation->add_force_entity(m_add_force_dialog->spec(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        show_failure(QString("Force creation failed: %1").arg(failure_message), "Force Creation Failed", failure_message);
        return;
    }

    reset_elapsed_time();
    refresh_view_state();
    statusBar()->showMessage("Added force entity");
}

void MainWindow::edit_selected_entity()
{
    const SceneEntitySelection& selected = m_simulation->selected_entity();

    if (!m_simulation->can_author_scene() || selected.id == 0)
    {
        statusBar()->showMessage("Select an entity and reset simulation before editing");
        return;
    }

    if (!m_simulation->can_edit_selected_entity())
    {
        statusBar()->showMessage("The selected entity does not have an editor");
        return;
    }

    if (selected.kind == SceneEntityKindPhysicsObject)
    {
        SimulationController::SpawnedObjectSpec object_spec;

        if (!m_simulation->get_selected_object_spec(&object_spec))
        {
            statusBar()->showMessage("Could not load selected object properties");
            return;
        }

        ensure_non_modal_dialog(m_edit_object_dialog, m_simulation, m_viewport, this, SLOT(commit_edit_object()));

        m_edit_object_dialog->setWindowTitle("Edit Object");
        m_edit_object_dialog->set_spec(object_spec);
        show_non_modal_dialog(m_edit_object_dialog);
        statusBar()->showMessage("Editing selected object");
        return;
    }

    if (selected.kind == SceneEntityKindRagdoll)
    {
        RagdollSceneSpec ragdoll_spec;

        if (!m_simulation->get_selected_ragdoll_spec(&ragdoll_spec))
        {
            statusBar()->showMessage("Could not load selected ragdoll properties");
            return;
        }

        ensure_non_modal_dialog(m_edit_ragdoll_dialog, m_simulation, m_viewport, this, SLOT(commit_edit_ragdoll()));

        m_edit_ragdoll_dialog->set_spec(ragdoll_spec);
        show_non_modal_dialog(m_edit_ragdoll_dialog);
        statusBar()->showMessage("Editing selected ragdoll");
        return;
    }

    if (selected.kind == SceneEntityKindForce)
    {
        SimulationController::ForceSpec force_spec;

        if (!m_simulation->get_selected_force_spec(&force_spec))
        {
            statusBar()->showMessage("Could not load selected force properties");
            return;
        }

        ensure_non_modal_dialog(m_edit_force_dialog, m_simulation, m_viewport, this, SLOT(commit_edit_force()));

        m_edit_force_dialog->setWindowTitle("Edit Force");
        m_edit_force_dialog->set_spec(force_spec);
        show_non_modal_dialog(m_edit_force_dialog);
        statusBar()->showMessage("Editing selected force");
        return;
    }

    statusBar()->showMessage("Selected entity type has no property editor yet");
}

void MainWindow::commit_edit_object()
{
    std::string error_message;

    if (!m_edit_object_dialog)
    {
        return;
    }

    restore_dialog_selection(m_edit_object_dialog->edit_entity_id(), SceneEntityKindPhysicsObject);

    if (!m_simulation->update_selected_object(m_edit_object_dialog->spec(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        show_failure(QString("Object edit failed: %1").arg(failure_message), "Object Edit Failed", failure_message);
        return;
    }

    reset_elapsed_time();
    refresh_view_state();
    statusBar()->showMessage("Updated selected object");
}

void MainWindow::commit_edit_ragdoll()
{
    std::string error_message;

    if (!m_edit_ragdoll_dialog)
    {
        return;
    }

    restore_dialog_selection(m_edit_ragdoll_dialog->edit_entity_id(), SceneEntityKindRagdoll);

    if (!m_simulation->update_selected_ragdoll(m_edit_ragdoll_dialog->spec(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        show_failure(QString("Ragdoll edit failed: %1").arg(failure_message), "Ragdoll Edit Failed", failure_message);
        return;
    }

    refresh_after_scene_change(false);
    statusBar()->showMessage("Updated selected ragdoll");
}

void MainWindow::commit_edit_force()
{
    std::string error_message;

    if (!m_edit_force_dialog)
    {
        return;
    }

    restore_dialog_selection(m_edit_force_dialog->edit_entity_id(), SceneEntityKindForce);

    if (!m_simulation->update_selected_force(m_edit_force_dialog->spec(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        show_failure(QString("Force edit failed: %1").arg(failure_message), "Force Edit Failed", failure_message);
        return;
    }

    reset_elapsed_time();
    refresh_view_state();
    statusBar()->showMessage("Updated selected force");
}

void MainWindow::delete_selected_entity()
{
    if (!m_simulation->delete_selected_entity())
    {
        statusBar()->showMessage("Select an entity and reset simulation before deleting");
        return;
    }

    refresh_after_scene_change(false);
    statusBar()->showMessage("Deleted selected entity");
}

void MainWindow::duplicate_selected_entity()
{
    std::string error_message;

    if (!m_simulation->duplicate_selected_entity(&error_message))
    {
        if (!error_message.empty())
        {
            const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
            show_failure(QString("Duplicate failed: %1").arg(failure_message), "Duplicate Failed", failure_message);
        }
        else
        {
            statusBar()->showMessage("Select an entity and reset simulation before duplicating");
        }
        return;
    }

    refresh_after_scene_change(m_simulation->selected_entity().kind == SceneEntityKindRagdoll);
    statusBar()->showMessage("Duplicated selected entity");
}

void MainWindow::deselect_entity()
{
    if (m_simulation->axis_move_session().active)
    {
        m_simulation->cancel_axis_move();
        refresh_view_state();
        statusBar()->showMessage("Move cancelled");
        return;
    }

    if (m_simulation->axis_rotate_session().active)
    {
        m_simulation->cancel_axis_rotate();
        refresh_view_state();
        statusBar()->showMessage("Rotation cancelled");
        return;
    }

    if (m_simulation->uniform_scale_session().active)
    {
        m_simulation->cancel_uniform_scale();
        refresh_view_state();
        statusBar()->showMessage("Scale cancelled");
        return;
    }

    if (m_simulation->selected_entity().id == 0)
    {
        return;
    }

    m_simulation->clear_selected_entity();
    refresh_view_state();
    statusBar()->showMessage("Selection cleared");
}