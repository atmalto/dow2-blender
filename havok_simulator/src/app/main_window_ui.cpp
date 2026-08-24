#include "main_window.h"

#include <QComboBox>
#include <QDoubleSpinBox>
#include <QStatusBar>

#include "main_window_ui_state.h"
#include "ragdoll_preview_window.h"
#include "simulation_controller.h"
#include "viewport_widget.h"

namespace
{
    const int kEntityIdRole = Qt::UserRole;
    const int kEntityKindRole = Qt::UserRole + 1;

    const char* scene_entity_kind_label(SceneEntityKind kind)
    {
        if (kind == SceneEntityKindRagdoll)
        {
            return "ragdoll";
        }
        if (kind == SceneEntityKindPhysicsObject)
        {
            return "object";
        }
        if (kind == SceneEntityKindForce)
        {
            return "force";
        }

        return "entity";
    }
}

void MainWindow::ground_mode_changed(int index)
{
    m_simulation->set_ground_mode(index == 0 ? SimulationController::GroundFlat : SimulationController::GroundSlanted);
    reset_elapsed_time();
    refresh_view_state();
}

void MainWindow::entity_selection_changed(int index)
{
    if (!m_entity_select_combo)
    {
        return;
    }

    const uint entity_id = m_entity_select_combo->itemData(index, kEntityIdRole).toUInt();
    const int entity_kind = m_entity_select_combo->itemData(index, kEntityKindRole).toInt();

    if (entity_id == 0 || entity_kind == SceneEntityKindNone)
    {
        return;
    }

    if (m_simulation->select_entity(static_cast<SceneEntityId>(entity_id), static_cast<SceneEntityKind>(entity_kind)))
    {
        refresh_after_selection_change(true, static_cast<SceneEntityKind>(entity_kind) == SceneEntityKindRagdoll);
        m_viewport->setFocus(Qt::OtherFocusReason);
    }
}

void MainWindow::duration_limit_changed(int index)
{
    if (index == 1)
    {
        m_simulation_duration_limit_seconds = 5.0f;
    }
    else if (index == 2)
    {
        m_simulation_duration_limit_seconds = 10.0f;
    }
    else if (index == 3)
    {
        m_simulation_duration_limit_seconds = 20.0f;
    }
    else
    {
        m_simulation_duration_limit_seconds = 0.0f;
    }

    refresh_ui();
}

void MainWindow::ragdoll_start_position_changed()
{
    if (!m_ragdoll_start_x || !m_ragdoll_start_y || !m_ragdoll_start_z)
    {
        return;
    }

    if (!ensure_can_author_scene("Reset simulation before changing scene entities"))
    {
        refresh_ui();
        return;
    }

    m_simulation->set_ragdoll_start_position(
        static_cast<float>(m_ragdoll_start_x->value()),
        static_cast<float>(m_ragdoll_start_y->value()),
        static_cast<float>(m_ragdoll_start_z->value()));
    m_viewport->updateGL();
}

void MainWindow::viewport_selection_changed()
{
    const SceneEntitySelection& selected = m_simulation->selected_entity();

    refresh_after_selection_change(false, selected.kind == SceneEntityKindRagdoll);

    if (selected.id != 0)
    {
        statusBar()->showMessage(QString("Selected %1 #%2")
            .arg(scene_entity_kind_label(selected.kind))
            .arg(selected.id));
    }
    else
    {
        statusBar()->showMessage("Selection cleared");
    }
}

void MainWindow::refresh_ui()
{
    MainWindowUiView view = {
        m_play_action,
        m_pause_action,
        m_step_action,
        m_reset_action,
        m_new_scene_action,
        m_load_scene_action,
        m_save_scene_action,
        m_open_ragdoll_action,
        m_import_physics_action,
        m_add_object_action,
        m_edit_entity_action,
        m_duplicate_entity_action,
        m_delete_entity_action,
        m_clear_scene_action,
        m_entity_select_combo,
        m_ragdoll_start_x,
        m_ragdoll_start_y,
        m_ragdoll_start_z,
        m_scene_summary_label,
        m_ragdoll_path_label,
        m_simulation_summary_label
    };

    MainWindowUiState::apply(
        *m_simulation,
        view,
        m_elapsed_simulation_time,
        m_simulation_duration_limit_seconds);
}

void MainWindow::refresh_ragdoll_preview_window(bool open_for_selected_ragdoll)
{
    RagdollPreviewData preview_data;
    const SceneEntitySelection& selected = m_simulation->selected_entity();
    bool has_preview_data = false;

    if (!open_for_selected_ragdoll)
    {
        if (!m_ragdoll_preview_window || !m_ragdoll_preview_window->isVisible())
        {
            return;
        }
    }

    if (selected.kind == SceneEntityKindRagdoll && selected.id != 0)
    {
        has_preview_data = m_simulation->get_ragdoll_preview_data(selected.id, &preview_data);
    }
    else if (m_ragdoll_preview_window && m_ragdoll_preview_window->entity_id() != 0)
    {
        has_preview_data = m_simulation->get_ragdoll_preview_data(m_ragdoll_preview_window->entity_id(), &preview_data);
    }

    if (!has_preview_data)
    {
        if (m_ragdoll_preview_window)
        {
            m_ragdoll_preview_window->clear_preview_data();
            m_ragdoll_preview_window->hide();
        }
        return;
    }

    if (!m_ragdoll_preview_window)
    {
        m_ragdoll_preview_window = new RagdollPreviewWindow(this);
        m_ragdoll_preview_window->setWindowModality(Qt::NonModal);
    }

    m_ragdoll_preview_window->set_preview_data(preview_data);

    if (open_for_selected_ragdoll)
    {
        show_non_modal_dialog(m_ragdoll_preview_window);
    }
}