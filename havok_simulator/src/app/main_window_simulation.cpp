#include "main_window.h"

#include <QStatusBar>
#include <QTimer>

#include "simulation_controller.h"
#include "tool_dialogs.h"

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
    stop_simulation_timer();
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
    refresh_view_state();
}

void MainWindow::reset_simulation()
{
    stop_simulation_timer();
    m_simulation->set_playing(false);
    m_simulation->reset();
    reset_elapsed_time();
    refresh_view_state();
}

void MainWindow::open_settings_dialog()
{
    SimulationSettingsDialog dialog(this);
    dialog.exec();

    // Ragdoll mass scale and gravity are applied when the world is (re)built, so
    // reset the simulation after the user adjusts them to make changes take effect.
    reset_simulation();
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
        stop_simulation_timer();
        m_simulation->set_playing(false);
        statusBar()->showMessage(QString("Simulation auto-paused at %1 seconds").arg(m_simulation_duration_limit_seconds, 0, 'f', 0));
    }

    refresh_view_state();
}