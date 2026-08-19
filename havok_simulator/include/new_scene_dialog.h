#ifndef HAVOK_SCENE_APP_NEW_SCENE_DIALOG_H
#define HAVOK_SCENE_APP_NEW_SCENE_DIALOG_H

#include <QDialog>

#include "scene_presets.h"

class QComboBox;

class NewSceneDialog : public QDialog
{
    Q_OBJECT

public:
    explicit NewSceneDialog(QWidget* parent = 0);

    ScenePresetId selected_preset() const;

private:
    QComboBox* m_preset_combo;
};

#endif