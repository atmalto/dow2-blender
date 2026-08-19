#include "main_window_ui_state.h"

#include <QAction>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QLabel>
#include <QString>
#include <QStandardItemModel>

#include "simulation_controller.h"

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

    void add_entity_group_header(QComboBox* combo, const QString& label)
    {
        QStandardItemModel* model = qobject_cast<QStandardItemModel*>(combo ? combo->model() : 0);
        const int index = combo ? combo->count() : 0;

        if (!combo)
        {
            return;
        }

        combo->addItem(label);
        if (model && model->item(index))
        {
            model->item(index)->setEnabled(false);
        }
    }

    void add_entity_combo_item(QComboBox* combo, const std::string& name, SceneEntityId id, SceneEntityKind kind)
    {
        const int index = combo ? combo->count() : 0;

        if (!combo)
        {
            return;
        }

        combo->addItem(QString("  %1").arg(QString::fromLocal8Bit(name.c_str())));
        combo->setItemData(index, static_cast<uint>(id), kEntityIdRole);
        combo->setItemData(index, static_cast<int>(kind), kEntityKindRole);
    }
}

void MainWindowUiState::apply(
    SimulationController& simulation,
    const MainWindowUiView& view,
    float elapsed_simulation_time,
    float simulation_duration_limit_seconds)
{
    const bool is_playing = simulation.is_playing();
    const bool has_transform_session = simulation.has_active_tool_session();
    const bool can_author_scene = simulation.can_author_scene();
    const bool has_ragdoll = simulation.has_ragdoll();
    const SceneEntitySelection& selected = simulation.selected_entity();
    const SceneDocument& scene_document = simulation.scene_document();
    float ragdoll_x = 0.0f;
    float ragdoll_y = 0.0f;
    float ragdoll_z = 0.0f;

    simulation.get_ragdoll_start_position(ragdoll_x, ragdoll_y, ragdoll_z);

    if (view.play_action)
    {
        view.play_action->setEnabled(!is_playing && !has_transform_session);
    }
    if (view.pause_action)
    {
        view.pause_action->setEnabled(is_playing);
    }
    if (view.step_action)
    {
        view.step_action->setEnabled(!is_playing && !has_transform_session);
    }
    if (view.reset_action)
    {
        view.reset_action->setEnabled(true);
    }
    if (view.new_scene_action)
    {
        view.new_scene_action->setEnabled(can_author_scene);
    }
    if (view.load_scene_action)
    {
        view.load_scene_action->setEnabled(can_author_scene);
    }
    if (view.save_scene_action)
    {
        view.save_scene_action->setEnabled(can_author_scene);
    }
    if (view.open_ragdoll_action)
    {
        view.open_ragdoll_action->setEnabled(can_author_scene);
    }
    if (view.import_physics_action)
    {
        view.import_physics_action->setEnabled(can_author_scene);
    }
    if (view.add_object_action)
    {
        view.add_object_action->setEnabled(can_author_scene);
    }
    if (view.edit_entity_action)
    {
        view.edit_entity_action->setEnabled(can_author_scene && simulation.can_edit_selected_entity());
    }
    if (view.duplicate_entity_action)
    {
        view.duplicate_entity_action->setEnabled(can_author_scene && selected.id != 0);
    }
    if (view.delete_entity_action)
    {
        view.delete_entity_action->setEnabled(can_author_scene && selected.id != 0);
    }
    if (view.clear_scene_action)
    {
        view.clear_scene_action->setEnabled(true);
    }

    if (view.entity_select_combo)
    {
        int selected_index = -1;
        const std::vector<RagdollSceneEntity>& ragdolls = scene_document.ragdolls();
        const std::vector<ForceSceneEntity>& forces = scene_document.forces();
        const std::vector<PhysicsObjectSceneEntity>& objects = scene_document.objects();
        std::size_t entity_index = 0;

        view.entity_select_combo->blockSignals(true);
        view.entity_select_combo->clear();

        add_entity_group_header(view.entity_select_combo, "Ragdolls");
        for (entity_index = 0; entity_index < ragdolls.size(); ++entity_index)
        {
            add_entity_combo_item(
                view.entity_select_combo,
                ragdolls[entity_index].record.name,
                ragdolls[entity_index].record.id,
                SceneEntityKindRagdoll);
            if (selected.id == ragdolls[entity_index].record.id && selected.kind == SceneEntityKindRagdoll)
            {
                selected_index = view.entity_select_combo->count() - 1;
            }
        }

        add_entity_group_header(view.entity_select_combo, "Forces");
        for (entity_index = 0; entity_index < forces.size(); ++entity_index)
        {
            add_entity_combo_item(
                view.entity_select_combo,
                forces[entity_index].record.name,
                forces[entity_index].record.id,
                SceneEntityKindForce);
            if (selected.id == forces[entity_index].record.id && selected.kind == SceneEntityKindForce)
            {
                selected_index = view.entity_select_combo->count() - 1;
            }
        }

        add_entity_group_header(view.entity_select_combo, "Rigid Bodies");
        for (entity_index = 0; entity_index < objects.size(); ++entity_index)
        {
            add_entity_combo_item(
                view.entity_select_combo,
                objects[entity_index].record.name,
                objects[entity_index].record.id,
                SceneEntityKindPhysicsObject);
            if (selected.id == objects[entity_index].record.id && selected.kind == SceneEntityKindPhysicsObject)
            {
                selected_index = view.entity_select_combo->count() - 1;
            }
        }

        if (selected_index >= 0)
        {
            view.entity_select_combo->setCurrentIndex(selected_index);
        }
        else if (view.entity_select_combo->count() > 0)
        {
            view.entity_select_combo->setCurrentIndex(0);
        }

        view.entity_select_combo->blockSignals(false);
    }

    if (view.scene_summary_label)
    {
        const int object_count = simulation.spawned_object_count();
        const int force_count = simulation.force_count();
        const int ragdoll_count = simulation.ragdoll_count();
        QString summary;

        if (object_count == 0 && force_count == 0 && ragdoll_count == 0)
        {
            summary = "Scene is empty. Use New Scene, import, or add entities to begin.";
        }
        else
        {
            summary = QString("Scene contains %1 rigid body object(s), %2 force entity(s), and %3 ragdoll scene entit%4.")
                .arg(object_count)
                .arg(force_count)
                .arg(ragdoll_count)
                .arg(ragdoll_count == 1 ? "y" : "ies");
        }

        if (selected.id != 0)
        {
            summary += QString(" Selected %1 #%2.")
                .arg(scene_entity_kind_label(selected.kind))
                .arg(selected.id);
        }

        if (!can_author_scene)
        {
            summary += " Reset is required before scene authoring.";
        }

        view.scene_summary_label->setText(summary);
        view.scene_summary_label->setToolTip(summary);
    }

    if (view.ragdoll_path_label)
    {
        const QString ragdoll_path = has_ragdoll
            ? QString::fromLocal8Bit(simulation.ragdoll_path().c_str())
            : QString("No ragdoll loaded");

        view.ragdoll_path_label->setText(ragdoll_path);
        view.ragdoll_path_label->setToolTip(has_ragdoll ? ragdoll_path : QString());
    }

    if (view.ragdoll_start_x && view.ragdoll_start_y && view.ragdoll_start_z)
    {
        view.ragdoll_start_x->blockSignals(true);
        view.ragdoll_start_y->blockSignals(true);
        view.ragdoll_start_z->blockSignals(true);
        view.ragdoll_start_x->setValue(ragdoll_x);
        view.ragdoll_start_y->setValue(ragdoll_y);
        view.ragdoll_start_z->setValue(ragdoll_z);
        view.ragdoll_start_x->setEnabled(has_ragdoll && can_author_scene);
        view.ragdoll_start_y->setEnabled(has_ragdoll && can_author_scene);
        view.ragdoll_start_z->setEnabled(has_ragdoll && can_author_scene);
        view.ragdoll_start_x->blockSignals(false);
        view.ragdoll_start_y->blockSignals(false);
        view.ragdoll_start_z->blockSignals(false);
    }

    if (view.simulation_summary_label)
    {
        RagdollRuntimeDiagnostics ragdoll_diagnostics;
        QString summary = is_playing
            ? "Simulation running at 60 Hz fixed timestep."
            : "Simulation paused. Use Step for single-frame advance.";

        if (simulation_duration_limit_seconds > 0.0f)
        {
            summary += QString(" Auto-pause limit: %1 s.").arg(simulation_duration_limit_seconds, 0, 'f', 0);
        }
        else
        {
            summary += " Auto-pause limit: Off.";
        }

        summary += QString(" Simulated time: %1 s.").arg(elapsed_simulation_time, 0, 'f', 2);

        if (has_ragdoll)
        {
            summary += " Ragdoll rigid bodies are loaded into the world.";

            if (simulation.get_selected_ragdoll_runtime_diagnostics(&ragdoll_diagnostics))
            {
                summary += QString(" Hold: %1.")
                    .arg(ragdoll_diagnostics.is_holding ? "on" : "off");
                summary += QString(" Max stress: %1")
                    .arg(ragdoll_diagnostics.max_stress, 0, 'f', 3);

                if (ragdoll_diagnostics.max_stress_bone_index >= 0)
                {
                    summary += QString(" (bone %1).").arg(ragdoll_diagnostics.max_stress_bone_index);
                }
                else
                {
                    summary += ".";
                }
            }
        }

        view.simulation_summary_label->setText(summary);
        view.simulation_summary_label->setToolTip(summary);
    }
}