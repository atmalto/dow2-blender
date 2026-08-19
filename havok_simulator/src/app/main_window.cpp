#include "main_window.h"

#include <QAction>
#include <QComboBox>
#include <QCoreApplication>
#include <QDockWidget>
#include <QDoubleSpinBox>
#include <QFileDialog>
#include <QFileInfo>
#include <QFormLayout>
#include <QIcon>
#include <QImage>
#include <QLabel>
#include <QMenu>
#include <QMenuBar>
#include <QMessageBox>
#include <QPainter>
#include <QPixmap>
#include <QShortcut>
#include <QSizePolicy>
#include <QSize>
#include <QStringList>
#include <QStandardItemModel>
#include <QStatusBar>
#include <QTimer>
#include <QToolBar>
#include <QVBoxLayout>
#include <QWidget>

#include "main_window_ui_state.h"
#include "new_scene_dialog.h"
#include "ragdoll_preview_window.h"
#include "scene_file_commands.h"
#include "scene_presets.h"
#include "simulation_controller.h"
#include "tool_dialogs.h"
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

    QIcon load_toolbar_icon(const QString& file_name)
    {
        const int icon_size = 24;
        const QString candidates[] = {
            QCoreApplication::applicationDirPath() + "/../../media/" + file_name,
            QCoreApplication::applicationDirPath() + "/../media/" + file_name,
            QCoreApplication::applicationDirPath() + "/media/" + file_name,
            QString("media/") + file_name
        };

        for (int index = 0; index < 4; ++index)
        {
            const QString& candidate = candidates[index];
            if (!QFileInfo(candidate).exists())
            {
                continue;
            }

            QImage source(candidate);
            if (source.isNull())
            {
                continue;
            }

            QImage scaled_image = source
                .convertToFormat(QImage::Format_ARGB32_Premultiplied)
                .scaled(icon_size, icon_size, Qt::KeepAspectRatio, Qt::SmoothTransformation);
            QImage canvas(icon_size, icon_size, QImage::Format_ARGB32_Premultiplied);
            QPainter painter(&canvas);

            canvas.fill(Qt::transparent);
            painter.drawImage(
                (icon_size - scaled_image.width()) / 2,
                (icon_size - scaled_image.height()) / 2,
                scaled_image);
            painter.end();

            return QIcon(QPixmap::fromImage(canvas));
        }

        return QIcon();
    }

}

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
    , m_simulation(0)
    , m_viewport(0)
    , m_new_scene_action(0)
    , m_load_scene_action(0)
    , m_save_scene_action(0)
    , m_open_ragdoll_action(0)
    , m_import_physics_action(0)
    , m_clear_scene_action(0)
    , m_add_object_action(0)
    , m_add_force_action(0)
    , m_edit_entity_action(0)
    , m_delete_entity_action(0)
    , m_duplicate_entity_action(0)
    , m_play_action(0)
    , m_pause_action(0)
    , m_step_action(0)
    , m_reset_action(0)
    , m_scene_menu(0)
    , m_simulation_menu(0)
    , m_add_object_dialog(0)
    , m_edit_object_dialog(0)
    , m_add_force_dialog(0)
    , m_edit_force_dialog(0)
    , m_edit_ragdoll_dialog(0)
    , m_ragdoll_preview_window(0)
    , m_scene_dock(0)
    , m_simulation_dock(0)
    , m_entity_select_combo(0)
    , m_duration_limit_combo(0)
    , m_ragdoll_start_x(0)
    , m_ragdoll_start_y(0)
    , m_ragdoll_start_z(0)
    , m_scene_summary_label(0)
    , m_ragdoll_path_label(0)
    , m_simulation_summary_label(0)
    , m_step_timer(0)
    , m_elapsed_simulation_time(0.0f)
    , m_simulation_duration_limit_seconds(10.0f)
{
    setWindowTitle("Havok Scene Simulator");
    resize(1280, 800);

    m_simulation = new SimulationController();
    m_viewport = new ViewportWidget(this);
    m_viewport->set_simulation(m_simulation);
    connect(m_viewport, SIGNAL(selection_changed()), this, SLOT(viewport_selection_changed()));
    setCentralWidget(m_viewport);

    m_step_timer = new QTimer(this);
    m_step_timer->setInterval(16);

    create_actions();
    create_menus();
    create_toolbar();
    create_docks();
    refresh_ui();

    connect(m_step_timer, SIGNAL(timeout()), this, SLOT(advance_simulation()));

    statusBar()->showMessage("Ready");
}

