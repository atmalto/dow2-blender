#ifndef HAVOK_SCENE_APP_PHYSICS_IMPORT_DIALOG_H
#define HAVOK_SCENE_APP_PHYSICS_IMPORT_DIALOG_H

#include <vector>

#include <QDialog>

struct ImportedPhysicsSystem;

class QListWidget;

class PhysicsImportDialog : public QDialog
{
    Q_OBJECT

public:
    PhysicsImportDialog(const QString& source_path, const std::vector<ImportedPhysicsSystem>& systems, QWidget* parent = 0);

    std::vector<int> selected_system_indices() const;

private:
    QListWidget* m_system_list;
};

#endif