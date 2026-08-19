#include "physics_import_dialog.h"

#include "app_theme.h"

#include <QDialogButtonBox>
#include <QFileInfo>
#include <QLabel>
#include <QListWidget>
#include <QListWidgetItem>
#include <QVBoxLayout>

#include "physics_import.h"

PhysicsImportDialog::PhysicsImportDialog(const QString& source_path, const std::vector<ImportedPhysicsSystem>& systems, QWidget* parent)
    : QDialog(parent)
    , m_system_list(0)
{
    QVBoxLayout* layout = new QVBoxLayout(this);
    QLabel* description = 0;
    QDialogButtonBox* buttons = 0;
    std::size_t system_index = 0;

    setWindowTitle("Import Physics Systems");
    resize(420, 320);

    description = new QLabel(
        QString("Select the physics systems to import from %1. Systems start unchecked by default.")
            .arg(QFileInfo(source_path).fileName()),
        this);
    description->setWordWrap(true);
    layout->addWidget(description);

    m_system_list = new QListWidget(this);
    for (system_index = 0; system_index < systems.size(); ++system_index)
    {
        const ImportedPhysicsSystem& system = systems[system_index];
        QListWidgetItem* item = new QListWidgetItem(
            QString::fromLocal8Bit(system.name.c_str())
                + QString(" (%1 bodies)").arg(static_cast<int>(system.objects.size())),
            m_system_list);

        if (system.skipped_body_count > 0)
        {
            item->setText(item->text() + QString(", %1 skipped").arg(system.skipped_body_count));
        }

        item->setFlags(item->flags() | Qt::ItemIsUserCheckable);
        item->setCheckState(Qt::Unchecked);
        item->setData(Qt::UserRole, static_cast<int>(system_index));
    }
    layout->addWidget(m_system_list);

    buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, Qt::Horizontal, this);
    clear_dialog_button_box_icons(buttons);
    connect(buttons, SIGNAL(accepted()), this, SLOT(accept()));
    connect(buttons, SIGNAL(rejected()), this, SLOT(reject()));
    layout->addWidget(buttons);
}

std::vector<int> PhysicsImportDialog::selected_system_indices() const
{
    std::vector<int> selected;
    int item_index = 0;

    if (!m_system_list)
    {
        return selected;
    }

    for (item_index = 0; item_index < m_system_list->count(); ++item_index)
    {
        QListWidgetItem* item = m_system_list->item(item_index);
        if (item && item->checkState() == Qt::Checked)
        {
            selected.push_back(item->data(Qt::UserRole).toInt());
        }
    }

    return selected;
}