void MainWindow::create_actions()
{
    QShortcut* deselect_shortcut = 0;
    QShortcut* toggle_play_pause_shortcut = 0;

    m_new_scene_action = new QAction("New Scene", this);
    m_load_scene_action = new QAction("Load Scene", this);
    m_save_scene_action = new QAction("Save Scene", this);
    m_open_ragdoll_action = new QAction("Open Ragdoll", this);
    m_import_physics_action = new QAction("Import Physics", this);
    m_clear_scene_action = new QAction("Clear Scene", this);
    m_add_object_action = new QAction("Add Object", this);
    m_add_force_action = new QAction("Add Force", this);
    m_edit_entity_action = new QAction("Edit Selected", this);
    m_delete_entity_action = new QAction("Delete Selected", this);
    m_duplicate_entity_action = new QAction("Duplicate Selected", this);
    m_play_action = new QAction("Play", this);
    m_pause_action = new QAction("Pause", this);
    m_step_action = new QAction("Step", this);
    m_reset_action = new QAction("Reset", this);
    m_settings_action = new QAction("Settings", this);

    m_new_scene_action->setIcon(load_toolbar_icon("new.png"));
    m_open_ragdoll_action->setIcon(load_toolbar_icon("import-ragdoll.png"));
    m_import_physics_action->setIcon(load_toolbar_icon("import-physics.png"));
    m_clear_scene_action->setIcon(load_toolbar_icon("clear-scene.png"));
    m_add_object_action->setIcon(load_toolbar_icon("add-rigid-body.png"));
    m_add_force_action->setIcon(load_toolbar_icon("add-force.png"));
    m_edit_entity_action->setIcon(load_toolbar_icon("edit.png"));
    m_delete_entity_action->setIcon(load_toolbar_icon("remove.png"));
    m_duplicate_entity_action->setIcon(load_toolbar_icon("duplicate.png"));
    m_play_action->setIcon(load_toolbar_icon("play.png"));
    m_pause_action->setIcon(load_toolbar_icon("pause.png"));
    m_step_action->setIcon(load_toolbar_icon("step.png"));
    m_reset_action->setIcon(load_toolbar_icon("reset.png"));
    m_settings_action->setIcon(load_toolbar_icon("config.png"));
    m_settings_action->setToolTip("Simulation Settings (ragdoll weight & gravity)");

    m_new_scene_action->setShortcut(QKeySequence("Ctrl+N"));
    m_load_scene_action->setShortcut(QKeySequence("Ctrl+O"));
    m_save_scene_action->setShortcut(QKeySequence("Ctrl+S"));
    m_clear_scene_action->setShortcut(QKeySequence("Ctrl+W"));
    m_add_object_action->setShortcut(QKeySequence("R"));
    m_add_force_action->setShortcut(QKeySequence("F"));
    m_edit_entity_action->setShortcut(QKeySequence("E"));
    m_delete_entity_action->setShortcut(QKeySequence("Delete"));
    m_step_action->setShortcut(QKeySequence(Qt::Key_Right));
    m_reset_action->setShortcut(QKeySequence("Backspace"));

    deselect_shortcut = new QShortcut(QKeySequence(Qt::Key_Escape), this);
    toggle_play_pause_shortcut = new QShortcut(QKeySequence(Qt::Key_Space), this);

    m_new_scene_action->setEnabled(true);
    m_import_physics_action->setEnabled(true);
    m_clear_scene_action->setEnabled(true);

    connect(m_new_scene_action, SIGNAL(triggered()), this, SLOT(open_new_scene_dialog()));
    connect(m_load_scene_action, SIGNAL(triggered()), this, SLOT(load_scene()));
    connect(m_save_scene_action, SIGNAL(triggered()), this, SLOT(save_scene()));
    connect(m_open_ragdoll_action, SIGNAL(triggered()), this, SLOT(open_ragdoll()));
    connect(m_import_physics_action, SIGNAL(triggered()), this, SLOT(import_physics()));
    connect(m_clear_scene_action, SIGNAL(triggered()), this, SLOT(clear_scene()));
    connect(m_add_object_action, SIGNAL(triggered()), this, SLOT(open_add_object_dialog()));
    connect(m_add_force_action, SIGNAL(triggered()), this, SLOT(open_add_force_dialog()));
    connect(m_edit_entity_action, SIGNAL(triggered()), this, SLOT(edit_selected_entity()));
    connect(m_delete_entity_action, SIGNAL(triggered()), this, SLOT(delete_selected_entity()));
    connect(m_duplicate_entity_action, SIGNAL(triggered()), this, SLOT(duplicate_selected_entity()));
    connect(m_play_action, SIGNAL(triggered()), this, SLOT(play_simulation()));
    connect(m_pause_action, SIGNAL(triggered()), this, SLOT(pause_simulation()));
    connect(m_step_action, SIGNAL(triggered()), this, SLOT(step_simulation()));
    connect(m_reset_action, SIGNAL(triggered()), this, SLOT(reset_simulation()));
    connect(m_settings_action, SIGNAL(triggered()), this, SLOT(open_settings_dialog()));
    connect(deselect_shortcut, SIGNAL(activated()), this, SLOT(deselect_entity()));
    connect(toggle_play_pause_shortcut, SIGNAL(activated()), this, SLOT(toggle_play_pause()));
}

