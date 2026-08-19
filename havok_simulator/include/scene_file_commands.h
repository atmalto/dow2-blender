#ifndef HAVOK_SCENE_APP_SCENE_FILE_COMMANDS_H
#define HAVOK_SCENE_APP_SCENE_FILE_COMMANDS_H

class QString;
class QStatusBar;
class QWidget;

class SimulationController;

class SceneFileCommands
{
public:
    SceneFileCommands(QWidget& parent, QStatusBar& status_bar, SimulationController& simulation);

    bool begin_load_scene(QString* file_path) const;
    bool finish_load_scene(const QString& file_path) const;
    bool save_scene() const;
    bool open_ragdoll() const;
    bool import_physics() const;

private:
    QWidget& m_parent;
    QStatusBar& m_status_bar;
    SimulationController& m_simulation;
};

#endif
