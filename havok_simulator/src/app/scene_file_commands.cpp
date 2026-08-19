#include "scene_file_commands.h"

#include <QDialog>
#include <QFileDialog>
#include <QFileInfo>
#include <QMessageBox>
#include <QStatusBar>
#include <QStringList>

#include "physics_import.h"
#include "physics_import_dialog.h"
#include "scene_persistence.h"
#include "simulation_controller.h"

SceneFileCommands::SceneFileCommands(QWidget& parent, QStatusBar& status_bar, SimulationController& simulation)
    : m_parent(parent)
    , m_status_bar(status_bar)
    , m_simulation(simulation)
{
}

bool SceneFileCommands::begin_load_scene(QString* file_path) const
{
    if (!file_path)
    {
        return false;
    }

    *file_path = QFileDialog::getOpenFileName(
        &m_parent,
        "Load Scene",
        QString(),
        "Havok Scene App Scene (*.hkscene);;All Files (*)");

    if (file_path->isEmpty())
    {
        return false;
    }

    if (!m_simulation.can_author_scene())
    {
        m_status_bar.showMessage("Reset simulation before loading a scene");
        return false;
    }

    return true;
}

bool SceneFileCommands::finish_load_scene(const QString& file_path) const
{
    PersistedSceneData scene;
    std::vector<std::string> warnings;
    std::string error_message;

    if (!load_scene_file(file_path.toLocal8Bit().constData(), &scene, &warnings, &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        m_status_bar.showMessage(QString("Scene load failed: %1").arg(failure_message));
        QMessageBox::critical(&m_parent, "Scene Load Failed", failure_message);
        return false;
    }

    if (!m_simulation.load_persisted_scene(scene, &warnings, &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        m_status_bar.showMessage(QString("Scene load failed: %1").arg(failure_message));
        QMessageBox::critical(&m_parent, "Scene Load Failed", failure_message);
        return false;
    }

    m_status_bar.showMessage(QString("Loaded scene: %1").arg(QFileInfo(file_path).fileName()));

    if (!warnings.empty())
    {
        QStringList lines;
        std::size_t warning_index = 0;

        for (warning_index = 0; warning_index < warnings.size(); ++warning_index)
        {
            lines << QString::fromLocal8Bit(warnings[warning_index].c_str());
        }

        QMessageBox::warning(&m_parent, "Scene Load Warnings", lines.join("\n"));
    }

    return true;
}

bool SceneFileCommands::save_scene() const
{
    const QString file_path = QFileDialog::getSaveFileName(
        &m_parent,
        "Save Scene",
        QString(),
        "Havok Scene App Scene (*.hkscene);;All Files (*)");
    PersistedSceneData scene;
    std::string error_message;

    if (file_path.isEmpty())
    {
        return false;
    }

    if (!m_simulation.can_author_scene())
    {
        m_status_bar.showMessage("Reset simulation before saving a scene");
        return false;
    }

    if (!m_simulation.build_persisted_scene(&scene) ||
        !save_scene_file(file_path.toLocal8Bit().constData(), scene, &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        m_status_bar.showMessage(QString("Scene save failed: %1").arg(failure_message));
        QMessageBox::critical(&m_parent, "Scene Save Failed", failure_message);
        return false;
    }

    m_status_bar.showMessage(QString("Saved scene: %1").arg(QFileInfo(file_path).fileName()));

    if (!scene.ragdolls.empty())
    {
        QMessageBox::information(
            &m_parent,
            "External Ragdoll References",
            "Ragdoll HKX files are not embedded in the scene file.\n"
            "The scene stores file references for ragdolls and will skip them on load if those HKX files are missing.");
    }

    return true;
}

bool SceneFileCommands::open_ragdoll() const
{
    if (!m_simulation.can_author_scene())
    {
        m_status_bar.showMessage("Reset simulation before changing scene entities");
        return false;
    }

    const QString file_path = QFileDialog::getOpenFileName(
        &m_parent,
        "Open Ragdoll HKX",
        QString(),
        "Havok Files (*.hkx);;All Files (*)");

    if (file_path.isEmpty())
    {
        return false;
    }

    std::string error_message;
    if (!m_simulation.load_ragdoll(file_path.toLocal8Bit().constData(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        m_status_bar.showMessage(QString("Ragdoll load failed: %1").arg(failure_message));
        QMessageBox::critical(&m_parent, "Ragdoll Load Failed", failure_message);
        return false;
    }

    m_status_bar.showMessage(QString("Loaded ragdoll: %1").arg(file_path));
    return true;
}

bool SceneFileCommands::import_physics() const
{
    const QString file_path = QFileDialog::getOpenFileName(
        &m_parent,
        "Import Physics HKX",
        QString(),
        "Havok Physics (*.hkx)");
    std::vector<ImportedPhysicsSystem> systems;
    std::vector<int> selected_systems;
    std::string error_message;

    if (file_path.isEmpty())
    {
        return false;
    }

    if (!m_simulation.can_author_scene())
    {
        m_status_bar.showMessage("Reset simulation before importing physics");
        return false;
    }

    if (!load_imported_physics_systems(file_path.toLocal8Bit().constData(), systems, &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        m_status_bar.showMessage(QString("Physics import scan failed: %1").arg(failure_message));
        QMessageBox::critical(&m_parent, "Physics Import Failed", failure_message);
        return false;
    }

    PhysicsImportDialog dialog(file_path, systems, &m_parent);
    if (dialog.exec() != QDialog::Accepted)
    {
        return false;
    }

    selected_systems = dialog.selected_system_indices();
    if (selected_systems.empty())
    {
        m_status_bar.showMessage("No physics systems were selected for import");
        return false;
    }

    if (!m_simulation.import_physics_systems(systems, selected_systems, &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        m_status_bar.showMessage(QString("Physics import failed: %1").arg(failure_message));
        QMessageBox::critical(&m_parent, "Physics Import Failed", failure_message);
        return false;
    }

    m_status_bar.showMessage(QString("Imported physics from %1").arg(QFileInfo(file_path).fileName()));
    return true;
}