void MainWindow::create_menus()
{
    m_scene_menu = menuBar()->addMenu("Scene");
    m_scene_menu->addAction(m_new_scene_action);
    m_scene_menu->addAction(m_load_scene_action);
    m_scene_menu->addAction(m_save_scene_action);
    m_scene_menu->addAction(m_open_ragdoll_action);
    m_scene_menu->addAction(m_import_physics_action);
    m_scene_menu->addAction(m_clear_scene_action);
    m_scene_menu->addSeparator();
    m_scene_menu->addAction(m_add_object_action);
    m_scene_menu->addAction(m_add_force_action);
    m_scene_menu->addSeparator();
    m_scene_menu->addAction(m_edit_entity_action);
    m_scene_menu->addAction(m_duplicate_entity_action);
    m_scene_menu->addAction(m_delete_entity_action);

    m_simulation_menu = menuBar()->addMenu("Simulation");
    m_simulation_menu->addAction(m_play_action);
    m_simulation_menu->addAction(m_pause_action);
    m_simulation_menu->addAction(m_step_action);
    m_simulation_menu->addAction(m_reset_action);
    m_simulation_menu->addSeparator();
    m_simulation_menu->addAction(m_settings_action);
}

void MainWindow::create_toolbar()
{
    QToolBar* toolbar = addToolBar("Main");
    QLabel* entity_label = 0;
    QLabel* duration_label = 0;

    toolbar->setMovable(false);
    toolbar->setIconSize(QSize(24, 24));
    toolbar->setToolButtonStyle(Qt::ToolButtonIconOnly);
    toolbar->setStyleSheet(
        "QToolBar { background: #12161d; border: 0px; spacing: 4px; padding: 4px; }"
        "QToolButton { background: transparent; border: 0px; padding: 0px; margin: 0px; }"
        "QToolButton:hover { background: #2a3242; border: 0px; }"
        "QToolButton:pressed { background: transparent; border: 0px; }"
        "QToolButton:checked { background: transparent; border: 0px; }"
        "QToolButton:disabled { background: transparent; border: 0px; color: #7a8391; }"
        "QToolBar::separator { width: 1px; margin: 6px 4px; background: #2f3947; }");
    toolbar->addAction(m_new_scene_action);
    toolbar->addAction(m_open_ragdoll_action);
    toolbar->addAction(m_import_physics_action);
    toolbar->addAction(m_clear_scene_action);
    toolbar->addSeparator();
    toolbar->addAction(m_add_object_action);
    toolbar->addAction(m_add_force_action);
    toolbar->addAction(m_edit_entity_action);
    toolbar->addAction(m_duplicate_entity_action);
    toolbar->addAction(m_delete_entity_action);
    toolbar->addSeparator();
    toolbar->addAction(m_play_action);
    toolbar->addAction(m_pause_action);
    toolbar->addAction(m_step_action);
    toolbar->addAction(m_reset_action);
    toolbar->addAction(m_settings_action);
    toolbar->addSeparator();

    entity_label = new QLabel("Scene", toolbar);
    m_entity_select_combo = new QComboBox(toolbar);
    m_entity_select_combo->setMinimumWidth(220);
    connect(m_entity_select_combo, SIGNAL(currentIndexChanged(int)), this, SLOT(entity_selection_changed(int)));

    duration_label = new QLabel("Duration", toolbar);
    m_duration_limit_combo = new QComboBox(toolbar);
    m_duration_limit_combo->addItem("Off");
    m_duration_limit_combo->addItem("5 seconds");
    m_duration_limit_combo->addItem("10 seconds");
    m_duration_limit_combo->addItem("20 seconds");
    m_duration_limit_combo->setCurrentIndex(2);
    m_duration_limit_combo->setMinimumWidth(110);
    connect(m_duration_limit_combo, SIGNAL(currentIndexChanged(int)), this, SLOT(duration_limit_changed(int)));

    toolbar->addWidget(entity_label);
    toolbar->addWidget(m_entity_select_combo);
    toolbar->addSeparator();
    toolbar->addWidget(duration_label);
    toolbar->addWidget(m_duration_limit_combo);
}

