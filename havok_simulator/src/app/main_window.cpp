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
#include "sync_listener_dialog.h"
#include "sync_protocol.h"
#include "sync_server.h"
#include "simulation_controller.h"
#include "tool_dialogs.h"
#include "viewport_widget.h"

namespace
{
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
    , m_settings_action(0)
    , m_sync_listener_action(0)
    , m_scene_menu(0)
    , m_simulation_menu(0)
    , m_add_object_dialog(0)
    , m_edit_object_dialog(0)
    , m_add_force_dialog(0)
    , m_edit_force_dialog(0)
    , m_edit_ragdoll_dialog(0)
    , m_ragdoll_preview_window(0)
    , m_sync_listener_dialog(0)
    , m_sync_server(0)
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
    , m_sync_listener_port(sync_protocol::kDefaultPort)
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
    m_sync_listener_action = new QAction("Sync Listener...", this);

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
    connect(m_sync_listener_action, SIGNAL(triggered()), this, SLOT(open_sync_listener_dialog()));
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
    m_scene_menu->addAction(m_sync_listener_action);
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

bool MainWindow::ensure_can_author_scene(const QString& message)
{
    if (m_simulation->can_author_scene())
    {
        return true;
    }

    statusBar()->showMessage(message);
    return false;
}

void MainWindow::show_failure(const QString& status_message, const QString& dialog_title, const QString& detail)
{
    statusBar()->showMessage(status_message);
    QMessageBox::critical(this, dialog_title, detail);
}

void MainWindow::show_non_modal_dialog(QWidget* dialog)
{
    if (!dialog)
    {
        return;
    }

    dialog->show();
    dialog->raise();
    dialog->activateWindow();
}

void MainWindow::stop_simulation_timer()
{
    if (m_step_timer)
    {
        m_step_timer->stop();
    }
}

void MainWindow::reset_elapsed_time()
{
    m_elapsed_simulation_time = 0.0f;
}

void MainWindow::refresh_view_state()
{
    m_viewport->updateGL();
    refresh_ui();
}

void MainWindow::refresh_after_scene_change(bool open_for_selected_ragdoll)
{
    reset_elapsed_time();
    refresh_view_state();
    refresh_ragdoll_preview_window(open_for_selected_ragdoll);
}

void MainWindow::refresh_after_selection_change(bool redraw_viewport, bool open_for_selected_ragdoll)
{
    if (redraw_viewport)
    {
        m_viewport->updateGL();
    }

    refresh_ui();
    refresh_ragdoll_preview_window(open_for_selected_ragdoll);
}

void MainWindow::restore_dialog_selection(SceneEntityId entity_id, SceneEntityKind kind)
{
    if (entity_id != 0)
    {
        m_simulation->select_entity(entity_id, kind);
    }
}