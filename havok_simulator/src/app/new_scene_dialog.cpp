#include "new_scene_dialog.h"

#include "app_theme.h"

#include <QComboBox>
#include <QDialogButtonBox>
#include <QFormLayout>
#include <QLabel>
#include <QVBoxLayout>

NewSceneDialog::NewSceneDialog(QWidget* parent)
    : QDialog(parent)
    , m_preset_combo(0)
{
    QVBoxLayout* root_layout = new QVBoxLayout(this);
    QLabel* description = new QLabel("Choose a preset for the new scene.", this);
    QFormLayout* form_layout = new QFormLayout();
    QDialogButtonBox* buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, Qt::Horizontal, this);

    setWindowTitle("New Scene");
    resize(360, 140);

    description->setWordWrap(true);
    root_layout->addWidget(description);

    m_preset_combo = new QComboBox(this);
    m_preset_combo->addItem("Blank scene", static_cast<int>(ScenePresetBlank));
    m_preset_combo->addItem("Flat plane + force + cube", static_cast<int>(ScenePresetFlatPlaneWithForce));
    m_preset_combo->addItem("Diagonal plane", static_cast<int>(ScenePresetDiagonalPlane));
    form_layout->addRow("Preset", m_preset_combo);

    root_layout->addLayout(form_layout);
    clear_dialog_button_box_icons(buttons);

    connect(buttons, SIGNAL(accepted()), this, SLOT(accept()));
    connect(buttons, SIGNAL(rejected()), this, SLOT(reject()));
    root_layout->addWidget(buttons);
}

ScenePresetId NewSceneDialog::selected_preset() const
{
    if (!m_preset_combo)
    {
        return ScenePresetBlank;
    }

    return static_cast<ScenePresetId>(m_preset_combo->itemData(m_preset_combo->currentIndex()).toInt());
}