void MainWindow::create_docks()
{
    if (!m_scene_summary_label)
    {
        m_scene_summary_label = new QLabel(statusBar());
        m_scene_summary_label->setMinimumWidth(260);
        m_scene_summary_label->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Preferred);
        statusBar()->addPermanentWidget(m_scene_summary_label, 1);
    }

    if (!m_simulation_summary_label)
    {
        m_simulation_summary_label = new QLabel(statusBar());
        m_simulation_summary_label->setMinimumWidth(520);
        m_simulation_summary_label->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
        m_simulation_summary_label->setTextInteractionFlags(Qt::TextSelectableByMouse);
        statusBar()->addPermanentWidget(m_simulation_summary_label, 2);
    }
}

void MainWindow::close_scene_dialogs()
{
    if (m_add_object_dialog)
    {
        m_add_object_dialog->close();
    }
    if (m_add_force_dialog)
    {
        m_add_force_dialog->close();
    }
    if (m_edit_object_dialog)
    {
        m_edit_object_dialog->close();
    }
    if (m_edit_force_dialog)
    {
        m_edit_force_dialog->close();
    }
    if (m_edit_ragdoll_dialog)
    {
        m_edit_ragdoll_dialog->close();
    }
}

void MainWindow::open_new_scene_dialog()
{
    std::string error_message;

    if (!m_simulation->can_author_scene())
    {
        statusBar()->showMessage("Reset simulation before creating a new scene");
        return;
    }

    NewSceneDialog dialog(this);
    if (dialog.exec() != QDialog::Accepted)
    {
        return;
    }

    close_scene_dialogs();
    m_step_timer->stop();

    if (!m_simulation->create_scene_from_preset(dialog.selected_preset(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        statusBar()->showMessage(QString("New scene failed: %1").arg(failure_message));
        QMessageBox::critical(this, "New Scene Failed", failure_message);
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    refresh_ragdoll_preview_window(false);
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
    m_step_timer->stop();

    if (!file_commands.finish_load_scene(file_path))
    {
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    refresh_ragdoll_preview_window(false);
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

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    refresh_ragdoll_preview_window(true);
}

void MainWindow::open_add_object_dialog()
{
    if (!m_simulation->can_author_scene())
    {
        statusBar()->showMessage("Reset simulation before changing scene entities");
        return;
    }

    if (!m_add_object_dialog)
    {
        m_add_object_dialog = new AddObjectDialog(m_simulation, m_viewport, this);
        m_add_object_dialog->setWindowModality(Qt::NonModal);
        connect(m_add_object_dialog, SIGNAL(accepted()), this, SLOT(commit_add_object()));
    }

    m_add_object_dialog->show();
    m_add_object_dialog->raise();
    m_add_object_dialog->activateWindow();
}

void MainWindow::open_add_force_dialog()
{
    if (!m_simulation->can_author_scene())
    {
        statusBar()->showMessage("Reset simulation before changing scene entities");
        return;
    }

    if (!m_add_force_dialog)
    {
        m_add_force_dialog = new AddForceDialog(m_simulation, m_viewport, this);
        m_add_force_dialog->setWindowModality(Qt::NonModal);
        connect(m_add_force_dialog, SIGNAL(accepted()), this, SLOT(commit_add_force()));
    }

    m_add_force_dialog->show();
    m_add_force_dialog->raise();
    m_add_force_dialog->activateWindow();
}

void MainWindow::clear_scene()
{
    close_scene_dialogs();

    m_step_timer->stop();
    m_simulation->clear_scene();
    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    refresh_ragdoll_preview_window(false);
    statusBar()->showMessage("Scene cleared");
}

void MainWindow::import_physics()
{
    SceneFileCommands file_commands(*this, *statusBar(), *m_simulation);
    if (!file_commands.import_physics())
    {
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
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
        statusBar()->showMessage(QString("Object creation failed: %1").arg(failure_message));
        QMessageBox::critical(this, "Object Creation Failed", failure_message);
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
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
        statusBar()->showMessage(QString("Force creation failed: %1").arg(failure_message));
        QMessageBox::critical(this, "Force Creation Failed", failure_message);
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    statusBar()->showMessage("Added force entity");
}

void MainWindow::edit_selected_entity()
{
    const SceneEntitySelection& selected = m_simulation->selected_entity();
    std::string error_message;

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

        if (!m_edit_object_dialog)
        {
            m_edit_object_dialog = new AddObjectDialog(m_simulation, m_viewport, this);
            m_edit_object_dialog->setWindowModality(Qt::NonModal);
            connect(m_edit_object_dialog, SIGNAL(accepted()), this, SLOT(commit_edit_object()));
        }

        m_edit_object_dialog->setWindowTitle("Edit Object");
        m_edit_object_dialog->set_spec(object_spec);
        m_edit_object_dialog->show();
        m_edit_object_dialog->raise();
        m_edit_object_dialog->activateWindow();
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

        if (!m_edit_ragdoll_dialog)
        {
            m_edit_ragdoll_dialog = new RagdollPropertiesDialog(m_simulation, m_viewport, this);
            m_edit_ragdoll_dialog->setWindowModality(Qt::NonModal);
            connect(m_edit_ragdoll_dialog, SIGNAL(accepted()), this, SLOT(commit_edit_ragdoll()));
        }

        m_edit_ragdoll_dialog->set_spec(ragdoll_spec);
        m_edit_ragdoll_dialog->show();
        m_edit_ragdoll_dialog->raise();
        m_edit_ragdoll_dialog->activateWindow();
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

        if (!m_edit_force_dialog)
        {
            m_edit_force_dialog = new AddForceDialog(m_simulation, m_viewport, this);
            m_edit_force_dialog->setWindowModality(Qt::NonModal);
            connect(m_edit_force_dialog, SIGNAL(accepted()), this, SLOT(commit_edit_force()));
        }

        m_edit_force_dialog->setWindowTitle("Edit Force");
        m_edit_force_dialog->set_spec(force_spec);
        m_edit_force_dialog->show();
        m_edit_force_dialog->raise();
        m_edit_force_dialog->activateWindow();
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

    if (m_edit_object_dialog->edit_entity_id() != 0)
    {
        m_simulation->select_entity(m_edit_object_dialog->edit_entity_id(), SceneEntityKindPhysicsObject);
    }

    if (!m_simulation->update_selected_object(m_edit_object_dialog->spec(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        statusBar()->showMessage(QString("Object edit failed: %1").arg(failure_message));
        QMessageBox::critical(this, "Object Edit Failed", failure_message);
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    statusBar()->showMessage("Updated selected object");
}

void MainWindow::commit_edit_ragdoll()
{
    std::string error_message;

    if (!m_edit_ragdoll_dialog)
    {
        return;
    }

    if (m_edit_ragdoll_dialog->edit_entity_id() != 0)
    {
        m_simulation->select_entity(m_edit_ragdoll_dialog->edit_entity_id(), SceneEntityKindRagdoll);
    }

    if (!m_simulation->update_selected_ragdoll(m_edit_ragdoll_dialog->spec(), &error_message))
    {
        const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
        statusBar()->showMessage(QString("Ragdoll edit failed: %1").arg(failure_message));
        QMessageBox::critical(this, "Ragdoll Edit Failed", failure_message);
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    refresh_ragdoll_preview_window(false);
    statusBar()->showMessage("Updated selected ragdoll");
}

void MainWindow::commit_edit_force()
{
    std::string error_message;

    if (!m_edit_force_dialog)
    {
        return;
    }

    if (m_edit_force_dialog->edit_entity_id() != 0)
    {
        m_simulation->select_entity(m_edit_force_dialog->edit_entity_id(), SceneEntityKindForce);
    }

    if (!m_simulation->update_selected_force(m_edit_force_dialog->spec(), &error_message))
        {
            const QString failure_message = QString::fromLocal8Bit(error_message.c_str());
            statusBar()->showMessage(QString("Force edit failed: %1").arg(failure_message));
            QMessageBox::critical(this, "Force Edit Failed", failure_message);
            return;
        }

        m_elapsed_simulation_time = 0.0f;
        m_viewport->updateGL();
        refresh_ui();
        statusBar()->showMessage("Updated selected force");
}

void MainWindow::delete_selected_entity()
{
    if (!m_simulation->delete_selected_entity())
    {
        statusBar()->showMessage("Select an entity and reset simulation before deleting");
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    refresh_ragdoll_preview_window(false);
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
            statusBar()->showMessage(QString("Duplicate failed: %1").arg(failure_message));
            QMessageBox::critical(this, "Duplicate Failed", failure_message);
        }
        else
        {
            statusBar()->showMessage("Select an entity and reset simulation before duplicating");
        }
        return;
    }

    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
    refresh_ragdoll_preview_window(m_simulation->selected_entity().kind == SceneEntityKindRagdoll);
    statusBar()->showMessage("Duplicated selected entity");
}

void MainWindow::deselect_entity()
{
    if (m_simulation->axis_move_session().active)
    {
        m_simulation->cancel_axis_move();
        m_viewport->updateGL();
        refresh_ui();
        statusBar()->showMessage("Move cancelled");
        return;
    }

    if (m_simulation->axis_rotate_session().active)
    {
        m_simulation->cancel_axis_rotate();
        m_viewport->updateGL();
        refresh_ui();
        statusBar()->showMessage("Rotation cancelled");
        return;
    }

    if (m_simulation->uniform_scale_session().active)
    {
        m_simulation->cancel_uniform_scale();
        m_viewport->updateGL();
        refresh_ui();
        statusBar()->showMessage("Scale cancelled");
        return;
    }

    if (m_simulation->selected_entity().id == 0)
    {
        return;
    }

    m_simulation->clear_selected_entity();
    m_viewport->updateGL();
    refresh_ui();
    statusBar()->showMessage("Selection cleared");
}

void MainWindow::toggle_play_pause()
{
    if (m_simulation->is_playing())
    {
        pause_simulation();
    }
    else
    {
        play_simulation();
    }
}

void MainWindow::play_simulation()
{
    if (m_simulation->has_active_tool_session())
    {
        statusBar()->showMessage("Confirm or cancel the active transform before playing");
        return;
    }

    m_simulation->set_playing(true);
    m_step_timer->start();
    refresh_ui();
}

void MainWindow::pause_simulation()
{
    m_simulation->set_playing(false);
    m_step_timer->stop();
    refresh_ui();
}

void MainWindow::step_simulation()
{
    if (m_simulation->has_active_tool_session())
    {
        statusBar()->showMessage("Confirm or cancel the active transform before stepping");
        return;
    }

    m_simulation->step();
    m_elapsed_simulation_time += m_simulation->timestep();
    m_viewport->updateGL();
    refresh_ui();
}

void MainWindow::reset_simulation()
{
    m_step_timer->stop();
    m_simulation->set_playing(false);
    m_simulation->reset();
    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
}

void MainWindow::open_settings_dialog()
{
    SimulationSettingsDialog dialog(this);
    dialog.exec();

    // Ragdoll mass scale and gravity are applied when the world is (re)built, so
    // reset the simulation after the user adjusts them to make changes take effect.
    reset_simulation();
}

void MainWindow::ground_mode_changed(int index)
{
    m_simulation->set_ground_mode(index == 0 ? SimulationController::GroundFlat : SimulationController::GroundSlanted);
    m_elapsed_simulation_time = 0.0f;
    m_viewport->updateGL();
    refresh_ui();
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
        m_viewport->updateGL();
        refresh_ui();
        refresh_ragdoll_preview_window(static_cast<SceneEntityKind>(entity_kind) == SceneEntityKindRagdoll);
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

    if (!m_simulation->can_author_scene())
    {
        statusBar()->showMessage("Reset simulation before changing scene entities");
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

    refresh_ui();

    refresh_ragdoll_preview_window(selected.kind == SceneEntityKindRagdoll);

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

void MainWindow::advance_simulation()
{
    if (!m_simulation->is_playing())
    {
        return;
    }

    m_simulation->step();
    m_elapsed_simulation_time += m_simulation->timestep();

    if (m_simulation_duration_limit_seconds > 0.0f && m_elapsed_simulation_time >= m_simulation_duration_limit_seconds)
    {
        m_step_timer->stop();
        m_simulation->set_playing(false);
        statusBar()->showMessage(QString("Simulation auto-paused at %1 seconds").arg(m_simulation_duration_limit_seconds, 0, 'f', 0));
    }

    m_viewport->updateGL();
    refresh_ui();
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
        m_ragdoll_preview_window->show();
        m_ragdoll_preview_window->raise();
        m_ragdoll_preview_window->activateWindow();
    }
}